"""Call a few Study Bible tools in-process and check the answers (no MCP connection, so nothing can hang on a
session). Each call has a time limit and the process force-exits when done.

    .venv/Scripts/python.exe scripts/check_bible_tools.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from studybible_mcp import server  # noqa: E402

CASES = [
    ("lookup_verse", {"reference": "John 3:16"}, ["God"]),
    ("explore_person_events", {"person": "Mary Magdalene"}, ["Mary"]),
    ("graph_enriched_search", {"reference": "John 19:25"}, ["mary_1943"]),
    ("lookup_name", {"name": "Lazarus"}, ["Key References"]),
    ("get_confession", {"name": "Westminster Confession of Faith", "chapter": "1"}, ["Scripture"]),
]


async def main() -> int:
    failed = 0
    for name, args, want in CASES:
        try:
            out = (await asyncio.wait_for(server.call_tool(name, args), timeout=120))[0].text
        except asyncio.TimeoutError:
            out = "TIMEOUT"
        missing = [w for w in want if w not in out]
        bad = out.startswith(("Error", "Unknown tool", "TIMEOUT")) or missing
        failed += bool(bad)
        print(f"{'FAIL' if bad else 'ok  '} {name:24} {len(out):>6,} chars" + (f"  missing {missing}: {out[:300]!r}" if bad else ""), flush=True)
    print(f"{len(CASES) - failed} of {len(CASES)} passed", flush=True)
    if server.db and server.db.conn:
        await server.db.conn.close()
    return failed


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    code = asyncio.run(main())
    sys.stdout.flush()
    os._exit(1 if code else 0)
