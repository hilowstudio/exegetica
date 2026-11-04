"""Call every Study Bible tool in-process with a known question and check the answer holds what it should,
then make one real stdio round trip (spawn the server as the web app does, list its tools, call one). Calls
go through the server's MCP request handler, so arguments are checked against each tool's schema and a
failure shows as isError, as a client sees it. Runs the same way here and on the server; each call has a
time limit, and the process force-exits when done so no database thread keeps it alive.

No network: ESV and NET are fetched live from outside services, so the cases read the bundled translations
(BSB, KJV, WEB), and the theology search's query embedder loads from the local model cache. The ESV and NET
cases run with the client's HTTP layer replaced by one that fails, as when the service is down.

    .venv/Scripts/python.exe scripts/check_bible_tools.py [--show]
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import sys
import tempfile
import threading
import time
import types as pytypes
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # as in production (fly.toml): no HuggingFace call
_up = Path(__file__).resolve().parents
ROOT = _up[1]
if (ROOT / "src").exists():  # the repo; on the server the package is installed
    sys.path.insert(0, str(ROOT / "src"))
from mcp import types  # noqa: E402
from studybible_mcp import clients, server  # noqa: E402

CASES = [  # (tool, arguments, text the answer must contain; a leading "!" marks text it must not contain)
    ("word_study", {"strongs": "G26"}, ["G0026", "agapē", "Example Passages"]),
    ("word_study", {"strongs": "H7965"}, ["H7965", "Hebrew", "peace", "Example Passages"]),
    ("word_study", {"word": "shalom"}, ["H7965", "shalom", "!Abishalom"]),
    ("word_study", {"word": "hesed"}, ["H2617"]),
    ("word_study", {"word": "agape"}, ["G0026"]),
    ("lookup_verse", {"reference": "John 3:16"}, ["God so loved the world"]),
    ("lookup_verse", {"reference": "Romans 8:28", "translation": "KJV", "reader_mode": True}, ["KJV", "Vocabulary"]),
    ("get_passage", {"reference": "Psalm 23", "translation": "KJV"}, ["shepherd"]),
    ("get_passage", {"reference": "Tobit 1:1-3"}, ["(WEB)"]),  # deuterocanon routes to WEB
    ("compare_translations", {"reference": "John 1:1", "translations": ["BSB", "KJV", "WEB"]}, ["**BSB:**", "**KJV:**", "**WEB:**"]),
    ("vocabulary_list", {"reference": "Romans 3:21-26"}, ["Reader Vocabulary"]),
    ("search_lexicon", {"query": "love", "language": "greek"}, ["Lexicon Search", "G0025", "G0026", "G5368"]),
    # the words glossed "love" come before words whose long definitions mention it
    ("search_lexicon", {"query": "atonement", "limit": 3}, ["H3725", "!H7676"]),
    ("get_cross_references", {"reference": "John 3:16"}, ["Cross-References for John 3:16"]),
    ("lookup_name", {"name": "Lazarus"}, ["Key References"]),
    ("parse_morphology", {"code": "V-AAI-3S"}, ["Aorist"]),
    ("search_by_strongs", {"strongs": "G26", "limit": 5}, ["Verses with G26", "Mat.24.12"]),
    # Hebrew words carry a sense letter in the tagged text (H3068G, H0430G, H1254A)
    ("search_by_strongs", {"strongs": "H3068", "limit": 3}, ["Gen.2.4", "!No verses found"]),
    ("search_by_strongs", {"strongs": "H430", "limit": 3}, ["Gen.1.1", "*God*", "!No verses found"]),
    # H0136 (Adonai) is missing from BDB; its entry comes from TBESH
    ("search_by_strongs", {"strongs": "H136", "limit": 3}, ["Lord", "!Unknown Strong's", "!No verses found"]),
    ("search_by_strongs", {"strongs": "H1254", "limit": 3}, ["Gen.1.1", "!No verses found"]),
    ("explore_genealogy", {"person": "David", "direction": "ancestors", "generations": 3}, ["Jesse"]),
    ("people_in_passage", {"reference": "Genesis 22"}, ["Abraham"]),
    ("explore_person_events", {"person": "Mary Magdalene"}, ["Mary"]),
    ("explore_place", {"place": "Bethlehem"}, ["Bethlehem"]),
    ("find_connection", {"person1": "Abraham", "person2": "David"}, ["David"]),
    ("graph_enriched_search", {"reference": "John 19:25"}, ["mary_1943"]),
    ("get_study_notes", {"reference": "John 3:16"}, ["Study Notes"]),
    ("get_bible_dictionary", {"topic": "covenant"}, ["ovenant"]),
    ("get_key_terms", {"term": "grace"}, ["race"]),
    ("get_commentary", {"reference": "Romans 3:23"}, ["Commentary on Romans 3:23"]),
    ("get_church_fathers", {"reference": "John 1:1"}, ["Church Fathers on John 1:1"]),
    ("search_theology", {"query": "justification by faith alone"}, ["Theology Library"]),
    ("get_confession", {}, ["Westminster"]),
    ("get_confession", {"document": "Westminster Shorter Catechism", "section": "1"}, ["glorify God"]),
    ("get_confession", {"topic": "justification"}, ["Creeds & Confessions"]),
    ("find_confessions_by_verse", {"reference": "Romans 1:20"}, ["Confessions citing"]),
    ("get_confession_proofs", {"document": "wcf", "section": "1.1"}, ["Proof Texts", "Psa 19:1"]),
    # with no section, an outline of the articles, never every verse of the document
    ("get_confession_proofs", {"document": "wlc"}, ["194 articles", "Q1", "!**Proof texts:**"]),
    ("get_confession_proofs", {"document": "wsc", "section": "1"}, ["Q1", "glory"]),
    # one ACAI record per entry: the pillar called Boaz gets none of Ruth's Boaz's roles
    ("lookup_name", {"name": "Boaz"}, ["Kinsman-Redeemer"]),
    ("get_devotional", {"date": "January 1"}, ["Devotional Reading"]),
    ("get_parallel_passages", {"reference": "Matthew 19:5"}, ["Gen 2:24"]),
    # The LXX counts psalm headings as verses: English 51:1 is LXX 50:3, past a two-verse heading
    ("get_septuagint", {"reference": "Psalm 51:1"}, ["LXX): Psa 50:3 (English Psa 51:1)", "Have mercy upon me"]),
    ("get_septuagint", {"reference": "Psalm 3:1"}, ["Psa 3:2 (English Psa 3:1)", "afflict me multiplied"]),
    ("get_septuagint", {"reference": "Psalm 10:1"}, ["Psa 9:22 (English Psa 10:1)"]),
    ("get_septuagint", {"reference": "Psalm 50:1", "numbering": "lxx"}, ["heading of Psa 51"]),
    # Brenton numbers Isaiah 9 as English Bibles do; the English is paired by content, not number
    ("get_septuagint", {"reference": "Isaiah 9:6"}, ["ὅτι παιδ", "a child is born"]),
    # a verse the Swete digitization has no Greek for keeps Brenton's English
    ("get_septuagint", {"reference": "Psalm 43:8", "numbering": "lxx"}, ["has no Greek", "thou hast saved us"]),
    # Daniel: the Old Greek and Theodotion, with Brenton's English of Theodotion
    ("get_septuagint", {"reference": "Daniel 1:1"}, ["Old Greek", "Theodotion", "third year of the reign of Joakim"]),
    # Swete's numbering differs from the map's; these routes were found by content
    ("get_septuagint", {"reference": "Malachi 4:4"}, ["LXX): Mal 4:6", "Remember the law"]),
    ("get_septuagint", {"reference": "Daniel 3:24"}, ["LXX): Dan 3:91", "Nabuchodonosor heard"]),
    # books Swete names differently: Nehemiah (2 Esdras 11-23), Esther (Greek Esther), Nahum
    ("get_septuagint", {"reference": "Nehemiah 1:1"}, ["Neemias", "!No Septuagint text"]),
    ("get_septuagint", {"reference": "Esther 2:1"}, ["Greek (Swete)", "!No Septuagint text"]),
    ("get_septuagint", {"reference": "Nahum 1:1"}, ["Nineve", "!No Septuagint text"]),
    ("get_septuagint", {"reference": "Song of Solomon 1:1"}, ["Song of songs", "!No Septuagint text"]),
    ("get_septuagint", {"reference": "Susanna 5"}, ["Sus 1:5", "Theodotion"]),
]

# ESV and NET with the service down: the BSB is served in their place with a note, and the raw error stays
# in the log. (tool, arguments, must contain, isError expected)
LIVE_DOWN = "getaddrinfo failed"
DOWN_CASES = [
    ("get_passage", {"reference": "John 3:16", "translation": "ESV"},
     ["(BSB)", "ESV could not be reached", "God so loved", "!" + LIVE_DOWN], False),
    ("lookup_verse", {"reference": "John 3:16", "translation": "NET"},
     ["**BSB:**", "NET could not be reached", "!" + LIVE_DOWN], False),
    ("compare_translations", {"reference": "John 3:16", "translations": ["ESV", "KJV"]},
     ["**KJV:**", "**BSB:**", "in place of the ESV", "!" + LIVE_DOWN], False),
    ("get_passage", {"reference": "Hezekiah 3:1", "translation": "ESV"},  # nothing to serve
     ["ESV could not be reached", "!" + LIVE_DOWN], True),
]


@contextlib.contextmanager
def live_translations_down():
    """The ESV and NET clients get an HTTP layer that fails before any request leaves, and a key, so the
    ESV path reaches the request."""
    class Down:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, **_):
            raise OSError(f"[Errno 11001] {LIVE_DOWN} for {url}")

    saved_httpx, saved_key = clients.httpx, os.environ.get("ESV_API_KEY")
    clients.httpx = pytypes.SimpleNamespace(AsyncClient=Down)
    os.environ["ESV_API_KEY"] = "check-key"
    try:
        yield
    finally:
        clients.httpx = saved_httpx
        if saved_key is None:
            os.environ.pop("ESV_API_KEY", None)
        else:
            os.environ["ESV_API_KEY"] = saved_key


async def call(name: str, args: dict) -> tuple[str, bool]:
    """One call through the server's MCP request handler: (text, isError)."""
    req = types.CallToolRequest(params=types.CallToolRequestParams(name=name, arguments=args))
    res = (await server.server.request_handlers[types.CallToolRequest](req)).root
    return "".join(c.text for c in res.content if c.type == "text"), bool(res.isError)


async def stdio_round_trip() -> str | None:
    """Spawn `python -m studybible_mcp.server --transport stdio`, list its tools, call one cheap tool and one
    that doesn't exist. None when all is well, else what went wrong (with the server's last log lines)."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "studybible_mcp.server", "--transport", "stdio"],
                                   env={**os.environ}, cwd=str(ROOT))
    with tempfile.TemporaryFile("w+", encoding="utf-8") as log:
        try:
            async with asyncio.timeout(60):
                async with stdio_client(params, errlog=log) as (read, write), ClientSession(read, write) as session:
                    await session.initialize()
                    listed = {t.name for t in (await session.list_tools()).tools}
                    ok = await session.call_tool("lookup_verse", {"reference": "John 3:16", "translation": "KJV"})
                    bad = await session.call_tool("no_such_tool", {})
        except Exception as e:  # noqa: BLE001
            log.seek(0)
            return f"{type(e).__name__}: {e}\n" + "".join(log.readlines()[-15:])
    problems = []
    if listed != set(server._TOOL_HANDLERS):
        problems.append(f"listed tools differ: {sorted(listed ^ set(server._TOOL_HANDLERS))}")
    if ok.isError or "God so loved the world" not in "".join(c.text for c in ok.content if c.type == "text"):
        problems.append(f"lookup_verse failed: {ok.content}")
    if not bad.isError:
        problems.append("an unknown tool did not come back as an error")
    return "; ".join(problems) or None


async def main(show: bool) -> int:
    untested = sorted(set(server._TOOL_HANDLERS) - {name for name, _, _ in CASES})
    unlisted = sorted({t.name for t in server.TOOLS} ^ set(server._TOOL_HANDLERS))
    for what, names in (("no case for", untested), ("listed but not handled (or handled but not listed)", unlisted)):
        if names:
            print(f"FAIL {what}: {', '.join(names)}", flush=True)
    async def check(name: str, args: dict, want: list[str], expect_error: bool = False) -> bool:
        t = time.time()
        try:
            out, is_error = await asyncio.wait_for(call(name, args), timeout=120)
        except asyncio.TimeoutError:
            out, is_error = "TIMEOUT", True
        missing = [w for w in want if not w.startswith("!") and w not in out]
        unwanted = [w[1:] for w in want if w.startswith("!") and w[1:] in out]
        bad = is_error != expect_error or not out.strip() or missing or unwanted
        print(f"{'FAIL' if bad else 'ok  '} {name:26} {str(args)[:58]:58} {len(out):>6,} chars {time.time() - t:5.1f}s"
              + (f"  missing {missing}" if missing else "") + (f"  contains {unwanted}" if unwanted else "")
              + ("  isError" if is_error else ""), flush=True)
        if show or bad:
            print("      " + out[:900].replace("\n", "\n      "), flush=True)
        return bool(bad)

    failed = 0
    for name, args, want in CASES:
        failed += await check(name, args, want)
    with live_translations_down():
        for name, args, want, expect_error in DOWN_CASES:
            failed += await check(name, args, want, expect_error)
    total = len(CASES) + len(DOWN_CASES)
    covered = len({name for name, _, _ in CASES} & set(server._TOOL_HANDLERS))
    print(f"\n{total - failed} of {total} passed, covering {covered} of {len(server._TOOL_HANDLERS)} tools",
          flush=True)
    failed += bool(untested or unlisted)
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
    print(f"{'FAIL' if problem else 'ok  '} stdio round trip (spawn, list tools, call lookup_verse and an unknown tool) "
          f"{time.time() - t:5.1f}s" + (f"\n      {problem}" if problem else ""), flush=True)
    return failed


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    code = asyncio.run(main("--show" in sys.argv))
    sys.stdout.flush()
    os._exit(1 if code else 0)
