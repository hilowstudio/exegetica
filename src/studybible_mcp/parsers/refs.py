"""
OSIS reference normalizer.

Confession proof-texts, and several other sources, cite Scripture in OSIS form
(`1Cor.10.31`, `Ps.73.25-Ps.73.28`, `Rom.1.19-Rom.1.20`). This maps an OSIS
reference to the internal book code + chapter/verse span used across the DB.
Shared infrastructure — reused wherever OSIS references appear.
"""

import re

# OSIS book abbreviation -> internal book code (matches BOOK_ABBREV_MAP values).
OSIS_TO_INTERNAL = {
    "Gen": "Gen", "Exod": "Exo", "Lev": "Lev", "Num": "Num", "Deut": "Deu",
    "Josh": "Jos", "Judg": "Jdg", "Ruth": "Rut", "1Sam": "1Sa", "2Sam": "2Sa",
    "1Kgs": "1Ki", "2Kgs": "2Ki", "1Chr": "1Ch", "2Chr": "2Ch", "Ezra": "Ezr",
    "Neh": "Neh", "Esth": "Est", "Job": "Job", "Ps": "Psa", "Psalm": "Psa",
    "Prov": "Pro", "Eccl": "Ecc", "Song": "Sng", "SongofSongs": "Sng",
    "Isa": "Isa", "Jer": "Jer", "Lam": "Lam", "Ezek": "Ezk", "Dan": "Dan",
    "Hos": "Hos", "Joel": "Jol", "Amos": "Amo", "Obad": "Oba", "Jonah": "Jon",
    "Mic": "Mic", "Nah": "Nam", "Hab": "Hab", "Zeph": "Zep", "Hag": "Hag",
    "Zech": "Zec", "Mal": "Mal",
    "Matt": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn", "Acts": "Act",
    "Rom": "Rom", "1Cor": "1Co", "2Cor": "2Co", "Gal": "Gal", "Eph": "Eph",
    "Phil": "Php", "Col": "Col", "1Thess": "1Th", "2Thess": "2Th",
    "1Tim": "1Ti", "2Tim": "2Ti", "Titus": "Tit", "Phlm": "Phm", "Heb": "Heb",
    "Jas": "Jas", "1Pet": "1Pe", "2Pet": "2Pe", "1John": "1Jn", "2John": "2Jn",
    "3John": "3Jn", "Jude": "Jud", "Rev": "Rev",
    # Deuterocanon (OSIS deuterocanonical codes -> our WEB codes).
    "Tob": "Tob", "Jdt": "Jdt", "Wis": "Wis", "Sir": "Sir", "Bar": "Bar",
    "1Macc": "1Ma", "2Macc": "2Ma", "3Macc": "3Ma", "4Macc": "4Ma",
    "1Esd": "1Es", "2Esd": "2Es", "PrMan": "Man", "EpJer": "Bar",
}

_PART = re.compile(r"^([1-4]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def parse_osis(ref: str) -> tuple[str, int, int, int] | None:
    """Parse an OSIS reference to (internal_book, chapter, v_start, v_end).

    'Rom.11.36' -> ('Rom', 11, 36, 36); 'Ps.73.25-Ps.73.28' -> ('Psa', 73, 25, 28).
    Handles ranges where the right side is a full OSIS ref, a 'chapter.verse',
    or a bare verse. Returns None if it cannot be parsed or the book is unknown.
    """
    ref = (ref or "").strip()
    if not ref:
        return None
    left, _, right = ref.partition("-")
    m = _PART.match(left.strip())
    if not m:
        return None
    osis_book, chap_s, v1_s = m.groups()
    book = OSIS_TO_INTERNAL.get(osis_book)
    if not book:
        return None
    chapter, v1 = int(chap_s), int(v1_s)
    v2 = v1
    if right:
        r = right.strip()
        rm = _PART.match(r)
        if rm:                                   # 'Ps.73.28'
            v2 = int(rm.group(3))
        elif ":" in r or "." in r:               # 'Ps.73.28' variants / '73.28'
            v2 = int(re.split(r"[.:]", r)[-1])
        elif r.isdigit():                        # bare verse '28'
            v2 = int(r)
    if v2 < v1:
        v2 = v1
    return book, chapter, v1, v2
