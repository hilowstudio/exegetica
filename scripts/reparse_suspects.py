"""Re-parse the books probe_missing_openings.py flagged, with the fixed Gutenberg parser.

For each single-file suspect: fetch the full book, and if the new parse holds >=3% more text
than what's stored, replace ONLY its chapters (title, author, shelf, cover, classification all
kept), then run the usual cleanup. Merged works from the shelf import (multi-volume sets and
pulp-by-author collections) are listed for import_shelf_adds.py --refresh --only instead, since
their volumes must be re-merged together.

    .venv\\Scripts\\python.exe scripts\\reparse_suspects.py --dry-run
    .venv\\Scripts\\python.exe scripts\\reparse_suspects.py
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import pathlib
import re
import sqlite3
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from format_gutenberg import clean_book, dedup_book  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402
import import_shelf_adds as imp  # noqa: E402

_PROBE = _ROOT / ".seed_cache" / "reading_room" / "opening_probe.json"
_OUT = _ROOT / ".seed_cache" / "reading_room" / "reparse_results.json"


def _merged_works() -> dict[str, str]:
    """first gid -> shelf, for every multi-file work in the shelf import."""
    shelves = {r["shelf"] for r in csv.DictReader(open(imp._LEDGER, encoding="utf-8")) if r["decision"] == "add"}
    out = {}
    for shelf in shelves:
        for w in imp._load(shelf):
            if len(w["gids"]) > 1:
                out[w["gids"][0]] = shelf
    return out


def _replace(con, book_id: int, chapters: list[dict]) -> None:
    con.execute("delete from book_chapters where book_id=?", (book_id,))
    con.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(book_id, c["section_number"], c["title"], c["html"], c["words"]) for c in chapters])
    con.execute("update books set chapter_count=?, word_count=? where id=?",
                (len(chapters), sum(c["words"] for c in chapters), book_id))
    con.commit()
    clean_book(con, book_id)
    dedup_book(con, book_id)


async def _run(args) -> None:
    probe = json.loads(_PROBE.read_text(encoding="utf-8"))
    suspects = [p for p in probe if p["suspect"]]
    merged = _merged_works()
    multi = [p for p in suspects if p["gid"] in merged]
    single = [p for p in suspects if p["gid"] not in merged]
    print(f"{len(suspects)} suspects: {len(single)} single-file, {len(multi)} merged works (re-import separately)")
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    results, start = [], time.monotonic()
    async with httpx.AsyncClient(headers={"User-Agent": BROWSER_UA}, follow_redirects=True,
                                 timeout=httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def one(p):
            row = con.execute("select id, title, author, word_count from books where slug=?", (p["slug"],)).fetchone()
            if not row:
                return p, None, None
            async with sem:
                try:
                    book = await asyncio.wait_for(
                        gb.fetch_book(client, p["gid"], {"author": row[2] or "", "title": row[1]}), 180)
                except Exception:  # noqa: BLE001
                    book = None
            return p, row, book

        tasks = [asyncio.create_task(one(p)) for p in single]
        for n, fut in enumerate(asyncio.as_completed(tasks), 1):
            p, row, book = await fut
            if not row or not book:
                results.append({**p, "outcome": "fetch failed"}); continue
            old, new = row[3] or 0, book["word_count"]
            if new >= 1.03 * old:
                if not args.dry_run:
                    _replace(con, row[0], book["chapters"])
                outcome = "replaced"
            else:
                outcome = "kept (no gain)"
            results.append({**p, "outcome": outcome, "old_words": old, "new_words": new,
                            "old_first": p["first_chapter"], "new_first": book["chapters"][0]["title"][:60]})
            if n % 100 == 0:
                print(f"  {n}/{len(single)}  ({time.monotonic() - start:.0f}s)", flush=True)
    con.close()
    _OUT.write_text(json.dumps({"results": results,
                                "merged": [{"gid": p["gid"], "shelf": merged[p["gid"]], "title": p["title"]} for p in multi]},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    rep = [r for r in results if r["outcome"] == "replaced"]
    print(f"\n{'(dry-run) ' if args.dry_run else ''}{len(rep)} replaced, "
          f"{sum(r['outcome'] == 'kept (no gain)' for r in results)} unchanged, "
          f"{sum(r['outcome'] == 'fetch failed' for r in results)} failed, in {time.monotonic() - start:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="db/books.db")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(_run(ap.parse_args()))


if __name__ == "__main__":
    main()
