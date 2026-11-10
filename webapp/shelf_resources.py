"""Prep Room resources on shelves (decision 0029, phase 4).

A teacher puts a resource on their own shelf or on a class shelf. A class shelf keeps a copy of the resource's newest
saved version (encrypted in `shelf_texts`), refreshed inside the same transaction as every save
(`prep.add_version`), so the class always sees the newest version and keeps the last one when the resource or its
teacher's account goes. Students read the student copy alone (`prep_catalog.student_copy`): never an answer key or
teaching notes, and an answer key, or a resource that is nothing but teacher-only parts, goes to a class's teachers
alone. A copy made in the Prep Room is on no shelf until the teacher puts it in place of the original."""
from __future__ import annotations

import re
import uuid

from starlette.responses import JSONResponse

from webapp import auth, db, extraction, generator, prep_catalog, yorkville

UPSERT_TEXT = """insert into shelf_texts (item_id, nonce, ct, words) values ($1, $2, $3, $4)
                 on conflict (item_id) do update set nonce = excluded.nonce, ct = excluded.ct, words = excluded.words"""


def kind_word(format_id: str) -> str:
    """'Quiz / Test' -> 'Quiz', as the Prep Room names a kind in its lists."""
    name = (generator.FORMATS.get(format_id) or {}).get("name") or "Resource"
    return re.split(r" / | \(", name)[0].strip() or "Resource"


def keys_only(format_id: str, document: str) -> bool:
    """True when a resource has nothing for students: an answer key, or only teacher-only parts and headings."""
    if format_id == "answer_key":
        return True
    body = re.sub(r"(?m)^#{1,6}\s.*$", "", prep_catalog.student_copy(document or ""))
    return not body.strip()


def _course_names() -> dict:
    return {c["key"]: c["name"] for c in yorkville.courses()}


async def snapshot(uid: uuid.UUID, resource_id) -> dict | str:
    """The resource as a class shelf will hold it: its ref, title and newest version. A message when it can't go."""
    try:
        rid = uuid.UUID(str(resource_id))
    except ValueError:
        return "That resource isn't in your Prep Room."
    row = await db.fetchrow("select id, format_id, title, settings from prep_resources where id = $1 and user_id = $2", rid, uid)
    if not row:
        return "That resource isn't in your Prep Room."
    v = await db.fetchrow("select n, document from prep_versions where resource_id = $1 order by n desc limit 1", rid)
    if not v:
        return "That resource has no saved version yet."
    return {"title": row["title"], "document": v["document"],
            "ref": {"resource_id": str(rid), "format_id": row["format_id"], "kind_word": kind_word(row["format_id"]),
                    "n": v["n"], "keys_only": keys_only(row["format_id"], v["document"]),
                    "band": (row["settings"] or {}).get("grade_band") or "secondary"}}


async def store_text(item_id, document: str, conn=None) -> None:
    nonce, ct = extraction.encrypt_text(document)
    await (conn or db).execute(UPSERT_TEXT, item_id, nonce, ct, len(document.split()))


async def refresh(conn, resource_id, n: int, document: str) -> None:
    """Every class shelf that holds this resource now holds this version: called inside add_version's transaction."""
    rows = await conn.fetch("""select id, ref from shelf_items where kind = 'resource' and course_key is not null
                                and ref->>'resource_id' = $1""", str(resource_id))
    for r in rows:
        ref = dict(r["ref"] or {})
        ref.update(n=n, keys_only=keys_only(ref.get("format_id") or "", document))
        await conn.execute("update shelf_items set ref = $2 where id = $1", r["id"], ref)
        await store_text(r["id"], document, conn)


async def rename(resource_id, title: str) -> None:
    """A renamed resource is renamed on its class shelves, without the "(copy)" a copy is first given."""
    await db.execute("""update shelf_items set label = $2 where kind = 'resource' and course_key is not null
                         and ref->>'resource_id' = $1""", str(resource_id), _shelf_title(title))


def _shelf_title(title: str) -> str:
    return re.sub(r"\s*\(copy\)\s*$", "", title or "").strip()[:200] or (title or "")[:200]


async def on_shelves(resource_ids: list) -> dict[str, list[dict]]:
    """{resource id: [{item, course, name, audience, n}]} for the class shelves that hold each resource."""
    ids = [str(i) for i in resource_ids if i]
    if not ids:
        return {}
    rows = await db.fetch("""select id, course_key, audience, ref from shelf_items where kind = 'resource'
                              and course_key is not null and ref->>'resource_id' = any($1::text[]) order by added_at""", ids)
    names, out = _course_names(), {}
    for r in rows:
        out.setdefault(r["ref"]["resource_id"], []).append(
            {"item": str(r["id"]), "course": r["course_key"], "name": names.get(r["course_key"], r["course_key"]),
             "audience": r["audience"], "n": (r["ref"] or {}).get("n")})
    return out


async def mine(uid: uuid.UUID) -> list[dict]:
    """The resources a teacher put on their own shelf, newest first, with where each lives in the Prep Room."""
    rows = await db.fetch("""select r.id, r.unit_id, r.format_id, r.title from shelf_items s
                               join prep_resources r on r.id::text = s.ref->>'resource_id' and r.user_id = s.user_id
                              where s.user_id = $1 and s.kind = 'resource' order by s.added_at desc""", uid)
    return [{"id": str(r["id"]), "title": r["title"], "kind_word": kind_word(r["format_id"]),
             "href": (f"/generate/unit/{r['unit_id']}/r/{r['id']}" if r["unit_id"] else f"/generate/r/{r['id']}")} for r in rows]


async def on_my_shelf(uid: uuid.UUID, resource_id) -> bool:
    return bool(await db.fetchval("select 1 from shelf_items where user_id = $1 and kind = 'resource' and ref->>'resource_id' = $2",
                                  uid, str(resource_id)))


def _guard(request):
    user = auth.current_user(request)
    if not (user and (auth.is_teacher(user) or auth.is_admin(user))):
        return None, JSONResponse({"error": "The Prep Room is for teachers."}, status_code=403)
    if not db.ready():
        return None, JSONResponse({"error": "Your shelves can't be reached right now. Try again in a minute."}, status_code=503)
    return user, None


async def own_shelf(request):
    """PUT puts a Prep Room resource on the teacher's own shelf; DELETE takes it off. The resource stays in the unit."""
    user, denied = _guard(request)
    if denied:
        return denied
    uid = uuid.UUID(user["id"])
    try:
        rid = uuid.UUID(request.path_params["id"])
    except ValueError:
        return JSONResponse({"error": "That resource isn't in your Prep Room."}, status_code=404)
    if request.method == "DELETE":
        await db.execute("delete from shelf_items where user_id = $1 and kind = 'resource' and ref->>'resource_id' = $2", uid, str(rid))
        return JSONResponse({"ok": True})
    title = await db.fetchval("select title from prep_resources where id = $1 and user_id = $2", rid, uid)
    if title is None:
        return JSONResponse({"error": "That resource isn't in your Prep Room."}, status_code=404)
    if not await db.fetchval("select 1 from shelf_items where user_id = $1 and kind = 'resource' and ref->>'resource_id' = $2", uid, str(rid)):
        await db.execute("insert into shelf_items (user_id, kind, ref, label, added_by) values ($1, 'resource', $2, $3, $1)",
                         uid, {"resource_id": str(rid)}, title[:200])
    return JSONResponse({"ok": True})


async def replace(user, copy_id, original_id) -> list[str] | str:
    """Put a copy on every class shelf that holds the original, in its place. The original stays in its unit. Called
    the other way round, it is the Undo."""
    from webapp import shelves
    uid = uuid.UUID(user["id"])
    try:
        cid, oid = uuid.UUID(str(copy_id)), uuid.UUID(str(original_id))
    except ValueError:
        return "That resource isn't in your Prep Room."
    snap = await snapshot(uid, cid)
    if isinstance(snap, str):
        return snap
    if not await db.fetchval("select 1 from prep_resources where id = $1 and user_id = $2", oid, uid):
        return "That resource isn't in your Prep Room."
    rows = await db.fetch("""select id, course_key, audience from shelf_items where kind = 'resource' and course_key is not null
                              and ref->>'resource_id' = $1""", str(oid))
    if not rows:
        return "The original isn't on a class shelf."
    names = _course_names()
    done = []
    for r in rows:
        if not await shelves._teaches(user, r["course_key"]):
            continue
        audience = "teachers" if snap["ref"]["keys_only"] else r["audience"]
        await db.execute("update shelf_items set ref = $2, label = $3, audience = $4 where id = $1",
                         r["id"], snap["ref"], _shelf_title(snap["title"]), audience)
        await store_text(r["id"], snap["document"])
        done.append(names.get(r["course_key"], r["course_key"]))
    return done or "Only a teacher of that class can change its shelf."


async def replace_route(request):
    user, denied = _guard(request)
    if denied:
        return denied
    try:
        b = await request.json()
    except Exception:  # noqa: BLE001
        b = {}
    out = await replace(user, request.path_params["id"], b.get("original"))
    if isinstance(out, str):
        return JSONResponse({"error": out}, status_code=400)
    return JSONResponse({"shelves": out})
