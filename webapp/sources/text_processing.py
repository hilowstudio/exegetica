"""Pure text-processing for source full text — boilerplate stripping, overlapping
chunking, and heading-based chapter segmentation. Ported from quillnext
`src/lib/sources/text-processing.ts`. Dependency-free; never raises.
"""
from __future__ import annotations

import re

# --- Project Gutenberg boilerplate markers (tolerant to decades of format drift) ---
_G_START = re.compile(r"\*{2,}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{2,}", re.I | re.S)
_G_END = re.compile(r"\*{2,}\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{2,}", re.I | re.S)
_G_END_FALLBACK = re.compile(r"\n\s*End of (?:the )?Project Gutenberg.*$", re.I | re.S)


def strip_gutenberg_boilerplate(text: str | None) -> str:
    """Keep only the body between the START and END markers (with a loose-end
    fallback). Returns the trimmed original if no markers are found."""
    if not text:
        return ""
    m = _G_START.search(text)
    if m:
        text = text[m.end():]
    m = _G_END.search(text)
    if m:
        text = text[: m.start()]
    else:
        text = _G_END_FALLBACK.sub("", text)
    return text.strip()


def chunk_text(text: str | None, window: int = 300, overlap: int = 50) -> list[str]:
    """Overlapping word windows (300 words / 50 overlap / 250 step); drop <50-char
    chunks. Identical granularity to the transcript chunker so book/video match."""
    words = (text or "").split()
    step = window - overlap
    out: list[str] = []
    i, n = 0, len(words)
    while i < n:
        chunk = " ".join(words[i : i + window])
        if len(chunk) >= 50:
            out.append(chunk)
        if i + window >= n:
            break
        i += step
    return out


# --- Heading detection for chapter segmentation ---
_KW = r"(?:chapter|book|part|section|letter|canto|act|scene)"
_NAMED = r"(?:prologue|epilogue|introduction|preface|foreword|argument)"
_re_kw = re.compile(rf"^{_KW}\b", re.I)
_re_named = re.compile(rf"^{_NAMED}\b", re.I)
_re_roman = re.compile(r"^[ivxlcdm]{1,7}\.?$", re.I)
_re_arabic = re.compile(r"^\d{1,3}\.?$")


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 80:
        return False
    low = s.lower()
    if _re_named.match(low) or _re_kw.match(low):
        return True
    # Bare Roman numeral: require a trailing period OR length >= 2, so a lone "I"
    # pronoun on its own line isn't mistaken for a heading.
    if _re_roman.match(low) and (low.endswith(".") or len(low.rstrip(".")) >= 2):
        return True
    if _re_arabic.match(s):
        return True
    return False


# A real chapter's body dwarfs a table-of-contents line; dropping sub-threshold
# sections removes TOC entries and stray front-matter headings. Matches the 200-char
# content-leaf floor quillnext uses in its OpenStax/LibreTexts adapters.
_MIN_SECTION_CHARS = 200


def segment_into_chapters(text: str | None) -> list[dict]:
    """Split into structural sections at detected heading lines (heading inclusive),
    then drop sub-threshold sections (TOC entries / front-matter headings). No usable
    headings → one "Full text" section. Returns [{section_number, title, text}].
    (Alignment to a published TOC for cleaner titles is a later refinement.)
    """
    if not text:
        return []
    lines = text.split("\n")
    heads = [i for i, ln in enumerate(lines) if _is_heading(ln)]
    if not heads:
        return [{"section_number": 1, "title": "Full text", "text": text.strip()}]
    sections: list[dict] = []
    for n, li in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        sections.append({"title": lines[li].strip(), "text": "\n".join(lines[li:end]).strip()})

    kept = [s for s in sections if len(s["text"]) >= _MIN_SECTION_CHARS]
    if not kept:  # e.g. only a TOC was detected — fall back to the whole body
        return [{"section_number": 1, "title": "Full text", "text": text.strip()}]
    for i, s in enumerate(kept):
        s["section_number"] = i + 1
    return kept
