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
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_MATERIALS = Path(__file__).resolve().parent.parent / "docs" / "john-materials"
_MEMORY_MASTER = _MATERIALS / "GEN_memory-master.md"


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
            "List the student course materials for the Sophomore Bible: Gospel of John "
            "curriculum — every unit reading guide (with its passage and memory verse), the "
            "four quarter projects, and the memory-verse set. Call this first when a student "
            "asks what readings/projects/verses exist, or to find which unit covers a given "
            "passage or topic before fetching it."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_reading_guide",
        "description": (
            "Return the student reading guide for one unit of the Gospel of John course "
            "(units 1-28): its passage, the big question, and the observe/interpret/respond "
            "prompts. If you don't know the unit number, call list_john_curriculum first."
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
            "Return the student guide for one of the four quarter projects in the Gospel of "
            "John course (quarter 1-4): the assignment, what to build, the options, and the "
            "due dates."
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
            "Return the Gospel of John course memory-verse master sheet: the 16 verses in the "
            "order they're learned, which unit introduces each, the rolling-review schedule, "
            "and a context note per verse. Pass a unit number to focus on the verse for that "
            "unit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "unit": {"type": "integer", "description": "Optional unit number (0-28) to focus on."}
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


_HANDLERS = {
    "list_john_curriculum": _handle_list,
    "get_reading_guide": _handle_reading_guide,
    "get_project": _handle_project,
    "get_memory_verses": _handle_memory,
}


def handle(name: str, args: dict) -> str:
    """Dispatch a curriculum tool by name. Raises KeyError if not a curriculum tool."""
    return _HANDLERS[name](args or {})


def system_note() -> str:
    """A block appended to the chat system prompt so the model knows these tools exist."""
    return (
        "\n\n---\n\n"
        "## Course materials (Gospel of John)\n"
        "You are also the study assistant for a high-school Sophomore Bible course on the "
        "Gospel of John (Yorkville Christian School). Students may ask about their unit "
        "reading guides, the four quarter projects, or the year's memory verses. Answer from "
        "the actual course documents using the curriculum tools: call list_john_curriculum to "
        "see what exists or to map a passage or topic to a unit, then get_reading_guide(unit), "
        "get_project(quarter), or get_memory_verses(unit). Quote the guide's own wording, keep "
        "explanations at a high-school level, and never invent an assignment, a due date, or a "
        "memory verse that isn't in these documents. If a student asks for daily-page answers "
        "or a teacher answer key, explain that those aren't available here."
    )
