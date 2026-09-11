#!/usr/bin/env python3
"""End-to-end Living Library extraction for a public-domain book (non-durable run).

Needs: internet egress, ANTHROPIC_API_KEY, DATABASE_URL (all from .env).

    .venv/Scripts/python.exe scripts/extract_book.py "The Story of an Hour" "Kate Chopin"

Runs the SAME steps the Inngest function runs (fetch → derive → objectives batches →
finalize), just in sequence with no durability. Persists to Neon; prints a summary.
Start with a SHORT work — a full novel makes many Claude calls.
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from webapp import db, extraction  # noqa: E402


async def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "The Story of an Hour"
    author = sys.argv[2] if len(sys.argv) > 2 else "Kate Chopin"
    meta = {"title": title, "authors": [author] if author else []}

    await db.init_pool()
    if not db.ready():
        print("DATABASE_URL not set — cannot persist.")
        return 1
    try:
        exid = await extraction.ensure_extraction_row(meta)
        print(f"extraction row: {exid}\nrunning steps (fetch → derive → objectives → finalize)…")
        res = await extraction.run_all(exid, meta)
        print("\nRESULT:")
        for k in ("status", "us_clear", "sections", "objectives", "alignments", "extraction_id"):
            print(f"  {k}: {res.get(k)}")
        return 0
    finally:
        await db.close_pool()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
