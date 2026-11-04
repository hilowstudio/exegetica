"""ESV and NET failures (docs/harness-maturity-proposal.md, Layer 2, step 5): the raw error goes to the
log only, the model gets a plain sentence, and the bundled BSB is served in place of the live text with
a note naming the substitution. When nothing can be served the call is an error. A successful live quote
keeps its copyright line. Through the same MCP request handler a client talks to. No network, no
database files."""
import asyncio
import logging
import types as pytypes

import pytest
from mcp import types

from studybible_mcp import clients
from studybible_mcp import server as bible

RAW = "getaddrinfo failed for api.esv.org"
LEAKS = (RAW, "Errno", "ESV_API_KEY", "BIBLE_API_KEY", "HTTP 503", "https://")


def _http(*, raises: Exception | None = None, status: int = 200, payload=None):
    """A stand-in for httpx inside clients.py: every GET raises, or answers with status and JSON."""
    class Response:
        status_code = status

        def json(self):
            return payload

    class Client:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, *_, **__):
            if raises:
                raise raises
            return Response()

    return pytypes.SimpleNamespace(AsyncClient=Client)


class _FakeDB:
    """The bundled translations: BSB has John 3:16 and nothing else."""

    def __init__(self):
        self.conn = None

    @staticmethod
    def _normalize_reference(reference):
        return {"John 3:16": "Jhn.3.16"}.get(reference, reference)

    async def has_translations(self):
        return True

    async def available_translations(self):
        return ["BSB", "KJV"]

    async def get_verse(self, _reference):
        return None

    async def get_translation_verse(self, translation, reference):
        if (translation, reference) == ("BSB", "Jhn.3.16"):
            return {"text": "For God so loved the world"}
        return None

    async def get_translation_passage(self, translation, book, chapter, v1, v2):
        if (translation, book, chapter) == ("BSB", "Jhn", 3) and v1 <= 16 <= v2:
            return [{"verse": 16, "text": "For God so loved the world"}]
        return []


@pytest.fixture(autouse=True)
def _fake_db(monkeypatch):
    monkeypatch.setattr(bible, "db", _FakeDB())
    monkeypatch.setattr(bible, "_db_lock", asyncio.Lock())
    monkeypatch.setenv("ESV_API_KEY", "test-key")


async def _call(name, args) -> types.CallToolResult:
    req = types.CallToolRequest(params=types.CallToolRequestParams(name=name, arguments=args))
    return (await bible.server.request_handlers[types.CallToolRequest](req)).root


def _text(res: types.CallToolResult) -> str:
    return "".join(c.text for c in res.content if c.type == "text")


@pytest.mark.parametrize("translation", ["ESV", "NET"])
async def test_a_network_failure_raises_a_plain_message_and_logs_the_cause(monkeypatch, caplog, translation):
    monkeypatch.setattr(clients, "httpx", _http(raises=OSError(RAW)))
    with caplog.at_level(logging.WARNING, logger="study-bible-mcp"):
        with pytest.raises(clients.Unavailable) as e:
            await clients.fetch_optional(translation, "John 3:16")
    assert str(e.value) == f"The {translation} could not be reached just now."
    assert RAW in caplog.text


@pytest.mark.parametrize("setup,cause,message", [
    (lambda mp: mp.setattr(clients, "httpx", _http(status=503)), "HTTP 503",
     "The ESV could not be reached just now."),
    (lambda mp: (mp.delenv("ESV_API_KEY"), mp.delenv("BIBLE_API_KEY", raising=False)), "ESV_API_KEY",
     "The ESV is not set up on this server."),
], ids=["http-error", "no-key"])
async def test_an_esv_error_status_or_missing_key_is_unavailable(monkeypatch, caplog, setup, cause, message):
    setup(monkeypatch)
    with caplog.at_level(logging.WARNING, logger="study-bible-mcp"):
        with pytest.raises(clients.Unavailable) as e:
            await clients.fetch_optional("ESV", "John 3:16")
    assert str(e.value) == message
    assert cause in caplog.text


@pytest.mark.parametrize("tool,args,label", [
    ("get_passage", {"reference": "John 3:16", "translation": "ESV"}, "(BSB)"),
    ("lookup_verse", {"reference": "John 3:16", "translation": "NET"}, "**BSB:**"),
    ("compare_translations", {"reference": "John 3:16", "translations": ["ESV", "KJV"]}, "**BSB:**"),
])
async def test_a_live_failure_serves_the_bsb_with_a_note_and_no_raw_error(monkeypatch, tool, args, label):
    monkeypatch.setattr(clients, "httpx", _http(raises=OSError(RAW)))
    res = await _call(tool, args)
    msg = _text(res)
    assert res.isError is False
    assert label in msg and "For God so loved the world" in msg
    assert "could not be reached" in msg and "BSB" in msg
    assert not any(leak in msg for leak in LEAKS), msg


async def test_a_live_failure_with_nothing_to_serve_is_an_error(monkeypatch):
    monkeypatch.setattr(clients, "httpx", _http(raises=OSError(RAW)))
    res = await _call("get_passage", {"reference": "Hezekiah 3:1", "translation": "ESV"})
    assert res.isError is True
    assert _text(res) == "The ESV could not be reached just now. The BSB has no text for Hezekiah 3:1 either."


async def test_a_successful_live_quote_keeps_its_copyright_line(monkeypatch):
    monkeypatch.setattr(clients, "httpx", _http(payload={"passages": ["For God so loved the world, ESV"]}))
    res = await _call("get_passage", {"reference": "John 3:16", "translation": "ESV"})
    msg = _text(res)
    assert res.isError is False
    assert "## John 3:16 (ESV)" in msg and "For God so loved the world, ESV" in msg
    assert clients.ATTRIBUTION["ESV"] in msg
    assert "could not be reached" not in msg
