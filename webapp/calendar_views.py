"""
Calendar views: a daily and weekly schedule for the Gospel of John course.

Server-rendered like course_views, and it reads the AUTHORITATIVE course calendar
(docs/john/john-course-calendar.json), which is generated from the finished lessons by
scripts/build_course_calendar.py (true to final state, not the pre-generation plan).
Reuses the site chrome and CSS from course_views.
"""
from __future__ import annotations

import datetime as dt
import functools
import json
from pathlib import Path

from webapp.course_views import _crumbs, _page, _u, esc

CAL_PATH = Path(__file__).parent.parent / "docs" / "john" / "john-course-calendar.json"

SCHED = {"regular": "50 min", "thursday": "Thu 36", "half_day": "Half 26",
         "finals_exam": "Final"}
EVENT_TAG = {"review": "Review day", "final": "Final exam", "tentative": "Flex day"}


@functools.lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(CAL_PATH.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _by_date() -> dict[str, dict]:
    """date (iso) -> entry. Lessons and events both keep their own fields; a
    private _type of 'lesson' or 'event' says which (events keep their kind:
    review / final / tentative)."""
    cal = _load()
    out: dict[str, dict] = {}
    for r in cal.get("lessons", []):
        out[r["date"]] = {**r, "_type": "lesson"}
    for e in cal.get("events", []):
        out.setdefault(e["date"], {**e, "_type": "event"})
    return out


def _all_dates() -> list[str]:
    return sorted(_by_date())


@functools.lru_cache(maxsize=1)
def _week_mondays() -> tuple[dt.date, ...]:
    """Mondays of every week that holds at least one lesson or event."""
    mons = set()
    for d in _by_date():
        day = dt.date.fromisoformat(d)
        mons.add(day - dt.timedelta(days=day.weekday()))
    return tuple(sorted(mons))


def _monday_of(date_s: str) -> dt.date:
    d = dt.date.fromisoformat(date_s)
    return d - dt.timedelta(days=d.weekday())


def default_week() -> str:
    """The current week if the term is in session, else the first week."""
    mons = _week_mondays()
    today = dt.date.today()
    today_mon = today - dt.timedelta(days=today.weekday())
    return (today_mon if today_mon in mons else mons[0]).isoformat()


def _sched_label(entry: dict) -> str:
    return SCHED.get(entry.get("schedule"), entry.get("schedule") or "")


def _mode_toggle(date_s: str, mode: str, view: str) -> str:
    """Day / Week switch, styled like the audience toggle."""
    d = "on" if mode == "day" else ""
    w = "on" if mode == "week" else ""
    return (f'<div class="view-toggle" role="group" aria-label="Calendar view">'
            f'<a class="{d}" href="{_u("/calendar/day/" + date_s, view)}">Day</a>'
            f'<a class="{w}" href="{_u("/calendar/week/" + date_s, view)}">Week</a></div>')


def _badges(entry: dict) -> str:
    chips = []
    sl = _sched_label(entry)
    if sl:
        chips.append(f'<span class="chip">{esc(sl)}</span>')
    if entry.get("plant"):
        chips.append(f'<span class="chip avail">plants John {esc(entry.get("planted"))}</span>')
    if entry.get("checkpoint") is not None:
        chips.append('<span class="chip sem">checkpoint</span>')
    if entry.get("project"):
        chips.append(f'<span class="chip sem">project {esc(entry.get("project"))}</span>')
    return f'<div class="cal-badges">{"".join(chips)}</div>' if chips else ""


def _short(entry: dict) -> str:
    if entry["_type"] == "event":
        return (entry.get("label") or EVENT_TAG.get(entry.get("kind"), "Event"))[:44]
    return entry.get("passage") or entry.get("unit", "")


# --------------------------------------------------------------------------- week
def _week_cell(date: dt.date, entry: dict | None, view: str) -> str:
    top = (f'<div class="cal-top"><span class="dow">{date.strftime("%a")}</span>'
           f'<span class="dnum">{date.strftime("%b")} {date.day}</span></div>')
    if entry is None:
        return (f'<div class="cal-day empty-day">{top}<span class="foc">No class</span></div>')
    if entry["_type"] == "event":
        return (f'<div class="cal-day is-event">{top}'
                f'<span class="pass">{esc(EVENT_TAG.get(entry.get("kind"), "Event"))}</span>'
                f'<span class="foc">{esc(entry.get("label") or "")}</span></div>')
    klass = "cal-day is-checkpoint" if entry.get("checkpoint") is not None else "cal-day"
    unit, lesson = entry.get("unit", ""), entry.get("lesson", "")
    unit_lesson = f'{esc(unit)} &middot; {esc(lesson)}' if lesson else esc(unit)
    return (
        f'<a class="{klass}" href="{_u("/calendar/day/" + date.isoformat(), view)}">{top}'
        f'<span class="pass">{esc(entry.get("passage") or "")}</span>'
        f'<span class="foc">{unit_lesson}</span>'
        f'<span class="foc">{esc(entry.get("focus") or "")}</span>'
        f'{_badges(entry)}</a>'
    )


def week(date_s: str, *, view: str, here: str) -> str:
    monday = _monday_of(date_s)
    by, mons = _by_date(), _week_mondays()
    cells = [_week_cell(monday + dt.timedelta(days=off),
                        by.get((monday + dt.timedelta(days=off)).isoformat()), view)
             for off in range(5)]
    grid = f'<div class="cal-week">{"".join(cells)}</div>'
    title = f'Week of {monday.strftime("%B")} {monday.day}, {monday.year}'

    i = mons.index(monday) if monday in mons else \
        min(range(len(mons)), key=lambda k: abs((mons[k] - monday).days))
    prev_a = (f'<a href="{_u("/calendar/week/" + mons[i-1].isoformat(), view)}">'
              f'<span class="dir">Previous</span>Week of {mons[i-1].strftime("%b")} {mons[i-1].day}</a>'
              if i > 0 else "<span></span>")
    next_a = (f'<a href="{_u("/calendar/week/" + mons[i+1].isoformat(), view)}" style="text-align:right">'
              f'<span class="dir">Next</span>Week of {mons[i+1].strftime("%b")} {mons[i+1].day}</a>'
              if i < len(mons) - 1 else "<span></span>")
    pager = f'<div class="pager">{prev_a}{next_a}</div>'

    head = (f'<div class="cal-head"><div><span class="eyebrow">Calendar</span>'
            f'<h1>{esc(title)}</h1></div>{_mode_toggle(date_s, "week", view)}</div>')
    body = (_crumbs([("Calendar", "/calendar"), (title, None)], view)
            + head + grid + pager + _jump(view))
    return _page(f"{title} — Gospel of John", body, here=here, view=view)


def _jump(view: str) -> str:
    """A compact month-grouped list of weeks to jump to."""
    by_month: dict[str, list[dt.date]] = {}
    for m in _week_mondays():
        by_month.setdefault(m.strftime("%B %Y"), []).append(m)
    rows = []
    for label, ms in by_month.items():
        links = " ".join(
            f'<a class="chip" href="{_u("/calendar/week/" + m.isoformat(), view)}">{m.strftime("%b")} {m.day}</a>'
            for m in ms)
        rows.append(f'<div class="cal-jump-row"><span class="cal-jump-mon">{esc(label)}</span>{links}</div>')
    return (f'<section style="margin-top:2.4rem"><span class="eyebrow">Jump to a week</span>'
            f'<div class="cal-jump">{"".join(rows)}</div></section>')


# --------------------------------------------------------------------------- day
def day(date_s: str, *, view: str, here: str) -> str | None:
    by = _by_date()
    entry = by.get(date_s)
    if entry is None:
        return None
    d = dt.date.fromisoformat(date_s)
    long_date = f'{d.strftime("%A")}, {d.strftime("%B")} {d.day}, {d.year}'
    dates = _all_dates()
    idx = dates.index(date_s)

    if entry["_type"] == "event":
        head = (f'<div class="cal-head"><div>'
                f'<span class="eyebrow">{esc(EVENT_TAG.get(entry.get("kind"), "Calendar event"))}</span>'
                f'<h1>{esc(entry.get("label") or EVENT_TAG.get(entry.get("kind"), "Event"))}</h1>'
                f'<p class="lede">{esc(long_date)}</p></div>{_mode_toggle(date_s, "day", view)}</div>')
        blocks = '<p class="empty">No lesson on this day. It is a scheduled calendar event.</p>'
    else:
        unit, lesson = entry.get("unit", ""), entry.get("lesson", "")
        head = (f'<div class="cal-head"><div>'
                f'<span class="eyebrow">{esc(unit)}{(" &middot; " + esc(lesson)) if lesson else ""}</span>'
                f'<h1>{esc(entry.get("passage") or "")}</h1>'
                f'<p class="lede">{esc(long_date)} &middot; {esc(_sched_label(entry))}'
                + (f' &middot; {esc(entry.get("focus"))}' if entry.get("focus") else "")
                + f'</p></div>{_mode_toggle(date_s, "day", view)}</div>')
        verse = ""
        if entry.get("plant"):
            verse = (f'<div class="verse"><span class="ref">Memory verse planted today</span>'
                     f'<div class="txt">John {esc(entry.get("planted"))}</div></div>')
        actions = (f'<div class="toolbar">'
                   f'<a class="btn btn--gold" href="{_u("/course/day/" + date_s, view)}">Open the lesson page</a>'
                   f'</div>')
        marks = _badges(entry)
        blocks = verse + actions + (f'<div style="margin:.4rem 0">{marks}</div>' if marks else "")

    prev_a = (f'<a href="{_u("/calendar/day/" + dates[idx-1], view)}">'
              f'<span class="dir">Previous</span>{esc(_short(by[dates[idx-1]]))}</a>'
              if idx > 0 else "<span></span>")
    next_a = (f'<a href="{_u("/calendar/day/" + dates[idx+1], view)}" style="text-align:right">'
              f'<span class="dir">Next</span>{esc(_short(by[dates[idx+1]]))}</a>'
              if idx < len(dates) - 1 else "<span></span>")
    pager = f'<div class="pager">{prev_a}{next_a}</div>'

    mon = _monday_of(date_s)
    body = (_crumbs([("Calendar", "/calendar"),
                     (f'Week of {mon.strftime("%b")} {mon.day}', "/calendar/week/" + date_s),
                     (f'{d.strftime("%a")} {d.strftime("%b")} {d.day}', None)], view)
            + head + blocks + pager)
    return _page(f"{entry.get('passage') or entry.get('label') or 'Day'} — Gospel of John",
                 body, here=here, view=view)
