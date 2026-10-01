"""Seed the e-reader corpus (db/books.db) from Standard Ebooks (Phase 1 showcase).

This is the BULK reader-ingest path — deliberately distinct from the extraction pipeline:
download → parse structure → store cleaned chapters + genre shelves. It skips the expensive
LLM derive/objectives steps, which a reader doesn't need.

    # prove it on a small sample
    .venv\\Scripts\\python.exe scripts\\seed_books.py --limit 15
    # a single title (debugging)
    .venv\\Scripts\\python.exe scripts\\seed_books.py --slug jane-austen_pride-and-prejudice
    # the full ~1,500-book showcase (resumable — safe to re-run after any interruption)
    .venv\\Scripts\\python.exe scripts\\seed_books.py

Robust for a long bulk run: a completion-pool (a slow book never blocks others), a hard
per-book time cap, transient-retry on the download, and resume — a re-run skips books already
seeded with genres and retries the rest. Publish with:
    .venv\\Scripts\\python.exe scripts\\publish_db.py books
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sqlite3
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from webapp.sources import standardebooks as se  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402

_SCHEMA = """
create table if not exists books (
    id            integer primary key autoincrement,
    slug          text unique not null,
    title         text not null,
    author        text,
    author_sort   text,                         -- 'Surname, Given' library sort key
    source        text not null,
    license       text,
    us_clear      integer not null default 1,
    language      text,
    subjects      text,                         -- JSON array (LoC-style subject headings)
    genres        text,                         -- JSON array (SE se:subject shelves)
    chapter_count integer not null default 0,
    word_count    integer not null default 0,
    added_at      text not null default (datetime('now'))
);
create table if not exists book_chapters (
    book_id        integer not null,
    section_number integer not null,
    title          text,
    html           text not null,
    words          integer not null default 0,
    primary key (book_id, section_number)
);
create index if not exists book_chapters_book_idx on book_chapters(book_id);
"""


def _open_db(path: pathlib.Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    # Self-migrate a books.db built before genres/author_sort existed.
    cols = {r[1] for r in con.execute("pragma table_info(books)")}
    for col in ("author_sort", "genres"):
        if col not in cols:
            con.execute(f"alter table books add column {col} text")
    con.commit()
    return con


def _seeded_slugs(con: sqlite3.Connection) -> set[str]:
    """Slugs already fully seeded WITH genres — the resume set. Rows lacking genres (e.g. from
    an older schema) are treated as unseeded so a re-run backfills them."""
    return {r[0] for r in con.execute(
        "select slug from books where genres is not null and genres != '[]'")}


def _store(con: sqlite3.Connection, book: dict) -> None:
    cur = con.cursor()
    cur.execute("select id from books where slug=?", (book["slug"],))
    row = cur.fetchone()
    if row:  # idempotent re-seed
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug, title, author, author_sort, source, license, us_clear,
                             language, subjects, genres, chapter_count, word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (book["slug"], book["title"], book["author"], book.get("author_sort"), se.SOURCE,
         se.LICENSE, 1, book["language"], json.dumps(book["subjects"]),
         json.dumps(book.get("genres") or []), len(book["chapters"]), book["word_count"]),
    )
    bid = cur.lastrowid
    cur.executemany(
        "insert into book_chapters(book_id, section_number, title, html, words) values(?,?,?,?,?)",
        [(bid, ch["section_number"], ch["title"], ch["html"], ch["words"]) for ch in book["chapters"]],
    )
    con.commit()


async def _run(args) -> None:
    db_path = _ROOT / args.db
    con = _open_db(db_path)
    # Explicit timeouts: a slow/huge tarball trips the read timeout well inside the per-book cap.
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        if args.slug:
            slugs = [args.slug]
        else:
            print("listing Standard Ebooks repos…", flush=True)
            slugs = await se.list_books(client, limit=args.limit)
            if args.skip_existing:
                have = _seeded_slugs(con)
                slugs = [s for s in slugs if s not in have]
                print(f"  {len(have)} already seeded; {len(slugs)} to fetch", flush=True)
            else:
                print(f"  {len(slugs)} book repos to seed", flush=True)

        sem = asyncio.Semaphore(args.concurrency)

        async def worker(slug):
            async with sem:
                try:  # asyncio.TimeoutError (a subclass of Exception) is the hard per-book cap
                    return slug, await asyncio.wait_for(se.fetch_book(client, slug), timeout=args.timeout)
                except Exception:  # noqa: BLE001 — never let one book kill the run
                    return slug, None

        ok = fail = 0
        total = len(slugs)
        start = time.monotonic()
        tasks = [asyncio.create_task(worker(s)) for s in slugs]
        for fut in asyncio.as_completed(tasks):
            slug, book = await fut
            n = ok + fail + 1
            if book:
                _store(con, book)
                ok += 1
                genres = ", ".join((book.get("genres") or [])[:3]) or "—"
                print(f"  [{n}/{total}] {book['title'][:44]:44} {book['word_count']:>7,}w  {genres}", flush=True)
            else:
                fail += 1
                print(f"  [{n}/{total}] SKIP {slug}", flush=True)

    size = db_path.stat().st_size
    print(f"\nseeded {ok} ({fail} skipped) this run in {time.monotonic() - start:.0f}s "
          f"→ {args.db} ({size / 1e6:.1f} MB)", flush=True)
    if fail:
        print("  re-run to retry skipped books (resume skips the ones already done).", flush=True)
    con.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Seed db/books.db from Standard Ebooks.")
    p.add_argument("--db", default="db/books.db", help="output SQLite path (default db/books.db)")
    p.add_argument("--limit", type=int, default=None, help="max books to seed (default: all)")
    p.add_argument("--slug", help="seed a single repo slug (debugging)")
    p.add_argument("--concurrency", type=int, default=4, help="parallel fetches in flight")
    p.add_argument("--timeout", type=float, default=100.0, help="hard per-book time cap (seconds)")
    p.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True,
                   help="resume: skip books already seeded with genres (default on)")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
