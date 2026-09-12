"""Project Gutenberg adapter — discover via the Gutendex catalog API, then fetch +
de-boilerplate the plain-text body. Ported from quillnext `src/lib/sources/gutenberg.ts`.

Gutendex is PD by construction, so no per-item license check. Edition ranking floats
a real UTF-8 text body to the top, then popularity (download_count) picks the canonical
edition, then title/author closeness.
"""
from __future__ import annotations

import httpx

from webapp.sources.matching import BROWSER_UA, author_last_name, normalize, score_title_author
from webapp.sources.text_processing import strip_gutenberg_boilerplate

_GUTENDEX = "https://gutendex.com/books"


def _pick_plain_text_url(formats: dict | None) -> str | None:
    """Prefer UTF-8 text/plain, else any text/plain*, excluding readme + .zip."""
    if not formats:
        return None

    def ok(u):
        return bool(u) and "readme" not in u.lower() and not u.lower().endswith(".zip")

    exact = formats.get("text/plain; charset=utf-8")
    if ok(exact):
        return exact
    for k, u in formats.items():
        if k.startswith("text/plain") and ok(u):
            return u
    return None


async def discover(meta: dict) -> dict | None:
    title = (meta or {}).get("title") or ""
    authors = (meta or {}).get("authors") or []
    if not title.strip():
        return None
    # Search by TITLE only: Gutendex's search is accent-sensitive and ANDs all terms, so an
    # ASCII author name ("Bronte") returns nothing against an accented catalog author
    # ("Brontë"). The accent-folding scorer below picks the right author from the results.
    query = title.strip()
    want_title = normalize(title)
    want_author = author_last_name(authors[0]) if authors else None

    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as c:
        r = await c.get(_GUTENDEX, params={"search": query})
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []

    best, best_rank = None, None
    for b in results:
        cand_authors = [a.get("name") for a in (b.get("authors") or [])]
        score = score_title_author(b.get("title"), cand_authors, want_title, want_author)
        if score is None:
            continue
        url = _pick_plain_text_url(b.get("formats") or {})
        if not url:
            continue
        # a real UTF-8 body dominates, then popularity, then title/author closeness
        rank = 1_000_000 + (b.get("download_count") or 0) + score
        if best_rank is None or rank > best_rank:
            best, best_rank = {"source_id": str(b.get("id")), "text_url": url}, rank
    return best


async def fetch(text_url: str) -> str | None:
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as c:
        r = await c.get(text_url)
        if r.status_code != 200:
            return None
        text = r.text
    cleaned = strip_gutenberg_boilerplate(text)
    return cleaned if len(cleaned) > 200 else None
