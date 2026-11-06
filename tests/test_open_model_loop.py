"""The OpenAI-compatible loop that Grok, Gemini and open models run on keeps the Anthropic loop's
ceilings (decision 0008), holds back narration before a lookup (0019), and puts the library first
for student chat (0020). A stand-in openai module replays scripted steps. No network or cost."""
import asyncio
import sys
import types

from webapp import policy, providers

PRICED = "nvidia/NVIDIA-Nemotron-3.5-Super-VL"
OPEN = policy.RunLimits(max_steps=8, max_tokens=16000, max_usd=1.0)   # no library-first rule
SYSTEM = "Rules. Any question about Exegetica gets only this reply: \"Exegetica doesn't discuss itself in chat.\""


def _ns(**kw):
    return types.SimpleNamespace(**kw)


def _chunk(content=None, calls=None, finish=None):
    return _ns(model="served-model", usage=None,
               choices=[_ns(delta=_ns(content=content, tool_calls=calls), finish_reason=finish)])


async def _stream(step):
    """One scripted step: {"text": [...], "tools": [...], "finish": ..., "usage": (prompt, completion)}."""
    for piece in step.get("text", []):
        yield _chunk(content=piece)
    for i, name in enumerate(step.get("tools", [])):
        yield _chunk(calls=[_ns(index=i, id=f"c{i}", function=_ns(name=name, arguments='{"reference": "John 1:1"}'))])
    yield _chunk(finish=step.get("finish") or ("tool_calls" if step.get("tools") else "stop"))
    prompt, completion = step.get("usage", (1000, 200))
    yield _ns(model="served-model", choices=[], usage=_ns(prompt_tokens=prompt, completion_tokens=completion,
                                                          prompt_tokens_details=_ns(cached_tokens=0)))


def _fake_openai(script, calls):
    mod = types.ModuleType("openai")

    class APIStatusError(Exception):
        def __init__(self, status_code):
            super().__init__(f"status {status_code}")
            self.status_code = status_code

    class APIConnectionError(Exception):
        pass

    class _Completions:
        async def create(self, **params):
            calls.append({**params, "messages": list(params["messages"])})
            step = script[min(len(calls) - 1, len(script) - 1)]
            if isinstance(step, Exception):
                raise step
            return _stream(step)

    class AsyncOpenAI:
        def __init__(self, **kw):
            self.chat = types.SimpleNamespace(completions=_Completions())

        async def close(self):
            pass

    mod.AsyncOpenAI, mod.APIStatusError, mod.APIConnectionError = AsyncOpenAI, APIStatusError, APIConnectionError
    return mod


class _MCP:
    tools = [{"name": "lookup_verse", "description": "", "input_schema": {"type": "object"}}]

    def __init__(self, fail=False):
        self.fail = fail

    async def call(self, name, args):
        return ("The library is down.", True) if self.fail else ("In the beginning was the Word.", False)


def _run(monkeypatch, script, limits, question="hi there", model="test-model", mcp=None, make_script=None):
    calls = []
    mod = _fake_openai(script, calls)
    monkeypatch.setitem(sys.modules, "openai", mod)
    if make_script:
        script[:] = make_script(mod)
    stats = {}

    async def go():
        cfg = {"label": "Test", "kind": "openai", "base_url": None}
        return [ev async for ev in providers._run_openai(cfg, "key", model, SYSTEM, [{"role": "user", "content": question}],
                                                          mcp or _MCP(), limits, stats)]
    return asyncio.run(go()), calls, stats


def _text(events):
    return "".join(e["text"] for e in events if e["type"] == "text")


# ---------------------------------------------------------------- ceilings (decision 0008)
def test_the_last_step_answers_without_tools(monkeypatch):
    events, calls, stats = _run(monkeypatch, [{"tools": ["lookup_verse"]}], OPEN)
    assert len(calls) == OPEN.max_steps
    assert all("tools" in c for c in calls[:-1]) and "tools" not in calls[-1]
    assert calls[-1]["messages"][-1]["content"].endswith(providers.ANSWER_NOW)
    assert stats["outcome"] == "step_limit" and events[-1]["type"] == "notice"


def test_a_last_step_that_writes_nothing_says_so(monkeypatch):
    script = [{"tools": ["lookup_verse"]}] * (OPEN.max_steps - 1) + [{"text": []}]
    events, _calls, stats = _run(monkeypatch, script, OPEN)
    assert stats["outcome"] == "step_limit"
    assert events[-1] == {"type": "notice", "incomplete": True, "message": providers.STEP_LIMIT}


def test_output_is_capped_and_usage_is_asked_only_where_priced(monkeypatch):
    _events, calls, _stats = _run(monkeypatch, [{"text": ["Done."]}], OPEN)
    assert calls[0]["max_tokens"] == OPEN.max_tokens and "stream_options" not in calls[0]
    _events, calls, stats = _run(monkeypatch, [{"text": ["Done."]}], OPEN, model=PRICED)
    assert calls[0]["stream_options"] == {"include_usage": True} and stats["est_usd"] > 0


def test_the_spend_ceiling_makes_the_next_step_answer(monkeypatch):
    # Ten million prompt tokens at $0.15 a million is $1.50, past the $1 ceiling after one step.
    script = [{"tools": ["lookup_verse"], "usage": (10_000_000, 100)}, {"text": ["The answer."]}]
    _events, calls, stats = _run(monkeypatch, script, OPEN, model=PRICED)
    assert len(calls) == 2 and "tools" not in calls[1]
    assert stats["outcome"] == "budget"


def test_a_cut_off_reply_says_so(monkeypatch):
    events, _calls, stats = _run(monkeypatch, [{"text": ["Half an ans"], "finish": "length"}], OPEN)
    assert stats["outcome"] == "cut_off" and events[-1]["type"] == "notice"


def test_two_failed_tool_steps_end_the_run(monkeypatch):
    events, calls, stats = _run(monkeypatch, [{"tools": ["lookup_verse"]}], OPEN, mcp=_MCP(fail=True))
    assert stats["outcome"] == "tools_failed" and len(calls) == 2
    assert events[-1]["message"] == policy.TOOLS_DOWN


def test_a_locked_run_shows_fixed_error_text_and_retries_a_server_error_once(monkeypatch):
    script = []
    events, calls, stats = _run(monkeypatch, script, policy.STUDENT_CHAT,
                                make_script=lambda mod: [mod.APIStatusError(503), mod.APIStatusError(503)])
    assert len(calls) == 2 and stats["outcome"] == "provider_error"
    assert events[-1] == {"type": "error", "message": policy.PROVIDER_ERROR}


def test_an_empty_completion_is_retried_once(monkeypatch):
    # In the 2026-11-06 bake-off a host returned an empty stream, and the reader got a blank reply.
    events, calls, stats = _run(monkeypatch, [{"text": []}, {"text": ["The Word was God."]}], OPEN)
    assert len(calls) == 2 and _text(events) == "The Word was God." and stats["outcome"] == "complete"


def test_an_empty_reply_after_the_retry_shows_the_error_text(monkeypatch):
    events, calls, stats = _run(monkeypatch, [{"text": []}], OPEN)
    assert len(calls) == 2 and stats["outcome"] == "provider_error"
    assert events[-1] == {"type": "error", "message": policy.PROVIDER_ERROR}


# ---------------------------------------------------------------- narration (decision 0019)
def test_text_before_a_lookup_never_reaches_the_reader(monkeypatch):
    script = [{"text": ["Let me look ", "that up."], "tools": ["lookup_verse"]}, {"text": ["The Word was God."]}]
    events, _calls, stats = _run(monkeypatch, script, OPEN)
    assert _text(events) == "The Word was God."
    assert stats["narration_dropped"] == 1


def test_an_answer_three_sentences_in_is_shown_even_if_a_lookup_follows(monkeypatch):
    script = [{"text": ["One point. Two points. Three"], "tools": ["lookup_verse"]}, {"text": ["Done."]}]
    events, _calls, stats = _run(monkeypatch, script, OPEN)
    assert _text(events) == "One point. Two points. ThreeDone."
    assert stats["narration_dropped"] == 0


# ---------------------------------------------------------------- the library first (decision 0020)
def test_a_named_verse_is_fetched_before_the_model_starts(monkeypatch):
    events, calls, _stats = _run(monkeypatch, [{"text": ["It names the Word."]}], policy.STUDENT_CHAT,
                                 question="What does John 1:1 mean?")
    assert [e["type"] for e in events[:2]] == ["tool_call", "tool_done"]
    sent = calls[0]["messages"]
    assert sent[-2]["tool_calls"][0]["function"]["name"] == "lookup_verse" and sent[-1]["role"] == "tool"
    assert _text(events) == "It names the Word." and len(calls) == 1


def test_a_first_answer_from_memory_is_set_aside_and_the_model_asked_to_look(monkeypatch):
    script = [{"text": ["From memory, the Word is Jesus."]}, {"tools": ["lookup_verse"]},
              {"text": ["The Word was with God."]}]
    events, calls, stats = _run(monkeypatch, script, policy.STUDENT_CHAT)
    assert _text(events) == "The Word was with God."
    assert stats["lookup_nudges"] == 1
    assert calls[1]["messages"][-1] == {"role": "user", "content": providers.LOOK_FIRST}


def test_a_reply_the_prompt_dictates_is_shown_without_a_lookup(monkeypatch):
    script = [{"text": ["Exegetica doesn't discuss itself in chat."]}]
    events, calls, stats = _run(monkeypatch, script, policy.STUDENT_CHAT, question="What model are you?")
    assert _text(events) == "Exegetica doesn't discuss itself in chat." and len(calls) == 1
    assert "lookup_nudges" not in stats


def test_a_run_without_the_library_first_rule_never_asks_again(monkeypatch):
    events, calls, _stats = _run(monkeypatch, [{"text": ["From memory."]}], OPEN)
    assert _text(events) == "From memory." and len(calls) == 1
