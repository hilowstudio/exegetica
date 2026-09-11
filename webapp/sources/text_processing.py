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
# Verse tokens must carry their period ("v." / "vv.") so the roman numeral V in a real
# heading ("Book V") is not mistaken for a cross-reference.
_XREF = re.compile(r"[,)(]|--|[–—]|\bvv?\.|\b(?:chap|chaps|pp|sec|cf|see|note|vol)\b\.?", re.I)


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


_ORDINALS = {w: i + 1 for i, w in enumerate(
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth "
    "thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth".split())}
_CARDINALS = {w: i + 1 for i, w in enumerate(
    "one two three four five six seven eight nine ten eleven twelve".split())}


def _roman_to_int(s: str) -> int | None:
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    if any(ch not in vals for ch in s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total or None


def _enum_to_int(tok: str) -> int | None:
    tok = tok.rstrip(".").lower()
    if tok.isdigit():
        return int(tok)
    if tok in _ORDINALS:
        return _ORDINALS[tok]
    if tok in _CARDINALS:
        return _CARDINALS[tok]
    if re.fullmatch(r"[ivxlcdm]+", tok):
        return _roman_to_int(tok)
    return None


def _major_ordinal(title: str) -> int | None:
    """The numeric value of a major heading's enumerator (Book Third → 3, BOOK 3 → 3,
    Book III → 3), used to fold a work's front-matter outline, real body, and back-matter
    index for the same division into one section."""
    m = re.match(rf"^{_MAJOR}\s+(?:the\s+)?([ivxlcdm]+|\d+|[a-z]+)", title.strip(), re.I)
    return _enum_to_int(m.group(1)) if m else None


def _entry_ordinal(title: str) -> int | None:
    """Enumerator of any heading or TOC entry — major, minor, or a bare numeral —
    e.g. 'Chapter V. …'→5, 'BOOK 3'→3, 'IV. The Storm'→4. Used to align a body section
    to its table-of-contents entry by number."""
    t = title.strip()
    m = re.match(rf"^(?:{_MAJOR}|{_MINOR})\s+(?:the\s+)?([ivxlcdm]+|\d+|[a-z]+)", t, re.I)
    if m:
        return _enum_to_int(m.group(1))
    m = re.match(r"^(?:the\s+)?([ivxlcdm]+|\d+)\b", t, re.I)  # bare leading numeral
    return _enum_to_int(m.group(1)) if m else None


def _descriptive_tail(title: str) -> str:
    """The part of a heading beyond its keyword + enumerator + punctuation — the actual
    words of a title. '' when the heading is only a label ('Chapter 5', 'Book I')."""
    t = re.sub(rf"^(?:{_MAJOR}|{_MINOR})\b", "", title.strip(), flags=re.I)
    t = re.sub(r"^\s*(?:the\s+)?(?:[ivxlcdm]+|\d+|[a-z]+)\b", "", t, flags=re.I)
    t = re.sub(r"^[\s.:)—–-]+", "", t)
    return t.strip() if re.search(r"[A-Za-z]{2,}", t) else ""


def _is_descriptive(title: str) -> bool:
    return bool(_descriptive_tail(title))


def _align_titles(sections: list[dict], toc: list[str] | None) -> list[dict]:
    """Replace a section's terse label ('Chapter 5') with a richer table-of-contents title
    ('Chapter 5. The Confrontation') — conservatively, so a wrong TOC never mis-titles a
    section. Two safe paths: (1) by enumerator, when both carry the same number; (2) purely
    positional, only when the TOC and sections line up 1:1. A section that already has a
    descriptive title is left alone."""
    if not toc:
        return sections
    toc = [t.strip() for t in toc if t and t.strip()]
    by_num = {}
    for t in toc:
        n = _entry_ordinal(t)
        if n is not None and _is_descriptive(t):
            by_num.setdefault(n, t)
    positional = len(toc) == len(sections) and all(_is_descriptive(t) for t in toc)
    for i, s in enumerate(sections):
        if _is_descriptive(s["title"]):
            continue  # body heading is already rich — trust it over the TOC
        num = _entry_ordinal(s["title"])
        if num is not None and num in by_num:
            s["title"] = by_num[num]
        elif positional:
            s["title"] = toc[i]
    return sections


def _dedupe_major(sections: list[dict]) -> list[dict]:
    """A top-level division (book/part) is unique, so if the same one appears more than
    once — a front-matter argument, the real body, a back-matter index — keep only the
    occurrence with the largest body. Unkeyed headings pass through untouched."""
    best: dict = {}
    passthrough: list[dict] = []
    for pos, s in enumerate(sections):
        k = _major_ordinal(s["title"])
        if k is None:
            passthrough.append((pos, s))
            continue
        if k not in best or len(s["text"]) > len(best[k][1]["text"]):
            best[k] = (pos, s)
    merged = list(best.values()) + passthrough
    return [s for _pos, s in sorted(merged, key=lambda t: t[0])]


def segment_into_chapters(text: str | None, toc: list[str] | None = None) -> list[dict]:
    """Split into structural sections at detected heading lines (heading inclusive),
    choosing the coarsest heading tier that yields a plausible section count, folding
    duplicate top-level divisions (front-matter outline / real body / back-matter index) to
    their real body, and — when a published table of contents is supplied (EPUB nav / PDF
    outline) or embedded in the text — upgrading terse section labels to their descriptive
    TOC titles. No usable headings → one "Full text" section. Returns
    [{section_number, title, text}].
    """
    if not text:
        return []
    lines = text.split("\n")
    kept: list[dict] = []
    for tier in _TIERS:
        candidate = _segment_pass(lines, set(tier))
        if tier == ("major",):  # fold duplicate top-level divisions to their real bodies
            candidate = _dedupe_major(candidate)
        if 2 <= len(candidate) <= _MAX_SECTIONS:
            kept = candidate
            break
    if not kept:  # no tier produced a plausible split → treat the body as one section
        return [{"section_number": 1, "title": "Full text", "text": text.strip()}]
    kept = _align_titles(kept, toc)  # titles enrich only from a structured TOC (nav/outline)
    for i, s in enumerate(kept):
        s["section_number"] = i + 1
    return kept
