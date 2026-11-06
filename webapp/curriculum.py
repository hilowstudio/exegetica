"""
Student-facing John curriculum tools for the chat.

Exposes the course's *student* materials — the per-unit reading guides, the four
quarter project guides, and the memory-verse master sheet — as MCP-style tools
the Theologian/Assistant can call to answer questions from the actual documents
instead of from memory.

STUDENT-FACING ONLY. These handlers read a fixed whitelist of files under
docs/john-materials/, addressed by validated integers (unit / quarter). They
never touch the teacher guides (docs/john-lessons/), any *_TEACHER-KEY file, the
daily-page answer content, or anything outside the materials directory — there is
no path passed in from the model, so there is no traversal surface.

The one exception is get_course_schedule, which reads docs/john-course-calendar.json
(the same calendar the public /calendar page shows) and reports today's Chicago date
with the day's unit, lesson, passage, and focus. It names no lesson file.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

_MATERIALS = Path(__file__).resolve().parent.parent / "docs" / "john-materials"
_MEMORY_MASTER = _MATERIALS / "GEN_memory-master.md"
# The authoritative course calendar (built from the finished lessons by
# scripts/build_course_calendar.py). Each lesson row names its teacher lesson file; the
# schedule tool reads that name only for the unit number and never shows it.
_CALENDAR = _MATERIALS.parent / "john-course-calendar.json"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _first(m: re.Match | None) -> str:
    return m.group(1).strip() if m else ""


def _guide_meta(text: str) -> tuple[str, str]:
    """Extract (passage, memory_verse) from a reading guide's header, tolerating the
    three header styles in use: 'Passage range:', bold '**Passage range:**', and
    'Passage:' with 'New memory verse:' / 'Memory work:' (review-only) lines."""
    flat = text.replace("**", "")
    pm = re.search(r"^>\s*(?:Passage range|Passages|Passage)\s*:\s*([^\n(]+?)\s*(?:\(|$)", flat, re.M | re.I)
    passage = pm.group(1).strip() if pm else ""
    verse = ""
    vm = re.search(r"^>\s*(?:New memory verse|Memory verse)\s*:\s*([^\n]+)$", flat, re.M | re.I)
    if vm:  # only a real John reference counts (a review-only 'Memory work:' line has none)
        jm = re.search(r"John\s+\d+:\d+(?:[–\-]\d+)?", vm.group(1))
        verse = jm.group(0) if jm else ""
    return passage, verse


def _as_int(v) -> int | None:
    """Coerce a model-supplied value ('5', 5, 'Unit 5', 'U5') to an int, or None."""
    if v is None:
        return None
    digits = re.sub(r"\D", "", str(v))
    return int(digits) if digits else None


# --------------------------------------------------------------------------
# Manifest (scanned once at import; the corpus is small and never changes)
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _reading_guides() -> dict[int, dict]:
    out: dict[int, dict] = {}
    for p in sorted(_MATERIALS.glob("GEN_U*_reading-guide.md")):
        fm = re.match(r"GEN_U(\d+)_reading-guide\.md$", p.name)
        if not fm:
            continue
        unit = int(fm.group(1))
        text = _read(p)
        passage, verse = _guide_meta(text)
        out[unit] = {
            "unit": unit,
            "title": _first(re.search(r"^#\s*Reading guide,\s*Unit\s*\d+:\s*(.+)$", text, re.M)),
            "passage": passage,
            "memory_verse": verse,
            "text": text,
        }
    return out


@lru_cache(maxsize=1)
def _projects() -> dict[int, dict]:
    out: dict[int, dict] = {}
    for p in sorted(_MATERIALS.glob("GEN_project-*-guide.md")):
        text = _read(p)
        m = re.search(r"^#\s*Project guide,\s*Q(\d+):\s*(.+)$", text, re.M)
        if not m:
            continue
        q = int(m.group(1))
        out[q] = {"quarter": q, "title": m.group(2).strip(), "text": text}
    return out


@lru_cache(maxsize=1)
def _memory_unit_map() -> dict[int, str]:
    """Unit -> the memory verse it introduces, parsed from the master's schedule table."""
    try:
        text = _read(_MEMORY_MASTER)
    except OSError:
        return {}
    out: dict[int, str] = {}
    for um, ref in re.findall(r"^\|\s*U(\d+)\s*\|\s*(John\s[0-9:–\-]+)\s*\|", text, re.M):
        out[int(um)] = ref.strip()
    return out


# --------------------------------------------------------------------------
# Tool schemas (Anthropic tool-dict shape; the providers layer adapts these
# to OpenAI/Gemini/Grok function tools automatically)
# --------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "list_john_curriculum",
        "description": (
            "Call first when a student asks what readings, projects or memory verses the Sophomore "
            "Bible course on the Gospel of John has, or to find which unit covers a passage or "
            "topic before fetching it. Lists every unit reading guide with its passage and memory "
            "verse, the four quarter projects, and the memory-verse set."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_reading_guide",
        "description": (
            "Call for one unit's student reading guide in the Gospel of John course (units "
            "1-28): its passage, the big question, and the observe, interpret and respond "
            "prompts. If the unit number is unknown, call list_john_curriculum first. For the "
            "unit the class is on now, call get_course_schedule."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"unit": {"type": "integer", "description": "Unit number, 1-28."}},
            "required": ["unit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_project",
        "description": (
            "Call for a quarter project in the Gospel of John course. Returns the student guide "
            "for quarter 1-4: the assignment, what to build, the options, and the due dates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"quarter": {"type": "integer", "description": "Quarter number, 1-4."}},
            "required": ["quarter"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_memory_verses",
        "description": (
            "Call for the Gospel of John course's memory verses. Returns the master sheet: the "
            "16 verses in the order they're learned, which unit introduces each, the "
            "rolling-review schedule, and a context note per verse. Pass a unit to be told which "
            "verse it introduces."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "unit": {"type": "integer", "description": "Optional unit number (0-28) to focus on."}
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_course_schedule",
        "description": (
            "Call whenever a question depends on today's date or on where the class is (\"what "
            "are we reading today?\", \"what unit are we on?\", \"what's next week?\"). Never guess "
            "the date. Returns today's date (Chicago time, the school's time zone) and what the "
            "Gospel of John course calendar has scheduled: the day's unit, lesson, passage, and "
            "focus, or, on a day with no lesson (weekend, break, exam day, before or after the "
            "school year), the most recent and next lessons. Pass a date to look up another day, "
            "and view='week' for that whole school week."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Optional day to look up, as YYYY-MM-DD, or 'today', 'tomorrow', "
                    "'yesterday'. Defaults to today.",
                },
                "view": {
                    "type": "string",
                    "enum": ["day", "week"],
                    "description": "Optional: 'day' (default) or 'week' for Monday-Friday of that week.",
                },
            },
            "additionalProperties": False,
        },
    },
]

HANDLER_NAMES = {t["name"] for t in TOOLS}


# --------------------------------------------------------------------------
# Handlers (all synchronous file reads; return plain text)
# --------------------------------------------------------------------------
def _handle_list(_args: dict) -> str:
    rg, pr = _reading_guides(), _projects()
    lines = ["# Gospel of John — student course materials", "", "## Unit reading guides"]
    for u in sorted(rg):
        g = rg[u]
        row = f"- **Unit {u}: {g['title'] or '(untitled)'}**"
        if g["passage"]:
            row += f" — {g['passage']}"
        if g["memory_verse"]:
            row += f" — memory verse {g['memory_verse']}"
        lines.append(row)
    lines += ["", "## Quarter projects"]
    for q in sorted(pr):
        lines.append(f"- **Project {q}: {pr[q]['title']}**")
    lines += [
        "",
        "## Memory verses",
        "16 verses across the year, in learning order. Call get_memory_verses for the full "
        "sheet (verses, schedule, and context notes).",
        "",
        "Fetch any of these in full with get_reading_guide(unit), get_project(quarter), or "
        "get_memory_verses(unit).",
    ]
    return "\n".join(lines)


def _handle_reading_guide(args: dict) -> str:
    rg = _reading_guides()
    unit = _as_int(args.get("unit"))
    if unit is None or unit not in rg:
        avail = ", ".join(str(u) for u in sorted(rg))
        return (
            f"There is no reading guide for unit {args.get('unit')!r}. "
            f"Available units are: {avail}. (Unit 0 is orientation and has no reading guide.)"
        )
    return rg[unit]["text"]


def _handle_project(args: dict) -> str:
    pr = _projects()
    q = _as_int(args.get("quarter"))
    if q is None or q not in pr:
        avail = ", ".join(str(k) for k in sorted(pr))
        return f"There is no project for quarter {args.get('quarter')!r}. Available quarters: {avail}."
    return pr[q]["text"]


def _handle_memory(args: dict) -> str:
    try:
        text = _read(_MEMORY_MASTER)
    except OSError:
        return "The memory-verse master sheet is unavailable."
    unit = _as_int(args.get("unit"))
    if unit is None:
        return text
    umap = _memory_unit_map()
    if unit in umap:
        hint = f"Unit {unit} introduces the memory verse **{umap[unit]}**.\n\n"
    else:
        hint = f"Unit {unit} is a review-only unit — it introduces no new memory verse.\n\n"
    return hint + text


# --------------------------------------------------------------------------
# Course schedule. Today's date is computed per call and never written into the
# system prompt: a date there would rewrite the cached prompt prefix every day.
# --------------------------------------------------------------------------
_SCHEDULE_NAMES = {
    "regular": "regular day, 50-minute class",
    "thursday": "Thursday schedule, 36-minute class",
    "half_day": "half day, 26-minute class",
    "finals_exam": "final-exam schedule",
}
_EVENT_NAMES = {"review": "Review day", "final": "Final exam", "tentative": "Flex day (tentative)"}


def _central_offset(now_utc: datetime) -> int:
    """Hours from UTC to Chicago time by the US rule: CDT (-5) from 2 a.m. on the second
    Sunday in March to 2 a.m. on the first Sunday in November, CST (-6) otherwise."""
    y = now_utc.year
    mar1, nov1 = date(y, 3, 1), date(y, 11, 1)
    dst_on = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    dst_off = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    start = datetime(y, 3, dst_on.day, 8, tzinfo=timezone.utc)  # 2:00 CST
    end = datetime(y, 11, dst_off.day, 7, tzinfo=timezone.utc)  # 2:00 CDT
    return -5 if start <= now_utc < end else -6


@lru_cache(maxsize=1)
def _chicago_tz():
    """The system's America/Chicago zone, or None where there is no tz database (Windows
    without the tzdata package)."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Chicago")
    except Exception:  # noqa: BLE001 (ZoneInfoNotFoundError, or no zoneinfo at all)
        return None


def _chicago_today(now_utc: datetime | None = None) -> date:
    """Today's date in Chicago, the school's time zone, at call time."""
    now_utc = now_utc or datetime.now(timezone.utc)
    tz = _chicago_tz()
    if tz is not None:
        return now_utc.astimezone(tz).date()
    return (now_utc + timedelta(hours=_central_offset(now_utc))).date()


@lru_cache(maxsize=1)
def _schedule() -> dict | None:
    """The course calendar, loaded once: lessons and events by date, the sorted lesson
    dates, and the number of numbered lessons in each unit. None if it can't be read."""
    try:
        cal = json.loads(_CALENDAR.read_text(encoding="utf-8"))
        lessons = sorted(cal.get("lessons") or [], key=lambda r: r["date"])
        events: dict[str, list[dict]] = {}
        for e in cal.get("events") or []:
            events.setdefault(e["date"], []).append(e)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if not lessons:
        return None
    return {
        "course": cal.get("course") or "Gospel of John course",
        "lessons": {r["date"]: r for r in lessons},
        "dates": [r["date"] for r in lessons],
        "events": events,
        "per_unit": Counter(r.get("unit") for r in lessons
                            if re.fullmatch(r"L\d+", r.get("lesson") or "")),
    }


def _long(d: date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def _parse_day(raw, today: date) -> date | None:
    """'2026-11-02', 'today', 'tomorrow', 'yesterday', or nothing (today); None if unreadable."""
    s = str(raw).strip().lower() if raw is not None else ""
    rel = {"": 0, "today": 0, "tomorrow": 1, "yesterday": -1}
    if s in rel:
        return today + timedelta(days=rel[s])
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[t ].*)?", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _unit_key(r: dict) -> str:
    """'U9' or 'CHK-2', read from the lesson's file name (the name itself is never shown)."""
    m = re.match(r"(?:GEN_)?(U\d+|CHK-\d+)", r.get("file") or "")
    return m.group(1) if m else ""


def _unit_label(r: dict) -> str:
    key = _unit_key(r)
    if key.startswith("CHK-"):
        return f"Checkpoint {key[4:]}"
    if key:
        return f"Unit {key[1:]}: {r.get('unit') or ''}".rstrip(": ")
    return r.get("unit") or "Lesson"


def _lesson_label(r: dict, per_unit: Counter) -> str:
    m = re.fullmatch(r"L(\d+)", r.get("lesson") or "")
    if not m:
        return ""
    n = per_unit.get(r.get("unit"))
    return f"lesson {m.group(1)} of {n}" if n else f"lesson {m.group(1)}"


def _brief(r: dict, per_unit: Counter) -> str:
    """One line for a lesson: date, unit, lesson, passage."""
    s = f"{_long(date.fromisoformat(r['date']))}. {_unit_label(r)}"
    ll = _lesson_label(r, per_unit)
    if ll:
        s += f", {ll}"
    if r.get("passage"):
        s += f". {r['passage']}"
    return s


def _event_brief(e: dict) -> str:
    kind = _EVENT_NAMES.get(e.get("kind"), "Calendar event")
    return f"{kind}: {e['label']}" if e.get("label") else kind


def _lesson_lines(r: dict, per_unit: Counter) -> list[str]:
    head = f"- **{_unit_label(r)}**"
    ll = _lesson_label(r, per_unit)
    if ll:
        head += f", {ll}"
    lines = [head]
    if r.get("passage"):
        lines.append(f"- Passage: {r['passage']}")
    if r.get("focus"):
        lines.append(f"- Focus: {r['focus']}")
    sched = _SCHEDULE_NAMES.get(r.get("schedule"), r.get("schedule"))
    if sched:
        lines.append(f"- Schedule: {sched}")
    if r.get("plant") and r.get("planted"):
        lines.append(f"- New memory verse: John {r['planted']}")
    if r.get("project") == "intro":
        lines.append("- A quarter project is introduced (get_project has the student project guides).")
    elif r.get("project") == "due":
        lines.append("- A quarter project is due (get_project has the student project guides).")
    key = _unit_key(r)
    if key.startswith("U") and int(key[1:]) in _reading_guides():
        lines.append(f"- This unit's reading guide: get_reading_guide(unit={int(key[1:])})")
    return lines


def _nearest(sch: dict, day: date) -> tuple[dict | None, dict | None]:
    """(most recent lesson before `day`, next lesson after `day`)."""
    iso, dates = day.isoformat(), sch["dates"]
    before = [d for d in dates if d < iso]
    after = [d for d in dates if d > iso]
    return (sch["lessons"][before[-1]] if before else None,
            sch["lessons"][after[0]] if after else None)


def _quiet_run(sch: dict, day: date) -> tuple[date, date]:
    """The run of days around `day` with neither a lesson nor an event (inside the course)."""
    busy = lambda d: d.isoformat() in sch["lessons"] or d.isoformat() in sch["events"]  # noqa: E731
    start = end = day
    while not busy(start - timedelta(days=1)):
        start -= timedelta(days=1)
    while not busy(end + timedelta(days=1)):
        end += timedelta(days=1)
    return start, end


def _day_section(sch: dict, day: date, today: date) -> list[str]:
    rel = {0: " (today)", 1: " (tomorrow)", -1: " (yesterday)"}.get((day - today).days, "")
    lines = [f"## {_long(day)}{rel}"]
    iso, per_unit = day.isoformat(), sch["per_unit"]
    lesson, events = sch["lessons"].get(iso), sch["events"].get(iso, [])

    if lesson:
        lines += _lesson_lines(lesson, per_unit)
        lines += [f"- Also on the calendar: {_event_brief(e)}" for e in events]
        _, nxt = _nearest(sch, day)
        if nxt:
            lines.append(f"- Next lesson: {_brief(nxt, per_unit)}")
        return lines

    first = date.fromisoformat(sch["dates"][0])
    last = date.fromisoformat(sch["dates"][-1])
    prev, nxt = _nearest(sch, day)
    if events:
        why = "On the calendar: " + "; ".join(_event_brief(e) for e in events) + "."
    elif day < first:
        why = f"The course has not started yet. The first lesson is {_long(first)}."
    elif day > last:
        why = f"The course's lessons are over. The last lesson was {_long(last)}."
    else:
        start, end = _quiet_run(sch, day)
        if all(d.weekday() >= 5 for d in (start + timedelta(days=k) for k in range((end - start).days + 1))):
            why = "It is a weekend."
        elif start == end:
            why = "The class does not meet that day."
        else:
            why = f"The class does not meet from {_long(start)} through {_long(end)}."
    lines.append(f"No John lesson is scheduled. {why}")
    if prev:
        lines.append(f"- Most recent lesson: {_brief(prev, per_unit)}")
    if nxt:
        lines.append(f"- Next lesson: {_brief(nxt, per_unit)}")
    # An exam or review day that comes before the next lesson (or after the last one).
    upcoming = sorted(d for d in sch["events"] if d > iso and (nxt is None or d < nxt["date"]))
    if upcoming:
        e = sch["events"][upcoming[0]][0]
        lines.append(f"- Next on the calendar: {_long(date.fromisoformat(upcoming[0]))}. {_event_brief(e)}")
    return lines


def _week_section(sch: dict, day: date, today: date) -> list[str]:
    monday = day - timedelta(days=day.weekday())
    lines = [f"## Week of {_long(monday)}"]
    per_unit, any_lesson = sch["per_unit"], False
    for k in range(5):
        d = monday + timedelta(days=k)
        iso = d.isoformat()
        tag = " (today)" if d == today else ""
        lesson, events = sch["lessons"].get(iso), sch["events"].get(iso, [])
        if lesson:
            any_lesson = True
            row = f"{_unit_label(lesson)}"
            ll = _lesson_label(lesson, per_unit)
            row += f", {ll}" if ll else ""
            row += f". {lesson['passage']}" if lesson.get("passage") else ""
            row += f". Focus: {lesson['focus']}" if lesson.get("focus") else ""
        elif events:
            row = "; ".join(_event_brief(e) for e in events)
        else:
            row = "no class"
        lines.append(f"- **{d:%a} {d:%b} {d.day}**{tag}: {row}")
    if not any_lesson:
        prev, nxt = _nearest(sch, monday)
        if prev:
            lines.append(f"- Most recent lesson: {_brief(prev, per_unit)}")
        after = _nearest(sch, monday + timedelta(days=6))[1]
        if after:
            lines.append(f"- Next lesson: {_brief(after, per_unit)}")
    return lines


def _handle_schedule(args: dict) -> str:
    today = _chicago_today()
    head = f"Today is {_long(today)} (Chicago time, the school's time zone)."
    day = _parse_day(args.get("date"), today)
    if day is None:
        return (f"{head}\n\nThe date {args.get('date')!r} could not be read. Give it as YYYY-MM-DD "
                "(for example 2026-11-02) or as today, tomorrow, or yesterday, or leave it out "
                "for today. For a weekday name, work out its date from today's date above.")
    view = str(args.get("view") or "day").strip().lower()
    if view not in ("day", "week"):
        return f"{head}\n\nThe view {args.get('view')!r} is not available. Use 'day' or 'week'."
    sch = _schedule()
    if sch is None:
        return f"{head}\n\nThe course calendar is unavailable right now."
    body = _week_section(sch, day, today) if view == "week" else _day_section(sch, day, today)
    return "\n".join([head, f"Course calendar: {sch['course']}.", "", *body])


_HANDLERS = {
    "list_john_curriculum": _handle_list,
    "get_reading_guide": _handle_reading_guide,
    "get_project": _handle_project,
    "get_memory_verses": _handle_memory,
    "get_course_schedule": _handle_schedule,
}


def handle(name: str, args: dict) -> str:
    """Dispatch a curriculum tool by name. Raises KeyError if not a curriculum tool."""
    return _HANDLERS[name](args or {})


def system_note() -> str:
    """A block appended to the chat system prompt so the model knows these tools exist.

    It sets no voice or role of its own; the chat's prompt and conduct floor govern how
    replies are written. It treats the course docs only as a source of facts.
    """
    return (
        "\n\n---\n\n"
        "## The Gospel of John course\n"
        "Some questions come from students in a high-school Sophomore Bible course on the "
        "Gospel of John (Yorkville Christian School), asking about a unit's reading guide, one "
        "of the four quarter projects, or the year's memory verses. The course tools answer from "
        "the actual course documents: one lists the units, projects, and memory verses, and others "
        "return a unit's reading guide, a quarter's project, and the memory-verse sheet. You do not "
        "know today's date. When a question depends on it, or on where the class is (today's "
        "reading, the current unit, what comes next), the course-schedule tool returns today's date "
        "and the course calendar for that day or week; use it rather than guessing.\n\n"
        "These answers follow the same rules as every other reply. The course documents are a "
        "source of facts (which passage a unit covers, what a project asks, which verse is "
        "memorized when). Ground your answer in them: quote their specifics (passages, verses, "
        "assignments, due dates) accurately, and never invent one that isn't there. Explain plainly "
        "enough for a sophomore to follow. If someone asks for daily-page answers or a teacher "
        "answer key, say those aren't available here."
    )
