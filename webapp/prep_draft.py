"""Drafting in the Prep Room (decision 0026): gather a unit's sources into one request, stream the draft,
and save it as a version when it finishes. Revisions are saved the same way. Teacher-only (0007).

Sources are given to the model in the order the teacher listed them, inside one word budget
(generator._GEN_WORD_BUDGET): documents, transcripts and outlines first, then the rest is shared by the
books. A book that fits is read whole; a large one uses its comprehension and the covered text."""
from __future__ import annotations

import asyncio
import html as _html
import logging
import re
import uuid
from urllib.parse import urlparse

import httpx
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from webapp import auth, comprehension, db, filetext, generator, library_store, policy, prep, prep_catalog, reader, yorkville

logger = logging.getLogger("study-bible-web.prep")

DOC_WORDS = 20_000            # most of one upload, link or transcript a draft is given
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
UPLOAD_FORMATS = ("pdf", "docx", "txt", "md", "epub")
NOT_SAVED = "This draft wasn't saved: saving is unavailable right now. Copy it before you leave the page."
_BACKGROUND: set = set()      # queued comprehension builds, kept referenced until they finish


def _short_name(format_id: str) -> str:
    name = generator.FORMATS[format_id]["name"]
    return re.split(r" / | \(", name)[0].strip()


def _cap(text: str, words: int) -> str:
    parts = (text or "").split()
    return text if len(parts) <= words else " ".join(parts[:words]) + " [...]"


# ------------------------------------------------------------------------------------ gathering
async def _library_item(uid: uuid.UUID, item_id: str, excerpt_ids: list[str] | None) -> dict | None:
    row = await db.fetchrow(
        """select e.id, e.kind, e.title, e.creator, e.source_url, e.source_meta, e.full_text, li.notes
             from library_items li join library_extractions e on e.id = li.extraction_id
            where li.user_id = $1 and e.id = $2""", uid, uuid.UUID(item_id))
    if not row:
        return None
    item = {"kind": row["kind"], "title": row["title"], "creator": row["creator"], "url": row["source_url"],
            "notes": row["notes"]}
    from webapp import excerpts
    text = await excerpts.transcript_for_draft({"kind": row["kind"], "source_url": row["source_url"],
                                                "episode": (row["source_meta"] or {}).get("episode")})
    if text or (row["kind"] in ("video", "podcast") and row["full_text"]):
        item["transcript"] = _cap(text or row["full_text"], DOC_WORDS)
    saved = await excerpts.for_item(uid, uuid.UUID(item_id), excerpt_ids)
    if saved:
        item["excerpts"] = saved
    return item


def _book_share(book: dict, ref: dict, share: int, query: str) -> tuple[dict, str | None]:
    """Synchronous part of a book source (books.db and embeddings): the material and any notice."""
    chapters = book["chapters"]
    coverage = ref.get("coverage") or {}
    covered, cov_desc, last = generator._coverage(coverage, chapters)
    total = book.get("word_count") or sum(c.get("words", 0) for c in chapters)
    base = {"type": "book", "book": book, "covered": covered, "cov_desc": cov_desc,
            "positioned": bool(coverage)}
    if total <= share:
        return {**base, "mode": "whole", "chapters": chapters}, None
    return {**base, "mode": "pending", "last": last, "query": query}, None


async def gather(uid: uuid.UUID | None, sources: list[dict], query: str) -> tuple[list, list, list]:
    """(materials, drew_on labels, notices) for a draft. `sources` come from prep.sources_for_draft
    (with decrypted text) or, for a quick resource, from the request after prep.clean_ref."""
    budget = generator._GEN_WORD_BUDGET
    materials: list[dict | None] = [None] * len(sources)
    drew_on, notices, books = [], [], []
    for i, s in enumerate(sources):
        kind, ref = s["kind"], s.get("ref") or {}
        if kind in ("upload", "link"):
            text = _cap(s.get("text") or "", DOC_WORDS)
            if text.strip():
                materials[i] = {"type": "document", "label": s["label"], "text": text, "url": ref.get("url")}
                budget -= len(text.split())
        elif kind == "outline":
            m = yorkville.outline_material(ref.get("key", ""), ref.get("parts"))
            if m:
                materials[i] = m
                budget -= 3_000
            else:
                notices.append(f"{s['label']}: its outline isn't available, so this draft didn't use it.")
        elif kind == "passage":
            materials[i] = {"type": "passage", "ref": ref["ref"], "translation": ref.get("translation")}
        elif kind == "library" and uid:
            item = await _library_item(uid, ref["item_id"], ref.get("excerpts"))
            if item:
                materials[i] = {"type": "library", "item": item}
                budget -= len((item.get("transcript") or "").split())
            else:
                notices.append(f"{s['label']} is no longer on your Living Library shelf.")
        elif kind == "book":
            books.append(i)
    share = max(budget // max(len(books), 1), 8_000)
    for i in books:
        s = sources[i]
        book = await run_in_threadpool(reader._gen_book_sync, s["ref"]["slug"])
        if not book or not book.get("chapters"):
            notices.append(f"{s['label']} isn't in the Reading Room any more, so this draft didn't use it.")
            continue
        m, note = await run_in_threadpool(_book_share, book, s["ref"], share, query)
        if m["mode"] == "pending":
            m, note = await _large_book(m, share)
        if note:
            notices.append(note)
        materials[i] = m
    for i, m in enumerate(materials):
        if m:
            drew_on.append(sources[i]["label"])
    return [m for m in materials if m], drew_on, notices


async def _large_book(m: dict, share: int) -> tuple[dict, str | None]:
    book = m["book"]
    state, comp = await comprehension.status(book)
    note = None
    if state == "missing" and db.ready():
        # Queue the whole-book reading without waiting on it: the draft goes ahead from the chosen
        # chapters, and an unreachable queue never holds the teacher up.
        from webapp import app as appmod                 # the Inngest trigger lives with the app
        task = asyncio.create_task(appmod._request_comprehension(book["slug"]))
        _BACKGROUND.add(task)
        task.add_done_callback(_BACKGROUND.discard)
        note = (f'Exegetica is reading all of "{book["title"]}" for the first time, which takes a few minutes. '
                "This draft used the chapters you chose; drafts after that will know the whole book.")
    covered = m["covered"] or {c["n"] for c in book["chapters"] if c["n"] <= m["last"]}
    if comp:
        covered_text, retrieved = await run_in_threadpool(
            comprehension.select_covered_text, book, covered, m["query"], share)
        recap = comprehension.recap_before(comp, min(covered) if covered else 1)
        return {**m, "mode": "large", "comp": comp, "covered_text": covered_text, "recap": recap,
                "retrieved": retrieved}, note
    keep, left = [], share                                # no comprehension: the covered chapters, newest first
    for c in reversed([c for c in book["chapters"] if c["n"] in covered]):
        if left - c.get("words", 0) < 0 and keep:
            break
        keep.append(c)
        left -= c.get("words", 0)
    keep.sort(key=lambda c: c["n"])
    if len(keep) < len(covered):
        note = note or f'"{book["title"]}" is long, so this draft read the last {len(keep)} chapters you chose.'
    return {**m, "mode": "whole", "chapters": keep}, note


# --------------------------------------------------------------------------------------- routes
async def gallery(request):
    if not auth.is_teacher(auth.current_user(request)):
        return JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    return JSONResponse({**prep_catalog.gallery(), "courses": yorkville.courses()})


_ACCESS_WORD = {"school": "school copy", "reference": "school textbook", None: "public domain"}


def _book_search_sync(q: str, level: int, limit: int = 10) -> list[dict]:
    """Reading Room books for a source: every word must be in the title or author, and the school's own
    copies and textbooks come first, then titles that start with the words."""
    words = [w for w in re.findall(r"[\w']+", (q or "").lower()) if len(w) > 1][:6]
    if not words:
        return []
    con = reader._connect()
    try:
        has_access = "access" in {r[1] for r in con.execute("pragma table_info(books)")}
        where = reader._visible(con, level) + "".join(" and (lower(title) like ? or lower(author) like ?)" for _ in words)
        params = [p for w in words for p in (f"%{w}%", f"%{w}%")]
        acc = "access" if has_access else "null as access"
        rows = con.execute(
            f"""select slug, title, author, word_count, {acc} from books where {where}
                order by (case when {acc.split(' as ')[0]} in ('school', 'reference') then 0 else 1 end),
                         (case when lower(title) like ? then 0 else 1 end), length(title)
                limit ?""", [*params, f"{words[0]}%", limit]).fetchall()
        return [{"slug": r["slug"], "title": r["title"], "author": r["author"], "words": r["word_count"],
                 "access": _ACCESS_WORD.get(r["access"], "public domain")} for r in rows]
    finally:
        con.close()


async def books(request):
    user = auth.current_user(request)
    if not auth.is_teacher(user):
        return JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    if not reader.available():
        return JSONResponse({"results": []})
    return JSONResponse({"results": await run_in_threadpool(_book_search_sync, request.query_params.get("q", ""),
                                                            reader.reader_level(user))})


async def outlines(request):
    if not auth.is_teacher(auth.current_user(request)):
        return JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    return JSONResponse({"results": yorkville.search_outlines(request.query_params.get("q", ""))})


async def draft(request):
    """Make a resource: in a unit (its sources, objectives and note), or as a quick resource from the
    sources sent with the request. Streams like the old Generator and saves the result as version 1."""
    from webapp import app as appmod
    user = auth.current_user(request)
    if not auth.is_teacher(user):
        return JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    b = await prep._body(request)
    format_id = b.get("format_id")
    if format_id not in generator.FORMATS:
        return JSONResponse({"error": "Pick a kind of resource."}, status_code=400)
    s = b.get("settings") if isinstance(b.get("settings"), dict) else {}
    settings = {"variant": str(s.get("variant") or "")[:300] or None,
                "item_types": [str(t)[:40] for t in (s.get("item_types") or [])][:8],
                "length": s.get("length") if s.get("length") in prep_catalog.LENGTHS else "standard",
                "grade_band": s.get("grade_band") if s.get("grade_band") in prep.GRADE_BANDS else None,
                "brief": str(s.get("brief") or "")[:4000]}
    uid = prep._uuid(user.get("id"))
    unit_id = prep._uuid(b.get("unit_id")) if b.get("unit_id") else None
    unit = None
    if unit_id:
        if not db.ready() or not uid:
            return JSONResponse({"error": prep.UNAVAILABLE}, status_code=503)
        unit = await prep.get_unit(uid, unit_id)
        if not unit:
            return prep._not_found("That unit")
        unit["course_name"] = yorkville.course_name(unit.get("course_key"))
        sources = await prep.sources_for_draft(uid, unit_id)
    else:
        sources = []
        for x in (b.get("sources") or [])[:6]:
            kind = (x or {}).get("kind")
            if kind in ("book", "outline", "passage", "library"):
                ref = prep.clean_ref(kind, x.get("ref"))
                if ref:
                    sources.append({"kind": kind, "ref": ref, "label": prep._clean(x.get("label"), 200) or kind})
    grade_band = settings["grade_band"] or (unit or {}).get("grade_band") or "secondary"
    settings["grade_band"] = grade_band
    query = f'{generator.FORMATS[format_id]["name"]}. {settings["brief"]} {(unit or {}).get("title", "")}'.strip()
    materials, drew_on, notices = await gather(uid if db.ready() else None, sources, query)
    provider, model, api_key = policy.byok(b)
    system_text = generator.build_system(format_id, grade_band)
    task = generator.build_unit_task(format_id, settings=settings, unit=unit, materials=materials)
    title = prep._clean(b.get("title"), prep.MAX_TITLE) or (
        f'{_short_name(format_id)} · {drew_on[0] if drew_on else (unit or {}).get("title") or "Quick"}')[:prep.MAX_TITLE]

    async def save(document, report):
        if not (db.ready() and uid):
            return {"type": "notice", "message": NOT_SAVED}
        rid = await prep.create_resource(uid, unit_id, format_id, title, settings)
        n = rid and await prep.add_version(uid, uuid.UUID(rid), document, "draft", drew_on=drew_on, report=report)
        if not n:
            return {"type": "notice", "message": NOT_SAVED}
        return {"type": "saved", "resource_id": rid, "n": n, "title": title}

    start = {"type": "start", "format": format_id, "provider": provider, "drew_on": drew_on, "notices": notices}
    capped = await appmod.prep_capped(request, start)       # decision 0027
    if capped:
        return capped
    return appmod._generation("prep:draft", start, provider, api_key, model, system_text, task,
                              request.app.state.mcp, policy.GENERATE, on_complete=save,
                              on_end=appmod.prep_counter(user))


async def revise(request):
    """Change a saved resource by instruction. Reads its newest version from the server (a hand edit is
    saved as a version first), streams the revision, and saves it as the next version."""
    from webapp import app as appmod
    uid, denied = prep._guard(request)
    if denied:
        return denied
    b = await prep._body(request)
    rid = prep._uuid(b.get("resource_id"))
    instruction = str(b.get("instruction") or "").strip()[:2000]
    if not rid or not instruction:
        return JSONResponse({"error": "Say what to change."}, status_code=400)
    res = await prep.get_resource(uid, rid)
    document = ((res or {}).get("version") or {}).get("document")
    if not document:
        return prep._not_found("That resource")
    provider, model, api_key = policy.byok(b)
    system_text, task = generator.build_revision(document, instruction)

    async def save(new_doc, _report):
        n = await prep.add_version(uid, rid, new_doc, "revise", instruction=instruction)
        return {"type": "saved", "resource_id": str(rid), "n": n} if n else {"type": "notice", "message": NOT_SAVED}

    start = {"type": "start", "provider": provider}
    capped = await appmod.prep_capped(request, start)       # decision 0027
    if capped:
        return capped
    return appmod._generation("prep:revise", start, provider, api_key, model, system_text, task,
                              request.app.state.mcp, policy.REVISE, on_complete=save,
                              on_end=appmod.prep_counter(auth.current_user(request)))


async def upload_source(request):
    """A document the teacher uploads to a unit (PDF, Word, text, EPUB): read now, kept encrypted."""
    uid, denied = prep._guard(request)
    if denied:
        return denied
    unit_id = prep._uuid(request.path_params["id"])
    form = await request.form()
    f = form.get("file")
    if not unit_id or f is None or not getattr(f, "filename", None):
        return JSONResponse({"error": "Choose a file to upload."}, status_code=400)
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in UPLOAD_FORMATS:
        return JSONResponse({"error": "Upload a PDF, Word document, EPUB, or text file."}, status_code=400)
    data = await f.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "That file is over 15 MB."}, status_code=400)
    text = await run_in_threadpool(filetext.extract_text, data, ext)
    if len(text.split()) < 20:
        return JSONResponse({"error": "Exegetica couldn't read any text in that file. A scanned PDF needs "
                                     "its text layer; try exporting it again or uploading a Word copy."},
                            status_code=400)
    label = prep._clean(form.get("label"), 200) or prep._clean(f.filename, 200)
    out = await prep.add_source(uid, unit_id, "upload", prep.clean_ref("upload", {"filename": f.filename,
                                                                                 "format": ext}), label, text=text)
    if out is None:
        return prep._not_found("That unit")
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"source": out}, status_code=201)


_UA = {"User-Agent": "Exegetica-PrepRoom/1.0 (+https://exegetica.app)"}


async def fetch_page(url: str) -> tuple[str, str] | str:
    """(title, readable text) of a public web page or PDF, or a message saying why not."""
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
        for _ in range(5):
            p = urlparse(url)
            if p.scheme not in ("http", "https") or not p.hostname:
                return "That isn't a web address."
            if not await asyncio.to_thread(library_store._host_is_public, p.hostname):
                return "That address can't be reached from Exegetica."
            try:
                resp = await client.get(url, headers=_UA)
            except Exception:  # noqa: BLE001
                return "That page didn't answer. Check the address and try again."
            if resp.is_redirect and resp.headers.get("location"):
                url = str(httpx.URL(str(resp.url)).join(resp.headers["location"]))
                continue
            break
        else:
            return "That page redirects too many times."
    if resp.status_code != 200:
        return f"That page answered with an error ({resp.status_code})."
    ct = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    body = resp.content[:MAX_UPLOAD_BYTES]
    if ct == "application/pdf":
        return url.rsplit("/", 1)[-1] or "PDF", await run_in_threadpool(filetext.extract_text, body, "pdf")
    if ct not in ("text/html", "application/xhtml+xml", "text/plain"):
        return "Exegetica can read web pages and PDFs, not that kind of file."
    if ct == "text/plain":
        return url, body.decode(resp.encoding or "utf-8", "replace")
    return await run_in_threadpool(readable, body.decode(resp.encoding or "utf-8", "replace"))


def readable(page: str) -> tuple[str, str]:
    """The title and main text of an HTML page: the article or main element when there is one, without
    scripts, navigation, headers, footers or asides."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page, "html.parser")
    og = soup.find("meta", property="og:title")
    title = (og.get("content") if og else None) or (soup.title.get_text() if soup.title else "") or ""
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    blocks = [re.sub(r"\s+", " ", el.get_text(" ")).strip()
              for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote", "pre", "td"])]
    text = "\n\n".join(b for b in blocks if b)
    return _html.unescape(title).strip(), text


async def link_source(request):
    """A web page or online PDF added to a unit: read now, kept encrypted like an upload."""
    uid, denied = prep._guard(request)
    if denied:
        return denied
    unit_id = prep._uuid(request.path_params["id"])
    b = await prep._body(request)
    url = str(b.get("url") or "").strip()
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(("youtube.com", "youtu.be", "podcasts.apple.com", "spotify.com")):
        return JSONResponse({"error": "Add videos and podcasts to your Living Library, then add them here, so "
                                     "their transcript comes with them."}, status_code=400)
    got = await fetch_page(url)
    if isinstance(got, str):
        return JSONResponse({"error": got}, status_code=400)
    title, text = got
    if len(text.split()) < 40:
        return JSONResponse({"error": "Exegetica couldn't find readable text on that page. If it needs a "
                                     "sign-in, save it as a PDF and upload it instead."}, status_code=400)
    label = prep._clean(b.get("label"), 200) or prep._clean(title, 200) or host
    out = await prep.add_source(uid, unit_id, "link", prep.clean_ref("link", {"url": url}), label, text=text) \
        if unit_id else None
    if out is None:
        return prep._not_found("That unit")
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"source": out}, status_code=201)
