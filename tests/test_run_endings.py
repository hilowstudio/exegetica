"""Every run ends in one named outcome, and the numbers for metrics survive a closed browser
(webapp/providers.py). A fake Anthropic client; no network, no cost."""
import asyncio
import sys
import types

from webapp import policy, providers
from tests.test_policy_and_loop import _MCP, _fake_anthropic


class _FailingMCP(_MCP):
    async def call(self, name, args):
        return "The library did not answer.", True


def _collect(mcp, script, limits=policy.CHAT, monkeypatch=None):
    calls, stats = [], {}
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic(script, calls))

    async def go():
        return [ev async for ev in providers.run("anthropic", None, "claude-opus-5-5", "s",
                                                  [{"role": "user", "content": "q"}], mcp, limits=limits, stats=stats)]
    return asyncio.run(go()), calls, stats


def test_two_failed_tool_steps_end_the_run(monkeypatch):
    events, calls, stats = _collect(_FailingMCP(), ["tool_use"], monkeypatch=monkeypatch)
    assert len(calls) == 2 and stats["outcome"] == "tools_failed" and stats["tool_errors"] == 2
    assert events[-2] == {"type": "notice", "incomplete": True, "message": policy.TOOLS_DOWN}
    assert events[-1] == {"type": "end", "outcome": "tools_failed"}


def test_one_failed_step_does_not_end_the_run(monkeypatch):
    class _FlakyMCP(_MCP):
        n = 0

        async def call(self, name, args):
            self.n += 1
            return ("down", True) if self.n == 1 else ("In the beginning was the Word.", False)
    _events, calls, stats = _collect(_FlakyMCP(), ["tool_use", "tool_use", "end_turn"], monkeypatch=monkeypatch)
    assert stats["outcome"] == "complete" and len(calls) == 3


def test_a_student_never_sees_the_raw_api_error(monkeypatch):
    monkeypatch.setattr(providers, "RETRY_WAIT", 0)
    mod = _fake_anthropic(["end_turn"], [])

    class APIStatusError(Exception):
        status_code = 529
        body = None

    def boom(**params):
        raise APIStatusError("overloaded: request body echoed here")
    mod.APIStatusError = APIStatusError
    client = mod.AsyncAnthropic()
    client.messages.stream = boom
    mod.AsyncAnthropic = lambda **kw: client
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    stats = {}

    async def go():
        return [ev async for ev in providers.run("anthropic", None, "claude-opus-5-5", "s",
                                                  [{"role": "user", "content": "q"}], _MCP(),
                                                  limits=policy.CHAT, stats=stats)]
    events = asyncio.run(go())
    assert events[0] == {"type": "error", "message": policy.PROVIDER_ERROR}
    assert "echoed" not in str(events) and stats["http_status"] == 529 and stats["outcome"] == "provider_error"


def test_a_closed_browser_still_counts_the_tokens_streamed(monkeypatch):
    """Usage is tallied from stream events, so a run cut off mid-step is still costed."""
    class _Stream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def __aiter__(self):
            return self._events()

        async def _events(self):
            usage = types.SimpleNamespace(input_tokens=5000, output_tokens=1,
                                          cache_read_input_tokens=0, cache_creation_input_tokens=0)
            yield types.SimpleNamespace(type="message_start", message=types.SimpleNamespace(usage=usage))
            yield types.SimpleNamespace(type="message_delta", usage=types.SimpleNamespace(output_tokens=900))
            yield types.SimpleNamespace(type="content_block_delta",
                                        delta=types.SimpleNamespace(type="text_delta", text="The Word"))
            await asyncio.sleep(10)   # the browser closes while the model is still writing

    mod = _fake_anthropic(["end_turn"], [])
    client = mod.AsyncAnthropic()
    client.messages.stream = lambda **p: _Stream()
    mod.AsyncAnthropic = lambda **kw: client
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    stats = {}

    async def go():
        gen = providers.run("anthropic", None, "claude-opus-5-5", "s", [{"role": "user", "content": "q"}],
                            _MCP(), limits=policy.CHAT, stats=stats)
        async for ev in gen:
            if ev["type"] == "text":
                break
        await gen.aclose()
    asyncio.run(go())
    assert stats["outcome"] == "cancelled"
    assert stats["input"] == 5000 and stats["output"] == 900 and stats["est_usd"] > 0


class _FailingStream:
    """Streams `text` (if any), then raises `err`."""
    def __init__(self, err, text=None):
        self.err, self.text = err, text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def __aiter__(self):
        return self._events()

    async def _events(self):
        usage = types.SimpleNamespace(input_tokens=2000, output_tokens=1,
                                      cache_read_input_tokens=0, cache_creation_input_tokens=0)
        yield types.SimpleNamespace(type="message_start", message=types.SimpleNamespace(usage=usage))
        if self.text:
            yield types.SimpleNamespace(type="content_block_delta",
                                        delta=types.SimpleNamespace(type="text_delta", text=self.text))
        raise self.err


def _with_failures(monkeypatch, failures, status=200, kind="overloaded_error"):
    """A client whose first streams fail as `failures` describes (None: fail before any text;
    a string: fail after streaming that text), then answer normally. The default error is the
    one the SDK raises for an error event sent mid-stream: the stream's 200 status, typed by its body."""
    monkeypatch.setattr(providers, "RETRY_WAIT", 0)
    mod = _fake_anthropic(["end_turn"], [])
    client = mod.AsyncAnthropic()
    normal = client.messages.stream
    attempts = []

    def stream(**params):
        attempts.append(params)
        if len(attempts) <= len(failures):
            err = mod.APIStatusError(kind)
            err.status_code, err.body = status, {"type": "error", "error": {"type": kind, "message": kind}}
            return _FailingStream(err, failures[len(attempts) - 1])
        return normal(**params)
    client.messages.stream = stream
    mod.AsyncAnthropic = lambda **kw: client
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    stats = {}

    async def go():
        return [ev async for ev in providers.run("anthropic", None, "claude-opus-5-5", "s",
                                                  [{"role": "user", "content": "q"}], _MCP(),
                                                  limits=policy.CHAT, stats=stats)]
    return asyncio.run(go()), attempts, stats


def test_a_step_that_fails_before_any_text_is_retried_once(monkeypatch):
    events, attempts, stats = _with_failures(monkeypatch, [None])
    assert len(attempts) == 2 and stats["outcome"] == "complete"
    assert not any(e["type"] == "error" for e in events)
    assert stats["input"] >= 2000   # the failed attempt's tokens are still counted


def test_only_one_retry_per_run(monkeypatch):
    events, attempts, stats = _with_failures(monkeypatch, [None, None])
    assert len(attempts) == 2 and stats["outcome"] == "provider_error"
    assert {"type": "error", "message": policy.PROVIDER_ERROR} in events


def test_text_already_shown_is_kept_and_not_retried(monkeypatch):
    events, attempts, stats = _with_failures(monkeypatch, ["In the beginning"])
    assert len(attempts) == 1 and stats["outcome"] == "provider_error"
    assert events[0] == {"type": "text", "text": "In the beginning"}
    assert events[-2] == {"type": "error", "message": policy.PROVIDER_ERROR}


def test_a_bad_request_is_not_retried(monkeypatch):
    _events, attempts, stats = _with_failures(monkeypatch, [None], status=400, kind="invalid_request_error")
    assert len(attempts) == 1 and stats["outcome"] == "provider_error"


def test_byok_paths_report_an_outcome(monkeypatch):
    async def fake_attempt(*a, **k):
        yield {"type": "text", "text": "answer"}
    monkeypatch.setattr(providers, "_attempt", lambda *a, **k: fake_attempt())
    stats = {}

    async def go():
        return [ev async for ev in providers.run("openai", "sk-test", "gpt-5.6", "s",
                                                  [{"role": "user", "content": "q"}], _MCP(), stats=stats)]
    events = asyncio.run(go())
    assert events[-1] == {"type": "end", "outcome": "complete"} and stats["outcome"] == "complete"
