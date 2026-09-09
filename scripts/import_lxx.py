#!/usr/bin/env python3
"""
Import the Greek Septuagint (Swete) text and the LXX<->standard versification
map into the Study Bible database.

Run after build_database.py (it calls create_schema() itself, so it also adds
the new tables to a database built before these tables existed, without a full
rebuild). Downloads are handled by scripts/download_lxx.py.
"""

import sqlite3
import sys
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.database import create_schema
from studybible_mcp.parsers.lxx import parse_swete_lxx, parse_versification_map, parse_brenton

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
    """Import Greek LXX text + versification map."""
    console.print("[bold blue]Study Bible MCP - LXX Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    data = Path(data_dir) if data_dir else (project_dir / "data")

    vers_csv = data / "lxx" / "swete_versification.csv"
    words_csv = data / "lxx" / "swete_words.csv"
    lxx_json = data / "lxx" / "copenhagen_lxx.json"
    eng_json = data / "lxx" / "copenhagen_eng.json"

    for p in (vers_csv, words_csv, lxx_json, eng_json):
        if not p.exists():
            console.print(f"[red]Missing {p}[/red]. Run [bold]python scripts/download_lxx.py[/bold] first.")
            sys.exit(1)
    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_file)
    try:
        create_schema(conn)  # idempotent: adds lxx_verses + versification_map if missing

        # --- LXX Greek text ---
        console.print("Importing Swete LXX Greek text...")
        conn.execute("DELETE FROM lxx_verses")
        count, batch = 0, []
        for v in parse_swete_lxx(vers_csv, words_csv):
            batch.append((v["reference"], v["book"], v["chapter"], v["verse"], v["text_greek"]))
            count += 1
            if len(batch) >= 1000:
                conn.executemany(
                    "INSERT OR REPLACE INTO lxx_verses (reference, book, chapter, verse, text_greek) "
                    "VALUES (?, ?, ?, ?, ?)", batch)
                conn.commit(); batch = []
        if batch:
            conn.executemany(
                "INSERT OR REPLACE INTO lxx_verses (reference, book, chapter, verse, text_greek) "
                "VALUES (?, ?, ?, ?, ?)", batch)
            conn.commit()
        console.print(f"  [green]✓[/green] {count:,} LXX verses")

        # --- Brenton English (pair onto the Greek verses by LXX reference) ---
        brenton_zip = data / "lxx" / "brenton_usfm.zip"
        if brenton_zip.exists():
            console.print("Importing Brenton English Septuagint...")
            pairs = [(v["text_english"], v["reference"]) for v in parse_brenton(brenton_zip)]
            conn.executemany(
                "UPDATE lxx_verses SET text_english = ? WHERE reference = ?", pairs)
            conn.commit()
            matched = conn.execute(
                "SELECT COUNT(*) FROM lxx_verses WHERE text_english IS NOT NULL").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM lxx_verses").fetchone()[0]
            console.print(
                f"  [green]✓[/green] Brenton paired to {matched:,}/{total:,} Greek verses "
                f"({100*matched//max(total,1)}%)")
        else:
            console.print("  [yellow]Brenton USFM not found — Greek text only.[/yellow]")

        # --- Versification map ---
        console.print("Importing Copenhagen versification map...")
        conn.execute("DELETE FROM versification_map")
        mcount, batch = 0, []
        for r in parse_versification_map(lxx_json, eng_json):
            batch.append((r["lxx_ref"], r["standard_ref"], r["base_ref"]))
            mcount += 1
        conn.executemany(
            "INSERT OR REPLACE INTO versification_map (lxx_ref, standard_ref, base_ref) "
            "VALUES (?, ?, ?)", batch)
        conn.commit()
        console.print(f"  [green]✓[/green] {mcount:,} versification mappings")

        conn.execute("ANALYZE"); conn.commit()
        console.print("\n[bold green]✓ LXX import complete![/bold green]")
        console.print("[dim]Text: Swete LXX (Public Domain). Mapping: Copenhagen (CC BY).[/dim]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
