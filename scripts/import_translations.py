#!/usr/bin/env python3
"""
Import the curated readable translations into the `translations` table.

Run after build_database.py (it calls create_schema() itself, so it also adds
the translations table to an existing database). Downloads via
scripts/download_translations.py.
"""

import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers.translations import TRANSLATIONS, parse_usfm_bible

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
    """Import curated readable translations into the database."""
    console.print("[bold blue]Study Bible MCP - Translation Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data")

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    try:
        create_schema(conn)  # ensures the translations table exists
        total = 0
        for abbrev, (_ebible_id, name, _lic) in TRANSLATIONS.items():
            zip_path = data / "translations" / f"{abbrev}.zip"
            if not zip_path.exists():
                console.print(f"  [yellow]Skipping {abbrev} — {zip_path} not found[/yellow]")
                continue
            conn.execute("DELETE FROM translations WHERE translation = ?", (abbrev,))
            count, batch = 0, []
            for v in parse_usfm_bible(zip_path):
                batch.append((abbrev, v["reference"], v["book"], v["chapter"], v["verse"], v["text"]))
                count += 1
                if len(batch) >= 1000:
                    conn.executemany(
                        "INSERT OR REPLACE INTO translations "
                        "(translation, reference, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?, ?)",
                        batch)
                    conn.commit(); batch = []
            if batch:
                conn.executemany(
                    "INSERT OR REPLACE INTO translations "
                    "(translation, reference, book, chapter, verse, text) VALUES (?, ?, ?, ?, ?, ?)",
                    batch)
                conn.commit()
            console.print(f"  [green]✓[/green] {abbrev} ({name}): {count:,} verses")
            total += count

        conn.execute("ANALYZE"); conn.commit()
        console.print(f"\n[bold green]✓ Imported {total:,} verses across {len(TRANSLATIONS)} translations[/bold green]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
