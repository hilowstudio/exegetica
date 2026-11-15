"""A teacher's own uploads and saved links in the Living Library (decision 0029, phase 3).

A teacher uploads a book or a document, or saves a web page, and Exegetica files it as the kind of thing it is: a
book, an article, a handout, or another document. The text is read once and kept encrypted (`shelf_texts`), the way
a Prep Room upload is. It opens in a reading view at /read/doc/<id>. Placed on a class shelf it is copied there,
so the class keeps it when the teacher's own copy goes. A public-domain or openly licensed book can be suggested
for the Reading Room; the maker decides at /ops. Students never upload (decision 0029)."""
from __future__ import annotations

import html
import re
import uuid
from urllib.parse import urlparse

from starlette.concurrency import run_in_threadpool
from markupsafe import Markup
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse

from webapp import auth, db, extraction, filetext, prep_draft, shell

TYPES = ("book", "article", "handout", "document", "sermon")
TYPE_WORD = {"book": "Book", "article": "Article", "handout": "Handout", "document": "Document",
             "sermon": "Sermon Transcript"}   # a talk written down: a sermon, message or teaching lesson (Adam, 2026-11-14)
MAX_WORDS = 300_000          # a whole book; a unit's copy is trimmed to the Prep Room's own limit
MAX_DOCS = 200               # per teacher
UNAVAILABLE = "Your shelves can't be reached right now. Try again in a minute."


def _uid(user) -> uuid.UUID:
    return uuid.UUID(user["id"])


def _clean(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def guess_type(words: int, name: str, link: bool) -> str:
    """A first guess at what an upload is; the teacher can change it."""
    n = (name or "").lower()
    if link:
        return "article"
    if words >= 25_000:
        return "book"
    if re.search(r"study guide|worksheet|handout|quiz|notes|guide|lesson|review|packet|test", n):
        return "handout"
    return "document"


def _guard(request):
    user = auth.current_user(request)
    if not (user and (auth.is_teacher(user) or auth.is_admin(user))):
        return None, JSONResponse({"error": "Uploads are for teachers."}, status_code=403)
    if not db.ready():
        return None, JSONResponse({"error": UNAVAILABLE}, status_code=503)
    return user, None


def _out(r) -> dict:
    ref = r["ref"] or {}
    return {"id": str(r["id"]), "kind": r["kind"], "type": ref.get("type") or "document", "title": r["label"] or ref.get("title") or "",
            "author": ref.get("author") or "", "site": ref.get("site") or "", "url": ref.get("url"),
            "words": ref.get("words") or 0, "suggested": ref.get("suggested")}


async def _store(uid: uuid.UUID, kind: str, ref: dict, label: str, text: str) -> dict | str:
    n = await db.fetchval("select count(*) from shelf_items where user_id = $1 and kind in ('upload','link')", uid)
    if n >= MAX_DOCS:
        return f"Your shelves hold up to {MAX_DOCS} uploads and links. Delete one to add another."
    words = text.split()
    if len(words) > MAX_WORDS:
        text, words = " ".join(words[:MAX_WORDS]), words[:MAX_WORDS]
    ref = {**ref, "words": len(words)}
    row = await db.fetchrow("""insert into shelf_items (user_id, kind, ref, label, added_by) values ($1, $2, $3, $4, $1)
                               returning id, kind, ref, label""", uid, kind, ref, label[:200])
    nonce, ct = extraction.encrypt_text(text)
    await db.execute("insert into shelf_texts (item_id, nonce, ct, words) values ($1, $2, $3, $4)", row["id"], nonce, ct, len(words))
    return _out(row)


async def mine(uid: uuid.UUID) -> list[dict]:
    rows = await db.fetch("""select id, kind, ref, label from shelf_items where user_id = $1 and kind in ('upload','link')
                              order by added_at desc""", uid)
    return [_out(r) for r in rows]


async def upload(request):
    """A file a teacher brings to their shelf: read now, filed by kind, kept encrypted."""
    user, denied = _guard(request)
    if denied:
        return denied
    form = await request.form()
    f = form.get("file")
    if f is None or not getattr(f, "filename", None):
        return JSONResponse({"error": "Choose a file to upload."}, status_code=400)
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in prep_draft.UPLOAD_FORMATS:
        return JSONResponse({"error": "Upload a PDF, Word document, EPUB, or text file."}, status_code=400)
    data = await f.read(prep_draft.MAX_UPLOAD_BYTES + 1)
    if len(data) > prep_draft.MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "That file is over 15 MB."}, status_code=400)
    text = await run_in_threadpool(filetext.extract_text, data, ext)
    if len(text.split()) < 20:
        return JSONResponse({"error": "Exegetica couldn't read any text in that file. A scanned PDF needs its text "
                                     "layer; try exporting it again or uploading a Word copy."}, status_code=400)
    title = _clean(form.get("title"), 200) or _clean(re.sub(r"\.[^.]+$", "", f.filename).replace("_", " "), 200)
    kind = form.get("type") if form.get("type") in TYPES else guess_type(len(text.split()), f.filename, False)
    ref = {"type": kind, "title": title, "author": _clean(form.get("author"), 160), "filename": _clean(f.filename, 200), "format": ext}
    out = await _store(_uid(user), "upload", ref, title, text)
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"doc": out}, status_code=201)


async def link(request):
    """A web page or online PDF a teacher saves to their shelf: read now, kept as an article."""
    user, denied = _guard(request)
    if denied:
        return denied
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    url = str(b.get("url") or "").strip()
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(("youtube.com", "youtu.be", "podcasts.apple.com", "spotify.com")):
        return JSONResponse({"error": "Add a video or a podcast with the Video or Podcast tab, so its transcript comes with it."},
                            status_code=400)
    got = await prep_draft.fetch_page(url)
    if isinstance(got, str):
        return JSONResponse({"error": got}, status_code=400)
    title, text = got
    if len(text.split()) < 40:
        return JSONResponse({"error": "Exegetica couldn't find readable text on that page. If it needs a sign-in, save "
                                     "it as a PDF and upload it instead."}, status_code=400)
    kind = b.get("type") if b.get("type") in TYPES else "article"
    site = host[4:] if host.startswith("www.") else host
    title = _clean(b.get("title"), 200) or _clean(title, 200) or site
    out = await _store(_uid(user), "link", {"type": kind, "title": title, "url": url, "site": site}, title, text)
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"doc": out}, status_code=201)


async def change(request):
    """Rename an upload or link, set its author or kind (PATCH), or delete it (DELETE). The teacher's own only."""
    user, denied = _guard(request)
    if denied:
        return denied
    try:
        item = uuid.UUID(request.path_params["id"])
    except ValueError:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    row = await db.fetchrow("select id, kind, ref, label from shelf_items where id = $1 and user_id = $2 and kind in ('upload','link')",
                            item, _uid(user))
    if not row:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    if request.method == "DELETE":
        await db.execute("delete from shelf_items where id = $1", item)
        return JSONResponse({"ok": True})
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    ref, label = dict(row["ref"] or {}), row["label"]
    if b.get("title") is not None:
        label = _clean(b["title"], 200) or label
        ref["title"] = label
    if b.get("author") is not None:
        ref["author"] = _clean(b["author"], 160)
    if b.get("type") in TYPES:
        ref["type"] = b["type"]
    await db.execute("update shelf_items set ref = $2, label = $3 where id = $1", item, ref, label)
    return JSONResponse({"doc": _out({"id": row["id"], "kind": row["kind"], "ref": ref, "label": label})})


async def text_of(item: uuid.UUID) -> str | None:
    r = await db.fetchrow("select nonce, ct from shelf_texts where item_id = $1", item)
    if not r:
        return None
    try:
        return extraction.decrypt_text(r["nonce"], r["ct"])
    except Exception:  # noqa: BLE001
        return None


async def copy_text(src: uuid.UUID, dst: uuid.UUID) -> None:
    await db.execute("""insert into shelf_texts (item_id, nonce, ct, words) select $2, nonce, ct, words from shelf_texts
                        where item_id = $1 on conflict (item_id) do nothing""", src, dst)


async def readable_by(user, item: uuid.UUID):
    """The shelf item if this person may read it: their own, or on a class shelf they teach, or (a student) one
    marked for the students of a class they take."""
    if not user:
        return None
    row = await db.fetchrow("select id, user_id, course_key, audience, kind, ref, label, added_by from shelf_items where id = $1 "
                            "and kind in ('upload','link','resource')", item)
    if not row:
        return None
    if row["user_id"] and row["user_id"] == _uid(user):
        return row
    if row["course_key"]:
        from webapp import shelves
        if await shelves._teaches(user, row["course_key"]):
            return row
        if row["audience"] == "students" and row["course_key"] in await shelves.student_courses(_uid(user)):
            return row
    return None


def _same(a: str, b: str) -> bool:
    k = lambda s: re.sub(r"[\W_]+", " ", s or "").strip().lower()  # noqa: E731
    return bool(k(a)) and k(a) == k(b)


def _paragraphs(text: str, title: str = "") -> str:
    """The text as paragraphs, escaped: a blank line between paragraphs, or one paragraph a line in a short text.
    A first line that only repeats the title is left to the heading."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) < 3:
        blocks = [b.strip() for b in text.splitlines() if b.strip()]
    if blocks and _same(blocks[0], title):
        blocks = blocks[1:]
    return "".join("<p>" + html.escape(re.sub(r"\s+", " ", b)) + "</p>" for b in blocks)


async def page(request):
    """The reading view of an upload or a saved link, in the Reading Room's typography."""
    user = auth.current_user(request)
    try:
        item = uuid.UUID(request.path_params["id"])
    except ValueError:
        item = None
    row = await readable_by(user, item) if (item and db.ready()) else None
    text = await text_of(item) if row else None
    if not row or text is None:
        if user and item and db.ready():       # from a Classroom link, perhaps: offer the class (decision 0030)
            offer = await _join_offer(request, user, item)
            if offer:
                return offer
        return shell.for_others(request, "Living Library", "That isn't on your shelves.") if user else \
            shell.for_others(request, "Living Library", "It's on a class shelf in the Living Library.")
    ref = row["ref"] or {}
    teacher = bool(user) and (auth.is_teacher(user) or auth.is_admin(user))
    if row["kind"] == "resource":
        return await _resource_page(request, user, row, text, teacher)
    return shell.page(request, "doc.html", title=row["label"] or ref.get("title") or "Document",
                      doc={"id": str(row["id"]), "kind": row["kind"], "type": ref.get("type") or "document",
                           "type_word": TYPE_WORD.get(ref.get("type") or "document", "Document"), "title": row["label"],
                           "author": ref.get("author") or "", "site": ref.get("site") or "", "url": ref.get("url"),
                           "words": ref.get("words") or len(text.split()), "own": bool(row["user_id"]),
                           "origin": ref.get("origin") or str(row["id"]),   # the teacher's own copy a class copy came from
                           "class_copy": bool(row["course_key"])},
                      body_html=Markup(_paragraphs(text, row["label"])), can_place=teacher)


async def _joinable(user, item: uuid.UUID):
    """The class-shelf row this person could read once they choose its class, or None: a student only for what is
    marked for students, in a course with student logins; a teacher for any course on the school's list."""
    from webapp import shelves
    row = await db.fetchrow("""select id, course_key, audience, label from shelf_items where id = $1 and course_key is not null
                                and kind in ('upload','link','resource')""", item)
    if not row:
        return None
    teacher = shelves.is_teacher(user)
    if not teacher and row["audience"] != "students":
        return None
    course = next((c for c in shelves.courses_for(teacher) if c["key"] == row["course_key"]), None)
    return (row, course) if course else None


async def _join_offer(request, user, item: uuid.UUID):
    """The page someone sees when a Classroom link leads to a shelf they haven't chosen: what it is, whose shelf, and
    one button that adds the class and opens it. Classes stay each person's own choice (decision 0029)."""
    got = await _joinable(user, item)
    if not got:
        return None
    row, course = got
    from webapp import shelves
    name = html.escape(course["name"])
    whose = "the classes you teach" if shelves.is_teacher(user) else "your classes"
    body = (f'<main class="prose shell-col"><nav class="back"><a href="/library">Your shelves</a></nav>{shell.MASTHEAD}'
            f'<h1>{html.escape(row["label"] or "On a class shelf")}</h1>'
            f"<p>It's on the {name} shelf in the Living Library. Add {name} to {whose} to open it. "
            f"You can change your classes any time on Your shelves.</p>"
            f'<form method="post" action="/read/doc/{row["id"]}/join"><button type="submit" class="join-btn">'
            f"Add {name} and open it</button></form></main>")
    return shell.render(request, shell.Built(f"{course['name']} · Living Library · Exegetica", body,
                                             css=("/static/css/prose.css",), noindex=True))


async def join(request):
    """Add the item's class to this person's classes, then open the item (POST from the offer above)."""
    from starlette.responses import RedirectResponse
    from webapp import shelves, teacher_courses
    user = auth.current_user(request)
    try:
        item = uuid.UUID(request.path_params["id"])
    except ValueError:
        item = None
    got = await _joinable(user, item) if (user and item and db.ready()) else None
    if got:
        key = got[0]["course_key"]
        if shelves.is_teacher(user):
            await teacher_courses.set_course(user.get("email"), key, True)
        else:
            mine = await shelves.student_courses(_uid(user))
            if key not in mine and len(mine) < 12:
                await shelves.set_student_courses(_uid(user), mine + [key])
    return RedirectResponse(f"/read/doc/{item}" if item else "/library", status_code=303)


async def _resource_page(request, user, row, text: str, teacher: bool):
    """A Prep Room resource on a class shelf, on the Prep Room's own handout paper (decision 0029, phase 4). A student
    gets the student copy and nothing else; the class's teachers get both copies, and its own teacher a way back."""
    from webapp import prep_catalog, yorkville
    ref = row["ref"] or {}
    course = {c["key"]: c["name"] for c in yorkville.courses()}.get(row["course_key"], row["course_key"] or "")
    owner_href = None
    if teacher and ref.get("resource_id"):
        try:
            mine = await db.fetchrow("select id, unit_id from prep_resources where id = $1 and user_id = $2",
                                     uuid.UUID(str(ref["resource_id"])), _uid(user))
        except ValueError:
            mine = None
        if mine:
            owner_href = f"/generate/unit/{mine['unit_id']}/r/{mine['id']}" if mine["unit_id"] else f"/generate/r/{mine['id']}"
    if teacher:
        note = (f"On the {course} shelf for its students, who see the Student copy: no answer key or teaching notes."
                if row["audience"] == "students" else f"On the {course} shelf for its teachers alone.")
    else:
        note = ""
    return shell.page(request, "doc.html", title=row["label"] or "Resource",
                      doc={"id": str(row["id"]), "kind": "resource", "resource": True, "title": row["label"],
                           "kind_word": ref.get("kind_word") or "Resource", "band": ref.get("band") or "secondary",
                           "owner_href": owner_href, "note": note},
                      markdown=text if teacher else prep_catalog.student_copy(text),
                      both=teacher and prep_catalog.has_teacher_part(text), can_place=False)


# ---- suggestions for the Reading Room (decision 0029) ----

async def suggest(request):
    user, denied = _guard(request)
    if denied:
        return denied
    try:
        item = uuid.UUID(request.path_params["id"])
    except ValueError:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    row = await db.fetchrow("select id, ref, label from shelf_items where id = $1 and user_id = $2 and kind = 'upload'", item, _uid(user))
    if not row:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    basis = _clean(b.get("basis"), 500)
    if len(basis) < 6:
        return JSONResponse({"error": "Say why everyone may read it: the year it was published, or its open license."},
                            status_code=400)
    if await db.fetchval("select 1 from catalog_suggestions where item_id = $1 and status = 'pending'", item):
        return JSONResponse({"error": "You've suggested it already. The maker will decide."}, status_code=400)
    ref = dict(row["ref"] or {})
    await db.execute("insert into catalog_suggestions (item_id, user_id, title, author, basis) values ($1, $2, $3, $4, $5)",
                     item, _uid(user), row["label"], ref.get("author") or None, basis)
    ref["suggested"] = "pending"
    await db.execute("update shelf_items set ref = $2 where id = $1", item, ref)
    return JSONResponse({"ok": True})


async def pending() -> list[dict]:
    rows = await db.fetch("""select s.id, s.item_id, s.title, s.author, s.basis, s.status, s.created_at, t.words
                               from catalog_suggestions s left join shelf_texts t on t.item_id = s.item_id
                              where s.status = 'pending' or s.decided_at > now() - interval '30 days'
                              order by s.status = 'pending' desc, s.created_at desc limit 40""")
    return [dict(r) for r in rows]


async def decide(request):
    """The maker approves or declines a suggestion (POST from /ops), or downloads its text (GET .../text)."""
    user = auth.current_user(request)
    if not auth.is_admin(user) or not db.ready():
        return PlainTextResponse("Not Found", status_code=404)
    try:
        sid = uuid.UUID(request.path_params["id"])
    except ValueError:
        return PlainTextResponse("Not Found", status_code=404)
    row = await db.fetchrow("select id, item_id, title, status from catalog_suggestions where id = $1", sid)
    if not row:
        return PlainTextResponse("Not Found", status_code=404)
    if request.method == "GET":
        text = await text_of(row["item_id"]) if row["item_id"] else None
        if text is None:
            return PlainTextResponse("The uploaded text is gone: its teacher deleted it or their account.", status_code=410)
        name = re.sub(r"[^\w -]", "", row["title"] or "book")[:80].strip() or "book"
        return PlainTextResponse(text, headers={"Content-Disposition": f'attachment; filename="{name}.txt"'})
    form = await request.form()
    to = form.get("decision")
    if to in ("approved", "declined"):
        await db.execute("update catalog_suggestions set status = $2, decided_at = now() where id = $1", sid, to)
        if row["item_id"]:
            await db.execute("update shelf_items set ref = jsonb_set(ref, '{suggested}', to_jsonb($2::text)) where id = $1",
                             row["item_id"], to)
    return RedirectResponse("/ops#suggestions", status_code=303)
