"""Moments in the Living Library's videos and podcast episodes (decision 0026): the published transcript when
one exists (webapp/transcripts.py, shared), and each teacher's saved excerpts (private): a time range, the
words spoken there, and a note. A unit's draft gets them through prep_draft._library_item. Teacher-only."""
from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import asyncio
import logging
import time

from starlette.responses import JSONResponse

from webapp import auth, db, metrics, transcripts, usage

logger = logging.getLogger("study-bible-web.excerpts")
_TASKS: set = set()

NO_TRANSCRIPT = {
    "video": "This video has no transcript yet.",
    "podcast": "This show publishes no transcript for this episode.",
}
MAKE_NOTE = ("Gemini, Google's AI model, can write one in a minute or two. It is kept for every teacher who adds "
             "this {kind}. Until then you can save moments by their times, with a note or the words you hear.")
FAILED = "The transcript didn't finish. Try again later."
STALE_MINUTES = 15       # a job running longer than this is taken to have died, and may be started again


def _youtube_id(url: str | None) -> str | None:
    try:
        u = urlparse(url or "")
    except ValueError:
        return None
    host = (u.hostname or "").lower()
    if host.endswith("youtu.be"):
        return u.path.strip("/")[:11] or None
    if host.endswith("youtube.com"):
        if u.path.startswith(("/embed/", "/shorts/", "/live/")):
            return u.path.split("/")[2][:11]
        return (parse_qs(u.query).get("v") or [None])[0]
    return None


def link_at(item: dict, start: float) -> str | None:
    """A link that opens the video at the moment (YouTube's t=)."""
    vid = _youtube_id(item.get("source_url"))
    return f"https://www.youtube.com/watch?v={vid}&t={int(start)}s" if vid else None


def _key(item: dict, episode: str | None) -> str | None:
    if item["kind"] == "video":
        vid = _youtube_id(item["source_url"])
        return f"yt:{vid}" if vid else None
    return f"ep:{item['id']}:{episode}" if episode else None


async def _item(uid: uuid.UUID, extraction_id: uuid.UUID) -> dict | None:
    """A video or podcast on this teacher's shelf."""
    row = await db.fetchrow(
        """select e.id, e.kind, e.title, e.source_url from library_items li
             join library_extractions e on e.id = li.extraction_id
            where li.user_id = $1 and e.id = $2 and e.kind in ('video', 'podcast')""", uid, extraction_id)
    return dict(row) if row else None


async def _transcript(key: str | None) -> dict | None:
    if not key:
        return None
    row = await db.fetchrow("select segments, source from library_transcripts where key = $1", key)
    return {"segments": row["segments"], "source": row["source"]} if row else None


async def for_item(uid: uuid.UUID, extraction_id: uuid.UUID, ids: list[str] | None) -> list[dict]:
    """The teacher's excerpts of an item for a draft (all, or the chosen ones), oldest place first."""
    rows = await db.fetch(
        """select id, episode_title, start_s, end_s, quote, note from library_excerpts
            where user_id = $1 and extraction_id = $2 order by episode_title nulls first, start_s""",
        uid, extraction_id)
    keep = set(ids or [])
    out = []
    for r in rows:
        if keep and str(r["id"]) not in keep:
            continue
        at = f'{transcripts.stamp(r["start_s"])}–{transcripts.stamp(r["end_s"])}'
        if r["episode_title"]:
            at = f'{r["episode_title"]}, {at}'
        text = " ".join(x for x in ((f'"{r["quote"]}"' if r["quote"] else ""), (f'Note: {r["note"]}' if r["note"] else "")) if x)
        out.append({"at": at, "text": text or "(no words saved)"})
    return out


async def transcript_for_draft(item: dict) -> str | None:
    """A video's whole transcript as stamped lines (a podcast's episodes come through their excerpts)."""
    t = await _transcript(_key(item, None)) if item.get("kind") == "video" else None
    return transcripts.as_text(t["segments"]) if t else None


# ----------------------------------------------------------------------------------------- routes
def _guard(request):
    user = auth.current_user(request)
    if not auth.is_teacher(user):
        return None, JSONResponse({"error": "The Living Library is for teachers."}, status_code=403)
    if not db.ready():
        return None, JSONResponse({"error": "Saving is unavailable right now. Try again in a minute."}, status_code=503)
    try:
        return uuid.UUID(str(user.get("id"))), None
    except ValueError:
        return None, JSONResponse({"error": "Sign in again."}, status_code=401)


def _plain(r) -> dict:
    return {"id": str(r["id"]), "episode_key": r["episode_key"], "episode_title": r["episode_title"],
            "start": r["start_s"], "end": r["end_s"], "quote": r["quote"], "note": r["note"]}


async def moments(request):
    """GET: an item's transcript (for a video, or the episode named by ?episode=) and the teacher's excerpts."""
    uid, denied = _guard(request)
    if denied:
        return denied
    try:
        item = await _item(uid, uuid.UUID(request.path_params["id"]))
    except ValueError:
        item = None
    if not item:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    episode = request.query_params.get("episode")
    t = await _transcript(_key(item, episode))
    rows = await db.fetch("select * from library_excerpts where user_id = $1 and extraction_id = $2 "
                          "order by episode_title nulls first, start_s", uid, item["id"])
    job = None if t else await _job(_key(item, episode))
    return JSONResponse({"kind": item["kind"], "transcript": t, "excerpts": [
        _plain(r) | {"link": link_at(item, r["start_s"])} for r in rows],
        "missing": None if t else NO_TRANSCRIPT[item["kind"]], "job": job,
        "make": None if t else MAKE_NOTE.format(kind="video" if item["kind"] == "video" else "episode")})


async def episode_list(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    try:
        item = await _item(uid, uuid.UUID(request.path_params["id"]))
    except ValueError:
        item = None
    if not item or item["kind"] != "podcast" or not item["source_url"]:
        return JSONResponse({"error": "That isn't a podcast on your shelf."}, status_code=404)
    try:
        eps = await transcripts.episodes(item["source_url"])
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "The show's feed didn't answer. Try again later."}, status_code=502)
    return JSONResponse({"episodes": [{k: e[k] for k in ("guid", "title", "date", "duration")} |
                                      {"has_transcript": bool(e["transcripts"])} for e in eps]})


async def fetch_transcript(request):
    """POST {episode?}: look for a published transcript now and keep it for everyone who adds the item."""
    uid, denied = _guard(request)
    if denied:
        return denied
    try:
        item = await _item(uid, uuid.UUID(request.path_params["id"]))
        body = await request.json()
    except Exception:  # noqa: BLE001
        item, body = None, {}
    if not item:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    episode = (body or {}).get("episode")
    key = _key(item, episode)
    if not key:
        return JSONResponse({"error": "Choose an episode first."}, status_code=400)
    found = None
    title = item["title"]
    if item["kind"] == "video":
        found = await transcripts.youtube(key[3:])
    else:
        try:   # the transcript links come from the feed itself, never from the request
            ep = next((e for e in await transcripts.episodes(item["source_url"]) if e["guid"] == episode), None)
        except Exception:  # noqa: BLE001
            ep = None
        if ep:
            title = ep["title"]
            found = await transcripts.episode_transcript(ep["transcripts"])
    if not found:
        if not (body or {}).get("make"):
            return JSONResponse({"transcript": None, "missing": NO_TRANSCRIPT[item["kind"]], "job": await _job(key)})
        return JSONResponse(await _start(uid, item, key, episode))
    segs, source = found
    await db.execute("""insert into library_transcripts (key, title, segments, source) values ($1, $2, $3, $4)
                        on conflict (key) do update set segments = excluded.segments, source = excluded.source,
                                                        fetched_at = now()""", key, title, segs, source)
    return JSONResponse({"transcript": {"segments": segs, "source": source}})


# ------------------------------------------------------------------------- Gemini transcription jobs (0028)
async def _job(key: str | None) -> dict | None:
    if not key:
        return None
    row = await db.fetchrow("select status, error, extract(epoch from now() - updated_at) / 60 as age "
                            "from library_transcribe_jobs where key = $1", key)
    if not row or (row["status"] == "running" and row["age"] > STALE_MINUTES):
        return None
    return {"status": row["status"], "error": row["error"]}


async def _start(uid: uuid.UUID, item: dict, key: str, episode: str | None) -> dict:
    """Start Gemini on a transcript, unless one is already being made or the teacher is at today's limit."""
    job = await _job(key)
    if job and job["status"] == "running":
        return {"transcript": None, "job": job}
    capped = await usage.transcribe_check(str(uid))
    if capped:
        return {"transcript": None, "missing": capped, "job": None}
    await db.execute("""insert into library_transcribe_jobs (key, status) values ($1, 'running')
                        on conflict (key) do update set status = 'running', error = null, updated_at = now()""", key)
    payload = {"key": key, "kind": item["kind"], "user_id": str(uid), "title": item["title"],
               "video_id": key[3:] if item["kind"] == "video" else None,
               "feed_url": item["source_url"] if item["kind"] == "podcast" else None, "guid": episode}
    try:
        from webapp import app as appmod
        if appmod._inngest_serve_app is None:
            raise RuntimeError("no Inngest here")
        from webapp import inngest_app
        await inngest_app.trigger_transcribe(payload)
    except Exception:  # noqa: BLE001  (no queue: run it here; a restart mid-run leaves a job that goes stale)
        task = asyncio.create_task(run(**payload))
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
    return {"transcript": None, "job": {"status": "running", "error": None}}


async def run(key: str, kind: str, user_id: str, title: str | None = None, video_id: str | None = None,
              feed_url: str | None = None, guid: str | None = None) -> dict:
    """Write one transcript with Gemini and keep it; record its cost in /ops and against the daily caps. Never
    raises: a failure is kept on the job row as a plain sentence, so a retry can't charge twice."""
    t0, stats = time.monotonic(), {"model_req": transcripts.MODEL}
    try:
        if kind == "video":
            segs, source, used = await transcripts.gemini_youtube(video_id)
        else:
            ep = next((e for e in await transcripts.episodes(feed_url) if e["guid"] == guid), None)
            if not ep or not ep["audio"]:
                raise transcripts.TranscribeError("That episode isn't in the show's feed any more.")
            title = ep["title"]
            segs, source, used = await transcripts.gemini_audio(ep["audio"], ep["duration"])
        usd = transcripts.cost(used)
        stats.update(outcome="complete", input=used["in"], output=used["out"], est_usd=usd)
        await db.execute("""insert into library_transcripts (key, title, segments, source) values ($1, $2, $3, $4)
                            on conflict (key) do update set segments = excluded.segments, source = excluded.source,
                                                            fetched_at = now()""", key, title, segs, source)
        await db.execute("delete from library_transcribe_jobs where key = $1", key)
        return {"status": "done", "segments": len(segs), "usd": round(usd, 4)}
    except Exception as e:  # noqa: BLE001
        message = str(e) if isinstance(e, transcripts.TranscribeError) else FAILED
        if not isinstance(e, transcripts.TranscribeError):
            logger.exception("transcription failed")
        stats.setdefault("outcome", "provider_error")
        try:
            await db.execute("update library_transcribe_jobs set status = 'failed', error = $2, updated_at = now() "
                             "where key = $1", key, message)
        except Exception:  # noqa: BLE001
            logger.exception("could not mark the transcription failed")
        return {"status": "failed", "error": message}
    finally:
        metrics.record(metrics.from_stats("library:transcribe", "server", stats,
                                          outcome=stats.get("outcome") or "cancelled",
                                          duration_ms=(time.monotonic() - t0) * 1000))
        await usage.transcribe_add(user_id, float(stats.get("est_usd") or 0))


async def save_excerpt(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    try:
        item = await _item(uid, uuid.UUID(request.path_params["id"]))
        b = await request.json()
    except Exception:  # noqa: BLE001
        item, b = None, {}
    if not item:
        return JSONResponse({"error": "That isn't on your shelf."}, status_code=404)
    start, end = transcripts.parse_stamp(str(b.get("start", ""))), transcripts.parse_stamp(str(b.get("end", "")))
    if start is None or end is None or end < start or end - start > 3600:
        return JSONResponse({"error": "Give a start and an end, such as 2:14 and 3:05."}, status_code=400)
    episode = str(b.get("episode") or "")[:300] or None
    if item["kind"] == "podcast" and not episode:
        return JSONResponse({"error": "Choose an episode first."}, status_code=400)
    t = await _transcript(_key(item, episode))
    quote = transcripts.cut(t["segments"], start, end) if t else str(b.get("quote") or "").strip()[:2000]
    note = str(b.get("note") or "").strip()[:1000]
    n = await db.fetchval("select count(*) from library_excerpts where user_id = $1", uid)
    if n >= 2000:
        return JSONResponse({"error": "You have saved 2,000 moments. Delete some to save more."}, status_code=400)
    row = await db.fetchrow(
        """insert into library_excerpts (user_id, extraction_id, episode_key, episode_title, start_s, end_s, quote, note)
           values ($1, $2, $3, $4, $5, $6, $7, $8) returning *""",
        uid, item["id"], episode, str(b.get("episode_title") or "")[:300] or None, start, end, quote or None, note or None)
    return JSONResponse({"excerpt": _plain(row) | {"link": link_at(item, start)}}, status_code=201)


async def delete_excerpt(request):
    uid, denied = _guard(request)
    if denied:
        return denied
    try:
        status = await db.execute("delete from library_excerpts where id = $1 and user_id = $2",
                                  uuid.UUID(request.path_params["id"]), uid)
    except ValueError:
        status = ""
    return JSONResponse({"ok": True}) if status.endswith(" 1") else JSONResponse(
        {"error": "That moment isn't yours to delete."}, status_code=404)
