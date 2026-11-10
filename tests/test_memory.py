"""Scripture Memory as redesigned on 2026-11-09 (exegetica-design skill): the server's lookups (references, the
course's week, a verse in the original from the library) and the page's own rules (spaced review inside the
page only, honest words for an attempt, print that waits for its faces, Recite together for teachers, the
ESV notice). No network, no ESV calls, no browser."""
import datetime as dt
import re
from pathlib import Path

import pytest

from webapp import app as appmod
from webapp import memory

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "webapp" / "static" / "js" / "memory.js").read_text(encoding="utf-8")
CSS = (ROOT / "webapp" / "static" / "css" / "memory.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("ref,want", [
    ("John 3:16", ("John", 3, 16, 16)),
    ("John 13:34-35", ("John", 13, 34, 35)),
    ("1 Corinthians 15:3–11", ("1 Corinthians", 15, 3, 11)),
    ("Psalm 23:1-6", ("Psalm", 23, 1, 6)),
    ("John", None),
])
def test_references_parse(ref, want):
    assert memory.parse_ref(ref) == want


def test_the_course_week_follows_the_calendar():
    week = memory.course_week(dt.date(2026, 11, 9))
    assert week["current"]["reference"] == "John 6:35" and week["current"]["unit"]
    assert week["review"][0] == "John 20:31" and "John 6:35" not in week["review"]
    assert len(week["anchors"]) == 16 and week["order"][0] == "John 20:31"
    assert memory.course_week(dt.date(2026, 8, 1))["current"] is None            # before the year starts
    assert memory.course_week(dt.date(2027, 7, 1))["current"] is None            # well after it ends
    assert set(week) == {"course", "anchors", "order", "current", "review", "lesson"}   # course facts only, nothing about a student
    assert week["lesson"]["passage"] == "John 7:14-24" and week["lesson"]["today"]


def test_a_verse_in_the_original_comes_from_the_library():
    if memory._bible_db() is None:
        pytest.skip("no study_bible.db on this machine")
    greek = memory.original_words("John 20:31")
    assert greek["language"] == "Greek" and greek["dir"] == "ltr" and len(greek["words"]) == 24
    believe = [w for w in greek["words"] if w["strongs"] == "G4100"][0]
    assert believe["gloss"] and believe["definition"] and believe["translit"]
    hebrew = memory.original_words("Psalm 119:11")
    assert hebrew["language"] == "Hebrew" and hebrew["dir"] == "rtl" and "/" not in hebrew["words"][0]["word"]
    psalm = memory.original_words("Psalm 23:1")
    assert not any("\\" in w["word"] or "/" in w["word"] for w in psalm["words"])   # STEP's joins never show


def test_a_failed_lookup_is_neither_remembered_nor_called_absent():
    # "The library has no Greek" only when the server says so; a lookup that didn't answer can be tried again
    assert 'e.body.error==="not in the library"' in JS and "originals[ref]=false" in JS
    assert "panelRetry(" in JS and "Try again" in JS


def test_the_lookups_are_routed():
    paths = {getattr(r, "path", "") for r in appmod.app.routes}
    for p in ("texts", "chapter", "original", "course", "cover"):
        assert f"/api/memory/{p}" in paths, p


def test_review_comes_back_on_a_growing_schedule_inside_the_page_only():
    assert "var REVIEW_DAYS = [1, 3, 7, 14, 30, 60];" in JS                       # rule B4
    for call in ("Notification", "serviceWorker", "PushManager", "setInterval("):
        assert call not in JS, call                                              # no notifications or nagging (E2)


def test_an_attempt_is_described_truly():
    # "Word for word." only when every word matched; a close attempt says how many slipped (rule E4)
    assert "var exact = a.ptr===W.length && a.slips===0;" in JS
    assert "Nearly. " in JS and "slipped." in JS
    assert "🎉" not in JS and "😓" not in JS                                      # no celebration effects (E2)


def test_the_ladder_names_its_steps_plainly():
    names = re.findall(r'name:"([^"]+)"', JS)
    assert names[:8] == ["Read it", "Listen", "Say it aloud", "Write it out", "Say it from the first letters",
                         "Write it from the first letters", "Say it from memory", "Write it from memory"]


def test_paper_waits_for_its_faces_and_credits_the_esv():
    assert "document.fonts.load('400 16px \"EB Garamond\"')" in JS and "document.fonts.load('400 30px \"Fraunces\"')" in JS   # H11
    assert "@page cards{size:letter" in CSS and "@page book{size:5.5in 8.5in" in CSS
    assert "Scripture quotations are from the ESV® Bible" in JS


def test_recite_together_is_offered_to_teachers():
    assert "if(isTeacher()) go.push('<button class=\"btn quiet\" id=\"t-recite\">'" in JS     # in the take-it-elsewhere group
    assert 'role="dialog" aria-modal="true"' in (ROOT / "webapp" / "templates" / "memory.html").read_text(encoding="utf-8")


def test_the_practice_page_fades_by_class_and_keeps_its_hairlines_whole():
    for mode in ("m-first", "m-shape", "m-blank", "m-say", "m-type"):
        assert f".{mode} " in CSS, mode
    assert "text-decoration-skip-ink:none" in CSS
