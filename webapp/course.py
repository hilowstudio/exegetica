"""
Course publishing layer: turn the generated Markdown into a browsable course.

Reads the authoritative calendar map (docs/john/john-calendar-map.json) and scans the
generated Markdown in docs/john/john-lessons (teacher guides) and docs/john/john-materials
(student + course docs), then builds ONE manifest indexed by day / week / month /
unit / semester with an `audience` tag on every artifact. The Starlette app renders
views over this manifest; the same manifest drives the PDF batch.

Deliberately design-independent: no styling here, just structure + Markdown->HTML.
Audience rule (mirrors the pipeline's STUDENT_FACING notion): everything in
john-lessons and every *_TEACHER-KEY.md is teacher-only; everything else in
john-materials (syllabus, orientation, journals, memory sheets, reading guides)
is student-facing.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
CALENDAR = DOCS / "john" / "john-calendar-map.json"
TEACHER_DIR = DOCS / "john" / "john-lessons"
STUDENT_DIR = DOCS / "john" / "john-materials"

# Friendly titles for the course-level student docs (fallback is the file's H1).
COURSE_DOC_TITLES = {
    "GEN_syllabus": "Syllabus",
    "GEN_how-to-read-john": "How to Read John",
    "GEN_reading-journal-guide": "Reading Journal Guide",
    "GEN_quiet-time-journal-guide": "Quiet-Time Journal Guide",
    "GEN_memory-master": "Memory Verse Master Sheet",
    "GEN_memory-cards": "Memory Verse Flashcards",
}
# Order course docs sensibly on the landing page.
COURSE_DOC_ORDER = list(COURSE_DOC_TITLES)

# The only file stems in john-materials/ that students may open. Everything else there (answer
# keys, both finals, anything added later) is teacher-only until a pattern here says otherwise.
_STUDENT_FILE = re.compile("(?:" + "|".join([
    r"GEN_(?:U\d+|CHK-\d+)_reading-guide",
    r"GEN_(?:U\d+|CHK-\d+)-L\d+_daily-page",
    r"GEN_U\d+_[\w-]+-card",
    r"GEN_project-\d+-[\w-]+-guide",
    r"GEN_review-\d+-[\w-]+-study-guide",
    r"GEN_(?:reading|quiet-time)-journal(?:-guide)?",
    r"U\d+-[\w-]+-reading",
    *(re.escape(stem) for stem in COURSE_DOC_TITLES),
]) + ")")

# Locked unit -> memory-verse reference (the 16-verse anchor set). The full ESV
# text lives in the Memory Verse master sheet; here we surface just the reference
# as a call-out on the unit/day pages.
UNIT_MEMORY_VERSE = {
    "U0": "20:31", "U1": "1:14", "U2": "1:12", "U4": "3:16", "U6": "4:24",
    "U9": "6:35", "U12": "8:12", "U14": "10:11", "U15": "11:25", "U18": "13:34-35",
    "U19": "14:6", "U20": "15:5", "U21": "16:33", "U23": "17:3", "U25": "19:30",
    "U27": "21:17",
}

_md = MarkdownIt("commonmark", {"html": False}).enable("table")


# --------------------------------------------------------------------------- helpers
def _h1(path: Path) -> str | None:
    """The file's first Markdown H1, for display."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
    except OSError:
        return None
    return None


def _unit_key(unit_label: str) -> str:
    """'U2 Witness & first disciples' -> 'U2'; 'CHK-1 chs 1-3' -> 'CHK-1'."""
    return unit_label.split()[0] if unit_label else ""


def _liu_head(lesson_in_unit: str | None) -> int | None:
    """'2/4' -> 2; '' / None -> None."""
    s = (lesson_in_unit or "").strip()
    return int(s.split("/")[0]) if s[:1].isdigit() else None


def render_html(path: Path) -> str:
    """Render a Markdown file to an HTML fragment (no page shell, no styling)."""
    return _md.render(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- scan
def scan_artifacts() -> list[dict]:
    """Parse both docs dirs into artifact records keyed by filename convention."""
    arts: list[dict] = []

    # Teacher lesson guides (john-lessons/): GEN_U2-L2-John-1-35-51.md
    #                                        or hand-built U1-L2_The-Word_John-1-1-5.md
    for p in sorted(TEACHER_DIR.glob("*.md")):
        name = p.name
        rec = {"path": p, "file": name, "audience": "teacher", "kind": "teacher_guide",
               "unit_key": "", "lesson_in_unit": None, "passage_slug": "",
               "title": _h1(p) or p.stem}
        m = (re.match(r"GEN_(U\d+|CHK-\d+)-L(\d+)-John-(.+)\.md$", name)
             or re.match(r"(U\d+|CHK-\d+)-L(\d+)[_-](.+)\.md$", name))
        if m:
            rec.update(unit_key=m.group(1), lesson_in_unit=int(m.group(2)), passage_slug=m.group(3))
        else:
            head = re.match(r"(U\d+|CHK-\d+)", name)
            if head:
                rec["unit_key"] = head.group(1)
        arts.append(rec)

    # Student + course docs (john-materials/). Default-deny: a file is shown to students only
    # if it matches a known student pattern, so a new answer key or exam stays teacher-only.
    for p in sorted(STUDENT_DIR.glob("*.md")):
        name, stem = p.name, p.stem
        if name.endswith("_TEACHER-KEY.md"):
            arts.append({"path": p, "file": name, "audience": "teacher", "kind": "teacher_key",
                         "unit_key": "", "lesson_in_unit": None, "passage_slug": "",
                         "title": _h1(p) or "Teacher Key",
                         "base": stem[: -len("_TEACHER-KEY")]})
            continue
        if not _STUDENT_FILE.fullmatch(stem):
            arts.append({"path": p, "file": name, "audience": "teacher", "kind": "teacher_material",
                         "unit_key": "", "lesson_in_unit": None, "passage_slug": "",
                         "title": _h1(p) or stem, "stem": stem})
            continue
        rg = re.match(r"GEN_(U\d+|CHK-\d+)_reading-guide$", stem)
        if rg:
            arts.append({"path": p, "file": name, "audience": "student", "kind": "reading_guide",
                         "unit_key": rg.group(1), "lesson_in_unit": None, "passage_slug": "",
                         "title": _h1(p) or f"{rg.group(1)} Reading Guide"})
            continue
        arts.append({"path": p, "file": name, "audience": "student", "kind": "course_doc",
                     "unit_key": "", "lesson_in_unit": None, "passage_slug": "",
                     "title": COURSE_DOC_TITLES.get(stem, _h1(p) or stem), "stem": stem})
    return arts


# --------------------------------------------------------------------------- manifest
def build_manifest() -> dict:
    """Fuse the calendar map with the scanned artifacts into one browsable index."""
    cal = json.loads(CALENDAR.read_text(encoding="utf-8"))
    lessons = cal["lessons"]
    arts = scan_artifacts()

    guides_by_unit_lesson: dict[tuple[str, int], list[dict]] = {}
    reading_guide_by_unit: dict[str, dict] = {}
    for a in arts:
        if a["kind"] == "teacher_guide" and a["unit_key"] and a["lesson_in_unit"]:
            guides_by_unit_lesson.setdefault((a["unit_key"], a["lesson_in_unit"]), []).append(a)
        elif a["kind"] == "reading_guide" and a["unit_key"]:
            reading_guide_by_unit[a["unit_key"]] = a

    course_docs = [a for a in arts if a["kind"] == "course_doc"]
    course_docs.sort(key=lambda a: COURSE_DOC_ORDER.index(a["stem"])
                     if a.get("stem") in COURSE_DOC_ORDER else 99)
    teacher_keys = [a for a in arts if a["kind"] == "teacher_key"]

    units: dict[str, dict] = {}
    unit_order: list[str] = []
    days: list[dict] = []
    for r in lessons:
        ukey = _unit_key(r["unit"])
        if ukey not in units:
            units[ukey] = {"key": ukey, "label": r["unit"], "semester": r.get("semester"),
                           "lessons": [], "reading_guide": reading_guide_by_unit.get(ukey),
                           "memory_verse": UNIT_MEMORY_VERSE.get(ukey), "dates": []}
            unit_order.append(ukey)
        head = _liu_head(r.get("lesson_in_unit"))
        d = date.fromisoformat(r["date"])
        iso = d.isocalendar()
        day = {**r, "unit_key": ukey, "lesson_in_unit_head": head,
               "week": f"{iso[0]}-W{iso[1]:02d}", "month": r["date"][:7],
               "memory_verse": UNIT_MEMORY_VERSE.get(ukey),
               "teacher_guides": guides_by_unit_lesson.get((ukey, head), []) if head else [],
               "reading_guide": reading_guide_by_unit.get(ukey)}
        days.append(day)
        units[ukey]["lessons"].append(day)
        units[ukey]["dates"].append(r["date"])

    weeks: dict[str, list[dict]] = {}
    months: dict[str, list[dict]] = {}
    for day in days:
        weeks.setdefault(day["week"], []).append(day)
        months.setdefault(day["month"], []).append(day)

    return {
        "course": cal.get("course"),
        "sections": cal.get("sections"),
        "units": units, "unit_order": unit_order,
        "days": days,
        "weeks": weeks, "months": months,
        "course_docs": course_docs,
        "teacher_keys": teacher_keys,
        "artifacts": arts,
    }


def _summary() -> str:
    m = build_manifest()
    out = [
        f"course : {m['course']}",
        f"totals : units={len(m['unit_order'])} days={len(m['days'])} "
        f"weeks={len(m['weeks'])} months={len(m['months'])}",
        f"student: course_docs={len(m['course_docs'])} "
        f"reading_guides={sum(1 for a in m['artifacts'] if a['kind']=='reading_guide')}",
        f"teacher: guides={sum(1 for a in m['artifacts'] if a['kind']=='teacher_guide')} "
        f"keys={len(m['teacher_keys'])}",
        f"days with a teacher guide attached: {sum(1 for d in m['days'] if d['teacher_guides'])}",
        "first units:",
    ]
    for uk in m["unit_order"][:8]:
        u = m["units"][uk]
        g = sum(1 for d in u["lessons"] if d["teacher_guides"])
        out.append(f"  {uk:6} {u['label'][:32]:32} lessons={len(u['lessons']):2} "
                   f"guides={g} reading_guide={'yes' if u['reading_guide'] else 'no'}")
    return "\n".join(out)


if __name__ == "__main__":
    print(_summary())
