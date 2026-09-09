#!/usr/bin/env python3
"""
Download public-domain Bible dictionaries (JSON) for the `dictionaries` table.

Sources are registered in parsers/dictionaries.py. Files land in
data/dictionaries/. Re-run to refresh.
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.dictionaries import DICTIONARY_SOURCES

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


@click.command()
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(data_dir: str | None):
    """Download registered PD dictionary sources."""
    console.print("[bold blue]Study Bible MCP - Dictionary Download[/bold blue]\n")
    out = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data" / "dictionaries")
    out.mkdir(parents=True, exist_ok=True)

    for source_id, spec in DICTIONARY_SOURCES.items():
        dest = out / spec["filename"]
        console.print(f"[cyan]{source_id}[/cyan] ({spec['name']}) -> {dest.name}")
        try:
            resp = httpx.get(spec["url"], follow_redirects=True, timeout=120)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            console.print(f"  [green]saved[/green] {len(resp.content):,} bytes")
        except Exception as e:
            console.print(f"  [red]failed:[/red] {e}")

    console.print("\n[green]Done.[/green] Now run import_dictionaries.py.")


if __name__ == "__main__":
    main()
