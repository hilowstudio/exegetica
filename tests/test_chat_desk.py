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
PASSAGE = (STATIC / "js" / "passage.js").read_text(encoding="utf-8")       # the panel every page shares
PANEL = (ROOT / "webapp" / "templates" / "partials" / "passage.html").read_text(encoding="utf-8")
SHELL_CSS = (STATIC / "css" / "shell.css").read_text(encoding="utf-8")


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
    assert "return Passage.linkHtml(esc(s)" in JS and 'class="ref" href="/?passage=' in PASSAGE
    assert 'closest(".ref[data-ref]")' in PASSAGE and "open(a.getAttribute(\"data-ref\"), a)" in PASSAGE
    assert 'id="passage"' in PANEL and 'aria-labelledby="pg-title"' in PANEL
    base = (ROOT / "webapp" / "templates" / "base.html").read_text(encoding="utf-8")
    assert '{% include "partials/passage.html" %}' in base and "/static/js/passage.js" in base   # on every page
    assert "body.passage-open .app > .col{padding-right:420px}" in CSS        # beside the conversation on a wide screen
    assert ".passage{position:fixed" in SHELL_CSS and "#passage" not in CSS


def test_the_desk_calls_no_model():
    desk = JS[JS.index("/* ---------- the passage beside the conversation"):]
    assert "/api/chat" not in desk.replace("/api/chats", "")
    assert "/api/chat" not in PASSAGE.replace("/api/chats", "")
    assert "/api/memory/chapter" in PASSAGE and "/api/memory/original" in PASSAGE and '"/api/memory"' in PASSAGE


def test_ask_fills_the_box_and_never_sends():
    ask = JS[JS.index("Passage.ask=function(r){"):JS.index("function openFromAddress(){")]
    assert 'input.value="Help me study "+r+".";' in ask and "send(" not in ask and ".submit" not in ask
    assert "window.history.replaceState(null,\"\",location.pathname);" in JS     # a reload doesn't ask again (chat has its own history)


def test_a_verse_added_from_chat_matches_scripture_memory():
    mem = (STATIC / "js" / "memory.js").read_text(encoding="utf-8")
    seed = re.search(r"var SEED = \[(.*?)\];", mem, re.S).group(1)
    panel_seed = re.search(r"var MEM_SEED = \[(.*?)\];", PASSAGE, re.S).group(1)
    assert re.findall(r'"([^"]+)"', seed) == re.findall(r'"([^"]+)"', panel_seed)
    assert '"studybible.memory.v1"' in PASSAGE and "async function keep(ref)" in PASSAGE
    assert "if (!db) { Shell.toast(\"Scripture Memory couldn't be reached" in PASSAGE   # a failed read never overwrites the account


def test_a_streaming_reply_leaves_the_reader_where_they_are():
    assert "function atBottom()" in JS and "if(follow){mainEl.scrollTop=mainEl.scrollHeight" in JS
    assert 'id="jump"' in HTML and "Jump to the latest" in HTML


def test_studies_are_grouped_and_closed_ones_say_so():
    assert "function dayGroup(ts)" in JS and '"Earlier this week"' in JS
    assert 'ro.textContent="Read only"' in JS


def test_the_wordmark_scrolls_with_the_conversation():
    main = re.search(r'<main class="scroll" id="main">(.*?)</main>', HTML, re.S).group(1)
    assert '{% include "partials/masthead.html" %}' in main


def test_the_studies_button_sits_where_the_list_opens():
    # Adam, 2026-11-09: a Studies button at the top right was not intuitive. It sits at the top left, labelled,
    # and the open list carries its own hide control at its top edge (the familiar sidebar pattern).
    assert '<span>Studies</span></button>' in HTML and 'id="side-x"' in HTML and 'aria-label="Hide studies"' in HTML
    assert ".thread-h{position:absolute;top:12px;left:calc(var(--rail-w) + 16px);right:20px;" in CSS and "margin-right:auto" in CSS
    assert ".side.open ~ .col .menu-btn{visibility:hidden}" in CSS
    assert "menuBtn.onclick=()=>setStudiesOpen(true,true);" in JS and "sideX.onclick=()=>setStudiesOpen(false,true);" in JS
    assert "visibility:hidden}" in CSS[CSS.index(".side{"):CSS.index(".side.open{")]   # a closed list takes no focus
