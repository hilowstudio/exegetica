"""Re-parse the three merged horror works (seed_horror_multivol.py) with the fixed Gutenberg
parser, replacing ONLY their chapters — title, shelf, self-hosted cover, and classification
are kept. Their volumes were first parsed by the old splitter, which could drop a volume's
opening.

    .venv\\Scripts\\python.exe scripts\\reparse_horror_multivol.py
"""
from __future__ import annotations

import asyncio
import pathlib
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from reparse_suspects import _replace  # noqa: E402
from seed_horror_multivol import WORKS  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402


async def main() -> None:
    con = sqlite3.connect(_ROOT / "db" / "books.db", timeout=120)
    async with httpx.AsyncClient(headers={"User-Agent": BROWSER_UA}, follow_redirects=True,
                                 timeout=httpx.Timeout(connect=15.0, read=90.0, write=30.0, pool=15.0)) as client:
        for work in WORKS:
            row = con.execute("select id, author, word_count from books where slug like ?",
                              (f"%-pg{work['gids'][0]}",)).fetchone()
            if not row:
                print(f"  not in library: {work['title']}"); continue
            merged = []
            for gid in work["gids"]:
                vol = await gb.fetch_book(client, gid, {"author": row[1] or "", "title": work["title"]})
                if not vol:
                    print(f"  ! pg{gid} failed; leaving {work['title']} unchanged"); merged = []; break
                for ch in vol["chapters"]:
                    merged.append({**ch, "section_number": len(merged) + 1})
            if merged:
                _replace(con, row[0], merged)
                new = con.execute("select word_count from books where id=?", (row[0],)).fetchone()[0]
                print(f"  {work['title']}: {row[2]:,} -> {new:,} words, {len(merged)} chapters")
    con.close()


if __name__ == "__main__":
    asyncio.run(main())
