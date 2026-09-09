#!/usr/bin/env python3
"""
Download the six public-domain commentaries (chapter JSON) from HelloAO
(bible.helloao.org): Gill, Matthew Henry, JFB, Adam Clarke, Calvin,
Keil & Delitzsch. Cached to data/commentaries/{id}/{BOOK}/{chapter}.json so
re-runs are fast and import_commentaries.py can work offline.
"""

import asyncio
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from studybible_mcp.parsers.commentaries import COMMENTARIES

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console(legacy_windows=False)

API = "https://bible.helloao.org/api"

# Standard chapter counts per USFM book (Protestant canon).
BOOK_CHAPTERS = {
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34, "JOS": 24, "JDG": 21,
    "RUT": 4, "1SA": 31, "2SA": 24, "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36,
    "EZR": 10, "NEH": 13, "EST": 10, "JOB": 42, "PSA": 150, "PRO": 31, "ECC": 12,
    "SNG": 8, "ISA": 66, "JER": 52, "LAM": 5, "EZK": 48, "DAN": 12, "HOS": 14,
    "JOL": 3, "AMO": 9, "OBA": 1, "JON": 4, "MIC": 7, "NAM": 3, "HAB": 3,
    "ZEP": 3, "HAG": 2, "ZEC": 14, "MAL": 4, "MAT": 28, "MRK": 16, "LUK": 24,
    "JHN": 21, "ACT": 28, "ROM": 16, "1CO": 16, "2CO": 13, "GAL": 6, "EPH": 6,
    "PHP": 4, "COL": 4, "1TH": 5, "2TH": 3, "1TI": 6, "2TI": 4, "TIT": 3,
    "PHM": 1, "HEB": 13, "JAS": 5, "1PE": 5, "2PE": 3, "1JN": 5, "2JN": 1,
    "3JN": 1, "JUD": 1, "REV": 22,
}


async def _fetch(client, sem, url, dest, counters):
    async with sem:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                counters["ok"] += 1
            else:
                counters["miss"] += 1
        except Exception:
            counters["err"] += 1


async def _run(base: Path, force: bool):
    sem = asyncio.Semaphore(12)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=30.0),
                                 follow_redirects=True,
                                 headers={"User-Agent": "studybible-mcp"}) as client:
        for cid in COMMENTARIES:
            books_resp = await client.get(f"{API}/c/{cid}/books.json")
            books = [b["id"] for b in books_resp.json().get("books", [])]
            counters = {"ok": 0, "miss": 0, "err": 0}
            tasks = []
            for book in books:
                for ch in range(1, BOOK_CHAPTERS.get(book, 0) + 1):
                    dest = base / "commentaries" / cid / book / f"{ch}.json"
                    if dest.exists() and not force:
                        continue
                    tasks.append(_fetch(client, sem, f"{API}/c/{cid}/{book}/{ch}.json", dest, counters))
            if tasks:
                await asyncio.gather(*tasks)
            console.print(f"  [green]✓[/green] {cid}: {counters['ok']} fetched "
                          f"({len(books)} books; {counters['miss']} skipped)")


@click.command()
@click.option("--force", "-f", is_flag=True, help="Re-download even if cached")
@click.option("--data-dir", "-d", type=click.Path(), help="Data directory (default: ./data)")
def main(force: bool, data_dir: str | None):
    """Download the six public-domain commentaries from HelloAO."""
    console.print("[bold blue]Study Bible MCP - Commentary Downloader[/bold blue]")
    console.print("Source: HelloAO Free Use Bible API (Public Domain commentaries)\n")
    base = Path(data_dir) if data_dir else (Path(__file__).parent.parent / "data")
    asyncio.run(_run(base, force))
    console.print("\nNext: [bold]python scripts/import_commentaries.py[/bold]")


if __name__ == "__main__":
    main()
