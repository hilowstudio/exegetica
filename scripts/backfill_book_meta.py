"""Backfill genre shelves + surname-first sort key onto an already-seeded db/books.db.

The reader corpus was first seeded before the adapter captured genres/author_sort, so those rows
have chapters but no shelving data. This refetches ONLY each book's content.opf (a few KB via raw
GitHub) and UPDATEs the row — no multi-MB tarball re-download.

    .venv\\Scripts\\python.exe scripts\\backfill_book_meta.py          # only rows missing genres
    .venv\\Scripts\\python.exe scripts\\backfill_book_meta.py --all    # refresh every row

Resumable and idempotent: safe to re-run; skipped books can be retried by running again.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import sqlite3  # noqa: E402

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from webapp.sources import standardebooks as se  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402


def _ensure_cols(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("pragma table_info(books)")}
    for col in ("author_sort", "genres"):
        if col not in cols:
            con.execute(f"alter table books add column {col} text")
    con.commit()


async def _run(args) -> None:
    db_path = _ROOT / args.db
    if not db_path.exists():
        sys.exit(f"{args.db} not found — seed it first.")
    con = sqlite3.connect(db_path)
    _ensure_cols(con)
    if args.all:
        slugs = [r[0] for r in con.execute("select slug from books")]
    else:
        slugs = [r[0] for r in con.execute(
            "select slug from books where genres is null or genres = '' or genres = '[]'")]
    print(f"{len(slugs)} books to backfill", flush=True)
    if not slugs:
        con.close()
        return

    timeout = httpx.Timeout(connect=15.0, read=30.0, write=15.0, pool=15.0)
    headers = {"User-Agent": BROWSER_UA}
    ok = fail = 0
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def worker(slug):
            async with sem:
                try:
                    return slug, await asyncio.wait_for(se.fetch_meta(client, slug), timeout=45)
                except Exception:  # noqa: BLE001
                    return slug, None

        tasks = [asyncio.create_task(worker(s)) for s in slugs]
        for fut in asyncio.as_completed(tasks):
            slug, meta = await fut
            n = ok + fail + 1
            if meta:
                con.execute(
                    "update books set genres=?, author_sort=? where slug=?",
                    (json.dumps(meta["genres"]), meta["author_sort"], slug),
                )
                con.commit()
                ok += 1
                if n % 50 == 0 or n == len(slugs):
                    print(f"  [{n}/{len(slugs)}] {ok} updated, {fail} skipped", flush=True)
            else:
                fail += 1
                print(f"  [{n}/{len(slugs)}] SKIP {slug}", flush=True)

    # A quick shelf summary so we can see the taxonomy that resulted.
    counts: dict[str, int] = {}
    for (g_json,) in con.execute("select genres from books where genres is not null"):
        for g in json.loads(g_json or "[]"):
            counts[g] = counts.get(g, 0) + 1
    con.close()
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:14]
    print(f"\nbackfilled {ok} ({fail} skipped) in {time.monotonic() - start:.0f}s", flush=True)
    print("top genres: " + ", ".join(f"{g} {c}" for g, c in top), flush=True)
    if fail:
        print("  re-run to retry skipped books.", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill genres + author_sort onto db/books.db.")
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--all", action="store_true", help="refresh every row, not just those missing genres")
    p.add_argument("--concurrency", type=int, default=8)
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
