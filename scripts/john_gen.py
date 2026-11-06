#!/usr/bin/env python3
"""John course: the generation pipeline.

One sturdy, tool-grounded path that produces every artifact the course needs -
teacher lesson guides, per-unit student reading guides, the student-devotional
template, and the course-level documents - by driving the REAL app loop
(providers.run over the co-located Study Bible MCP server). Every Scripture
quotation is ESV, fetched and checked through the tools; the facts are pinned
from the calendar map; the course's design invariants ride on every job.

Sturdiness: one MCP bridge is reused across a batch; each job is idempotent
(skips an existing output unless --force); a failed or too-short generation
retries once and is never written as a broken file; every run is appended to a
JSONL log. Use --dry-run to assemble and inspect a job without an API call.

Usage:
  python -m scripts.john_gen lesson --index 8
  python -m scripts.john_gen reading-guide --unit U2
  python -m scripts.john_gen devotional --passage 1:35-51
  python -m scripts.john_gen course --doc how-to-read-john
  python -m scripts.john_gen course --all
  flags: --dry-run  --force  --no-sermon
"""
import argparse
import asyncio
import json
import re
import time
from itertools import groupby
from pathlib import Path

from webapp import generator, providers
from webapp.app import MCPBridge, MODEL, PROJECT_ROOT

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

DOCS = PROJECT_ROOT / "docs"
TEACHER = DOCS / "john" / "john-lessons"          # teacher lesson guides
MATERIALS = DOCS / "john" / "john-materials"      # student + course-level documents
SERMONS = DOCS / "john" / "john-sermons"
FRAMING = DOCS / "john" / "john-framing"          # optional per-unit theological framing (fresh-builds)
PROMPTS = DOCS / "john" / "_prompts"              # --emit writes assembled prompts here (Claude-in-chat path)
MAP = json.loads((DOCS / "john" / "john-calendar-map.json").read_text(encoding="utf-8"))
PASSAGES = json.loads((DOCS / "john" / "john-lesson-passages.json").read_text(encoding="utf-8")) \
    if (DOCS / "john" / "john-lesson-passages.json").exists() else {}
LOG = DOCS / "john" / "_john-gen-log.jsonl"

# 16-verse anchor core (evangelical school; short, load-bearing, rolling + cumulative).
# One planted per listed unit; other units review. Longer/secondary verses are taught
# but not memorized (optional stretch for the disciple tier).
UNIT_MV = {"U0": "20:31", "U1": "1:14", "U2": "1:12", "U4": "3:16", "U6": "4:24",
    "U9": "6:35", "U12": "8:12", "U14": "10:11", "U15": "11:25", "U18": "13:34-35",
    "U19": "14:6", "U20": "15:5", "U21": "16:33", "U23": "17:3", "U25": "19:30", "U27": "21:17"}

MEMORY_VERSES = ["20:31", "1:14", "1:12", "3:16", "4:24", "6:35", "8:12", "10:11",
    "11:25", "13:34-35", "14:6", "15:5", "16:33", "17:3", "19:30", "21:17"]

DAY = {"regular": "Regular (50 min)", "thursday": "Thursday (36 min)", "half_day": "Half-day (26 min)"}

PREAMBLE = (
    "COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. "
    "SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, "
    "NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like "
    "[School Name]); "
    "use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or "
    "recitation-culture framing). "
    "DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who "
    "cannot yet find the passage, a churched but passive student, and a maturing disciple - with a "
    "low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; "
    "treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it "
    "in the study-bible tools. "
    "VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as "
    "a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD "
    "RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or "
    "split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact "
    "punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and "
    "stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X "
    "but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim "
    "as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, "
    "Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague "
    "nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. "
    "(6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not "
    "'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords "
    "(synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, "
    "the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO "
    "metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). "
    "Match the warm, plain voice of the course's hand-built exemplar lessons. "
    "NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If "
    "you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room "
    "line) - do not include it with a placeholder or left blank."
)

CONTEXT = {"subject_name": "Bible & Theology",
           "sub_subject_name": "New Testament Studies: Life and Doctrine in Christ",
           "topic_name": "The Gospel of John"}


def _slug(s):
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")


def _obj(ref, text, c=14):
    return {"id": f"JN.{ref.replace(':', '.').replace(' ', '')}", "g": 10, "c": c,
            "t": text, "a": {"scripture": [f"John {ref}" if ref[0].isdigit() else ref]}}


def _sermon_range(fname):
    m = re.search(r"\(John ([\d\-]+)\)", fname)
    if not m:
        return (None, None, None)
    p = [int(x) for x in m.group(1).split("-") if x]
    if len(p) == 1:
        return (p[0], None, None)
    if len(p) >= 3:
        return (p[0], p[1], p[2])
    return (p[0], p[1], p[1])


def _prange(pas):
    m = re.match(r"\s*(\d+):(\d+)(?:[-–](\d+))?", pas or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))) if m else (None, None, None)


def paired_sermons(passage):
    lc, la, lb = _prange(passage)
    if lc is None:
        return []
    out = []
    for p in sorted(SERMONS.glob("*.md")):
        sc, sa, sb = _sermon_range(p.name)
        if sc != lc:
            continue
        if la is None or sa is None or (sa <= lb and sb >= la):
            out.append(p)
    return out


# student-facing formats get an artifact cleanup (teacher formats keep Standards + keys)
STUDENT_FACING = {"bible_reading_guide", "student_devotional", "course_syllabus",
                  "book_survey", "reflection_journal", "scripture_memory_plan", "flashcards"}


def _clean_student(doc: str):
    """Strip generator artifacts from a student-facing doc; return (clean_doc, teacher_key|None)."""
    m = re.search(r"#{1,6}[ \t]\S", doc)     # first heading, even if leaked prose is glued before it
    if m and m.start() > 0:
        doc = doc[m.start():]
    # Drop any masthead field the model left as a bare placeholder, whether the
    # label is bold ("> **Contact:** [email / room]") or plain ("> Contact: [x / y]").
    # The bracket must hold a multi-word placeholder (a space or slash), so a real
    # reference like "[3:16]" is never touched.
    doc = re.sub(
        r"(?m)^>[ \t]*(?:(?:\*\*[^*\n]+\*\*|[A-Za-z][\w /&']*)[ \t]*:?[ \t]*)?"
        r"\[[^\]\n]*[ /][^\]\n]*\][ \t]*$\n?", "", doc)
    key = None                                # split off an Answer Key (teacher-only)
    ak = re.search(r"\n#{1,6}[ \t]*Answer Key\b", doc, re.I)
    if ak:
        key = doc[ak.start():].strip()
        doc = doc[:ak.start()]
    doc = doc.rstrip()                        # strip trailing Standards line / rules, interleaved
    for _ in range(4):
        new = re.sub(r"(?:\n+-{3,}|\n+Standards:[ \t]*[^\n]*)\s*$", "", doc).rstrip()
        if new == doc:
            break
        doc = new
    return doc.strip() + "\n", key


_DASH_CELL = re.compile(r"(?<=\|)(\s*)—(\s*)(?=\|)")   # lone em dash in a table cell
_DASH = re.compile(r"\s*—\s*")
_VERSE_TAIL = re.compile(r"\d+:\d+[\-–\d]*[\*\"'\)]*\s*$")


def _dedash(text: str) -> str:
    """Replace em dashes (the machine tell the voice guide bans) with real
    punctuation. Scripture is quoted verbatim and John's ESV uses no em dashes, so
    this only touches authored separators: a colon by default, a comma right after a
    verse reference, and a blank for a lone em dash used as an empty table cell."""
    text = _DASH_CELL.sub(r"\1 \2", text)

    def repl(m):
        return ", " if _VERSE_TAIL.search(text[:m.start()]) else ": "
    return _DASH.sub(repl, text)


# --------------------------------------------------------------------------- finalize
def finalize_doc(job, doc, tools=(), err=None, source="api"):
    """Post-process a finished draft (from the API OR from Claude in chat), apply the same
    guardrails, write it, and log. Shared by Gen.run and the --ingest path so both paths get
    identical cleanup (student strip, dedash, answer-key split, canonical H1)."""
    fmt, out = job["format"], job["out"]
    doc = (doc or "").strip()
    ok = bool(doc) and len(doc) >= job.get("min_chars", 1200) and not err
    if ok:
        out.parent.mkdir(parents=True, exist_ok=True)
        key = None
        if fmt in STUDENT_FACING:
            doc, key = _clean_student(doc)
        doc = _dedash(doc)                            # no em dashes ship (voice guide)
        if job.get("title"):                          # force a canonical first H1 (reading guides)
            doc = re.sub(r"(?m)^#{1,6}[ \t]+.*$", lambda m: f"# {job['title']}", doc, count=1)
        out.write_text(doc, encoding="utf-8")
        if key:
            (out.parent / (out.stem + "_TEACHER-KEY.md")).write_text(
                f"# Teacher key - {out.stem}\n\n{_dedash(key)}\n", encoding="utf-8")
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": job["label"], "format": fmt,
           "out": str(out), "chars": len(doc), "tools": sorted(set(tools)), "ok": ok,
           "error": err, "source": source}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{'ok' if ok else 'FAIL'}] {out.name} ({len(doc)}c, {source}, tools={sorted(set(tools))})"
          + ("" if ok else f"  <-- NOT WRITTEN ({err or 'too short'})"))
    return rec


def emit_prompt(job, prompt_dir=None):
    """Assemble the exact SYSTEM + TASK for a job and write it to _prompts/ WITHOUT calling the
    API, so Claude-in-chat can generate the document on the subscription. Pair with --ingest."""
    prompt_dir = prompt_dir or PROMPTS
    fmt = job["format"]
    system = generator.build_system(fmt, "secondary")
    task = generator.build_task(fmt, job["objectives"], "secondary",
                                job.get("context", CONTEXT), job["brief"])
    prompt_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", job["label"]).strip("-")
    p = prompt_dir / f"{slug}.md"
    meta = {"format": fmt, "out": str(job["out"]), "min_chars": job.get("min_chars", 1200),
            "student_facing": fmt in STUDENT_FACING, "title": job.get("title", ""),
            "sermon": job.get("_sermon", [])}
    p.write_text(
        "<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,\n"
        "     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible\n"
        "     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>\n"
        "     (applies the guardrails and writes it, no API).\n"
        f"     meta: {json.dumps(meta)} -->\n\n"
        "===================== SYSTEM =====================\n\n" + system +
        "\n\n===================== TASK =====================\n\n" + task + "\n",
        encoding="utf-8")
    print(f"[emit] {p}  (out={job['out'].name}, format={fmt}, "
          f"min_chars={meta['min_chars']}, student_facing={meta['student_facing']})")
    return p


def ingest_completion(job, draft_path):
    """Take a Claude-in-chat draft for a job, run it through the same guardrails, and write it."""
    doc = Path(draft_path).read_text(encoding="utf-8")
    return finalize_doc(job, doc, source="claude-in-chat")


# --------------------------------------------------------------------------- engine
class Gen:
    def __init__(self, dry=False):
        self.dry = dry
        self.bridge = None

    async def __aenter__(self):
        if not self.dry:
            self.bridge = MCPBridge()
            await self.bridge.start()
            print(f"[gen] MCP up: {len(self.bridge.tools)} tools")
        return self

    async def __aexit__(self, *a):
        if self.bridge:
            await self.bridge.stop()

    async def run(self, job, force=False):
        fmt, out = job["format"], job["out"]
        system = generator.build_system(fmt, "secondary")
        task = generator.build_task(fmt, job["objectives"], "secondary", job.get("context", CONTEXT), job["brief"])
        if self.dry:
            print(f"[dry] {job['label']}: format={fmt} out={out.name} objectives={len(job['objectives'])} "
                  f"system={len(system)}c task={len(task)}c")
            return {"ok": True, "dry": True, "label": job["label"]}
        if out.exists() and not force:
            print(f"[skip] {out.name} exists (--force to overwrite)")
            return {"ok": True, "skipped": True}
        min_chars = job.get("min_chars", 1200)
        doc, tools, err = "", [], None
        for attempt in (1, 2):
            buf, tools, err = [], [], None
            try:
                async for ev in providers.run("anthropic", None, MODEL, system,
                                              [{"role": "user", "content": task}], self.bridge):
                    t = ev["type"]
                    if t == "text":
                        buf.append(ev["text"])
                    elif t == "tool_call":
                        tools.append(ev["name"])
                        # The document is the model's FINAL turn (after the last tool
                        # round). A new tool call means whatever text preceded it was
                        # process narration ("let me get the rest..."), not the
                        # artifact -- drop it so it can't bleed into the file.
                        buf.clear()
                    elif t == "error":
                        err = ev["message"]
                        print(f"[error] {err}")
            except Exception as e:  # noqa: BLE001
                err = str(e)
                print(f"[exc] {e}")
            doc = "".join(buf).strip()
            if doc and len(doc) >= min_chars and not err:
                break
            if attempt == 1:
                print(f"[gen] {job['label']}: retrying once ({'error' if err else 'short output'})")
                await asyncio.sleep(2)
        return finalize_doc(job, doc, tools=tools, err=err)


# --------------------------------------------------------------------------- job builders
def _carried_verses(unit_key: str):
    """Anchor verses already introduced at or before this unit (the rolling-review
    set), plus the next new one. For units that introduce no verse of their own."""
    try:
        n = int(unit_key[1:])
    except ValueError:
        return [], None
    order = sorted((int(u[1:]), v) for u, v in UNIT_MV.items() if u[1:].isdigit())
    carried = [v for un, v in order if un <= n]
    nxt = next((f"John {v} (Unit {un})" for un, v in order if un > n), None)
    return carried, nxt


def _parse_ref(ref: str):
    """'4:24' -> (4,24,4,24); '4:1-15' -> (4,1,4,15); '4:20-26' -> (4,20,4,26).
    Returns (start_chap, start_verse, end_chap, end_verse) or None if unparseable."""
    m = re.match(r"^\s*(\d+):(\d+)(?:\s*[-–]\s*(?:(\d+):)?(\d+))?\s*$", ref or "")
    if not m:
        return None
    sc, sv = int(m.group(1)), int(m.group(2))
    if m.group(4):
        ec = int(m.group(3)) if m.group(3) else sc
        ev = int(m.group(4))
    else:
        ec, ev = sc, sv
    return sc, sv, ec, ev


def _mv_position(mv: str, passage: str):
    """Where the memory verse sits relative to a lesson's passage: 'before' (a later
    lesson reaches it), 'inside' (this lesson plants it), or 'after' (already planted).
    None if either ref won't parse."""
    a, b = _parse_ref(mv), _parse_ref(passage)
    if not a or not b:
        return None
    mvk = a[0] * 1000 + a[1]
    start, end = b[0] * 1000 + b[1], b[2] * 1000 + b[3]
    if mvk < start:
        return "before"
    if mvk > end:
        return "after"
    return "inside"


def _memory_line(unit_key: str, kind: str, passage: str = None) -> str:
    """Memory-verse instruction for a unit. Units on the 16-verse list plant/review
    their verse; every other unit introduces NO verse, so say that outright, or the
    model invents one (differently in every doc). For a plant unit's lessons, the plant
    lands ONLY in the lesson whose passage actually contains the verse (passage-aware),
    so an anchor that sits mid-unit is not misplanted on lesson 1."""
    mv = UNIT_MV.get(unit_key)
    if mv:
        if kind != "lesson":
            return f"UNIT MEMORY VERSE: John {mv} (ESV, with the review note)."
        pos = _mv_position(mv, passage) if passage else None
        carried, _ = _carried_verses(unit_key)
        priors = ", ".join(f"John {v}" for v in carried if v != mv) or "none yet"
        if pos == "inside":
            return (f"UNIT MEMORY VERSE: John {mv} (ESV). This lesson's passage contains it. PLANT it here as "
                    f"this unit's one new graded verse and teach it fresh. It is the only new verse this unit.")
        if pos == "after":
            return (f"MEMORY VERSES: this unit's new verse is John {mv}, and it sits in a later passage this "
                    f"lesson has not reached yet. Do NOT plant, teach, or quiz John {mv} here. If memory work "
                    f"comes up, keep the already-assigned verses sharp ({priors}).")
        if pos == "before":
            return (f"UNIT MEMORY VERSE: John {mv} (ESV) was planted earlier in this unit, in the passage where "
                    f"it appears. REVIEW it here. Do NOT re-plant it.")
        return f"UNIT MEMORY VERSE: John {mv} (plant if this is the unit's first lesson, else review)."
    carried, nxt = _carried_verses(unit_key)
    carried_str = ", ".join(f"John {v}" for v in carried) or "none yet"
    return ("MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory "
            "verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, "
            "or invent a memory verse from this unit. If memory work comes up, say only that there is no "
            f"new verse this unit and to keep the assigned verses sharp ({carried_str})"
            + (f"; the next new one comes in {nxt}." if nxt else "."))


def _reading_title(unit_label: str) -> str:
    """Canonical H1 for a unit reading guide, so titles and PDF names stay uniform.
    'U2 Witness & first disciples' -> 'Reading guide, Unit 2: Witness and first disciples'."""
    key, _, name = unit_label.partition(" ")
    num = key[1:] if key[:1] == "U" and key[1:].isdigit() else key
    name = name.replace("&", "and").strip()
    return f"Reading guide, Unit {num}: {name}" if name else f"Reading guide, Unit {num}"


def _framing(unit_key: str) -> str:
    """Adam's theological framing for a fresh-build unit (from the Theologian persona),
    if present at docs/john/john-framing/<unit>.md. Injected into the brief like a sermon."""
    p = FRAMING / f"{unit_key}.md"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def lesson_job(index, passage=None, use_sermon=True):
    row = next((r for r in MAP["lessons"] if r["i"] == index), None)
    if not row:
        raise SystemExit(f"no lesson index {index}")
    uk = row["unit"].split()[0]
    passage = passage or PASSAGES.get(str(index)) or row["passage"]
    sermon = ""
    used = []
    if use_sermon and ":" in (passage or ""):
        for p in paired_sermons(passage):
            sermon += p.read_text(encoding="utf-8")[:7000] + "\n\n"
            used.append(p.name)
    framing = _framing(uk)
    brief = "\n".join([PREAMBLE, "",
        f"PRODUCE the teacher lesson guide for global lesson {row['i']} of 150.",
        f"UNIT (use this exact name): {row['unit']}.  LESSON WITHIN UNIT: {row['lesson_in_unit']}.",
        f"PASSAGE: John {passage}.  DAY TYPE: {DAY.get(row['day_type'], row['day_type'])} (use the matching variant).",
        (f"CALENDAR NOTE (from the master plan; honor its day-type shape): {row['note']}" if row.get("note") else ""),
        _memory_line(uk, "lesson", passage),
        "Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.",
        (f"\nFRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's "
         f"voice; treat it as his ruling: follow it on the contested points and land where it lands):\n"
         f"-----\n{framing}\n-----" if framing else ""),
        (f"\nPAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):\n-----\n{sermon.strip()}\n-----" if sermon else "")])
    obj = [_obj(passage, f"Teach John {passage} faithfully so students grasp who Jesus is and the response he calls for (John 20:31).")]
    return {"label": f"lesson {index} ({uk} John {passage})", "format": "bible_lesson_guide",
            "objectives": obj, "context": {**CONTEXT, "sub_topic_name": f"John {passage}"},
            "brief": brief, "out": TEACHER / f"GEN_{uk}-L{row['lesson_in_unit'].split('/')[0]}-John-{_slug(passage)}.md",
            "min_chars": 3000, "_sermon": used}


def reading_guide_job(unit_key, use_sermon=False):
    rows = [r for r in MAP["lessons"] if r["unit"].split()[0] == unit_key]
    if not rows:
        raise SystemExit(f"no unit {unit_key}")
    unit = rows[0]["unit"]
    lesson_passages = [PASSAGES.get(str(r["i"]), r["passage"]) for r in rows]
    verse_passages = [p for p in lesson_passages if ":" in p]
    mv = UNIT_MV.get(unit_key)
    rng = f"{verse_passages[0]}..{verse_passages[-1]}" if verse_passages else lesson_passages[0]
    framing = _framing(unit_key)
    brief = "\n".join([PREAMBLE, "",
        f"PRODUCE the per-unit STUDENT reading guide for {unit} (John {rng}).",
        "Give a short follow-along block for each of these lesson passages, in order: "
        + "; ".join(f"John {p}" for p in verse_passages) + ".",
        _memory_line(unit_key, "reading"),
        (f"\nFRAMING (Adam's theological framing for this passage; keep the student guide consistent with "
         f"its rulings and emphasis, put in plain student language):\n-----\n{framing}\n-----" if framing else ""),
        "Student-facing, plain and warm; light prompts that lean on the Reading Journal and the discussion, "
        "not take-home busywork. Mark 'Go deeper' prompts optional. Keep it honest for a searching student."])
    obj = [_obj(rng, f"Help a 10th grader read John {rng} with understanding and response.")]
    if mv:
        obj.append(_obj(mv, f"Know and review the unit memory verse John {mv}.", c=9))
    return {"label": f"reading-guide {unit_key}", "format": "bible_reading_guide", "objectives": obj,
            "context": {**CONTEXT, "sub_topic_name": f"John {rng}"},
            "brief": brief, "title": _reading_title(unit),
        "out": MATERIALS / f"GEN_{unit_key}_reading-guide.md", "min_chars": 1500}


def devotional_job(passage):
    brief = "\n".join([PREAMBLE, "",
        f"PRODUCE the student-led devotional TEMPLATE for a group leading John {passage} to the class.",
        "It is a template the students fill and lead from, mirroring the course's lesson arc in miniature. "
        "Graded as participation (preparation, engagement, service); theology is coached live, not scored. "
        "Keep faith content invitational for a mixed-faith room."])
    return {"label": f"devotional John {passage}", "format": "student_devotional",
            "objectives": [_obj(passage, f"Build and lead a short devotional on John {passage} that ministers to peers and invites response.")],
            "context": {**CONTEXT, "sub_topic_name": f"John {passage}"},
            "brief": brief, "out": MATERIALS / f"GEN_devotional_John-{_slug(passage)}.md", "min_chars": 1000}


COURSE_DOCS = {
    "syllabus": dict(format="course_syllabus", file="GEN_syllabus.md", min_chars=2000,
        objectives=[_obj("20:31", "State the purpose and shape of a year in the Gospel of John.")],
        brief="""PRODUCE the student- and parent-facing course syllabus. Use ONLY these specifics; do not invent policy.
INSTRUCTOR: Adam Vega. SECTIONS: Periods 2 and 5 (same curriculum). MEETS: daily, full year, Sep 8 2026 - May 28 2027. CONTACT LINE: leave a placeholder "[email address / room number]".
DESCRIPTION: one book, slowly and in order - the Gospel of John, verse by verse from first verse to last. John's stated purpose is John 20:31.
AIM (the central questions the course returns to): Who is Jesus, according to John? What does John mean by believing, and what does believing change? How does the whole story of the Bible come together in Christ? What does it look like to receive grace rather than earn it?
HOW THE YEAR IS ORGANIZED: two halves. Fall = the Book of Signs (John 1-12); Spring = the Book of Glory (John 13-21: the upper room, the cross, the resurrection). Semester 1 final Jan 11-14 2027; Semester 2 final May 25-28 2027.
HOW WE STUDY: each class opens with a 7-minute quiet time (prayer and journaling); we read the passage aloud; we work through the text together in discussion in small "John groups"; we close by responding in writing. Verse by verse, in context, Christ-centered.
WHAT STUDENTS DO: keep a Reading Journal (observation and response) and a personal Quiet-Time Journal; memorize 16 key verses across the year, reviewed cumulatively; take an active part in discussion; help lead student devotionals for their peers; complete four projects, one per quarter; sit two semester final exams; take checkpoint quizzes and rolling memory-verse quizzes. Most graded work happens in the room, in class.
REQUIRED MATERIALS: a physical Bible the student can mark in (the class teaches primarily from the ESV; any faithful translation is welcome); a dedicated notebook for the Reading Journal and one for the Quiet-Time Journal; something to write with, every day.
GRADING (state the categories and weights exactly): Participation & Discipleship 30%, Memory & Quizzes 30%, Projects 25%, Semester Final 15%. Note that the final's weight follows school policy (the semester grade is coursework plus a 15% final exam). Homework is minimal - mostly the daily reading.
MEMORY VERSES (list all 16 references; added a few at a time and reviewed cumulatively): John 20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35, 14:6, 15:5, 16:33, 17:3, 19:30, 21:17.
PROJECTS (four, one per quarter; one line each on what the student creates; each is built in steps - a proposal, a plan, and a draft - and presented to the class): Q1 The Signs (make something that shows why one of Jesus' miracles is a "sign" and what it reveals about him); Q2 Character Study (get inside one person's encounter with Jesus in John); Q3 Teaching the Farewell Discourse (small groups teach a section of John 13-17 to the class); Q4 The Passion and a Personal Response (trace the crucifixion and resurrection across John 18-20 and respond honestly to John 20:31).
CLASSROOM EXPECTATIONS: come with your Bible open and your mind engaged; honest questions are welcome and doubt is not disqualifying; treat one another with respect, especially in disagreement; be present and take part, because much of the learning is in the discussion; keep up with the journal and the memory work; follow the school's policies on attendance, late work, and technology.
ACADEMIC HONESTY: your work should be your own, and give credit for any source you draw on; per school policy, AI content generators may not be used for coursework unless a teacher approves in advance; most graded work happens in class, in your own words.
NOTE TO PARENTS: warm and grace-centered - the goal is not only that students learn the facts of the Gospel of John, though they will, but that they meet the Jesus John wrote about; taught from historic Christian orthodoxy in keeping with the school's statement of faith, with a steady emphasis on grace (we come to God because of what Christ has done, not what we achieve); questions are met with patience and respect; parents are welcome to reach out any time. Close with the instructor's name, Adam Vega."""),
    "how-to-read-john": dict(format="book_survey", file="GEN_how-to-read-john.md", min_chars=1200,
        objectives=[_obj("20:30-31", "Orient a 10th grader to how to read the Gospel of John."),
                    _obj("1:1-18", "See the book's two halves and its purpose.", c=9)],
        brief="PRODUCE a one-page 'How to Read John' orientation handout for Unit 0, student-facing. Cover: what a "
              "Gospel is and that there are four; John's own stated purpose (John 20:31); the book's two halves "
              "(the Book of Signs, chs. 1-12, and the Book of Glory, chs. 13-21); how we will read it (verse by "
              "verse, slowly, asking who Jesus is and what response he calls for); how to find John and navigate it; "
              "and a warm note that honest questions and doubts are welcome. Keep it a concise student orientation page "
              "(a map for the front of the notebook); a couple of honest reflection prompts are fine, but do not make "
              "it a graded worksheet and do not include an answer key. Plain and inviting; ESV."),
    "reading-journal-guide": dict(format="reflection_journal", file="GEN_reading-journal-guide.md", min_chars=900,
        objectives=[_obj("20:30-31", "Keep a Reading Journal of observation and response while studying John.")],
        brief="PRODUCE a one-page Reading Journal guide, student-facing. Explain what the Reading Journal is, how to "
              "keep it in class (observations of the text, then an honest personal response), what a good entry looks "
              "like (with one short example), and that it is graded inside participation for genuine effort, never for "
              "the 'right' answer. The four in-class steps are Locate, Observe, Respond, and Apply - do NOT include "
              "a prayer step (prayer belongs to the SEPARATE Quiet-Time Journal; the two journals stay distinct). "
              "This is the analytical journal: observe the text, respond honestly, then one line of application. "
              "Warm and simple; ESV where Scripture appears."),
    "quiet-time-journal-guide": dict(format="reflection_journal", file="GEN_quiet-time-journal-guide.md", min_chars=800,
        objectives=[_obj("20:31", "Practice a simple daily quiet time of prayer and journaling.")],
        brief="PRODUCE a one-page Quiet-Time Journal guide, student-facing. Explain the daily 7-minute quiet time that "
              "opens class: what to do (settle, read the centering verse, journal, pray, sit), that it is ungraded and "
              "personal and never read aloud, that phones are away, and give an honest on-ramp so a student unsure "
              "about God can still write questions to him. The template MUST match this free rhythm exactly and number "
              "the steps from 1: Settle; Read the centering verse; Journal (a FREE devotional space, not analytical "
              "Observe/Interpret/Apply steps); Pray; Sit. This is the personal, free devotional-and-prayer journal, "
              "kept DISTINCT from the Reading Journal (which does the observation and analysis). Keep the template "
              "simple - a free Journal space and a Prayer space. Gentle, unpressured; ESV."),
    "memory-master": dict(format="scripture_memory_plan", file="GEN_memory-master.md", min_chars=1500,
        objectives=[_obj(v, f"Memorize John {v} (ESV).", c=9) for v in MEMORY_VERSES],
        brief="PRODUCE the Memory Verse master sheet, student-facing, for the whole year. List all 16 verses IN THIS "
              "ORDER with their full ESV text: " + ", ".join(f"John {v}" for v in MEMORY_VERSES) + ". Add a cumulative "
              "rolling-review schedule (each verse is added at its own unit and all prior verses stay in review; "
              "only 16 of the 29 units introduce a verse, so never say or imply a new verse is added every unit). "
              "IMPORTANT: the course has 29 units (U0-U28); if you show a 'Unit' column use THESE exact unit numbers, "
              "do NOT renumber them 1-16: 20:31=Unit 0, 1:14=Unit 1, 1:12=Unit 2, 3:16=Unit 4, 4:24=Unit 6, "
              "6:35=Unit 9, 8:12=Unit 12, 10:11=Unit 14, 11:25=Unit 15, 13:34-35=Unit 18, 14:6=Unit 19, 15:5=Unit 20, "
              "16:33=Unit 21, 17:3=Unit 23, 19:30=Unit 25, 21:17=Unit 27. Quote every verse in the ESV via the tools."),
    "memory-cards": dict(format="flashcards", file="GEN_memory-cards.md", min_chars=1200,
        objectives=[_obj(v, f"Recall John {v} (ESV).", c=9) for v in MEMORY_VERSES],
        brief="PRODUCE a set of 16 memory-verse flashcards IN THIS ORDER, one per verse: " + ", ".join(f"John {v}" for v in MEMORY_VERSES)
              + ". Front = the reference; back = the verse in the ESV. On each back, give ONLY the verse's own words and "
              "DROP the enclosing quotation marks that belong to the surrounding speech, so no card has a dangling "
              "opening or closing quote. Quote every verse in the ESV, grounded via the tools."),
}


def course_job(slug):
    d = COURSE_DOCS.get(slug)
    if not d:
        raise SystemExit(f"unknown course doc '{slug}'. options: {', '.join(COURSE_DOCS)}")
    return {"label": f"course:{slug}", "format": d["format"], "objectives": d["objectives"],
            "context": CONTEXT, "brief": "\n".join([PREAMBLE, "", d["brief"]]),
            "out": MATERIALS / d["file"], "min_chars": d["min_chars"]}


# --------------------------------------------------------------------------- driver
async def run_jobs(jobs, dry, force):
    async with Gen(dry=dry) as g:
        results = []
        for j in jobs:
            results.append(await g.run(j, force=force))
    ok = sum(1 for r in results if r.get("ok"))
    print(f"\n[done] {ok}/{len(results)} ok" + (" (dry-run)" if dry else ""))
    return results


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lesson"); p.add_argument("--index", type=int, required=True); p.add_argument("--passage")
    p = sub.add_parser("reading-guide"); p.add_argument("--unit", required=True)
    p = sub.add_parser("devotional"); p.add_argument("--passage", required=True)
    p = sub.add_parser("course"); p.add_argument("--doc"); p.add_argument("--all", action="store_true")
    for pp in sub.choices.values():
        pp.add_argument("--dry-run", action="store_true")
        pp.add_argument("--force", action="store_true")
        pp.add_argument("--no-sermon", action="store_true")
        pp.add_argument("--emit", action="store_true",
                        help="write the assembled prompt to docs/john/_prompts/ instead of calling the API")
        pp.add_argument("--ingest", metavar="DRAFT",
                        help="apply the guardrails to a Claude-in-chat draft and write it (no API)")
    a = ap.parse_args()

    if a.cmd == "lesson":
        jobs = [lesson_job(a.index, a.passage, not a.no_sermon)]
    elif a.cmd == "reading-guide":
        jobs = [reading_guide_job(a.unit)]
    elif a.cmd == "devotional":
        jobs = [devotional_job(a.passage)]
    elif a.cmd == "course":
        slugs = list(COURSE_DOCS) if a.all else [a.doc]
        if not a.all and not a.doc:
            raise SystemExit("course: pass --doc <slug> or --all. slugs: " + ", ".join(COURSE_DOCS))
        jobs = [course_job(s) for s in slugs]

    if a.emit:                                        # assemble prompts; no API (Claude-in-chat)
        for j in jobs:
            emit_prompt(j)
        return
    if a.ingest:                                      # finalize a chat draft; no API
        if len(jobs) != 1:
            raise SystemExit("--ingest handles one job at a time")
        ingest_completion(jobs[0], a.ingest)
        return
    asyncio.run(run_jobs(jobs, a.dry_run, a.force))


if __name__ == "__main__":
    main()
