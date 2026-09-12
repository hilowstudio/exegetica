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
        "ready": (row.get("status") == "extracted"),  # study materials already built
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
        """select li.extraction_id, e.kind, e.title, e.creator, e.cover_url, e.source_url, e.source_meta, e.status
           from library_items li join library_extractions e on e.id = li.extraction_id
           where li.user_id = $1 order by li.added_at desc""",
        _uid(user),
    )
    return JSONResponse({"items": [_to_client(r) for r in rows]})


async def catalog_search(request):
    """Search the SEEDED shared catalog — books already built into study materials — so a
    teacher can add ready work in one click instead of re-extracting. Empty q → browse all."""
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    q = (request.query_params.get("q") or "").strip()
    rows = await db.fetch(
        """select e.id, e.title, e.creator, e.cover_url,
                  (select count(*) from library_sections   s where s.extraction_id=e.id) secs,
                  (select count(*) from library_objectives  o where o.extraction_id=e.id and o.user_id is null) objs
           from library_extractions e
           where e.status='extracted' and e.kind='book'
             and ($1 = '' or e.title ilike '%'||$1||'%' or e.creator ilike '%'||$1||'%')
           order by e.title limit 40""",
        q,
    )
    return JSONResponse({"catalog": [
        {"id": str(r["id"]), "type": "book", "title": r["title"] or "", "sub": r["creator"] or "",
         "cover": r["cover_url"], "sections": r["secs"], "objectives": r["objs"], "ready": True}
        for r in rows]})


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

    # Books key by the SAME identity as Build/seed (title|author-surname, or ISBN) so a
    # teacher adding a title lands on the already-seeded catalog row (guaranteed reuse),
    # not a divergent one. Video/podcast keep their strong-id key.
    if kind == "book":
        from webapp import extraction
        dedup_key = extraction.book_dedup_key(
            {"title": item.get("title"), "authors": [item.get("sub") or ""], "isbn": item.get("isbn")})
    else:
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
           returning id, kind, title, creator, cover_url, source_url, source_meta, status""",
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


# --------------------------------------------------------------------------- #
# Borderline-review queue: when two same-tier (upload) copies of a book score
# within _PROMOTE_MARGIN, neither auto-wins — a teacher decides which is canonical.
# Reviewers see quality SIGNALS only, never the private source text.
# --------------------------------------------------------------------------- #
def _is_teacher(user) -> bool:
    return bool(user) and (user or {}).get("role") == "teacher"


async def reviews_list(request):
    """Pending borderline copies awaiting a promote/keep-private decision (teacher-only)."""
    user = auth.current_user(request)
    if not _is_teacher(user):
        return JSONResponse({"error": "teacher access required"}, status_code=403)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    rows = await db.fetch(
        """select e.id as extraction_id, e.title, e.creator,
                  e.canonical_source, e.canonical_tier, e.quality_score as incumbent_quality,
                  st.user_id as candidate_user, st.quality_score as candidate_quality,
                  st.source_format, st.char_count, st.acquisition, st.updated_at
             from library_source_texts st
             join library_extractions e on e.id = st.extraction_id
            where st.review_status = 'pending'
            order by st.updated_at desc""",
    )
    out = [{
        "extraction_id": str(r["extraction_id"]), "title": r["title"], "creator": r["creator"],
        "incumbent": {"source": r["canonical_source"], "tier": r["canonical_tier"],
                      "quality": r["incumbent_quality"]},
        "candidate": {"user_id": str(r["candidate_user"]), "quality": r["candidate_quality"],
                      "format": r["source_format"], "chars": r["char_count"],
                      "acquisition": r["acquisition"], "uploaded_at": r["updated_at"].isoformat()},
    } for r in rows]
    return JSONResponse({"reviews": out})


async def _review_target(request):
    """Shared validation for promote/reject: teacher + a pending candidate. Returns
    (user, exid, cand_uid) or a JSONResponse error."""
    user = auth.current_user(request)
    if not _is_teacher(user):
        return JSONResponse({"error": "teacher access required"}, status_code=403)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        body = await request.json()
        exid = uuid.UUID((body.get("extraction_id") or "").strip())
        cand_uid = uuid.UUID((body.get("user_id") or "").strip())
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "extraction_id and user_id required"}, status_code=400)
    st = await db.fetchrow(
        "select review_status, quality_score from library_source_texts where extraction_id=$1 and user_id=$2",
        exid, cand_uid,
    )
    if not st or st["review_status"] != "pending":
        return JSONResponse({"error": "no pending review for that copy"}, status_code=404)
    return (user, exid, cand_uid, st["quality_score"])


async def review_promote(request):
    """Promote a borderline copy to canonical and rebuild the shared derivative from it."""
    t = await _review_target(request)
    if isinstance(t, JSONResponse):
        return t
    _user, exid, cand_uid, cand_q = t
    from webapp import inngest_app

    ex = await db.fetchrow("select title, creator from library_extractions where id=$1", exid)
    await db.execute(
        """update library_extractions set
             canonical_source=$2, canonical_tier=2, quality_score=$3,
             verify_verdict='accepted', status='extracting', updated_at=now()
           where id=$1""",
        exid, f"upload:{cand_uid}", cand_q,
    )
    # This copy wins; sibling pending candidates for the same book lose.
    await db.execute(
        "update library_source_texts set review_status='promoted', updated_at=now() where extraction_id=$1 and user_id=$2",
        exid, cand_uid,
    )
    await db.execute(
        "update library_source_texts set review_status='rejected', updated_at=now() "
        "where extraction_id=$1 and user_id<>$2 and review_status='pending'",
        exid, cand_uid,
    )
    try:
        await inngest_app.trigger_rederive(
            title=ex["title"], author=ex["creator"] or None, extraction_id=exid, user_id=cand_uid,
        )
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "could not queue rebuild"}, status_code=502)
    return JSONResponse({"extraction_id": str(exid), "status": "extracting", "promoted": True})


async def review_reject(request):
    """Keep a borderline copy private; leave the current canonical derivative untouched."""
    t = await _review_target(request)
    if isinstance(t, JSONResponse):
        return t
    _user, exid, cand_uid, _q = t
    await db.execute(
        "update library_source_texts set review_status='rejected', updated_at=now() where extraction_id=$1 and user_id=$2",
        exid, cand_uid,
    )
    return JSONResponse({"extraction_id": str(exid), "rejected": True})
