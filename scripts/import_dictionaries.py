#!/usr/bin/env python3
"""
Import public-domain Bible dictionaries into the `dictionaries` table.

Reads each registered source from data/dictionaries/, dispatches to its parser
(parsers/dictionaries.py), and inserts headword-keyed articles. Re-running
replaces a source's rows in place. Downloads via download_dictionaries.py.
"""

import json
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers import dictionaries as dictmod

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(db_path: str | None, data_dir: str | None):
    """Import PD dictionaries into the database."""
    console.print("[bold blue]Study Bible MCP - Dictionary Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data" / "dictionaries")

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    from studybible_mcp.database import create_schema
    from studybible_mcp.parsers.dictionaries import DICTIONARY_SOURCES

    conn = sqlite3.connect(db_file)
    create_schema(conn)

    grand = 0
    for source_id, spec in DICTIONARY_SOURCES.items():
        path = data / spec["filename"]
        if not path.exists():
            console.print(f"[yellow]skip[/yellow] {source_id}: {path.name} not found")
            continue
        parser = getattr(dictmod, spec["parser"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = [
            (source_id, spec["name"], r["headword"], r["body"])
            for r in parser(payload)
        ]
        conn.execute("DELETE FROM dictionaries WHERE source = ?", (source_id,))
        conn.executemany(
            "INSERT INTO dictionaries (source, source_name, headword, body) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        console.print(f"[green]{source_id}[/green]: {len(rows):,} articles")
        grand += len(rows)

    total = conn.execute("SELECT COUNT(*) FROM dictionaries").fetchone()[0]
    console.print(f"\n[bold green]dictionaries total:[/bold green] {total:,} rows.")
    conn.close()


if __name__ == "__main__":
    main()
