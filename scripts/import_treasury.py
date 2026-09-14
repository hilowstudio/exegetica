#!/usr/bin/env python3
"""
Import Spurgeon's *Treasury of David* into `commentaries` (source spurgeon-treasury),
served by get_commentary as verse-by-verse Psalms exposition.

Source: .seed_cache/chspurgeon-tod (CC0; run download_treasury.py first). Only Spurgeon's
own **Exposition** is ingested — the multi-author "Explanatory Notes & Quaint Sayings" and
the "Hints to the Village Preacher" sermon outlines are skipped so the source stays cleanly
attributable to Spurgeon.

Two file layouts:
  - psalms 1-118, 120-150: one file volume-N/psalm-M.md, with an intro (stored as verse 0)
    then '## Exposition' -> '### Verse N' / '### Verses N-M' verse-keyed sections.
  - psalm 119: a directory volume-6/psalm-119/verses-*.md, each with '## Exposition Verse N'.

    .venv\\Scripts\\python.exe scripts\\import_treasury.py --dry-run   # per-psalm row counts
    .venv\\Scripts\\python.exe scripts\\import_treasury.py             # write

This is a post-`build_database.py --rebuild` importer (re-run after any rebuild).
"""
from __future__ import annotations

import argparse
import html
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from studybible_mcp.database import create_schema  # noqa: E402
from studybible_mcp.parsers.commentaries import COMMENTARIES  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SRC = _ROOT / ".seed_cache" / "chspurgeon-tod"
_DB = _ROOT / "db" / "study_bible.db"
_SOURCE = "spurgeon-treasury"
_BOOK = "Psa"

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.S)


def _clean(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_leading_quote(body: str) -> str:
    """Drop the leading '> ...' blockquote (the KJV verse being commented on)."""
    lines = body.split("\n")
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith(">")):
        i += 1
    return "\n".join(lines[i:]).strip()


def _verse_range(heading: str) -> tuple[int | None, int | None]:
    ns = [int(x) for x in re.findall(r"\d+", heading)]
    return (min(ns), max(ns)) if ns else (None, None)


def _parse_standard(path: pathlib.Path) -> list[tuple[int, int, str]]:
    raw = _FRONTMATTER.sub("", path.read_text(encoding="utf-8"))
    rows: list[tuple[int, int, str]] = []

    expo = re.search(r"^##\s+Exposition\s*$", raw, re.M)
    if not expo:
        return rows

    # Intro prose (between the '# Psalm N' title and the Exposition) -> verse 0.
    head = re.sub(r"^#\s+Psalm.*$", "", raw[: expo.start()], flags=re.M)
    intro = _clean(head)
    if intro:
        rows.append((0, 0, intro))

    # Exposition body up to the next '## ' section (Explanatory Notes / Hints / Works).
    after = raw[expo.end():]
    nxt = re.search(r"^##\s+", after, re.M)
    body = after[: nxt.start()] if nxt else after

    parts = re.split(r"^###\s+(.+?)\s*$", body, flags=re.M)
    for i in range(1, len(parts), 2):
        vs, ve = _verse_range(parts[i])
        if vs is None:
            continue
        text = _clean(_strip_leading_quote(parts[i + 1]))
        if text:
            rows.append((vs, ve, text))
    return rows


def _parse_119(directory: pathlib.Path) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    for f in sorted(directory.glob("verses-*.md")):
        raw = _FRONTMATTER.sub("", f.read_text(encoding="utf-8"))
        parts = re.split(r"^##\s+Exposition\s+Verse\s+(\d+)\s*$", raw, flags=re.M)
        for i in range(1, len(parts), 2):
            v = int(parts[i])
            body = parts[i + 1]
            cut = re.search(r"^###\s+", body, re.M)  # stop before Explanatory Notes / Hints
            if cut:
                body = body[: cut.start()]
            text = _clean(_strip_leading_quote(body))
            if text:
                rows.append((v, v, text))
    return rows


def _psalm_files() -> dict[int, pathlib.Path]:
    """Map psalm number -> file (or the psalm-119 directory)."""
    out: dict[int, pathlib.Path] = {}
    for p in _SRC.glob("volume-*/psalm-*"):
        m = re.match(r"psalm-(\d+)", p.name)
        if m:
            out[int(m.group(1))] = p
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report per-psalm counts, do not write")
    args = ap.parse_args()

    if not _SRC.exists():
        print(f"Source not found: {_SRC}. Run download_treasury.py first.")
        sys.exit(1)
    if not _DB.exists():
        print(f"Database not found: {_DB}. Run build_database.py first.")
        sys.exit(1)

    files = _psalm_files()
    all_rows: list[tuple[str, str, str, int, int, int, str]] = []
    name = COMMENTARIES[_SOURCE]
    empty: list[int] = []
    for psalm in sorted(files):
        path = files[psalm]
        parsed = _parse_119(path) if path.is_dir() else _parse_standard(path)
        if not parsed:
            empty.append(psalm)
        for vs, ve, text in parsed:
            all_rows.append((_SOURCE, name, _BOOK, psalm, vs, ve, text))

    total = len(all_rows)
    verse_rows = sum(1 for r in all_rows if r[4] > 0)
    print(f"parsed {len(files)} psalms -> {total:,} rows "
          f"({verse_rows:,} verse-keyed, {total - verse_rows} chapter intros)")
    if empty:
        print(f"  [warn] {len(empty)} psalms produced no rows: {empty}")

    if args.dry_run:
        for psalm in sorted(files)[:5]:
            n = sum(1 for r in all_rows if r[3] == psalm)
            print(f"    Psalm {psalm}: {n} rows")
        print("(dry run — nothing written)")
        return

    conn = sqlite3.connect(_DB)
    try:
        create_schema(conn)
        conn.execute("DELETE FROM commentaries WHERE source = ?", (_SOURCE,))
        conn.executemany(
            "INSERT INTO commentaries "
            "(source, source_name, book, chapter, verse_start, verse_end, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            all_rows,
        )
        conn.execute("ANALYZE")
        conn.commit()
        n = conn.execute("SELECT count(*) FROM commentaries WHERE source = ?", (_SOURCE,)).fetchone()[0]
        print(f"[ok] imported {n:,} Treasury of David rows into commentaries (source={_SOURCE}).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
