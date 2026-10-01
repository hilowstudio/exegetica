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

import html as _html
import io
import json
import os
import pathlib
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import uuid

from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, JSONResponse, Response

from webapp import auth, db

_STATIC = pathlib.Path(__file__).resolve().parent / "static"
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


def _safe_int(v, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---- SQLite reads (sync; wrapped in run_in_threadpool by the handlers) ----

def _list_sync(q: str | None, limit: int, offset: int) -> dict:
    con = _connect()
    try:
        where, params = "", []
        if q:
            where = "where title like ? or author like ?"
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


def _shelves_sync() -> list[dict]:
    """The whole corpus shelved like a library: one shelf per genre (a book appears under each of
    its genres), each shelf sorted by the surname-first sort key. Shelves ordered alphabetically."""
    con = _connect()
    try:
        rows = con.execute(
            "select slug, title, author, author_sort, genres, chapter_count, word_count from books"
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


def _catalog_sync() -> dict:
    """The whole corpus as one flat list (no per-genre duplication), for the client-side
    faceted browse: search, filter by section/length/source, and sort happen in the browser."""
    con = _connect()
    try:
        cols = {c[1] for c in con.execute("pragma table_info(books)")}
        cover = "cover_url" if "cover_url" in cols else "null as cover_url"
        rows = con.execute(
            f"""select slug, title, author, author_sort, genres, source, chapter_count, word_count, {cover}
                from books order by author_sort collate nocase, title"""
        ).fetchall()
    finally:
        con.close()
    items = []
    for r in rows:
        items.append({
            "slug": r["slug"], "title": r["title"], "author": r["author"] or "",
            "author_sort": r["author_sort"] or r["author"] or r["title"],
            "sections": json.loads(r["genres"] or "[]"), "source": r["source"],
            "chapters": r["chapter_count"], "words": r["word_count"] or 0,
            "cover": r["cover_url"],
        })
    return {"items": items, "total": len(items)}


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


def _book_sync(slug: str) -> dict | None:
    con = _connect()
    try:
        b = con.execute(
            """select id, slug, title, author, author_sort, genres, language, subjects,
                      chapter_count, word_count from books where slug=?""",
            (slug,),
        ).fetchone()
        if not b:
            return None
        toc = con.execute(
            "select section_number, title, words from book_chapters where book_id=? order by section_number",
            (b["id"],),
        ).fetchall()
        d = {k: b[k] for k in b.keys() if k != "id"}
        d["subjects"] = json.loads(d["subjects"] or "[]")
        d["genres"] = json.loads(d.get("genres") or "[]")
        d["toc"] = [dict(t) for t in toc]
        return d
    finally:
        con.close()


def _chapter_sync(slug: str, n: int) -> dict | None:
    con = _connect()
    try:
        b = con.execute("select id, slug, title, chapter_count from books where slug=?", (slug,)).fetchone()
        if not b:
            return None
        ch = con.execute(
            "select section_number, title, html, words from book_chapters where book_id=? and section_number=?",
            (b["id"], n),
        ).fetchone()
        if not ch:
            return None
        return {
            "book_slug": b["slug"], "book_title": b["title"], "chapter_count": b["chapter_count"],
            "section_number": ch["section_number"], "title": ch["title"], "html": ch["html"],
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
    """A whole book as plaintext chapters, for the Living Library generator (reads books.db —
    the converged PD corpus). Uploads/in-copyright works are NOT served here; they stay private."""
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
    return FileResponse(_STATIC / "reader.html")


async def books_list(request):
    if not available():
        return JSONResponse({"items": [], "total": 0, "available": False})
    q = (request.query_params.get("q") or "").strip() or None
    limit = min(_safe_int(request.query_params.get("limit"), 60), 200)
    offset = max(_safe_int(request.query_params.get("offset"), 0), 0)
    data = await run_in_threadpool(_list_sync, q, limit, offset)
    data["available"] = True
    return JSONResponse(data)


async def shelves(request):
    """The whole corpus shelved by genre (a book under each of its genres), each shelf
    alphabetical by author surname — the browse default."""
    if not available():
        return JSONResponse({"shelves": [], "total": 0, "available": False})
    data = await run_in_threadpool(_shelves_sync)  # {"shelves": [...], "total": N}
    data["available"] = True
    return JSONResponse(data)


async def catalog(request):
    """The whole corpus as one flat list — powers the search-first faceted browse.
    Library-admin cover overrides (Neon) are merged on top of the baked-in cover URLs."""
    if not available():
        return JSONResponse({"items": [], "total": 0, "available": False})
    data = await run_in_threadpool(_catalog_sync)
    if db.ready():
        try:
            rows = await db.fetch(
                "select book_slug, cover_url, (webp is not null) as has_webp, "
                "extract(epoch from updated_at)::bigint as v from cover_overrides")
        except Exception:
            rows = []
        ov = {r["book_slug"]: r for r in rows}
        for it in data["items"]:
            r = ov.get(it["slug"])
            if r:   # self-hosted override -> versioned local path; legacy url-only -> the URL
                it["cover"] = ("/api/cover/" + it["slug"] + "?v=" + str(r["v"])) if r["has_webp"] else r["cover_url"]
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
    d = await run_in_threadpool(_book_sync, request.path_params["slug"])
    return JSONResponse(d) if d else JSONResponse({"error": "not found"}, status_code=404)


async def book_chapter(request):
    if not available():
        return JSONResponse({"error": "unavailable"}, status_code=503)
    n = _safe_int(request.path_params.get("n"), 1)
    d = await run_in_threadpool(_chapter_sync, request.path_params["slug"], n)
    return JSONResponse(d) if d else JSONResponse({"error": "not found"}, status_code=404)


async def position_get(request):
    """All of this reader's saved positions, {slug: section_number}. Anonymous → empty
    (the client falls back to localStorage)."""
    user = auth.current_user(request)
    if not user or not db.ready():
        return JSONResponse({"positions": {}})
    rows = await db.fetch(
        "select book_slug, section_number, pages from reading_state where user_id=$1", uuid.UUID(user["id"])
    )
    return JSONResponse({
        "positions": {r["book_slug"]: r["section_number"] for r in rows},   # chapter, for the reader to resume
        "progress": {r["book_slug"]: r["pages"] for r in rows},             # furthest page reached, for "Continue Reading"
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


def _cover_query_sync(slug: str) -> str | None:
    """The admin cover-search query for a book: its main title (no subtitle or volume number,
    which over-narrow an exact-phrase search) and the author's surname."""
    con = _connect()
    try:
        r = con.execute("select title, author, author_sort from books where slug=?", (slug,)).fetchone()
    finally:
        con.close()
    if not r:
        return None
    title = re.split(r":|;", r["title"] or "")[0]
    title = re.sub(r",?\s+(volume|vol\.?)\s+\w+\s*$", "", title, flags=re.I).strip().replace('"', "")
    if r["author_sort"]:                       # "Hugo, Victor" -> Hugo
        surname = r["author_sort"].split(",")[0]
    else:
        surname = " ".join((r["author"] or "").split()[-1:])
    surname = surname.strip().replace('"', "")
    terms = [f'"{title}"'] + ([f'"{surname}"'] if surname else []) + ["~CLASSIC", '"BOOK COVER"']
    return " AND ".join(terms)


_SERPER_PAGES = 2   # 10 images a page (free accounts can't raise "num"); one credit per page


def _serper_page(q: str, key: str, page: int) -> list[dict]:
    req = urllib.request.Request(
        "https://google.serper.dev/images", data=json.dumps({"q": q, "page": page}).encode(),
        headers={"X-API-KEY": key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read()).get("images") or []


def _serper_images_sync(q: str, key: str) -> list[dict]:
    """Google Images results via Serper.dev (Google's own Custom Search API is closed to new
    customers, and scraping Google from the server gets blocked). Pages are fetched in
    parallel; a later page failing still returns the first."""
    from concurrent.futures import ThreadPoolExecutor
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
                    "title": it.get("title") or "", "domain": it.get("domain") or it.get("source") or ""})
    return out


async def cover_search(request):
    """Library admins: one-click Google Images search for a book's cover. Returns the query,
    a plain Google Images link (always), and inline results when SERPER_API_KEY is set."""
    if not auth.is_admin(auth.current_user(request)):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    slug = (request.query_params.get("slug") or "").strip()
    q = await run_in_threadpool(_cover_query_sync, slug) if slug else None
    if not q:
        return JSONResponse({"ok": False, "error": "no-book"}, status_code=404)
    google = "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote_plus(q)
    key = (os.environ.get("SERPER_API_KEY") or "").strip()
    if not key:
        return JSONResponse({"ok": True, "query": q, "google_url": google, "results": [], "error": "no-key"})
    try:
        results = await run_in_threadpool(_serper_images_sync, q, key)
    except Exception:
        return JSONResponse({"ok": True, "query": q, "google_url": google, "results": [],
                             "error": "search-failed"})
    return JSONResponse({"ok": True, "query": q, "google_url": google, "results": results})


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
        await db.execute(
            """insert into cover_overrides(book_slug, cover_url, webp, updated_by, updated_at)
               values($1, $2, $3, $4, now())
               on conflict (book_slug) do update
                 set cover_url=excluded.cover_url, webp=excluded.webp,
                     updated_by=excluded.updated_by, updated_at=now()""",
            slug, url, webp, (user.get("email") or "")[:200],
        )
        return JSONResponse({"ok": True, "cover": "/api/cover/" + slug + "?v=" + str(int(time.time()))})
    await db.execute("delete from cover_overrides where book_slug=$1", slug)
    orig = await run_in_threadpool(_cover_of, slug)   # revert → the original baked-in cover
    return JSONResponse({"ok": True, "cover": orig})
