"""Title and author lines as the house covers print them.

Catalog titles and authors arrive in library-catalog shapes that read badly on a cover: subtitles
("Mary Olivier: A Life"), series codes ("ANF09. ..."), bracketed full names and roles ("H. G.
(Herbert George) Wells", "Richard Baker (Translator)"), and names mangled by turning "Beerbohm, Max,
Sir, 1872-1956" into display order ("Max, Sir Beerbohm"). These rules produce the cover's short
title and author line without touching the catalog; assets/cover-text.csv holds hand corrections
(slug, title, author, note) that always win.

    from cover_text import resolve
    title, author = resolve(slug, raw_title, raw_author)
"""
from __future__ import annotations

import csv
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parent.parent
OVERRIDES = _ROOT / "assets" / "cover-text.csv"

# ---------------------------------------------------------------- authors
_HON = r"(?:Sir|Lady|Dame|Mrs\.|Mr\.|Rev\.|Dr\.|Jr\.?|Sr\.?)"
_PEER = re.compile(r"^(?:Baron|Baroness|Viscount|Earl|Marquess|Marquis|Duke|Count|Countess)\b")
_DEGREE = re.compile(r"^(?:[A-Z][A-Za-z]{0,3}\.\s?){1,4}$")            # D.D., M.A., LL.D., F.R.S.
_ROLES = {"editor": "Edited by", "ed.": "Edited by", "ed": "Edited by", "translator": "Translated by",
          "tr": "Translated by", "tr.": "Translated by", "compiler": "Compiled by"}
_PARTICLE = re.compile(r"^(?:of|de|da|di|del|della|du|le|la|von|van|der|the|abbé)\b")
_KNOWN = {"flavel": "John Flavel", "schaff": "Philip Schaff"}             # bare lowercase surnames from CCEL
_BLANK = {"various", "unknown", ""}


def _role_of(raw: str) -> str | None:
    for m in re.finditer(r"[\[(]([^\])]+)[\])]|,\s*(Editor|Translator|Compiler)\b", raw):
        word = (m.group(1) or m.group(2) or "").strip().lower()
        if word in _ROLES:
            return _ROLES[word]
    return None


def _strip_dates(s: str) -> str:
    s = re.sub(r"\bactive\s+(?:\d{1,2}(?:st|nd|rd|th)\s+century|\d{1,4})", "", s)
    s = re.sub(r"\b(?:c\.\s*)?\d{1,4}\??\s*(?:BCE|BC|CE|AD)?(?:\s*[-–—]\s*(?:c\.\s*)?\d{0,4}\??\s*(?:BCE|BC|CE|AD)?)?", "", s)
    return s


def _tidy(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r"(,\s*)+,", ",", s)
    return s.strip(" ,;-–—")


def _uninvert(name: str) -> str:
    """'of Hippo Augustine' -> 'Augustine of Hippo'; 'abbé Prévost' -> 'Abbé Prévost'."""
    if name.lower() in _KNOWN:
        return _KNOWN[name.lower()]
    if name.startswith("abbé "):
        return "Abbé " + name[5:]
    m = re.match(r"^(?P<pre>.+?)\s+(?P<name>[^\s]+)$", name)
    if m and _PARTICLE.match(name) and m.group("name")[:1].isupper():
        return f"{m.group('name')} {m.group('pre')}"
    return name


def _person_from_parts(parts: list[str]) -> list[str]:
    """One comma-separated author string -> the people in it, put back in reading order."""
    for i in range(len(parts) - 1, 0, -1):                                 # 'John W. Campbell, Jr.' -> one part
        if re.match(r"^[JS]r\.?$", parts[i]):
            parts[i - 1] = f"{parts[i - 1]}, {parts[i].rstrip('.')}."
            del parts[i]
    parts = [p for i, p in enumerate(parts)
             if p and not (i and _DEGREE.match(p) and len(parts[0].split()) > 1)]
    parts = [p for p in parts if p.lower() not in _ROLES and not re.match(r"^Bishop of\b", p)]
    if len(parts) <= 1:
        return parts
    first, rest = parts[0], " ".join(parts[1:])
    m = re.match(r"^(?:graf|graf von|freiherr von)\s+(\S+)$", parts[1]) if len(parts) == 2 else None
    if m:                                                                  # 'Leo, graf Tolstoy'
        return [f"{first} {m.group(1)}"]
    if len(parts) == 2 and re.match(r"^(?:comte|vicomte|baron|baronne|marquis|marquise|duc|duchesse|comtesse|count|countess)\b", parts[1]):
        return [f"{first}, {parts[1]}"]                                    # 'Philippe-Paul, comte de Ségur'
    m = re.match(rf"^(?P<hon>(?:{_HON}\s+)+)(?P<sur>[^\s,]+)$", rest)      # 'Max, Sir Beerbohm'
    if m and len(first.split()) <= 4:
        hon = m.group("hon").split()
        jr = [h for h in hon if h.startswith(("Jr", "Sr"))]
        pre = [h for h in hon if h not in jr]
        name = " ".join(pre + [first, m.group("sur")])
        return [name + (", " + jr[0].rstrip(".") + "." if jr else "")]
    if re.match(r"^Lord\s+\S+$", rest) and len(parts) == 2:                # 'Alfred, Lord Tennyson'
        return [f"{first}, {rest}"]
    if _PEER.match(parts[1]):                                              # 'James Bryce, Viscount Bryce'
        return _person_from_parts([first] + parts[2:])
    if parts[1].startswith("the ") and len(parts) == 2:                    # 'Dionysius, the Pseudo-Areopagite'
        return [f"{first} {parts[1]}"]
    if _PARTICLE.match(first) and len(parts) == 2 and len(parts[1].split()) == 1:
        return [f"{parts[1]} {first}"]                                     # 'the Younger, Pliny'
    if (len(parts) == 2 and len(first.split()) == 1 and first[:1].isupper()
            and 1 <= len(parts[1].split()) <= 3 and all(w[:1].isupper() for w in parts[1].split())
            and (re.search(r"[A-Z]\.", parts[1]) or len(parts[1].split()) == 1)):
        return [f"{parts[1]} {first}"]                                     # 'Bett, Henry', 'Easton, M.G.'
    return parts                                                           # several people


def _people(raw: str) -> tuple[list[str], bool, str | None]:
    """A catalog author string -> (the people in reading order, whether 'and others' followed, their role)."""
    a = raw.strip()
    role = _role_of(a)
    a = re.sub(r"^(Mrs\.|Miss|Lady)\s*\(([^)]+)\)\s+(\S+)$", r"\2 \3", a)   # 'Mrs. (Margaret) Oliphant'
    a = re.sub(r"\s*\([^)]*\)", "", a)
    m = re.match(r"^(?P<g>[^,\[\]]+),\s*(?P<mid>[^\[\]]*?(?:\d|\[[^\]]*\])[^\[\]]*?(?:\[[^\]]*\])?)\s+(?P<s>[^\s,\]\d?]+)$", a)
    if m:                                                    # 'Joseph, 1854-1916 [Compiler] Jacobs'
        hon = re.findall(rf"{_HON}", m.group("mid"))
        a = f"{m.group('g')}, {' '.join(hon)} {m.group('s')}" if hon else f"{m.group('g')} {m.group('s')}"
    a = re.sub(r"\s*\[[^\]]*\]", "", a)
    a = _tidy(_strip_dates(a))
    others = bool(re.search(r"\band others\b", a))
    a = _tidy(re.sub(r",?\s*\band others\b", "", a))
    people: list[str] = []
    for chunk in re.split(r"\s+&\s+|\s+and\s+", a):
        people += _person_from_parts([p.strip() for p in chunk.split(",")])
    return [_uninvert(p) for p in people if p], others, role


def catalog_author(raw: str | None) -> str:
    """The reading-room display author: every person, un-garbled, in reading order; no role or trimming."""
    a = (raw or "").strip()
    if a.lower() in _BLANK:
        return a
    if not re.search(r"[,(\[\d]", a) and not _PARTICLE.match(a) and a.lower() not in _KNOWN:
        return a                                             # already in reading order ('Walt & Leigh Richmond')
    if any(_PEER.match(p.strip()) for p in a.split(",")[1:]):
        return a                                             # 'Arthur Wellesley, Duke of Wellington' reads as it is
    a = re.sub(r",?\s*(?:Translated|Edited) by\b.*$", "", a)
    people, others, _role = _people(a)
    if not people:
        return a
    return ", ".join(people) + (" and others" if others else "")


def cover_author(raw: str | None) -> str:
    a = (raw or "").strip()
    if a.lower() in _BLANK:
        return ""
    people, others, role = _people(a)
    if not people:
        return ""
    if len(people) == 1 and not others:
        return f"{role} {people[0]}" if role else people[0]
    if len(people) == 2 and not others:
        return f"{people[0]} & {people[1]}"
    return f"{people[0]} and others"


# ---------------------------------------------------------------- titles
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Spring|Summer|Fall|Autumn|Winter)"
SERIES = ("The Expositor's Bible", "Expositor's Bible", "Expositions of Holy Scripture")


def _names(author: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'’]+", author or "") if len(w) > 3}


def cover_title(raw: str | None, author: str | None, keep_subtitle: bool = False) -> tuple[str, str | None]:
    """(cover title, cover author line if the title supplies it, else None). keep_subtitle keeps
    what follows a colon, for books that would otherwise share a cover title."""
    t = (raw or "").strip()
    m = re.match(rf"^(.*?),\s*({_MONTHS}[\s,]+(?:\d{{1,2}},\s*)?\d{{4}})$", t)
    if m:                                                    # a pulp issue: magazine / issue month
        return m.group(1).strip(), m.group(2)
    by = None
    m = re.match(r"^ECF:\s*(?P<a>[^:]+?)\s*:\s*(?P<t>.+)$", t)        # 'ECF: Cyril of Alexandria: Against Julian'
    if m:
        t, by = m.group("t"), m.group("a")
    t = re.sub(r"^ECF:\s*", "", t)
    t = re.sub(r"^[A-Z]{2,6}\d[\w-]*\.\s*", "", t)          # 'ANF09. ...'
    t = re.sub(r"^(?:Ante-Nicene|Nicene and Post-Nicene) Fathers,(?: Series \d,)? Volume \d+:\s*", "", t)   # cover shows the contents
    if ":" in t:                                             # a series name or the author's name before the colon
        head, tail = t.split(":", 1)
        words = {w for w in re.findall(r"[a-zà-ÿ'’]+", head.lower()) if len(w) > 3} - {"saint", "blessed", "bishop", "pope"}
        if head.strip() in SERIES or (words and words <= _names(author or "")):   # the head is just the author's name
            t = tail.strip()
    t = re.sub(r"\s*\$[a-z]\b.*$", "", t, flags=re.I)                   # catalog subfield debris: '$C Translated ...'
    t = re.sub(r"\s*\([^)]*\)|\s*\[[^\]]*\]", "", t)
    t = re.sub(r"[,.]?\s+(?:Edited|Translated|Selected and Edited|Compiled|Collected)(?: and \w+)? by\b.*$", "", t)
    t = re.sub(r",?\s+[Ww]ith (?:an )?(?:Introduction|Introductory|Notes|Illustrations|a Memoir)\b.*$", "", t)
    t = re.sub(r"\s*[,—–-]*\s*\b(?:Complete|Entire|Unabridged|Illustrated|With Illustrations)\s*$", "", t, flags=re.I)
    if not keep_subtitle:
        t = re.split(r";\s*or,?\s+|,?\s+or,\s+|;\s+|:\s+|\s+[—–-]\s+|\s*--\s*(?=\w)", t, maxsplit=1)[0]
    t = re.sub(r"\s*--\s*([\"”]?)\s*$", r"\1", t)                       # '"Speaking of Operations--"'
    if t.count('"') == 1:
        t = t.replace('"', "")
    t = re.sub(r"\bVol\.\s*", "Volume ", t)
    t = re.sub(r"(\d)(St|Nd|Rd|Th|D)\b", lambda m: m.group(1) + m.group(2).lower(), t)   # '1St' -> '1st'
    t = re.sub(r"\s+", " ", t).strip(" ,;:—–-")
    t = t[:1].upper() + t[1:]
    t = _ampersand(t)
    return t or (raw or "").strip(), by


# ---------------------------------------------------------------- "and" between names
# Literary pairs whose names aren't among the library's author first names.
_PAIR_NAMES = set("""Romeo Juliet Antony Cleopatra Troilus Cressida Tristan Tristram Isolde Iseult Pelleas Melisande
Daphnis Chloe Hero Leander Abelard Heloise Cupid Psyche Aucassin Nicolette Paolo Francesca Dido Aeneas Philemon Baucis
Pyramus Thisbe Orpheus Eurydice Venus Adonis Box Cox Torchy Vee Curdie Wendy Gog Magog Gareth Lynette Lancelot Guinevere
Geraint Enid Balin Balan Merlin Vivien Damon Pythias Castor Pollux Jason Medea Hamlet Ophelia Perseus Andromeda Theseus
Ariadne Sohrab Rustum Layla Majnun Ruth Naomi Esther Mordecai Ahab Jezebel Samson Delilah Cain Abel Jacob Esau""".split())
# Author first names that are also ordinary words, so they never count as names here.
_NOT_NAMES = set("""The A An Life Love Grace Hope Faith Joy May June April August Will Rose Earnest Hart Field Wood Stone
Mark Bill Frank Hunter Major Young King Queen Prince Princess Duke Duchess Captain General Price Law Lord Sir Saint St Christian Fortune Glory Victory Honor Liberty Patience
Prudence Mercy Truth Ernest Sunny Summer Winter Autumn Dawn Eve Star Sky River Cliff Dale Glen Heath Moor Forest""".split())
_FIRST: set[str] | None = None


def _first_names() -> set[str]:
    """First names of the library's authors (Peter, Mary, Moses, Aaron...), plus the literary pairs."""
    global _FIRST
    if _FIRST is None:
        import sqlite3
        _FIRST = set(_PAIR_NAMES)
        db = _ROOT / "db" / "books.db"
        if db.exists():
            con = sqlite3.connect(db)
            for (a,) in con.execute("select author from books"):
                for person in re.split(r",|&| and ", cover_author(a)):
                    w = re.sub(r"^(?:Sir|Lady|Dame|Saint|St\.|Mrs\.|Mr\.|Rev\.|Dr\.)\s+", "", person.strip()).split()
                    if len(w) >= 2 and w[0][:1].isupper() and len(w[0]) > 2 and "." not in w[0]:
                        _FIRST.add(w[0])
            con.close()
        _FIRST -= _NOT_NAMES
    return _FIRST


_SMALL = set("a an the and or nor but of in on at to by for with from as into upon".split())
_OPENERS = set("his her its their my our your other others some various sundry certain how what why when where who "
               "which that this these those".split())


def _bare(w: str) -> str:
    return w.lower().strip(",.;:!?'’\"“”()")


def _ampersand(t: str) -> str:
    """'and' becomes '&' where it joins a pair, at most once per title:
    1. two people's names: 'Antony and Cleopatra', 'Lewis and Clark';
    2. a tight pair of single words: one capitalized word each side, the pair closed off by a small
       word, punctuation or the end ('The Decline and Fall of the Roman Empire', 'Pride and Prejudice').
    It stays 'and' at the end of a list ('Men, Women and Ghosts'), before a phrase ('and His Companions',
    'and How to...', 'and Critical History') and in 'and Other Stories'."""
    if "&" in t:
        return t
    w = t.split()
    names = _first_names()
    best = None
    for i in range(1, len(w) - 1):
        if w[i] != "and":
            continue
        L, R = w[i - 1], w[i + 1]
        if L.endswith((",", ";", ":")) or not (L[:1].isupper() and R[:1].isupper()):
            continue
        if _bare(L) in _SMALL or _bare(R) in _SMALL | _OPENERS:
            continue
        if i >= 2 and w[i - 2].endswith(","):                 # the last item of a list
            continue
        lb, rb = L.strip(",;:'’\"“”"), R.strip(",;:'’\"“”")
        if lb in names and rb in names:                       # rule 1: names
            best = i
            break
        after = w[i + 2] if i + 2 < len(w) else ""
        closed = not after or R[-1] in ",;:.!?" or _bare(after) in _SMALL
        if closed and best is None:                           # rule 2: a closed pair
            best = i
    if best is None:
        return t
    w[best] = "&"
    return " ".join(w)


# ---------------------------------------------------------------- both
_OV: dict | None = None


def overrides() -> dict[str, dict]:
    global _OV
    if _OV is None:
        _OV = {}
        if OVERRIDES.exists():
            with open(OVERRIDES, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    _OV[r["slug"]] = r
    return _OV


def resolve_all(rows) -> dict[str, tuple[str, str]]:
    """{slug: (title, author)} for (slug, title, author) rows. Where trimming subtitles would give two
    different books the same cover (Catena Aurea on Mark and on Matthew), those keep their subtitles."""
    out = {s: resolve(s, t, a) for s, t, a in rows}
    seen: dict[tuple, list] = {}
    raw = {s: (t, a) for s, t, a in rows}
    for s, ta in out.items():
        seen.setdefault((ta[0].lower(), ta[1].lower()), []).append(s)
    for slugs in seen.values():
        if len(slugs) > 1 and len({raw[s][0] for s in slugs}) > 1:
            for s in slugs:
                if s not in overrides():
                    t, by = cover_title(raw[s][0], raw[s][1], keep_subtitle=True)
                    out[s] = (t, out[s][1])
    return out


def resolve(slug: str, title: str | None, author: str | None) -> tuple[str, str]:
    """The cover's title and author line (mixed case; the cover sets the author in capitals)."""
    t, by = cover_title(title, author)
    a = by if by is not None else cover_author(author)
    ov = overrides().get(slug)
    if ov:
        t = ov.get("title") or t
        if ov.get("author") is not None and ov.get("author") != "":
            a = "" if ov["author"] == "-" else ov["author"]
    return t, a
