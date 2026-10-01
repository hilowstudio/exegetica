"""Curate a Reading Room expansion from Project Gutenberg — metadata only, no book bodies.

Reads Gutenberg's official catalog dump (one fast CSV, the whole catalogue), applies the
curation pipeline, and emits a REVIEWABLE manifest — nothing is fetched or seeded here.
That's deliberate: you approve the manifest, then a separate seeder ingests the approved rows.

Why the CSV, not gutendex: gutendex is per-page and far too slow to walk 60k works; the
catalog CSV is a single download and carries the signal we actually curate on — the
**Bookshelves** (PG's editorial curation) and **LoCC** (Library of Congress class).

Curation (see the chat plan; calibrated English-only + "broad worth-reading"):
  Hard filters   — English, Type=Text; minus junk CLASSES: periodicals (LoCC AP / periodical
                   shelves), bibliography & catalogs (LoCC Z), and gov/legislative/patent noise
                   by subject+title.
  Positive select— on a CURATED (non-"Category:") Gutenberg bookshelf. That's PG editors'
                   own curation (Harvard Classics, Best Books Ever, Historical Fiction,
                   Children's Literature, …) — ~12k English works, right at the target size.
                   The 48k "Category:"-only auto-taxonomy tail is left behind.
  Dedup          — drop works we already hold (books.db: Standard Ebooks + CCEL),
                   best-copy-wins (we never displace a Standard Ebooks copy).
Output: a CSV manifest (ranked, with genre + include reason) + a printed summary.

    .venv\\Scripts\\python.exe scripts\\harvest_gutenberg.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

from webapp.sources.matching import BROWSER_UA, author_last_name, normalize  # noqa: E402

_AUTHOR_SAME = 75  # token_set_ratio ≥ this ⇒ same person (calibrated: different people ≤45,
#                    same person ≥84 on the real collision set — a wide, safe gap)

_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
_CATALOG_CACHE = _ROOT / ".seed_cache" / "pg_catalog.csv"
_BOOKS_DB = _ROOT / "db" / "books.db"
_OUT_DEFAULT = _ROOT / ".seed_cache" / "gutenberg_manifest.csv"

# --- junk classes to exclude (an English/Bible school reading room) --------------------- #
_BLOCK_LOCC = ("AP", "AN", "Z")  # periodicals, newspapers, bibliography/library catalogs
_BLOCK_SHELF = re.compile(
    r"(punch|notes and queries|mirror of literature|the american missionary|periodical|magazine)",
    re.I,
)
_BLOCK_SUBJECT = re.compile(
    r"(periodicals|united states\.?\s*congress|great britain\.?\s*parliament|\bpatents?\b|"
    r"statutes|law reports|session laws|\bcatalogs?\b|\bcatalogues?\b|almanacs)",
    re.I,
)
_BLOCK_TITLE = re.compile(
    r"(^the project gutenberg\b|^index\b|\bindex of the project|congressional record|"
    r"statutes at large|hansard|parliamentary debates)",
    re.I,
)

# Confirmed dups of works we already hold, but with a SPELLING/orthography variant in the
# title that no title-matcher can catch ("Centre"/"Center", "Asse"/"Ass"). Verified by hand
# against the dedup audit — excluded by exact Gutenberg id. (NOT id 14833 "Varney the Vampyre"
# — that's a distinct work, only 6087 "The Vampyre" is Polidori's, which we hold as "The Vampire".)
_EXCLUDE_IDS = {
    "18857",  # A Journey to the Centre of the Earth = held "…Center…" (Verne)
    "1666",   # The Golden Asse = held "The Golden Ass" (Apuleius)
    "19370",  # Ullr Uprising = held "Uller Uprising" (Piper)
    "6087",   # The Vampyre; a Tale = held "The Vampire" (Polidori)
    "241",    # Clotelle = held "Clotel" (William Wells Brown; revised edition of the same work)
}

# --- genre shelving: LoCC-first, then subject/shelf keywords ---------------------------- #
_LOCC_GENRE = [
    (("BS",), "Bible"),
    (("BR", "BV", "BX", "BT", "BL", "BM", "BP", "BQ"), "Religion"),
    (("B", "BC", "BD", "BF", "BH", "BJ"), "Philosophy"),
    (("D", "E", "F", "C"), "History & Biography"),
    (("PN",), "Literature"),
    (("PA",), "Classical"),
    (("PZ",), "Fiction & Children's"),
    (("PR", "PS", "PQ", "PT", "PB", "PC", "PG", "PH", "PJ", "PK", "PL"), "Fiction"),
    (("Q", "R", "S", "T", "U", "V"), "Science & Practical"),
    (("G", "H", "J", "K", "L", "M", "N"), "Society & Arts"),
]
_GENRE_KW = [
    ("Poetry", re.compile(r"\bpoetry\b|\bpoems?\b", re.I)),
    ("Drama", re.compile(r"\bdrama\b|\bplays?\b", re.I)),
    ("Children's", re.compile(r"children|juvenile|fairy tale", re.I)),
]


def _locc_list(x):
    return [c.strip() for c in x.get("LoCC", "").split(";") if c.strip()]


def _shelves(x):
    return [s.strip() for s in x.get("Bookshelves", "").split(";") if s.strip()]


def _curated_shelves(x):
    return [s for s in _shelves(x) if not s.startswith("Category:")]


def _genre(x) -> str:
    for code in _locc_list(x):
        for prefixes, name in _LOCC_GENRE:
            if any(code == p or code.startswith(p) for p in prefixes):
                blob = x.get("Subjects", "") + " ; " + x.get("Bookshelves", "")
                for gname, rx in _GENRE_KW:
                    if rx.search(blob):
                        return gname
                return name
    return "General"


def _author_and_years(authors_field: str) -> tuple[str, str]:
    # "Surname, Given, 1775-1817; Other, A., 1900-1950" -> first author name + years
    first = authors_field.split(";")[0].strip()
    m = re.search(r",\s*(\d{3,4}\??)\s*-\s*(\d{3,4}\??)?\s*$", first)
    years = ""
    if m:
        years = f"{m.group(1)}-{m.group(2) or ''}"
        first = first[: m.start()].strip()
    return first, years


# Title words that carry no identity — dropped before comparison so "The Adventures of
# Huckleberry Finn" (SE) and "Adventures of Huckleberry Finn" (PG) still match.
_TITLE_STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "de", "with", "his", "her"}
# Words that mark a DISTINCT companion/sequel — never merge a title into another over one of
# these ("The Second Jungle Book" is not "The Jungle Book"; "Further Adventures…" is its own work).
_SEQUEL = {"second", "third", "fourth", "fifth", "sixth", "further", "new", "more", "another",
           "other", "sequel", "continued", "next", "additional", "supplementary",
           "ii", "iii", "iv", "vi", "vii", "viii", "ix"}


def _title_tokens(title: str) -> frozenset[str]:
    """Significant title tokens, subtitle stripped. 'Frankenstein; Or, The Modern Prometheus'
    and 'Walden, and On the Duty…' both reduce to their leading, distinctive words. Digits are
    kept (any length) so 'Part 1' and 'Part 2' stay distinct."""
    t = re.split(r"[;:]", title or "")[0]              # drop after ; or :
    t = re.split(r",?\s+or\b", t, maxsplit=1, flags=re.I)[0]  # drop ", or …" alt-title tails
    return frozenset(w for w in normalize(t).split()
                     if w not in _TITLE_STOP and (w.isdigit() or len(w) > 1))


def _canonkey(title: str) -> str:
    """Order-independent canonical title (sorted significant tokens) — for author-independent
    collision detection, so 'Dostoyevsky, Fyodor' and 'Fyodor Dostoevsky' meet on the title."""
    return " ".join(sorted(_title_tokens(title)))


def _is_dup(tt: frozenset, sn: str, index: dict) -> tuple[str, str] | None:
    """A work we already hold, matched by surname + title-token overlap. Returns
    (match_type, held_label) or None. Conservative for single-token titles (require equality)
    to avoid merging distinct same-author works; looser when there's more to compare."""
    if not tt:
        return None
    for ptoks, label in index.get(sn, ()):
        if not ptoks:
            continue
        if tt == ptoks:
            return ("exact-title", label)
        small = min(len(tt), len(ptoks))
        if small == 1:
            continue  # one side is a single word already != the other → too risky to merge
        # Subset only. One title's significant words fully contain the other's (a subtitle or
        # "…, Complete" tail). Distinct works with distinguishing tokens ("First"/"Second",
        # "III"/"IV", "People"/"Land", "1991"/"1992") are never subsets, so they're kept apart.
        if tt <= ptoks or ptoks <= tt:
            extra = (ptoks - tt) if tt <= ptoks else (tt - ptoks)
            if extra & _SEQUEL:      # "The Second Jungle Book" ⊃ "The Jungle Book" → distinct
                continue
            return ("subset", label)
    return None


def _author_same_person(a: str, b: str) -> bool:
    """Do two author STRINGS name the same person? Order-, format-, spelling- and
    co-author-tolerant ('Dostoyevsky, Fyodor'≈'Fyodor Dostoevsky'; 'Marx'⊂'Marx, Engels')."""
    na, nb = set(normalize(a).split()), set(normalize(b).split())
    if not na or not nb:
        return False
    if na <= nb or nb <= na:               # one name contained in the other (co-authors, partials)
        return True
    return fuzz.token_set_ratio(normalize(a), normalize(b)) >= _AUTHOR_SAME


def _load_existing() -> dict:
    """Two indexes over everything we hold:
       'sn'  : surname     -> [(title_tokens, label)]           (same-author subtitle/subset)
       'key' : canon-title -> [(author_string, label)]          (cross-name-format collisions)"""
    idx = {"sn": {}, "key": {}}
    if not _BOOKS_DB.exists():
        return idx
    c = sqlite3.connect(_BOOKS_DB)
    for title, author, source in c.execute("select title, author, source from books"):
        label = f"{(title or '')[:50]} — {author or '?'} [{source}]"
        idx["sn"].setdefault(author_last_name(author or ""), []).append((_title_tokens(title or ""), label))
        key = _canonkey(title or "")
        if key:
            idx["key"].setdefault(key, []).append((author or "", label))
    c.close()
    return idx


def _load_catalog() -> list[dict]:
    if not _CATALOG_CACHE.exists():
        print("Downloading PG catalog CSV…")
        r = httpx.get(_CATALOG_URL, headers={"User-Agent": BROWSER_UA}, timeout=180, follow_redirects=True)
        r.raise_for_status()
        _CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CATALOG_CACHE.write_bytes(r.content)
    return list(csv.DictReader(io.StringIO(_CATALOG_CACHE.read_text(encoding="utf-8"))))


def _curate(rows: list[dict], existing: dict) -> tuple[list[dict], list[dict], dict]:
    out: list[dict] = []
    audit: list[dict] = []
    stats = collections.Counter()
    for x in rows:
        if x.get("Type") != "Text":
            continue
        if "en" not in [l.strip() for l in x.get("Language", "").split(";")]:
            continue
        stats["english_text"] += 1
        if x.get("Text#") in _EXCLUDE_IDS:      # hand-verified spelling-variant dups
            stats["dup"] += 1; stats["dup::spelling-variant"] += 1
            audit.append({"gutenberg_id": x.get("Text#"), "title": x.get("Title", ""),
                          "author": x.get("Authors", ""), "match_type": "spelling-variant",
                          "matched_held_copy": "(manual exclusion — see _EXCLUDE_IDS)"})
            continue
        title, subjects = x.get("Title", ""), x.get("Subjects", "")
        locc = _locc_list(x)
        curated = _curated_shelves(x)
        # hard exclusions (junk classes)
        if any(any(c == p or c.startswith(p) for p in _BLOCK_LOCC) for c in locc):
            stats["blocked"] += 1; continue
        if _BLOCK_TITLE.search(title) or _BLOCK_SUBJECT.search(subjects) or _BLOCK_SHELF.search(x.get("Bookshelves", "")):
            stats["blocked"] += 1; continue
        # positive selection: on a curated (non-Category) shelf
        if not curated:
            stats["not_curated"] += 1; continue
        title = re.sub(r"\s+", " ", title).strip()  # PG joins title+subtitle with a newline
        author, years = _author_and_years(x.get("Authors", ""))
        author = re.sub(r"\s+", " ", author).strip()
        sn, tt, key = author_last_name(author), _title_tokens(title), _canonkey(title)
        hit = _is_dup(tt, sn, existing["sn"])                     # same-author: exact-title / subset
        if not hit and key:                                        # cross-name-format: same title, same person
            for held_author, label in existing["key"].get(key, ()):
                if _author_same_person(author, held_author):
                    hit = ("cross-name", label); break
        if hit:
            stats["dup"] += 1
            stats[f"dup::{hit[0]}"] += 1
            audit.append({"gutenberg_id": x.get("Text#"), "title": title, "author": author,
                          "match_type": hit[0], "matched_held_copy": hit[1]})
            continue
        label = f"{title[:50]} — {author} [gutenberg]"           # de-dup within the harvest too
        existing["sn"].setdefault(sn, []).append((tt, label))
        if key:
            existing["key"].setdefault(key, []).append((author, label))
        genre = _genre(x)
        out.append({
            "gutenberg_id": x.get("Text#"),
            "title": title,
            "author": author,
            "author_years": years,
            "issued": x.get("Issued", ""),
            "genre": genre,
            "locc": " | ".join(locc),
            "curated_shelves": " | ".join(curated),
            "subjects": " | ".join(subjects.split(";")[:4]).strip(),
        })
        stats["kept"] += 1
        stats[f"genre::{genre}"] += 1
    out.sort(key=lambda r: (r["genre"], r["author"], r["title"]))
    return out, audit, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=_OUT_DEFAULT)
    args = ap.parse_args()

    rows = _load_catalog()
    print(f"catalog rows: {len(rows)}")
    existing = _load_existing()
    print(f"deduping against {sum(len(v) for v in existing['sn'].values())} works already in books.db")
    kept, audit, stats = _curate(rows, existing)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
        w.writeheader(); w.writerows(kept)
    audit_path = args.out.with_name("gutenberg_dedup_audit.csv")
    with open(audit_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["gutenberg_id", "title", "author", "match_type", "matched_held_copy"])
        w.writeheader(); w.writerows(audit)

    print("\n=== curation summary ===")
    print(f"  English Text works:        {stats['english_text']}")
    print(f"  blocked (junk classes):    {stats['blocked']}")
    print(f"  no curated shelf (tail):   {stats['not_curated']}")
    print(f"  duplicate of a held copy:  {stats['dup']}  "
          f"({', '.join(f'{k[5:]}={v}' for k,v in stats.items() if k.startswith('dup::'))})")
    print(f"  KEPT:                      {stats['kept']}")
    print("\n  by genre:")
    for k, n in sorted([(k, v) for k, v in stats.items() if k.startswith("genre::")], key=lambda x: -x[1]):
        print(f"    {n:6d}  {k[7:]}")
    print(f"\nmanifest -> {args.out}")
    print(f"dedup audit -> {audit_path}  ({len(audit)} matches)")


if __name__ == "__main__":
    main()
