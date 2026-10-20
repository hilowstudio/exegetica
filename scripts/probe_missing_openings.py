"""Find Gutenberg books whose opening was dropped at import — cheaply.

The old chapter splitter's one way of losing body text was at the START of a book: an opening
chapter with no heading of its own ran together with the title page and was discarded as front
matter (Asimov's "Youth" was stored from Chapter II). Later chapters were never at risk. So to
find the damage we only need the beginning of each Gutenberg page, not the whole work:

  1. a ranged request fetches the first ~150 KB of the book's HTML;
  2. we locate where our stored first chapter's prose begins in it (anchored on words past the
     chapter heading, since headings also appear in the contents list);
  3. we count the words of text before that point. A title page + contents is a few hundred;
     well over that means text was dropped -> the book is a suspect.

Writes .seed_cache/reading_room/opening_probe.json. Suspects are then re-parsed in full by
reparse_suspects (only replaced when the fixed parser finds >=3% more text).

    .venv\\Scripts\\python.exe scripts\\probe_missing_openings.py --limit 50
    .venv\\Scripts\\python.exe scripts\\probe_missing_openings.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import sqlite3
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from webapp.sources.matching import BROWSER_UA  # noqa: E402

_OUT = _ROOT / ".seed_cache" / "reading_room" / "opening_probe.json"
_HEAD_BYTES = 150_000
_NUMBERED = re.compile(r"^\s*(?:chapter|book|part|letter|canto|section|act)?\s*(?:ii|2|second|the second)\b\.?", re.I)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _anchor(con, book_id: int) -> tuple[list[str], str]:
    """~12 prose words from the stored first chapter, past its heading; and that chapter's title."""
    row = con.execute("select title, html from book_chapters where book_id=? order by section_number limit 1",
                      (book_id,)).fetchone()
    if not row:
        return [], ""
    title, html = row
    body = re.sub(r"^\s*<h[1-6]\b[^>]*>.*?</h[1-6]>", " ", html or "", count=1, flags=re.I | re.S)
    toks = _tokens(re.sub(r"<[^>]+>", " ", body))
    start = 8 if len(toks) > 40 else 0
    return toks[start:start + 12], title or ""


async def _head(client, gid: str) -> str | None:
    for url in (f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}-images.html",
                f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.html"):
        try:
            r = await client.get(url, headers={"Range": f"bytes=0-{_HEAD_BYTES}", "Accept-Encoding": "identity"})
        except httpx.HTTPError:
            continue
        if r.status_code in (200, 206) and r.text:
            return r.text
    return None


def _words_before(html: str, anchor: list[str]) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    for el in soup.select('[class*="pg-boilerplate"], [class*="pgheader"], #pg-header, #pg-footer, style, script'):
        el.decompose()
    toks = _tokens((soup.body or soup).get_text(" "))
    n = len(anchor)
    for i in range(len(toks) - n + 1):
        if toks[i:i + n] == anchor:
            return i
    return None                                   # opening not within the first 150 KB


async def _run(args) -> None:
    con = sqlite3.connect(_ROOT / args.db)
    rows = [(bid, slug, title, wc) for (bid, slug, title, wc) in con.execute(
        "select id, slug, title, word_count from books where source='gutenberg'")
        if re.search(r"-pg\d+$", slug or "")]
    if args.limit:
        rows = rows[:args.limit]
    results, start = [], time.monotonic()
    async with httpx.AsyncClient(headers={"User-Agent": BROWSER_UA}, follow_redirects=True,
                                 timeout=httpx.Timeout(30.0)) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def one(row):
            bid, slug, title, wc = row
            gid = re.search(r"-pg(\d+)$", slug).group(1)
            anchor, first_title = _anchor(con, bid)
            numbered = bool(_NUMBERED.match(first_title))
            async with sem:
                html = await _head(client, gid)
            before = _words_before(html, anchor) if (html and len(anchor) >= 6) else None
            return {"slug": slug, "gid": gid, "title": title, "stored_words": wc, "first_chapter": first_title[:60],
                    "starts_at_second": numbered, "words_before_opening": before,
                    "fetched": html is not None}

        tasks = [asyncio.create_task(one(r)) for r in rows]
        for n, fut in enumerate(asyncio.as_completed(tasks), 1):
            results.append(await fut)
            if n % 500 == 0:
                print(f"  {n}/{len(rows)}  ({time.monotonic() - start:.0f}s)", flush=True)
    for r in results:
        b = r["words_before_opening"]
        r["suspect"] = r["starts_at_second"] or (b is not None and b > args.threshold) or (r["fetched"] and b is None)
    _OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    sus = [r for r in results if r["suspect"]]
    print(f"\nprobed {len(results)} books in {time.monotonic() - start:.0f}s -> {len(sus)} suspects "
          f"({sum(r['starts_at_second'] for r in results)} start at a second chapter; "
          f"{sum(1 for r in results if r['fetched'] and r['words_before_opening'] is None)} opening not found in first 150 KB; "
          f"{sum(1 for r in results if not r['fetched'])} not fetched)")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--limit", type=int)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--threshold", type=int, default=1000, help="words of text before the stored opening")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
