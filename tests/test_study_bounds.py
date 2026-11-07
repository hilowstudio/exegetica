"""Decision F (docs/decisions/0015) and the bot's one reply about itself (0001).
Reads the shipped page and prompts; no network, no cost."""
import pathlib
import re

from webapp import app as appmod
from webapp import policy

_WEBAPP = pathlib.Path(__file__).resolve().parents[1] / "webapp"
INDEX = "\n".join((_WEBAPP / p).read_text(encoding="utf-8") for p in ("templates/chat.html", "static/js/chat.js"))


def test_the_page_closes_a_study_where_the_server_would_refuse_it():
    m = re.search(r"const OPEN_HOURS=(\d+),MAX_MESSAGES=(\d+);", INDEX)
    assert m, "studyClosed() constants not found in the chat page"
    assert int(m.group(1)) == 24
    assert int(m.group(2)) == policy.MAX_MESSAGES


def test_a_closed_study_cannot_send():
    send = INDEX[INDEX.index("async function send(text)"):]
    send = send[:send.index("busy=true")]
    assert "studyClosed(" in send and "return" in send
    assert 'id="closed-note"' in INDEX and 'id="closed-new"' in INDEX
    assert "created:Date.now()" in INDEX                      # new studies record when they began
    assert "!isTeacher()&&start" in INDEX                     # the one-day rule is for students


def test_every_chat_prompt_discusses_exegetica_only_by_its_tools_and_sources():
    """Decision 0001 (2026-11-05): who made it, who reads it, how it works, its feelings, and its
    model all get one fixed reply pointing to the FAQ; only its tools and sources are answered."""
    assert "hello@hilowstudio.dev" in appmod.SELF_REPLY and "FAQ under the ⓘ icon" in appmod.SELF_REPLY
    for persona, subject in (("professor", "bible"), ("professor", "history"), ("researcher", "history")):
        prompt = appmod._system_for(persona, subject)
        assert appmod.SELF_REPLY in prompt and "The one exception" in prompt and "Sources available" in prompt
        for gone in ("A. James Vega", "Pastor Adam", "mandated reporter", "Three exceptions",
                     "It has no feelings", "one plain answer"):
            assert gone not in prompt, gone
