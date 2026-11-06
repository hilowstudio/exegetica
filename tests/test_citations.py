"""What a reply drew on (webapp/citations.py): the run's tool results held in memory, quotations and
references found in text, the note under a chat reply, and the Generator's source check. The pure
cases run anywhere; the bundled-Bible cases read db/study_bible.db and skip where it is absent.
No network."""
import asyncio

import pytest

from webapp import citations

needs_bible = pytest.mark.skipif(citations.bible() is None, reason="no study_bible.db here")


class _Bridge:
    tools = [{"name": "lookup_verse"}]
    session = "the bridge's own"

    async def call(self, name, args):
        if name == "broken":
            return "library unavailable", True
        return f"result of {name}: Jesus said, “I am the bread of life; whoever comes to me shall not hunger.”", False


def recorded(*calls):
    run = citations.Recorder(_Bridge())
    for name in calls:
        asyncio.run(run.call(name, {}))
    return run


def test_the_recorder_keeps_successful_results_and_passes_the_bridge_through():
    run = recorded("lookup_verse", "broken")
    assert run.calls == 2 and len(run.outputs) == 1 and "bread of life" in run.outputs[0]
    assert run.tools == _Bridge.tools and run.session == "the bridge's own"


def test_quotations_are_found_in_curly_straight_and_block_form():
    text = ('He said, “one two three four five six seven.” Then "short one" and\n'
            '> a blockquote line that runs on for a while\n\nEnd.')
    found = [q for q, _, _ in citations.quotations(text)]
    assert found == ["one two three four five six seven.", "a blockquote line that runs on for a while"]


@pytest.mark.parametrize("text,refs", [
    ("See John 3:16 and 1 Cor 13:4-7.", [("Jhn", 3, 16, 16), ("1Co", 13, 4, 7)]),
    ("Song of Solomon 2:1 names the rose.", [("Sng", 2, 1, 1)]),
    ("We met at 10:30 in Chapter 3:2.", [("Cha", 3, 2, 2)]),   # an unknown book; the check leaves it out
])
def test_references_are_read_from_text(text, refs):
    assert [(r["code"], r["chapter"], r["v1"], r["v2"]) for r in citations.references(text)] == refs


def test_a_quotation_counts_as_held_only_when_every_piece_is():
    held = citations.Held(["In the beginning was the Word, and the Word was with God."])
    assert citations.found("In the beginning was the Word … the Word was with God", held)
    assert not citations.found("In the beginning was the Word … and the Word became flesh", held)


def test_a_quotation_across_a_verse_boundary_is_found_in_a_fetched_passage():
    # get_passage prints each verse behind its number; a reply quoting John 11:14-15 from such a
    # passage was once stopped as unheld affection ("I am glad").
    passage = ("**14** Then Jesus told them plainly, \"Lazarus has died, **15** and for your sake I am glad "
               "that I was not there, so that you may believe. But let us go to him.\"")
    held = citations.Held([passage])
    quote = "Lazarus has died, and for your sake I am glad that I was not there, so that you may believe"
    assert citations.found(quote, held)
    assert citations.quote_check(type("Run", (), {"outputs": [passage]}), None)(quote)
    assert not citations.found("Lazarus has died, and for your sake I am glad that I was there", held)


def test_the_reply_check_trusts_only_this_runs_results_for_short_quotations():
    run = recorded("lookup_verse")
    ok = citations.quote_check(run, None)
    assert ok("I am the bread of life")
    assert not ok("I love you")          # Scripture has the phrase, but no source of this run does
    assert not ok("love")                # too short to compare: fails closed


@needs_bible
def test_the_bundled_bible_vouches_for_a_long_quotation_and_not_a_short_one():
    ok = citations.quote_check(recorded(), citations.bible())
    assert ok("As the Father has loved Me, so have I loved you")   # John 15:9 (BSB)
    assert not ok("I love you")


def test_a_reply_with_no_library_tool_is_labeled():
    assert citations.chat_note("An answer from memory.", recorded(), [], None) == citations.NO_SOURCE


def test_a_reply_lists_quotations_no_source_holds():
    run = recorded("lookup_verse")
    good = "Jesus said, “I am the bread of life; whoever comes to me shall not hunger” (John 6:35)."
    assert citations.chat_note(good, run, [], None) is None
    bad = good + " Augustine wrote, “our hearts are restless until they rest in thee always.”"
    note = citations.chat_note(bad, run, [], None)
    assert note.startswith("Not found in the library results") and "our hearts are restless" in note


def test_earlier_results_in_the_study_count_for_the_note():
    run = recorded("lookup_verse")
    text = "As he wrote, “our hearts are restless until they rest in thee always.”"
    earlier = ["Augustine, Confessions 1.1: our hearts are restless until they rest in thee always."]
    assert citations.chat_note(text, run, earlier, None) is None


class _FakeBible:
    def codes(self):
        return {"Jhn", "Gen"}

    def verse_exists(self, code, chapter, verse):
        return (code, chapter) == ("Jhn", 3) and verse <= 36

    def holds(self, fragment, hint=None):
        return "god so loved the world" in fragment


@pytest.mark.parametrize("route,reported", [("generate", True), ("revise", False)])
def test_a_generator_run_ends_with_its_source_check(monkeypatch, route, reported):
    import json

    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from webapp import app as appmod
    from webapp import metrics, providers

    async def fake_run(provider, api_key, model, system_text, history, mcp, limits=None, stats=None):
        await mcp.call("lookup_verse", {"reference": "John 6:35"})
        stats.update(outcome="complete", steps=2)
        yield {"type": "text", "text": "Read John 3:16.\n\n“I am the bread of life; whoever comes to me shall not hunger.”\n"}
        yield {"type": "end", "outcome": "complete"}
    monkeypatch.setattr(providers, "run", fake_run)
    monkeypatch.setattr(citations, "bible", lambda: _FakeBible())
    monkeypatch.setattr(metrics, "record", lambda row: None)

    async def endpoint(request):
        return appmod._generation(route, {"type": "start"}, "anthropic", None, "", "system", "task", _Bridge(), None)
    client = TestClient(Starlette(routes=[Route("/g", endpoint, methods=["POST"])]))
    events = [json.loads(line[5:]) for line in client.post("/g").text.split("\n") if line.startswith("data:")]
    reports = [e for e in events if e["type"] == "report"]
    assert events[-1] == {"type": "done"}
    if reported:
        assert reports == [{"type": "report", "references": 1, "missing_references": [], "quotations": 1,
                            "quotations_not_found": []}]
    else:
        assert reports == []


def test_the_generator_report_lists_what_was_not_found():
    doc = ("Read John 3:16 and John 22:3, then Hezekiah 4:1.\n\n"
           "“For God so loved the world, that he gave his only Son” (John 3:16).\n"
           "“A sentence the model made up and put in quotation marks.”\n"
           "“A line from the reading the teacher chose for today.”")
    report = citations.generator_report(doc, ["prompt: a line from the reading the teacher chose for today."],
                                      _FakeBible())
    assert report["type"] == "report"
    assert report["references"] == 3            # Hezekiah is no book, so it is left out
    assert report["missing_references"] == ["John 22:3"]
    assert report["quotations"] == 3
    assert report["quotations_not_found"] == ["A sentence the model made up and put…"]
