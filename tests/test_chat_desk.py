"""The chat page as redesigned on 2026-11-09 (exegetica-design skill): a study desk. References in replies open the
passage beside the conversation (rule B1), lookups are named in plain words (F11, the FAQ's follow-up), a streaming
reply never pulls the reader away (G12), studies are grouped by date, and nothing on the desk calls a model.
No network, no browser."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "webapp" / "static"
JS = (STATIC / "js" / "chat.js").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "chat.css").read_text(encoding="utf-8")
HTML = (ROOT / "webapp" / "templates" / "chat.html").read_text(encoding="utf-8")


def _tool_names():
    src = (ROOT / "src" / "studybible_mcp" / "tools.py").read_text(encoding="utf-8")
    cur = (ROOT / "webapp" / "curriculum.py").read_text(encoding="utf-8")
    return set(re.findall(r'name="([a-z_]+)",\s*\n\s*annotations', src)) | set(re.findall(r'"name":\s*"([a-z_]+)"', cur))


def test_every_library_tool_has_plain_words():
    words = set(re.findall(r"\b([a-z_]+):\[\"", JS[JS.index("const TOOL_WORDS="):JS.index("function toolSubject")]))
    names = _tool_names()
    assert len(names) > 25
    assert not (names - words), sorted(names - words)
    assert "chips.label(" in JS and "label: function (name, text)" in (STATIC / "js" / "shell.js").read_text(encoding="utf-8")


def test_references_in_replies_open_the_passage():
    assert "return linkRefs(esc(s)" in JS and 'class="ref" href="#" data-ref="' in JS
    assert "closest(\".ref[data-ref]\")" in JS and "openPassage(" in JS
    assert 'id="passage"' in HTML and 'aria-labelledby="pg-title"' in HTML
    assert ".passage.open ~ .col{padding-right:420px}" in CSS        # beside the conversation on a wide screen


def test_the_desk_calls_no_model():
    desk = JS[JS.index("/* ---------- the passage beside the conversation"):]
    assert "/api/chat" not in desk.replace("/api/chats", "")
    assert "/api/memory/chapter" in desk and "/api/memory/original" in desk and '"/api/memory"' in desk


def test_a_verse_added_from_chat_matches_scripture_memory():
    mem = (STATIC / "js" / "memory.js").read_text(encoding="utf-8")
    seed = re.search(r"var SEED = \[(.*?)\];", mem, re.S).group(1)
    chat_seed = re.search(r"const MEM_SEED=\[(.*?)\];", JS, re.S).group(1)
    assert re.findall(r'"([^"]+)"', seed) == re.findall(r'"([^"]+)"', chat_seed)
    assert '"studybible.memory.v1"' in JS and "async function addToMemory(ref)" in JS
    assert "if(!db){Shell.toast(\"Scripture Memory couldn't be reached" in JS   # a failed read never overwrites the account


def test_a_streaming_reply_leaves_the_reader_where_they_are():
    assert "function atBottom()" in JS and "if(follow){mainEl.scrollTop=mainEl.scrollHeight" in JS
    assert 'id="jump"' in HTML and "Jump to the latest" in HTML


def test_studies_are_grouped_and_closed_ones_say_so():
    assert "function dayGroup(ts)" in JS and '"Earlier this week"' in JS
    assert 'ro.textContent="Read only"' in JS


def test_the_wordmark_scrolls_with_the_conversation():
    main = re.search(r'<main class="scroll" id="main">(.*?)</main>', HTML, re.S).group(1)
    assert '{% include "partials/masthead.html" %}' in main
