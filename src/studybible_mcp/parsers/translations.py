"""
Parser for readable Bible translations distributed as USFM (from eBible.org).

Yields verse dicts keyed by the internal 'Book.Chapter.Verse' reference in
standard (English) versification, so they align with verses.reference.
"""

import re
import zipfile
from pathlib import Path
from typing import Iterator

from .lxx import usfm_to_internal

# Curated public-domain / open translations: abbrev -> (eBible id, name, license).
TRANSLATIONS = {
    "BSB": ("engbsb", "Berean Standard Bible", "Public Domain"),
    "WEB": ("eng-web", "World English Bible", "Public Domain"),
    "KJV": ("eng-kjv2006", "King James Version", "Public Domain"),
    "ASV": ("eng-asv", "American Standard Version (1901)", "Public Domain"),
    "YLT": ("engylt", "Young's Literal Translation", "Public Domain"),
}

# Footnotes / cross-references / endnotes: drop marker AND content.
_USFM_NOTES = re.compile(r"\\(?:f|fe|x)\b.*?\\(?:f|fe|x)\*", re.S)
# Any remaining USFM marker: drop the marker, keep the enclosed text.
_USFM_MARKER = re.compile(r"\\\+?[a-z0-9]+\*?")


def _clean_usfm(text: str) -> str:
    text = _USFM_NOTES.sub("", text)
    # USFM 3 word markup: \w word|strong="G..." lemma="..."\w*  ->  word
    text = re.sub(r"\\\+?w\s+(.*?)\\\+?w\*",
                  lambda m: m.group(1).split("|", 1)[0], text, flags=re.S)
    # strip any residual word attributes, then remaining markers
    text = re.sub(r'\|[a-z0-9-]+="[^"]*"', "", text)
    text = _USFM_MARKER.sub("", text)
    text = text.replace("¶", " ")  # KJV-style pilcrows
    return re.sub(r"\s+", " ", text).strip()


def parse_usfm_bible(zip_path: Path) -> Iterator[dict]:
    """Yield {reference, book, chapter, verse, text} from a USFM translation zip."""
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".usfm"):
                continue
            txt = z.read(name).decode("utf-8", "replace")
            m = re.search(r"\\id\s+(\w+)", txt)
            if not m:
                continue
            book = usfm_to_internal(m.group(1))
            chapter = None
            parts = re.split(r"(\\c\s+\d+|\\v\s+\d+)", txt)
            i = 1
            while i < len(parts):
                marker = parts[i]
                content = parts[i + 1] if i + 1 < len(parts) else ""
                if marker.lstrip("\\").startswith("c"):
                    chapter = int(marker.split()[1])
                else:  # \v
                    verse = int(marker.split()[1])
                    text = _clean_usfm(content)
                    if chapter is not None and text:
                        yield {
                            "reference": f"{book}.{chapter}.{verse}",
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "text": text,
                        }
                i += 2
