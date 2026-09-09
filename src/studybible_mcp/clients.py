"""
Optional, live-proxied translations (never bundled or cached).

These are copyrighted modern translations reached through the user's own API
access at request time:
  - ESV  — Crossway API (https://api.esv.org), requires ESV_API_KEY (free,
           non-commercial). Text is fetched live and never stored.
  - NET  — bible.org labs API (keyless, free, non-commercial). Quotations must
           be marked "(NET)" and link to netbible.org.

If a key is missing or a request fails, the caller degrades gracefully to the
bundled public-domain translations — the server never depends on these.
"""

import os

import httpx

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


async def _fetch_esv(reference: str) -> tuple[str | None, str | None]:
    # Accept either ESV_API_KEY or BIBLE_API_KEY (a Crossway key under either name).
    key = os.environ.get("ESV_API_KEY") or os.environ.get("BIBLE_API_KEY")
    if not key:
        return None, ("ESV requires a Crossway API key. Set the ESV_API_KEY (or BIBLE_API_KEY) "
                      "environment variable (free for non-commercial use: https://api.esv.org).")
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
            return None, f"ESV API error (HTTP {r.status_code})."
        passages = r.json().get("passages") or []
        text = passages[0].strip() if passages else ""
        return (text or None), (None if text else f"ESV: no passage found for '{reference}'.")
    except Exception as e:
        return None, f"ESV fetch failed: {e}"


async def _fetch_net(reference: str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(
                "https://labs.bible.org/api/",
                params={"passage": reference, "type": "json", "formatting": "plain"},
            )
        if r.status_code != 200:
            return None, f"NET API error (HTTP {r.status_code})."
        data = r.json()
        if not isinstance(data, list) or not data:
            return None, f"NET: no passage found for '{reference}'."
        text = " ".join((v.get("text") or "").strip() for v in data).strip()
        return (text or None), (None if text else f"NET: empty passage for '{reference}'.")
    except Exception as e:
        return None, f"NET fetch failed: {e}"


async def fetch_optional(translation: str, reference: str) -> tuple[str | None, str | None]:
    """Return (text, error) for an optional live translation, or (None, None) if not one."""
    t = translation.upper()
    if t == "ESV":
        return await _fetch_esv(reference)
    if t == "NET":
        return await _fetch_net(reference)
    return None, None
