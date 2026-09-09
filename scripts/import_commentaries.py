#!/usr/bin/env python3
"""
Import the cached public-domain commentaries into the `commentaries` table.

Run after download_commentaries.py (and after build_database.py — it calls
create_schema() itself, so it also adds the table to an existing database).
"""

import json
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers.commentaries import COMMENTARIES, parse_commentary_chapter
from studybible_mcp.parsers.lxx import usfm_to_internal

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
    """Import cached public-domain commentaries into the database."""
    console.print("[bold blue]Study Bible MCP - Commentary Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    comm_dir = (Path(data_dir) if data_dir else (project_dir / "data")) / "commentaries"

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)
    if not comm_dir.exists():
        console.print(f"[red]No commentary data at {comm_dir}[/red]. Run download_commentaries.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    try:
        create_schema(conn)
        grand_total = 0
        for cid, name in COMMENTARIES.items():
            src_dir = comm_dir / cid
            if not src_dir.exists():
                console.print(f"  [yellow]Skipping {cid} — not downloaded[/yellow]")
                continue
            conn.execute("DELETE FROM commentaries WHERE source = ?", (cid,))
            count, batch = 0, []
            for book_dir in sorted(p for p in src_dir.iterdir() if p.is_dir()):
                book = usfm_to_internal(book_dir.name)
                for ch_file in book_dir.glob("*.json"):
                    if not ch_file.stem.isdigit():
                        continue
                    chapter = int(ch_file.stem)
                    try:
                        data = json.loads(ch_file.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    for row in parse_commentary_chapter(data, cid, book, chapter):
                        batch.append((row["source"], name, row["book"], row["chapter"],
                                      row["verse_start"], row["verse_end"], row["text"]))
                        count += 1
                        if len(batch) >= 1000:
                            conn.executemany(
                                "INSERT INTO commentaries "
                                "(source, source_name, book, chapter, verse_start, verse_end, text) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                            conn.commit(); batch = []
            if batch:
                conn.executemany(
                    "INSERT INTO commentaries "
                    "(source, source_name, book, chapter, verse_start, verse_end, text) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                conn.commit()
            console.print(f"  [green]✓[/green] {name}: {count:,} entries")
            grand_total += count

        conn.execute("ANALYZE"); conn.commit()
        console.print(f"\n[bold green]✓ Imported {grand_total:,} commentary entries[/bold green]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
