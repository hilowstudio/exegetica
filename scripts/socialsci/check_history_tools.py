"""Call every history tool in-process with a known question and check the answer holds what it should,
then make one real stdio round trip (spawn the server as the web app does, list its tools, call one). Calls
go through the server's MCP request handler, so arguments are checked against each tool's schema and a
failure shows as isError, as a client sees it. Runs the same way here and on the server; each call has a
time limit, and the process force-exits when done so no database thread keeps it alive.

    .venv/Scripts/python.exe scripts/socialsci/check_history_tools.py [--show]
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # as in production (fly.toml): no HuggingFace call
_up = Path(__file__).resolve().parents
ROOT = _up[2]
if (ROOT / "src").exists():  # the repo; on the server the package is installed
    sys.path.insert(0, str(ROOT / "src"))
from mcp import types  # noqa: E402
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
    ("lookup_person", {"name": "Jane Austen"}, ["Died 1817-07-18 in Winchester", "Born 1775-12-16 in Steventon\n"]),
    # Julian dates as entered (the export moves them into the Gregorian calendar), and disputed dates shown
    ("lookup_person", {"name": "William Shakespeare"}, ["Died 1616-04-23"]),
    ("lookup_person", {"name": "Isaac Newton"}, ["Born 1642-12-25", "also given as 1643-01-04"]),
    ("lookup_person", {"name": "Plato"}, ["(c. 428 BC-c. 348 BC)", "also given as 429 BC, 427 BC"]),
    ("explore_life", {"person": "Johannes Kepler"}, ["1571-12-27: Born"]),
    ("explore_event", {"event": "Battle of Hastings"}, ["1066-10-14"]),
    ("succession", {"person": "Elizabeth I of England"}, ["1558-11-17"]),
    ("lookup_person", {"name": "Ettore Majorana"}, ["Ettore Majorana (born 1906) [Q367196]"]),  # died, date unknown
    ("lookup_person", {"name": "Vitus Bering"}, ["Vitus Bering (1681-1741)", "Died 1741-12-19"]),
    ("explore_event", {"event": "Treaty of Versailles"}, ["1919-06-28 to 1920-01-10"]),
    # names Wikidata keeps only as multilingual labels (the first build read English labels only and lost them)
    ("lookup_person", {"name": "Victor Hugo"}, ["Victor Hugo (1802-1885)"]),
    ("lookup_person", {"name": "Pablo Picasso"}, ["Pablo Picasso (1881-1973)"]),
    ("explore_historic_place", {"place": "Jacksonville, Florida"}, ["Jacksonville", "Florida"]),
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


async def call(name: str, args: dict) -> tuple[str, bool]:
    """One call through the server's MCP request handler: (text, isError)."""
    req = types.CallToolRequest(params=types.CallToolRequestParams(name=name, arguments=args))
    res = (await server.server.request_handlers[types.CallToolRequest](req)).root
    return "".join(c.text for c in res.content if c.type == "text"), bool(res.isError)


async def stdio_round_trip() -> str | None:
    """Spawn `python -m socialsci_mcp.server --transport stdio`, list its tools, call one cheap tool and one
    that doesn't exist. None when all is well, else what went wrong (with the server's last log lines)."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "socialsci_mcp.server", "--transport", "stdio"],
                                   env={**os.environ}, cwd=str(ROOT))
    with tempfile.TemporaryFile("w+", encoding="utf-8") as log:
        try:
            async with asyncio.timeout(60):
                async with stdio_client(params, errlog=log) as (read, write), ClientSession(read, write) as session:
                    await session.initialize()
                    listed = {t.name for t in (await session.list_tools()).tools}
                    ok = await session.call_tool("lookup_person", {"name": "John Adams"})
                    bad = await session.call_tool("no_such_tool", {})
        except Exception as e:  # noqa: BLE001
            log.seek(0)
            return f"{type(e).__name__}: {e}\n" + "".join(log.readlines()[-15:])
    problems = []
    if listed != set(server.HANDLERS):
        problems.append(f"listed tools differ: {sorted(listed ^ set(server.HANDLERS))}")
    if ok.isError or "John Adams" not in "".join(c.text for c in ok.content if c.type == "text"):
        problems.append(f"lookup_person failed: {ok.content}")
    if not bad.isError:
        problems.append("an unknown tool did not come back as an error")
    return "; ".join(problems) or None


async def main(show: bool) -> int:
    untested = sorted(set(server.HANDLERS) - {name for name, _, _ in CASES})
    if untested:
        print(f"FAIL no case for: {', '.join(untested)}", flush=True)
    failed = 0
    for name, args, want in CASES:
        t = time.time()
        try:
            out, is_error = await asyncio.wait_for(call(name, args), timeout=120)
        except asyncio.TimeoutError:
            out, is_error = "TIMEOUT", True
        missing = [w for w in want if w not in out]
        bad = is_error or not out.strip() or missing
        failed += bool(bad)
        print(f"{'FAIL' if bad else 'ok  '} {name:28} {str(args)[:60]:60} {len(out):>6,} chars {time.time() - t:5.1f}s"
              + (f"  missing {missing}" if missing else "") + ("  isError" if is_error else ""), flush=True)
        if show or bad:
            print("      " + out[:900].replace("\n", "\n      "), flush=True)
    print(f"\n{len(CASES) - failed} of {len(CASES)} passed, covering {len(server.HANDLERS) - len(untested)} of "
          f"{len(server.HANDLERS)} tools", flush=True)
    failed += bool(untested)
    if server.db and server.db.conn:
        await server.db.conn.close()

    # A hung child or pipe must not hang the check: force-exit if the round trip outlasts its limit.
    watchdog = threading.Timer(90, lambda: (print("FAIL stdio round trip hung past 90 s", flush=True), os._exit(1)))
    watchdog.daemon = True
    watchdog.start()
    t = time.time()
    problem = await stdio_round_trip()
    watchdog.cancel()
    failed += bool(problem)
    print(f"{'FAIL' if problem else 'ok  '} stdio round trip (spawn, list tools, call lookup_person and an unknown tool) "
          f"{time.time() - t:5.1f}s" + (f"\n      {problem}" if problem else ""), flush=True)
    return failed


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    code = asyncio.run(main("--show" in sys.argv))
    sys.stdout.flush()
    os._exit(1 if code else 0)
