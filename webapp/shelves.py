"""The Living Library's shelves, for everyone signed in (decision 0029).

A person's library opens on a shelf for each class they take or teach (the school's texts for it, from
webapp/data/yorkville.json), then the Reading Room books they have shelved. Teachers keep choosing their classes in
`teacher_courses` (decision 0026); students choose theirs here, in `student_courses`. What a person may open
follows the Reading Room's own access rules (reader.reader_level): a student never gets a reference copy.
Nothing here is ever given to a model (decision 0002)."""
from __future__ import annotations

import uuid

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from webapp import auth, db, reader, teacher_courses, yorkville

UNAVAILABLE = "Your shelves can't be reached right now. Try again in a minute."
GUEST_CLASSES = "Class shelves are for Yorkville Christian School accounts."


def _uid(user) -> uuid.UUID:
    return uuid.UUID(user["id"])


def is_teacher(user) -> bool:
    return bool(user) and (auth.is_teacher(user) or auth.is_admin(user))


def _top_grade(grades: str) -> int:
    nums = [int(x) for x in str(grades or "").replace("–", "-").split("-") if x.strip().isdigit()]
    return max(nums) if nums else 0


SUBJECTS = ["Bible", "English", "Social Studies", "Science", "Mathematics", "World Languages", "Health", "Agriculture"]


def _subject_rank(c) -> int:
    return SUBJECTS.index(c.get("subject")) if c.get("subject") in SUBJECTS else len(SUBJECTS)


def courses_for(teacher: bool) -> list[dict]:
    """The courses a person may pick, Bible first. Student logins are grades 9 to 12, so a student sees only those."""
    allowed = [c for c in yorkville.courses() if teacher or _top_grade(c.get("grades")) >= 9]
    return sorted(allowed, key=_subject_rank)   # stable: the school's own order within a subject


def courses_open_to(user) -> list[dict]:
    """The courses this person may pick. A guest from outside the school picks none (decision 0005)."""
    return [] if auth.is_guest(user) else courses_for(is_teacher(user))


async def student_courses(uid: uuid.UUID) -> list[str]:
    rows = await db.fetch("select course_key from student_courses where user_id = $1 order by added_at, course_key", uid)
    return [r["course_key"] for r in rows]


async def set_student_courses(uid: uuid.UUID, keys: list[str]) -> None:
    await db.execute("delete from student_courses where user_id = $1 and not (course_key = any($2::text[]))", uid, keys)
    for k in keys:
        await db.execute("insert into student_courses (user_id, course_key) values ($1, $2) on conflict do nothing", uid, k)


async def shelve_book(uid: uuid.UUID, slug: str, title: str) -> None:
    await db.execute(
        """insert into shelf_items (user_id, kind, ref, label, added_by) values ($1, 'book', $2, $3, $1)
           on conflict (user_id, (ref->>'slug')) where kind = 'book' and user_id is not null do nothing""",
        uid, {"slug": slug}, (title or "")[:200])


async def unshelve_book(uid: uuid.UUID, slug: str) -> None:
    await db.execute("delete from shelf_items where user_id = $1 and kind = 'book' and ref->>'slug' = $2", uid, slug)


async def classes_of(user) -> list[str]:
    if auth.is_guest(user):
        return []
    if is_teacher(user):
        return await teacher_courses.mine(user.get("email"))
    return await student_courses(_uid(user))


async def shelved(uid: uuid.UUID) -> list[str]:
    rows = await db.fetch("select ref->>'slug' as slug from shelf_items where user_id = $1 and kind = 'book' "
                          "order by added_at desc", uid)
    return [r["slug"] for r in rows if r["slug"]]


def class_shelves(keys: list[str], items: dict[str, dict], teacher: bool, placed: list[dict] | None = None,
                  videos: dict[str, dict] | None = None, me: str | None = None) -> list[dict]:
    """A shelf for each chosen course, in the picker's order (Bible first), holding the school's texts for it. A text this person
    can open carries its book. One they can't is still shown, so the shelf says what the class reads: an outline
    for a teacher, or for a student a book the class reads in print."""
    by_key = {c["key"]: c for c in yorkville.courses()}
    order = [c["key"] for c in sorted(yorkville.courses(), key=_subject_rank)]
    works = yorkville.works(keys)
    out = []
    for k in sorted(keys, key=lambda k: order.index(k) if k in order else len(order)):   # the picker's order
        c = by_key.get(k)
        if not c:
            continue
        shelf = []
        for w in works:
            if k not in w["courses"]:
                continue
            o = yorkville.outline(w["outline"]) if w["state"] == "outline" else None
            book = items.get(w.get("slug") or "")
            state = "text" if book else ("outline" if o and teacher else "print")
            shelf.append({"key": w["key"], "title": (o or {}).get("title") or w.get("title") or "",
                          "author": w.get("author") or ", ".join((o or {}).get("authors") or []),
                          "state": state, "book": book, "outline": w.get("outline") if state == "outline" else None})
        added = []
        for pl in placed or []:
            if pl["course"] != k:
                continue
            entry = {"id": pl["id"], "kind": pl["kind"], "audience": pl["audience"], "label": pl["label"]}
            if teacher:                                   # who added it is for the class's teachers alone
                entry["added_name"] = pl.get("added_name") or ("You" if pl.get("added_by") == me else None)
                entry["yours"] = pl.get("added_by") == me
                entry["ref"] = pl["ref"]                  # what one Save to sends on (decision 0031); no audio address
            if pl["kind"] == "book":
                book = items.get(pl["ref"].get("slug") or "")
                if not book:
                    continue
                entry["book"] = book
            elif pl["kind"] == "resource":
                r = pl["ref"]
                entry["doc"] = {"type": "resource", "kind_word": r.get("kind_word") or "Resource", "title": pl["label"],
                                "n": r.get("n")}
            elif pl["kind"] in ("upload", "link"):
                r = pl["ref"]
                entry["doc"] = {"type": r.get("type") or "document", "title": pl["label"], "author": r.get("author") or "",
                                "site": r.get("site") or "", "url": r.get("url")}
            elif pl["kind"] == "podcast":
                r, ep = pl["ref"], pl["ref"].get("ep") or {}
                entry["podcast"] = {"title": ep.get("title") or pl["label"], "show": ep.get("show") or "",
                                    "artwork": ep.get("artwork"), "length": ep.get("length") or "",
                                    "start": r.get("start"), "end": r.get("end"), "note": r.get("note"),
                                    "quote": r.get("quote"), "url": f"/listen/{pl['id']}"}
            else:
                v = (videos or {}).get(pl["ref"].get("item_id") or "")
                if not v:
                    continue
                start = pl["ref"].get("start")
                entry["video"] = {**v, "url": f"/watch/{pl['id']}", "start": start, "end": pl["ref"].get("end"),   # plays in Exegetica (0034)
                                  "note": pl["ref"].get("note"), "quote": pl["ref"].get("quote")}
            added.append(entry)
        out.append({"key": k, "name": c["name"], "subject": c.get("subject"), "grades": c.get("grades"), "works": shelf,
                    "added": added})
    return out


async def home(request):
    """Everything the Living Library's front page shows for this person."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "Sign in with your school account to keep shelves."}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": UNAVAILABLE}, status_code=503)
    teacher, uid = is_teacher(user), _uid(user)
    keys = await classes_of(user)
    mine = await shelved(uid)
    placed = await placements(keys, students_only=not teacher)
    texts = [w.get("slug") for w in yorkville.works(keys) if w.get("slug")]
    placed_books = [p["ref"].get("slug") for p in placed if p["kind"] == "book"]
    items = await run_in_threadpool(reader.items_sync, texts + placed_books + mine, reader.reader_level(user))
    await reader.apply_overrides(items.values())
    videos = await _videos([p["ref"].get("item_id") for p in placed if p["kind"] == "video"])
    books = [items[s] for s in mine if s in items]
    from webapp import shelf_docs, shelf_resources
    docs = await shelf_docs.mine(uid) if teacher else []
    prep_work = await shelf_resources.mine(uid) if teacher else []
    rows = await db.fetch("select book_slug, section_number, pages from reading_state where user_id = $1", uid)
    return JSONResponse({
        "teacher": teacher, "guest": auth.is_guest(user), "courses": courses_open_to(user), "mine": keys,
        "classes": class_shelves(keys, items, teacher, placed, videos, str(uid)), "books": books, "docs": docs, "prep": prep_work,
        "progress": {r["book_slug"]: {"section": r["section_number"], "pages": r["pages"]} for r in rows if r["book_slug"] in items},
    })


async def choose_classes(request):
    """Set the classes this person takes (a student) or teaches (a teacher), all at once."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "Sign in with your school account first."}, status_code=401)
    if auth.is_guest(user):
        return JSONResponse({"error": GUEST_CLASSES}, status_code=403)
    if not db.ready():
        return JSONResponse({"error": UNAVAILABLE}, status_code=503)
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    keys = b.get("courses") if isinstance(b, dict) else None
    known = {c["key"] for c in courses_open_to(user)}
    if not isinstance(keys, list) or not set(keys) <= known or len(keys) > 12:
        return JSONResponse({"error": "Pick classes from the school's list."}, status_code=400)
    if is_teacher(user):
        now = set(await teacher_courses.mine(user.get("email")))
        for k in set(keys) - now:
            await teacher_courses.set_course(user.get("email"), k, True)
        for k in now - set(keys):
            await teacher_courses.set_course(user.get("email"), k, False)
    else:
        await set_student_courses(_uid(user), keys)
    return JSONResponse({"ok": True, "mine": await classes_of(user)})


async def shelf_books(request):
    """The slugs on this person's shelf, so the Reading Room can mark them."""
    user = auth.current_user(request)
    if not user or not db.ready():
        return JSONResponse({"slugs": [], "signed": bool(user)})
    return JSONResponse({"slugs": await shelved(_uid(user)), "signed": True})


async def shelve(request):
    """Put a Reading Room book on this person's shelf (PUT) or take it off (DELETE)."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "Sign in with your school account to keep a shelf."}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": UNAVAILABLE}, status_code=503)
    slug, uid = request.path_params["slug"], _uid(user)
    if request.method == "DELETE":
        await unshelve_book(uid, slug)
        return JSONResponse({"ok": True, "shelved": False})
    items = await run_in_threadpool(reader.items_sync, [slug], reader.reader_level(user))
    if slug not in items:
        return JSONResponse({"error": "That book isn't in the Reading Room."}, status_code=404)
    await shelve_book(uid, slug, items[slug]["title"])
    return JSONResponse({"ok": True, "shelved": True})


# ---- class shelves (decision 0029, phase 2) ----
# A class shelf belongs to a course, not to a teacher: one per course, shared by every teacher and section of it.
# Its rows have course_key set and user_id null, so they stay when the teacher who added them goes (added_by is set
# null then, and nothing names them). Teachers place Reading Room books and videos (a whole video, or a moment of
# one); students see what is marked for them. Taking an item off never destroys it: when it wasn't yours, the
# original goes back to the shelf of the teacher who added it.

PLACEABLE = ("book", "video", "podcast", "upload", "link", "resource")


def _key_of(kind: str, ref: dict) -> str:
    """What makes two placements on one shelf the same thing."""
    if kind == "book":
        return ref.get("slug") or ""
    if kind in ("upload", "link"):
        return ref.get("origin") or ref.get("url") or ""     # the teacher's own copy it came from
    if kind == "resource":
        return str(ref.get("resource_id") or "")             # one Prep Room resource, whatever its version
    start = ref.get("start")
    if kind == "podcast":                                    # one episode of a show, or a moment in it
        return f"{ref.get('item_id')}#{ref.get('guid') or ''}@{-1 if start is None else int(start)}"
    return f"{ref.get('item_id')}@{-1 if start is None else int(start)}"   # a moment at 0:00 is not the whole video


async def _teaches(user, course_key: str) -> bool:
    return is_teacher(user) and course_key in await teacher_courses.mine(user.get("email"))


async def placements(course_keys: list[str], students_only: bool) -> list[dict]:
    if not course_keys:
        return []
    rows = await db.fetch(
        """select s.id, s.course_key, s.audience, s.kind, s.ref, s.label, s.added_by, s.added_at, u.name as added_name
             from shelf_items s left join users u on u.id = s.added_by
            where s.course_key = any($1::text[]) and ($2 = false or s.audience = 'students')
            order by s.added_at""", course_keys, students_only)
    return [{"id": str(r["id"]), "course": r["course_key"], "audience": r["audience"], "kind": r["kind"],
             "ref": _public_ref(r["kind"], r["ref"]), "label": r["label"],
             "added_by": str(r["added_by"]) if r["added_by"] else None, "added_name": r["added_name"]} for r in rows]


def _public_ref(kind: str, ref: dict) -> dict:
    """A placement's ref as a browser may see it: a podcast's audio address stays on the server (decision 0031)."""
    if kind != "podcast" or not isinstance(ref, dict):
        return ref
    ep = {k: v for k, v in (ref.get("ep") or {}).items() if k not in ("audio", "feed")}
    return {**ref, "ep": ep}


async def _episode_for(ref: dict) -> dict | str:
    """The episode a podcast placement holds, from the teacher's Living Library: a single episode they kept, or one
    episode of a show (its guid), looked up in the show's feed. A whole show never goes on a class shelf (0031)."""
    from webapp import transcripts
    try:
        item_id = uuid.UUID(str(ref.get("item_id") or ""))
    except ValueError:
        return "That podcast isn't in the Living Library."
    row = await db.fetchrow("""select id, title, creator, cover_url, source_url, source_meta from library_extractions
                                where id = $1 and kind = 'podcast'""", item_id)
    if not row:
        return "That podcast isn't in the Living Library."
    meta = (row["source_meta"] or {}).get("episode")
    if meta:
        return {"item_id": str(row["id"]), "guid": meta.get("guid"), "title": row["title"] or "", "show": meta.get("show") or row["creator"] or "",
                "date": meta.get("date") or "", "length": meta.get("length") or "", "seconds": meta.get("seconds"),
                "description": meta.get("description") or "", "artwork": row["cover_url"], "audio": meta.get("audio"),
                "feed": row["source_url"]}
    guid = str(ref.get("guid") or "")
    if not guid:
        return "A class shelf takes an episode, not a whole show. Choose an episode of it."
    try:
        ep = next((e for e in await transcripts.episodes(row["source_url"], limit=5000) if e["guid"] == guid), None)
    except Exception:  # noqa: BLE001
        ep = None
    if not ep:
        return "That episode isn't in the show's feed any more."
    return {"item_id": str(row["id"]), "guid": guid, "title": ep["title"], "show": row["title"] or "",
            "date": (ep.get("date") or "")[:16], "length": ep.get("duration") or "", "seconds": None, "description": "",
            "artwork": row["cover_url"], "audio": ep.get("audio"), "feed": row["source_url"]}


async def _videos(ids: list[str]) -> dict[str, dict]:
    ids = [i for i in dict.fromkeys(ids) if i]
    if not ids:
        return {}
    rows = await db.fetch("""select id, title, creator, cover_url, source_url from library_extractions
                              where id = any($1::uuid[]) and kind = 'video'""", ids)
    return {str(r["id"]): {"title": r["title"] or "", "sub": r["creator"] or "", "thumbnail": r["cover_url"],
                           "url": r["source_url"]} for r in rows}




async def place(user, course_key: str, kind: str, ref: dict, audience: str, label: str) -> dict | str:
    """Put a book or a video on a class shelf. A message when it can't go there."""
    if kind not in PLACEABLE:
        return "That can't go on a class shelf yet."
    if not await _teaches(user, course_key):
        return "Choose that class in your classes first."
    if kind == "book":
        items = await run_in_threadpool(reader.items_sync, [ref.get("slug") or ""], reader.reader_level(user))
        book = items.get(ref.get("slug") or "")
        if not book:
            return "That book isn't in the Reading Room."
        ref = {"slug": book["slug"]}
        if await run_in_threadpool(reader.is_reference, book["slug"]):
            audience = "teachers"                 # a teacher's edition never reaches a student
        label = label or book["title"]
    elif kind == "resource":                    # the student copy of a Prep Room resource, always its newest version
        from webapp import shelf_resources
        snap = await shelf_resources.snapshot(_uid(user), ref.get("resource_id"))
        if isinstance(snap, str):
            return snap
        ref, label = snap["ref"], label or snap["title"]
        if ref["keys_only"]:
            audience = "teachers"                 # an answer key never reaches a student
    elif kind == "podcast":                     # an episode, or a moment in one, that students hear in the player
        ep = await _episode_for(ref)
        if isinstance(ep, str):
            return ep
        clean = {"item_id": ep.pop("item_id"), "guid": ep["guid"], "ep": ep}
        for f in ("start", "end"):
            if isinstance(ref.get(f), (int, float)):
                clean[f] = float(ref[f])
        for f in ("quote", "note"):
            if ref.get(f):
                clean[f] = str(ref[f])[:600]
        ref = clean
        label = label or ep["title"]
    elif kind in ("upload", "link"):
        from webapp import shelf_docs
        try:
            src_id = uuid.UUID(str(ref.get("item_id") or ""))
        except ValueError:
            return "That isn't on your shelves."
        src = await shelf_docs.readable_by(user, src_id)
        if not src:
            return "That isn't on your shelves."
        sref = {k: v for k, v in (src["ref"] or {}).items() if k != "suggested"}
        ref = {**sref, "origin": sref.get("origin") or str(src["id"])}
        kind, label = src["kind"], label or src["label"]
    else:
        vids = await _videos([str(ref.get("item_id") or "")])
        v = vids.get(str(ref.get("item_id") or ""))
        if not v:
            return "That video isn't in the Living Library."
        clean = {"item_id": str(ref["item_id"])}
        for f in ("start", "end"):
            if isinstance(ref.get(f), (int, float)):
                clean[f] = float(ref[f])
        for f in ("quote", "note"):
            if ref.get(f):
                clean[f] = str(ref[f])[:600]   # a moment's words travel with it, so it outlives the moment
        ref = clean
        label = label or v["title"]
    audience = audience if audience in ("students", "teachers") else "students"
    held = [p for p in await placements([course_key], False) if p["kind"] == kind and _key_of(kind, p["ref"]) == _key_of(kind, ref)]
    if held:
        return f"{held[0]['label']} is already on that class shelf."
    row = await db.fetchrow(
        """insert into shelf_items (course_key, audience, kind, ref, label, added_by) values ($1, $2, $3, $4, $5, $6)
           returning id""", course_key, audience, kind, ref, (label or "")[:200], _uid(user))
    if kind in ("upload", "link"):              # the class keeps its own copy of the text
        from webapp import shelf_docs
        await shelf_docs.copy_text(src["id"], row["id"])
    elif kind == "resource":
        from webapp import shelf_resources
        await shelf_resources.store_text(row["id"], snap["document"])
    return {"id": str(row["id"]), "course": course_key, "audience": audience, "kind": kind,
            "ref": _public_ref(kind, ref), "label": label}


async def take_off(user, item_id: uuid.UUID) -> dict | str | None:
    """Take an item off a class shelf. When another teacher added it and still has an account, the original goes
    back to that teacher's own shelf. The removed row comes back for an undo."""
    row = await db.fetchrow("select id, course_key, audience, kind, ref, label, added_by from shelf_items where id = $1 "
                            "and course_key is not null", item_id)
    if not row:
        return None
    if not await _teaches(user, row["course_key"]):
        return "Only a teacher of that class can change its shelf."
    returned = False
    creator = row["added_by"]
    if creator and creator != _uid(user) and row["kind"] != "resource":   # a resource is still in its teacher's Prep Room
        if row["kind"] == "book":
            await shelve_book(creator, row["ref"].get("slug"), row["label"])
        elif row["kind"] in ("upload", "link"):
            await _return_doc(creator, row)
        else:
            await db.execute("""insert into library_items (user_id, extraction_id) values ($1, $2)
                                on conflict (user_id, extraction_id) do nothing""", creator, uuid.UUID(row["ref"]["item_id"]))
        returned = True
    await db.execute("delete from shelf_items where id = $1", item_id)
    return {"course": row["course_key"], "audience": row["audience"], "kind": row["kind"], "ref": row["ref"],
            "label": row["label"], "returned": returned}


async def _return_doc(creator: uuid.UUID, row) -> None:
    """An upload or link taken off a class shelf goes back to its teacher, unless their own copy is still there."""
    from webapp import shelf_docs
    origin = (row["ref"] or {}).get("origin")
    if origin and await db.fetchval("select 1 from shelf_items where id = $1::uuid and user_id = $2", origin, creator):
        return
    ref = {k: v for k, v in (row["ref"] or {}).items() if k != "origin"}
    new = await db.fetchval("""insert into shelf_items (user_id, kind, ref, label, added_by) values ($1, $2, $3, $4, $1)
                               returning id""", creator, row["kind"], ref, row["label"])
    await shelf_docs.copy_text(row["id"], new)


async def set_audience(user, item_id: uuid.UUID, audience: str) -> bool | str:
    row = await db.fetchrow("select course_key, kind, ref from shelf_items where id = $1 and course_key is not null", item_id)
    if not row:
        return False
    if not await _teaches(user, row["course_key"]):
        return "Only a teacher of that class can change its shelf."
    if audience == "students" and row["kind"] == "book" and await run_in_threadpool(reader.is_reference, row["ref"].get("slug")):
        return "A teacher's copy stays with the teachers."
    if audience == "students" and row["kind"] == "resource" and (row["ref"] or {}).get("keys_only"):
        return "It has nothing for students: an answer key stays with the teachers."
    await db.execute("update shelf_items set audience = $2 where id = $1", item_id, audience)
    return True


async def class_holding(user, kind: str, key: str) -> list[dict]:
    """The teacher's classes, each marked with the placement of this book or video when it's already there."""
    mine = await teacher_courses.mine(user.get("email"))
    names = {c["key"]: c["name"] for c in yorkville.courses()}
    held = {}
    for p in await placements(mine, False):
        if p["kind"] == kind and _key_of(kind, p["ref"]) == key:
            held[p["course"]] = p
    order = [c["key"] for c in sorted(yorkville.courses(), key=_subject_rank)]
    return [{"key": k, "name": names.get(k, k), "holds": held.get(k)}
            for k in sorted(mine, key=lambda k: order.index(k) if k in order else len(order))]


def _guard_teacher(request):
    user = auth.current_user(request)
    if not is_teacher(user):
        return None, JSONResponse({"error": "Class shelves are filled by the class's teachers."}, status_code=403)
    if not db.ready():
        return None, JSONResponse({"error": UNAVAILABLE}, status_code=503)
    return user, None


async def class_items_add(request):
    user, denied = _guard_teacher(request)
    if denied:
        return denied
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    out = await place(user, request.path_params["course"], b.get("kind"), b.get("ref") if isinstance(b.get("ref"), dict) else {},
                      b.get("audience") or "students", str(b.get("label") or ""))
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"item": out}, status_code=201)


async def class_item_change(request):
    user, denied = _guard_teacher(request)
    if denied:
        return denied
    try:
        item_id = uuid.UUID(request.path_params["id"])
    except ValueError:
        return JSONResponse({"error": "That item isn't on a class shelf."}, status_code=404)
    if request.method == "DELETE":
        out = await take_off(user, item_id)
    else:
        try:
            b = await request.json()
        except Exception:  # noqa: BLE001
            b = {}
        if b.get("audience") not in ("students", "teachers"):
            return JSONResponse({"error": "Say who should see it."}, status_code=400)
        out = await set_audience(user, item_id, b["audience"])
    if out is None or out is False:
        return JSONResponse({"error": "That item isn't on a class shelf."}, status_code=404)
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=403)
    return JSONResponse({"ok": True, **(out if isinstance(out, dict) else {})})


async def class_holding_get(request):
    user, denied = _guard_teacher(request)
    if denied:
        return denied
    kind = request.query_params.get("kind") or ""
    if kind in ("upload", "link", "resource"):
        return JSONResponse({"classes": await class_holding(user, kind, request.query_params.get("key") or "")})
    ref = {"slug": request.query_params.get("key")} if kind == "book" else {
        "item_id": request.query_params.get("key"), "guid": request.query_params.get("guid") or None,
        "start": float(request.query_params["start"]) if request.query_params.get("start") else None}
    return JSONResponse({"classes": await class_holding(user, kind, _key_of(kind, ref))})
