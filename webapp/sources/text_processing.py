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


# --- CCEL cache-txt boilerplate ---
# CCEL plain-text exports open with a metadata card (Title/Creator/Rights/...) fenced
# by long underscore rules, and close with an auto-generated index of footnote links
# ("  537. file:///ccel/..."). Neither is part of the work's prose.
_C_RULE = re.compile(r"^\s*_{20,}\s*$")
_C_INDEX_LINE = re.compile(r"^\s*\d+\.\s+file:///", re.I)


def strip_ccel_boilerplate(text: str | None) -> str:
    """Drop CCEL's leading metadata card (through the second underscore rule) and its
    trailing footnote-link index. Returns the trimmed original if the fences aren't found."""
    if not text:
        return ""
    lines = text.split("\n")
    rules = [i for i, ln in enumerate(lines) if _C_RULE.match(ln)]
    if len(rules) >= 2:
        lines = lines[rules[1] + 1:]  # body begins after the card's closing rule
    kept = [ln for ln in lines if not _C_INDEX_LINE.match(ln)]
    return "\n".join(kept).strip()


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
# A keyword heading must be followed by an enumerator (CHAPTER I, BOOK 3, PART FIRST),
# so prose that merely opens with the word ("part of the rest…", "Book of Genesis")
# and reference-style lines are not mistaken for structure.
# An enumerator: arabic, roman, or an ordinal/cardinal word (optionally "the first").
_ENUM = (
    r"(?:\d{1,3}|[ivxlcdm]{1,8}|(?:the\s+)?(?:"
    r"first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|"
    r"thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve))"
)
_MAJOR = r"(?:book|part|volume|canto)"
_MINOR = r"(?:chapter|section|letter|act|scene|lecture|sermon|discourse|homily)"
_NAMED = r"(?:prologue|epilogue|introduction|preface|foreword|argument)"
_re_major = re.compile(rf"^{_MAJOR}\s+{_ENUM}\b", re.I)
_re_minor = re.compile(rf"^{_MINOR}\s+{_ENUM}\b", re.I)
_re_named = re.compile(rf"^{_NAMED}\b", re.I)
_re_roman = re.compile(r"^[ivxlcdm]{1,7}\.?$", re.I)
_re_arabic = re.compile(r"^\d{1,3}\.?$")
# A genuine heading is short and clean. Cross-reference prose ("Book 2, chap. 1--6. See
# also…") starts like a heading but carries commas, parens, ranges, or reference tokens —
# reject those so scripture/cross-refs in the body don't read as structure.
_XREF = re.compile(r"[,)(]|--|[–—]|\b(?:chap|chaps|vv?|pp|sec|cf|see|note|vol)\b\.?", re.I)


def _kw_heading(low: str, kw_re: re.Pattern) -> bool:
    return bool(kw_re.match(low)) and len(low) <= 50 and not _XREF.search(low)


def _heading_level(line: str) -> str | None:
    """Classify a line's heading level, or None. Levels, coarsest first: 'major'
    (book/part/volume), 'minor' (chapter/section/…), 'named' (prologue/preface/…),
    'roman'/'arabic' (bare numerals — the weakest, page-number-shaped signals)."""
    s = line.strip()
    if not s or len(s) > 80:
        return None
    low = s.lower()
    if _kw_heading(low, _re_major):
        return "major"
    if _kw_heading(low, _re_minor):
        return "minor"
    if _re_named.match(low) and not _XREF.search(low) and len(low) <= 50:
        return "named"
    # Bare Roman numeral: require a trailing period OR length >= 2, so a lone "I"
    # pronoun on its own line isn't mistaken for a heading.
    if _re_roman.match(low) and (low.endswith(".") or len(low.rstrip(".")) >= 2):
        return "roman"
    if _re_arabic.match(s):
        return "arabic"
    return None


# A real chapter's body dwarfs a table-of-contents line; dropping sub-threshold sections
# removes TOC entries and stray front-matter headings.
_MIN_SECTION_CHARS = 200
# A sane book segments into a few to a few dozen sections. A count past this means the
# heading tier is too fine (e.g. every chapter of a 13-book work, or PDF page numbers) —
# so we prefer a coarser tier and, failing that, fall back to the whole body.
_MAX_SECTIONS = 60
# Heading tiers from coarsest/strongest to finest/weakest. We segment at the first tier
# that yields a sane section count, so Confessions splits into its 13 books (not 200+
# chapters) and a plain novel still splits into its chapters.
_TIERS = (
    ("major",),
    ("minor", "named"),
    ("minor", "named", "roman"),
    ("minor", "named", "roman", "arabic"),
)


def _segment_pass(lines: list[str], levels: set[str]) -> list[dict]:
    heads = [i for i, ln in enumerate(lines) if _heading_level(ln) in levels]
    if not heads:
        return []
    sections: list[dict] = []
    for n, li in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        sections.append({"title": lines[li].strip(), "text": "\n".join(lines[li:end]).strip()})
    return [s for s in sections if len(s["text"]) >= _MIN_SECTION_CHARS]


def segment_into_chapters(text: str | None) -> list[dict]:
    """Split into structural sections at detected heading lines (heading inclusive),
    choosing the coarsest heading tier that yields a plausible section count. No usable
    headings → one "Full text" section. Returns [{section_number, title, text}].
    (Alignment to a published TOC for cleaner titles is a later refinement.)
    """
    if not text:
        return []
    lines = text.split("\n")
    kept: list[dict] = []
    for tier in _TIERS:
        candidate = _segment_pass(lines, set(tier))
        if 2 <= len(candidate) <= _MAX_SECTIONS:
            kept = candidate
            break
    if not kept:  # no tier produced a plausible split → treat the body as one section
        return [{"section_number": 1, "title": "Full text", "text": text.strip()}]
    for i, s in enumerate(kept):
        s["section_number"] = i + 1
    return kept
