"""Project Gutenberg adapter — discover via the Gutendex catalog API, then fetch +
de-boilerplate the plain-text body. Ported from quillnext `src/lib/sources/gutenberg.ts`.

Gutendex is PD by construction, so no per-item license check. Edition ranking floats
a real UTF-8 text body to the top, then popularity (download_count) picks the canonical
edition, then title/author closeness.
"""
from __future__ import annotations

import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from webapp.sources.matching import (
    BROWSER_UA,
    author_last_name,
    author_tokens,
    normalize,
    score_title_author,
)
from webapp.sources.standardebooks import _clean_chapter
from webapp.sources.text_processing import strip_gutenberg_boilerplate

_RETRY_STATUS = {429, 500, 502, 503, 504}

# For the bulk e-reader corpus (seed_gutenberg.py). PG hosts US-public-domain texts.
SOURCE = "gutenberg"
LICENSE = "PD-US"


async def _get_with_retry(client: httpx.AsyncClient, url: str, *, params=None, attempts: int = 4):
    """GET that rides out gutendex/gutenberg throttling — a bulk seed fires hundreds of
    requests and free mirrors return 429/5xx transiently. Retries those (and network errors)
    with backoff; returns the httpx.Response (200) or None."""
    for i in range(attempts):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r
            if r.status_code not in _RETRY_STATUS:
                return None
        except Exception:  # noqa: BLE001 — network hiccup; treat as retryable
            if i == attempts - 1:
                return None
        await asyncio.sleep(1.0 * (2 ** i))  # 1s, 2s, 4s
    return None

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
    # A placeholder "author" (Anonymous/Unknown) isn't a surname to match on — Gutenberg
    # files those works under an empty or translator author — so match the distinctive title
    # alone (Beowulf, The Epic of Gilgamesh).
    if want_author in {"anonymous", "unknown", "anon", "various", "anonymous anonymous"}:
        want_author = None
    # Token-overlap author match tolerates pre-modern name shapes ("Augustine of Hippo",
    # "Thomas Aquinas") that a surname-only test misses; None → title-only (placeholders).
    want_tokens = author_tokens(authors[0]) if (authors and want_author) else None

    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as c:
        r = await _get_with_retry(c, _GUTENDEX, params={"search": query})
        if r is None:
            return None
        results = r.json().get("results") or []

    best, best_rank = None, None
    for b in results:
        cand_authors = [a.get("name") for a in (b.get("authors") or [])]
        score = score_title_author(b.get("title"), cand_authors, want_title, want_author,
                                   want_author_tokens=want_tokens)
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
        r = await _get_with_retry(c, text_url)
        if r is None:
            return None
        text = r.text
    cleaned = strip_gutenberg_boilerplate(text)
    return cleaned if len(cleaned) > 200 else None


# --------------------------------------------------------------------------- #
# Bulk e-reader ingest: HTML → beautiful, chaptered copies (seed_gutenberg.py)
# --------------------------------------------------------------------------- #
# PG's HTML lives under several naming schemes depending on the book's vintage/images; try
# them in order. A book with none of these is text/epub-only → skipped (not a beautiful copy).
_HTML_URLS = (
    "https://www.gutenberg.org/ebooks/{gid}.html.images",
    "https://www.gutenberg.org/ebooks/{gid}.html.noimages",
    "https://www.gutenberg.org/cache/epub/{gid}/pg{gid}-images.html",
    "https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.html.utf8",
    "https://www.gutenberg.org/files/{gid}/{gid}-h/{gid}-h.htm",
)

# Chapter titles that are front/back matter, not the readable body — dropped.
_SKIP_TITLE = re.compile(
    r"^\s*(contents|table of contents|title\s*page|half.?title|colophon|cover|copyright|"
    r"the full project gutenberg|project gutenberg|transcriber.?s? note|transcriber|"
    r"list of illustrations|illustrations|list of plates|colou?r plates|plates|"
    r"units of measure|advertisement|by the same author|frontispiece|endnotes|footnotes)\b",
    re.I,
)


def _display_name(pg_author: str) -> tuple[str, str]:
    """PG stores 'Surname, Given' → (display 'Given Surname', sort 'Surname, Given').
    Multi-author strings and comma-less names are left as-is."""
    a = (pg_author or "").strip()
    if "," not in a:
        return a, a
    surname, _, given = a.partition(",")
    return f"{given.strip()} {surname.strip()}".strip(), a


def _slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")


def _choose_level(body) -> str | None:
    """Fallback chaptering: the heading level with the most entries in a sane range — so a
    book that nests chapters (<h3>) under parts (<h2>) splits on the <h3> chapters, not the
    two parts."""
    best, lvl = 0, None
    for tag in ("h2", "h3", "h4", "h1"):
        c = len(body.find_all(tag))
        if 3 <= c <= 400 and c > best:
            best, lvl = c, tag
    return lvl


def _raw_chapters(body) -> list:
    """Ordered chapter nodes: prefer <div class='chapter'> (PG's clean convention), else split
    the serialized body at each heading of the chosen level (string split → robust to nesting;
    fragments are re-parsed and cleaned). Returns soup nodes ready for _clean_chapter."""
    # Only trust div.chapter blocks that actually hold text — some PG HTML uses empty
    # <div class="chapter"> as scroll anchors, with the prose in following siblings.
    divs = [d for d in body.find_all("div", class_="chapter") if len(d.get_text(strip=True)) > 40]
    if len(divs) >= 3:
        return divs
    level = _choose_level(body)
    if not level:
        return [body]  # unstructured → single chapter (a short work, or low-value blob)
    html = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
    toks = re.split(rf"(<{level}\b[^>]*>.*?</{level}>)", html, flags=re.I | re.S)
    nodes = []
    i = 1  # toks[0] is the preamble before the first heading (title page etc.) — dropped
    while i < len(toks):
        frag = toks[i] + (toks[i + 1] if i + 1 < len(toks) else "")
        nodes.append(BeautifulSoup(frag, "html.parser"))
        i += 2
    return nodes


async def fetch_book(client: httpx.AsyncClient, gid, meta: dict) -> dict | None:
    """One Gutenberg work → the e-reader book dict (same shape as standardebooks.fetch_book).
    Title/author/genre come from the curated manifest `meta`; the HTML supplies clean chapters."""
    r = None
    for tmpl in _HTML_URLS:
        r = await _get_with_retry(client, tmpl.format(gid=gid))
        if r is not None:
            break
    if r is None:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for el in soup.select('[class*="pg-boilerplate"], [class*="pgheader"], #pg-header, #pg-footer'):
        el.decompose()
    body = soup.body or soup

    chapters = []
    for node in _raw_chapters(body):
        title, chtml, words = _clean_chapter(node)
        if words < 30 or _SKIP_TITLE.match(title or ""):
            continue
        chapters.append({"section_number": len(chapters) + 1, "title": title,
                         "html": chtml, "words": words})
    if not chapters:
        return None

    display, sort = _display_name(meta.get("author") or "")
    title = meta.get("title") or ""
    genre = meta.get("genre")
    subjects = [s.strip() for s in (meta.get("subjects") or "").split("|") if s.strip()]
    return {
        "slug": (f"{_slugify(display)}_{_slugify(title)}"[:78] or "book") + f"-pg{gid}",
        "title": title,
        "author": display,
        "author_sort": sort,
        "language": "en",
        "subjects": subjects,
        "genres": [genre] if genre else [],
        "chapters": chapters,
        "word_count": sum(c["words"] for c in chapters),
    }
