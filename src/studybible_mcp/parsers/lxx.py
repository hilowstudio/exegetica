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

import bisect
import json
import math
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Iterator

# Swete book codes that differ from the internal (STEPBible) codes used elsewhere.
_SWETE_BOOK_FIX = {"Sol": "Sng", "Joe": "Jol", "Eze": "Ezk", "Nah": "Nam"}

# Copenhagen USFM codes that are not just the title-cased internal code.
_USFM_SPECIAL = {"DAG": "Dan"}  # Daniel (Greek) -> canonical Daniel


def swete_book_to_internal(code: str) -> str:
    return _SWETE_BOOK_FIX.get(code, code)


def usfm_to_internal(code: str) -> str:
    return _USFM_SPECIAL.get(code, code.title())


def parse_swete_lxx(versification_path: Path, words_path: Path, include_empty: bool = False) -> Iterator[dict]:
    """Yield LXX verse dicts (reference, book, chapter, verse, text_greek).

    reference is the internal 'Book.Chapter.Verse' form in LXX versification. The digitization
    numbers some verses with no Greek (Psalm 43:8, 1 Kingdoms 17:12-31), each holding one empty
    word. With include_empty those verses come through with text_greek ''.
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
        text = " ".join(t for t in tokens if t).strip()
        if not text and not include_empty:
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


# Additions an English (WEB) reference folds into a chapter of another book, and the Swete book that
# prints each on its own: Susanna is Dan 13, Bel Dan 14, the Letter of Jeremiah Baruch 6, Psalm 151 Ps2 1.
_FOLDED_IN_SWETE = {("Dan", "13"): ("Sus", "1"), ("Dan", "14"): ("Bel", "1"), ("Bar", "6"): ("Epj", "1"),
                    ("Ps2", "1"): ("Psa", "151")}


def swete_ref(ref: str) -> str:
    """A Copenhagen LXX reference, or an English one, in Swete's numbering where the book or chapter differs.

    Copenhagen's Greek Esther (Esg) is Swete's Est, and its Ezra (2 Esdras) runs on into Nehemiah as
    chapters 11-23, which Swete prints as Neh 1-13. The additions English references fold into another
    book (Susanna as Dan 13) are separate books in Swete. Verse numbers pass through unchanged.
    """
    book, _, rest = ref.partition(".")
    chapter, _, verse = rest.partition(".")
    if book == "Esg":
        return f"Est.{rest}"
    if book == "Ezr" and chapter.isdigit() and int(chapter) > 10:
        return f"Neh.{int(chapter) - 10}.{verse}"
    if (book, chapter) in _FOLDED_IN_SWETE:
        new_book, new_chapter = _FOLDED_IN_SWETE[(book, chapter)]
        return f"{new_book}.{new_chapter}.{verse}"
    return ref


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
# Brenton English Septuagint (USFM): verse-by-verse English of the Greek LXX, in
# the Greek order (151 Psalms, Jeremiah in LXX order) but often not with Swete's
# verse numbers. See align_brenton below.
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
    """Parse Brenton's English Septuagint (a USFM zip) into verses, in file order.

    Yields {reference, book, chapter, verse, letter, text_english}. Brenton splits some verses
    into lettered parts (Psalm 144:13a, 1 Kings 2:35a-o); each part is its own row with its
    letter, and the reference keeps it ('Psa.144.13a'). Brenton's numbering is often not
    Swete's, so pair the two with align_brenton, not by reference.
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
            parts = re.split(r"(\\c\s+\d+|\\v\s+\d+[a-z]*)", txt)
            i = 1
            while i < len(parts):
                marker = parts[i]
                content = parts[i + 1] if i + 1 < len(parts) else ""
                if marker.lstrip("\\").startswith("c"):
                    chapter = int(marker.split()[1])
                else:  # \v
                    label = marker.split()[1]
                    verse = int(re.match(r"\d+", label).group())
                    letter = label[len(str(verse)):]
                    english = _clean_usfm_text(content)
                    if chapter is not None and english:
                        yield {
                            "reference": f"{book}.{chapter}.{label}",
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "letter": letter,
                            "text_english": english,
                        }
                i += 2


# ---------------------------------------------------------------------------
# Pairing Brenton's English with Swete's Greek
# ---------------------------------------------------------------------------
#
# Brenton's verse numbers often differ from Swete's. Brenton numbers some chapters as English
# Bibles do (Isaiah 9, Malachi 4, Numbers 16-17), splits additions into lettered verses that
# Swete prints inside one verse (1 Kings 2:35a-o, Esther 1:1b-s, Psalm 144:13a), and translates
# Theodotion's Daniel where Swete's "Dan" is the Old Greek. Pairing by verse number put the wrong
# English beside the Greek, a verse or more off for whole chapters. align_brenton pairs them by
# content instead, one book at a time: a dynamic-programming alignment, after Gale and Church's
# sentence alignment, on text length, the proper names both sides share, and a small preference
# for matching verse numbers.

# Swete book -> the Brenton book that translates it, where the codes differ. Swete prints both
# Greek texts of Daniel, Susanna, and Bel (Dan, Sus, Bel the Old Greek; Dat, Sut, Bet Theodotion),
# and Brenton translated Theodotion's, so the Old Greek books get no English.
BRENTON_BOOK_FOR = {"Est": "Esg", "Epj": "Lje", "Dat": "Dan", "Sut": "Sus", "Bet": "Bel"}
NO_BRENTON = {"Dan", "Sus", "Bel"}

_GREEK_LATIN = dict(zip("αβγδεζηθικλμνξοπρστυφχψως",
                        ["a", "b", "g", "d", "e", "z", "e", "t", "i", "k", "l", "m", "n", "x", "o", "p", "r",
                         "s", "t", "u", "f", "k", "ps", "o", "s"]))
_ENGLISH_STOP = {
    "and", "for", "but", "then", "now", "lord", "god", "thou", "thy", "when", "who", "what", "behold",
    "therefore", "because", "let", "his", "her", "they", "these", "this", "there", "that", "the", "she",
    "you", "wherefore", "moreover", "after", "before", "all", "every", "with", "from", "thus", "how",
    "why", "whosoever", "whoso", "are", "was", "will", "shall", "not", "neither", "nor", "yea", "also",
    "again", "until", "unto", "upon", "even", "said", "say", "saying", "hear", "come",
}


def _name_key(latin: str) -> str:
    """A proper name reduced to its first consonants, so Greek and English spellings meet:
    Δαυείδ and David are both 'dvd', Ναβουχοδονοσόρ and Nabuchodonosor both 'nbkd'."""
    latin = latin.lower().replace("ou", "u").replace("ph", "f").replace("th", "t").replace("ch", "k")
    latin = latin.replace("c", "k").replace("q", "k").replace("j", "i").replace("w", "v").replace("æ", "e")
    out: list[str] = []
    for i, ch in enumerate(latin):
        if ch == "u" and i and latin[i - 1] in "ae":  # Δαυείδ, Λευί: upsilon after a or e sounds as v
            ch = "v"
        if ch in "aeiouyh" or not ch.isalpha():
            continue
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)[:4]


def _greek_names(text: str) -> frozenset:
    keys = set()
    for w in re.findall(r"\w+", text):
        if not w[:1].isupper() or w.isupper():  # skip lowercase words and Swete's capitalized openings
            continue
        plain = "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c)).lower()
        key = _name_key("".join(_GREEK_LATIN.get(c, "") for c in plain))
        if len(key) >= 3:
            keys.add(key)
    return frozenset(keys)


def _english_names(text: str) -> frozenset:
    keys = set()
    for w in re.findall(r"[A-Za-zæÆ]+", text):
        if w[:1].isupper() and len(w) >= 3 and w.lower() not in _ENGLISH_STOP:
            key = _name_key(w)
            if len(key) >= 3:
                keys.add(key)
    return frozenset(keys)


_SIGMA2 = 2 * 0.3 ** 2   # spread of log(English length / expected length) for a true pair
_SKIP = 4.0              # a verse on one side with nothing on the other
_MERGE = 1.5             # each extra verse joined into a pair
_SUBVERSE_MERGE = 0.2    # joining lettered parts (12a, 12b) to the verse they belong to
_MAX_RUN = 4             # verses joined in an ordinary merge
_SAME_NUMBER = 0.3       # the preference for pairing verses that carry the same number


def align_verses(greek: list[dict], english: list[dict], band: int = 100, max_greek: int = 2) -> dict[int, list[int]]:
    """Align one book: {index into greek: [indexes into english]}.

    greek rows carry chapter, verse, and text_greek ('' where Swete has the verse number but no
    words); english rows carry chapter, verse, letter, and text_english, both in reading order.
    A pair can join up to max_greek Greek verses (the English goes to the first) and up to
    _MAX_RUN English verses, or any run of lettered parts of one verse. A Greek verse with no
    words takes English only at its own number. The search stays within `band` verses of the
    diagonal.
    """
    n, m = len(greek), len(english)
    if not n or not m:
        return {}
    glen = [len(g["text_greek"] or "") for g in greek]
    elen = [len(e["text_english"]) for e in english]
    ratio = sum(elen) / max(sum(glen), 1)
    gnames = [_greek_names(g["text_greek"] or "") for g in greek]
    enames = [_english_names(e["text_english"]) for e in english]
    gsum, esum = [0], [0]
    for x in glen:
        gsum.append(gsum[-1] + x)
    for x in elen:
        esum.append(esum[-1] + x)

    def number(row):
        return row["chapter"], row["verse"]

    # parent[j]: where the run of lettered parts ending at english[j] begins (its unlettered verse)
    parent = list(range(m))
    for j in range(1, m):
        e = english[j]
        if e.get("letter") and number(english[j - 1]) == number(e):
            parent[j] = parent[j - 1]

    def pair(i0: int, i1: int, j0: int, j1: int) -> float:
        g_len, e_len = gsum[i1] - gsum[i0], esum[j1] - esum[j0]
        same = number(greek[i0]) == number(english[j0])
        if g_len == 0:
            return 0.1 if same and i1 - i0 == 1 else 9.0
        x = math.log((e_len + 40) / (ratio * g_len + 40))
        c = x * x / _SIGMA2
        gn = gnames[i0] if i1 - i0 == 1 else frozenset().union(*gnames[i0:i1])
        en = enames[j0] if j1 - j0 == 1 else frozenset().union(*enames[j0:j1])
        if gn & en:
            c -= 2.0
        elif gn and en:
            c += 1.0
        if same:
            c -= _SAME_NUMBER
        if j1 - j0 > 1:
            run = english[j0 + 1:j1]
            lettered = all(e.get("letter") and number(e) == number(english[j0]) for e in run)
            c += _SUBVERSE_MERGE if lettered else _MERGE * (j1 - j0 - 1)
        if i1 - i0 > 1:
            c += _MERGE * (i1 - i0 - 1)
        return c

    cost: dict[tuple[int, int], float] = {(0, 0): 0.0}
    back: dict[tuple[int, int], tuple[int, int]] = {}
    for i in range(n + 1):
        mid = i * m // n
        for j in range(max(0, mid - band), min(m, mid + band) + 1):
            if i == 0 and j == 0:
                continue
            best, arg = math.inf, None
            starts = {j - dj for dj in range(1, _MAX_RUN + 1) if j - dj >= 0}
            if j and parent[j - 1] < j - 1:
                starts.add(parent[j - 1])
            steps: list[tuple[int, int, float | None]] = []
            if j:
                steps.append((i, j - 1, _SKIP))                         # English with no Greek
            if i:
                steps.append((i - 1, j, 0.3 if not glen[i - 1] else _SKIP))  # Greek with no English
            for di in range(1, min(max_greek, i) + 1):
                steps.extend((i - di, pj, None) for pj in starts)
            for pi, pj, c in steps:
                prev = cost.get((pi, pj))
                if prev is None:
                    continue
                total = prev + (c if c is not None else pair(pi, i, pj, j))
                if total < best:
                    best, arg = total, (pi, pj)
            if arg is not None:
                cost[(i, j)] = best
                back[(i, j)] = arg
    if (n, m) not in cost:
        if band < max(n, m):
            return align_verses(greek, english, band * 3, max_greek)
        return {}
    pairs: dict[int, list[int]] = {}
    i, j = n, m
    while (i, j) != (0, 0):
        pi, pj = back[(i, j)]
        if i > pi and j > pj:
            pairs[pi] = list(range(pj, j))
        i, j = pi, pj
    return pairs


def brenton_for(swete_book: str, brenton: dict[str, list[dict]]) -> list[dict]:
    """The Brenton verses that translate a Swete book, in order."""
    if swete_book in NO_BRENTON:
        return []
    if swete_book == "Sip":  # Sirach's prologue: Brenton's Sir 1:1 through 1:1g
        return [e for e in brenton.get("Sir", []) if (e["chapter"], e["verse"]) == (1, 1) and e["letter"] < "h"]
    rows = brenton.get(BRENTON_BOOK_FOR.get(swete_book, swete_book), [])
    if swete_book == "Sir":  # after the prologue, Brenton's 1:1h is Sirach 1:1
        rows = [dict(e, letter="") if (e["chapter"], e["verse"], e["letter"]) == (1, 1, "h") else e
                for e in rows if not ((e["chapter"], e["verse"]) == (1, 1) and e["letter"] < "h")]
    if swete_book == "Ezr":  # Brenton's Ezra runs on into Nehemiah as chapters 11-23
        rows = [e for e in rows if e["chapter"] <= 10]
    return rows


def align_brenton(greek: list[dict], brenton_rows: list[dict]) -> dict[str, str]:
    """{Swete reference: Brenton English} for every Greek verse the English pairs with.

    greek is parse_swete_lxx(..., include_empty=True) output; brenton_rows is parse_brenton output.
    """
    by_book_g: dict[str, list[dict]] = {}
    for g in greek:
        by_book_g.setdefault(g["book"], []).append(g)
    by_book_e: dict[str, list[dict]] = {}
    for e in brenton_rows:
        by_book_e.setdefault(e["book"], []).append(e)

    out: dict[str, str] = {}
    for book, rows in by_book_g.items():
        english = brenton_for(book, by_book_e)
        found = align_verses(rows, english, max_greek=4 if book == "Sip" else 2)
        for gi, ejs in found.items():
            out[rows[gi]["reference"]] = " ".join(english[j]["text_english"] for j in ejs)
    return out


# ---------------------------------------------------------------------------
# Checking the English -> Swete routes by content
# ---------------------------------------------------------------------------
#
# Copenhagen's map is in the numbering of a modern LXX edition, and Swete's numbering is not always the
# same: Swete prints Malachi 4 as English Bibles do but with the LXX order (English 4:4 is Swete 4:6),
# numbers Daniel 3:24-90 for the Prayer of Azariah (English 3:24 is 3:91), and numbers Job 40-41 and parts
# of Jeremiah, Exodus, 3 Kingdoms, Proverbs, and 1 Esdras differently. Where it differs the map sends an
# English verse to the wrong Greek verse or to none. Every Swete verse now carries Brenton's English, and
# Brenton follows the King James wording closely, so comparing the two finds the Swete verse that holds
# each English verse. content_routes keeps the map's route unless a nearby verse reads clearly better.

_ROUTE_STOP = set(
    "the and of to in that shall he his him they them for unto with be is not all which their thou thy thee "
    "ye you was were are have hath had from as by this but on upon will my me it an so said say then also "
    "or there when what who whom out up into us we our your yea even".split())


def _route_words(text: str) -> frozenset:
    words = set()
    for w in re.findall(r"[a-z]+", (text or "").lower()):
        if len(w) < 3 or w in _ROUTE_STOP:
            continue
        for suffix in ("eth", "est", "ed", "es", "s"):
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                w = w[:-len(suffix)]
                break
        words.add(w)
    return frozenset(words)


def _overlap(a: frozenset, b: frozenset) -> float:
    return len(a & b) / math.sqrt(len(a) * len(b)) if a and b else 0.0


_FLAG = (0.3, 0.15)     # a nearby verse scores at least 0.3, and 0.15 above the routed one
_STRONG = (0.6, 0.3)    # enough on its own
_NEIGHBOURS = 2         # or this many English verses within three share the same shift
_MERGED = 0.45          # or the routed verse is not in Swete, and the text sits a verse or two away


def content_routes(english: dict[str, str], routed: dict[str, str], greek_english: dict[str, str],
                   swete_refs: set[str]) -> dict[str, tuple[str, float]]:
    """{English verse: (Swete verse, score)} where content finds a better Swete verse than the route.

    english holds the English text by English reference; routed the Swete verse the map gives each
    (identity where it gives none); greek_english Brenton's English by Swete reference; swete_refs every
    Swete reference. Candidates are the Swete verses in the routed verse's book, in its chapter and the
    English verse's chapter and those beside them. A candidate replaces the route when it scores _STRONG,
    when the English verses around it shift by the same amount (a renumbered block, as in Daniel 3-4),
    when the routed verse is not in Swete and the text sits in a verse beside it, or when another English
    verse has taken the routed verse (a reordering, as in Malachi 4). A single look-alike (one tribe in a
    list, a repeated refrain) stays put.
    """
    order: dict[str, list[tuple[int, int, str]]] = {}
    for ref in greek_english:
        book, ch, v = ref.split(".")
        order.setdefault(book, []).append((int(ch), int(v), ref))
    by_chapter: dict[tuple[str, int], list[str]] = {}
    position: dict[str, float] = {}
    for book, rows in order.items():
        rows.sort()
        for i, (ch, _v, ref) in enumerate(rows):
            by_chapter.setdefault((book, ch), []).append(ref)
            position[ref] = i
    words = {ref: _route_words(t) for ref, t in greek_english.items()}

    keys = {book: [(ch, v) for ch, v, _ in rows] for book, rows in order.items()}

    def place(ref: str) -> float:
        """A verse's place in its book's reading order, or half a place before where it would sit."""
        if ref in position:
            return position[ref]
        book, ch, v = ref.split(".")
        return bisect.bisect_left(keys.get(book, []), (int(ch), int(v))) - 0.5

    flagged: dict[str, tuple[str, float, float, int]] = {}
    for eref, text in english.items():
        lref = routed.get(eref, eref)
        book, lch, _ = lref.split(".")
        if book not in order:
            continue
        ewords = _route_words(text)
        here = _overlap(ewords, words[lref]) if lref in words else 0.0
        ech = eref.split(".")[1]
        best, best_ref = 0.0, None
        for ch in {int(lch) - 1, int(lch), int(lch) + 1, int(ech) - 1, int(ech), int(ech) + 1}:
            for ref in by_chapter.get((book, ch), ()):
                s = _overlap(ewords, words[ref])
                if s > best:
                    best, best_ref = s, ref
        if best_ref and best_ref != lref and best >= _FLAG[0] and best - here >= _FLAG[1]:
            flagged[eref] = (best_ref, best, here, round(place(best_ref) - place(lref)))

    out: dict[str, tuple[str, float]] = {}
    for eref, (ref, best, here, shift) in flagged.items():
        book, ch, v = eref.rsplit(".", 2)
        near = [f"{book}.{ch}.{int(v) + d}" for d in (-3, -2, -1, 1, 2, 3)]
        same = sum(1 for n in near if n in flagged and flagged[n][3] == shift)
        merged = routed.get(eref, eref) not in swete_refs and abs(shift) <= 2 and best >= _MERGED
        if (best >= _STRONG[0] and best - here >= _STRONG[1]) or same >= _NEIGHBOURS or merged:
            out[eref] = (ref, round(best, 3))
    # A verse whose routed Greek verse now belongs to another English verse moves on lighter evidence:
    # Swete puts Malachi's "Remember the law" (English 4:4) last, and English 4:5 takes Swete 4:4.
    taken = {ref for ref, _ in out.values()}
    for eref, (ref, best, here, shift) in flagged.items():
        if eref not in out and routed.get(eref, eref) in taken and best >= _MERGED:
            out[eref] = (ref, round(best, 3))
    return out
