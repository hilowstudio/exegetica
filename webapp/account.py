"""
Download my data and Delete my account (QSF DAT-01/02/03, HON-02; docs/decisions/0013-privacy-and-retention.md).

Export returns everything the server keeps for the signed-in account as one JSON file. Delete
removes it: first the account's upload originals in R2 (if any remain), then, in one
transaction, the account's id is scrubbed from the shared catalog and the account row is deleted,
which cascades to every per-account table (scripts/schema.sql). Shared catalog summaries that an
upload produced stay, with nothing left that names the account.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from starlette.responses import JSONResponse

from webapp import auth, db, r2

logger = logging.getLogger("study-bible-web.account")

CONFIRM = "delete"


def _plain(value):
    """JSON-safe copies of database values."""
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


async def collect(user_id: uuid.UUID) -> dict:
    """Everything the server keeps for one account."""
    async def one(sql):
        row = await db.fetchrow(sql, user_id)
        return _plain(dict(row)) if row else None

    async def many(sql):
        return [_plain(dict(r)) for r in await db.fetch(sql, user_id)]

    account = await one("select email, name, role, created_at, last_login_at from users where id = $1")
    memory = await one("select state, updated_at from memory_state where user_id = $1")
    chats = await one("select state, updated_at from chat_state where user_id = $1")
    covers = await one("select prefs, updated_at from cover_prefs where user_id = $1")
    return {
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "about": ("Everything Exegetica's server keeps for this account. Settings and any studies kept "
                  "only in a browser are stored in that browser and are not included."),
        "account": account,
        "scripture_memory": memory,
        "studies": chats,
        "reading_places": await many(
            "select book_slug, section_number, pages, updated_at from reading_state where user_id = $1 "
            "order by updated_at desc"),
        "cover_preferences": covers,
        "library_shelf": await many(
            """select e.kind, e.title, e.creator, li.notes, li.tags, li.added_at
               from library_items li join library_extractions e on e.id = li.extraction_id
               where li.user_id = $1 order by li.added_at"""),
        # The text of an uploaded book is the uploader's own copy; it is kept encrypted and is not
        # repeated here.
        "library_uploads": await many(
            """select e.title, e.creator, st.source_format, st.acquisition, st.char_count, st.created_at
               from library_source_texts st join library_extractions e on e.id = st.extraction_id
               where st.user_id = $1 order by st.created_at"""),
    }


async def remove(user_id: uuid.UUID, email: str | None) -> dict:
    """Delete one account and everything it owns. R2 first: if that fails nothing else is touched."""
    files = 0
    if r2.configured():
        files = await r2.delete_prefix_async(f"uploads/{user_id}/")
        files += await r2.delete_prefix_async(f"studio/{user_id}/")   # Image Studio (webapp/studio.py)
    async with db.pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "update library_extractions set canonical_source = 'upload:removed' where canonical_source = $1",
                f"upload:{user_id}")
            if email:
                await conn.execute("update cover_overrides set updated_by = null where lower(updated_by) = lower($1)",
                                   email)
            status = await conn.execute("delete from users where id = $1", user_id)
    return {"files": files, "account": status.endswith(" 1")}


async def export_data(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "Sign in to download your data."}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "The database is unavailable. Try again later."}, status_code=503)
    data = await collect(uuid.UUID(user["id"]))
    name = f"exegetica-data-{dt.date.today().isoformat()}.json"
    return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{name}"',
                                       "Cache-Control": "no-store"})


async def delete_account(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "Sign in to delete your account."}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "The database is unavailable. Nothing was deleted."}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    if (body or {}).get("confirm") != CONFIRM:
        return JSONResponse({"error": f'Type "{CONFIRM}" to confirm.'}, status_code=400)
    try:
        result = await remove(uuid.UUID(user["id"]), user.get("email"))
    except Exception:  # noqa: BLE001
        logger.exception("account deletion failed")
        return JSONResponse({"error": "The account could not be deleted. Try again later."}, status_code=500)
    logger.info("account deleted: files=%d", result["files"])   # no id, no email
    request.session.clear()
    return JSONResponse({"ok": True})
