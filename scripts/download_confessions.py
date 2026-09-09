#!/usr/bin/env python3
"""
Download reformed-standards/compendium confession & catechism YAML (Apache-2.0).

Files land in data/confessions/compendium/. Re-run to refresh.
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.confessions import COMPENDIUM_DOCS

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)
RAW = "https://raw.githubusercontent.com/reformed-standards/compendium/HEAD/data"


@click.command()
@click.option("--data-dir", type=click.Path(), help="Data directory")
def main(data_dir: str | None):
    """Download the compendium standards."""
    console.print("[bold blue]Study Bible MCP - Confession Download[/bold blue]\n")
    out = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data" / "confessions" / "compendium")
    out.mkdir(parents=True, exist_ok=True)

    ok = 0
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        for doc_id, path in COMPENDIUM_DOCS.items():
            try:
                resp = client.get(f"{RAW}/{path}.yaml")
                resp.raise_for_status()
                (out / f"{doc_id}.yaml").write_bytes(resp.content)
                ok += 1
            except Exception as e:
                console.print(f"  [red]{doc_id} failed:[/red] {e}")
    console.print(f"[green]Downloaded {ok}/{len(COMPENDIUM_DOCS)} documents[/green] to {out}")
    console.print("Now run import_confessions.py.")


if __name__ == "__main__":
    main()
