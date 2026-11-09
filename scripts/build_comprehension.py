"""Build the whole-work comprehension (webapp/comprehension.py) for large books from this machine, ahead of the
first teacher who drafts from them, instead of waiting on the Inngest build that first request would start.
Same steps as `build-comprehension` (plan, map each span, reduce), same cache (library_comprehension in Neon,
read by production), so a book built here is never built again there.

    python scripts/build_comprehension.py --list                     # the school and reference books that need it
    python scripts/build_comprehension.py --slug tb-trigonometry     # one book
    python scripts/build_comprehension.py --all                      # every one listed

Reads db/books.db (it must match the published copy: the cache is keyed to the word count) and DATABASE_URL and
ANTHROPIC_API_KEY from .env. Costs real money (Sonnet 5 at $2 / $10 per million tokens: about $0.70 a 200,000-word
book); prints each call's tokens and a running total, and stops a book whose reply was cut off."""
from __future__ import annotations

import argparse
import asyncio
import math
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from webapp import comprehension, db, extraction, generator  # noqa: E402

PRICE_IN, PRICE_OUT = 2.00, 10.00          # Sonnet 5, dollars per million tokens
spent = {"in": 0, "out": 0, "calls": 0, "cut": 0}


async def _counted_call(params: dict):
    """extraction._call with the usage recorded (same request, same JSON parsing)."""
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()
    try:
        msg = await client.messages.create(**params)
    finally:
        await client.close()
    spent["in"] += msg.usage.input_tokens
    spent["out"] += msg.usage.output_tokens
    spent["calls"] += 1
    if msg.stop_reason == "max_tokens":
        spent["cut"] += 1
        print(f"    a reply was cut off at max_tokens ({msg.usage.output_tokens} tokens)", flush=True)
    text = extraction._text_of(msg)
    out = extraction._parse_json(text)
    if not out:
        print(f"    unreadable reply: stop_reason={msg.stop_reason}, {msg.usage.output_tokens} tokens, "
              f"text starts {text[:160]!r}", flush=True)
    return out


def _cost() -> float:
    return spent["in"] * PRICE_IN / 1e6 + spent["out"] * PRICE_OUT / 1e6


def candidates() -> list[tuple[str, str, int]]:
    con = sqlite3.connect(ROOT / "db" / "books.db")
    try:
        return con.execute(
            "select slug, title, word_count from books where access in ('school', 'reference') and word_count > ? "
            "and word_count <= ? order by word_count desc",
            (generator._GEN_WORD_BUDGET, comprehension._MAX_WORDS)).fetchall()
    finally:
        con.close()


async def build(slug: str) -> bool:
    plan = await comprehension.step_plan(slug)
    if plan.get("status") != "build":
        print(f"{slug}: {plan.get('status')} (nothing to do)", flush=True)
        return True
    spans, title, total = plan["spans"], plan["title"], plan["total"]
    print(f"{slug}: {total:,} words in {len(spans)} spans", flush=True)
    cut_before = spent["cut"]
    sem = asyncio.Semaphore(comprehension.MAP_CONCURRENCY)

    async def one(i, span):
        async with sem:
            note = await comprehension.step_map(slug, span, i, len(spans))
            if not note.get("summary"):                    # one retry, as the Inngest step would
                print(f"    span {i + 1} came back empty; trying it once more", flush=True)
                note = await comprehension.step_map(slug, span, i, len(spans))
            return note

    notes = await asyncio.gather(*(one(i, s) for i, s in enumerate(spans)))
    empty = [i for i, n in enumerate(notes) if not n.get("summary")]
    if empty or spent["cut"] > cut_before:
        print(f"{slug}: stopped before the synthesis: {len(empty)} span(s) came back empty, "
              f"{spent['cut'] - cut_before} reply(ies) cut off. Nothing stored.", flush=True)
        return False
    result = await comprehension.step_reduce(slug, title, total, notes)
    print(f"{slug}: {result['status']}; running total ${_cost():.2f} ({spent['calls']} calls)", flush=True)
    return True


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--slug", action="append")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    books = candidates()
    if a.list or not (a.slug or a.all):
        for s, t, w in books:
            print(f"{w:>9,}  {s}  ({t})")
        return
    await db.init_pool()
    if not db.ready():
        sys.exit("DATABASE_URL is not set or Neon is unreachable: the result would have nowhere to go.")
    extraction._call = _counted_call
    slugs = a.slug or [s for s, _, _ in books]
    t0 = time.time()
    try:
        for s in slugs:
            if not await build(s):
                break
    finally:
        await db.close_pool()
    print(f"done: {spent['calls']} calls, {spent['in']:,} in / {spent['out']:,} out tokens, ${_cost():.2f}, "
          f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
