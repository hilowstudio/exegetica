#!/usr/bin/env python3
"""
Add Project Gutenberg's English dime novels to the Reading Room, one book per novel.

Each dime-novel issue was a single complete story (Nick Carter, Frank Reade, Buffalo Bill,
Frank Merriwell, Deadwood Dick...), so unlike the pulp magazines there's nothing to group:
the Gutenberg text is the book. Candidates come from Gutenberg's catalog (subject or
bookshelf "Dime novels", English only); works already in the library are skipped. Shelving
comes from Gutenberg's subject headings (detective -> Mystery & Crime, inventors/science
fiction -> Science Fiction, romance -> Romance, juvenile -> Children's, else Adventure).

Every book is written with its chapters and checked afterwards (the 2026-09-21 horror batch
went in without chapters because its store step never wrote them).

    .venv\\Scripts\\python.exe scripts\\seed_dime_novels.py --dry-run
    .venv\\Scripts\\python.exe scripts\\seed_dime_novels.py
    .venv\\Scripts\\python.exe scripts\\build_covers_db.py && .venv\\Scripts\\python.exe scripts\\build_covers_db.py --finalize
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from build_pulp_eligibility import norm, surname  # noqa: E402
from format_gutenberg import clean_book  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402

CATALOG = ROOT / ".seed_cache" / "pulp" / "pg_catalog.csv"
DB = ROOT / "db" / "books.db"
SHELVES = (("detective", "Mystery & Crime"), ("mystery", "Mystery & Crime"), ("crime", "Mystery & Crime"),
           ("science fiction", "Science Fiction"), ("inventor", "Science Fiction"), ("mechanics", "Science Fiction"),
           ("romance", "Romance"), ("love stories", "Romance"), ("juvenile", "Children's"))


def sections(subjects: str) -> list[str]:
    s = subjects.lower()
    out = list(dict.fromkeys(sec for kw, sec in SHELVES if kw in s))
    if not out or re.search(r"adventure|western|frontier|indians|trapper|buffalo bill|pioneer", s):
        out.append("Adventure")
    return list(dict.fromkeys(out))


def candidates(con) -> list[dict]:
    have_ids = {s.rsplit("-pg", 1)[1] for (s,) in con.execute("select slug from books where slug like '%-pg%'")}
    have_works = {(norm(re.split(r"[:;]", t or "")[0]), surname(a or "")) for t, a in con.execute("select title, author from books")}
    out, seen = [], set()
    for r in csv.DictReader(open(CATALOG, encoding="utf-8")):
        if r["Type"] != "Text" or r["Language"] != "en":
            continue
        if not re.search(r"dime novel", f"{r['Subjects']} {r['Bookshelves']}", re.I):
            continue
        if re.search(r"history and criticism", r["Subjects"] or "", re.I):
            continue                                                    # writing ABOUT dime novels
        title = " ".join((r["Title"] or "").split())
        first_author = (r["Authors"] or "").split(";")[0].strip()
        author = re.sub(r",\s*\d{3,4}\??-.*$", "", first_author)          # drop life dates
        work = (norm(re.split(r"[:;]", title)[0]), surname(gb._display_name(author)[0]))
        if r["Text#"] in have_ids or work in have_works or work in seen:
            continue                                                    # already ours, or a second edition
        seen.add(work)
        out.append({"gid": r["Text#"], "title": title, "author": author,
                    "subjects": [s.strip() for s in (r["Subjects"] or "").split(";") if s.strip()]})
    return out


def store(con, book: dict, meta: dict) -> int:
    secs = sections("; ".join(meta["subjects"]))
    cover = f"https://www.gutenberg.org/cache/epub/{meta['gid']}/pg{meta['gid']}.cover.medium.jpg"
    cur = con.cursor()
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,subjects,
                             genres,section,genres_backup,title_backup,cover_url,chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (book["slug"], book["title"], book["author"], book["author_sort"], gb.SOURCE, gb.LICENSE, 1, "en",
         json.dumps(meta["subjects"]), json.dumps(secs), json.dumps(secs), json.dumps(secs), meta["title"],
         cover, len(book["chapters"]), book["word_count"]))
    bid = cur.lastrowid
    cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                    [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in book["chapters"]])
    con.commit()
    clean_book(con, bid)                                   # strip Gutenberg cruft, ensure chapter headings
    n = con.execute("select count(*) from book_chapters where book_id=?", (bid,)).fetchone()[0]
    if n != len(book["chapters"]):
        raise RuntimeError(f"{book['title']}: wrote {len(book['chapters'])} chapters, found {n}")
    return bid


async def main_async(dry: bool, limit: int | None) -> None:
    con = sqlite3.connect(DB, timeout=120)
    todo = candidates(con)[:limit] if limit else candidates(con)
    print(f"{len(todo)} dime novels to add")
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    ok, failed, flags = 0, [], []
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as client:
        sem = asyncio.Semaphore(4)

        async def one(meta):
            async with sem:
                try:
                    fetch_meta = {**meta, "subjects": "|".join(meta["subjects"])}   # fetch_book wants a string
                    return meta, await asyncio.wait_for(gb.fetch_book(client, meta["gid"], fetch_meta), 120)
                except Exception:  # noqa: BLE001
                    return meta, None

        for fut in asyncio.as_completed([one(m) for m in todo]):
            meta, book = await fut
            if not book:
                failed.append(meta["title"][:50]); continue
            if len(book["chapters"]) == 1 and book["word_count"] > 20000:
                flags.append(f"{book['title'][:50]} (one {book['word_count']:,}-word chapter)")
            if book["word_count"] < 3000:
                flags.append(f"{book['title'][:50]} (only {book['word_count']:,} words)")
            if not dry:
                store(con, book, meta)
            ok += 1
            if ok % 25 == 0:
                print(f"  {ok} done", flush=True)
    con.close()
    print(f"\n{'(dry run) ' if dry else ''}added {ok}; failed {len(failed)}")
    for f in failed:
        print("  failed:", f)
    for f in flags:
        print("  check:", f)


def main() -> None:
    ap = argparse.ArgumentParser(description="Add Gutenberg's English dime novels to the Reading Room")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    asyncio.run(main_async(a.dry_run, a.limit))


if __name__ == "__main__":
    main()
