#!/usr/bin/env python3
"""
Reload the ACAI entity annotations (people, places, groups, key terms) into an existing Study Bible
database, without the full rebuild that build_database.py needs.

Run after `scripts/download_stepbible.py --aquifer`. Rows are written with INSERT OR REPLACE by
ACAI id, so running it twice changes nothing. lookup_name ties an ACAI record to a name entry by
name and verse (database.acai_for_names), so more records mean more entries enriched.
"""

import sqlite3
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from build_database import console, import_acai_entities  # noqa: E402
from studybible_mcp.database import create_schema  # noqa: E402


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(db_path: str | None, data_dir: str | None):
    """Reload ACAI entities into study_bible.db."""
    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else project_dir / "db" / "study_bible.db"
    acai_dir = (Path(data_dir) if data_dir else project_dir / "data") / "acai"
    if not db_file.exists() or not acai_dir.exists():
        console.print(f"[red]Need {db_file} and {acai_dir}.[/red] Run build_database.py and "
                      "download_stepbible.py --aquifer first.")
        sys.exit(1)
    conn = sqlite3.connect(db_file)
    try:
        create_schema(conn)
        import_acai_entities(conn, acai_dir)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
