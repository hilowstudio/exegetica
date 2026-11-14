"""Decision 0033: reading supports for a course's students, written so no level is ever named or shipped."""
import re
from pathlib import Path

from webapp import generator, prep_catalog

ROOT = Path(__file__).resolve().parents[1]
LEVELS = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\b|\bgrades?\s+\d|\b(?:sixth|seventh|eighth|ninth)\b|\blexile\b", re.I)


def test_only_a_supported_course_gets_the_supports():
    fmt = next(iter(generator.FORMATS))
    assert generator.supports_for("bible-2")
    assert not generator.supports_for("algebra-1") and not generator.supports_for(None)
    assert generator.READING_SUPPORTS in generator.build_system(fmt, "secondary", supports=True)
    assert generator.READING_SUPPORTS not in generator.build_system(fmt, "secondary")


def test_the_supports_never_name_a_level():
    for text in (generator.READING_SUPPORTS, generator.REVISION_SUPPORTS):
        assert not LEVELS.search(text), text
        assert "Never state, label or hint at a reading level" in text


def test_a_revision_keeps_the_supports():
    system, _ = generator.build_revision("# Doc\n\nText.", "Shorten it.", supports=True)
    assert generator.REVISION_SUPPORTS in system
    system, _ = generator.build_revision("# Doc\n\nText.", "Shorten it.")
    assert generator.REVISION_SUPPORTS not in system


def test_the_scrub_takes_out_any_level_talk_and_keeps_the_rest():
    doc = ("# The Lamb of God\n\n> **Grade Band:** Secondary  \n> **Estimated Time:** 20 minutes\n\n"
           "This page is written at a sixth-grade reading level. Read John 1:29 aloud.\n\n"
           "- Simplified for struggling readers.\n1. What does John call Jesus?\n")
    out = generator.scrub_levels(doc)
    assert "Grade Band" not in out and "reading level" not in out and "Simplified" not in out
    assert "Estimated Time" in out and "Read John 1:29 aloud." in out and "What does John call Jesus?" in out


def test_a_student_copy_never_carries_a_grade_band_line():
    doc = "# Handout\n\n> **Grade Band:** Secondary  \n> **Estimated Time:** 20 minutes\n\n1. Read John 3:16.\n"
    out = prep_catalog.student_copy(doc)
    assert "Grade Band" not in out and "Estimated Time" in out and "Read John 3:16." in out


def test_the_supports_are_never_shipped_to_a_browser():
    marks = ("Supports for this class's readers", "readers who need support", "SUPPORTED_COURSES")
    for folder in ("webapp/static", "webapp/templates"):
        for f in (ROOT / folder).rglob("*"):
            if f.is_file() and f.suffix in (".js", ".css", ".html", ".json", ".txt"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                for m in marks:
                    assert m not in text, f"{m!r} found in {f}"
