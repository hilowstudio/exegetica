#!/usr/bin/env python3
"""
Download the curated set of public-domain / open English translations (USFM)
from eBible.org: BSB, WEB, KJV, ASV, YLT.
"""

import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.translations import TRANSLATIONS

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)


@click.command()
@click.option("--force", "-f", is_flag=True, help="Re-download even if files exist")
@click.option("--data-dir", "-d", type=click.Path(), help="Data directory (default: ./data)")
def main(force: bool, data_dir: str | None):
    """Download curated readable translations (USFM) from eBible.org."""
    console.print("[bold blue]Study Bible MCP - Translation Downloader[/bold blue]")
    console.print("Source: eBible.org (public-domain / open translations)\n")

    base = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
    dest_dir = base / "translations"
    dest_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    with httpx.Client(timeout=httpx.Timeout(120.0, connect=30.0), follow_redirects=True) as client:
        for abbrev, (ebible_id, name, _lic) in TRANSLATIONS.items():
            dest = dest_dir / f"{abbrev}.zip"
            if dest.exists() and not force:
                console.print(f"  [dim]Skipping {abbrev} ({name}) — cached[/dim]")
                ok += 1
                continue
            url = f"https://ebible.org/Scriptures/{ebible_id}_usfm.zip"
            console.print(f"[bold]{abbrev}[/bold] ({name})")
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    dest.write_bytes(resp.content)
                    console.print(f"  [green]✓[/green] {len(resp.content) / (1024*1024):.1f} MB")
                    ok += 1
                else:
                    console.print(f"  [red]✗[/red] HTTP {resp.status_code} ({url})")
            except Exception as e:
                console.print(f"  [red]✗[/red] {e}")

    console.print(f"\n[bold]Downloaded {ok}/{len(TRANSLATIONS)} translations[/bold]")
    if ok:
        console.print("Next: [bold]python scripts/import_translations.py[/bold]")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
