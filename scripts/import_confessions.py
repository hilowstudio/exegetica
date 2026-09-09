#!/usr/bin/env python3
"""
Import compendium confessions: proof-texts (all docs) + net-new documents.

- confession_proof_texts: one row per (article/question, marker, cited verse),
  resolved from OSIS to internal verse spans. Powers find_confessions_by_verse
  and get_confession_proofs.
- historical_documents: sections for the standards NOT already bundled from
  TheologAI (Savoy, Second Helvetic, Scots, Keach, ...), extending get_confession.

Run after download_confessions.py.
"""

import sqlite3
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers.confessions import (
    COMPENDIUM_DOCS, COMPENDIUM_NEW_DOCS,
    parse_compendium_proofs, parse_compendium_sections,
)

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
    """Import compendium proof-texts and net-new documents."""
    console.print("[bold blue]Study Bible MCP - Confession Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data" / "confessions" / "compendium")
    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    create_schema(conn)

    proof_rows = 0
    doc_ids = list(COMPENDIUM_DOCS)
    conn.execute(
        f"DELETE FROM confession_proof_texts WHERE doc_id IN ({','.join('?' for _ in doc_ids)})",
        doc_ids,
    )
    new_doc_ids = list(COMPENDIUM_NEW_DOCS)
    conn.execute(
        f"DELETE FROM historical_documents WHERE doc_id IN ({','.join('?' for _ in new_doc_ids)})",
        new_doc_ids,
    )

    section_rows = 0
    for doc_id in COMPENDIUM_DOCS:
        path = data / f"{doc_id}.yaml"
        if not path.exists():
            console.print(f"[yellow]skip[/yellow] {doc_id}: not downloaded")
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))

        proofs = list(parse_compendium_proofs(doc, doc_id))
        conn.executemany(
            "INSERT INTO confession_proof_texts "
            "(doc_id, doc_title, section_label, section_text, marker, osis_ref, "
            " book, chapter, verse_start, verse_end) "
            "VALUES (:doc_id, :doc_title, :section_label, :section_text, :marker, "
            ":osis_ref, :book, :chapter, :verse_start, :verse_end)",
            proofs,
        )
        proof_rows += len(proofs)

        if doc_id in COMPENDIUM_NEW_DOCS:
            secs = list(parse_compendium_sections(doc, doc_id))
            conn.executemany(
                "INSERT INTO historical_documents "
                "(doc_id, doc_title, doc_type, doc_date, tradition, section_num, "
                " section_label, content, topics) "
                "VALUES (:doc_id, :doc_title, :doc_type, :doc_date, :tradition, "
                ":section_num, :section_label, :content, :topics)",
                secs,
            )
            section_rows += len(secs)
            console.print(f"  [green]{doc_id}[/green]: {len(proofs)} proofs, "
                          f"{len(secs)} sections (new doc)")
        else:
            console.print(f"  [cyan]{doc_id}[/cyan]: {len(proofs)} proofs")

    conn.commit()
    total_proofs = conn.execute("SELECT COUNT(*) FROM confession_proof_texts").fetchone()[0]
    total_docs = conn.execute("SELECT COUNT(DISTINCT doc_id) FROM historical_documents").fetchone()[0]
    console.print(f"\n[bold green]confession_proof_texts:[/bold green] {total_proofs:,} rows "
                  f"({proof_rows:,} inserted).")
    console.print(f"[bold green]historical_documents:[/bold green] {total_docs} documents "
                  f"(+{section_rows:,} sections from {len(COMPENDIUM_NEW_DOCS)} new standards).")
    conn.close()


if __name__ == "__main__":
    main()
