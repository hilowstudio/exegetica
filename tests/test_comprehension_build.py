"""The whole-work comprehension build on Inngest (webapp/comprehension.py, webapp/inngest_app.py
`build-comprehension`) and the Generator's "being prepared" notice (webapp/app.py). Fakes for
books.db, Neon, Inngest, and the model; no network, no cost."""
import asyncio
import datetime as dt
import json

import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, comprehension, generator, inngest_app, metrics, providers, reader

UTC = dt.timezone.utc


def _book(words_per=50000, chapters=6, slug="big-book"):
    chs = [{"n": i, "title": f"Chapter {i}", "text": f"Text of chapter {i}.", "words": words_per}
           for i in range(1, chapters + 1)]
    return {"slug": slug, "title": "Big Book", "author": "A. Writer", "chapter_count": chapters,
            "word_count": words_per * chapters, "chapters": chs}


def _cached(monkeypatch, row):
    async def get(key):
        return row
    monkeypatch.setattr(comprehension, "get", get)


# ---------------------------------------------------------------- status
def test_status_reads_every_state(monkeypatch):
    book = _book()
    total = book["word_count"]
    now = dt.datetime.now(UTC)
    cases = [
        (None, "missing"),
        ({"summary": "s", "_model": "m", "_word_count": total, "_built_at": now}, "ready"),
        ({"summary": "s", "_model": "m", "_word_count": total - 1, "_built_at": now}, "missing"),   # text changed
        ({"summary": "", "_model": comprehension.FAILED_MODEL, "_word_count": total, "_built_at": now}, "failed"),
        ({"summary": "", "_model": comprehension.FAILED_MODEL, "_word_count": total,
          "_built_at": now - comprehension.RETRY_AFTER - dt.timedelta(minutes=1)}, "missing"),        # try again
    ]
    for row, want in cases:
        _cached(monkeypatch, row)
        state, comp = asyncio.run(comprehension.status(book))
        assert state == want, (row, state)
        assert (comp is not None) == (want == "ready")


def test_status_too_large_and_database_down(monkeypatch):
    assert asyncio.run(comprehension.status(_book(words_per=comprehension._MAX_WORDS)))[0] == "too_large"

    async def down(key):
        raise RuntimeError("no table")
    monkeypatch.setattr(comprehension, "get", down)
    assert asyncio.run(comprehension.status(_book())) == ("missing", None)


# ---------------------------------------------------------------- steps
def test_plan_splits_the_book_into_ordered_spans(monkeypatch):
    book = _book(words_per=50000, chapters=6)
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: book)
    _cached(monkeypatch, None)
    plan = asyncio.run(comprehension.step_plan("big-book"))
    assert plan["status"] == "build" and plan["total"] == 300000
    covered = [n for a, b in plan["spans"] for n in range(a, b + 1)]
    assert covered == [1, 2, 3, 4, 5, 6]
    json.dumps(plan)   # crosses a step boundary, so it must be plain JSON


def test_plan_stops_when_already_built(monkeypatch):
    book = _book()
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: book)
    _cached(monkeypatch, {"summary": "s", "_model": "m", "_word_count": book["word_count"],
                          "_built_at": dt.datetime.now(UTC)})
    assert asyncio.run(comprehension.step_plan("big-book")) == {"status": "ready"}
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: None)
    assert asyncio.run(comprehension.step_plan("gone")) == {"status": "no_book"}


def test_map_reads_only_its_span(monkeypatch):
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: _book())
    seen = {}

    async def fake_map(title, batch, i, n):
        seen["ns"] = [c["n"] for c in batch]
        return {"first": batch[0]["n"], "last": batch[-1]["n"], "summary": "x", "themes": [], "significant": []}
    monkeypatch.setattr(comprehension, "_map_batch", fake_map)
    asyncio.run(comprehension.step_map("big-book", [3, 4], 1, 3))
    assert seen["ns"] == [3, 4]
    with pytest.raises(RuntimeError):
        asyncio.run(comprehension.step_map("big-book", [40, 41], 1, 3))


def test_reduce_stores_or_raises_for_a_retry(monkeypatch):
    stored = []

    async def store(key, title, comp, total, model=None):
        stored.append((key, comp, total, model))
    monkeypatch.setattr(comprehension, "_store", store)
    notes = [{"first": 1, "last": 3, "summary": "a", "themes": [], "significant": []},
             {"first": 4, "last": 6, "summary": "b", "themes": [], "significant": []}]

    async def empty(title, notes):
        return {}
    monkeypatch.setattr(comprehension, "_reduce", empty)
    with pytest.raises(RuntimeError):
        asyncio.run(comprehension.step_reduce("big-book", "Big Book", 300000, notes))
    assert not stored

    async def good(title, notes):
        return {"summary": "whole", "arc": [], "themes": [], "significance": []}
    monkeypatch.setattr(comprehension, "_reduce", good)
    assert asyncio.run(comprehension.step_reduce("big-book", "Big Book", 300000, notes)) == \
        {"status": "built", "spans": 2}
    key, comp, total, model = stored[0]
    assert comp["recap"][-1] == {"through_section": 6, "so_far": "a b"} and model is None


def test_failure_leaves_a_marker(monkeypatch):
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: _book())
    stored = []

    async def store(key, title, comp, total, model=None):
        stored.append((key, total, model))
    monkeypatch.setattr(comprehension, "_store", store)

    class Ctx:
        event = type("E", (), {"data": {"event": {"data": {"book_key": "big-book"}}}})()
    asyncio.run(inngest_app.comprehension_failed_fn(Ctx()))
    assert stored == [("big-book", 300000, comprehension.FAILED_MODEL)]


# ---------------------------------------------------------------- the Inngest function
class _Ctx:
    """Runs steps inline and records their ids, as Inngest would on a first pass."""
    def __init__(self, data):
        self.event = type("E", (), {"data": data})()
        self.ids = []
        ctx = self

        class Step:
            async def run(self, step_id, fn, *args):
                ctx.ids.append(step_id)
                return await fn(*args)

        class Group:
            async def parallel(self, callables):
                return tuple([await c() for c in callables])
        self.step, self.group = Step(), Group()


def test_build_function_runs_one_step_per_span(monkeypatch):
    book = _book(words_per=50000, chapters=12)
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: book)
    _cached(monkeypatch, None)
    monkeypatch.setattr(comprehension, "_MIN_BATCH_WORDS", 50000)   # one span per chapter

    async def fake_map(title, batch, i, n):
        return {"first": batch[0]["n"], "last": batch[-1]["n"], "summary": f"s{i}", "themes": [], "significant": []}
    got = {}

    async def fake_reduce(key, title, total, notes):
        got["notes"] = notes
        return {"status": "built", "spans": len(notes)}
    monkeypatch.setattr(comprehension, "_map_batch", fake_map)
    monkeypatch.setattr(comprehension, "step_reduce", fake_reduce)
    ctx = _Ctx({"book_key": "big-book"})
    out = asyncio.run(inngest_app.build_comprehension_fn._handler(ctx))
    assert out == {"status": "built", "spans": 12}
    assert ctx.ids == ["plan"] + [f"map-{i}" for i in range(12)] + ["reduce"]
    assert len(set(ctx.ids)) == len(ctx.ids)                      # step ids are the memo keys
    assert [n["summary"] for n in got["notes"]] == [f"s{i}" for i in range(12)]   # in reading order


def test_build_function_is_one_per_book():
    cfg = inngest_app.build_comprehension_fn.get_config("http://x").main
    assert cfg.singleton is not None and cfg.singleton.key == "event.data.book_key"
    assert cfg.concurrency[0].limit == comprehension.MAP_CONCURRENCY


# ---------------------------------------------------------------- the generate endpoint
@pytest.fixture
def gen_env(monkeypatch):
    seen = {"runs": []}

    async def fake_run(provider, api_key, model, system_text, history, mcp, limits=None, stats=None):
        seen["runs"].append(history[0]["content"])
        stats.update(outcome="complete")
        yield {"type": "text", "text": "A study guide."}
        yield {"type": "end", "outcome": "complete"}
    monkeypatch.setattr(providers, "run", fake_run)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "t", "role": "teacher"})
    monkeypatch.setattr(auth, "is_teacher", lambda u: True)
    monkeypatch.setattr(metrics, "record", lambda row: None)
    book = _book(words_per=generator._GEN_WORD_BUDGET, chapters=3)
    monkeypatch.setattr(reader, "_gen_book_sync", lambda slug: book)
    app = Starlette(routes=[Route("/api/generate/book", appmod.generate_book_endpoint, methods=["POST"])])
    app.state.mcp = None
    seen["client"] = TestClient(app)
    seen["format"] = next(iter(generator.FORMATS))
    return seen


def _post(env):
    r = env["client"].post("/api/generate/book", json={"format_id": env["format"], "book_slug": "big-book",
                                                       "coverage": {"through": 2}})
    assert r.status_code == 200, r.text
    return [json.loads(x[5:]) for x in r.text.split("\n") if x.startswith("data:")]


def _state(monkeypatch, state, comp=None, queued=True):
    async def status(book):
        return state, comp
    calls = []

    async def request(key):
        calls.append(key)
        return queued
    monkeypatch.setattr(comprehension, "status", status)
    monkeypatch.setattr(appmod, "_request_comprehension", request)
    return calls


def test_a_large_book_without_comprehension_is_queued_and_says_so(gen_env, monkeypatch):
    calls = _state(monkeypatch, "missing")
    events = _post(gen_env)
    assert calls == ["big-book"] and not gen_env["runs"]          # no model call
    assert {"type": "notice", "message": appmod.BOOK_PREPARING, "incomplete": True} in events


def test_without_inngest_or_after_a_failed_build_it_still_generates(gen_env, monkeypatch):
    _state(monkeypatch, "missing", queued=False)
    assert any(e.get("type") == "text" for e in _post(gen_env)) and len(gen_env["runs"]) == 1
    calls = _state(monkeypatch, "failed")
    assert any(e.get("type") == "text" for e in _post(gen_env)) and not calls


def test_a_ready_book_generates_from_its_comprehension(gen_env, monkeypatch):
    comp = {"summary": "The whole work.", "arc": [], "themes": [], "significance": [],
            "recap": [{"through_section": 1, "so_far": "So far."}]}
    calls = _state(monkeypatch, "ready", comp)
    monkeypatch.setattr(comprehension, "select_covered_text",
                        lambda book, covered, query, budget: ([(1, "Chapter 1", "Text.")], False))
    _post(gen_env)
    assert not calls and "The whole work." in gen_env["runs"][0]
