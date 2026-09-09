#!/usr/bin/env python3
"""
Download public-domain verse-keyed devotionals (JSON) for the `devotionals` table.

Sources registered in parsers/devotionals.py. Files land in data/devotionals/.
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.devotionals import DEVOTIONAL_SOURCES

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


@click.command()
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(data_dir: str | None):
    """Download registered devotional sources."""
    console.print("[bold blue]Study Bible MCP - Devotional Download[/bold blue]\n")
    out = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data" / "devotionals")
    out.mkdir(parents=True, exist_ok=True)

    for source_id, spec in DEVOTIONAL_SOURCES.items():
        dest = out / spec["filename"]
        try:
            resp = httpx.get(spec["url"], follow_redirects=True, timeout=120)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            console.print(f"[green]{source_id}[/green] ({spec['name']}): {len(resp.content):,} bytes")
        except Exception as e:
            console.print(f"[red]{source_id} failed:[/red] {e}")
    console.print("\nNow run import_devotionals.py.")


if __name__ == "__main__":
    main()
