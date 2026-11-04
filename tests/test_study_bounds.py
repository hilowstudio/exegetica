"""Decision F (docs/decisions/0015) and the bot's answer to "who can read this?" (0001, 0009).
Reads the shipped page and prompts; no network, no cost."""
import pathlib
import re

from webapp import app as appmod
from webapp import policy

INDEX = (pathlib.Path(__file__).resolve().parents[1] / "webapp" / "static" / "index.html").read_text(encoding="utf-8")


def test_the_page_closes_a_study_where_the_server_would_refuse_it():
    m = re.search(r"const OPEN_HOURS=(\d+),MAX_MESSAGES=(\d+);", INDEX)
    assert m, "studyClosed() constants not found in index.html"
    assert int(m.group(1)) == 24
    assert int(m.group(2)) == policy.MAX_MESSAGES


def test_a_closed_study_cannot_send():
    send = INDEX[INDEX.index("async function send(text)"):]
    send = send[:send.index("busy=true")]
    assert "studyClosed(" in send and "return" in send
    assert 'id="closed-note"' in INDEX and 'id="closed-new"' in INDEX
    assert "created:Date.now()" in INDEX                      # new studies record when they began
    assert "!isTeacher()&&start" in INDEX                     # the one-day rule is for students


def test_every_chat_prompt_answers_who_reads_this_with_the_faq_facts():
    faq = re.search(r"<summary>Who can read what I type\?</summary><p>(.*?)<a ", INDEX).group(1)
    for fact in ("outside model provider", "limited time", "A. James Vega", "mandated reporter"):
        assert fact in faq and fact in appmod.ABOUT_EXEGETICA, fact
    assert "/privacy" in appmod.ABOUT_EXEGETICA
    assert "Three exceptions" in appmod.CONDUCT_FLOOR and "who can read or see what is typed" in appmod.CONDUCT_FLOOR
    for persona, subject in (("professor", "bible"), ("professor", "history")):
        assert appmod.ABOUT_EXEGETICA in appmod._system_for(persona, subject)
