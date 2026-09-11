"""Full-text source registry — best-first discover-all, then fetch-first-available
under a wall-clock budget. Ported from quillnext `src/lib/sources/registry.ts`.
Never raises: a source that errors is skipped and we fall through.

Sources are added here in best-first priority order as their adapters are built
(see docs/living-library-sources.md build waves). Gutenberg is the first.
"""
from __future__ import annotations

import time

from webapp.sources import ccel, gutenberg

# (key, module) in best-first priority order. Gutenberg leads: it is US-clear by
# construction (so it can publish full_text) and its plain text is cleanest. CCEL
# follows for the on-mission classics Gutenberg lacks (Fathers/Reformers/Puritans/
# creeds); CCEL grounds derivation only and never publishes full_text.
_SOURCES = [
    ("gutenberg", gutenberg),
    ("ccel", ccel),
]
_FETCH = {key: mod.fetch for key, mod in _SOURCES}


async def discover_all(meta: dict) -> list[dict]:
    """Probe every source in priority order; collect all hits (best-first) so fetch
    can fall through. The light step — probing all is cheap. Never raises."""
    if not meta or not (meta.get("title") or "").strip():
        return []
    hits: list[dict] = []
    for key, mod in _SOURCES:
        try:
            hit = await mod.discover(meta)
            if hit and hit.get("text_url"):
                hits.append({"source": key, "source_id": hit["source_id"], "text_url": hit["text_url"]})
        except Exception:  # noqa: BLE001
            pass
    return hits


async def fetch_first_available(hits: list[dict], budget_s: float = 40.0) -> dict | None:
    """Fetch each discovered location in priority order; return the first that yields
    text. Bounded by a wall-clock budget: do NOT start a new fetch once it's spent."""
    start = time.monotonic()
    for h in hits:
        if time.monotonic() - start >= budget_s:
            break
        fn = _FETCH.get(h["source"])
        if not fn:
            continue
        try:
            text = await fn(h["text_url"])
            if text:
                return {"source": h["source"], "source_id": h["source_id"], "text": text}
        except Exception:  # noqa: BLE001
            pass
    return None
