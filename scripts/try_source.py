#!/usr/bin/env python3
"""Manual smoke-test of the Living Library source adapters (needs internet egress).

    .venv/Scripts/python.exe scripts/try_source.py "The Adventures of Tom Sawyer" "Mark Twain"

Discovers + fetches a public-domain full text (Gutenberg for now), strips boilerplate,
segments into chapters, and prints a summary. No AI, no DB writes — just the source layer.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webapp.sources import registry, text_processing as TP  # noqa: E402


async def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "The Adventures of Tom Sawyer"
    author = sys.argv[2] if len(sys.argv) > 2 else "Mark Twain"
    meta = {"title": title, "authors": [author] if author else []}

    print(f"query: {title!r} / {author!r}")
    hits = await registry.discover_all(meta)
    print(f"discover: {len(hits)} hit(s): {[h['source'] + ':' + h['source_id'] for h in hits]}")
    if not hits:
        print("no source has it (or network blocked)")
        return 1
    got = await registry.fetch_first_available(hits)
    if not got:
        print("discovered but no full text fetched")
        return 1
    text = got["text"]
    secs = TP.segment_into_chapters(text)
    print(f"fetched from {got['source']} ({got['source_id']}): {len(text):,} chars -> {len(secs)} sections")
    for s in secs[:8]:
        print(f"  #{s['section_number']:>3}  {s['title'][:50]:50}  {len(s['text']):>8,} chars")
    if len(secs) > 8:
        print(f"  ... and {len(secs) - 8} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
