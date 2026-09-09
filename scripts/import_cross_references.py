#!/usr/bin/env python3
"""
Import OpenBible.info cross-references into the Study Bible database.

Source: https://www.openbible.info/labs/cross-references/ (CC BY 4.0).
~344k community-voted cross-references (derived from the Treasury of Scripture
Knowledge plus OpenBible's topical/search data). We store the vote count as the
`relevance` weight; the query layer ranks by it.

OpenBible uses OSIS book codes (Gen, Exod, Ps, Matt, John, 1John, ...); we map
them to the internal STEPBible codes used by the `verses` table (Gen, Exo, Psa,
Mat, Jhn, 1Jn, ...) so a cross-reference's `source` matches what
StudyBibleDB._normalize_reference() produces for a user query.
"""

import io
import sqlite3
import sys
import zipfile
from pathlib import Path

import click
import httpx
from rich.console import Console

# Force UTF-8 output so rich can render ✓/✗ on Windows consoles.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

XREF_URL = "https://a.openbible.info/data/cross-references.zip"

# OSIS book code -> internal (STEPBible) code used across the database.
OSIS_TO_INTERNAL = {
    "Gen": "Gen", "Exod": "Exo", "Lev": "Lev", "Num": "Num", "Deut": "Deu",
    "Josh": "Jos", "Judg": "Jdg", "Ruth": "Rut",
    "1Sam": "1Sa", "2Sam": "2Sa", "1Kgs": "1Ki", "2Kgs": "2Ki",
    "1Chr": "1Ch", "2Chr": "2Ch", "Ezra": "Ezr", "Neh": "Neh", "Esth": "Est",
    "Job": "Job", "Ps": "Psa", "Prov": "Pro", "Eccl": "Ecc", "Song": "Sng",
    "Isa": "Isa", "Jer": "Jer", "Lam": "Lam", "Ezek": "Ezk", "Dan": "Dan",
    "Hos": "Hos", "Joel": "Jol", "Amos": "Amo", "Obad": "Oba", "Jonah": "Jon",
    "Mic": "Mic", "Nah": "Nam", "Hab": "Hab", "Zeph": "Zep", "Hag": "Hag",
    "Zech": "Zec", "Mal": "Mal",
    "Matt": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn", "Acts": "Act",
    "Rom": "Rom", "1Cor": "1Co", "2Cor": "2Co", "Gal": "Gal", "Eph": "Eph",
    "Phil": "Php", "Col": "Col", "1Thess": "1Th", "2Thess": "2Th",
    "1Tim": "1Ti", "2Tim": "2Ti", "Titus": "Tit", "Phlm": "Phm", "Heb": "Heb",
    "Jas": "Jas", "1Pet": "1Pe", "2Pet": "2Pe", "1John": "1Jn", "2John": "2Jn",
    "3John": "3Jn", "Jude": "Jud", "Rev": "Rev",
}


def convert_single(osis_ref: str) -> str:
    """'John.3.16' -> 'Jhn.3.16' (internal book code)."""
    parts = osis_ref.split(".")
    if not parts:
        return osis_ref
    book = OSIS_TO_INTERNAL.get(parts[0], parts[0])
    return ".".join([book] + parts[1:])


def convert_ref(osis_ref: str) -> str:
    """Handle single verses and ranges ('Col.1.16-Col.1.17')."""
    if "-" in osis_ref:
        start, end = osis_ref.split("-", 1)
        return f"{convert_single(start)}-{convert_single(end)}"
    return convert_single(osis_ref)


def download_data(cache: Path | None) -> str:
    """Return the cross_references.txt content, using a cached zip if present."""
    if cache and cache.exists():
        console.print(f"Using cached [bold]{cache.name}[/bold]")
        raw = cache.read_bytes()
    else:
        console.print(f"Downloading OpenBible cross-references from {XREF_URL} ...")
        resp = httpx.get(XREF_URL, follow_redirects=True, timeout=120)
        resp.raise_for_status()
        raw = resp.content
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
    z = zipfile.ZipFile(io.BytesIO(raw))
    return z.read("cross_references.txt").decode("utf-8", "replace")


@click.command()
@click.option("--db-path", "-d", type=click.Path(), help="Path to database")
@click.option("--data-dir", type=click.Path(), help="Directory for the cached zip")
def main(db_path: str | None, data_dir: str | None):
    """Import OpenBible.info cross-references (CC BY 4.0) into the database."""
    console.print("[bold blue]Study Bible MCP - OpenBible Cross-References Import[/bold blue]\n")

    project_dir = Path(__file__).parent.parent
    db_file = Path(db_path) if db_path else (project_dir / "db" / "study_bible.db")
    cache = (Path(data_dir) if data_dir else (project_dir / "data")) / "cross-references.zip"

    if not db_file.exists():
        console.print(f"[red]Database not found: {db_file}[/red]")
        console.print("Run [bold]python scripts/build_database.py[/bold] first.")
        sys.exit(1)

    text = download_data(cache)
    lines = text.splitlines()

    conn = sqlite3.connect(db_file)
    try:
        # Replace any prior OpenBible rows so re-runs are idempotent.
        conn.execute("DELETE FROM cross_references WHERE type = 'openbible'")

        count = 0
        skipped = 0
        batch: list[tuple] = []
        for line in lines:
            if not line or line.startswith("From Verse") or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            frm, to, votes = parts[0], parts[1], parts[2]
            try:
                relevance = int(votes)
            except ValueError:
                relevance = 0
            source = convert_single(frm)
            target = convert_ref(to)
            # Sanity: source book must be known, else skip (bad row).
            if frm.split(".")[0] not in OSIS_TO_INTERNAL:
                skipped += 1
                continue
            batch.append((source, target, "openbible", None, relevance))
            count += 1
            if len(batch) >= 5000:
                conn.executemany(
                    "INSERT INTO cross_references (source, target, type, note, relevance) "
                    "VALUES (?, ?, ?, ?, ?)", batch)
                conn.commit()
                batch = []

        if batch:
            conn.executemany(
                "INSERT INTO cross_references (source, target, type, note, relevance) "
                "VALUES (?, ?, ?, ?, ?)", batch)
            conn.commit()

        conn.execute("ANALYZE")
        conn.commit()
        console.print(f"\n[green]✓[/green] Imported {count:,} cross-references"
                      + (f" ([yellow]{skipped} skipped[/yellow])" if skipped else ""))
        console.print("[dim]Source: OpenBible.info (CC BY 4.0)[/dim]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
