#!/usr/bin/env python3
"""
Import TheologAI's historical documents + UBS parallel passages into the database.

Run after build_database.py (calls create_schema itself). Downloads via
scripts/download_theologai.py.
"""

import json
import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers.theologai import DOC_TRADITION, parse_historical_document, parse_ubs_parallels

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
    """Import historical documents + UBS parallel passages."""
    console.print("[bold blue]Study Bible MCP - TheologAI Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    base = (Path(data_dir) if data_dir else (project_dir / "data")) / "theologai"

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    try:
        create_schema(conn)

        # --- Historical documents ---
        hist_dir = base / "historical"
        conn.execute("DELETE FROM historical_documents")
        docs, sections = 0, 0
        for doc_id in DOC_TRADITION:
            f = hist_dir / f"{doc_id}.json"
            if not f.exists():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            for row in parse_historical_document(data, doc_id):
                conn.execute(
                    "INSERT INTO historical_documents "
                    "(doc_id, doc_title, doc_type, doc_date, tradition, section_num, section_label, content, topics) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (row["doc_id"], row["doc_title"], row["doc_type"], row["doc_date"],
                     row["tradition"], row["section_num"], row["section_label"],
                     row["content"], row["topics"]))
                sections += 1
            docs += 1
        conn.commit()
        console.print(f"  [green]✓[/green] Historical documents: {docs} documents, {sections:,} sections")

        # --- UBS parallel passages ---
        xml_f = base / "ParallelPassages.xml"
        if xml_f.exists():
            conn.execute("DELETE FROM parallel_passages")
            count, batch = 0, []
            for row in parse_ubs_parallels(xml_f.read_text(encoding="utf-8")):
                batch.append((row["group_id"], row["book"], row["chapter"],
                              row["verse_start"], row["verse_end"], row["ref_display"]))
                count += 1
                if len(batch) >= 1000:
                    conn.executemany(
                        "INSERT INTO parallel_passages "
                        "(group_id, book, chapter, verse_start, verse_end, ref_display) "
                        "VALUES (?, ?, ?, ?, ?, ?)", batch)
                    conn.commit(); batch = []
            if batch:
                conn.executemany(
                    "INSERT INTO parallel_passages "
                    "(group_id, book, chapter, verse_start, verse_end, ref_display) "
                    "VALUES (?, ?, ?, ?, ?, ?)", batch)
                conn.commit()
            groups = conn.execute("SELECT COUNT(DISTINCT group_id) FROM parallel_passages").fetchone()[0]
            console.print(f"  [green]✓[/green] UBS parallel passages: {count:,} refs in {groups:,} groups")
        else:
            console.print("  [yellow]ParallelPassages.xml not found — skipped[/yellow]")

        conn.execute("ANALYZE"); conn.commit()
        console.print("\n[bold green]✓ TheologAI import complete![/bold green]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
