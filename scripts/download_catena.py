#!/usr/bin/env python3
"""
Download the HistoricalChristianFaith Commentaries-Database (prebuilt SQLite of
church-father comment excerpts keyed to verses).
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

URL = ("https://github.com/HistoricalChristianFaith/Commentaries-Database/"
       "releases/download/latest/commentaries.sqlite")


@click.command()
@click.option("--force", "-f", is_flag=True, help="Re-download even if cached")
@click.option("--data-dir", "-d", type=click.Path(), help="Data directory (default: ./data)")
def main(force: bool, data_dir: str | None):
    """Download the patristic catena database (~150 MB)."""
    console.print("[bold blue]Study Bible MCP - Patristic Catena Downloader[/bold blue]")
    console.print("Source: HistoricalChristianFaith/Commentaries-Database\n")

    base = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
    dest = base / "patristic" / "commentaries.sqlite"
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        console.print(f"  [dim]Cached: {dest}[/dim]")
    else:
        console.print("Downloading commentaries.sqlite (~150 MB)...")
        r = httpx.get(URL, follow_redirects=True, timeout=httpx.Timeout(300.0, connect=30.0))
        r.raise_for_status()
        dest.write_bytes(r.content)
        console.print(f"  [green]✓[/green] {len(r.content) / (1024*1024):.0f} MB")

    console.print("\nNext: [bold]python scripts/import_catena.py[/bold]")


if __name__ == "__main__":
    main()
