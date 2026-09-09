#!/usr/bin/env python3
"""
Materialize the `word_frequency` table from the owned STEPBible tags.

Scans every verse's `word_data` (per-word JSON carrying each word's Strong's
number) and counts occurrences per Strong's across the whole tagged corpus
(Hebrew OT + Greek NT). This is computed entirely from data we already own —
no external download — and powers reader-mode vocabulary (the rarest words in
a passage). Safe to re-run; it rebuilds the table each time.

Run after build_database.py. create_schema() adds the table to an existing
database, so this also works against an already-built DB without a full rebuild.
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


def _language_of(strongs: str) -> str:
    s = (strongs or "").strip().upper()
    if s.startswith("H"):
        return "hebrew"
    if s.startswith("G"):
        return "greek"
    return "other"


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
def main(db_path: str | None):
    """Count Strong's occurrences across the tagged corpus."""
    console.print("[bold blue]Study Bible MCP - Word Frequency[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    create_schema(conn)  # ensures word_frequency exists

    counts: dict[str, int] = defaultdict(int)
    scanned = 0
    cur = conn.execute("SELECT word_data FROM verses WHERE word_data IS NOT NULL")
    for (raw,) in cur:
        if not raw:
            continue
        try:
            words = json.loads(raw)
        except (ValueError, TypeError):
            continue
        scanned += 1
        for w in words:
            if not isinstance(w, dict):
                continue
            s = (w.get("strongs") or "").strip().upper()
            if s:
                counts[s] += 1

    console.print(f"Scanned [cyan]{scanned:,}[/cyan] tagged verses; "
                  f"[cyan]{len(counts):,}[/cyan] distinct Strong's numbers.")

    conn.execute("DELETE FROM word_frequency")
    conn.executemany(
        "INSERT INTO word_frequency (strongs, language, count) VALUES (?, ?, ?)",
        [(s, _language_of(s), n) for s, n in counts.items()],
    )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM word_frequency").fetchone()[0]
    heb = conn.execute("SELECT COUNT(*) FROM word_frequency WHERE language='hebrew'").fetchone()[0]
    grk = conn.execute("SELECT COUNT(*) FROM word_frequency WHERE language='greek'").fetchone()[0]
    console.print(f"[green]word_frequency:[/green] {total:,} rows "
                  f"([cyan]{heb:,}[/cyan] Hebrew, [cyan]{grk:,}[/cyan] Greek).")
    conn.close()


if __name__ == "__main__":
    main()
