"""The Prep Room's saved work (decision 0026): a teacher's units, the sources each one draws on, and
every resource made in it, kept with its versions so a reload or a bad revision loses nothing.

Teacher-only (decision 0007). Every row belongs to the teacher who made it and every query is scoped
to that account. The maker can read them, as /privacy says. Rows go with the account (decision 0013).

The text of an uploaded document or a fetched link is the teacher's own copy of someone's work. It is
kept encrypted (the Living Library's tier-1 key, webapp/extraction.py), is never shared, and is
decrypted only to draft from it.
"""
from __future__ import annotations

import logging
import re
import uuid

from starlette.responses import JSONResponse

from webapp import auth, db

logger = logging.getLogger("study-bible-web.prep")

KINDS = ("book", "outline", "passage", "library", "upload", "link")
GRADE_BANDS = ("primary", "middle", "secondary", "undergraduate", "seminary")   # generator.GRADE_BANDS
MAX_UNITS = 300
MAX_SOURCES = 24
MAX_OBJECTIVES = 16
MAX_VERSIONS = 40
MAX_DOC_CHARS = 400_000
MAX_SOURCE_WORDS = 60_000
MAX_TITLE = 160
MAX_NOTES = 4_000

UNAVAILABLE = "Saving is unavailable right now. Try again in a minute."


# ---------------------------------------------------------------------------------------- helpers
def _clean(s, limit: int) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:limit]


def _uuid(s) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(s))
    except (TypeError, ValueError):
        return None


def _plain(row) -> dict:
    out = {}
    for k, v in dict(row).items():
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif hasattr(v, "isoformat"):
            v = v.isoformat()
        elif isinstance(v, (bytes, bytearray, memoryview)):
            continue
        out[k] = v
    return out


def clean_objectives(items) -> list[dict]:
    """Picked spine objectives, kept with their grade, complexity and anchors so drafts get them."""
    out = []
    for o in (items or [])[:MAX_OBJECTIVES]:
        if not isinstance(o, dict) or not o.get("id"):
            continue
        anchors = o.get("a") or o.get("anchors") or {}
        out.append({
            "id": _clean(o["id"], 80),
            "t": _clean(o.get("t") or o.get("text"), 600),
            "g": o.get("g"),
            "c": o.get("c"),
            "path": _clean(o.get("path"), 300),
            "a": {k: [_clean(x, 200) for x in (anchors.get(k) or [])][:8]
                  for k in ("scripture", "confessions", "greek", "standards") if anchors.get(k)},
        })
    return out


def clean_ref(kind: str, ref: dict) -> dict | None:
    """Only the fields each kind of source needs, so a client can't store anything else."""
    ref = ref if isinstance(ref, dict) else {}
    if kind == "book":
        slug = _clean(ref.get("slug"), 200)
        if not slug:
            return None
        cov = ref.get("coverage") if isinstance(ref.get("coverage"), dict) else {}
        coverage = {}
        if cov.get("through"):
            coverage = {"through": int(cov["through"])}
        elif isinstance(cov.get("range"), list) and len(cov["range"]) == 2:
            coverage = {"range": [int(cov["range"][0]), int(cov["range"][1])]}
        elif isinstance(cov.get("chapters"), list):
            coverage = {"chapters": [int(x) for x in cov["chapters"]][:200]}
        out = {"slug": slug, "coverage": coverage}
        if coverage.get("through") and ref.get("through_title"):
            out["through_title"] = _clean(ref["through_title"], 200)   # what the unit pane shows
        return out
    if kind == "outline":
        key = _clean(ref.get("key"), 120)
        parts = [_clean(p, 120) for p in (ref.get("parts") or [])][:60]
        return {"key": key, "parts": parts} if key else None
    if kind == "passage":
        r = _clean(ref.get("ref"), 120)
        return {"ref": r, "translation": _clean(ref.get("translation"), 12) or "ESV"} if r else None
    if kind == "library":
        item = _uuid(ref.get("item_id"))
        if not item:
            return None
        out = {"item_id": str(item)}
        if isinstance(ref.get("excerpts"), list):
            out["excerpts"] = [str(e) for e in ref["excerpts"] if _uuid(e)][:40]
        return out
    if kind == "upload":
        shelf = _uuid(ref.get("shelf"))
        return {"filename": _clean(ref.get("filename"), 200), "format": _clean(ref.get("format"), 10),
                **({"shelf": str(shelf)} if shelf else {})}
    if kind == "link":
        url = _clean(ref.get("url"), 1000)
        return {"url": url} if url.startswith(("http://", "https://")) else None
    return None


def _guard(request):
    """(account id, None) for a signed-in teacher with the database up, else (None, response)."""
    user = auth.current_user(request)
    if not auth.is_teacher(user):                       # decision 0007
        return None, JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    if not db.ready():
        return None, JSONResponse({"error": UNAVAILABLE}, status_code=503)
    uid = _uuid(user.get("id"))
    if not uid:
        return None, JSONResponse({"error": "Sign in again to save your work."}, status_code=401)
    return uid, None


async def _body(request) -> dict:
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        return {}
    return b if isinstance(b, dict) else {}


def _not_found(what="That"):
    return JSONResponse({"error": f"{what} isn't in your Prep Room."}, status_code=404)


# ------------------------------------------------------------------------------------------ units
async def list_units(uid: uuid.UUID) -> list[dict]:
    rows = await db.fetch(
        """select u.id, u.title, u.course_key, u.grade_band, u.updated_at, u.created_at,
                  (select count(*) from prep_sources s where s.unit_id = u.id) as n_sources,
                  (select count(*) from prep_resources r where r.unit_id = u.id) as n_resources
             from prep_units u where u.user_id = $1 and u.parent_id is null and u.kind = 'unit'
            order by u.updated_at desc""", uid)   # a course's containers live on its own page (0032)
    return [_plain(r) for r in rows]


async def create_unit(uid: uuid.UUID, title: str, course_key: str | None, grade_band: str) -> dict | None:
    n = await db.fetchval("select count(*) from prep_units where user_id = $1 and parent_id is null and kind = 'unit'", uid)
    if n >= MAX_UNITS:
        return None
    row = await db.fetchrow(
        """insert into prep_units (user_id, title, course_key, grade_band)
           values ($1, $2, $3, $4) returning id, title, course_key, grade_band, notes, objectives,
                                             created_at, updated_at""",
        uid, title, course_key, grade_band)
    return _plain(row)


async def get_unit(uid: uuid.UUID, unit_id: uuid.UUID) -> dict | None:
    row = await db.fetchrow(
        """select id, title, course_key, grade_band, notes, objectives, created_at, updated_at
             from prep_units where id = $1 and user_id = $2""", unit_id, uid)
    if not row:
        return None
    unit = _plain(row)
    unit["sources"] = [_plain(r) for r in await db.fetch(
        """select id, kind, ref, label, words, position, added_at from prep_sources
            where unit_id = $1 order by position, added_at""", unit_id)]
    unit["resources"] = await list_resources(uid, unit_id)
    return unit


async def update_unit(uid: uuid.UUID, unit_id: uuid.UUID, fields: dict) -> bool:
    sets, args = [], [unit_id, uid]
    for col, val in fields.items():
        args.append(val)
        sets.append(f"{col} = ${len(args)}")
    if not sets:
        return True
    status = await db.execute(
        f"update prep_units set {', '.join(sets)}, updated_at = now() where id = $1 and user_id = $2", *args)
    return status.endswith(" 1")


async def delete_unit(uid: uuid.UUID, unit_id: uuid.UUID) -> bool:
    status = await db.execute("delete from prep_units where id = $1 and user_id = $2", unit_id, uid)
    return status.endswith(" 1")


async def _touch(unit_id) -> None:
    if unit_id:
        await db.execute("update prep_units set updated_at = now() where id = $1", unit_id)


# ---------------------------------------------------------------------------------------- sources
# What makes two sources the same, now that a passage or a moment can be added to a unit from any page.
SAME_SOURCE = {"book": "slug", "outline": "key", "passage": "ref", "library": "item_id", "link": "url",
               "upload": "shelf"}   # an upload from a shelf; a file uploaded to the unit itself may repeat


def merged_excerpts(old: dict, new: dict) -> dict | None:
    """A Living Library item already in the unit, with the new moments joined to it; None when nothing changes.
    No excerpts means the whole item, which already holds every moment."""
    before, adding = old.get("excerpts"), new.get("excerpts")
    if not before:
        return None
    if not adding:
        return {"item_id": old["item_id"]}
    joined = list(dict.fromkeys(before + adding))[:40]
    return None if joined == before else {"item_id": old["item_id"], "excerpts": joined}


async def _merge_source(same, kind: str, ref: dict) -> dict | str:
    """A second add of the same source: moments join the item already there; anything else is refused plainly.
    The reply carries the earlier ref, so an undo can put it back."""
    old = same["ref"] or {}
    joined = merged_excerpts(old, ref) if kind == "library" else None
    if joined is None:
        if kind == "library" and ref.get("excerpts"):
            return ("That moment is already in this unit." if old.get("excerpts")
                    else f"All of {same['label']} is already in this unit, so its moments are too.")
        return f"{same['label']} is already in this unit."
    row = await db.fetchrow("""update prep_sources set ref = $2 where id = $1
                               returning id, kind, ref, label, words, position, added_at""", same["id"], joined)
    await _touch(same["unit_id"])
    return {**_plain(row), "merged": True, "before": old}


async def add_source(uid: uuid.UUID, unit_id: uuid.UUID, kind: str, ref: dict, label: str,
                     text: str | None = None) -> dict | None | str:
    """The new source, None when the unit isn't the teacher's, or a message when it can't be added."""
    owner = await db.fetchval("select user_id from prep_units where id = $1", unit_id)
    if owner != uid:
        return None
    key = SAME_SOURCE.get(kind)
    if key and ref.get(key):
        same = await db.fetchrow("select id, unit_id, ref, label from prep_sources where unit_id = $1 and kind = $2 and ref->>$3 = $4",
                                 unit_id, kind, key, str(ref[key]))
        if same:
            return await _merge_source(same, kind, ref)
    n = await db.fetchval("select count(*) from prep_sources where unit_id = $1", unit_id)
    if n >= MAX_SOURCES:
        return f"A unit holds up to {MAX_SOURCES} sources. Remove one to add another."
    nonce = ct = None
    words = None
    if text is not None:
        from webapp import extraction
        words = len(text.split())
        if words > MAX_SOURCE_WORDS:
            text = " ".join(text.split()[:MAX_SOURCE_WORDS])
            words = MAX_SOURCE_WORDS
        nonce, ct = extraction.encrypt_text(text)
    row = await db.fetchrow(
        """insert into prep_sources (unit_id, kind, ref, label, words, position, text_nonce, text_ct)
           values ($1, $2, $3, $4, $5, $6, $7, $8)
           returning id, kind, ref, label, words, position, added_at""",
        unit_id, kind, ref, label, words, int(n), nonce, ct)
    await _touch(unit_id)
    return _plain(row)


async def remove_source(uid: uuid.UUID, source_id: uuid.UUID) -> bool:
    unit_id = await db.fetchval(
        """delete from prep_sources s using prep_units u
            where s.id = $1 and s.unit_id = u.id and u.user_id = $2 returning s.unit_id""", source_id, uid)
    await _touch(unit_id)
    return unit_id is not None


async def update_source(uid: uuid.UUID, source_id: uuid.UUID, ref: dict, label: str | None) -> bool:
    status = await db.execute(
        """update prep_sources s set ref = $3, label = coalesce($4, s.label) from prep_units u
            where s.id = $1 and s.unit_id = u.id and u.user_id = $2""", source_id, uid, ref, label)
    return status.endswith(" 1")


async def sources_for_draft(uid: uuid.UUID, unit_id: uuid.UUID) -> list[dict]:
    """What one draft draws on. A container in a course takes its own sources, its ancestors' and the shelf
    items on its passage (course_routes.draft_sources, decision 0032); a plain unit takes its own."""
    from webapp import course_routes
    course = await course_routes.draft_sources(uid, unit_id)
    return course if course is not None else await own_sources(uid, unit_id)


async def own_sources(uid: uuid.UUID, unit_id: uuid.UUID) -> list[dict]:
    """The unit's own sources with any stored text decrypted."""
    rows = await db.fetch(
        """select s.id, s.kind, s.ref, s.label, s.words, s.text_nonce, s.text_ct from prep_sources s
             join prep_units u on u.id = s.unit_id
            where s.unit_id = $1 and u.user_id = $2 order by s.position, s.added_at""", unit_id, uid)
    out = []
    for r in rows:
        src = {"id": str(r["id"]), "kind": r["kind"], "ref": r["ref"], "label": r["label"]}
        if r["text_ct"] is not None:
            from webapp import extraction
            try:
                src["text"] = extraction.decrypt_text(r["text_nonce"], r["text_ct"])
            except Exception:  # noqa: BLE001
                logger.exception("could not decrypt a prep source")
                src["text"] = ""
        out.append(src)
    return out


# -------------------------------------------------------------------------------------- resources
async def list_resources(uid: uuid.UUID, unit_id: uuid.UUID | None = None, quick: bool = False) -> list[dict]:
    where, args = "r.user_id = $1", [uid]
    if unit_id:
        args.append(unit_id)
        where += f" and r.unit_id = ${len(args)}"
    elif quick:
        where += " and r.unit_id is null"
    rows = await db.fetch(
        f"""select r.id, r.unit_id, r.format_id, r.title, r.settings, r.created_at, r.updated_at,
                   (select max(n) from prep_versions v where v.resource_id = r.id) as latest
              from prep_resources r where {where} order by r.updated_at desc limit 300""", *args)
    return [_plain(r) for r in rows]


async def create_resource(uid: uuid.UUID, unit_id: uuid.UUID | None, format_id: str, title: str,
                          settings: dict) -> str | None:
    if unit_id:
        owner = await db.fetchval("select user_id from prep_units where id = $1", unit_id)
        if owner != uid:
            return None
    rid = await db.fetchval(
        """insert into prep_resources (user_id, unit_id, format_id, title, settings)
           values ($1, $2, $3, $4, $5) returning id""", uid, unit_id, format_id, title, settings)
    await _touch(unit_id)
    return str(rid)


async def add_version(uid: uuid.UUID, resource_id: uuid.UUID, document: str, origin: str,
                      instruction: str | None = None, drew_on: list | None = None,
                      report: dict | None = None) -> int | None:
    """Save the next version of a resource; the oldest go once it holds MAX_VERSIONS. None when the
    resource isn't the teacher's."""
    document = (document or "")[:MAX_DOC_CHARS]
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "select unit_id from prep_resources where id = $1 and user_id = $2 for update", resource_id, uid)
            if not row:
                return None
            unit_id = row["unit_id"]
            n = (await conn.fetchval("select coalesce(max(n), 0) from prep_versions where resource_id = $1",
                                     resource_id)) + 1
            await conn.execute(
                """insert into prep_versions (resource_id, n, origin, instruction, document, drew_on, report)
                   values ($1, $2, $3, $4, $5, $6, $7)""",
                resource_id, n, origin, (instruction or None) and instruction[:2000], document,
                drew_on or [], report)
            await conn.execute("delete from prep_versions where resource_id = $1 and n <= $2",
                               resource_id, n - MAX_VERSIONS)
            from webapp import shelf_resources   # a class always sees the newest version (decision 0029)
            await shelf_resources.refresh(conn, resource_id, n, document)
            await conn.execute("update prep_resources set updated_at = now() where id = $1", resource_id)
            if unit_id:
                await conn.execute("update prep_units set updated_at = now() where id = $1", unit_id)
    return n


async def get_resource(uid: uuid.UUID, resource_id: uuid.UUID, n: int | None = None) -> dict | None:
    row = await db.fetchrow(
        """select id, unit_id, format_id, title, settings, created_at, updated_at
             from prep_resources where id = $1 and user_id = $2""", resource_id, uid)
    if not row:
        return None
    res = _plain(row)
    res["versions"] = [_plain(v) for v in await db.fetch(
        """select n, origin, instruction, created_at, length(document) as chars from prep_versions
            where resource_id = $1 order by n desc""", resource_id)]
    want = n if n is not None else (res["versions"][0]["n"] if res["versions"] else None)
    if want is not None:
        v = await db.fetchrow(
            "select n, origin, document, drew_on, report, created_at from prep_versions "
            "where resource_id = $1 and n = $2", resource_id, want)
        res["version"] = _plain(v) if v else None
    return res


async def update_resource(uid: uuid.UUID, resource_id: uuid.UUID, title: str | None,
                          unit_id: uuid.UUID | None, move: bool) -> bool:
    if move and unit_id:
        owner = await db.fetchval("select user_id from prep_units where id = $1", unit_id)
        if owner != uid:
            return False
    status = await db.execute(
        """update prep_resources set title = coalesce($3, title),
                  unit_id = case when $4 then $5 else unit_id end, updated_at = now()
            where id = $1 and user_id = $2""", resource_id, uid, title, move, unit_id)
    return status.endswith(" 1")


async def delete_resource(uid: uuid.UUID, resource_id: uuid.UUID) -> bool:
    status = await db.execute("delete from prep_resources where id = $1 and user_id = $2", resource_id, uid)
    return status.endswith(" 1")


# ------------------------------------------------------------------------------------------ routes
async def holding(uid: uuid.UUID, kind: str, key: str) -> dict:
    """{unit id: {"source": id, "ref": ref}} for this teacher's units that already hold a source, so "Add to a
    unit" can check them, the way a "Save to" list checks the playlists that hold a video."""
    field = SAME_SOURCE.get(kind)
    if not field or not key:
        return {}
    rows = await db.fetch(
        """select s.unit_id, s.id, s.ref from prep_sources s join prep_units u on u.id = s.unit_id
            where u.user_id = $1 and s.kind = $2 and s.ref->>$3 = $4""", uid, kind, field, key)
    return {str(r["unit_id"]): {"source": str(r["id"]), "ref": r["ref"]} for r in rows}


async def units_list(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    units = await list_units(uid)
    q = request.query_params
    if q.get("kind"):                       # ?kind=passage&key=John 7:15 marks the units that already hold it
        held = await holding(uid, q["kind"], _clean(q.get("key"), 1000))
        for u in units:
            if u["id"] in held:
                u["holds"] = held[u["id"]]
    quick = await list_resources(uid, quick=True)
    await _mark_shelves(quick)
    return JSONResponse({"units": units, "quick": quick})


async def _mark_shelves(resources: list[dict]) -> None:
    """Each resource says which class shelves hold it, so the Prep Room can name them before a change."""
    from webapp import shelf_resources
    held = await shelf_resources.on_shelves([r["id"] for r in resources])
    for r in resources:
        r["shelves"] = held.get(str(r["id"]), [])


async def unit_create(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    b = await _body(request)
    title = _clean(b.get("title"), MAX_TITLE)
    if not title:
        return JSONResponse({"error": "Give the unit a name."}, status_code=400)
    band = b.get("grade_band") if b.get("grade_band") in GRADE_BANDS else "secondary"
    unit = await create_unit(uid, title, _clean(b.get("course_key"), 80) or None, band)
    if unit is None:
        return JSONResponse({"error": f"The Prep Room holds up to {MAX_UNITS} units. Delete an old one first."},
                            status_code=400)
    unit.update(sources=[], resources=[])
    return JSONResponse({"unit": unit}, status_code=201)


async def unit_get(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    unit_id = _uuid(request.path_params["id"])
    unit = unit_id and await get_unit(uid, unit_id)
    if unit:
        await _mark_shelves(unit["resources"])
        from webapp import course_routes          # a course container also draws on what's above and its passage
        feed = await course_routes.draft_sources(uid, unit_id, labels_only=True)
        if feed is not None:
            unit["course_draws"] = [s["label"] for s in feed]
    return JSONResponse({"unit": unit}) if unit else _not_found("That unit")


async def unit_update(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    unit_id = _uuid(request.path_params["id"])
    b = await _body(request)
    fields = {}
    if "title" in b:
        title = _clean(b["title"], MAX_TITLE)
        if not title:
            return JSONResponse({"error": "Give the unit a name."}, status_code=400)
        fields["title"] = title
    if "course_key" in b:
        fields["course_key"] = _clean(b["course_key"], 80) or None
    if b.get("grade_band") in GRADE_BANDS:
        fields["grade_band"] = b["grade_band"]
    if "notes" in b:
        fields["notes"] = str(b.get("notes") or "")[:MAX_NOTES]
    if "objectives" in b:
        fields["objectives"] = clean_objectives(b.get("objectives"))
    if not unit_id or not await update_unit(uid, unit_id, fields):
        return _not_found("That unit")
    return JSONResponse({"ok": True})


async def unit_delete(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    unit_id = _uuid(request.path_params["id"])
    return JSONResponse({"ok": True}) if unit_id and await delete_unit(uid, unit_id) else _not_found("That unit")


async def source_add(request):
    """Add a source to a unit. Books, outlines, passages and Living Library items arrive as JSON
    references; uploads and links go through `prep_files.py`, which reads them first."""
    uid, denied = _guard(request)
    if denied:
        return denied
    unit_id = _uuid(request.path_params["id"])
    b = await _body(request)
    kind = b.get("kind")
    if kind == "shelf":                       # an upload or a link from the Living Library: the unit keeps its own copy
        return await _from_shelf(request, uid, unit_id, b)
    if kind not in ("book", "outline", "passage", "library"):
        return JSONResponse({"error": "Unknown kind of source."}, status_code=400)
    ref = clean_ref(kind, b.get("ref"))
    label = _clean(b.get("label"), 200)
    if not ref or not label:
        return JSONResponse({"error": "That source is missing what it needs."}, status_code=400)
    if not unit_id:
        return _not_found("That unit")
    out = await add_source(uid, unit_id, kind, ref, label)
    if out is None:
        return _not_found("That unit")
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"source": out}, status_code=201)


async def _from_shelf(request, uid, unit_id, b):
    from webapp import shelf_docs
    item = _uuid((b.get("ref") or {}).get("item_id")) if isinstance(b.get("ref"), dict) else None
    row = await shelf_docs.readable_by(auth.current_user(request), item) if item else None
    text = await shelf_docs.text_of(item) if row else None
    if not unit_id or not row or text is None:
        return JSONResponse({"error": "That isn't on your shelves."}, status_code=404)
    ref = row["ref"] or {}
    if row["kind"] == "link":
        kind, cref = "link", clean_ref("link", {"url": ref.get("url")})
    else:
        kind, cref = "upload", clean_ref("upload", {"filename": ref.get("filename") or row["label"], "format": ref.get("format") or "txt",
                                                    "shelf": str(ref.get("origin") or item)})
    out = await add_source(uid, unit_id, kind, cref, _clean(b.get("label"), 200) or row["label"], text=text)
    if out is None:
        return _not_found("That unit")
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"source": out}, status_code=201)


async def source_update(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    source_id = _uuid(request.path_params["id"])
    b = await _body(request)
    kind = b.get("kind")
    ref = clean_ref(kind, b.get("ref")) if kind in ("book", "outline", "library") else None
    if not source_id or not ref:
        return JSONResponse({"error": "That change can't be made to this source."}, status_code=400)
    label = _clean(b.get("label"), 200) or None
    return JSONResponse({"ok": True}) if await update_source(uid, source_id, ref, label) else _not_found("That source")


async def source_remove(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    source_id = _uuid(request.path_params["id"])
    return JSONResponse({"ok": True}) if source_id and await remove_source(uid, source_id) else _not_found("That source")


async def resource_get(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    rid = _uuid(request.path_params["id"])
    n = request.query_params.get("n")
    res = rid and await get_resource(uid, rid, int(n) if n and n.isdigit() else None)
    if not res:
        return _not_found("That resource")
    from webapp import shelf_resources
    res["shelves"] = (await shelf_resources.on_shelves([rid])).get(str(rid), [])
    res["on_my_shelf"] = await shelf_resources.on_my_shelf(uid, rid)
    orig = _uuid((res.get("settings") or {}).get("copy_of"))
    if orig:                                  # a copy says where its original is, so it can take its place
        o = await get_resource(uid, orig)
        if o:
            res["copy_of"] = {"id": str(orig), "title": o["title"],
                              "shelves": (await shelf_resources.on_shelves([orig])).get(str(orig), [])}
    return JSONResponse({"resource": res})


async def copy_resource(uid: uuid.UUID, resource_id: uuid.UUID, unit_id: uuid.UUID | None = None) -> dict | None:
    """Make a copy (decision 0029): the newest version, as version 1 of a new resource on no shelf. In the same unit
    its title says it's a copy. Sent to another of the teacher's units (decision 0031), it keeps its title."""
    res = await get_resource(uid, resource_id)
    v = (res or {}).get("version")
    if not v:
        return None
    same = unit_id is None or str(unit_id) == str(res.get("unit_id"))
    if not same and not await get_unit(uid, unit_id):
        return None
    title = (res["title"] + (" (copy)" if same else ""))[:MAX_TITLE]
    target = (_uuid(res["unit_id"]) if res.get("unit_id") else None) if same else unit_id
    new = await create_resource(uid, target, res["format_id"], title,
                                {**(res.get("settings") or {}), "copy_of": str(resource_id)})
    if not new:
        return None
    await add_version(uid, _uuid(new), v["document"], "restore", instruction=f"Copied from “{res['title']}”, version {v['n']}",
                      drew_on=v.get("drew_on"), report=v.get("report"))
    return {"id": str(new), "title": title, "unit_id": str(target) if target else None, "format_id": res["format_id"]}


async def resource_copy(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    rid = _uuid(request.path_params["id"])
    b = await _body(request)
    unit = _uuid(b.get("unit")) if isinstance(b, dict) and b.get("unit") else None   # another unit (decision 0031)
    out = rid and await copy_resource(uid, rid, unit)
    return JSONResponse({"resource": out}, status_code=201) if out else _not_found("That resource")


async def resource_save(request):
    """Save a version the teacher made by hand, or bring back an earlier one (it becomes the newest)."""
    uid, denied = _guard(request)
    if denied:
        return denied
    rid = _uuid(request.path_params["id"])
    b = await _body(request)
    origin = b.get("origin") if b.get("origin") in ("edit", "restore") else "edit"
    if origin == "restore":
        old = rid and await get_resource(uid, rid, int(b.get("from_n") or 0))
        document = ((old or {}).get("version") or {}).get("document")
        note = f"Brought back version {int(b.get('from_n') or 0)}"
    else:
        document, note = b.get("document"), None
    if not rid or not isinstance(document, str) or not document.strip():
        return JSONResponse({"error": "There's nothing to save."}, status_code=400)
    n = await add_version(uid, rid, document, origin, instruction=note)
    return JSONResponse({"n": n}) if n else _not_found("That resource")


async def resource_update(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    rid = _uuid(request.path_params["id"])
    b = await _body(request)
    title = _clean(b.get("title"), MAX_TITLE) or None if "title" in b else None
    move = "unit_id" in b
    target = _uuid(b.get("unit_id")) if move else None
    if not rid or not await update_resource(uid, rid, title, target, move):
        return _not_found("That resource")
    if title:
        from webapp import shelf_resources
        await shelf_resources.rename(rid, title)
    return JSONResponse({"ok": True})


async def resource_delete(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    rid = _uuid(request.path_params["id"])
    return JSONResponse({"ok": True}) if rid and await delete_resource(uid, rid) else _not_found("That resource")
