"""
Per-user state storage (Neon). Endpoints for signed-in users only; anonymous
users never call these (the client falls back to localStorage).

Each user's Scripture Memory (and, later, chats) is stored as a single JSON blob
keyed to their user id. The client owns the data shape and its ids — the server
just returns and replaces the whole blob.
"""
from __future__ import annotations

import uuid

from starlette.responses import JSONResponse

from webapp import auth, db

_EMPTY_MEMORY = {"verses": [], "folders": []}
_EMPTY_CHATS = {"chats": []}


def _uid(user) -> uuid.UUID:
    return uuid.UUID(user["id"])


async def memory_get(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    row = await db.fetchrow("select state from memory_state where user_id=$1", _uid(user))
    state = (row["state"] if row and row["state"] else None) or dict(_EMPTY_MEMORY)
    state.setdefault("verses", [])
    state.setdefault("folders", [])
    return JSONResponse(state)


async def memory_put(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    state = {
        "verses": body.get("verses") or [],
        "folders": body.get("folders") or [],
    }
    await db.execute(
        """insert into memory_state (user_id, state, updated_at)
           values ($1, $2, now())
           on conflict (user_id) do update set state=excluded.state, updated_at=now()""",
        _uid(user), state,
    )
    return JSONResponse({"ok": True})


async def chat_get(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    row = await db.fetchrow("select state from chat_state where user_id=$1", _uid(user))
    state = (row["state"] if row and row["state"] else None) or dict(_EMPTY_CHATS)
    state.setdefault("chats", [])
    return JSONResponse(state)


async def chat_put(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    state = {"chats": body.get("chats") or []}
    await db.execute(
        """insert into chat_state (user_id, state, updated_at)
           values ($1, $2, now())
           on conflict (user_id) do update set state=excluded.state, updated_at=now()""",
        _uid(user), state,
    )
    return JSONResponse({"ok": True})
