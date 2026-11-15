"""Watching a class shelf's video inside Exegetica (decision 0034).

A video on a class shelf opens a watch page (/watch/<shelf item>): its title, who made it, the player, the teacher's
note and any credit its owner asked for. A video whose owner allows it is played from Exegetica's own copy in R2 (the
browser gets a short-lived link to the file only after the access check). Any other video plays in YouTube's
privacy-enhanced player, which loads only when someone presses play. A clip starts at its second and stops at its end.
Nothing about what anyone watched is kept on the server (0002).
"""
from __future__ import annotations

import uuid

from starlette.responses import JSONResponse, RedirectResponse, Response

from webapp import auth, db, excerpts, r2, shell, shelves

LINK_SECONDS = 6 * 3600          # long enough for a class period and a paused video; short enough to be no lasting link
GONE = "That video isn't on your class shelves."


def _uuid(s: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(s))
    except (TypeError, ValueError):
        return None


async def placement(user, item_id: uuid.UUID | None) -> dict | None:
    """A video on one of this person's class shelves, with its catalog entry: a student's own classes and only what is
    placed for students, or a class a teacher teaches (the podcast player's rule, webapp/listen.py)."""
    if not user or not item_id or not db.ready():
        return None
    row = await db.fetchrow("""select s.id, s.course_key, s.audience, s.ref, s.label, e.id as video_id, e.title, e.creator,
                                      e.cover_url, e.source_url, e.source_meta
                                 from shelf_items s join library_extractions e on e.id::text = s.ref->>'item_id'
                                where s.id = $1 and s.course_key is not null and s.kind = 'video' and e.kind = 'video'""", item_id)
    if not row or row["course_key"] not in await shelves.classes_of(user):
        return None
    if not shelves.is_teacher(user) and row["audience"] != "students":
        return None
    return dict(row)


def hosted(meta: dict | None) -> dict | None:
    """Exegetica's own copy of a video, when there is one: {"key", "seconds", "length", "captions", ...}. Its still is the
    catalog cover, kept in R2 and served by /api/library/cover/<id>, so a shelf tile and the page show it from Exegetica."""
    h = (meta or {}).get("hosted")
    return h if isinstance(h, dict) and h.get("key") else None


def embed_url(source_url: str | None, start=None, end=None) -> str | None:
    """YouTube's privacy-enhanced player for a video Exegetica can't host, set to the clip."""
    vid = excerpts._youtube_id(source_url)
    if not vid:
        return None
    q = ["rel=0", "modestbranding=1", "playsinline=1", "autoplay=1"]
    if start is not None:
        q.append(f"start={int(start)}")
    if end is not None:
        q.append(f"end={int(end)}")
    return f"https://www.youtube-nocookie.com/embed/{vid}?" + "&".join(q)


def stamp(t) -> str:
    t = max(0, int(t or 0))
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


async def page(request):
    """The watch page for a video, or a clip of one, on a class shelf."""
    user = auth.current_user(request)
    row = await placement(user, _uuid(request.path_params.get("id")))
    if not row:
        return shell.for_others(request, "Living Library", GONE) if user else \
            shell.for_others(request, "Living Library", "It's on a class shelf in the Living Library.")
    ref, meta = row["ref"] or {}, row["source_meta"] or {}
    h = hosted(meta)
    start, end = ref.get("start"), ref.get("end")
    clip = start is not None and end is not None and end > start
    names = {c["key"]: c["name"] for c in shelves.courses_for(True)}
    sid = str(row["id"])
    return shell.page(request, "watch.html", title=row["label"] or row["title"] or "Video",
                      v={"id": sid, "title": row["label"] or row["title"], "maker": row["creator"] or "",
                         "length": (h or {}).get("length") or meta.get("meta") or "",
                         "course": names.get(row["course_key"], ""),
                         "hosted": bool(h), "src": f"/api/watch/{sid}/video" if h else None,
                         "poster": row["cover_url"] if h and (row["cover_url"] or "").startswith("/api/library/cover/") else None,
                         "captions": f"/api/watch/{sid}/captions" if h and h.get("captions") else None,
                         "embed": None if h else embed_url(row["source_url"], start, end),
                         "start": start, "end": end,
                         "clip": f"{stamp(start)}–{stamp(end)}" if clip else (f"from {stamp(start)}" if start else None),
                         "note": ref.get("note"), "quote": ref.get("quote"),
                         "credit": meta.get("credit") or "", "source_url": row["source_url"],
                         "site": None if h else _site(row["source_url"])})


def _site(url: str | None) -> str | None:
    """The owner's site for a video that plays only there (a jesusfilm.org scene page): its bare host name."""
    from urllib.parse import urlparse
    host = (urlparse(url or "").hostname or "").lower()
    if not host or excerpts._youtube_id(url) or urlparse(url).scheme not in ("http", "https"):
        return None
    return host[4:] if host.startswith("www.") else host


async def _file(request, part: str):
    row = await placement(auth.current_user(request), _uuid(request.path_params.get("id")))
    h = hosted((row or {}).get("source_meta"))
    key = (h.get("key") if part == "video" else h.get(part)) if h else None
    if not row or not h or not key or not r2.configured():
        return None, JSONResponse({"error": GONE}, status_code=404)
    return key, None


async def video(request):
    """GET /api/watch/<shelf item>/video: a short-lived link to Exegetica's copy, for the people whose shelf it is on."""
    key, err = await _file(request, "video")
    if err:
        return err
    return RedirectResponse(r2.presign_get(key, LINK_SECONDS), status_code=302, headers={"Cache-Control": "private, no-store"})


async def captions(request):
    """GET /api/watch/<shelf item>/captions: the captions, served from Exegetica itself so the player can read them."""
    key, err = await _file(request, "captions")
    if err:
        return err
    data = await r2.get_bytes_async(key)
    if data is None:
        return JSONResponse({"error": GONE}, status_code=404)
    return Response(data, media_type="text/vtt; charset=utf-8", headers={"Cache-Control": "private, max-age=3600"})
