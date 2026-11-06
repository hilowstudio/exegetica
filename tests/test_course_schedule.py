"""The course schedule tool reads the John calendar and reports today's Chicago date with the
day's lesson, or says plainly there is none and gives the nearest lessons (webapp/curriculum.py).
Runs against a small calendar fixture with a pinned "today". No network."""
import json
from datetime import date, datetime, timezone

import pytest

from webapp import curriculum

CAL = {
    "course": "Test course",
    "lessons": [
        {"date": "2026-11-05", "dow": "Thursday", "schedule": "thursday", "unit": "Bread of Life",
         "lesson": "L1", "passage": "John 6:1-15 (ESV)", "focus": "five loaves", "plant": True,
         "planted": "6:35", "checkpoint": None, "half_day": False, "project": None,
         "file": "GEN_U9-L1-John-6-1-15.md"},
        {"date": "2026-11-06", "dow": "Friday", "schedule": "regular", "unit": "Bread of Life",
         "lesson": "L2", "passage": "John 6:16-24 (ESV)", "focus": "walking on the water",
         "plant": False, "planted": "", "checkpoint": None, "half_day": False, "project": "due",
         "file": "GEN_U9-L2-John-6-16-24.md"},
        {"date": "2026-11-09", "dow": "Monday", "schedule": "regular", "unit": "CHK-2",
         "lesson": "checkpoint", "passage": "Recap of John 4 through 6", "focus": "checkpoint",
         "plant": False, "planted": "", "checkpoint": 2, "half_day": False, "project": None,
         "file": "GEN_CHK-2-L1-John-checkpoint-quiz.md"},
        {"date": "2026-11-30", "dow": "Monday", "schedule": "regular", "unit": "Rivers of living water",
         "lesson": "L1", "passage": "John 7:1-13 (ESV)", "focus": "lost brothers", "plant": False,
         "planted": "", "checkpoint": None, "half_day": False, "project": None,
         "file": "GEN_U10-L1-John-7-1-13.md"},
    ],
    "events": [
        {"date": "2026-12-01", "dow": "Tuesday", "schedule": "finals_exam", "kind": "final",
         "label": "Semester final exam window"},
    ],
}


@pytest.fixture
def cal(tmp_path, monkeypatch):
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(CAL), encoding="utf-8")
    monkeypatch.setattr(curriculum, "_CALENDAR", path)
    monkeypatch.setattr(curriculum, "_chicago_today", lambda now_utc=None: date(2026, 11, 5))
    curriculum._schedule.cache_clear()
    yield
    curriculum._schedule.cache_clear()


def run(**args):
    return curriculum.handle("get_course_schedule", args)


def test_tool_is_registered():
    assert "get_course_schedule" in curriculum.HANDLER_NAMES
    # The note describes the tool and never names it, so no name is copied into a reply (decision 0021).
    assert "course-schedule tool" in curriculum.system_note()
    assert "get_course_schedule" not in curriculum.system_note()


def test_today_is_a_lesson_day(cal):
    out = run()
    assert "Today is Thursday, November 5, 2026" in out
    assert "## Thursday, November 5, 2026 (today)" in out
    assert "Unit 9: Bread of Life**, lesson 1 of 2" in out
    assert "John 6:1-15 (ESV)" in out and "five loaves" in out
    assert "New memory verse: John 6:35" in out
    assert "Next lesson: Friday, November 6, 2026" in out


def test_another_date_is_looked_up(cal):
    out = run(date="2026-11-06")
    assert "## Friday, November 6, 2026 (tomorrow)" in out
    assert "lesson 2 of 2" in out and "A quarter project is due" in out


def test_lesson_file_names_are_never_shown(cal):
    for args in ({}, {"date": "2026-11-09"}, {"date": "2026-11-20"}, {"view": "week"}):
        out = run(**args)
        assert "GEN_" not in out and ".md" not in out


def test_checkpoint_day(cal):
    out = run(date="2026-11-09")
    assert "**Checkpoint 2**" in out and "Recap of John 4 through 6" in out


def test_weekend_gives_no_lesson_and_the_neighbors(cal):
    out = run(date="2026-11-07")
    assert "No John lesson is scheduled. It is a weekend." in out
    assert "Most recent lesson: Friday, November 6, 2026" in out
    assert "Next lesson: Monday, November 9, 2026" in out


def test_break_names_the_whole_gap(cal):
    out = run(date="2026-11-20")
    assert "No John lesson is scheduled." in out
    assert "from Tuesday, November 10, 2026 through Sunday, November 29, 2026" in out
    assert "Next lesson: Monday, November 30, 2026. Unit 10: Rivers of living water" in out


def test_event_day(cal):
    out = run(date="2026-12-01")
    assert "No John lesson is scheduled. On the calendar: Final exam: Semester final exam window." in out


def test_before_the_course(cal):
    out = run(date="2026-08-01")
    assert "has not started yet. The first lesson is Thursday, November 5, 2026." in out
    assert "Next lesson: Thursday, November 5, 2026" in out
    assert "Most recent lesson" not in out


def test_after_the_course(cal):
    out = run(date="2027-06-10")
    assert "lessons are over" in out and "Monday, November 30, 2026" in out
    assert "Next lesson" not in out


def test_week_view(cal):
    out = run(date="2026-11-04", view="week")
    assert "## Week of Monday, November 2, 2026" in out
    assert "**Mon Nov 2**: no class" in out
    assert "**Thu Nov 5** (today): Unit 9: Bread of Life, lesson 1 of 2" in out


@pytest.mark.parametrize("bad", ["next tuesday", "2026-02-30", "11/05/2026", 20261105, "2026-13-01"])
def test_bad_date_is_a_plain_message(cal, bad):
    out = run(date=bad)
    assert isinstance(out, str) and "could not be read" in out and "YYYY-MM-DD" in out


def test_bad_view_is_a_plain_message(cal):
    assert "is not available" in run(view="month")


def test_missing_calendar_is_a_plain_message(tmp_path, monkeypatch):
    monkeypatch.setattr(curriculum, "_CALENDAR", tmp_path / "missing.json")
    curriculum._schedule.cache_clear()
    try:
        out = run()
    finally:
        curriculum._schedule.cache_clear()
    assert "Today is" in out and "unavailable" in out


@pytest.mark.parametrize("utc, expected", [
    (datetime(2026, 11, 2, 5, 30, tzinfo=timezone.utc), date(2026, 11, 1)),   # CST, after fall-back
    (datetime(2026, 7, 1, 4, 0, tzinfo=timezone.utc), date(2026, 6, 30)),     # CDT
    (datetime(2026, 11, 2, 6, 30, tzinfo=timezone.utc), date(2026, 11, 2)),
])
def test_chicago_date_without_a_tz_database(monkeypatch, utc, expected):
    monkeypatch.setattr(curriculum, "_chicago_tz", lambda: None)
    assert curriculum._chicago_today(utc) == expected


def test_the_real_calendar_loads():
    curriculum._schedule.cache_clear()
    sch = curriculum._schedule()
    assert sch is not None and sch["dates"]
    out = run(date=sch["dates"][0])
    assert "No John lesson" not in out and "**" in out
