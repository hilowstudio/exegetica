"""
Persisted Living Library shelf (Neon). Signed-in users only; anonymous visitors
keep the in-memory demo shelf client-side.

Adding a resource finds-or-creates the shared, deduped catalog row
(library_extractions) and links the user's shelf (library_items). The catalog row
holds the intrinsic metadata (shared); the shelf row is the per-teacher reference.
The catalog row's id is the client-facing item id, so it is stable across reloads
and shared across teachers who add the same resource.
"""
from __future__ import annotations

import re
import uuid
from urllib.parse import parse_qs, urlparse

from starlette.responses import JSONResponse

from webapp import auth, db

_DEFAULT_ACCENT = "#5b4b8a"


def _uid(user) -> uuid.UUID:
    return uuid.UUID(user["id"])


def _slug(*parts: str) -> str:
    s = "|".join((p or "").strip().lower() for p in parts)
    return re.sub(r"\s+", " ", s).strip("| ")


def _youtube_id(url: str | None) -> str | None:
    try:
        u = urlparse(url or "")
        host = (u.hostname or "").lower()
        if host.endswith("youtu.be"):
            return (u.path.lstrip("/") or "")[:20] or None
        if "youtube.com" in host:
            v = parse_qs(u.query).get("v")
            if v:
                return v[0][:20]
            m = re.search(r"/(?:embed|shorts)/([^/?]+)", u.path)
            if m:
                return m.group(1)[:20]
    except Exception:  # noqa: BLE001
        pass
    return None


def _dedup_key(kind: str, item: dict) -> str:
    """The real-world identity for de-duplication (see plan §3). Falls back to a
    title|creator slug when the strong id is missing."""
    if kind == "book":
        isbn = re.sub(r"[^0-9Xx]", "", item.get("isbn") or "")
        return isbn or "t:" + _slug(item.get("title"), item.get("sub"))
    if kind == "video":
        return _youtube_id(item.get("url")) or "t:" + _slug(item.get("title"), item.get("sub"))
    if kind == "podcast":
        return (item.get("feed") or "").strip() or "t:" + _slug(item.get("title"), item.get("sub"))
    return "t:" + _slug(item.get("title"), item.get("sub"))


def _to_client(row) -> dict:
    """Map a catalog row back to the shape library.html renders."""
    kind = row["kind"]
    meta = row["source_meta"] or {}
    it = {
        "id": str(row["extraction_id"]),
        "type": kind,
        "title": row["title"] or "",
        "sub": row["creator"] or "",
        "meta": meta.get("meta", ""),
        "accent": meta.get("accent", _DEFAULT_ACCENT),
    }
    if kind == "book":
        it["cover"] = row["cover_url"]
        it["isbn"] = meta.get("isbn")
    elif kind == "podcast":
        it["artwork"] = row["cover_url"]
        it["feed"] = row["source_url"]
    else:  # video
        it["thumbnail"] = row["cover_url"]
        it["url"] = row["source_url"]
    return it


async def shelf_get(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    rows = await db.fetch(
        """select li.extraction_id, e.kind, e.title, e.creator, e.cover_url, e.source_url, e.source_meta
           from library_items li join library_extractions e on e.id = li.extraction_id
           where li.user_id = $1 order by li.added_at desc""",
        _uid(user),
    )
    return JSONResponse({"items": [_to_client(r) for r in rows]})


async def shelf_add(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        item = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    kind = item.get("type")
    if kind not in ("book", "video", "podcast"):
        return JSONResponse({"error": "unsupported type"}, status_code=400)

    dedup_key = _dedup_key(kind, item)
    cover = item.get("cover") or item.get("artwork") or item.get("thumbnail")
    source_url = item.get("url") or item.get("feed")
    source_meta = {"meta": item.get("meta") or "", "accent": item.get("accent") or _DEFAULT_ACCENT}
    if item.get("isbn"):
        source_meta["isbn"] = item["isbn"]
    uid = _uid(user)

    # Find-or-create the shared catalog row. On conflict we do NOT overwrite the
    # existing metadata (it may be curated) — just touch updated_at and reuse it.
    ex = await db.fetchrow(
        """insert into library_extractions
             (kind, dedup_key, title, creator, cover_url, source_url, source_meta, seeded_by_user_id)
           values ($1, $2, $3, $4, $5, $6, $7, $8)
           on conflict (kind, dedup_key) do update set updated_at = now()
           returning id, kind, title, creator, cover_url, source_url, source_meta""",
        kind, dedup_key, item.get("title") or "", item.get("sub") or "",
        cover, source_url, source_meta, uid,
    )
    await db.execute(
        """insert into library_items (user_id, extraction_id) values ($1, $2)
           on conflict (user_id, extraction_id) do nothing""",
        uid, ex["id"],
    )
    row = dict(ex)
    row["extraction_id"] = ex["id"]
    return JSONResponse({"item": _to_client(row)})


async def shelf_remove(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        exid = uuid.UUID(request.path_params["id"])
    except (ValueError, KeyError):
        return JSONResponse({"error": "bad id"}, status_code=400)
    # Only unlinks the user's shelf; the shared catalog row is left intact.
    await db.execute("delete from library_items where user_id = $1 and extraction_id = $2", _uid(user), exid)
    return JSONResponse({"ok": True})


async def extract_request(request):
    """Queue a public-domain book extraction (Inngest). Find-or-creates the shared
    catalog row (so the client has an id to poll) and fires the event — unless the book
    is already extracted, in which case it's reused with no reprocessing."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    title = (body.get("title") or "").strip()
    author = (body.get("author") or "").strip() or None
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)

    from webapp import extraction, inngest_app

    dedup = extraction.book_dedup_key({"title": title, "authors": [author] if author else []})
    ex = await db.fetchrow(
        """insert into library_extractions (kind, dedup_key, title, creator, status, seeded_by_user_id)
           values ('book', $1, $2, $3, 'pending', $4)
           on conflict (kind, dedup_key) do update set
             status = case when library_extractions.status = 'extracted' then 'extracted' else 'pending' end,
             updated_at = now()
           returning id, status""",
        dedup, title, author or "", _uid(user),
    )
    exid = ex["id"]
    reused = ex["status"] == "extracted"
    if not reused:
        try:
            await inngest_app.trigger_extract(title, author, exid)
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "could not queue extraction"}, status_code=502)
    return JSONResponse({"extraction_id": str(exid), "status": ex["status"], "reused": reused})


async def extract_status(request):
    """Poll an extraction's status + counts (for the client to watch progress)."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        exid = uuid.UUID(request.path_params["id"])
    except (ValueError, KeyError):
        return JSONResponse({"error": "bad id"}, status_code=400)
    row = await db.fetchrow(
        """select e.status, e.error,
             (select count(*) from library_sections   s where s.extraction_id = e.id) sections,
             (select count(*) from library_objectives o where o.extraction_id = e.id and o.user_id is null) objectives,
             (select count(*) from library_alignments a where a.extraction_id = e.id) alignments,
             e.derivative->>'summary' summary
           from library_extractions e where e.id = $1""",
        exid,
    )
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(
        {
            "status": row["status"], "error": row["error"], "sections": row["sections"],
            "objectives": row["objectives"], "alignments": row["alignments"], "summary": row["summary"],
        }
    )


async def extraction_detail(request):
    """The full extraction result for display: derivative + community objectives (with
    their cited section) + spine alignments (with the node's readable name)."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        exid = uuid.UUID(request.path_params["id"])
    except (ValueError, KeyError):
        return JSONResponse({"error": "bad id"}, status_code=400)
    ex = await db.fetchrow("select status, us_clear, derivative from library_extractions where id=$1", exid)
    if not ex:
        return JSONResponse({"error": "not found"}, status_code=404)
    objs = await db.fetch(
        """select o.text, o.citation, s.number sec_num, s.title sec_title
           from library_objectives o left join library_sections s on s.id = o.section_id
           where o.extraction_id = $1 and o.user_id is null and o.status = 'accepted'
           order by s.position nulls first, o.created_at""",
        exid,
    )
    aligns = await db.fetch(
        """select a.spine_level, a.spine_node_id, n.name node_name, s.number sec_num
           from library_alignments a
           left join spine_nodes n on n.id = a.spine_node_id
           left join library_sections s on s.id = a.section_id
           where a.extraction_id = $1 and a.source = 'auto'
           order by (a.section_id is null) desc, a.spine_level""",
        exid,
    )
    d = ex["derivative"] or {}
    return JSONResponse(
        {
            "status": ex["status"], "us_clear": ex["us_clear"],
            "summary": d.get("summary"), "themes": d.get("themes"), "reading_level": d.get("reading_level"),
            "objectives": [
                {
                    "text": o["text"], "citation": o["citation"],
                    "section": (o["sec_title"] or (("Ch. " + o["sec_num"]) if o["sec_num"] else None)),
                }
                for o in objs
            ],
            "alignments": [
                {
                    "level": a["spine_level"], "node": a["node_name"] or a["spine_node_id"],
                    "code": a["spine_node_id"], "section": a["sec_num"],
                }
                for a in aligns
            ],
        }
    )


# --- upload path (in-copyright / accessibility): presign → PUT to R2 → complete ---
_MAX_UPLOAD_BYTES = 60 * 1024 * 1024
_UPLOAD_CT = {"epub": "application/epub+zip", "pdf": "application/pdf", "txt": "text/plain", "md": "text/markdown"}


async def upload_presign(request):
    """Return a presigned R2 PUT URL for a direct browser→bucket upload of a book file."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    from webapp import r2

    if not r2.configured():
        return JSONResponse({"error": "uploads not configured"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    fmt = (body.get("source_format") or "").lower().lstrip(".")
    try:
        size = int(body.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    if fmt not in _UPLOAD_CT:
        return JSONResponse({"error": "unsupported file type (epub, pdf, txt, md)"}, status_code=400)
    if size <= 0 or size > _MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "file too large (60 MB max)"}, status_code=400)
    key = f"uploads/{user['id']}/{uuid.uuid4().hex}.{fmt}"
    ct = _UPLOAD_CT[fmt]
    return JSONResponse({"upload_url": r2.presign_put(key, ct), "object_key": key, "content_type": ct})


async def upload_complete(request):
    """After the browser PUTs the file to R2: validate, find-or-create the catalog row,
    and queue the in-copyright extraction (tier-1 private text + shared derivative)."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    from webapp import extraction, inngest_app, r2

    if not r2.configured():
        return JSONResponse({"error": "uploads not configured"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    key = body.get("object_key") or ""
    title = (body.get("title") or "").strip()
    author = (body.get("author") or "").strip() or None
    acquisition = body.get("acquisition") or "owned"
    fmt = (body.get("source_format") or "").lower().lstrip(".")
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    if not key.startswith(f"uploads/{user['id']}/"):
        return JSONResponse({"error": "bad object key"}, status_code=400)
    if acquisition not in ("owned", "borrowed", "accessibility"):
        return JSONResponse({"error": "bad acquisition"}, status_code=400)
    if body.get("attested") is not True:
        return JSONResponse({"error": "attestation required"}, status_code=400)
    if not await r2.head_async(key):
        return JSONResponse({"error": "upload not found — try again"}, status_code=400)

    dedup = extraction.book_dedup_key({"title": title, "authors": [author] if author else []})
    ex = await db.fetchrow(
        """insert into library_extractions (kind, dedup_key, title, creator, status, seeded_by_user_id)
           values ('book', $1, $2, $3, 'pending', $4)
           on conflict (kind, dedup_key) do update set status='pending', updated_at=now()
           returning id""",
        dedup, title, author or "", _uid(user),
    )
    exid = ex["id"]
    try:
        await inngest_app.trigger_upload_extract(
            title=title, author=author, extraction_id=exid, r2_object_key=key,
            source_format=fmt or "epub", user_id=str(_uid(user)), acquisition=acquisition,
        )
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "could not queue extraction"}, status_code=502)
    return JSONResponse({"extraction_id": str(exid), "status": "pending"})
