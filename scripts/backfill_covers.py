"""Backfill cover art for seeded catalog books.

For every extracted book missing a cover, resolve one from Google Books (falling back to
Open Library) and write it to library_extractions.cover_url. Idempotent: only fills blanks
unless --all is passed. Runnable plain (no PYTHONPATH needed).

    .venv\\Scripts\\python.exe scripts\\backfill_covers.py [--dry-run] [--all] [--limit N]
                                                            [--concurrency N] [--delay S]
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

# self-resolve project root + UTF-8 stdout so `import webapp` works when run directly
_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

import os  # noqa: E402

import asyncpg  # noqa: E402
import httpx  # noqa: E402

from webapp import library  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="resolve + report, write nothing")
    ap.add_argument("--all", action="store_true", help="re-resolve even books that already have a cover")
    ap.add_argument("--limit", type=int, default=0, help="cap how many books to process (0 = all)")
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--delay", type=float, default=0.15, help="pause between resolves per worker (be polite)")
    args = ap.parse_args()

    con = await asyncpg.connect(os.environ["DATABASE_URL"])
    where = "status='extracted' and kind='book'"
    if not args.all:
        where += " and (cover_url is null or cover_url='')"
    sql = f"select id, title, creator from library_extractions where {where} order by title"
    if args.limit:
        sql += f" limit {args.limit}"
    books = await con.fetch(sql)
    print(f"books to resolve: {len(books)}" + ("  (dry run)" if args.dry_run else ""))
    if not books:
        await con.close()
        return

    sem = asyncio.Semaphore(args.concurrency)
    stats = {"found": 0, "none": 0}

    # Resolve covers concurrently over HTTP (the slow part); a single asyncpg connection is
    # NOT concurrency-safe, so collect results and write them sequentially afterwards.
    async with httpx.AsyncClient(timeout=15.0) as client:
        async def one(row):
            async with sem:
                url = await library.resolve_cover(client, row["title"] or "", row["creator"] or "")
                await asyncio.sleep(args.delay)
                print(f"  {'OK ' if url else '-- '} {(row['title'] or '')[:48]:48} {'' if url else 'no cover'}")
                return row["id"], url

        results = await asyncio.gather(*(one(r) for r in books))

    updates = [(rid, url) for rid, url in results if url]
    stats["found"] = len(updates)
    stats["none"] = len(results) - len(updates)
    if updates and not args.dry_run:
        await con.executemany(
            "update library_extractions set cover_url=$2 where id=$1", updates)

    await con.close()
    print(f"\ndone: covers found {stats['found']} | no cover {stats['none']}"
          + ("  (nothing written — dry run)" if args.dry_run else ""))


if __name__ == "__main__":
    asyncio.run(main())
