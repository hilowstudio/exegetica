"""
Parsers for verse-keyed public-domain devotionals into the `devotionals` table.

Each source is a set of daily readings, every reading anchored to a key verse
(parsed to internal book/chapter/verse) and a calendar date. Devotional content
is kept clearly separate from the exegesis tools and always attributed.
"""

import re
from typing import Iterator

from ..database import BOOK_ABBREV_MAP

DEVOTIONAL_SOURCES = {
    "morning-evening": {
        "name": "Spurgeon's Morning and Evening",
        "url": "https://raw.githubusercontent.com/dwahrens/morning-and-evening/HEAD/data/m_e.json",
        "filename": "morning_evening.json",
        "parser": "parse_morning_evening",
        "license": "Public Domain (C.H. Spurgeon, 1865)",
    },
}

_TIME = {"am": "morning", "pm": "evening", "morning": "morning", "evening": "evening"}
_MONTHS = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]

# "Book C:V", "Book C:V-W", or "Book C" — book may be numbered ("1 Samuel").
_REF = re.compile(r"^\s*(\d?\s*[A-Za-z][A-Za-z. ]*?)\s+(\d+)(?::(\d+))?", re.UNICODE)


def parse_scripture_ref(ref: str) -> tuple[str | None, int | None, int | None, str]:
    """Parse a plain reference to (book_code, chapter, verse, display) — book/verse nullable."""
    ref = (ref or "").strip().strip('".')
    m = _REF.match(ref)
    if not m:
        return None, None, None, ref
    book_str, chap, verse = m.group(1).strip(), m.group(2), m.group(3)
    code = BOOK_ABBREV_MAP.get(book_str.lower().strip())
    display = f"{book_str} {chap}" + (f":{verse}" if verse else "")
    return code, int(chap), (int(verse) if verse else None), display


def _extract_ref(keyverse: str) -> str:
    """Take the reference off the end of a '"quote" — Book C:V' key-verse string."""
    for dash in ("—", "–", " - "):   # em dash, en dash, spaced hyphen
        if dash in keyverse:
            return keyverse.rsplit(dash, 1)[1].strip()
    return keyverse.strip()


def parse_morning_evening(data: list, source_id: str, source_name: str) -> Iterator[dict]:
    """dwahrens Morning & Evening JSON: [{date, time, month, day, keyverse, body}]."""
    for e in data:
        if not isinstance(e, dict):
            continue
        month = e.get("month")
        day = e.get("day")
        tod = _TIME.get((e.get("time") or "").lower())
        ref_str = _extract_ref(e.get("keyverse") or "")
        code, chap, verse, display = parse_scripture_ref(ref_str)
        month_name = _MONTHS[month - 1].title() if isinstance(month, int) and 1 <= month <= 12 else ""
        title = f"{month_name} {day}".strip() + (f" ({tod.title()})" if tod else "")
        body = re.sub(r"[ \t]+\n", "\n", (e.get("body") or "").replace("\r\n", "\n")).strip()
        if not body:
            continue
        yield {
            "source": source_id, "source_name": source_name, "title": title,
            "month": month, "day": day, "time_of_day": tod,
            "key_ref": display, "book": code, "chapter": chap, "verse": verse,
            "body": body,
        }
