"""The chat route's own decisions, made before or around any model call: fixed replies, limits,
the crisis panel first, the model lock, the reply check, the keep-alive, and the metrics row
(webapp/app.py chat()). A minimal app with fake tools and a fake provider; no network, no cost."""
import json

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, citations, metrics, policy, providers, reply_check, usage

STUDENT = {"id": "00000000-0000-0000-0000-000000000001", "email": "s@school.test", "role": "student"}
TEACHER = {"id": "00000000-0000-0000-0000-000000000002", "email": "t@school.test", "role": "teacher"}


class _Bridge:
    tools = [{"name": "lookup_verse", "description": "", "input_schema": {"type": "object"}}]
    session = object()

    async def call(self, name, args):
        return "text", False


@pytest.fixture
def env(monkeypatch):
    """A client, the provider calls it received, and the metrics rows it recorded."""
    seen = {"runs": [], "rows": []}
    user = {"who": STUDENT}

    async def fake_run(provider, api_key, model, system_text, history, mcp, limits=None, stats=None):
        seen["runs"].append({"provider": provider, "model": model, "limits": limits, "key": api_key})
        stats.update(outcome="complete", steps=1, est_usd=0.01, model_req=model)
        for chunk in seen.get("script", ["The Word was God (John 1:1). "]):
            yield {"type": "text", "text": chunk}
        yield {"type": "end", "outcome": "complete"}

    monkeypatch.setattr(providers, "run", fake_run)
    monkeypatch.setattr(auth, "current_user", lambda request: user["who"])
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u.get("role") == "teacher")
    monkeypatch.setattr(metrics, "record", lambda row: seen["rows"].append(row))
    monkeypatch.setattr(usage, "_recent", {})

    async def no_cap(user_id, teacher):
        return seen.get("cap")
    monkeypatch.setattr(usage, "check", no_cap)

    async def no_add(*a):
        return None
    monkeypatch.setattr(usage, "add", no_add)
    app = Starlette(routes=[Route("/api/chat", appmod.chat, methods=["POST"])])
    app.state.mcp = _Bridge()
    app.state.mcp_history = None
    seen["client"] = TestClient(app)
    seen["user"] = user
    return seen


def _events(env, messages, **body):
    r = env["client"].post("/api/chat", json={"messages": messages, **body})
    assert r.status_code == 200, r.text
    return [json.loads(line[5:]) for line in r.text.split("\n") if line.startswith("data:")], r.text


def _study(*turns):
    out = []
    for i, t in enumerate(turns):
        out.append({"role": "user" if i % 2 == 0 else "assistant", "content": t})
    return out


def test_a_bare_greeting_gets_fixed_text_and_no_model_call(env):
    events, _ = _events(env, _study("Hello!"))
    assert {"type": "text", "text": policy.GREETING["bible"]} in events
    assert events[-2] == {"type": "end", "outcome": "greeting"} and not env["runs"]
    assert env["rows"][0]["outcome"] == "greeting"


@pytest.mark.parametrize("text", ["hi", "Hey there", "good morning", "hello exegetica!!", "yo"])
def test_greetings_are_recognised(text):
    assert policy.is_greeting(text)


@pytest.mark.parametrize("text", ["hi, who was Nicodemus?", "hello how are you", "Hi!! what does logos mean"])
def test_questions_with_a_greeting_go_to_the_model(text):
    assert not policy.is_greeting(text)


def test_a_long_tool_free_study_gets_the_fixed_reply(env):
    turns = ["q", "a"] * policy.DRIFT_TURNS + ["one more"]
    events, _ = _events(env, _study(*turns))
    assert {"type": "text", "text": policy.DRIFT_TEXT} in events and not env["runs"]


def test_drift_does_not_apply_to_teachers(env):
    env["user"]["who"] = TEACHER
    turns = ["q", "a"] * policy.DRIFT_TURNS + ["one more"]
    _events(env, _study(*turns))
    assert len(env["runs"]) == 1


def test_a_tool_in_the_last_replies_resets_drift():
    msgs = _study(*(["q", "a"] * policy.DRIFT_TURNS + ["q"]))
    msgs[1]["tools"] = [{"name": "lookup_verse"}]
    assert not policy.drifted(msgs)
    msgs[-2]["tools"] = [{"name": "lookup_verse"}]
    assert not policy.drifted(msgs)


def test_students_are_locked_to_the_student_model(env):
    _events(env, _study("Who was Nicodemus?"), provider="openai", model="gpt-5.6", api_key="sk-x")
    run = env["runs"][0]
    assert (run["provider"], run["model"], run["key"]) == ("anthropic", policy.STUDENT_MODEL, None)
    assert run["limits"] is policy.STUDENT_CHAT


def test_a_capped_student_in_crisis_still_gets_the_help_panel(env):
    env["cap"] = usage.CAPPED
    events, _ = _events(env, _study("I want to kill myself"))
    kinds = [e["type"] for e in events]
    assert kinds.index("safety") < kinds.index("error")
    assert {"type": "error", "message": usage.CAPPED} in events and not env["runs"]
    assert env["rows"][0]["outcome"] == "capped"


def test_too_many_turns_in_a_minute_are_refused_without_a_model_call(env):
    for _ in range(usage.PER_MINUTE):
        _events(env, _study("Who was Nicodemus?"))
    events, _ = _events(env, _study("Who was Nicodemus?"))
    assert {"type": "error", "message": usage.TOO_FAST} in events
    assert len(env["runs"]) == usage.PER_MINUTE


def test_a_stopped_reply_is_recorded_as_a_check_stop(env):
    env["script"] = ["The Word was God. ", "I love you. ", "More text."]
    events, _ = _events(env, _study("Who was Nicodemus?"))
    assert {"type": "error", "message": reply_check.STOP_TEXT} in events
    assert {"type": "end", "outcome": "check_stop"} in events
    assert "I love you" not in json.dumps(events)
    row = env["rows"][-1]
    assert row["outcome"] == "check_stop" and row["checks_stopped"] == 1


def test_a_slow_model_gets_keep_alives(env, monkeypatch):
    import asyncio

    async def slow_run(*a, stats=None, **k):
        await asyncio.sleep(0.25)
        stats.update(outcome="complete", steps=1)
        yield {"type": "text", "text": "Answer."}
        yield {"type": "end", "outcome": "complete"}
    monkeypatch.setattr(providers, "run", slow_run)
    monkeypatch.setattr(appmod, "HEARTBEAT", 0.05)
    events, raw = _events(env, _study("Who was Nicodemus?"))
    assert ": keep-alive" in raw and {"type": "end", "outcome": "complete"} in events


def test_the_metrics_row_carries_no_text_or_person(env):
    _events(env, _study("Who was Nicodemus?"))
    row = env["rows"][-1]
    assert set(row) <= set(metrics.FIELDS)
    assert row["outcome"] == "complete" and row["route"] == "chat:bible" and row["key_source"] == "server"
    assert len(row["prefix_hash"]) == 12
    blob = json.dumps(row)
    for leak in ("Nicodemus", STUDENT["id"], STUDENT["email"]):
        assert leak not in blob


def test_signed_out_chat_is_refused(env):
    env["user"]["who"] = None
    r = env["client"].post("/api/chat", json={"messages": _study("hi")})
    assert r.status_code == 401


def test_a_reply_that_used_no_library_tool_is_labeled(env):
    events, _ = _events(env, _study("Who was Nicodemus?"))
    assert events[-2:] == [{"type": "source_note", "text": citations.NO_SOURCE}, {"type": "done"}]


def test_a_stop_on_the_last_sentence_still_sends_the_stop_line(env):
    env["script"] = ["The Word was God. ", "I love you"]   # no boundary after it: released only at the end
    events, _ = _events(env, _study("Who was Nicodemus?"))
    assert {"type": "error", "message": reply_check.STOP_TEXT} in events
    assert {"type": "end", "outcome": "check_stop"} in events
    assert "I love you" not in json.dumps(events)
    assert not any(e["type"] == "source_note" for e in events)


def _quoting_run(quote, tool_text):
    """A run that calls one tool, then quotes text in its reply."""
    async def run(provider, api_key, model, system_text, history, mcp, limits=None, stats=None):
        out, _ = await mcp.call("lookup_verse", {"reference": "John 15:9"})
        assert out == tool_text
        yield {"type": "tool_done", "name": "lookup_verse", "input": {}, "output": out, "error": False}
        stats.update(outcome="complete", steps=2)
        yield {"type": "text", "text": f"Jesus said, “{quote}” (John 15:9). "}
        yield {"type": "end", "outcome": "complete"}
    return run


@pytest.mark.parametrize("quote,stopped", [
    ("As the Father has loved me, so have I loved you", False),   # the tool returned it
    ("I love you, and you alone, always", True),                  # no source holds it
])
def test_quoted_affection_passes_only_when_this_runs_tool_returned_it(env, monkeypatch, quote, stopped):
    verse = "John 15:9: As the Father has loved me, so have I loved you. Abide in my love."

    class Bridge(type(env["client"].app.state.mcp)):
        async def call(self, name, args):
            return verse, False
    env["client"].app.state.mcp = Bridge()
    monkeypatch.setattr(citations, "bible", lambda: None)
    monkeypatch.setattr(providers, "run", _quoting_run(quote, verse))
    events, _ = _events(env, _study("What does John 15:9 say?"))
    assert ({"type": "error", "message": reply_check.STOP_TEXT} in events) is stopped
    if not stopped:
        assert not any(e["type"] == "source_note" for e in events)   # quoted from the tool: nothing to note
