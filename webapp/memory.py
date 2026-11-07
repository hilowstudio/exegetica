"""
Scripture Memory — server-side ESV proxy for the client-only memory feature.

The memorization state (verses, folders, per-verse progress) lives entirely in the
browser's localStorage; there is no server persistence and no accounts. The only
thing the server does for this feature is proxy the ESV API, because the ESV key
(BIBLE_API_KEY) is a secret that must not reach the client. Two read-only endpoints:

    GET /api/memory/text?ref=John+3:16   -> {"reference": "...", "text": "..."}
    GET /api/memory/audio?ref=John+3:16  -> {"reference": "...", "audioUrl": "..."}

Both are stateless lookups; they store nothing.
"""
from __future__ import annotations

import os

import httpx
from starlette.responses import JSONResponse

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
