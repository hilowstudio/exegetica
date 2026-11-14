"""A teacher's course (decision 0032): a tree of containers kept in the Prep Room's own table, laid onto a
school calendar.

This module is the logic with no database in it: a calendar's class meetings, laying units and lessons onto
them, pace, Bible passage ranges and their overlap, and which sources feed a container. The routes and the
queries live in `course_routes.py`.

The rules it carries, from the decision:
- Units hold their dates. Each unit takes the next `meetings` class meetings in order; its lessons sit on
  those meetings in order. A class that falls behind compresses the rest of the unit; the unit still ends
  on its date, so pace is "lessons left against meetings left in this unit".
- Making material for a container draws on its own sources and its ancestors' pinned sources, never on
  anything below it.
- A shelf item with a Bible passage attaches itself to each unit and lesson whose passage overlaps it.
  Those automatic sources are not inherited downward (a lesson on 6:25-29 does not pick up every chapter-6
  item through its unit); only pinned sources flow down. The course itself takes pinned sources only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CALENDARS = {"yorkville-2026-27": ROOT / "docs" / "school" / "yorkville_2026-27_calendar.json"}
MINUTES = {"regular": 50, "thursday": 36, "half_day": 26}
KINDS = ("course", "unit", "group", "lesson")


# ------------------------------------------------------------------ the calendar
@dataclass(frozen=True)
class Meeting:
    date: str          # ISO day
    schedule: str      # regular | thursday | half_day
    minutes: int
    tentative: bool = False


@dataclass(frozen=True)
class OffDay:
    date: str
    kind: str          # no_school | no_class | finals
    label: str


@lru_cache(maxsize=8)
def _calendar(key: str) -> dict:
    path = CALENDARS.get(key)
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def meetings(key: str) -> tuple[Meeting, ...]:
    """The class meetings of a school calendar, in order. A tentative day is kept and marked."""
    out = []
    for d in _calendar(key).get("days", []):
        status, sched = d.get("status"), d.get("schedule")
        if status in ("instructional", "half_day") and sched in MINUTES and d.get("period_2_meets") is True:
            out.append(Meeting(d["date"], sched, MINUTES[sched]))
        elif status == "tentative_class" and sched in MINUTES:
            out.append(Meeting(d["date"], sched, MINUTES[sched], tentative=True))
    return tuple(out)


def off_days(key: str) -> tuple[OffDay, ...]:
    """Weekdays without this class: no school, no class, and finals."""
    out = []
    for d in _calendar(key).get("days", []):
        if d.get("status") in ("no_school", "no_class", "finals"):
            label = (d.get("event") or "").strip() or (d.get("flag_reason") or "").split(" (")[0].strip()
            out.append(OffDay(d["date"], d["status"], label))
    return tuple(out)


def term(key: str) -> tuple[str, str] | None:
    cal = _calendar(key)
    return (cal["term_start"], cal["term_end"]) if cal.get("term_start") else None


# ------------------------------------------------------------------ laying the course onto the calendar
def lay(units: list[dict], meets: tuple[Meeting, ...]) -> dict:
    """Place units and their lessons on the meetings, in order.

    `units` is [{"id", "meetings": int, "lessons": [{"id"}, ...]}] in course order. Each unit takes its
    next `meetings` meetings; lesson i sits on the unit's meeting i. Returns
    {"units": {id: {"meetings": [...], "first", "last", "lessons": {lesson_id: Meeting | None},
                    "open": [Meeting], "over": [lesson_id]}},
     "unplanned": [Meeting]}  (meetings after the last unit), and "short" when units ask for more meetings
    than the calendar has."""
    out, i = {}, 0
    for u in units:
        n = max(0, int(u.get("meetings") or 0))
        mine = list(meets[i:i + n])
        i += n
        lessons = u.get("lessons") or []
        placed = {ls["id"]: (mine[k] if k < len(mine) else None) for k, ls in enumerate(lessons)}
        out[u["id"]] = {
            "meetings": mine,
            "first": mine[0].date if mine else None,
            "last": mine[-1].date if mine else None,
            "lessons": placed,
            "open": mine[len(lessons):],
            "over": [ls["id"] for k, ls in enumerate(lessons) if k >= len(mine)],
        }
    return {"units": out, "unplanned": list(meets[i:]), "short": max(0, i - len(meets))}


def pace(unit: dict, laid: dict, today: str) -> dict:
    """Where a unit stands on `today`: lessons taught, lessons left, the unit's meetings left (today counts
    while today's lesson is untaught), and how many lessons behind that leaves it."""
    lessons = unit.get("lessons") or []
    taught = sum(1 for ls in lessons if ls.get("taught_on"))
    left = len(lessons) - taught
    taught_today = any((ls.get("taught_on") or "") == today for ls in lessons)
    meetings_left = sum(1 for m in laid["meetings"] if m.date > today or (m.date == today and not taught_today))
    return {"taught": taught, "left": left, "meetings_left": meetings_left, "behind": max(0, left - meetings_left)}


def next_lesson(units: list[dict]) -> tuple[dict, dict] | None:
    """The first lesson not yet marked taught, with its unit: what the class does next."""
    for u in units:
        for ls in u.get("lessons") or []:
            if not ls.get("taught_on"):
                return u, ls
    return None


def meeting_on(meets: tuple[Meeting, ...], day: str) -> Meeting | None:
    return next((m for m in meets if m.date == day), None)


def today_iso() -> str:
    return date.today().isoformat()


# ------------------------------------------------------------------ Bible passages
_BOOKS = (
    "Genesis Exodus Leviticus Numbers Deuteronomy Joshua Judges Ruth Samuel Kings Chronicles Ezra Nehemiah Esther "
    "Job Psalms Psalm Proverbs Ecclesiastes Song Isaiah Jeremiah Lamentations Ezekiel Daniel Hosea Joel Amos "
    "Obadiah Jonah Micah Nahum Habakkuk Zephaniah Haggai Zechariah Malachi Matthew Mark Luke John Acts Romans "
    "Corinthians Galatians Ephesians Philippians Colossians Thessalonians Timothy Titus Philemon Hebrews James "
    "Peter Jude Revelation"
).split()
_REF = re.compile(
    r"\b(?P<book>(?:[1-3]\s)?(?:" + "|".join(_BOOKS) + r"))\.?\s+(?P<c1>\d{1,3})(?::(?P<v1>\d{1,3})[ab]?)?"
    r"(?:\s*[-–—]\s*(?:(?P<c2>\d{1,3}):)?(?P<x>\d{1,3})[ab]?)?(?![\d:])"
)
_END = 999


@dataclass(frozen=True)
class Passage:
    book: str
    start: tuple[int, int]
    end: tuple[int, int]

    def overlaps(self, other: "Passage | None") -> bool:
        return bool(other) and self.book == other.book and self.start <= other.end and other.start <= self.end

    def __str__(self) -> str:
        (c1, v1), (c2, v2) = self.start, self.end
        if v1 == 1 and v2 == _END:
            return f"{self.book} {c1}" if c1 == c2 else f"{self.book} {c1}-{c2}"
        if c1 == c2:
            return f"{self.book} {c1}:{v1}" + (f"-{v2}" if v2 != v1 else "")
        return f"{self.book} {c1}:{v1}-{c2}:{v2 if v2 != _END else ''}".rstrip(":")


def _from_match(m: re.Match) -> Passage:
    book = re.sub(r"\s+", " ", m["book"])
    book = "Psalms" if book == "Psalm" else book
    c1, v1, c2, x = int(m["c1"]), m["v1"], m["c2"], m["x"]
    if v1 is None:                                  # whole chapters: "John 9", "John 9-10"
        return Passage(book, (c1, 1), (int(x) if x else c1, _END))
    v1 = int(v1)
    if x is None:                                   # one verse
        return Passage(book, (c1, v1), (c1, v1))
    if c2 is None:                                  # same chapter: "John 6:25-29"
        return Passage(book, (c1, v1), (c1, max(v1, int(x))))
    return Passage(book, (c1, v1), (int(c2), int(x)))  # across chapters: "John 7:53-8:11"


def parse_passage(text: str | None) -> Passage | None:
    """The first Bible reference in `text`, or None. Reads labels like "John 6:22–59 · The Bread of Life"
    and titles like "Pictures of Jesus: The Temple of God (John 2:13–25)"."""
    m = _REF.search(text or "")
    return _from_match(m) if m else None


_MORE = re.compile(r"\s*[;,]\s*(?:(?P<c1>\d{1,3}):(?P<v1>\d{1,3})[ab]?|(?P<ch>\d{1,3})(?![\d:]))"
                   r"(?:\s*[-–—]\s*(?:(?P<c2>\d{1,3}):)?(?P<x>\d{1,3})[ab]?)?(?![\d:])")


def parse_passages(text: str | None) -> list[Passage]:
    """Every range in a list like "John 14:16-17, 14:26, 15:26-27" or "John 1:14; 19:35; 21:24"; a range with no
    book name takes the book before it."""
    out, text = [], text or ""
    for m in _REF.finditer(text):
        p = _from_match(m)
        out.append(p)
        j = m.end()
        while (k := _MORE.match(text, j)):
            if k["c1"]:
                c1, v1 = int(k["c1"]), int(k["v1"])
                if k["x"] is None:
                    out.append(Passage(p.book, (c1, v1), (c1, v1)))
                elif k["c2"] is None:
                    out.append(Passage(p.book, (c1, v1), (c1, max(v1, int(k["x"])))))
                else:
                    out.append(Passage(p.book, (c1, v1), (int(k["c2"]), int(k["x"]))))
            else:
                c1 = int(k["ch"])
                out.append(Passage(p.book, (c1, 1), (int(k["x"]) if k["x"] else c1, _END)))
            j = k.end()
    return out


def item_passage(item: dict) -> Passage | None:
    """A shelf item's passage: an exact range when the item carries one (Piper's `dg.from`), else its label."""
    ref = item.get("ref") or {}
    frm = (ref.get("dg") or {}).get("from")
    if isinstance(frm, list) and len(frm) == 4 and all(isinstance(n, int) for n in frm):
        lab = parse_passage(item.get("label"))
        return Passage(lab.book if lab else "John", (frm[0], frm[1]), (frm[2], frm[3]))
    return parse_passage(item.get("label")) or parse_passage(ref.get("title"))


# Kinds of Desiring God item that are talks written down, not articles or devotionals.
TRANSCRIPT_KINDS = ("Sermon", "Message", "Conference message", "Small Talk")


def teacher_source(item: dict) -> bool:
    """A shelf item the teacher prepares from and students never see named: a sermon or teaching transcript,
    or anything shelved for teachers only (Adam, 2026-11-12: "We are building materials using these
    transcripts as source materials"). The teacher's own sermons carry a sermon number; Ligonier lessons
    a series; Desiring God items their kind."""
    ref = item.get("ref") or {}
    return (item.get("audience") == "teachers" or ref.get("sermon") is not None
            or (ref.get("dg") or {}).get("kind") in TRANSCRIPT_KINDS
            or (ref.get("site") == "Ligonier Ministries" and ref.get("series") is not None))


# ------------------------------------------------------------------ what feeds a container
def feeding(chain: list[dict], pinned: dict, shelf: list[dict]) -> dict:
    """The sources that feed the last container in `chain` (root first).

    `pinned` maps container id -> its pinned sources (prep_sources rows as dicts). Returns
    {"own": [...], "above": [...], "passage": [...]} where "above" are ancestors' pinned sources (each
    tagged with the container it comes from) and "passage" the shelf items attached by overlap, minus any
    the teacher removed here."""
    node = chain[-1]
    own = list(pinned.get(node["id"], []))
    above = [dict(s, via=anc.get("title")) for anc in chain[:-1] for s in pinned.get(anc["id"], [])]
    auto = []
    if node.get("kind") != "course":
        here = parse_passages(node.get("passage"))
        hidden = {str(h) for h in node.get("hidden") or []}
        if here:
            auto = [it for it in shelf if str(it.get("id")) not in hidden
                    and (ip := item_passage(it)) and any(h.overlaps(ip) for h in here)]
    return {"own": own, "above": above, "passage": auto}
