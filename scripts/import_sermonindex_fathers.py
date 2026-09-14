#!/usr/bin/env python3
"""
Import ONLY the genuinely-new sermonindex patristic quotations into `patristic_catena`.

The full sermonindex set (68,240 rows) is ~97% duplicated by the existing
HistoricalChristianFaith catena; a dedup pass keeps only the ~1,750 rows that are neither
an exact-text duplicate nor a same-father+same-verse duplicate of what we already hold
(~half land on verses the catena did not cover). year + father_category are backfilled from
our own vetted catena rows by normalized father name; provenance is stamped source='sermonindex'
(CC BY 4.0 — SermonIndex is credited per-row via source_url and in get_church_fathers' footer).

Idempotent: re-running replaces the sermonindex rows only, never the HCF rows. Ensures the
`source` column exists and backfills pre-existing rows to 'historical-christian-faith'.
This is a post-`build_database.py --rebuild` importer (re-run after any rebuild + import_catena).

    .venv\\Scripts\\python.exe scripts\\import_sermonindex_fathers.py --dry-run
    .venv\\Scripts\\python.exe scripts\\import_sermonindex_fathers.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from studybible_mcp.database import create_schema, BOOK_ABBREV_MAP  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SRC = _ROOT / ".seed_cache" / "sermonindex_quotation.jsonl"
_DB = _ROOT / "db" / "study_bible.db"

_EPITHETS = {"of", "the", "saint", "st", "pope", "bishop", "venerable", "hippo", "alexandria",
    "milan", "ohrid", "nazianzus", "nyssa", "caesarea", "jerusalem", "constantinople", "carthage",
    "lyons", "poitiers", "antioch", "great", "dialogist", "confessor", "damascus", "sinai",
    "cyrrhus", "mopsuestia", "emesa", "stridon", "aquileia", "ravenna", "seville", "canterbury",
    "edessa"}


def _strip_paren(name: str) -> str:
    return re.sub(r"\s*\(+.*?\)+\s*", "", name or "").strip()


def _nf(name: str) -> str:
    s = unicodedata.normalize("NFKD", _strip_paren(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", " ", s)
    return " ".join(w for w in s.split() if w not in _EPITHETS)


def _nt(t: str, n: int = 120) -> str:
    s = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)[:n]


def _book_internal(book_name: str, osis: str) -> str | None:
    b = (book_name or "").strip().lower()
    if b in BOOK_ABBREV_MAP:
        return BOOK_ABBREV_MAP[b]
    m = re.match(r"^(\d)\s*([a-z]+)$", b)
    if m:
        return BOOK_ABBREV_MAP.get(f"{m.group(1)} {m.group(2)}")
    return BOOK_ABBREV_MAP.get((osis or "").strip().lower())


def _ensure_source_column(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(patristic_catena)")}
    if "source" not in cols:
        conn.execute("ALTER TABLE patristic_catena ADD COLUMN source TEXT")
    # Any row without provenance predates this importer → it's HCF.
    conn.execute(
        "UPDATE patristic_catena SET source = 'historical-christian-faith' "
        "WHERE source IS NULL AND father_name IS NOT NULL"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not _SRC.exists():
        print(f"Source not found: {_SRC}. Run download_sermonindex.py first.")
        sys.exit(1)
    if not _DB.exists():
        print(f"Database not found: {_DB}. Run build_database.py + import_catena.py first.")
        sys.exit(1)

    conn = sqlite3.connect(_DB)
    create_schema(conn)
    if not args.dry_run:
        _ensure_source_column(conn)
        conn.execute("DELETE FROM patristic_catena WHERE source = 'sermonindex'")

    # Existing catena: dedup keys + year/category backfill maps (exclude any sermonindex rows).
    has_source = "source" in {r[1] for r in conn.execute("PRAGMA table_info(patristic_catena)")}
    src_expr = "source" if has_source else "NULL AS source"
    cat_sig, cat_fv, ymap, cmap = set(), set(), {}, {}
    for fn, book, ch, vs, q, yr, cat, src in conn.execute(
            "SELECT father_name, book, chapter, verse_start, quote, year, father_category, "
            f"{src_expr} FROM patristic_catena"):
        if src == "sermonindex":
            continue
        k = _nf(fn)
        cat_sig.add(_nt(q))
        cat_fv.add((k, book, ch, vs))
        if yr and k not in ymap:
            ymap[k] = yr
        if cat and k not in cmap:
            cmap[k] = cat

    kept, skipped_dup, skipped_book, year_unknown = [], 0, 0, 0
    with _SRC.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            bi = _book_internal(r.get("book_name"), r.get("book"))
            if bi is None:
                skipped_book += 1
                continue
            k = _nf(r.get("father"))
            ch, v = r.get("chapter"), r.get("verse")
            if _nt(r.get("quotation")) in cat_sig or (k, bi, ch, v) in cat_fv:
                skipped_dup += 1
                continue
            ve = r.get("verse_end") or v
            year = ymap.get(k)
            if year is None:
                year_unknown += 1
            kept.append((
                _strip_paren(r.get("father")) or r.get("father"),
                cmap.get(k), year, bi, ch, v, ve if ve and ve >= v else v,
                r.get("quotation"), r.get("source_work"), r.get("url"), "sermonindex",
            ))

    print(f"sermonindex quotations scanned; keeping {len(kept):,} new rows "
          f"({skipped_dup:,} dup, {skipped_book:,} unmapped-book; {year_unknown} kept with unknown year)")

    if args.dry_run:
        print("(dry run — nothing written)")
        conn.close()
        return

    conn.executemany(
        "INSERT INTO patristic_catena "
        "(father_name, father_category, year, book, chapter, verse_start, verse_end, "
        "quote, source_title, source_url, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", kept)
    conn.execute("ANALYZE")
    conn.commit()
    n = conn.execute("SELECT count(*) FROM patristic_catena WHERE source = 'sermonindex'").fetchone()[0]
    total = conn.execute("SELECT count(*) FROM patristic_catena").fetchone()[0]
    conn.close()
    print(f"[ok] imported {n:,} SermonIndex rows; patristic_catena now {total:,} total.")


if __name__ == "__main__":
    main()
