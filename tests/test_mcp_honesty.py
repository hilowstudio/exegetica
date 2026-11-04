"""Server honesty (docs/harness-maturity-proposal.md, Layer 2): a tool that raises, overruns its
deadline, or lacks its data comes back with isError true and a plain sentence, through the same MCP
request handler a client talks to; "no results" stays an ordinary answer; two first calls open the
database once. Both servers. No network, no database files."""
import asyncio
import time

import pytest
from mcp import types

from socialsci_mcp import server as history
from studybible_mcp import server as bible

# (server module, a real tool name, arguments its schema accepts)
SERVERS = [
    pytest.param(bible, "lookup_verse", {"reference": "John 3:16"}, id="bible"),
    pytest.param(history, "lookup_person", {"name": "John Adams"}, id="history"),
]
LEAKS = ("Traceback", "SELECT", "sqlite", "secret_table", "C:\\", "/app/", ".db", "scripts/")


class _FakeConn:
    def __init__(self):
        self.interrupted = 0
        self.cursors = 0

    async def interrupt(self):
        self.interrupted += 1

    async def cursor(self):
        self.cursors += 1

    async def close(self):
        pass


class _FakeDB:
    def __init__(self, *_):
        self.conn = _FakeConn()


@pytest.fixture(autouse=True)
def _open_fake_db(monkeypatch, tmp_path):
    """Both servers see an already-open database, so no call touches db/."""
    missing = tmp_path / "missing.db"
    monkeypatch.setattr(bible, "db", _FakeDB())
    monkeypatch.setattr(history, "db", _FakeDB())
    monkeypatch.setattr(history, "get_db_path", lambda: missing)
    monkeypatch.setattr(history, "db_stamp", None)  # matches the missing file's stamp, so no reopen
    monkeypatch.setattr(bible, "_db_lock", asyncio.Lock())
    monkeypatch.setattr(history, "_db_lock", asyncio.Lock())


def _handlers(mod):
    return mod._TOOL_HANDLERS if mod is bible else mod.HANDLERS


async def _call(mod, name, args) -> types.CallToolResult:
    req = types.CallToolRequest(params=types.CallToolRequestParams(name=name, arguments=args))
    return (await mod.server.request_handlers[types.CallToolRequest](req)).root


def _text(res: types.CallToolResult) -> str:
    return "".join(c.text for c in res.content if c.type == "text")


@pytest.mark.parametrize("mod,tool,args", SERVERS)
async def test_a_raising_tool_is_an_error_with_a_plain_message(monkeypatch, mod, tool, args):
    async def boom(_args):
        raise RuntimeError("no such table: secret_table in SELECT * FROM secret_table at C:\\data\\x.db")

    monkeypatch.setitem(_handlers(mod), tool, boom)
    res = await _call(mod, tool, args)
    assert res.isError is True
    msg = _text(res)
    assert f"The {tool} tool failed" in msg
    assert not any(leak in msg for leak in LEAKS), msg


@pytest.mark.parametrize("mod,tool,args", SERVERS)
async def test_a_deadline_overrun_is_an_error_and_stops_the_query(monkeypatch, mod, tool, args):
    async def hang(_args):
        await asyncio.sleep(30)

    monkeypatch.setitem(_handlers(mod), tool, hang)
    monkeypatch.setattr(mod, "TOOL_DEADLINE", 0.2)
    t0 = time.perf_counter()
    res = await _call(mod, tool, args)
    assert time.perf_counter() - t0 < 2
    assert res.isError is True
    assert "took too long" in _text(res)
    assert mod.db.conn.interrupted == 1  # the shared connection's running query is stopped
    assert mod.db.conn.cursors == 1      # and any cursor it left open is dropped


@pytest.mark.parametrize("mod,tool,args", SERVERS)
async def test_no_results_stays_an_ordinary_answer(monkeypatch, mod, tool, args):
    async def nothing(_args):
        return mod.text("No entries found.")

    monkeypatch.setitem(_handlers(mod), tool, nothing)
    res = await _call(mod, tool, args)
    assert res.isError is False
    assert _text(res) == "No entries found."


@pytest.mark.parametrize("mod,tool,args", SERVERS)
async def test_an_unknown_tool_is_an_error(mod, tool, args):
    res = await _call(mod, "no_such_tool", {})
    assert res.isError is True


async def test_missing_bible_data_is_an_error_without_build_hints(monkeypatch):
    class NoGraph(_FakeDB):
        async def graph_has_data(self):
            return False

    monkeypatch.setattr(bible, "db", NoGraph())
    res = await _call(bible, "explore_place", {"place": "Bethel"})
    assert res.isError is True
    assert _text(res) == "The people-and-places graph is not installed on this server."


async def test_missing_history_database_is_an_error_without_its_path(monkeypatch):
    monkeypatch.setattr(history, "db", None)
    res = await _call(history, "lookup_person", {"name": "John Adams"})
    assert res.isError is True
    assert _text(res) == "The social sciences database is not installed on this server."


@pytest.mark.parametrize("mod", [bible, history], ids=["bible", "history"])
async def test_two_first_calls_open_the_database_once(monkeypatch, tmp_path, mod):
    opened = []

    class SlowDB(_FakeDB):
        async def connect(self):
            opened.append(self)
            await asyncio.sleep(0.05)  # a second call arrives mid-open

    path = tmp_path / "x.db"
    path.write_bytes(b"")
    monkeypatch.setattr(mod, "db", None)
    monkeypatch.setattr(mod, "get_db_path", lambda: path)
    monkeypatch.setattr(mod, "StudyBibleDB" if mod is bible else "SocialSciencesDB", SlowDB)
    await asyncio.gather(*(mod._open_db() for _ in range(5)))
    assert len(opened) == 1 and mod.db is opened[0]
