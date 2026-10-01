"""Seed the e-reader corpus (db/books.db) from the curated Gutenberg manifest.

Reads .seed_cache/gutenberg_manifest.csv (built by harvest_gutenberg.py — already deduped
against Standard Ebooks + CCEL) and ingests each work's HTML into clean, chaptered copies.
Same BULK reader-ingest path as seed_books.py: download → parse structure → store chapters.

    # pilot: a diverse 20-book sample, to eyeball parse quality in the reader
    .venv\\Scripts\\python.exe scripts\\seed_gutenberg.py --sample 20
    # a single work (debugging)
    .venv\\Scripts\\python.exe scripts\\seed_gutenberg.py --id 2488
    # the full curated run (resumable — safe to re-run after any interruption)
    .venv\\Scripts\\python.exe scripts\\seed_gutenberg.py

Resume skips works already seeded with genres. Publish with:
    .venv\\Scripts\\python.exe scripts\\publish_db.py books
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
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA, author_last_name  # noqa: E402

_MANIFEST = _ROOT / ".seed_cache" / "gutenberg_manifest.csv"
_SCHEMA = """
create table if not exists books (
    id integer primary key autoincrement, slug text unique not null, title text not null,
    author text, author_sort text, source text not null, license text,
    us_clear integer not null default 1, language text, subjects text, genres text,
    chapter_count integer not null default 0, word_count integer not null default 0,
    added_at text not null default (datetime('now')));
create table if not exists book_chapters (
    book_id integer not null, section_number integer not null, title text,
    html text not null, words integer not null default 0,
    primary key (book_id, section_number));
create index if not exists book_chapters_book_idx on book_chapters(book_id);
"""

# Trailing edition markers — stripped to a base title so multiple editions of one work group.
_EDITION_MARK = re.compile(
    r"[\s,;—-]+(complete|unabridged|(?:vol(?:ume)?|part|book|no)\.?\s*[\divxlc]+.*)$", re.I)


def _base_title(title: str) -> str:
    t = re.split(r"[;:]", title or "")[0]
    prev = None
    while prev != t:                       # strip repeated tails ("…, Volume 1, Complete")
        prev = t
        t = _EDITION_MARK.sub("", t).strip()
    return t.lower()


def _collapse_editions(rows: list[dict]) -> list[dict]:
    """One work = one book. Group by (surname, base-title); when a whole/complete edition
    exists in a group, drop the split-volume/part editions. Groups that are ONLY splits are
    kept as-is (they collectively are the work)."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((author_last_name(r["author"]), _base_title(r["title"])), []).append(r)
    out, dropped = [], 0
    for members in groups.values():
        if len(members) == 1:
            out.append(members[0]); continue
        whole = [m for m in members if not _EDITION_MARK.search(re.split(r"[;:]", m["title"])[0])]
        if whole:
            out.extend(whole); dropped += len(members) - len(whole)
        else:
            out.extend(members)  # only split volumes exist → keep them all
    if dropped:
        print(f"  edition-collapse: dropped {dropped} split-volume editions where a whole copy exists")
    return out


def _open_db(path: pathlib.Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(_SCHEMA)
    cols = {r[1] for r in con.execute("pragma table_info(books)")}
    for col in ("author_sort", "genres"):
        if col not in cols:
            con.execute(f"alter table books add column {col} text")
    con.commit()
    return con


def _seeded_slugs(con) -> set[str]:
    return {r[0] for r in con.execute(
        "select slug from books where genres is not null and genres != '[]'")}


def _store(con, book: dict) -> None:
    cur = con.cursor()
    cur.execute("select id from books where slug=?", (book["slug"],))
    row = cur.fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,chapter_count,word_count) values(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (book["slug"], book["title"], book["author"], book["author_sort"], gb.SOURCE, gb.LICENSE,
         1, book["language"], json.dumps(book["subjects"]), json.dumps(book["genres"]),
         len(book["chapters"]), book["word_count"]))
    bid = cur.lastrowid
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in book["chapters"]])
    con.commit()


def _expected_slug(row: dict) -> str:
    display, _ = gb._display_name(row["author"])
    return (f"{gb._slugify(display)}_{gb._slugify(row['title'])}"[:78] or "book") + f"-pg{row['gutenberg_id']}"


async def _run(args) -> None:
    con = _open_db(_ROOT / args.db)
    rows = list(csv.DictReader(open(_MANIFEST, encoding="utf-8")))
    if args.id:
        rows = [r for r in rows if r["gutenberg_id"] == str(args.id)]
    else:
        rows = _collapse_editions(rows)
        if args.sample:                       # diverse spread across the genre-sorted manifest
            step = max(1, len(rows) // args.sample)
            rows = rows[::step][:args.sample]
        if args.skip_existing:
            have = _seeded_slugs(con)
            before = len(rows)
            rows = [r for r in rows if _expected_slug(r) not in have]
            print(f"  {before - len(rows)} already seeded; {len(rows)} to fetch", flush=True)
        if args.limit:
            rows = rows[:args.limit]

    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA},
                                 follow_redirects=True) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def worker(row):
            async with sem:
                try:
                    book = await asyncio.wait_for(
                        gb.fetch_book(client, row["gutenberg_id"], row), timeout=args.timeout)
                    return row, book
                except Exception:  # noqa: BLE001 — never let one book kill the run
                    return row, None

        ok = fail = 0
        total = len(rows)
        start = time.monotonic()
        tasks = [asyncio.create_task(worker(r)) for r in rows]
        for fut in asyncio.as_completed(tasks):
            row, book = await fut
            n = ok + fail + 1
            if book:
                _store(con, book)
                ok += 1
                print(f"  [{n}/{total}] {book['title'][:42]:42} {book['word_count']:>7,}w  "
                      f"{len(book['chapters']):>3}ch  {(book['genres'] or ['—'])[0]}", flush=True)
            else:
                fail += 1
                print(f"  [{n}/{total}] SKIP pg{row['gutenberg_id']}  {row['title'][:40]}", flush=True)

    size = (_ROOT / args.db).stat().st_size
    print(f"\nseeded {ok} ({fail} skipped) in {time.monotonic()-start:.0f}s → {args.db} ({size/1e6:.1f} MB)")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Seed db/books.db from the curated Gutenberg manifest.")
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--sample", type=int, default=None, help="ingest a diverse N-book spread (pilot)")
    p.add_argument("--id", help="seed a single Gutenberg id (debugging)")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True)
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
