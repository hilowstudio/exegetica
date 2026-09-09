#!/usr/bin/env python3
"""
Download two openly-licensed datasets vendored by TJ-Frederick/TheologAI:
  - 17 historical documents (creeds, confessions, catechisms) — public domain.
  - The UBS Parallel Passage Database (ParallelPassages.xml) — CC BY-SA 4.0.
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.theologai import DOC_TRADITION

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

RAW = "https://raw.githubusercontent.com/TJ-Frederick/TheologAI/main"


@click.command()
@click.option("--force", "-f", is_flag=True, help="Re-download even if cached")
@click.option("--data-dir", "-d", type=click.Path(), help="Data directory (default: ./data)")
def main(force: bool, data_dir: str | None):
    """Download TheologAI historical documents + UBS parallel passages."""
    console.print("[bold blue]Study Bible MCP - TheologAI Data Downloader[/bold blue]")
    console.print("Historical documents (Public Domain) + UBS Parallel Passages (CC BY-SA 4.0)\n")

    base = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
    hist_dir = base / "theologai" / "historical"
    hist_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=30.0), follow_redirects=True) as client:
        console.print("Historical documents:")
        for doc_id in DOC_TRADITION:
            dest = hist_dir / f"{doc_id}.json"
            if dest.exists() and not force:
                ok += 1
                continue
            r = client.get(f"{RAW}/data/historical-documents/{doc_id}.json")
            if r.status_code == 200:
                dest.write_bytes(r.content)
                ok += 1
            else:
                console.print(f"  [red]✗[/red] {doc_id} (HTTP {r.status_code})")
        console.print(f"  [green]✓[/green] {ok}/{len(DOC_TRADITION)} documents")

        xml_dest = base / "theologai" / "ParallelPassages.xml"
        if xml_dest.exists() and not force:
            console.print("UBS parallel passages: [dim]cached[/dim]")
        else:
            console.print("UBS parallel passages:")
            r = client.get(f"{RAW}/data/parallel-passages/ubs-paratext/ParallelPassages.xml")
            r.raise_for_status()
            xml_dest.write_bytes(r.content)
            console.print(f"  [green]✓[/green] {len(r.content) / 1024:.0f} KB")

    console.print("\nNext: [bold]python scripts/import_theologai.py[/bold]")


if __name__ == "__main__":
    main()
