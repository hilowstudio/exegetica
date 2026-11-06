"""
Library lookups made in code before an open model's first step (docs/decisions/0020).

Open models answer from memory more often than Opus. When a student's message names its source
plainly (a verse or chapter, a creed or confession, a course unit, the memory verses, today's
lesson), these lookups run before the model starts, so it begins with the source in hand. The
patterns are narrow: a lookup the message doesn't clearly call for costs tokens and time, and the
model can still make any lookup it wants itself.
"""
from __future__ import annotations

import re

from studybible_mcp.database import BOOK_ABBREV_MAP

from webapp import citations

MAX_CALLS = 4

_BOOKS = set(BOOK_ABBREV_MAP)
# A whole chapter named without a verse: "John 4", "1 John 2", "Psalm 23".
_CHAPTER = re.compile(r"(?<![\w:])((?:[1-3]\s?)?[A-Z][a-z]+(?:\s+of\s+[A-Z][a-z]+)?)\s+(\d{1,3})\b(?![:.]\d)")

# (pattern, the name get_confession resolves). "1689" alone also names a year, so it counts only
# beside "confession" or "London Baptist".
_DOCUMENTS = [
    (r"westminster\s+confession|\bwcf\b", "Westminster Confession"),
    (r"shorter\s+catechism|\bwsc\b", "Westminster Shorter Catechism"),
    (r"larger\s+catechism|\bwlc\b", "Westminster Larger Catechism"),
    (r"\b1689\s+(?:london\s+baptist\s+)?confession|london\s+baptist|second\s+london", "1689"),
    (r"heidelberg", "Heidelberg Catechism"),
    (r"belgic\s+confession", "Belgic Confession"),
    (r"canons\s+of\s+dort|synod\s+of\s+dort", "Canons of Dort"),
    (r"nicene\s+creed", "Nicene Creed"),
    (r"apostles'?\s+creed", "Apostles' Creed"),
    (r"athanasian\s+creed", "Athanasian Creed"),
    (r"chalcedonian\s+definition|definition\s+of\s+chalcedon", "Chalcedonian Definition"),
    (r"augsburg\s+confession", "Augsburg Confession"),
    (r"(?:thirty-nine|39)\s+articles", "Thirty-Nine Articles"),
    (r"baltimore\s+catechism", "Baltimore Catechism"),
]
_DOCUMENTS = [(re.compile(p, re.I), name) for p, name in _DOCUMENTS]
# A section written just after the document's name: "WSC Q33", "Westminster Confession 25.6",
# "Heidelberg Catechism question 1", "1689 Confession chapter 29".
_SECTION = re.compile(r"\s*,?\s*(?:(?:chapter|ch\.?|article|art\.?|question|q\.?)\s*)?(\d{1,3}(?:[.:]\d{1,3})?)\b", re.I)

_UNIT = re.compile(r"\bunit\s+(\d{1,2})\b", re.I)
_MEMORY = re.compile(r"\bmemory\s+verses?\b", re.I)
_SCHEDULE = re.compile(r"\b(?:today|tonight|tomorrow|this\s+week|next\s+week|right\s+now)\b", re.I)


def plan(text: str, tool_names: set[str]) -> list[tuple[str, dict]]:
    """The lookups a student's message clearly calls for, as (tool, arguments), at most MAX_CALLS,
    using only tools this chat has."""
    calls: list[tuple[str, dict]] = []

    def add(name: str, args: dict) -> None:
        if name in tool_names and (name, args) not in calls and len(calls) < MAX_CALLS:
            calls.append((name, args))

    text = text or ""
    for ref in citations.references(text):
        if ref["code"] in BOOK_ABBREV_MAP.values():
            add("get_passage" if ref["v2"] > ref["v1"] else "lookup_verse", {"reference": ref["text"]})
    for m in _CHAPTER.finditer(text):
        if m.group(1).lower() in _BOOKS:
            add("get_passage", {"reference": f"{m.group(1)} {m.group(2)}"})
    for pattern, name in _DOCUMENTS:
        if m := pattern.search(text):
            section = _SECTION.match(text, m.end())
            add("get_confession", {"document": name, **({"section": section.group(1)} if section else {})})
    unit = _UNIT.search(text)
    if unit and 1 <= int(unit.group(1)) <= 28:
        add("get_reading_guide", {"unit": int(unit.group(1))})
    if _MEMORY.search(text):
        add("get_memory_verses", {"unit": int(unit.group(1))} if unit else {})
    if _SCHEDULE.search(text) and not unit:
        add("get_course_schedule", {})
    return calls
