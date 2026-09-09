"""
HTML views over the course manifest (see course.py). Server-rendered, no template
engine — small string builders keyed to the classes in static/course.css.

Audience gating: `view` is "student" (default) or "teacher". Teacher-only artifacts
(lesson guides, answer keys) are hidden in the student view and refused by the doc
route. NOTE: this is presentation-level gating for a local/trusted teacher tool. If
this app is ever hosted for students/parents, the teacher view MUST be put behind
real authentication before exposure.
"""
from __future__ import annotations

import html
from datetime import date as _date

from webapp import course

esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731

DAY_TYPE = {"regular": "Regular", "thursday": "Thursday", "half_day": "Half day",
            "review": "Review", "final": "Final"}


# --------------------------------------------------------------------------- bits
def _u(path: str, view: str) -> str:
    """Internal link that preserves the teacher view."""
    return f"{path}?view=teacher" if view == "teacher" else path


def _crest() -> str:
    return (
        '<svg class="crest" viewBox="0 0 30 34" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        '<path d="M15 1 L28 5 V16 C28 25 22 30 15 33 C8 30 2 25 2 16 V5 Z" '
        'fill="#131e3a" stroke="#f5b301" stroke-width="1.5"/>'
        '<text x="15" y="23" text-anchor="middle" font-family="Georgia, serif" '
        'font-size="16" fill="#f5b301">J</text></svg>'
    )


def _toggle(here: str, view: str) -> str:
    s = "on" if view == "student" else ""
    t = "on" if view == "teacher" else ""
    return (f'<div class="view-toggle" role="group" aria-label="Audience view">'
            f'<a class="{s}" href="{esc(here)}?view=student">Student</a>'
            f'<a class="{t}" href="{esc(here)}?view=teacher">Teacher</a></div>')


def _header(here: str, view: str) -> str:
    nav = (f'<a href="{_u("/course", view)}">Overview</a>'
           f'<a href="{_u("/course", view)}#units">Units</a>'
           f'<a href="{_u("/calendar", view)}">Calendar</a>')
    return (f'<header class="site-header"><div class="bar">'
            f'<a class="brand-mark" href="{_u("/course", view)}">{_crest()}'
            f'<span class="wordmark"><b>Gospel of John</b><span>Sophomore Bible</span></span></a>'
            f'<nav class="site-nav">{nav}{_toggle(here, view)}</nav></div></header>')


def _crumbs(items: list[tuple[str, str | None]], view: str) -> str:
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{_u(href, view)}">{esc(label)}</a>')
        else:
            parts.append(f"<span>{esc(label)}</span>")
    return '<nav class="crumbs">' + '<span class="sep">/</span>'.join(parts) + "</nav>"


def _page(title: str, body: str, *, here: str, view: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{esc(title)}</title>"
        "<link rel=\"stylesheet\" href=\"/static/fonts.css\">"
        "<link rel=\"stylesheet\" href=\"/static/course.css\">"
        "</head><body>"
        f"{_header(here, view)}<main>{body}</main>"
        "<footer class=\"site-footer\"><div class=\"bar\">"
        "<span>The Gospel of John &middot; Sophomore Bible &middot; 2026–27</span>"
        "<span>Yorkville Christian School</span></div></footer>"
        "</body></html>"
    )


def _fmt_date(iso: str, long: bool = False) -> str:
    d = _date.fromisoformat(iso)
    if long:
        return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}"
    return f"{d.strftime('%a')} {d.strftime('%b')} {d.day}"


def _week_label(week_key: str) -> str:
    y, w = week_key.split("-W")
    mon = _date.fromisocalendar(int(y), int(w), 1)
    return f"Week of {mon.strftime('%B')} {mon.day}, {mon.year}"


def _month_label(mk: str) -> str:
    d = _date.fromisoformat(mk + "-01")
    return f"{d.strftime('%B')} {d.year}"


def _verse_callout(ref: str | None, memory_file: str | None, view: str) -> str:
    if not ref:
        return ""
    inner = f'<span class="ref">Unit memory verse</span><div class="txt">John {esc(ref)}</div>'
    if memory_file:
        inner += (f'<div style="margin-top:.4rem"><a href="'
                  f'{_u("/course/doc/" + memory_file, view)}">Full text &amp; schedule &rarr;</a></div>')
    return f'<div class="verse">{inner}</div>'


def _memory_file(m: dict) -> str | None:
    for a in m["course_docs"]:
        if a.get("stem") == "GEN_memory-master":
            return a["file"]
    return None


def _lesson_row(m: dict, day: dict, view: str) -> str:
    date_s = day["date"]
    passage = day.get("passage") or ""
    dtype = DAY_TYPE.get(day.get("day_type", ""), (day.get("day_type") or "").title())
    role = day.get("role", "")
    # availability chip
    if view == "teacher":
        avail = bool(day["teacher_guides"])
        chip = ('<span class="chip avail">guide</span>' if avail
                else '<span class="chip pending">pending</span>')
    else:
        avail = bool(day.get("reading_guide"))
        chip = ('<span class="chip avail">reading guide</span>' if avail
                else '<span class="chip pending">in class</span>')
    cls = "lesson-row"
    if role == "checkpoint":
        cls += " is-checkpoint"
    elif role in ("review", "final"):
        cls += " is-review"
    return (
        f'<a class="{cls}" href="{_u("/course/day/" + date_s, view)}">'
        f'<span class="num">{day.get("i", "")}</span>'
        f'<span><span class="ttl">{esc(passage)}</span><br>'
        f'<span class="sub">{esc(_fmt_date(date_s))} &middot; {esc(dtype)}</span></span>'
        f'<span class="sub rt">{chip}</span></a>'
    )


# --------------------------------------------------------------------------- views
def overview(m: dict, *, view: str, here: str) -> str:
    days = m["days"]
    span = f"{_fmt_date(days[0]['date'])} &ndash; {_fmt_date(days[-1]['date'], )}" if days else ""
    mem = _memory_file(m)

    # start-here course docs
    cards = []
    for a in m["course_docs"]:
        cards.append(
            f'<a class="card" href="{_u("/course/doc/" + a["file"], view)}">'
            f'<h3>{esc(a["title"])}</h3>'
            f'<span class="meta">Student handout</span></a>')
    start = ('<section><span class="eyebrow">Start here</span>'
             '<h2>Course materials</h2>'
             f'<div class="grid cols">{"".join(cards) or "<p class=empty>None generated yet.</p>"}</div>'
             '</section>')

    # units
    ucards = []
    for uk in m["unit_order"]:
        u = m["units"][uk]
        dates = u["dates"]
        rng = f"{_fmt_date(dates[0])} &ndash; {_fmt_date(dates[-1])}" if dates else ""
        if view == "teacher":
            have = sum(1 for d in u["lessons"] if d["teacher_guides"])
            need = len(u["lessons"])
            chip = (f'<span class="chip avail">{have}/{need} guides</span>' if have
                    else f'<span class="chip pending">{need} to build</span>')
        else:
            chip = ('<span class="chip avail">reading guide</span>' if u["reading_guide"]
                    else '<span class="chip pending">reading guide pending</span>')
        mv = f'<span class="chip sem">John {esc(u["memory_verse"])}</span>' if u.get("memory_verse") else ""
        ucards.append(
            f'<a class="card" href="{_u("/course/unit/" + uk, view)}">'
            f'<span class="eyebrow">{esc(uk)}</span>'
            f'<h3>{esc(u["label"].split(" ", 1)[1] if " " in u["label"] else u["label"])}</h3>'
            f'<span class="meta">{rng} &middot; {len(u["lessons"])} lesson(s)</span>'
            f'<div style="margin-top:.5rem;display:flex;gap:.4rem;flex-wrap:wrap">{chip}{mv}</div></a>')
    units = (f'<section id="units"><span class="eyebrow">The year</span>'
             f'<h2>Units</h2><div class="grid cols">{"".join(ucards)}</div></section>')

    # calendar (months)
    mrows = []
    for mk in sorted(m["months"]):
        ds = m["months"][mk]
        mrows.append(
            f'<a class="lesson-row" href="{_u("/course/month/" + mk, view)}">'
            f'<span class="num">&#128197;</span>'
            f'<span class="ttl">{esc(_month_label(mk))}</span>'
            f'<span class="sub rt">{len(ds)} lesson(s)</span></a>')
    cal = (f'<section id="calendar" style="margin-top:2.4rem"><span class="eyebrow">Calendar</span>'
           f'<h2>Browse by month</h2><div class="lessons">{"".join(mrows)}</div></section>')

    hero = (f'<span class="eyebrow">{esc(m.get("course", ""))}</span>'
            f'<h1>The Gospel of John</h1>'
            f'<p class="lede">A full-year, verse-by-verse study for sophomores. '
            f'{len(days)} lessons across {span}. Two sections, one curriculum.</p>')
    tflag = ('<div class="teacher-flag">Teacher view &mdash; lesson guides and answer keys are visible. '
             'Switch to Student to see only what students and parents see.</div>' if view == "teacher" else "")
    body = _crumbs([("Overview", None)], view) + hero + tflag + start + units + cal
    _ = mem
    return _page("The Gospel of John — Sophomore Bible", body, here=here, view=view)


def unit(m: dict, key: str, *, view: str, here: str) -> str | None:
    u = m["units"].get(key)
    if not u:
        return None
    dates = u["dates"]
    rng = f"{_fmt_date(dates[0], True)} &ndash; {_fmt_date(dates[-1], True)}" if dates else ""
    name = u["label"].split(" ", 1)[1] if " " in u["label"] else u["label"]
    head = (f'<span class="eyebrow">{esc(key)} &middot; Semester {u.get("semester", "")}</span>'
            f'<h1>{esc(name)}</h1>'
            f'<p class="lede">{rng} &middot; {len(u["lessons"])} lesson(s).</p>')
    verse = _verse_callout(u.get("memory_verse"), _memory_file(m), view)

    # student: the unit reading guide (one per unit)
    rg = u.get("reading_guide")
    if view != "teacher":
        if rg:
            rg_block = (f'<div class="card" style="margin:1.4rem 0"><h3>Reading guide</h3>'
                        f'<p class="meta">Follow along across this unit’s lessons.</p>'
                        f'<a class="btn btn--gold" href="{_u("/course/doc/" + rg["file"], view)}" '
                        f'style="align-self:flex-start">Open reading guide</a></div>')
        else:
            rg_block = '<p class="empty">The reading guide for this unit hasn’t been generated yet.</p>'
    else:
        rg_block = ""

    rows = "".join(_lesson_row(m, d, view) for d in u["lessons"])
    lessons = f'<section><h2>Lessons</h2><div class="lessons">{rows}</div></section>'

    body = (_crumbs([("Overview", "/course"), (key, None)], view)
            + head + verse + rg_block + lessons)
    return _page(f"{name} — Gospel of John", body, here=here, view=view)


def day(m: dict, date_s: str, *, view: str, here: str) -> str | None:
    days = m["days"]
    idx = next((i for i, d in enumerate(days) if d["date"] == date_s), None)
    if idx is None:
        return None
    d = days[idx]
    u = m["units"].get(d["unit_key"], {})
    dtype = DAY_TYPE.get(d.get("day_type", ""), (d.get("day_type") or "").title())
    head = (f'<span class="eyebrow">Lesson {d.get("i", "")} of {len(days)} &middot; {esc(d["unit"])}</span>'
            f'<h1>{esc(d.get("passage") or "")}</h1>'
            f'<p class="lede">{_fmt_date(date_s, True)} &middot; {esc(dtype)}'
            + (f' &middot; {esc(d.get("role", ""))}' if d.get("role") else "") + "</p>")
    verse = _verse_callout(d.get("memory_verse"), _memory_file(m), view)

    blocks = ""
    if view == "teacher":
        if d["teacher_guides"]:
            for g in d["teacher_guides"]:
                blocks += (f'<div class="toolbar"><button class="btn" onclick="window.print()">'
                           f'Print / Save as PDF</button>'
                           f'<a class="btn" href="{_u("/course/doc/" + g["file"], view)}">Open full page</a></div>')
                blocks += f'<article class="doc">{course.render_html(g["path"])}</article>'
        else:
            blocks = '<p class="empty">The teacher lesson guide for this day hasn’t been generated yet.</p>'
    else:
        rg = d.get("reading_guide")
        if rg:
            blocks = (f'<div class="card"><h3>Reading guide</h3>'
                      f'<p class="meta">This lesson is part of {esc(d["unit"])}. Use the unit reading guide.</p>'
                      f'<a class="btn btn--gold" href="{_u("/course/doc/" + rg["file"], view)}" '
                      f'style="align-self:flex-start">Open reading guide</a></div>')
        else:
            blocks = ('<p class="empty">Work from your Reading Journal and the class discussion. '
                      'A unit reading guide will appear here once it’s ready.</p>')

    # pager
    prev_a = (f'<a href="{_u("/course/day/" + days[idx-1]["date"], view)}">'
              f'<span class="dir">Previous</span>{esc(days[idx-1].get("passage") or "")}</a>'
              if idx > 0 else "<span></span>")
    next_a = (f'<a href="{_u("/course/day/" + days[idx+1]["date"], view)}" style="text-align:right">'
              f'<span class="dir">Next</span>{esc(days[idx+1].get("passage") or "")}</a>'
              if idx < len(days) - 1 else "<span></span>")
    pager = f'<div class="pager">{prev_a}{next_a}</div>'

    body = (_crumbs([("Overview", "/course"), (d["unit_key"], "/course/unit/" + d["unit_key"]),
                     (_fmt_date(date_s), None)], view)
            + head + verse + blocks + pager)
    return _page(f"{d.get('passage') or 'Lesson'} — Gospel of John", body, here=here, view=view)


def _day_listing(m: dict, ds: list[dict], title: str, crumb_label: str, *, view: str, here: str) -> str:
    rows = "".join(_lesson_row(m, d, view) for d in ds)
    body = (_crumbs([("Overview", "/course"), ("Calendar", "/course#calendar"), (crumb_label, None)], view)
            + f'<h1>{esc(title)}</h1><div class="lessons">{rows or "<p class=empty>No lessons.</p>"}</div>')
    return _page(f"{title} — Gospel of John", body, here=here, view=view)


def week(m: dict, key: str, *, view: str, here: str) -> str | None:
    ds = m["weeks"].get(key)
    if not ds:
        return None
    return _day_listing(m, ds, _week_label(key), _week_label(key), view=view, here=here)


def month(m: dict, key: str, *, view: str, here: str) -> str | None:
    ds = m["months"].get(key)
    if not ds:
        return None
    return _day_listing(m, ds, _month_label(key), _month_label(key), view=view, here=here)


def find_artifact(m: dict, file: str) -> dict | None:
    return next((a for a in m["artifacts"] if a["file"] == file), None)


def doc(m: dict, art: dict, *, view: str, here: str) -> str:
    crumbs = [("Overview", "/course")]
    if art.get("unit_key"):
        crumbs.append((art["unit_key"], "/course/unit/" + art["unit_key"]))
    crumbs.append((art["title"], None))
    toolbar = ('<div class="toolbar"><button class="btn btn--gold" onclick="window.print()">'
               'Print / Save as PDF</button></div>')
    body = (_crumbs(crumbs, view) + toolbar
            + f'<article class="doc">{course.render_html(art["path"])}</article>')
    return _page(f"{art['title']} — Gospel of John", body, here=here, view=view)


def not_found(msg: str, *, view: str, here: str) -> str:
    body = _crumbs([("Overview", "/course")], view) + f'<h1>Not found</h1><p class="empty">{esc(msg)}</p>'
    return _page("Not found", body, here=here, view=view)


def forbidden(*, view: str, here: str) -> str:
    body = (_crumbs([("Overview", "/course")], view)
            + '<h1>Teacher material</h1>'
            '<p class="empty">This is a teacher guide or answer key. Switch to the Teacher view to open it.</p>')
    return _page("Teacher material", body, here=here, view=view)
