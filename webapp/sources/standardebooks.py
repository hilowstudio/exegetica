"""Standard Ebooks bulk adapter — for the in-app e-reader's showcase corpus.

Standard Ebooks (standardebooks.org) hand-typesets public-domain literature into clean
EPUB3 with semantic XHTML. Everything SE produces — markup, metadata, covers — is dedicated
to the public domain under CC0 1.0; the underlying texts are US-public-domain. That makes it
the ideal *readable* corpus (general classic literature: novels, poetry, drama), complementing
the CCEL divinity works, which are grounding-only and never republished.

Two facts shaped this adapter:

  1. The free bulk path is the **GitHub org**, not the site. standardebooks.org's OPDS feed
     and bulk-zip downloads are gated behind a paid Patrons-circle membership (401). The
     GitHub org (github.com/standardebooks) exposes one public repo per book — same content,
     unpaywalled, already unzipped.
  2. Each repo carries the EPUB source under `src/epub/`: `content.opf` (whose <spine> gives
     the exact reading order) and per-file semantic XHTML chapters under `text/`. So chapter
     boundaries and order come for free — no heading-heuristic segmentation needed (unlike the
     Gutenberg path, which leans on text_processing.segment_into_chapters).

Unlike the on-demand registry adapters (gutenberg/ccel: discover→fetch one work by title),
this is a BULK adapter: `list_books()` enumerates the org, `fetch_book(slug)` returns one
book's ordered, cleaned chapters. Driven by scripts/seed_books.py, not the extraction pipeline.
Never raises: a book that fails to parse is skipped by returning None.
"""
from __future__ import annotations

import asyncio
import io
import re
import tarfile
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from webapp.sources.matching import BROWSER_UA

LICENSE = "CC0-1.0"
SOURCE = "standardebooks"

_ORG_REPOS = "https://api.github.com/orgs/standardebooks/repos"
# Branch tarball via codeload — one request per book, and (unlike the REST API) not subject to
# the 60-req/hr unauthenticated limit. Includes images we discard.
_TARBALL = "https://codeload.github.com/standardebooks/{slug}/tar.gz/refs/heads/master"
# Just the metadata file (content.opf, a few KB) via raw — for backfilling genre + sort key onto
# already-seeded books without re-pulling the whole tarball.
_RAW_OPF = "https://raw.githubusercontent.com/standardebooks/{slug}/master/src/epub/content.opf"

# SE book repos are always `author-name_book-title` (an underscore separates author from work);
# the org's infra repos (tools, manual, web, …) never carry one. That single test cleanly
# separates the ~1,500 books from the housekeeping repos without probing each repo's contents.
def _is_book_repo(name: str) -> bool:
    return bool(name) and "_" in name


# Front/back matter that isn't the work's readable body — skipped by file stem (SE names these
# consistently). Prefaces, introductions, forewords, chapters, parts, etc. are all kept.
_SKIP_STEMS = {
    "titlepage", "imprint", "halftitlepage", "halftitle", "colophon", "uncopyright",
    "dedication", "epigraph", "endnotes", "loi", "copyright-page",
}

# Chapter HTML we keep, cleaned to these tags (all attributes dropped → inert, portable markup).
_KEEP_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "em", "i", "b", "strong", "blockquote", "br",
    "hr", "ul", "ol", "li", "span", "cite", "small", "sup", "sub", "abbr", "q", "header",
    "hgroup", "table", "thead", "tbody", "tr", "td", "th", "caption", "figure", "figcaption",
}
_DROP_WHOLE = {"script", "style", "nav", "aside"}  # dropped with their contents


async def list_books(client: httpx.AsyncClient, limit: int | None = None) -> list[str]:
    """Enumerate the org's book repos (slugs), best-effort. ~16 paginated REST calls for the
    full ~1,500 — well under the unauthenticated hourly limit."""
    slugs: list[str] = []
    page = 1
    while True:
        r = await client.get(_ORG_REPOS, params={"per_page": 100, "page": page, "type": "public"})
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        slugs.extend(repo["name"] for repo in batch if _is_book_repo(repo.get("name", "")))
        if limit and len(slugs) >= limit:
            return slugs[:limit]
        if len(batch) < 100:
            break
        page += 1
    return slugs


def _text_of(node) -> str:
    return " ".join((node.get_text(" ", strip=True) if node else "").split())


def _clean_chapter(body) -> tuple[str, str, int]:
    """From a chapter's <body>, return (title, cleaned_html, word_count). Title is the first
    heading's text (for the TOC); the returned HTML keeps its own heading, so the reader shows
    the chapter without a duplicated injected title."""
    for tag in body.find_all(_DROP_WHOLE):
        tag.decompose()
    head = body.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    title = _text_of(head)
    # Unwrap footnote/reference anchors (cross-file targets don't resolve in chapter-at-a-time
    # reading), then normalize every remaining tag to the keep-set with no attributes.
    for a in body.find_all("a"):
        a.unwrap()
    for tag in body.find_all(True):
        if tag.name in _KEEP_TAGS:
            tag.attrs = {}
        else:
            tag.unwrap()
    html = (body.decode_contents() if hasattr(body, "decode_contents") else str(body)).strip()
    words = len(re.sub(r"<[^>]+>", " ", html).split())
    return title, html, words


_RETRY_STATUS = {429, 500, 502, 503, 504}


async def _get_tarball(client: httpx.AsyncClient, slug: str, attempts: int = 3):
    """GET the repo tarball, riding out transient throttling so one bad book never hangs a bulk
    seed. A read-timeout means a slow/huge body → return None (skip; a resume run can retry it)
    rather than re-pulling it. Returns the httpx.Response (200) or None."""
    url = _TARBALL.format(slug=slug)
    for i in range(attempts):
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return r
            if r.status_code not in _RETRY_STATUS:
                return None
        except httpx.ReadTimeout:
            return None
        except httpx.HTTPError:
            pass  # transient connect/network hiccup — back off and retry
        await asyncio.sleep(1.0 * (2 ** i))  # 1s, 2s, 4s
    return None


_NAME_SUFFIX = {"jr", "sr", "ii", "iii", "iv"}


def _sort_key_from_name(name: str) -> str:
    """Best-effort 'Surname, Given' key when SE gives no file-as. SE almost always does, so this
    is a rare fallback. Leaves an already-inverted ('Tennyson, Alfred') or single name as-is."""
    n = (name or "").strip()
    if not n or "," in n:
        return n
    parts = n.split()
    if len(parts) < 2:
        return n
    if parts[-1].lower().strip(".") in _NAME_SUFFIX and len(parts) >= 3:
        return f"{parts[-2]}, {' '.join(parts[:-2] + parts[-1:])}"
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()  # '{ns}meta' -> 'meta'


def _parse_opf(opf_xml: str) -> dict:
    """Pull ordered chapter hrefs + book metadata from content.opf. Parsed with ElementTree
    (stdlib, namespace-aware) — NOT an HTML parser, which drops the text of <meta> (void in
    HTML), and SE keeps the genre shelves + surname-first sort key in <meta property="se:subject">
    / <meta property="file-as">. The <spine> lists itemrefs in reading order; the <manifest> maps
    each id to its href."""
    try:
        root = ET.fromstring(opf_xml)
    except ET.ParseError:
        return {"title": "", "author": "", "author_sort": "", "language": "en",
                "subjects": [], "genres": [], "hrefs": []}
    title, language = "", ""
    creators: list[tuple[str | None, str]] = []
    file_as: dict[str, str] = {}
    genres: list[str] = []
    dc_subjects: list[str] = []
    manifest: dict[str, str] = {}
    spine: list[str] = []
    for el in root.iter():
        ln, txt = _local(el.tag), (el.text or "").strip()
        if ln == "title" and not title:
            title = txt
        elif ln == "creator":
            creators.append((el.get("id"), txt))
        elif ln == "language" and not language:
            language = txt
        elif ln == "subject" and txt:
            dc_subjects.append(txt)
        elif ln == "meta":
            prop = el.get("property")
            if prop in ("schema:genre", "se:subject") and txt:  # current SE uses schema:genre
                genres.append(txt)
            elif prop == "file-as" and txt and el.get("refines"):
                file_as[el.get("refines").lstrip("#")] = txt
        elif ln == "item" and el.get("id") and el.get("href"):
            manifest[el.get("id")] = el.get("href")
        elif ln == "itemref" and el.get("idref"):
            spine.append(el.get("idref"))
    author_names = [t for _cid, t in creators if t]
    author_sort = ""
    if creators:
        cid = creators[0][0]
        author_sort = (file_as.get(cid) if cid else "") or _sort_key_from_name(
            author_names[0] if author_names else "")
    return {
        "title": title,
        "author": ", ".join(author_names),
        "author_sort": author_sort,
        "language": language or "en",
        "subjects": dc_subjects,
        "genres": list(dict.fromkeys(genres)),  # dedupe, preserve order
        "hrefs": [manifest[i] for i in spine if i in manifest and manifest[i].startswith("text/")],
    }


async def fetch_book(client: httpx.AsyncClient, slug: str) -> dict | None:
    """Download one SE repo's tarball and return {slug, title, author, language, subjects,
    word_count, chapters:[{section_number, title, html}]} — or None on any failure."""
    try:
        r = await _get_tarball(client, slug)
        if r is None or not r.content:
            return None
        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tf:
            members = {m.name: m for m in tf.getmembers() if m.isfile()}
            opf_name = next((n for n in members if n.endswith("src/epub/content.opf")), None)
            if not opf_name:
                return None
            base = opf_name[: -len("content.opf")]  # e.g. 'slug-master/src/epub/'
            meta = _parse_opf(tf.extractfile(members[opf_name]).read().decode("utf-8", "replace"))

            chapters: list[dict] = []
            for href in meta["hrefs"]:
                stem = href.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
                if stem in _SKIP_STEMS:
                    continue
                m = members.get(base + href)
                if not m:
                    continue
                xhtml = tf.extractfile(m).read().decode("utf-8", "replace")
                body = BeautifulSoup(xhtml, "html.parser").find("body")
                if not body:
                    continue
                title, html, words = _clean_chapter(body)
                if words < 20:  # a bare divider/section page, not readable prose
                    continue
                chapters.append({"title": title or f"Section {len(chapters) + 1}",
                                 "html": html, "words": words})
    except Exception:  # noqa: BLE001 — never let one malformed book stop a bulk seed
        return None

    if not meta.get("title") or not chapters:
        return None
    for i, ch in enumerate(chapters, 1):
        ch["section_number"] = i
    return {
        "slug": slug,
        "title": meta["title"],
        "author": meta["author"],
        "author_sort": meta["author_sort"],
        "language": meta["language"],
        "subjects": meta["subjects"],
        "genres": meta["genres"],
        "word_count": sum(ch["words"] for ch in chapters),
        "chapters": chapters,
    }


async def fetch_meta(client: httpx.AsyncClient, slug: str) -> dict | None:
    """Fetch ONLY content.opf (raw, a few KB) and return {slug, title, author, author_sort,
    language, subjects, genres} — for backfilling genre/sort onto already-seeded books without
    re-downloading their tarballs. None on failure."""
    url = _RAW_OPF.format(slug=slug)
    for i in range(3):
        try:
            r = await client.get(url)
            if r.status_code == 200 and r.text:
                m = _parse_opf(r.text)
                return {"slug": slug, "title": m["title"], "author": m["author"],
                        "author_sort": m["author_sort"], "language": m["language"],
                        "subjects": m["subjects"], "genres": m["genres"]}
            if r.status_code not in _RETRY_STATUS:
                return None
        except httpx.ReadTimeout:
            return None
        except httpx.HTTPError:
            pass
        await asyncio.sleep(1.0 * (2 ** i))
    return None
