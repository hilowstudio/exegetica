"""
Parsers for the Greek Septuagint (Swete) text and the Copenhagen versification
mappings.

- `parse_swete_lxx()` reconstructs verses from eliranwong/LXX-Swete-1930's two
  CSVs: a versification index (word-index -> 'Book.Chapter:Verse') and a word
  list (word-index -> Greek token). A verse is the span of words between one
  versification entry and the next.
- `parse_versification_map()` reads Copenhagen's lxx.json and eng.json and
  composes an LXX -> standard(English) reference map for the verses whose
  numbering diverges (Psalms, Jeremiah, Daniel, ...). Each scheme maps to a
  common base; composing lxx->base with the inverse of eng->base yields lxx->eng.
"""

import json
import re
import zipfile
from pathlib import Path
from typing import Iterator

# Swete book codes that differ from the internal (STEPBible) codes used elsewhere.
_SWETE_BOOK_FIX = {"Sol": "Sng", "Joe": "Jol", "Eze": "Ezk"}

# Copenhagen USFM codes that are not just the title-cased internal code.
_USFM_SPECIAL = {"DAG": "Dan"}  # Daniel (Greek) -> canonical Daniel


def swete_book_to_internal(code: str) -> str:
    return _SWETE_BOOK_FIX.get(code, code)


def usfm_to_internal(code: str) -> str:
    return _USFM_SPECIAL.get(code, code.title())


def parse_swete_lxx(versification_path: Path, words_path: Path) -> Iterator[dict]:
    """Yield LXX verse dicts (reference, book, chapter, verse, text_greek).

    reference is the internal 'Book.Chapter.Verse' form in LXX versification.
    """
    # word-index -> Greek token
    words: dict[int, str] = {}
    with open(words_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            idx, tok = line.split("\t", 1)
            if idx.isdigit():
                words[int(idx)] = tok

    if not words:
        return
    max_idx = max(words)

    # (start_index, ref) entries, in file order (already sorted by index)
    entries: list[tuple[int, str]] = []
    with open(versification_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            idx, ref = line.split("\t", 1)
            if idx.isdigit():
                entries.append((int(idx), ref.strip()))
    entries.sort(key=lambda e: e[0])

    for i, (start, ref) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else max_idx + 1
        tokens = [words[j] for j in range(start, end) if j in words]
        text = " ".join(tokens).strip()
        if not text:
            continue
        # ref is 'Psa.9:1' -> book='Psa', chapter=9, verse=1
        if "." not in ref or ":" not in ref:
            continue
        book_raw, cv = ref.split(".", 1)
        chap_s, verse_s = cv.split(":", 1)
        if not (chap_s.isdigit() and verse_s.isdigit()):
            continue
        book = swete_book_to_internal(book_raw)
        chapter, verse = int(chap_s), int(verse_s)
        yield {
            "reference": f"{book}.{chapter}.{verse}",
            "book": book,
            "chapter": chapter,
            "verse": verse,
            "text_greek": text,
        }


def _expand_refs(ref_str: str) -> list[str]:
    """Expand a Copenhagen ref token into internal per-verse refs.

    'PSA 9:22' -> ['Psa.9.22']
    'PSA 9:22-39' -> ['Psa.9.22', ..., 'Psa.9.39']   (within-chapter range)
    'JER 26:1-28' -> ['Jer.26.1', ..., 'Jer.26.28']
    Cross-chapter ranges (rare here) fall back to the start verse only.
    """
    def _num(tok: str) -> int | None:
        # Leading integer, tolerating subverse letters ('1a' -> 1).
        m = re.match(r"^\s*(\d+)", tok)
        return int(m.group(1)) if m else None

    try:
        book_raw, rest = ref_str.split(" ", 1)
    except ValueError:
        return []
    book = usfm_to_internal(book_raw)
    rest = rest.strip()
    if "-" not in rest:
        if ":" not in rest:
            return []
        chap, verse = rest.split(":", 1)
        c, v = _num(chap), _num(verse)
        return [f"{book}.{c}.{v}"] if c is not None and v is not None else []
    start, end = rest.split("-", 1)
    if ":" not in start:
        return []
    sc_s, sv_s = start.split(":", 1)
    ec_s, ev_s = end.split(":", 1) if ":" in end else (sc_s, end)
    sc, sv, ec, ev = _num(sc_s), _num(sv_s), _num(ec_s), _num(ev_s)
    if None in (sc, sv, ec, ev):
        return []
    if sc != ec:
        # Cross-chapter range: not enumerable without chapter lengths; anchor start.
        return [f"{book}.{sc}.{sv}"]
    return [f"{book}.{sc}.{v}" for v in range(sv, ev + 1)]


def _build_scheme_to_base(mapped_verses: dict) -> dict[str, str]:
    """Expand a scheme's mappedVerses into per-verse {scheme_ref: base_ref}."""
    out: dict[str, str] = {}
    for src, dst in mapped_verses.items():
        src_refs = _expand_refs(src)
        dst_refs = _expand_refs(dst)
        if len(src_refs) == len(dst_refs) and src_refs:
            for s, d in zip(src_refs, dst_refs):
                out[s] = d
    return out


def parse_versification_map(lxx_json_path: Path, eng_json_path: Path) -> Iterator[dict]:
    """Yield {lxx_ref, standard_ref, base_ref} rows for divergent verses.

    standard_ref is the English-scheme reference (matches verses.reference);
    base_ref is the common (Hebrew/original) base used by Copenhagen.
    """
    lxx = json.loads(Path(lxx_json_path).read_text(encoding="utf-8"))
    eng = json.loads(Path(eng_json_path).read_text(encoding="utf-8"))

    lxx_to_base = _build_scheme_to_base(lxx.get("mappedVerses", {}))
    eng_to_base = _build_scheme_to_base(eng.get("mappedVerses", {}))
    base_to_eng = {base: e for e, base in eng_to_base.items()}

    for lxx_ref, base_ref in lxx_to_base.items():
        standard_ref = base_to_eng.get(base_ref, base_ref)  # identity if eng == base
        yield {
            "lxx_ref": lxx_ref,
            "standard_ref": standard_ref,
            "base_ref": base_ref,
        }


# ---------------------------------------------------------------------------
# Brenton English Septuagint (USFM) — verse-by-verse English of the Greek LXX,
# in LXX versification (151 Psalms, Jeremiah in LXX order).
# ---------------------------------------------------------------------------

# Footnotes/cross-references/endnotes: remove the marker AND its content.
_USFM_NOTES = re.compile(r"\\(?:f|fe|x)\b.*?\\(?:f|fe|x)\*", re.S)
# Any remaining USFM marker (\p, \q1, \sc, \sc*, \add, \nd, \wj, \+xt, ...):
# drop the marker, keep the enclosed text.
_USFM_MARKER = re.compile(r"\\\+?[a-z0-9]+\*?")


def _clean_usfm_text(text: str) -> str:
    text = _USFM_NOTES.sub("", text)
    text = _USFM_MARKER.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_brenton(zip_path: Path) -> Iterator[dict]:
    """Parse Brenton's English Septuagint (a USFM zip) into LXX-numbered verses.

    Yields {reference, book, chapter, verse, text_english} with the reference in
    the internal 'Book.Chapter.Verse' form and LXX numbering, so it aligns with
    the Swete Greek rows in lxx_verses.
    """
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
                    english = _clean_usfm_text(content)
                    if chapter is not None and english:
                        yield {
                            "reference": f"{book}.{chapter}.{verse}",
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "text_english": english,
                        }
                i += 2
