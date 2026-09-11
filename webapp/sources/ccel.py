"""Christian Classics Ethereal Library (ccel.org) adapter — discover via CCEL's
by-author browse index, then fetch the work's plain-text cache export.

CCEL is the most on-mission public-domain source (Fathers → Reformers → Puritans →
creeds). Two quirks shape this adapter:

  1. CCEL's on-site search is JavaScript-rendered — the server HTML returns only a
     fixed featured carousel, identical for every query — so it is useless to a
     server-side fetch. Instead we use the deterministic browse index
     `/index/author/<INITIAL>`, which lists each author followed by their works as
     reader links whose anchor text IS the work title. We scope to the author whose
     heading matches, then score their works' titles with our own matcher.
  2. Every work exposes a clean plain-text export at a predictable path:
     `/ccel/<initial>/<author>/<work>/cache/<work>.txt`.

CCEL editions are US-public-domain works but may carry a copyrighted modern
translation/apparatus (e.g. the Outler Confessions), and CCEL's own terms are
non-commercial. So CCEL is deliberately NOT in extraction._US_CLEAR_SOURCES: its text
grounds the transformative derivatives but is never republished as full_text.
"""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from webapp.sources.matching import BROWSER_UA, author_last_name, normalize
from webapp.sources.text_processing import strip_ccel_boilerplate

_STOP = {"the", "of", "and", "a", "an", "in", "on", "to", "for", "with", "st", "saint", "de"}


def _title_score(cand_title: str, want_title_norm: str) -> int | None:
    """Score a candidate title against the wanted one, already scoped to one author's
    works — so this is looser than the cross-catalog matcher: require every significant
    word of the query to appear in the candidate, then prefer the tightest candidate.
    'the confessions' → {confessions} ⊆ 'confessions of saint augustine' ✓."""
    q = [t for t in want_title_norm.split() if t not in _STOP and len(t) >= 3]
    if not q:
        q = want_title_norm.split()
    cand = set(normalize(cand_title).split())
    if not q or any(t not in cand for t in q):
        return None
    return len(q) * 100 - len(cand)  # all query words present; fewer extra words ranks higher

_AUTHOR_INDEX = "https://www.ccel.org/index/author/{initial}"
# An author heading: /ccel/<slug> or /ccel/<slug>?show=worksBy (no work segment).
_HEADING = re.compile(r"^https?://(?:www\.)?ccel\.org/ccel/([a-z0-9_-]+)(?:\?show=worksBy)?$", re.I)
# A work reader link: /ccel/<author>/<work>, optionally with a repeated leaf.
_WORK = re.compile(r"^https?://(?:www\.)?ccel\.org/ccel/([a-z0-9_-]+)/([a-z0-9_.-]+)(?:/[a-z0-9_.-]+)?/?$", re.I)


def _cache_txt_url(author: str, work: str) -> str:
    return f"https://ccel.org/ccel/{author[0]}/{author}/{work}/cache/{work}.txt"


def _abs(href: str) -> str:
    return href if href.startswith("http") else f"https://www.ccel.org{href}"


async def discover(meta: dict) -> dict | None:
    title = (meta or {}).get("title") or ""
    authors = (meta or {}).get("authors") or []
    want_author = author_last_name(authors[0]) if authors else None
    if not title.strip() or not want_author:
        return None  # CCEL discovery is author-index-keyed; need a surname to scope
    want_title = normalize(title)
    initial = want_author[0].upper()

    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as c:
        r = await c.get(_AUTHOR_INDEX.format(initial=initial))
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

    # Walk anchors in document order: a name-like heading opens an author group; work
    # links until the next name-like heading belong to it. Utility links under an author
    # ("[Author Info]") are heading-shaped too but must NOT close the group, so only a
    # heading whose text is name-like (has a comma or a "(dates)"/"(N classics)") counts.
    in_author = False
    best, best_rank = None, None
    for a in soup.find_all("a", href=True):
        href = _abs(a["href"])
        text = " ".join(a.get_text(" ", strip=True).split())
        if _HEADING.match(href) and text:
            if "," in text or re.search(r"\(\d", text):  # a real author-name heading
                in_author = want_author in normalize(text).split()
            continue  # any heading-shaped link is never a work
        if not in_author:
            continue
        w = _WORK.match(href)
        if not w or "/cache" in href or "?" in href or not text:
            continue
        author_slug, work_slug = w.group(1), w.group(2)
        score = _title_score(text, want_title)
        if score is None:
            continue
        # Prefer a work published under the author's own slug over one nested in an
        # editor's collection (e.g. augustine/confess over schaff/npnf101).
        score += 1 if author_slug == want_author else 0
        if best_rank is None or score > best_rank:
            best = {"source_id": f"{author_slug}/{work_slug}", "text_url": _cache_txt_url(author_slug, work_slug)}
            best_rank = score
    return best


async def fetch(text_url: str) -> str | None:
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as c:
        r = await c.get(text_url)
        if r.status_code != 200 or "text/plain" not in r.headers.get("content-type", ""):
            return None
        text = r.text
    cleaned = strip_ccel_boilerplate(text)
    return cleaned if len(cleaned) > 200 else None
