#!/usr/bin/env python3
"""
Restore chapter text for Gutenberg books whose rows survived but whose chapters didn't.

Found 2026-10-04: the 20 books of the 2026-09-21 horror batch had their `books` rows (title,
author, section, LoC classification, self-hosted cover) but no `book_chapters` rows, locally and
in production. This re-fetches each from Project Gutenberg with the same chapter logic that
first imported it (seed_horror.py's forced splits; seed_horror_multivol.py's volume merges) and
inserts ONLY the chapters, so every other column of the existing row is kept.

    .venv\\Scripts\\python.exe scripts\\restore_empty_books.py --dry-run
    .venv\\Scripts\\python.exe scripts\\restore_empty_books.py
"""
from __future__ import annotations

import argparse
import asyncio
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

import seed_horror as sh  # noqa: E402
import seed_horror_multivol as shm  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402

DB = ROOT / "db" / "books.db"
VOLUMES = {w["gids"][0]: w["gids"] for w in shm.WORKS}     # first volume id -> all volume ids


async def fetch_chapters(client, gid: int, meta: dict) -> list[dict]:
    chapters = []
    for vid in VOLUMES.get(gid, [gid]):
        if vid in sh._FORCE_SPLIT:
            book = await sh._fetch_forced(client, vid, meta, sh._FORCE_SPLIT[vid])
        else:
            book = await gb.fetch_book(client, vid, meta)
        if not book:
            raise RuntimeError(f"pg{vid} returned no chapters")
        chapters += book["chapters"]
    return [{**c, "section_number": n} for n, c in enumerate(chapters, 1)]


async def main_async(dry: bool) -> None:
    con = sqlite3.connect(DB, timeout=120)
    empty = con.execute("""select id, slug, title, author, chapter_count from books b
                           where not exists (select 1 from book_chapters c where c.book_id = b.id)""").fetchall()
    print(f"{len(empty)} books without chapters")
    timeout = httpx.Timeout(connect=15.0, read=90.0, write=30.0, pool=15.0)
    ok = 0
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as client:
        for bid, slug, title, author, claimed in empty:
            m = re.search(r"-pg(\d+)$", slug)
            if not m:
                print(f"  SKIP {title}: not a Gutenberg slug"); continue
            try:
                chs = await asyncio.wait_for(fetch_chapters(client, int(m.group(1)), {"title": title, "author": author}), 300)
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {title}: {e}"); continue
            words = sum(c["words"] for c in chs)
            flag = "" if len(chs) == claimed else f"  (row said {claimed})"
            print(f"  {title[:44]:44} {len(chs):>4} ch {words:>8,} w{flag}")
            if dry:
                continue
            con.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                            [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in chs])
            con.execute("update books set chapter_count=?, word_count=? where id=?", (len(chs), words, bid))
            con.commit()
            ok += 1
    print(f"\n{'(dry run) ' if dry else ''}restored {ok} of {len(empty)}")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Restore chapters for books that lost them")
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(main_async(ap.parse_args().dry_run))


if __name__ == "__main__":
    main()
