#!/usr/bin/env python3
"""
Give the Hebrew lexicon real short definitions, and add the numbers BDB lacks, from TBESH.

The BDB import often stores a grammar label as the short definition ("noun masculine plural"
for elohim), and BDB has no entry at all for some common words (H5921 'al, H0136 Adonai,
H0085 Abraham). TBESH, STEPBible's brief Hebrew lexicon (CC BY 4.0), glosses every number.
This script leads each Hebrew short definition with the TBESH glosses and keeps the BDB senses
TBESH confirms (see studybible_mcp.parsers.lexicon.hebrew_short_definition), then inserts a
TBESH-only row for each missing number up to H8674.

Run after build_database.py and build_word_frequency.py (the frequencies rank a number's
senses). It recomputes from DictBDB.json each time, so running it twice changes nothing.
Existing rows are updated in place, so their ids stay put.
"""

import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.lexicon import (
    hebrew_short_definition, parse_bdb_lexicon, parse_tbesh_glosses, tbesh_entry,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

LAST_STRONGS = 8674  # TBESH's H9000s tag prefixes and suffixes, which no lexicon entry needs


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(db_path: str | None, data_dir: str | None):
    """Fill Hebrew short definitions and missing entries from TBESH."""
    console.print("[bold blue]Study Bible MCP - Hebrew glosses from TBESH[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data")
    tbesh_path, bdb_path = data / "TBESH.txt", data / "DictBDB.json"

    for p in (tbesh_path, bdb_path, db_file):
        if not p.exists():
            console.print(f"[red]Missing {p}[/red]. Run download_stepbible.py and build_database.py first.")
            sys.exit(1)

    tbesh = parse_tbesh_glosses(tbesh_path)
    bdb = {e["strongs"]: e["short_definition"] for e in parse_bdb_lexicon(bdb_path)}

    conn = sqlite3.connect(db_file)
    try:
        counts = {s: n for s, n in conn.execute(
            "SELECT strongs, count FROM word_frequency WHERE language = 'hebrew'")}
        if not counts:
            console.print("[yellow]word_frequency is empty; senses keep file order. "
                          "Run build_word_frequency.py first for the better order.[/yellow]")

        rows = conn.execute(
            "SELECT strongs, short_definition FROM lexicon WHERE language = 'hebrew'").fetchall()
        have = {s for s, _ in rows}
        updates = []
        for strongs, current in rows:
            new = hebrew_short_definition(bdb.get(strongs, current or ""), tbesh.get(strongs), counts)
            if new != current:
                updates.append((new, strongs))
        conn.executemany(
            "UPDATE lexicon SET short_definition = ? WHERE strongs = ? AND language = 'hebrew'", updates)
        console.print(f"  [green]✓[/green] {len(updates):,} of {len(rows):,} short definitions updated")

        added = []
        for base, info in tbesh.items():
            if base in have or int(base[1:]) > LAST_STRONGS:
                continue
            e = tbesh_entry(base, info, counts)
            added.append((e["strongs"], e["language"], e["word"], e["transliteration"], e["pronunciation"],
                          e["short_definition"], e["full_definition"], e["etymology"], e["usage_count"],
                          e["semantic_domain"], e["related_words"]))
        conn.executemany(
            "INSERT OR IGNORE INTO lexicon (strongs, language, word, transliteration, pronunciation, "
            "short_definition, full_definition, etymology, usage_count, semantic_domain, related_words) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", added)
        conn.commit()
        console.print(f"  [green]✓[/green] {len(added):,} numbers BDB lacks added from TBESH")
        console.print("[dim]Glosses: TBESH, STEPBible.org / Tyndale House (CC BY 4.0).[/dim]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
