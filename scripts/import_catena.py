#!/usr/bin/env python3
"""
Import the public-domain church-father catena into `patristic_catena`.

Reads the HistoricalChristianFaith prebuilt SQLite, filters to public-domain
fathers (author year < 1900 — later entries are fair-use excerpts of works
still under copyright), decodes the packed location integers
(chapter*1_000_000 + verse), and maps book names to internal codes.
"""

import re
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema, BOOK_ABBREV_MAP

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

PD_YEAR_CUTOFF = 1900  # entries by authors from this year on are treated as fair-use / (c)


def _book_to_internal(book: str) -> str | None:
    b = book.strip().lower()
    if b in BOOK_ABBREV_MAP:
        return BOOK_ABBREV_MAP[b]
    m = re.match(r"^(\d)\s*([a-z]+)$", b)  # '1corinthians' -> '1 corinthians'
    if m:
        return BOOK_ABBREV_MAP.get(f"{m.group(1)} {m.group(2)}")
    return None


def _decode(loc) -> tuple[int | None, int | None]:
    try:
        loc = int(loc)
    except (TypeError, ValueError):
        return None, None
    return loc // 1_000_000, loc % 1_000_000


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(db_path: str | None, data_dir: str | None):
    """Import the public-domain patristic catena into the database."""
    console.print("[bold blue]Study Bible MCP - Patristic Catena Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    src_sqlite = (Path(data_dir) if data_dir else (project_dir / "data")) / "patristic" / "commentaries.sqlite"

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)
    if not src_sqlite.exists():
        console.print(f"[red]Catena source not found: {src_sqlite}[/red]. Run download_catena.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    src = sqlite3.connect(src_sqlite)
    try:
        create_schema(conn)
        category = {name: cat for name, cat in
                    src.execute("SELECT name, father_category FROM father_meta")}

        conn.execute("DELETE FROM patristic_catena")
        count, skipped, batch = 0, 0, []
        rows = src.execute(
            "SELECT father_name, book, location_start, location_end, ts, txt, source_url, source_title "
            "FROM commentary"
        )
        for fname, book, ls, le, ts, txt, surl, stitle in rows:
            try:
                year = int(ts)
            except (TypeError, ValueError):
                skipped += 1
                continue
            if year >= PD_YEAR_CUTOFF:  # public-domain filter
                skipped += 1
                continue
            internal = _book_to_internal(book or "")
            if not internal:
                skipped += 1
                continue
            cs, vs = _decode(ls)
            ce, ve = _decode(le)
            if cs is None or vs is None:
                skipped += 1
                continue
            verse_end = ve if (ce == cs and ve is not None and ve >= vs) else vs
            batch.append((fname, category.get(fname), year, internal, cs, vs, verse_end,
                          txt, stitle, surl, "historical-christian-faith"))
            count += 1
            if len(batch) >= 2000:
                conn.executemany(
                    "INSERT INTO patristic_catena "
                    "(father_name, father_category, year, book, chapter, verse_start, verse_end, "
                    "quote, source_title, source_url, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                conn.commit(); batch = []
        if batch:
            conn.executemany(
                "INSERT INTO patristic_catena "
                "(father_name, father_category, year, book, chapter, verse_start, verse_end, "
                "quote, source_title, source_url, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
            conn.commit()

        conn.execute("ANALYZE"); conn.commit()
        console.print(f"  [green]✓[/green] Imported {count:,} public-domain father excerpts "
                      f"([yellow]{skipped:,} skipped[/yellow]: post-1900 / unmapped books)")
    finally:
        src.close()
        conn.close()


if __name__ == "__main__":
    main()
