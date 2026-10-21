"""Call every history tool in-process with a known question and check the answer holds what it should.
Runs the same way here and on the server (no MCP connection, so nothing can hang on a session); each call
has a time limit, and the process force-exits when done so no database thread keeps it alive.

    .venv/Scripts/python.exe scripts/socialsci/check_history_tools.py [--show]
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

_up = Path(__file__).resolve().parents
if len(_up) > 2 and (_up[2] / "src").exists():  # the repo; on the server the package is installed
    sys.path.insert(0, str(_up[2] / "src"))
from socialsci_mcp import server  # noqa: E402

CASES = [  # (tool, arguments, text the answer must contain)
    ("search_history", {"query": "Gettysburg Address"}, ["Gettysburg"]),
    ("find_documents", {"title": "Emancipation Proclamation"}, ["Emancipation"]),
    ("get_document", {"id": 5359}, ["Declaration"]),
    ("get_constitution", {"constitution": "us", "amendment": "19"}, ["sex"]),
    ("get_constitution", {"constitution": "illinois", "article": "schedule"}, ["Transition"]),
    ("get_flag_code", {}, ["flag"]),
    ("constitution_test_guide", {}, ["Constitution"]),
    ("search_history", {"query": "prohibition of intoxicating liquors", "year_from": 1900, "year_to": 1930}, ["18th Amendment"]),
    ("search_cases", {"query": "school search backpack"}, ["Safford"]),
    ("search_cases", {"query": "school officials search student purse Fourth Amendment"}, ["T. L. O."]),
    ("get_case", {"case": "Marbury v. Madison"}, ["Marbury"]),
    ("get_statute", {"citation": "720 ILCS 5/12C-60"}, ["Curfew"]),
    ("get_constitution_annotation", {"essay_id": "ArtIII.S3.C2.1"}, ["Treason"]),
    ("lookup_legislator", {"name": "Abraham Lincoln"}, ["Lincoln"]),
    ("define_term", {"term": "habeas corpus"}, ["Habeas"]),
    ("lookup_person", {"name": "John Adams"}, ["President of the United States", "John Adams"]),
    ("lookup_person", {"name": "Alexander Graham Bell"}, ["telephone"]),
    ("explore_family", {"person": "John Adams", "generations": 2}, ["John Quincy Adams"]),
    ("explore_life", {"person": "Abraham Lincoln"}, ["Born", "President of the United States"]),
    ("explore_event", {"event": "Battle of Gettysburg"}, ["1863"]),
    ("explore_event", {"event": "Great Chicago Fire"}, ["1871"]),
    ("explore_event", {"event": "1936 Summer Olympics"}, ["1936"]),
    ("explore_event", {"event": "Council of Trent"}, ["get_confession"]),
    ("explore_event", {"event": "Lewis and Clark Expedition"}, ["1804"]),
    ("explore_event", {"event": "Gettysburg Address"}, ["Lincoln"]),
    ("explore_event", {"event": "Kansas–Nebraska Act"}, ["Kansas"]),
    ("explore_event", {"event": "Reconstruction era"}, ["Reconstruction"]),
    ("explore_historic_place", {"place": "Chicago"}, ["Great Chicago Fire"]),
    ("find_historical_connection", {"from": "John Adams", "to": "John Quincy Adams"}, ["child was John Quincy Adams"]),
    ("find_historical_connection", {"from": "Thomas Jefferson", "to": "John Adams"}, ["succeeded John Adams"]),
    ("timeline", {"year_from": 1776}, ["Declaration", "Age of Enlightenment (17th century"]),
    ("timeline", {"year_from": 1861, "year_to": 1865, "country": "United States", "kind": "battle"}, ["Battle"]),
    ("succession", {"office": "President of the United States"}, ["George Washington"]),
    ("succession", {"person": "John Marshall"}, ["Chief Justice"]),
    ("people_in_document", {"document_id": 5359}, ["Thomas Jefferson"]),
    ("people_in_document", {"case": "Marbury v. Madison"}, ["John Marshall"]),
]


async def main(show: bool) -> int:
    failed = 0
    for name, args, want in CASES:
        t = time.time()
        try:
            out = (await asyncio.wait_for(server.call_tool(name, args), timeout=120))[0].text
        except asyncio.TimeoutError:
            out = "TIMEOUT"
        missing = [w for w in want if w not in out]
        bad = out.startswith(("Error in", "Unknown tool", "TIMEOUT")) or missing
        failed += bool(bad)
        print(f"{'FAIL' if bad else 'ok  '} {name:28} {str(args)[:60]:60} {len(out):>6,} chars {time.time() - t:5.1f}s"
              + (f"  missing {missing}" if missing else ""), flush=True)
        if show or bad:
            print("      " + out[:900].replace("\n", "\n      "), flush=True)
    print(f"\n{len(CASES) - failed} of {len(CASES)} passed", flush=True)
    if server.db and server.db.conn:
        await server.db.conn.close()
    return failed


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    code = asyncio.run(main("--show" in sys.argv))
    sys.stdout.flush()
    os._exit(1 if code else 0)
