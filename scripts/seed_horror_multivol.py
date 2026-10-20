"""Multi-volume horror works: Project Gutenberg splits some titles across 2–3 volume files,
but one work = one book in the Reading Room. Fetch each volume through the same clean-chapter
path (gb.fetch_book), concatenate the chapters in volume order into a single book, and insert
it on the "Horror & Gothic" shelf. Front matter (title pages, contents) is dropped per volume
by gb._SKIP_TITLE, so the merged copy reads continuously.

cover_url is the first volume's PG cover jpeg; run build_covers_db.py afterward to self-host.

    .venv\\Scripts\\python.exe scripts\\seed_horror_multivol.py --dry-run
    .venv\\Scripts\\python.exe scripts\\seed_horror_multivol.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sqlite3
import sys

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
from webapp.sources.matching import BROWSER_UA  # noqa: E402

SECTION = ["Horror & Gothic"]

# One work → the ordered list of Gutenberg volume ids that make it up, plus the concise display
# title. Author comes from the first volume's Gutendex record.
WORKS = [
    {"title": "In a Glass Darkly", "gids": [37172, 37173, 37174]},   # J. Sheridan Le Fanu
    {"title": "The Purcell Papers", "gids": [509, 510, 511]},        # J. Sheridan Le Fanu
    {"title": "Sidonia the Sorceress", "gids": [6700, 6701]},        # Wilhelm Meinhold
]


async def _gutendex(client, gid: int) -> dict | None:
    r = await gb._get_with_retry(client, f"https://gutendex.com/books/{gid}")
    return r.json() if r is not None else None


def _cover_url(formats: dict) -> str | None:
    for k, v in (formats or {}).items():
        if k.startswith("image/") and v and not v.lower().endswith(".zip"):
            return v
    return None


def _store(con, book: dict, cover_url: str | None, raw_title: str) -> None:
    cur = con.cursor()
    cur.execute("select id from books where slug=?", (book["slug"],))
    row = cur.fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,section,genres_backup,title_backup,cover_url,
                             chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (book["slug"], book["title"], book["author"], book["author_sort"], gb.SOURCE, gb.LICENSE,
         1, "en", json.dumps(book["subjects"]), json.dumps(SECTION), json.dumps(SECTION),
         json.dumps(SECTION), raw_title, cover_url, len(book["chapters"]), book["word_count"]))
    # write the chapters too (this was missing, so the 2026-09-21 batch went in with no text;
    # restored by restore_empty_books.py)
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(cur.lastrowid, c["section_number"], c["title"], c["html"], c["words"]) for c in book["chapters"]])
    con.commit()


async def _run(args) -> None:
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    timeout = httpx.Timeout(connect=15.0, read=90.0, write=30.0, pool=15.0)
    ok = fail = 0
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA},
                                 follow_redirects=True) as client:
        for work in WORKS:
            gids, title = work["gids"], work["title"]
            rec0 = await _gutendex(client, gids[0])
            authors = (rec0 or {}).get("authors") or []
            pg_author = authors[0]["name"] if authors else (work.get("author") or "")
            subjects = (rec0 or {}).get("subjects") or []
            cover = _cover_url((rec0 or {}).get("formats") or {})
            merged, wc = [], 0
            for gid in gids:
                meta = {"author": pg_author, "title": title, "genre": None,
                        "subjects": "|".join(subjects)}
                try:
                    vol = await asyncio.wait_for(gb.fetch_book(client, gid, meta), timeout=args.timeout)
                except Exception:  # noqa: BLE001
                    vol = None
                if not vol:
                    print(f"    ! volume pg{gid} failed to fetch")
                    continue
                for ch in vol["chapters"]:
                    merged.append({"section_number": len(merged) + 1, "title": ch["title"],
                                   "html": ch["html"], "words": ch["words"]})
                wc += vol["word_count"]
            if not merged:
                print(f"  SKIP {title}  (no chapters from any volume)"); fail += 1; continue
            display, sort = gb._display_name(pg_author)
            book = {
                "slug": (f"{gb._slugify(display)}_{gb._slugify(title)}"[:78] or "book") + f"-pg{gids[0]}",
                "title": title, "author": display, "author_sort": sort,
                "subjects": subjects, "chapters": merged, "word_count": wc,
            }
            print(f"  {title[:38]:38} {wc:>7,}w {len(merged):>3}ch  vols={len(gids)}  "
                  f"cover={'Y' if cover else 'n'}  {display[:24]}")
            if not args.dry_run:
                _store(con, book, cover, title)
            ok += 1
    print(f"\n{'(dry-run) ' if args.dry_run else ''}{ok} merged-works ingested, {fail} skipped")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--dry-run", action="store_true")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
