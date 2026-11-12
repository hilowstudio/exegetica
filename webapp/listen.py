"""Listening to a podcast episode inside Exegetica (decision 0031).

A podcast episode on a class shelf opens a player page (/listen/<shelf item>): its title, show, description, the
audio, and the transcript when a teacher has had one made. A teacher also hears a single episode they kept, inside
the Living Library. The audio always comes through Exegetica: many episodes play through a host's tracking address
before the file, so the server fetches the audio and passes it on, and the host sees Exegetica's server, never the
student's device. Where a student stopped is kept in their own browser (static/js/listen.js), never here.
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import uuid
from urllib.parse import urljoin, urlparse

import httpx
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, StreamingResponse

from webapp import auth, db, shell, shelves

logger = logging.getLogger("study-bible-web.listen")

# The relay names itself generically: a podcast host learns a school's player asked, nothing about who.
_UA = {"User-Agent": "Exegetica/1.0 (a podcast player for a school)", "Accept-Encoding": "identity"}
_RANGE = re.compile(r"bytes=\d*-\d*")
_REDIRECTS = 8
NOT_REACHED = "The episode's audio couldn't be reached. Try again in a few minutes."
_AUDIO_TYPES = ("application/octet-stream", "binary/octet-stream", "video/mp4", "application/ogg")


async def _public(url: str) -> bool:
    """Only an address on the public internet: never this machine, Fly's private network, or a local one."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    host = u.hostname.lower()
    if host == "localhost" or host.endswith((".internal", ".local", ".localhost")):
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, u.port or (443 if u.scheme == "https" else 80))
    except OSError:
        return False
    for *_, sockaddr in infos:
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                or ip.is_unspecified):
            return False
    return True


async def relay(request, url: str | None):
    """Fetch the audio on the listener's behalf and pass it on, with the byte ranges a player asks for."""
    if not url:
        return JSONResponse({"error": NOT_REACHED}, status_code=404)
    headers = dict(_UA)
    rng = request.headers.get("range")
    if rng and _RANGE.fullmatch(rng.strip()):
        headers["Range"] = rng.strip()
    client = httpx.AsyncClient(timeout=httpx.Timeout(20.0, read=90.0), follow_redirects=False)
    resp = None
    try:
        for _ in range(_REDIRECTS):           # each hop is checked: a tracker's redirect can't reach inside
            if not await _public(url):
                raise ValueError("not a public address")
            resp = await client.send(client.build_request("GET", url, headers=headers), stream=True)
            location = resp.headers.get("location")
            if resp.status_code in (301, 302, 303, 307, 308) and location:
                await resp.aclose()
                resp, url = None, urljoin(url, location)
                continue
            break
        if resp is None or resp.status_code not in (200, 206):
            raise ValueError(f"status {resp.status_code if resp else 'redirects'}")
        kind = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not (kind.startswith("audio/") or kind in _AUDIO_TYPES):
            raise ValueError(f"not audio: {kind}")
    except Exception as e:  # noqa: BLE001
        logger.info("audio relay failed: %s", e)
        if resp is not None:
            await resp.aclose()
        await client.aclose()
        return JSONResponse({"error": NOT_REACHED}, status_code=502)
    out = {"Content-Type": kind if kind.startswith("audio/") else "audio/mpeg", "Accept-Ranges": "bytes",
           "Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"}
    for h in ("content-length", "content-range"):
        if resp.headers.get(h):
            out[h.title()] = resp.headers[h]

    async def close():
        await resp.aclose()
        await client.aclose()

    return StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, headers=out, background=BackgroundTask(close))


# ---------------------------------------------------------------------------------------- who may listen
async def placement(user, item_id: uuid.UUID | None) -> dict | None:
    """A podcast on one of this person's class shelves: a student's own classes and only what is placed for students,
    or a class a teacher teaches."""
    if not user or not item_id or not db.ready():
        return None
    row = await db.fetchrow("""select id, course_key, audience, ref, label from shelf_items
                                where id = $1 and course_key is not null and kind = 'podcast'""", item_id)
    if not row or row["course_key"] not in await shelves.classes_of(user):
        return None
    if not shelves.is_teacher(user) and row["audience"] != "students":
        return None
    return dict(row)


def _uuid(s: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(s))
    except (TypeError, ValueError):
        return None


async def audio(request):
    """GET /api/listen/<shelf item>/audio: a class shelf's episode, for the people whose shelf it is on."""
    row = await placement(auth.current_user(request), _uuid(request.path_params.get("id")))
    if not row:
        return JSONResponse({"error": "That isn't on your class shelves."}, status_code=404)
    return await relay(request, ((row["ref"] or {}).get("ep") or {}).get("audio"))


async def item_audio(request):
    """GET /api/library/item/<id>/audio: a single episode a teacher kept, heard in the Living Library."""
    user = auth.current_user(request)
    if not auth.is_teacher(user) or not db.ready():
        return JSONResponse({"error": "The Living Library is for teachers."}, status_code=403)
    item = _uuid(request.path_params.get("id"))
    row = await db.fetchrow("""select e.source_meta from library_items li join library_extractions e on e.id = li.extraction_id
                                where li.user_id = $1 and e.id = $2 and e.kind = 'podcast'""", _uuid(user.get("id")), item) if item else None
    ep = ((row["source_meta"] or {}).get("episode") or {}) if row else {}
    if not ep.get("audio"):
        return JSONResponse({"error": "That episode isn't on your shelf."}, status_code=404)
    return await relay(request, ep["audio"])


async def page(request):
    """The player page for a podcast episode, or a moment in one, on a class shelf."""
    from webapp import excerpts, transcripts
    user = auth.current_user(request)
    row = await placement(user, _uuid(request.path_params.get("id")))
    if not row:
        return shell.for_others(request, "Living Library", "That isn't on your class shelves.") if user else \
            shell.for_others(request, "Living Library", "It's on a class shelf in the Living Library.")
    ref = row["ref"] or {}
    ep = ref.get("ep") or {}
    t = await excerpts.episode_transcript(ep.get("feed"), ref.get("guid"))
    names = {c["key"]: c["name"] for c in shelves.courses_for(True)}
    lines = []
    if t:
        cur, start = [], None
        for s in t["segments"]:             # about one line every 30 seconds, as the moments panel shows it
            if start is None:
                start = s["start"]
            cur.append(s["text"])
            if s["end"] - start >= 30:
                lines.append({"t": start, "at": transcripts.stamp(start), "text": " ".join(cur)})
                cur, start = [], None
        if cur:
            lines.append({"t": start or 0, "at": transcripts.stamp(start or 0), "text": " ".join(cur)})
    start, end = ref.get("start"), ref.get("end")
    return shell.page(request, "listen.html", title=row["label"] or ep.get("title") or "Podcast",
                      ep={"id": str(row["id"]), "title": ep.get("title") or row["label"], "show": ep.get("show") or "",
                          "date": ep.get("date") or "", "length": ep.get("length") or "", "seconds": ep.get("seconds"),
                          "description": ep.get("description") or "", "artwork": ep.get("artwork"),
                          "start": start, "end": end,
                          "moment": f"{transcripts.stamp(start)}–{transcripts.stamp(end)}" if start is not None and end else None,
                          "note": ref.get("note"), "quote": ref.get("quote"),
                          "course": names.get(row["course_key"], "")},
                      lines=lines)
