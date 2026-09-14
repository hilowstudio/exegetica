"""
Parser for HelloAO public-domain commentary chapter JSON.

Each chapter's `content` is a list of entries {type:"verse", number, content:[...]}.
Verse-by-verse commentaries (Gill) have one entry per verse; section-level ones
(Matthew Henry) have a few entries, each covering a verse range. We store each
entry as a row spanning [verse_start, verse_end] so a lookup can find the entry
covering a given verse.
"""

from typing import Iterator

# Public-domain commentaries (id -> display name). Tyndale (CC BY) is already
# covered by the Aquifer study notes, so it is not duplicated here. The six from
# HelloAO come in via import_commentaries.py; Spurgeon's Treasury of David (a
# verse-by-verse exposition of the Psalms) comes in via import_treasury.py.
COMMENTARIES = {
    "john-gill": "John Gill's Exposition",
    "matthew-henry": "Matthew Henry's Commentary",
    "jamieson-fausset-brown": "Jamieson-Fausset-Brown",
    "adam-clarke": "Adam Clarke's Commentary",
    "john-calvin": "Calvin's Commentaries",
    "keil-delitzsch": "Keil & Delitzsch (Old Testament)",
    "spurgeon-treasury": "Spurgeon — The Treasury of David (Psalms)",
    "ryle-expository": "J.C. Ryle — Expository Thoughts on the Gospels",
    "hodge-romans": "Charles Hodge — Commentary on Romans",
}


def _join_content(content) -> str:
    parts: list[str] = []
    for item in content or []:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            for key in ("text", "content"):
                v = item.get(key)
                if isinstance(v, str):
                    parts.append(v)
                elif isinstance(v, list):
                    parts.append(_join_content(v))
    return "\n\n".join(p.strip() for p in parts if p and p.strip()).strip()


def parse_commentary_chapter(data: dict, source: str, book: str, chapter: int) -> Iterator[dict]:
    """Yield {source, book, chapter, verse_start, verse_end, text} rows for a chapter."""
    chapter_obj = data.get("chapter", {}) or {}
    content = chapter_obj.get("content", []) or []
    total_verses = chapter_obj.get("numberOfVerses") or data.get("numberOfVerses") or 0

    entries = [e for e in content
               if isinstance(e, dict) and e.get("type") == "verse" and isinstance(e.get("number"), int)]

    for i, e in enumerate(entries):
        start = e["number"]
        body = _join_content(e.get("content", []))
        if not body:
            continue
        end = entries[i + 1]["number"] - 1 if i + 1 < len(entries) else (total_verses or start)
        if end < start:
            end = start
        yield {"source": source, "book": book, "chapter": chapter,
               "verse_start": start, "verse_end": end, "text": body}

    intro = chapter_obj.get("introduction")
    if isinstance(intro, str) and intro.strip():
        yield {"source": source, "book": book, "chapter": chapter,
               "verse_start": 0, "verse_end": 0, "text": intro.strip()}
