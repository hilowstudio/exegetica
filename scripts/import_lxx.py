#!/usr/bin/env python3
"""
Import the Greek Septuagint (Swete) text, Brenton's English paired with it, and the
LXX<->standard versification map into the Study Bible database.

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
from studybible_mcp.parsers.lxx import (
    align_brenton, content_routes, parse_brenton, parse_swete_lxx, parse_versification_map, swete_ref,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

# Greek-only units an English reference names in other ways (Greek Esther is cited as Esther, the
# Prayer of Manasseh and 2 Esdras have no Swete text), and the Psalms, which route through Hebrew.
_NOT_ROUTED = {"Esg", "Man", "2Es", "Psa"}


def english_bible(conn: sqlite3.Connection) -> dict[str, str]:
    """English text by English reference for the Old Testament and deuterocanon: the KJV, and the WEB
    for what the KJV lacks (the deuterocanon, and Susanna and Bel as Daniel 13-14). Brenton follows the
    KJV's wording, so it is the better match."""
    try:
        kjv_books = {b for (b,) in conn.execute("SELECT DISTINCT book FROM translations WHERE translation = 'KJV'")}
        out: dict[str, str] = {}
        for translation in ("KJV", "WEB"):
            for ref, book, chapter, text in conn.execute(
                    "SELECT reference, book, chapter, text FROM translations WHERE translation = ?", (translation,)):
                if book in _NOT_ROUTED:
                    continue
                if translation == "WEB" and book in kjv_books and (book, chapter) not in {("Dan", 13), ("Dan", 14)}:
                    continue
                out.setdefault(ref, text)
        return out
    except sqlite3.OperationalError:  # no translations table yet
        return {}


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

        # --- Brenton English, paired with the Greek by content (see parsers.lxx.align_brenton) ---
        greek = list(parse_swete_lxx(vers_csv, words_csv, include_empty=True))
        english: dict[str, str] = {}
        brenton_zip = data / "lxx" / "brenton_usfm.zip"
        if brenton_zip.exists():
            console.print("Aligning Brenton's English with the Greek (a minute or two)...")
            english = align_brenton(greek, list(parse_brenton(brenton_zip)))
        else:
            console.print("  [yellow]Brenton USFM not found: Greek text only.[/yellow]")

        # --- LXX Greek text ---
        # A verse the digitization numbers without Greek is kept only when Brenton's English fills it.
        console.print("Importing Swete LXX Greek text...")
        conn.execute("DELETE FROM lxx_verses")
        rows = [(v["reference"], v["book"], v["chapter"], v["verse"], v["text_greek"] or None,
                 english.get(v["reference"]))
                for v in greek if v["text_greek"] or v["reference"] in english]
        conn.executemany(
            "INSERT OR REPLACE INTO lxx_verses (reference, book, chapter, verse, text_greek, text_english) "
            "VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
        with_greek = sum(1 for r in rows if r[4])
        console.print(f"  [green]✓[/green] {with_greek:,} LXX verses with Greek, "
                      f"{len(rows) - with_greek:,} more with Brenton's English only")
        if english:
            console.print(f"  [green]✓[/green] Brenton paired to {len(english):,} verses")

        # --- Versification map, in Swete's numbering ---
        console.print("Importing Copenhagen versification map...")
        conn.execute("DELETE FROM versification_map")
        batch = [(swete_ref(r["lxx_ref"]), r["standard_ref"], r["base_ref"])
                 for r in parse_versification_map(lxx_json, eng_json)]
        conn.executemany(
            "INSERT OR REPLACE INTO versification_map (lxx_ref, standard_ref, base_ref) "
            "VALUES (?, ?, ?)", batch)
        conn.commit()
        console.print(f"  [green]✓[/green] {len(batch):,} versification mappings")

        # --- Routes checked by content, where Swete's numbering is not the map's ---
        conn.execute("DELETE FROM lxx_routes")
        bible = english_bible(conn)
        if not bible:
            console.print("  [yellow]No KJV or WEB text yet: run this again after import_translations.py "
                          "to check the routes by content.[/yellow]")
        elif english:
            routed: dict[str, str] = {}
            for lxx_ref, standard_ref, _ in batch:  # the server takes the first row for a standard_ref
                routed.setdefault(standard_ref, lxx_ref)
            routed = {e: swete_ref(routed.get(e, e)) for e in bible}
            # Daniel, Susanna, and Bel are looked up under the Old Greek's code, with Theodotion's English
            as_looked_up = {"Dat": "Dan", "Sut": "Sus", "Bet": "Bel"}
            def looked_up(ref: str) -> str:
                book, _, rest = ref.partition(".")
                return f"{as_looked_up.get(book, book)}.{rest}"
            greek_english = {looked_up(ref): text for ref, text in english.items()}
            swete_refs = {looked_up(r[0]) for r in rows}
            found = content_routes(bible, routed, greek_english, swete_refs)
            conn.executemany("INSERT INTO lxx_routes (standard_ref, lxx_ref, score) VALUES (?, ?, ?)",
                             [(e, ref, score) for e, (ref, score) in found.items()])
            conn.commit()
            console.print(f"  [green]✓[/green] {len(found):,} English verses re-routed to the Swete verse "
                          "that holds them")

        conn.execute("ANALYZE"); conn.commit()
        console.print("\n[bold green]✓ LXX import complete![/bold green]")
        console.print("[dim]Text: Swete LXX and Brenton (Public Domain). Mapping: Copenhagen (CC BY-SA 4.0).[/dim]")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
