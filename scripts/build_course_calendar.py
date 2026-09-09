"""Build the authoritative John course calendar from the FINISHED lessons.

The calendar is derived from the generated lesson files in docs/john-lessons/
(their embedded Date / Passage / Memory fields), NOT from the pre-generation
planning doc docs/john-calendar-map.json. Dates for the earliest units (U1-U4),
whose generated headers predate the date-in-header convention, are filled from
the real school teaching-day sequence in docs/yorkville_2026-27_calendar.json and
validated against every other lesson's embedded date. This keeps the calendar
true to the final state of the course.

Outputs:
  docs/john-course-calendar.json   machine-readable, one entry per teaching day
  docs/John_Course_Calendar.md     human-readable, grouped by month

Run:  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/build_course_calendar.py
"""
from __future__ import annotations
import re, glob, os, json, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS = os.path.join(ROOT, "docs", "john-lessons")
SCHOOL = os.path.join(ROOT, "docs", "yorkville_2026-27_calendar.json")
OUT_JSON = os.path.join(ROOT, "docs", "john-course-calendar.json")
OUT_MD = os.path.join(ROOT, "docs", "John_Course_Calendar.md")

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# The 16 memory anchors, unit -> (chapter, verse). The plant day is the lesson in
# that unit whose passage range covers the anchor verse.
ANCHORS = {0: (20, 31), 1: (1, 14), 2: (1, 12), 4: (3, 16), 6: (4, 24), 9: (6, 35),
           12: (8, 12), 14: (10, 11), 15: (11, 25), 18: (13, 34), 19: (14, 6),
           20: (15, 5), 21: (16, 33), 23: (17, 3), 25: (19, 30), 27: (21, 17)}

# Marks a lesson whose Memory field actually plants the new verse (phrasing varies by
# generation). Only needed as a fallback where the anchor verse is not in the unit's
# reading passage (John 1:12 is planted in Unit 2, which reads 1:19-51).
STRONG_PLANT = re.compile(
    r"(plant this lesson|plant today|plant and teach|planted today|\bPLANT John)", re.I)


def passage_range(p: str):
    """First ch:v(-[ch:]v) span in a passage string -> (c1, v1, c2, v2) or None."""
    if not p:
        return None
    p = p.replace("–", "-").replace("—", "-")
    m = re.search(r"(\d+):(\d+)\s*(?:-\s*(?:(\d+):)?(\d+))?", p)
    if not m:
        return None
    c1, v1 = int(m[1]), int(m[2])
    c2 = int(m[3]) if m[3] else c1
    v2 = int(m[4]) if m[4] else v1
    return (c1, v1, c2, v2)


def covers(rng, ch: int, v: int) -> bool:
    if not rng:
        return False
    c1, v1, c2, v2 = rng
    if ch < c1 or ch > c2:
        return False
    if c1 == c2:
        return v1 <= v <= v2
    if ch == c1:
        return v >= v1
    if ch == c2:
        return v <= v2
    return True


def passage_from_filename(b: str) -> str:
    """GEN_U3-L1-John-2-1-11.md -> 'John 2:1-11' (fallback when the field is missing)."""
    m = re.search(r"John-(\d+)-(\d+)-(?:(\d+)-)?(\d+)", b)
    if not m:
        return ""
    c1, v1, c2, v2 = m[1], m[2], m[3], m[4]
    return f"John {c1}:{v1}-" + (f"{c2}:{v2}" if c2 else v2)


def load_reading_guides():
    """Clean unit names and per-lesson titles from the finished reading guides."""
    unit_name, titles = {}, {}
    for f in glob.glob(os.path.join(ROOT, "docs", "john-materials", "GEN_U*_reading-guide.md")):
        um = re.search(r"GEN_U(\d+)_", os.path.basename(f))
        if not um:
            continue
        u = int(um[1])
        t = open(f, encoding="utf-8").read()
        h1 = re.search(r"^#\s+Reading guide,\s+Unit\s+\d+:\s+(.+)$", t, re.M)
        if h1:
            unit_name[u] = h1.group(1).strip()
        for m in re.finditer(r"^##\s+Lesson\s+(\d+):\s+(.+?)\s*(?:\(John[^)]*\))?\s*$", t, re.M):
            titles[(u, int(m[1]))] = m.group(2).strip()
    return unit_name, titles


def field(t: str, *names: str):
    for n in names:
        m = re.search(r"^\|\s*\**\s*" + re.escape(n) + r"\s*\**\s*\|\s*(.+?)\s*\|\s*$", t, re.M | re.I)
        if m:
            return m.group(1).strip()
    return None


def parse_date(s: str | None):
    if not s:
        return None
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if iso:
        return dt.date(int(iso[1]), int(iso[2]), int(iso[3]))
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})\b", s)
    if not m:
        return None
    mo = MONTHS[m[1]]
    return dt.date(2026 if mo >= 9 else 2027, mo, int(m[2]))


def lesson_title(t: str) -> str:
    """Fallback focus label: the real phrase after the last ':' or em-dash in the H1, else the Big idea."""
    h1 = re.search(r"^#\s+(.+)$", t, re.M)
    if h1:
        head = h1.group(1)
        for sep in (":", "—"):
            if sep in head:
                tail = head.rsplit(sep, 1)[1].strip()
                tail = re.sub(r"\s*\(John[^)]*\)\s*$", "", tail).strip()
                if tail and not re.match(r"(?i)(teacher|lesson|teaching|guide|copy|\d)", tail):
                    return tail
    big = field(t, "Big idea")
    if big:
        first = re.split(r"(?<=[.!?])\s", big)[0]
        return (first[:80] + "...") if len(first) > 83 else first
    return ""


def load_items():
    unit_name_map, title_map = load_reading_guides()
    unit_name_map.setdefault(0, "Entering John (orientation)")
    items = []
    for f in sorted(glob.glob(os.path.join(LESSONS, "*.md"))):
        b = os.path.basename(f)
        t = open(f, encoding="utf-8").read()
        chk = re.match(r"GEN_CHK-(\d+)", b)
        um = re.search(r"U(\d+)", b)
        lm = re.search(r"-L(\d+)", b)
        unit = -1 if chk else (int(um[1]) if um else 0)
        lesson = 0 if chk else (int(lm[1]) if lm else 0)
        passage = field(t, "Passage") or passage_from_filename(b)
        if chk:
            uname, focus = f"CHK-{chk[1]}", lesson_title(t)
        else:
            uname = unit_name_map.get(unit) or field(t, "Unit") or f"Unit {unit}"
            focus = title_map.get((unit, lesson)) or lesson_title(t)
        items.append(dict(
            file=b,
            unit=unit, lesson=lesson,
            checkpoint=(int(chk[1]) if chk else None),
            unit_name=uname,
            date=parse_date(field(t, "Date / Day type", "Date/Day type", "Date")),
            passage=passage,
            title=focus,
            plant=False, planted="",
            mem=field(t, "Memory verse") or "",
            # a project is introduced/due on ONE lesson; a multi-lesson unit can share the
            # "project-due" filename stem, so confirm the due day from the lesson body.
            project=("intro" if "project-introduced" in b
                     else "due" if ("project-due" in b and (chk or "comes due today" in t.lower()
                                    or "project due)" in t.split(chr(10), 1)[0].lower()))
                     else None),
        ))
    # plant day per anchor: prefer the narrowest lesson passage that covers the anchor
    # verse; fall back to the latest lesson whose Memory field marks the plant.
    def width(it):
        r = passage_range(it["passage"]) or (0, 0, 99, 99)
        return (r[2] - r[0], r[3] - r[1])
    for u, (ch, v) in ANCHORS.items():
        unit_lessons = [it for it in items if it["unit"] == u]
        covering = [it for it in unit_lessons if covers(passage_range(it["passage"]), ch, v)]
        if covering:
            tgt = min(covering, key=width)
        else:
            strong = [it for it in unit_lessons if STRONG_PLANT.search(it["mem"])]
            tgt = max(strong, key=lambda it: it["lesson"]) if strong else None
        if tgt:
            tgt["plant"] = True
            tgt["planted"] = "13:34-35" if u == 18 else f"{ch}:{v}"
    assert sum(it["plant"] for it in items) == len(ANCHORS), \
        f"expected {len(ANCHORS)} plant days, flagged {sum(it['plant'] for it in items)}"
    return items


def load_school():
    cal = json.load(open(SCHOOL, encoding="utf-8"))
    days = {x["date"]: x for x in cal["days"]}
    meet = [dt.date.fromisoformat(x["date"]) for x in cal["days"]
            if x.get("status") in ("instructional", "half_day") and x.get("period_2_meets")]
    return cal, days, sorted(meet)


def main():
    items = load_items()
    cal, days, meet = load_school()
    meet_set = set(meet)

    dated = [it for it in items if it["date"]]
    undated = sorted([it for it in items if not it["date"]], key=lambda it: (it["unit"], it["lesson"]))
    bad = [it for it in dated if it["date"] not in meet_set]
    assert not bad, f"embedded dates off the school calendar: {[(it['file'], str(it['date'])) for it in bad]}"

    taken = {it["date"] for it in dated}
    u0max = max(it["date"] for it in items if it["unit"] == 0 and it["date"])
    first_next = min(it["date"] for it in items if it["unit"] >= 5 and it["date"])
    open_slots = [d for d in meet if u0max < d < first_next and d not in taken]
    assert len(open_slots) == len(undated), \
        f"gap fill mismatch: {len(open_slots)} slots vs {len(undated)} undated lessons"
    for it, d in zip(undated, open_slots):
        it["date"] = d

    all_dates = [it["date"] for it in items]
    assert len(set(all_dates)) == len(items), "duplicate lesson dates"

    # annotate from the authoritative school calendar
    for it in items:
        sc = days.get(it["date"].isoformat(), {})
        it["dow"] = sc.get("day_of_week", it["date"].strftime("%A"))
        it["schedule"] = sc.get("schedule", "regular")
        it["half_day"] = (sc.get("status") == "half_day")

    # non-lesson events (reviews, finals, tentative grad) straight from the school calendar
    span_lo, span_hi = min(all_dates), max(all_dates)
    events = []
    for x in cal["days"]:
        d = dt.date.fromisoformat(x["date"])
        st = x.get("status")
        if st == "finals":
            events.append(dict(date=d, kind="final", label="Semester final exam window",
                               dow=x.get("day_of_week"), schedule=x.get("schedule")))
        elif st == "instructional" and "review day" in (x.get("event") or "").lower():
            events.append(dict(date=d, kind="review", label=x.get("event"),
                               dow=x.get("day_of_week"), schedule=x.get("schedule")))
        elif st == "tentative_class":
            events.append(dict(date=d, kind="tentative", label="Tentative flex day (graduation): pray for the class",
                               dow=x.get("day_of_week"), schedule=x.get("schedule")))

    rows = []
    for it in sorted(items, key=lambda it: it["date"]):
        rows.append(dict(
            date=it["date"].isoformat(), dow=it["dow"], schedule=it["schedule"],
            unit=it["unit_name"] if it["checkpoint"] is None else f"CHK-{it['checkpoint']}",
            lesson=("checkpoint" if it["checkpoint"] is not None
                    else f"L{it['lesson']}" if it["lesson"] else "orientation"),
            passage=it["passage"], focus=it["title"],
            plant=it["plant"], planted=it["planted"],
            checkpoint=it["checkpoint"], half_day=it["half_day"],
            project=it["project"], file=it["file"],
        ))

    out = dict(
        course="Sophomore Bible: The Gospel of John (2026-27)",
        source="Derived from the finished lessons in docs/john-lessons/ (embedded dates), "
               "with U1-U4 gaps filled from docs/yorkville_2026-27_calendar.json and validated. "
               "NOT built from docs/john-calendar-map.json (the pre-generation plan).",
        generated=dt.date.today().isoformat(),
        span=dict(first=span_lo.isoformat(), last=span_hi.isoformat()),
        counts=dict(lessons=len(items), plants=sum(r["plant"] for r in rows),
                    checkpoints=sum(r["checkpoint"] is not None for r in rows),
                    half_days=sum(r["half_day"] for r in rows)),
        lessons=rows,
        events=[dict(date=e["date"].isoformat(), dow=e["dow"], schedule=e["schedule"],
                     kind=e["kind"], label=e["label"]) for e in sorted(events, key=lambda e: e["date"])],
    )
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), indent=2)

    write_md(out)
    print(f"[calendar] {len(items)} lessons {span_lo}..{span_hi}; "
          f"{out['counts']['plants']} plants, {out['counts']['checkpoints']} checkpoints, "
          f"{out['counts']['half_days']} half-days; {len(events)} non-lesson events")
    print(f"[calendar] wrote {os.path.relpath(OUT_JSON, ROOT)} and {os.path.relpath(OUT_MD, ROOT)}")


SCHED_LABEL = {"regular": "50 min", "thursday": "Thu 36", "half_day": "Half 26",
               "finals_exam": "Final", None: ""}


def write_md(out: dict):
    L = []
    L.append("# The Gospel of John: course calendar (2026-27)")
    L.append("")
    L.append("> Sophomore Bible, Yorkville Christian School. **This calendar is generated from the "
             "finished lessons** (`docs/john-lessons/`), so it is true to the course as built, "
             "including every recut passage. Regenerate with `scripts/build_course_calendar.py`.")
    L.append("")
    c = out["counts"]
    L.append(f"> {c['lessons']} lessons, {out['span']['first']} to {out['span']['last']} · "
             f"{c['plants']} memory-verse plants · {c['checkpoints']} checkpoints · "
             f"{c['half_days']} half-days · 2 review days + 2 final windows.")
    L.append("")
    L.append("Legend: **[P]** memory-verse plant day (the verse follows) · **[CHK]** checkpoint quiz · "
             "**[proj]** project introduced or due · half-days and Thursdays are single-focus short periods.")
    L.append("")

    def fmtd(datestr):
        d = dt.date.fromisoformat(datestr)
        return d.strftime("%a ") + str(d.day) + " " + d.strftime("%b")

    L.append("## At a glance")
    L.append("")
    plants = [r for r in out["lessons"] if r["plant"]]
    L.append(f"**Memory-verse plants ({len(plants)}):** " + " · ".join(
        f"{fmtd(r['date'])} John {r['planted']}" for r in plants))
    L.append("")
    chks = [r for r in out["lessons"] if r["checkpoint"] is not None]
    L.append("**Checkpoints (4):** " + " · ".join(f"{fmtd(r['date'])} {r['unit']} ({r['passage']})" for r in chks))
    L.append("")
    projs = [r for r in out["lessons"] if r["project"]]
    L.append("**Project milestones:** " + " · ".join(
        f"{fmtd(r['date'])} {r['project']} ({r['focus']})" for r in projs))
    L.append("")
    halfs = [r for r in out["lessons"] if r["half_day"]]
    L.append("**Half-days (26 min):** " + " · ".join(f"{fmtd(r['date'])} {r['unit']} {r['lesson']}" for r in halfs))
    L.append("")
    revs = [e for e in out["events"] if e["kind"] == "review"]
    fins = [e for e in out["events"] if e["kind"] == "final"]
    fin_spans = f"{fmtd(fins[0]['date'])} to {fmtd(fins[3]['date'])} and {fmtd(fins[4]['date'])} to {fmtd(fins[7]['date'])}" if len(fins) == 8 else ""
    L.append("**Reviews and finals:** review " + " · ".join(fmtd(e["date"]) for e in revs)
             + f"; final exam windows {fin_spans}.")
    L.append("")

    # merge lessons + events into one date-ordered stream, grouped by month
    stream = []
    for r in out["lessons"]:
        stream.append((r["date"], "lesson", r))
    for e in out["events"]:
        stream.append((e["date"], "event", e))
    stream.sort(key=lambda x: (x[0], x[1] != "event"))

    cur_month = None
    for datestr, kind, r in stream:
        d = dt.date.fromisoformat(datestr)
        mk = d.strftime("%B %Y")
        if mk != cur_month:
            if cur_month is not None:
                L.append("")
            cur_month = mk
            L.append(f"## {mk}")
            L.append("")
            L.append("| Date | Day | Len | Unit | Lesson | Passage | Focus | |")
            L.append("|---|---|---|---|---|---|---|---|")
        day = d.strftime("%a %-d") if os.name != "nt" else d.strftime("%a ") + str(d.day)
        if kind == "event":
            tag = {"final": "FINAL", "review": "REVIEW", "tentative": "flex"}.get(r["kind"], r["kind"])
            L.append(f"| {day} | {r['dow'][:3]} | {SCHED_LABEL.get(r['schedule'], r['schedule'] or '')} | "
                     f"**{tag}** | | | {r['label']} | |")
            continue
        marks = []
        if r["plant"]:
            marks.append(f"[P {r['planted']}]")
        if r["checkpoint"] is not None:
            marks.append("[CHK]")
        if r["project"]:
            marks.append(f"[proj {r['project']}]")
        unit = r["unit"]
        lesson = r["lesson"]
        L.append(f"| {day} | {r['dow'][:3]} | {SCHED_LABEL.get(r['schedule'], r['schedule'] or '')} | "
                 f"{unit} | {lesson} | {r['passage']} | {r['focus']} | {' '.join(marks)} |")
    L.append("")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    main()
