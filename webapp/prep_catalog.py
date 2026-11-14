"""The Prep Room's Make panel: the resource kinds grouped by the job a teacher is doing, with the
variants each offers, and the rule that builds a student copy from a teacher's document.

The kinds themselves live in resource-generators.yaml (webapp/generator.FORMATS). This module only
sorts them for the gallery, names their variants in plain words, and withholds the variants that are
themselves devotions (decision 0010)."""
from __future__ import annotations

import re

from webapp import generator

GROUPS = [
    ("plan", "Plan", ["lesson_plan", "unit_plan", "course_syllabus", "project_planner", "planner_template",
                      "checklist", "tracker", "scripture_memory_plan"]),
    ("teach", "Teach", ["slide_deck", "explainer_sheet", "fact_sheet", "reference_chart", "biography_profile",
                        "timeline", "annotated_map", "family_tree", "classification_tree", "labeled_diagram",
                        "process_diagram", "how_to_guide", "project_guide", "art_technique_tutorial",
                        "listening_guide", "discussion_questions", "debate_kit", "case_study",
                        "role_play_scenario", "script"]),
    ("practice", "Practice", ["worksheet", "student_packet", "problem_set", "drill_set", "flashcards",
                              "puzzle_activity", "vocabulary_list", "grammar_practice", "sentence_diagram",
                              "logic_practice", "graphic_organizer", "comparison_matrix", "venn_diagram",
                              "story_map", "cornell_notes", "fill_in_template", "data_analysis", "lab_report",
                              "field_observation", "engineering_design", "music_worksheet",
                              "copywork_handwriting", "decodable_text", "translation_worksheet"]),
    ("assess", "Assess", ["quiz", "diagnostic", "study_guide", "rubric", "performance_rubric", "answer_key"]),
    ("read_write", "Read and write", ["reading_comprehension_set", "close_reading_guide", "reading_anthology",
                                      "writing_prompt_set", "essay_assignment", "outline_template",
                                      "reflection_journal"]),
    ("bible", "Study the Bible", ["bible_reading_guide", "bible_lesson_guide", "inductive_passage_study",
                                  "exegesis_report", "character_study", "book_survey", "harmony_chart",
                                  "word_study", "confession_study", "apologetics_argument_map",
                                  "sermon_lesson_outline", "faith_integration", "student_devotional"]),
]

# Variants that would have Exegetica write a devotion or prayers for someone to follow (decision 0010).
WITHHELD_VARIANTS = {"prayer_journal", "lectio_divina", "devotional_journal"}

# Kinds written for the teacher; the Student copy toggle doesn't apply to them.
FOR_TEACHER = {"lesson_plan", "unit_plan", "answer_key", "faith_integration", "bible_lesson_guide",
               "sermon_lesson_outline", "rubric", "performance_rubric", "diagnostic"}

LENGTHS = {"short": "Keep it short: about one page.",
           "standard": "",
           "long": "Make it fuller than usual: about three to four pages."}

_ITEM_LABELS = {"multiple_choice": "Multiple choice", "true_false": "True or false", "matching": "Matching",
                "fill_in_the_blank": "Fill in the blank", "short_answer": "Short answer", "essay": "Essay"}


def variant_label(v: str) -> str:
    """'pop_quiz' -> 'Pop quiz'; an instruction-style variant keeps the words before its colon."""
    head = v.split(":", 1)[0].strip()
    return head if " " in head or "(" in head else head.replace("_", " ").capitalize()


def variants(format_id: str) -> list[dict]:
    fmt = generator.FORMATS.get(format_id) or {}
    return [{"id": v, "label": variant_label(v)} for v in (fmt.get("variants") or []) if v not in WITHHELD_VARIANTS]


def variant_instruction(format_id: str, variant: str | None) -> str:
    """The line a draft gets for a chosen variant, or '' when it isn't one this kind offers."""
    if not variant or variant not in {v["id"] for v in variants(format_id)}:
        return ""
    if ":" in variant:
        return f"Variant: {variant.strip()}"
    if variant in generator.FORMATS:
        return f'Shape it as a {generator.FORMATS[variant]["name"]}.'
    return f"Variant: {variant_label(variant)}."


def gallery() -> dict:
    groups = []
    for key, label, ids in GROUPS:
        kinds = []
        for fid in ids:
            fmt = generator.FORMATS.get(fid)
            if not fmt:
                continue
            kinds.append({
                "id": fid, "name": fmt["name"], "definition": (fmt.get("definition") or "").strip(),
                "use_when": (fmt.get("use_when") or "").strip(),
                "structure": [str(s) for s in (fmt.get("structure") or [])][:6],
                "aka": fmt.get("aka") or [],
                "variants": variants(fid),
                "item_types": [{"id": t, "label": _ITEM_LABELS.get(t, t.replace("_", " ").capitalize())}
                               for t in (fmt.get("item_types") or [])],
                "for_teacher": fid in FOR_TEACHER,
            })
        groups.append({"key": key, "label": label, "kinds": kinds})
    return {"groups": groups, "grade_bands": generator.grade_bands(),
            "lengths": [{"id": k, "label": k.capitalize()} for k in LENGTHS]}


# ------------------------------------------------------------------ the student copy
# A teacher-only section is headed "Answer Key" or "Teaching Notes", or ends its heading with
# "(Teacher)". Drafts are told to mark them that way (webapp/generator.build_unit_task).
_TEACHER_HEAD = re.compile(
    r"^(#{1,6})\s+(?:answer key|answers|teaching notes|teacher notes|notes for the teacher|for the teacher"
    r"|teacher'?s? (?:guide|notes|key)|.*\((?:teacher|teacher only|for the teacher)\))\s*:?\s*$", re.I)
_HEAD = re.compile(r"^(#{1,6})\s")
_TEACHER_LINE = re.compile(r"^\s*(?:\*\*)?(?:standards|objectives? \(teacher\))(?:\*\*)?\s*:", re.I)
_BAND_LINE = re.compile(r"^\s*(?:>\s*)?(?:\*\*)?grade[ -]band(?:\*\*)?\s*:", re.I)   # never shown to students


def student_copy(md: str) -> str:
    """The document without its teacher-only sections, the `Standards:` and Grade Band lines, or a rule left
    dangling before a removed section. Mirrored by studentCopy() in static/js/prep.js."""
    out: list[str] = []
    skip_level = 0
    for line in (md or "").splitlines():
        head = _HEAD.match(line)
        if skip_level:
            if head and len(head.group(1)) <= skip_level:
                skip_level = 0
            else:
                continue
        m = _TEACHER_HEAD.match(line.strip())
        if m:
            skip_level = len(m.group(1))
            while out and out[-1].strip() in ("", "---", "***", "___"):
                out.pop()
            continue
        if _TEACHER_LINE.match(line) or _BAND_LINE.match(line):
            continue
        out.append(line)
    while out and out[-1].strip() in ("", "---", "***", "___"):
        out.pop()
    return "\n".join(out) + "\n"


def has_teacher_part(md: str) -> bool:
    return any(_TEACHER_HEAD.match(line.strip()) for line in (md or "").splitlines())
