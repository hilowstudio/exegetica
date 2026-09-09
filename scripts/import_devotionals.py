#!/usr/bin/env python3
"""
Import public-domain devotionals into the `devotionals` table.

Reads each registered source from data/devotionals/, dispatches to its parser
(parsers/devotionals.py), and inserts verse-keyed daily readings. Re-running
replaces a source's rows. Downloads via download_devotionals.py.
"""

import json
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers import devotionals as devmod
from studybible_mcp.parsers.devotionals import DEVOTIONAL_SOURCES

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
    """Import devotionals into the database."""
    console.print("[bold blue]Study Bible MCP - Devotional Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data" / "devotionals")
    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    create_schema(conn)

    total = 0
    for source_id, spec in DEVOTIONAL_SOURCES.items():
        path = data / spec["filename"]
        if not path.exists():
            console.print(f"[yellow]skip[/yellow] {source_id}: {path.name} not found")
            continue
        parser = getattr(devmod, spec["parser"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = list(parser(payload, source_id, spec["name"]))
        conn.execute("DELETE FROM devotionals WHERE source = ?", (source_id,))
        conn.executemany(
            "INSERT INTO devotionals (source, source_name, title, month, day, "
            "time_of_day, key_ref, book, chapter, verse, body) "
            "VALUES (:source, :source_name, :title, :month, :day, :time_of_day, "
            ":key_ref, :book, :chapter, :verse, :body)",
            rows,
        )
        conn.commit()
        keyed = sum(1 for r in rows if r["book"])
        console.print(f"[green]{source_id}[/green]: {len(rows):,} readings ({keyed:,} verse-keyed)")
        total += len(rows)

    grand = conn.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    console.print(f"\n[bold green]devotionals total:[/bold green] {grand:,} rows.")
    conn.close()


if __name__ == "__main__":
    main()
