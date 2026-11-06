"""
Optional, live-proxied translations (never bundled or cached).

These are copyrighted modern translations reached through the user's own API
access at request time:
  - ESV  — Crossway API (https://api.esv.org), requires ESV_API_KEY (free,
           non-commercial). Text is fetched live and never stored.
  - NET  — bible.org labs API (keyless, free, non-commercial). Quotations must
           be marked "(NET)" and link to netbible.org.

If a key is missing or a request fails, fetch_optional raises Unavailable and
the caller serves the bundled BSB in its place, so the server never depends on
these. The raw cause goes to the server log only: students can see what the
model sees.
"""

import logging
import os

import httpx

logger = logging.getLogger("study-bible-mcp")

# Live-proxy translations: abbrev -> short description.
OPTIONAL_TRANSLATIONS = {
    "ESV": "English Standard Version (Crossway API — needs your ESV_API_KEY)",
    "NET": "New English Translation (bible.org, keyless)",
}

# Attribution shown alongside the text where the licence requires it.
ATTRIBUTION = {
    "NET": "*NET Bible®, https://netbible.org — quoted with permission for non-commercial use.*",
    "ESV": "*Scripture quotations marked ESV are from the ESV® Bible, © Crossway. Fetched live via your API key.*",
}


class Unavailable(Exception):
    """A live translation could not be reached. The message is plain and safe for the model.
    The cause is already in the log."""

    def __init__(self, translation: str, cause: str, plain: str = "could not be reached just now"):
        logger.warning("%s fetch failed: %s", translation, cause)
        super().__init__(f"The {translation} {plain}.")
        self.translation = translation


def _esv_key() -> str | None:
    # Accept either ESV_API_KEY or BIBLE_API_KEY (a Crossway key under either name).
    return os.environ.get("ESV_API_KEY") or os.environ.get("BIBLE_API_KEY")


def esv_configured() -> bool:
    """Whether this server has a Crossway key, which makes the ESV the default translation."""
    return bool(_esv_key())


async def _fetch_esv(reference: str) -> tuple[str | None, str | None]:
    key = _esv_key()
    if not key:
        raise Unavailable("ESV", "no ESV_API_KEY or BIBLE_API_KEY is set", "is not set up on this server")
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                "https://api.esv.org/v3/passage/text/",
                params={
                    "q": reference,
                    "include-headings": "false",
                    "include-footnotes": "false",
                    "include-verse-numbers": "false",
                    "include-short-copyright": "false",
                    "include-passage-references": "false",
                },
                headers={"Authorization": f"Token {key}"},
            )
        if r.status_code != 200:
            raise Unavailable("ESV", f"HTTP {r.status_code}")
        passages = r.json().get("passages") or []
    except Unavailable:
        raise
    except Exception as e:
        raise Unavailable("ESV", f"{type(e).__name__}: {e}") from e
    text = passages[0].strip() if passages else ""
    return (text or None), (None if text else f"The ESV has no passage for '{reference}'.")


async def _fetch_net(reference: str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                "https://labs.bible.org/api/",
                params={"passage": reference, "type": "json", "formatting": "plain"},
            )
        if r.status_code != 200:
            raise Unavailable("NET", f"HTTP {r.status_code}")
        data = r.json()
    except Unavailable:
        raise
    except Exception as e:
        raise Unavailable("NET", f"{type(e).__name__}: {e}") from e
    if not isinstance(data, list) or not data:
        return None, f"The NET has no passage for '{reference}'."
    text = " ".join((v.get("text") or "").strip() for v in data if isinstance(v, dict)).strip()
    return (text or None), (None if text else f"The NET has no passage for '{reference}'.")


async def fetch_optional(translation: str, reference: str) -> tuple[str | None, str | None]:
    """Return (text, note) for an optional live translation, or (None, None) if not one.
    The note says plainly that a reference has no passage. Raises Unavailable when the service
    can't be reached or isn't set up."""
    t = translation.upper()
    if t == "ESV":
        return await _fetch_esv(reference)
    if t == "NET":
        return await _fetch_net(reference)
    return None, None
