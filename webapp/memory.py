"""
Scripture Memory — server-side ESV proxy for the client-only memory feature.

The memorization state (verses, folders, per-verse progress) lives entirely in the
browser's localStorage; there is no server persistence and no accounts. The only
thing the server does for this feature is proxy the ESV API, because the ESV key
(BIBLE_API_KEY) is a secret that must not reach the client. Two read-only endpoints:

    GET /api/memory/text?ref=John+3:16   -> {"reference": "...", "text": "..."}
    GET /api/memory/audio?ref=John+3:16  -> {"reference": "...", "audioUrl": "..."}
    GET /api/memory/texts?refs=a|b|c     -> {"texts": {ref: text}}, one ESV call for a whole list
    GET /api/memory/chapter?ref=...      -> the ESV chapter a verse sits in, verse by verse
    GET /api/memory/original?ref=...     -> the verse in Greek or Hebrew, word by word, from the library
    GET /api/memory/course               -> this week's memory verse in the John course, from its calendar
    GET /api/memory/cover?t=&m=          -> a house cover for a student's printed memory book

All are lookups. They store nothing about anyone (a signed-in student's verses are kept by
webapp/store.py, as before).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
import sqlite3
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from webapp import shell

ESV_TEXT_URL = "https://api.esv.org/v3/passage/text/"
ESV_AUDIO_URL = "https://api.esv.org/v3/passage/audio/"

# Verse-only text: no headings, verse numbers, footnotes, or reference line.
_TEXT_PARAMS = {
    "include-passage-references": "false",
    "include-verse-numbers": "false",
    "include-first-verse-numbers": "false",
    "include-footnotes": "false",
    "include-headings": "false",
    "include-short-copyright": "false",
    "include-passage-horizontal-lines": "false",
    "include-heading-horizontal-lines": "false",
    "indent-paragraphs": "0",
}


def _key() -> str | None:
    k = os.environ.get("BIBLE_API_KEY")
    return k.strip() if k else None


def _headers(key: str) -> dict:
    return {"Authorization": f"Token {key}"}


async def esv_text(reference: str) -> str:
    """Fetch clean ESV verse text for a reference. Raises on HTTP error."""
    key = _key()
    if not key:
        raise RuntimeError("BIBLE_API_KEY is not set on the server.")
    params = {"q": reference, **_TEXT_PARAMS}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(ESV_TEXT_URL, params=params, headers=_headers(key))
        r.raise_for_status()
        data = r.json()
    passages = data.get("passages") or []
    return passages[0].strip() if passages else ""


async def esv_audio_url(reference: str) -> str | None:
    """Resolve the (signed, temporary) ESV audio MP3 URL for a reference. The ESV
    audio endpoint 302-redirects to the MP3; we capture the redirect target."""
    key = _key()
    if not key:
        raise RuntimeError("BIBLE_API_KEY is not set on the server.")
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        r = await client.get(ESV_AUDIO_URL, params={"q": reference}, headers=_headers(key))
        if r.status_code in (301, 302, 303, 307, 308):
            return r.headers.get("location")
        # Some responses may already be the file; fall back to the final URL.
        if r.status_code == 200:
            return str(r.url)
        r.raise_for_status()
    return None


# ------------------------------------------------------------------ handlers
async def memory_page(request):
    return shell.page(request, "memory.html")


async def memory_text(request):
    ref = (request.query_params.get("ref") or "").strip()
    if len(ref) < 2:
        return JSONResponse({"error": "reference required"}, status_code=400)
    if not _key():
        return JSONResponse({"error": "BIBLE_API_KEY not set on server"}, status_code=503)
    try:
        text = await esv_text(ref)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        return JSONResponse({"error": f"ESV API returned {code}"}, status_code=502)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    return JSONResponse({"reference": ref, "text": text})


async def memory_audio(request):
    ref = (request.query_params.get("ref") or "").strip()
    if len(ref) < 2:
        return JSONResponse({"error": "reference required"}, status_code=400)
    if not _key():
        return JSONResponse({"error": "BIBLE_API_KEY not set on server"}, status_code=503)
    try:
        url = await esv_audio_url(ref)
    except httpx.HTTPStatusError as e:
        return JSONResponse({"error": f"ESV API returned {e.response.status_code}"}, status_code=502)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    return JSONResponse({"reference": ref, "audioUrl": url})


# ------------------------------------------------------------------ more lookups (the 2026-11-09 redesign)
_REF = re.compile(r"^\s*(.+?)\s+(\d+):(\d+)(?:\s*[-–]\s*(\d+))?\s*$")
_CHAPTERS: "OrderedDict[str, list[dict]]" = OrderedDict()   # recent chapters, so a class doesn't refetch one


def parse_ref(ref: str) -> tuple[str, int, int, int] | None:
    """'John 13:34-35' -> ('John', 13, 34, 35). None for anything else."""
    m = _REF.match(ref or "")
    if not m:
        return None
    v1 = int(m.group(3))
    return m.group(1).strip(), int(m.group(2)), v1, max(v1, int(m.group(4) or v1))


async def esv_texts(refs: list[str]) -> dict[str, str]:
    """Clean text for several references in one ESV call, in order. Falls back to one call each
    if ESV answers with a different number of passages."""
    key = _key()
    if not key:
        raise RuntimeError("BIBLE_API_KEY is not set on the server.")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(ESV_TEXT_URL, params={"q": ";".join(refs), **_TEXT_PARAMS}, headers=_headers(key))
        r.raise_for_status()
        passages = r.json().get("passages") or []
    if len(passages) == len(refs):
        return {ref: (p or "").strip() for ref, p in zip(refs, passages)}
    texts = await asyncio.gather(*(esv_text(ref) for ref in refs), return_exceptions=True)
    return {ref: (t if isinstance(t, str) else "") for ref, t in zip(refs, texts)}


async def esv_chapter(book: str, chapter: int) -> list[dict]:
    """A chapter's verses, [{"n": 1, "text": "..."}], from ESV with verse numbers, kept in memory."""
    name = f"{book} {chapter}"
    if name in _CHAPTERS:
        _CHAPTERS.move_to_end(name)
        return _CHAPTERS[name]
    key = _key()
    if not key:
        raise RuntimeError("BIBLE_API_KEY is not set on the server.")
    params = {"q": name, **_TEXT_PARAMS, "include-verse-numbers": "true", "include-first-verse-numbers": "true"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(ESV_TEXT_URL, params=params, headers=_headers(key))
        r.raise_for_status()
        passages = r.json().get("passages") or []
    parts = re.split(r"\[(\d+)\]", passages[0] if passages else "")
    verses = [{"n": int(parts[i]), "text": parts[i + 1].strip()} for i in range(1, len(parts) - 1, 2)]
    _CHAPTERS[name] = verses
    while len(_CHAPTERS) > 60:
        _CHAPTERS.popitem(last=False)
    return verses


def _bible_db() -> Path | None:
    from webapp import citations  # noqa: PLC0415
    b = citations.bible()
    return b.path if b else None


def _translit(t: str) -> str:
    """STEP's Hebrew transliteration marks syllables with dots and morphemes with slashes."""
    return re.sub(r"[./]", "", t or "").lower()


def original_words(ref: str) -> dict | None:
    """The verse in Greek or Hebrew from the library's tagged text: each word with its
    transliteration, gloss and lexicon definition. None where the library has nothing."""
    parsed = parse_ref(ref)
    path = _bible_db()
    if not parsed or not path:
        return None
    from studybible_mcp.database import StudyBibleDB  # noqa: PLC0415
    book, chapter, v1, v2 = parsed
    code = StudyBibleDB._normalize_reference(None, f"{book} {chapter}:{v1}").split(".")[0]
    refs = [f"{code}.{chapter}.{v}" for v in range(v1, v2 + 1)]
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as c:
        rows = c.execute(f"SELECT reference, word_data FROM verses WHERE reference IN ({','.join('?' * len(refs))})",
                         refs).fetchall()
        order = {r: i for i, r in enumerate(refs)}
        words, strongs = [], set()
        for reference, data in sorted(rows, key=lambda r: order.get(r[0], 0)):
            for w in json.loads(data or "[]"):
                # STEP marks morphemes with "/" and joins punctuation with "\" (אֶחְסָֽר\׃): the reader sees neither
                words.append({"verse": int(reference.rsplit(".", 1)[1]),
                              "word": (w.get("word") or "").replace("/", "").replace("\\", ""),
                              "translit": _translit(w.get("transliteration")),
                              "gloss": (w.get("gloss") or "").replace("/", ""), "strongs": w.get("strongs") or ""})
                strongs.add(w.get("strongs") or "")
        defs: dict[str, str] = {}
        plain = sorted({re.sub(r"[A-Z]$", "", s) for s in strongs if s})
        if plain:
            for st, short in c.execute(f"SELECT strongs, short_definition FROM lexicon WHERE strongs IN "
                                       f"({','.join('?' * len(plain))})", plain):
                defs[st] = (short or "").strip()
    if not words:
        return None
    for w in words:
        w["definition"] = defs.get(re.sub(r"[A-Z]$", "", w["strongs"]), "")
    hebrew = words[0]["strongs"].startswith("H")
    return {"reference": ref, "language": "Hebrew" if hebrew else "Greek", "dir": "rtl" if hebrew else "ltr",
            "words": words}


# The John course's memory verses come from its calendar: each anchor is planted on a lesson day.
_COURSE = Path(__file__).resolve().parent.parent / "docs" / "john" / "john-course-calendar.json"
try:
    _SCHOOL_TZ: dt.tzinfo = ZoneInfo("America/Chicago")
except Exception:  # noqa: BLE001  (no tz database here: Central time is near enough for "this week")
    _SCHOOL_TZ = dt.timezone(dt.timedelta(hours=-6))


@lru_cache(maxsize=1)
def _calendar() -> dict:
    try:
        return json.loads(_COURSE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def _plantings() -> tuple[tuple[dict, ...], str]:
    cal = _calendar()
    out = []
    for lesson in cal.get("lessons") or []:
        if lesson.get("plant") and lesson.get("planted"):
            ref = "John " + str(lesson["planted"]).replace("–", "-").strip()
            out.append({"date": lesson["date"], "reference": ref, "unit": lesson.get("unit") or ""})
    out.sort(key=lambda p: p["date"])
    return tuple(out), (cal.get("span") or {}).get("last", "")


def _lesson(today: dt.date) -> dict | None:
    """The latest lesson on or before today, within the week, that reads a passage (not a checkpoint)."""
    best = None
    for lesson in _calendar().get("lessons") or []:
        passage = re.sub(r"\s*\(.*?\)\s*$", "", str(lesson.get("passage") or "")).strip()
        if not parse_ref(passage) or lesson.get("date", "") > today.isoformat():
            continue
        if today - dt.date.fromisoformat(lesson["date"]) > dt.timedelta(days=6):
            continue
        if not best or lesson["date"] > best["date"]:
            best = {"date": lesson["date"], "passage": passage, "unit": lesson.get("unit") or "",
                    "focus": lesson.get("focus") or "", "today": lesson["date"] == today.isoformat()}
    return best


def course_week(today: dt.date | None = None) -> dict:
    """This week's verse in the Sophomore Bible course, the verses planted before it, and each
    anchor's unit. Public course facts only, nothing about any student."""
    plantings, last = _plantings()
    today = today or dt.datetime.now(_SCHOOL_TZ).date()
    planted = [p for p in plantings if p["date"] <= today.isoformat()]
    over = bool(last) and today > dt.date.fromisoformat(last) + dt.timedelta(days=14)
    current = planted[-1] if planted and not over else None
    return {"course": "Sophomore Bible", "anchors": {p["reference"]: p["unit"] for p in plantings},
            "order": [p["reference"] for p in plantings], "current": current,
            "review": [p["reference"] for p in planted[:-1]] if current else [],
            "lesson": _lesson(today) if not over else None}


async def memory_texts(request):
    refs = [r.strip() for r in (request.query_params.get("refs") or "").split("|") if len(r.strip()) >= 2][:40]
    if not refs:
        return JSONResponse({"error": "references required"}, status_code=400)
    if not _key():
        return JSONResponse({"error": "BIBLE_API_KEY not set on server"}, status_code=503)
    try:
        texts = await esv_texts(refs)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    return JSONResponse({"texts": texts})


async def memory_chapter(request):
    parsed = parse_ref(request.query_params.get("ref") or "")
    if not parsed:
        return JSONResponse({"error": "reference required"}, status_code=400)
    if not _key():
        return JSONResponse({"error": "BIBLE_API_KEY not set on server"}, status_code=503)
    book, chapter, v1, v2 = parsed
    try:
        verses = await esv_chapter(book, chapter)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    return JSONResponse({"book": book, "chapter": chapter, "first": v1, "last": v2, "verses": verses},
                        headers={"Cache-Control": "private, max-age=3600"})


async def memory_original(request):
    ref = (request.query_params.get("ref") or "").strip()
    data = await run_in_threadpool(original_words, ref)
    if not data:
        return JSONResponse({"error": "not in the library"}, status_code=404)
    return JSONResponse(data, headers={"Cache-Control": "public, max-age=86400"})


async def memory_course(request):
    return JSONResponse(course_week(), headers={"Cache-Control": "private, max-age=600"})


async def memory_cover(request):
    """A house cover titled By Heart, in the theme and motif a student picks for their printed book."""
    from webapp import house_cover  # noqa: PLC0415
    q = request.query_params
    theme, motif = q.get("t") or house_cover.HOUSE["light"], q.get("m") or house_cover.HOUSE["motif"]
    try:
        data = await run_in_threadpool(house_cover._drawn, "memory-book", "By Heart", "Scripture Memory", theme,
                                       house_cover.HOUSE["font"], motif)
    except KeyError:
        return JSONResponse({"error": "unknown style"}, status_code=400)
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "render failed"}, status_code=500)
    return Response(data, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})
