"""In-app e-reader — serving layer.

Reads the curated public-domain corpus from books.db (a static SQLite distributed via R2 to
the Fly volume, like study_bible.db / theology.db — see scripts/seed_books.py + publish_db.py),
and persists each signed-in reader's per-book position in Neon (reading_state). Books are
public-domain, so reading needs no login; only saving your place does (anonymous readers keep
position client-side).

SQLite is opened read-only per query and run in a threadpool, so the async event loop never
blocks on disk. The webapp otherwise reaches SQLite only through the MCP, so this is its own
small helper rather than a shared one.
"""
from __future__ import annotations

import asyncio
import html as _html
import io
import json
import logging
import os
import pathlib
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from webapp import auth, db, shell, typeset

logger = logging.getLogger("study-bible-web.reader")

_DEFAULT_DB = pathlib.Path(__file__).resolve().parent.parent / "db" / "books.db"
_DEFAULT_COVERS = pathlib.Path(__file__).resolve().parent.parent / "db" / "covers.db"


def _db_path() -> str:
    return os.environ.get("BOOKS_DB") or str(_DEFAULT_DB)


def available() -> bool:
    return os.path.exists(_db_path())


def _covers_path() -> str:
    return os.environ.get("COVERS_DB") or str(_DEFAULT_COVERS)


_COVER_MAXW = 400
_COVER_UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (admin cover import; hello@hilowstudio.dev)"}


def _url_to_webp(url: str, cap: int = 15 * 1024 * 1024):
    """Download an image URL (size-capped) and return resized WebP bytes, or None on failure.
    Same treatment as the bulk builder: max width 400px, quality 80 — so huge sources shrink."""
    try:
        from PIL import Image  # lazy: reader stays importable without Pillow (e.g. scripts)
        req = urllib.request.Request(url, headers=_COVER_UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read(cap + 1)
        if len(data) > cap:
            return None
        im = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = im.size
        if w < 40 or h < 40:
            return None
        if w > _COVER_MAXW:
            im = im.resize((_COVER_MAXW, round(h * _COVER_MAXW / w)))
        out = io.BytesIO()
        im.save(out, "WEBP", quality=80, method=6)
        return out.getvalue()
    except Exception:
        return None


def _cover_blob_sync(slug: str):
    """The self-hosted WebP cover bytes for a book, from the R2-distributed covers.db."""
    if not os.path.exists(_covers_path()):
        return None
    con = sqlite3.connect(f"file:{_covers_path()}?mode=ro", uri=True)
    try:
        r = con.execute("select webp from covers where slug=?", (slug,)).fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


# ---- school-only books (2026-11-09) ----
# Copies Yorkville Christian provides for its own accounts (in copyright; scripts/ingest_school_copy.py) carry
# access='school' in books.db. They are listed and opened only for a signed-in school account, a teacher or an
# admin; everyone else never sees them, and asking for one by its address answers "not found".
SCHOOL = "school"


def may_read_school(user) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").lower()
    return email.endswith("@" + auth.SCHOOL_DOMAIN) or auth.is_teacher(user) or auth.is_admin(user)


REFERENCE = "reference"   # a school textbook or curriculum: for the Prep Room, never on a Reading Room shelf


def reader_level(user) -> int:
    """0 the public, 1 a school account (reads school copies), 2 a teacher or admin (also finds reference copies)."""
    if not user:
        return 0
    if auth.is_teacher(user) or auth.is_admin(user):
        return 2
    return 1 if may_read_school(user) else 0


def _visible(con, school: int, shelf: bool = False) -> str:
    """The SQL condition for the books this reader may see (books.db from before 2026-11-09 has no access column).
    `school` is the reader's level (a bool still works: True is a school reader). Reference copies (textbooks the
    Prep Room drafts from) are never shelved; a teacher finds them by search."""
    if "access" not in {c[1] for c in con.execute("pragma table_info(books)")}:
        return "1=1"
    level = int(school)
    hidden = []
    if level < 1:
        hidden.append(SCHOOL)
    if level < 2 or shelf:
        hidden.append(REFERENCE)
    if not hidden:
        return "1=1"
    return "coalesce(access, '') not in (" + ", ".join(f"'{h}'" for h in hidden) + ")"


def is_reference(slug: str) -> bool:
    """A school textbook or teacher's edition: on a class shelf it is for the class's teachers alone (decision 0029)."""
    if not slug or not available():
        return False
    con = _connect()
    try:
        if "access" not in {c[1] for c in con.execute("pragma table_info(books)")}:
            return False
        row = con.execute("select access from books where slug=?", (slug,)).fetchone()
        return bool(row) and row[0] == REFERENCE
    finally:
        con.close()


def _closed_to(con, slug: str, school: int) -> bool:
    if "access" not in {c[1] for c in con.execute("pragma table_info(books)")}:
        return False
    r = con.execute("select access from books where slug=?", (slug,)).fetchone()
    if not r:
        return False
    need = {SCHOOL: 1, REFERENCE: 2}.get(r[0], 0)
    return int(school) < need


def _safe_int(v, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---- SQLite reads (sync; wrapped in run_in_threadpool by the handlers) ----

def _list_sync(q: str | None, limit: int, offset: int, school: bool = False) -> dict:
    con = _connect()
    try:
        where, params = f"where {_visible(con, school)}", []
        if q:
            where += " and (title like ? or author like ?)"
            params = [f"%{q}%", f"%{q}%"]
        total = con.execute(f"select count(*) from books {where}", params).fetchone()[0]
        rows = con.execute(
            f"""select slug, title, author, author_sort, genres, language, chapter_count, word_count
                from books {where} order by author_sort collate nocase, title limit ? offset ?""",
            [*params, limit, offset],
        ).fetchall()
        items = []
        for r in rows:
            d = dict(r)
            d["genres"] = json.loads(d.get("genres") or "[]")
            items.append(d)
        return {"total": total, "items": items}
    finally:
        con.close()


_GENRE_FALLBACK = "Other"


def _shelves_sync(school: bool = False) -> list[dict]:
    """The whole corpus shelved like a library: one shelf per genre (a book appears under each of
    its genres), each shelf sorted by the surname-first sort key. Shelves ordered alphabetically."""
    con = _connect()
    try:
        rows = con.execute(
            "select slug, title, author, author_sort, genres, chapter_count, word_count from books "
            f"where {_visible(con, school, shelf=True)}"
        ).fetchall()
    finally:
        con.close()
    shelves: dict[str, list] = {}
    for r in rows:
        b = {"slug": r["slug"], "title": r["title"], "author": r["author"],
             "author_sort": r["author_sort"] or r["author"] or r["title"],
             "chapter_count": r["chapter_count"], "word_count": r["word_count"]}
        for g in (json.loads(r["genres"] or "[]") or [_GENRE_FALLBACK]):
            shelves.setdefault(g, []).append(b)
    for books in shelves.values():
        books.sort(key=lambda x: (x["author_sort"].lower(), x["title"].lower()))
    ordered = [{"genre": g, "count": len(shelves[g]), "books": shelves[g]}
               for g in sorted(shelves, key=str.lower)]
    return {"shelves": ordered, "total": len(rows)}


def _catalog_sync(school: bool = False) -> dict:
    """The whole corpus as one flat list (no per-genre duplication), for the client-side
    faceted browse: search, filter by section/length/source, and sort happen in the browser."""
    con = _connect()
    try:
        cols = {c[1] for c in con.execute("pragma table_info(books)")}
        cover = "cover_url" if "cover_url" in cols else "null as cover_url"
        access = "access" if "access" in cols else "null as access"
        rows = con.execute(
            f"""select slug, title, author, author_sort, genres, source, chapter_count, word_count, {cover}, {access}
                from books where {_visible(con, school, shelf=True)} order by author_sort collate nocase, title"""
        ).fetchall()
    finally:
        con.close()
    items = [_item(r) for r in rows]
    return {"items": items, "total": len(items)}


def _item(r) -> dict:
    """One book as the catalog and the shelves describe it, enough to draw its house cover."""
    return {
        "slug": r["slug"], "title": r["title"], "author": r["author"] or "",
        "author_sort": r["author_sort"] or r["author"] or r["title"],
        "sections": json.loads(r["genres"] or "[]"), "source": r["source"],
        "chapters": r["chapter_count"], "words": r["word_count"] or 0,
        "cover": r["cover_url"], **({"school": True} if r["access"] == SCHOOL else {}),
        **({"reference": True} if r["access"] == REFERENCE else {}),
    }


def items_sync(slugs: list[str], school: int) -> dict[str, dict]:
    """Catalog entries for these books, by slug, for the Living Library's shelves (decision 0029). A book this
    reader may not open is left out. Unlike the catalog's shelves, a teacher keeps a reference copy here: on a
    class shelf it is that class's textbook."""
    slugs = [s for s in dict.fromkeys(slugs) if s]
    if not slugs or not available():
        return {}
    con = _connect()
    try:
        cols = {c[1] for c in con.execute("pragma table_info(books)")}
        cover = "cover_url" if "cover_url" in cols else "null as cover_url"
        access = "access" if "access" in cols else "null as access"
        rows = con.execute(
            f"""select slug, title, author, author_sort, genres, source, chapter_count, word_count, {cover}, {access}
                from books where slug in ({",".join("?" * len(slugs))}) and {_visible(con, school)}""", slugs
        ).fetchall()
    finally:
        con.close()
    return {r["slug"]: _item(r) for r in rows}


async def apply_overrides(items) -> None:
    """The library admin's cover replacements (Neon), over the covers baked into books.db."""
    if not db.ready():
        return
    try:
        rows = await db.fetch(
            "select book_slug, cover_url, (webp is not null) as has_webp, "
            "extract(epoch from updated_at)::bigint as v from cover_overrides")
    except Exception:
        return
    ov = {r["book_slug"]: r for r in rows}
    for it in items:
        r = ov.get(it["slug"])
        if r:   # self-hosted override -> versioned local path; legacy url-only -> the URL
            it["cover"] = ("/api/cover/" + it["slug"] + "?v=" + str(r["v"])) if r["has_webp"] else r["cover_url"]


def _cover_of(slug: str) -> str | None:
    """The book's original (baked-in) cover URL from books.db — used to revert an override."""
    con = _connect()
    try:
        if "cover_url" not in {c[1] for c in con.execute("pragma table_info(books)")}:
            return None
        r = con.execute("select cover_url from books where slug=?", (slug,)).fetchone()
        return r["cover_url"] if r else None
    finally:
        con.close()


def _book_sync(slug: str, school: bool = False) -> dict | None:
    con = _connect()
    try:
        if _closed_to(con, slug, school):
            return None
        b = con.execute(
            """select id, slug, title, author, author_sort, genres, language, subjects,
                      chapter_count, word_count, front_html, source, license from books where slug=?""",
            (slug,),
        ).fetchone()
        if not b:
            return None
        toc = con.execute(
            "select section_number, title, words, substr(html, 1, case when section_number = 1 then 30000 else 700 end) as head "
            "from book_chapters where book_id=? order by section_number",
            (b["id"],),
        ).fetchall()
        d = {k: b[k] for k in b.keys() if k != "id"}
        d["subjects"] = json.loads(d["subjects"] or "[]")
        d["genres"] = json.loads(d.get("genres") or "[]")
        d["toc"] = [dict(t) for t in toc]
        baked = {}
        try:                                                  # a baked edition carries its own contents names
            baked = {r["section_number"]: r for r in con.execute(
                "select section_number, label, name from edition_chapters where book_id=?", (b["id"],))}
        except sqlite3.OperationalError:
            pass
        for t in d["toc"]:                                    # contents-page label + name, in house style
            head = t.pop("head") or ""
            if t["section_number"] in baked:
                t["label"], t["name"] = baked[t["section_number"]]["label"] or "", baked[t["section_number"]]["name"] or ""
            else:
                t["label"], t["name"] = typeset.toc_entry(t["title"], head, t["section_number"] == 1)
            t["name"], t["syn"] = typeset.synopsis(t["name"])
        return d
    finally:
        con.close()


def _edition_row(con, book_id: int, n: int):
    try:
        return con.execute("select html, label, name from edition_chapters where book_id=? and section_number=?",
                           (book_id, n)).fetchone()
    except sqlite3.OperationalError:                          # a books.db from before baked editions
        return None


def _chapter_sync(slug: str, n: int, school: bool = False) -> dict | None:
    con = _connect()
    try:
        if _closed_to(con, slug, school):
            return None
        b = con.execute("select id, slug, title, chapter_count from books where slug=?", (slug,)).fetchone()
        if not b:
            return None
        ch = con.execute(
            "select section_number, title, html, words from book_chapters where book_id=? and section_number=?",
            (b["id"], n),
        ).fetchone()
        if not ch:
            return None
        ed = _edition_row(con, b["id"], n)
        if ed:                                                # a baked edition is served exactly as stored
            body = {"html": ed["html"], "label": ed["label"] or "", "name": ed["name"] or ""}
        else:                                                 # not yet baked: the live typesetting pass
            body = dict(zip(("html", "label", "name"),
                            typeset.typeset(ch["html"], ch["title"], n == 1, n == b["chapter_count"] and n > 1)))
        return {
            "book_slug": b["slug"], "book_title": b["title"], "chapter_count": b["chapter_count"],
            "section_number": ch["section_number"], "title": ch["title"], **body,
            "has_prev": n > 1, "has_next": n < b["chapter_count"],
        }
    finally:
        con.close()


def _html_to_text(h: str) -> str:
    """Chapter HTML → readable plaintext for the generator's prompt (block tags become
    paragraph breaks, everything else is stripped, entities unescaped)."""
    s = re.sub(r"(?is)</(p|h[1-6]|li|blockquote|div|tr|figcaption)>", "\n\n", h or "")
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _gen_book_sync(slug: str) -> dict | None:
    """A whole book as plaintext chapters, for the Prep Room's drafting (reads books.db). Reached only through
    teacher-only routes and server jobs, so school-only copies are readable here; a teacher may draft from them.
    A teacher's private uploads are not served here; they stay in the Living Library's vault."""
    con = _connect()
    try:
        b = con.execute(
            "select id, slug, title, author, chapter_count, word_count from books where slug=?",
            (slug,),
        ).fetchone()
        if not b:
            return None
        rows = con.execute(
            "select section_number, title, html, words from book_chapters where book_id=? order by section_number",
            (b["id"],),
        ).fetchall()
        return {
            "slug": b["slug"], "title": b["title"], "author": b["author"],
            "chapter_count": b["chapter_count"], "word_count": b["word_count"],
            "chapters": [{"n": r["section_number"], "title": r["title"],
                          "text": _html_to_text(r["html"]), "words": r["words"]} for r in rows],
        }
    finally:
        con.close()


# ---- handlers ----

async def reader_page(request):
    """One SPA for both the browse grid (/read) and a single book (/read/{slug})."""
    return shell.page(request, "reader.html")


async def books_list(request):
    if not available():
        return JSONResponse({"items": [], "total": 0, "available": False})
    q = (request.query_params.get("q") or "").strip() or None
    limit = min(_safe_int(request.query_params.get("limit"), 60), 200)
    offset = max(_safe_int(request.query_params.get("offset"), 0), 0)
    data = await run_in_threadpool(_list_sync, q, limit, offset, reader_level(auth.current_user(request)))
    data["available"] = True
    return JSONResponse(data)


async def shelves(request):
    """The whole corpus shelved by genre (a book under each of its genres), each shelf
    alphabetical by author surname — the browse default."""
    if not available():
        return JSONResponse({"shelves": [], "total": 0, "available": False})
    data = await run_in_threadpool(_shelves_sync, reader_level(auth.current_user(request)))
    data["available"] = True
    return JSONResponse(data)


async def catalog(request):
    """The whole corpus as one flat list — powers the search-first faceted browse.
    Library-admin cover overrides (Neon) are merged on top of the baked-in cover URLs."""
    if not available():
        return JSONResponse({"items": [], "total": 0, "available": False})
    data = await run_in_threadpool(_catalog_sync, reader_level(auth.current_user(request)))
    await apply_overrides(data["items"])
    data["available"] = True
    data["admin"] = auth.is_admin(auth.current_user(request))
    return JSONResponse(data)


async def cover_image(request):
    """Serve a self-hosted WebP cover. A `?v=` (versioned) request is an admin override —
    served from Neon; otherwise it's a baked-in cover from covers.db. Both long-cache: the
    override URL's ?v changes whenever the admin replaces it, so immutable is safe."""
    slug = request.path_params["slug"]
    hdr = {"Cache-Control": "public, max-age=31536000, immutable"}
    if request.query_params.get("v") and db.ready():   # versioned → an admin override in Neon
        try:
            row = await db.fetchrow("select webp from cover_overrides where book_slug=$1", slug)
        except Exception:
            row = None
        if row and row["webp"]:
            return Response(bytes(row["webp"]), media_type="image/webp", headers=hdr)
    blob = await run_in_threadpool(_cover_blob_sync, slug)   # baked-in covers.db (no Neon hit)
    if not blob:
        return JSONResponse({"error": "not found"}, status_code=404)
    return Response(blob, media_type="image/webp", headers=hdr)


async def book_detail(request):
    if not available():
        return JSONResponse({"error": "unavailable"}, status_code=503)
    d = await run_in_threadpool(_book_sync, request.path_params["slug"], reader_level(auth.current_user(request)))
    return JSONResponse(d) if d else JSONResponse({"error": "not found"}, status_code=404)


async def book_chapter(request):
    if not available():
        return JSONResponse({"error": "unavailable"}, status_code=503)
    n = _safe_int(request.path_params.get("n"), 1)
    d = await run_in_threadpool(_chapter_sync, request.path_params["slug"], n,
                                reader_level(auth.current_user(request)))
    return JSONResponse(d) if d else JSONResponse({"error": "not found"}, status_code=404)


async def position_get(request):
    """All of this reader's saved positions, {slug: section_number}. Anonymous → empty
    (the client falls back to localStorage)."""
    user = auth.current_user(request)
    if not user or not db.ready():
        return JSONResponse({"positions": {}})
    rows = await db.fetch(
        "select book_slug, section_number, pages, extract(epoch from updated_at)::bigint as at "
        "from reading_state where user_id=$1", uuid.UUID(user["id"])
    )
    return JSONResponse({
        "positions": {r["book_slug"]: r["section_number"] for r in rows},   # chapter, for the reader to resume
        "progress": {r["book_slug"]: r["pages"] for r in rows},             # furthest page reached, for "Continue Reading"
        "updated": {r["book_slug"]: r["at"] for r in rows},                 # last read, so the newest leads the row
    })


async def position_put(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    if not db.ready():
        return JSONResponse({"ok": False}, status_code=503)
    body = await request.json()
    slug = (body.get("slug") or "").strip()
    if not slug:
        return JSONResponse({"ok": False}, status_code=400)
    await db.execute(
        """insert into reading_state(user_id, book_slug, section_number, pages, updated_at)
           values($1, $2, $3, $4, now())
           on conflict (user_id, book_slug)
           do update set section_number=excluded.section_number,
             pages=greatest(reading_state.pages, excluded.pages), updated_at=now()""",
        uuid.UUID(user["id"]), slug, _safe_int(body.get("section_number"), 1), _safe_int(body.get("pages"), 1),
    )
    return JSONResponse({"ok": True})


def _cover_book_sync(slug: str) -> dict | None:
    con = _connect()
    try:
        r = con.execute("select title, author, author_sort from books where slug=?", (slug,)).fetchone()
    finally:
        con.close()
    return dict(r) if r else None


def _cover_query(book: dict) -> str:
    """The admin cover-search query for a book: plain words, no operators. The full title,
    the full author name, then "book cover"."""
    return " ".join(p.strip() for p in (book["title"], book["author"], "book cover") if p and p.strip())


# ---- CoverBrowser (coverbrowser.com): matching covers shown above the Google results.
# Its robots.txt disallows /search, so we never query it directly. Google indexes its
# collection pages; we find candidates with a site: image search, then open those pages
# (allowed) and keep only the covers whose alt text names this book. A collection page
# holds dozens of covers, and Google returns its neighbours too, so the check matters.
_CB_HOST = "www.coverbrowser.com"
_CB_PAGES_MAX = 5
_CB_ALTS: dict[str, dict[str, str]] = {}      # collection page URL -> {image path: alt}
_CB_NOT_BOOKS = re.compile(r"\b(movies?|dvds?|blu-?ray|video|music|albums?|cds?|games?|vinyl)\b|\[", re.I)


def _cb_norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def _main_title(title: str) -> str:
    """"Les Misérables, Volume 2: Cosette" -> "Les Misérables" (series sets drop subtitles)."""
    t = re.split(r":|;", title or "")[0]
    return re.sub(r",?\s+(volume|vol\.?|part|book)\s+\w+\s*$", "", t, flags=re.I).strip()


def _cb_page_alts(link: str) -> dict[str, str]:
    if link in _CB_ALTS:
        return _CB_ALTS[link]
    req = urllib.request.Request(link, headers=_COVER_UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        page = r.read(4 * 1024 * 1024).decode("utf-8", "replace")
    alts = {}
    for tag in re.findall(r"<img\b[^>]*>", page):
        src, alt = re.search(r'\bsrc="([^"]+)"', tag), re.search(r'\balt="([^"]*)"', tag)
        if src and alt and "/image/" in src.group(1):
            alts[src.group(1).split("/image/", 1)[1]] = _html.unescape(alt.group(1))
    if len(_CB_ALTS) > 500:
        _CB_ALTS.clear()
    _CB_ALTS[link] = alts
    return alts


def _cb_matches(alt: str, book: dict) -> bool:
    """Alt text reads "Collection - Title (Series) by Author". The book's main title (minus a
    leading article) must appear in it, and if the alt names an author, so must our surname."""
    collection, _, text = alt.partition(" - ") if " - " in alt else ("", "", alt)
    if _CB_NOT_BOOKS.search(collection + " " + text):
        return False
    t = _cb_norm(re.sub(r"^(the|a|an)\s+", "", _main_title(book["title"]), flags=re.I))
    if not t or f" {t} " not in f" {_cb_norm(text)} ":
        return False
    surname = (book.get("author_sort") or "").split(",")[0] or " ".join((book.get("author") or "").split()[-1:])
    if " by " in text.lower() and surname and _cb_norm(surname) not in _cb_norm(text):
        return False
    return True


def _cb_query(book: dict) -> str:
    return " ".join(p for p in (_main_title(book["title"]), book.get("author") or "") if p)


def _cb_from_pages(book: dict, links: list[str], dims: dict | None = None) -> list[dict]:
    """Open the candidate CoverBrowser collection pages and keep every cover whose alt text
    names this book. `dims` optionally maps an image path to (width, height) from the search."""
    links = [l for l in dict.fromkeys(links) if urllib.parse.urlparse(l).hostname == _CB_HOST][:_CB_PAGES_MAX]
    with ThreadPoolExecutor(4) as ex:
        futs = {link: ex.submit(_cb_page_alts, link) for link in links}
    out, seen = [], set()
    for link, f in futs.items():
        if f.exception() is not None:
            continue
        for path, alt in f.result().items():
            if path in seen or not _cb_matches(alt, book):
                continue
            seen.add(path)
            w, h = (dims or {}).get(path, (None, None))
            img = "https://www.coverbrowser.com/image/" + path
            out.append({"image": img, "thumb": img, "w": w, "h": h, "title": alt,
                        "domain": alt.split(" - ", 1)[0] if " - " in alt else "coverbrowser.com", "page": link})
    return out


def _coverbrowser_sync(book: dict, key: str) -> list[dict]:
    """Candidate pages via a Google image search limited to coverbrowser.com (Serper)."""
    hits = [h for h in _serper_page(_cb_query(book) + " site:coverbrowser.com", key, 1)
            if "/image/" in (h.get("imageUrl") or "")]
    dims = {h["imageUrl"].split("/image/", 1)[1]: (h.get("imageWidth"), h.get("imageHeight")) for h in hits}
    return _cb_from_pages(book, [h.get("link") or "" for h in hits], dims)


# ---- Tavily: the fallback web search when Serper is unavailable (no key, out of credits,
# or down). Its search returns about 5 images per query, so we run a few phrasings at once.
_TAVILY_PHRASINGS = ("book cover", "vintage paperback cover")   # ~5 images each -> ~10


def _tavily(body: dict, key: str) -> dict:
    req = urllib.request.Request("https://api.tavily.com/search", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Tavily {e.code}: {e.read()[:200].decode('utf-8', 'replace')}") from None


def _tavily_images_sync(book: dict, key: str) -> list[dict]:
    base = " ".join(p.strip() for p in (book["title"], book["author"]) if p and p.strip())
    with ThreadPoolExecutor(len(_TAVILY_PHRASINGS)) as ex:
        futs = [ex.submit(_tavily, {"query": f"{base} {ph}", "include_images": True,
                                    "include_image_descriptions": True, "max_results": 5}, key)
                for ph in _TAVILY_PHRASINGS]
    if all(f.exception() for f in futs):
        raise futs[0].exception()
    out, seen = [], set()
    for f in futs:
        if f.exception():
            continue
        for it in f.result().get("images") or []:
            it = it if isinstance(it, dict) else {"url": it}
            img = it.get("url") or ""
            if not re.match(r"^https?://", img, re.I) or img in seen:
                continue
            seen.add(img)
            out.append({"image": img, "thumb": img, "w": None, "h": None,
                        "title": it.get("title") or it.get("description") or "",
                        "domain": (urllib.parse.urlparse(img).hostname or "").removeprefix("www."), "page": ""})
    return out


def _coverbrowser_tavily_sync(book: dict, key: str) -> list[dict]:
    """Candidate CoverBrowser pages via a Tavily search limited to that site."""
    d = _tavily({"query": _cb_query(book), "include_domains": ["coverbrowser.com"], "max_results": 10}, key)
    return _cb_from_pages(book, [r.get("url") or "" for r in d.get("results") or []])


_SERPER_PAGES = 1   # 10 images a page (free accounts can't raise "num"); one credit per page
_WEB_RESULTS = 10


def _serper_page(q: str, key: str, page: int) -> list[dict]:
    req = urllib.request.Request(
        "https://google.serper.dev/images", data=json.dumps({"q": q, "page": page}).encode(),
        headers={"X-API-KEY": key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("images") or []
    except urllib.error.HTTPError as e:   # surface Serper's own reason, e.g. "Not enough credits"
        try:
            msg = json.loads(e.read()).get("message") or ""
        except Exception:
            msg = ""
        raise RuntimeError(f"Serper {e.code}: {msg}") from None


def _search_error(exc: Exception) -> str:
    logger.warning("cover search failed: %s", exc)
    msg = str(exc).lower()
    # Serper says "Not enough credits"; Tavily uses 432 (plan limit) and 433 (pay-as-you-go limit)
    return "no-credits" if ("credit" in msg or msg.startswith(("tavily 432", "tavily 433"))) else "search-failed"


# ---- Web image search providers, tried in order: Serper, a second Serper key, then Tavily.
# A key that reports it's out of credits is skipped for an hour, so each click doesn't spend
# a failed request on it before falling through. A top-up is picked up after the hour.
_PROVIDER_KEYS = (("serper", "SERPER_API_KEY"), ("serper", "SERPER_API_KEY_2"), ("tavily", "TAVILY_API_KEY"))
_EXHAUSTED_FOR = 3600
_exhausted: dict[str, float] = {}


def _web_providers() -> list[tuple[str, str, str]]:
    out = []
    for kind, env in _PROVIDER_KEYS:
        key = (os.environ.get(env) or "").strip().strip('"').strip("'")
        if key and time.time() - _exhausted.get(env, 0) > _EXHAUSTED_FOR:
            out.append((kind, env, key))
    return out


def _serper_images_sync(q: str, key: str) -> list[dict]:
    """Google Images results via Serper.dev (Google's own Custom Search API is closed to new
    customers, and scraping Google from the server gets blocked). Pages are fetched in
    parallel; a later page failing still returns the first."""
    with ThreadPoolExecutor(_SERPER_PAGES) as ex:
        futs = [ex.submit(_serper_page, q, key, p) for p in range(1, _SERPER_PAGES + 1)]
    images = futs[0].result()                       # page 1 failing is a real failure
    for f in futs[1:]:
        if f.exception() is None:
            images += f.result()
    out, seen = [], set()
    for it in images:
        img = it.get("imageUrl") or ""
        if not re.match(r"^https?://", img, re.I) or img in seen:
            continue
        seen.add(img)
        out.append({"image": img, "thumb": it.get("thumbnailUrl") or img,
                    "w": it.get("imageWidth"), "h": it.get("imageHeight"),
                    "title": it.get("title") or "", "domain": it.get("domain") or it.get("source") or "",
                    "page": it.get("link") or ""})
    return out


# ---- Original magazine issue: most of our SF is Gutenberg stories whose transcriber note names
# the issue they came from. scripts/build_magazine_covers.py matches those to scans of the
# issue's cover (Internet Archive, Galactic Central) and writes this index.
_MAG_INDEX = pathlib.Path(__file__).resolve().parent / "data" / "magazine_covers.json"
_mag_cache: dict | None = None


def _mag_covers() -> dict:
    global _mag_cache
    if _mag_cache is None:
        try:
            _mag_cache = json.loads(_MAG_INDEX.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _mag_cache = {}
    return _mag_cache


_PREVIEW_HOSTS = {"www.philsp.com"}    # http-only sources the browser can't load on our https pages
_preview_cache: dict[str, bytes] = {}


def _preview_url(url: str) -> str:
    host = urllib.parse.urlparse(url).hostname
    return ("/api/reading/cover/preview?u=" + urllib.parse.quote(url, safe="")) if host in _PREVIEW_HOSTS else url


async def cover_preview(request):
    """Library admins: a small WebP preview of an image from an http-only source (Galactic
    Central), fetched by the server. Allow-listed hosts only, so it's not an open proxy."""
    if not auth.is_admin(auth.current_user(request)):
        return Response(status_code=403)
    url = request.query_params.get("u") or ""
    if urllib.parse.urlparse(url).hostname not in _PREVIEW_HOSTS:
        return Response(status_code=400)
    data = _preview_cache.get(url)
    if data is None:
        data = await run_in_threadpool(_url_to_webp, url)
        if not data:
            return Response(status_code=404)
        if len(_preview_cache) > 400:
            _preview_cache.clear()
        _preview_cache[url] = data
    return Response(data, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


def _mag_results(slug: str) -> dict | None:
    rec = _mag_covers().get(slug)
    if not rec:
        return None
    return {"issue": rec["issue"], "results": [
        {"image": c["image"], "thumb": _preview_url(c["thumb"]), "w": None, "h": None, "title": rec["issue"],
         "domain": c["source"], "page": c["page"], "source": f'{rec["issue"]} ({c["source"]})'}
        for c in rec["candidates"]]}


# ---- PulpCovers (pulpcovers.com): high-resolution vintage pulp and paperback scans. The site
# sits behind Cloudflare, but it's Jetpack-connected, so WordPress.com's public API searches it
# with no key. Many hits are unrelated (the search matches post text), so we keep only posts
# whose title contains the book's title, and only portrait images big enough to use.
_PULPCOVERS_SITE = 47630909


def _pulpcovers_sync(book: dict) -> list[dict]:
    title = _main_title(book["title"])
    want = _cb_norm(re.sub(r"^(the|a|an)\s+", "", title, flags=re.I))
    if not want:
        return []
    url = (f"https://public-api.wordpress.com/rest/v1.1/sites/{_PULPCOVERS_SITE}/posts/?"
           + urllib.parse.urlencode({"search": title, "number": 20, "fields": "title,URL,attachments"}))
    with urllib.request.urlopen(urllib.request.Request(url, headers=_COVER_UA), timeout=20) as r:
        posts = json.loads(r.read()).get("posts") or []
    out, seen = [], set()
    for p in posts:
        ptitle = _html.unescape(p.get("title") or "")
        if f" {want} " not in f" {_cb_norm(ptitle)} ":
            continue
        for a in (p.get("attachments") or {}).values():
            img, w, h = a.get("URL") or "", a.get("width") or 0, a.get("height") or 0
            if not (a.get("mime_type") or "").startswith("image/") or img in seen or w < 400 or h <= w:
                continue
            seen.add(img)
            out.append({"image": img, "thumb": "https://i0.wp.com/" + re.sub(r"^https?://", "", img) + "?w=264",
                        "w": w, "h": h, "title": ptitle, "domain": "pulpcovers.com", "page": p.get("URL"),
                        "source": f"PulpCovers: {ptitle}"})
    return out


async def cover_search(request):
    """Library admins: one-click cover search. Returns the query, a plain Google Images link
    (always), and, when SERPER_API_KEY is set, CoverBrowser matches plus Google results."""
    if not auth.is_admin(auth.current_user(request)):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    slug = (request.query_params.get("slug") or "").strip()
    book = await run_in_threadpool(_cover_book_sync, slug) if slug else None
    if not book:
        return JSONResponse({"ok": False, "error": "no-book"}, status_code=404)
    q = _cover_query(book)
    base = {"ok": True, "query": q, "results": [], "coverbrowser": [], "magazine": _mag_results(slug),
            "google_url": "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote_plus(q)}
    pulp_task = asyncio.ensure_future(run_in_threadpool(_pulpcovers_sync, book))   # needs no key
    providers, errors = _web_providers(), []
    for i, (kind, env, key) in enumerate(providers):
        if kind == "serper":
            web_job, cb_job = run_in_threadpool(_serper_images_sync, q, key), run_in_threadpool(_coverbrowser_sync, book, key)
        else:
            web_job, cb_job = run_in_threadpool(_tavily_images_sync, book, key), run_in_threadpool(_coverbrowser_tavily_sync, book, key)
        web, cb = await asyncio.gather(web_job, cb_job, return_exceptions=True)
        if isinstance(web, Exception):
            err = _search_error(web)
            if err == "no-credits":
                _exhausted[env] = time.time()
            errors.append(err)
            continue                                    # next provider
        if isinstance(cb, Exception):
            _search_error(cb)
            cb = []
        try:
            pulp = await pulp_task
        except Exception:
            pulp = []
        have = {r["image"] for r in cb + pulp}
        return JSONResponse({**base, "web_source": "google" if kind == "serper" else "tavily",
                             "fallback": env != "SERPER_API_KEY",
                             "coverbrowser": cb, "pulpcovers": pulp,
                             "results": [r for r in web if r["image"] not in have][:_WEB_RESULTS]})
    try:
        pulp = await pulp_task
    except Exception:
        pulp = []
    if not providers and not errors:
        any_key = any((os.environ.get(env) or "").strip() for _k, env in _PROVIDER_KEYS)
        error = "no-credits" if any_key else "no-key"   # every configured key is resting after running out
    else:
        error = "no-credits" if errors and all(e == "no-credits" for e in errors) else "search-failed"
    return JSONResponse({**base, "pulpcovers": pulp, "error": error})


def _review_books_sync(slugs: list[str]) -> dict[str, dict]:
    con = _connect()
    try:
        out = {}
        for i in range(0, len(slugs), 500):
            chunk = slugs[i:i + 500]
            for r in con.execute(f"select slug, title, author, cover_url from books where slug in "
                                 f"({','.join('?' * len(chunk))})", chunk):
                out[r["slug"]] = dict(r)
        return out
    finally:
        con.close()


async def covers_review_page(request):
    if not shell.may_open(request, "admin"):
        return shell.for_others(request, "Magazine covers", "The magazine covers review is for library admins.")
    return shell.page(request, "covers.html")


async def covers_review(request):
    """Library admins: every book with a matched magazine-issue cover, its current cover, and
    whether that cover is already a custom one, for the bulk review page."""
    if not auth.is_admin(auth.current_user(request)):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    idx = _mag_covers()
    books = await run_in_threadpool(_review_books_sync, list(idx))
    custom = {}
    if db.ready():
        try:
            for r in await db.fetch("select book_slug, source, extract(epoch from updated_at)::bigint as v "
                                    "from cover_overrides"):
                custom[r["book_slug"]] = {"source": r["source"], "v": r["v"]}
        except Exception:                               # pre-migration: no source column yet
            for r in await db.fetch("select book_slug, extract(epoch from updated_at)::bigint as v from cover_overrides"):
                custom[r["book_slug"]] = {"source": None, "v": r["v"]}
    items = []
    for slug, rec in idx.items():
        b = books.get(slug)
        if not b or not rec["candidates"]:
            continue
        c = custom.get(slug)
        items.append({"slug": slug, "title": b["title"], "author": b["author"], "issue": rec["issue"],
                      "current": ("/api/cover/" + slug + "?v=" + str(c["v"])) if c else b["cover_url"],
                      "custom": bool(c), "custom_source": c["source"] if c else None,
                      "candidates": _mag_results(slug)["results"]})
    items.sort(key=lambda it: (it["issue"].split(",")[0], it["title"].lower()))
    return JSONResponse({"ok": True, "items": items})


async def cover_put(request):
    """Library admins can replace a book's cover art with a different image URL (or clear
    it to revert to the original). Stored in Neon and merged into the served catalog."""
    user = auth.current_user(request)
    if not auth.is_admin(user):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    if not db.ready():
        return JSONResponse({"ok": False, "error": "no-db"}, status_code=503)
    body = await request.json()
    slug = (body.get("slug") or "").strip()
    url = (body.get("cover_url") or "").strip()
    if not slug:
        return JSONResponse({"ok": False, "error": "no-slug"}, status_code=400)
    if url and not re.match(r"^https?://", url, re.I):
        return JSONResponse({"ok": False, "error": "bad-url"}, status_code=400)
    if url:
        webp = await run_in_threadpool(_url_to_webp, url)   # download + resize + WebP (self-host it)
        if not webp:
            return JSONResponse({"ok": False, "error": "fetch-failed"}, status_code=400)
        source = (body.get("source") or "").strip()[:300] or None        # e.g. "Galaxy Science
        page = (body.get("source_page") or "").strip()[:500] or None      # Fiction, July 1958 (…)"
        if page and not re.match(r"^https?://", page, re.I):
            page = None
        await db.execute(
            """insert into cover_overrides(book_slug, cover_url, webp, updated_by, updated_at, source, source_page)
               values($1, $2, $3, $4, now(), $5, $6)
               on conflict (book_slug) do update
                 set cover_url=excluded.cover_url, webp=excluded.webp, updated_by=excluded.updated_by,
                     updated_at=now(), source=excluded.source, source_page=excluded.source_page""",
            slug, url, webp, (user.get("email") or "")[:200], source, page,
        )
        return JSONResponse({"ok": True, "cover": "/api/cover/" + slug + "?v=" + str(int(time.time()))})
    await db.execute("delete from cover_overrides where book_slug=$1", slug)
    orig = await run_in_threadpool(_cover_of, slug)   # revert → the original baked-in cover
    return JSONResponse({"ok": True, "cover": orig})
