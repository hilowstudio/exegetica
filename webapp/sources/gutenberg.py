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
    two parts. Single-letter index headings ("A.", "B.") don't count, or a back-of-book index
    outvotes the real chapters and the book imports as its index.
    Text before the first heading of the chosen level is dropped as front matter, so a level
    that only starts late (a publisher's catalogue of <h3>s after a novel set in <h2>s) would
    throw the book away: prefer levels whose first heading leaves >=80% of the text after it."""
    html = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
    total = len(re.sub(r"<[^>]+>", "", html)) or 1
    best, lvl = (False, 0.0), None
    for tag in ("h2", "h3", "h4", "h1"):
        # repeated "FOOTNOTES:" / "Contents" headings aren't chapters — counting them splits the
        # book at its notes, and the notes-titled chunks (holding the next chapter) get dropped
        c = sum(1 for h in body.find_all(tag)
                if not re.fullmatch(r"[A-Z]\.?", h.get_text(strip=True)) and not _SKIP_TITLE.match(h.get_text(" ", strip=True)))
        if not 3 <= c <= 400:
            continue
        m = re.search(rf"<{tag}\b", html, re.I)
        cover = len(re.sub(r"<[^>]+>", "", html[m.start():])) / total if m else 0.0
        key = (cover >= 0.8, c if cover >= 0.8 else cover)
        if key > best:
            best, lvl = key, tag
    return lvl


def _raw_chapters(body) -> list:
    """Ordered chapter nodes: prefer <div class='chapter'> (PG's clean convention), else split
    the serialized body at each heading of the chosen level (string split → robust to nesting;
    fragments are re-parsed and cleaned). Returns soup nodes ready for _clean_chapter."""
    # Only trust div.chapter blocks that actually hold text — some PG HTML uses empty
    # <div class="chapter"> as scroll anchors, with the prose in following siblings.
    divs = [d for d in body.find_all("div", class_="chapter") if len(d.get_text(strip=True)) > 40]
    # ...and only when they hold the book: some PG files wrap just each chapter's HEADING in the
    # div and put the prose after it as siblings (Varney the Vampyre, many dime novels), which
    # would keep the headings and drop the text. Then split on headings instead.
    in_divs = sum(len(d.get_text(strip=True)) for d in divs)
    if len(divs) >= 3 and in_divs >= 0.95 * len(body.get_text(strip=True)):   # text outside the divs would be lost
        return divs
    level = _choose_level(body)
    if not level:
        # no heading tags, but chapters marked by plain paragraphs ("<p>CHAPTER IV.</p>"), common
        # in dime-novel transcriptions: promote those paragraphs to headings and split on them
        marks = [p for p in body.find_all("p")
                 if re.match(r"\s*CHAPTER\s+([IVXLC]+|\d+)\b", p.get_text(" ", strip=True), re.I)
                 and len(p.get_text(strip=True)) < 120]
        if len(marks) < 3:
            return [body]  # unstructured → single chapter (a short work, or low-value blob)
        for p in marks:
            p.name = "h3"
        level = "h3"
    html = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
    toks = re.split(rf"(<{level}\b[^>]*>.*?</{level}>)", html, flags=re.I | re.S)
    nodes = []
    # toks[0] is the preamble before the first heading: usually just the title page and contents
    # (dropped), but sometimes a long introduction or the opening stories — keep it then
    if len(re.sub(r"<[^>]+>", " ", toks[0]).split()) > 1000:
        nodes.append(BeautifulSoup(toks[0], "html.parser"))
    i = 1
    while i < len(toks):
        frag = toks[i] + (toks[i + 1] if i + 1 < len(toks) else "")
        nodes.append(BeautifulSoup(frag, "html.parser"))
        i += 2
    return nodes


def _restore_drop_caps(soup) -> None:
    """Pulp transcriptions set each chapter's first letter as an image (<img alt="A">, often in
    a div.figleft) and start the paragraph without it, so dropping images loses the letter
    ("drab gray sheet"). Put the letter back at the start of the next paragraph: with a space
    when the source leaves one ("A drab"), joined when it doesn't ("R" + "ed-hot")."""
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if not re.fullmatch(r"[A-Z]{1,2}", alt):
            continue
        holder = img.parent if img.parent and img.parent.name in ("div", "span") \
            and not img.parent.get_text(strip=True) else img
        para = holder.find_next("p")
        if para is None:
            continue
        first = next((s for s in para.strings if s.strip() or s), None)
        if first is None:
            continue
        rest = str(first)
        spaced = bool(re.match(r"^[\s ]", rest))
        first.replace_with(alt + (" " if spaced else "") + rest.lstrip("  \t\r\n"))
        holder.decompose()


def _split_every_heading(soup, meta: dict) -> list[dict]:
    """Fallback chaptering for books the level-based split mangles: a chapter starts at every
    <h1>–<h4>. Front-matter-titled chunks are dropped only when short (a real contents page),
    so a chunk that merely STARTS with "Contents" but carries the book is kept; a long
    preamble before the first heading is kept too."""
    for el in soup.select('[class*="pg-boilerplate"], [class*="pgheader"], #pg-header, #pg-footer'):
        el.decompose()
    _restore_drop_caps(soup)
    body = soup.body or soup
    html = body.decode_contents()
    toks = re.split(r"(<h[1-4]\b[^>]*>.*?</h[1-4]>)", html, flags=re.I | re.S)
    frags = [toks[0]] + [toks[i] + (toks[i + 1] if i + 1 < len(toks) else "") for i in range(1, len(toks), 2)]
    chapters = []
    for n, frag in enumerate(frags):
        title, chtml, words = _clean_chapter(BeautifulSoup(frag, "html.parser"))
        if words < 30 or (n == 0 and words < 1000):
            continue
        if _SKIP_TITLE.match(title or "") and words < 1500:
            continue
        if not title or _SKIP_TITLE.match(title):
            title = meta.get("title") or "Text"
        chapters.append({"section_number": len(chapters) + 1, "title": title, "html": chtml, "words": words})
    return chapters


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
    _restore_drop_caps(soup)
    body = soup.body or soup
    source_words = len(body.get_text(" ").split())   # whole page, for a caller's coverage check

    chapters, skipped = [], []
    for node in _raw_chapters(body):
        title, chtml, words = _clean_chapter(node)
        if words - len((title or "").split()) < 5:    # a bare heading; a 4-line poem still counts
            continue
        if _SKIP_TITLE.match(title or ""):
            # a long "Contents"/"Transcriber's Note" chunk is the book's text filed under a
            # front-matter heading — keep it under the work's title. Notes stay dropped.
            if words >= 1500 and not re.match(r"\s*(foot|end)notes\b", title, re.I):
                title = meta.get("title") or "Text"
            else:
                skipped.append((words, chtml))
                continue
        elif not title and not chapters:             # a kept preamble with no heading of its own
            title = meta.get("title") or "Text"
        chapters.append({"section_number": len(chapters) + 1, "title": title,
                         "html": chtml, "words": words})
    if not chapters and skipped:
        # a one-block story whose first heading is front matter ("Transcriber's Note"): the
        # block IS the work, so keep it under the work's own title rather than lose it
        words, chtml = max(skipped)
        chapters.append({"section_number": 1, "title": meta.get("title") or "Text", "html": chtml, "words": words})
    if sum(c["words"] for c in chapters) < 0.6 * source_words:
        # The split lost most of the book: headings only in the front matter, or chapters spread
        # across heading levels so the text landed in a dropped "Contents"/"Illustrations" chunk.
        # Re-split at EVERY heading and drop front-matter chunks only when they're short.
        alt = _split_every_heading(BeautifulSoup(r.text, "html.parser"), meta)
        if sum(c["words"] for c in alt) > sum(c["words"] for c in chapters):
            chapters = alt
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
        "source_words": source_words,
    }
