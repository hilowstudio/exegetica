#!/usr/bin/env python3
"""
Download the Greek Septuagint (Swete) text and the Copenhagen versification
mappings needed to relate LXX verse numbering to the standard (English/Hebrew)
scheme used by the rest of the database.

Sources:
- Greek text: eliranwong/LXX-Swete-1930 — a complete digitization of H.B. Swete's
  "The Old Testament in Greek according to the Septuagint" (Cambridge, 1909-1930).
  The Swete edition is public domain; we bundle the Greek word forms only.
- Versification mappings: Copenhagen-Alliance/versification-specification
  (CC BY / open) — standard-mappings/{lxx,eng}.json.
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

SWETE_BASE = "https://raw.githubusercontent.com/eliranwong/LXX-Swete-1930/master"
COPENHAGEN_BASE = (
    "https://raw.githubusercontent.com/Copenhagen-Alliance/"
    "versification-specification/master/versification-mappings/standard-mappings"
)

FILES = {
    "swete_versification": (f"{SWETE_BASE}/00-Swete_versification.csv", "lxx/swete_versification.csv"),
    "swete_words": (f"{SWETE_BASE}/01-Swete_word_with_punctuations.csv", "lxx/swete_words.csv"),
    "map_lxx": (f"{COPENHAGEN_BASE}/lxx.json", "lxx/copenhagen_lxx.json"),
    "map_eng": (f"{COPENHAGEN_BASE}/eng.json", "lxx/copenhagen_eng.json"),
    # Brenton's English Septuagint (Public Domain), in LXX versification.
    "brenton": ("https://ebible.org/Scriptures/eng-Brenton_usfm.zip", "lxx/brenton_usfm.zip"),
}


@click.command()
@click.option("--force", "-f", is_flag=True, help="Re-download even if files exist")
@click.option("--data-dir", "-d", type=click.Path(), help="Data directory (default: ./data)")
def main(force: bool, data_dir: str | None):
    """Download Greek LXX (Swete) text + Copenhagen versification mappings."""
    console.print("[bold blue]Study Bible MCP - LXX Data Downloader[/bold blue]")
    console.print("Sources: Swete LXX (Public Domain) + Copenhagen versification (CC BY-SA 4.0)\n")

    base = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
    ok = 0
    with httpx.Client(timeout=httpx.Timeout(180.0, connect=30.0), follow_redirects=True) as client:
        for key, (url, rel) in FILES.items():
            dest = base / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not force:
                console.print(f"  [dim]Skipping {rel} (cached)[/dim]")
                ok += 1
                continue
            console.print(f"[bold]{key}[/bold] -> {rel}")
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    dest.write_bytes(resp.content)
                    console.print(f"  [green]✓[/green] {len(resp.content) / (1024*1024):.1f} MB")
                    ok += 1
                else:
                    console.print(f"  [red]✗[/red] HTTP {resp.status_code}")
            except Exception as e:
                console.print(f"  [red]✗[/red] {e}")

    console.print(f"\n[bold]Downloaded {ok}/{len(FILES)} files[/bold]")
    if ok == len(FILES):
        console.print("Next: [bold]python scripts/import_lxx.py[/bold]")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
