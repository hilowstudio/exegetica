"""
Today's price at every service that runs an Media Studio model (docs/decisions/0017).

Each morning the studio asks each service what it charges, in whatever form that service
publishes, and keeps the answers in R2 beside the studio's folders (studio/prices.json). A model
then runs on whichever set-up service is cheapest that day.

- fal: its pricing API, which gives each endpoint's base rate. Where the studio runs a model
  above the base resolution, the route's `factor` scales the rate.
- Runware: the price block of the model's published schema, by rate label or measured run.
- WaveSpeed: its price-quote API, asked about the exact request the studio sends.
- Replicate: the billing tiers embedded in the model's page.

A price that cannot be read, or that lands more than five times above or below the price listed
in the catalog (the mark of reading the wrong number), is not used. The last good price stays,
marked for a look.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from webapp import r2, studio_services as svc

logger = logging.getLogger("study-bible-web.studio")

BOOK_KEY = "studio/prices.json"
STALE_AFTER = 20 * 3600   # a book older than this is refreshed on the next visit
SANE = 5.0
_UA = {"User-Agent": "Mozilla/5.0 (compatible; Exegetica price check)"}

_cache: dict = {"book": None, "at": 0.0}
_pages: dict[str, tuple[float, str]] = {}
_lock = asyncio.Lock()


async def fetch_text(url: str) -> str:
    """A public page, kept ten minutes so one refresh reads a shared page once."""
    hit = _pages.get(url)
    if hit and time.monotonic() - hit[0] < 600:
        return hit[1]
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0), follow_redirects=True) as client:
        r = await client.get(url, headers=_UA)
    r.raise_for_status()
    _pages[url] = (time.monotonic(), r.text)
    return r.text


async def fetch_json(url: str, headers: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0), follow_redirects=True) as client:
        r = await client.get(url, headers=_UA | (headers or {}))
    r.raise_for_status()
    return r.json()


# -------------------------------------------------------------------------------------------
# The book
# -------------------------------------------------------------------------------------------

async def load(fresh: bool = False) -> dict:
    """The last saved book, held a minute in memory."""
    if not fresh and _cache["book"] is not None and time.monotonic() - _cache["at"] < 60:
        return _cache["book"]
    raw = await r2.get_bytes_async(BOOK_KEY) if r2.configured() else None
    try:
        book = json.loads(raw) if raw else {}
    except ValueError:
        logger.warning("studio price book unreadable; starting a new one")
        book = {}
    book = book if isinstance(book, dict) else {}
    book.setdefault("routes", {})
    _cache.update(book=book, at=time.monotonic())
    return book


def stale(book: dict) -> bool:
    return not book.get("checked_ts") or time.time() - book["checked_ts"] > STALE_AFTER


def current(book: dict, route_id: str, listed: dict) -> dict:
    """The price to use for one route: today's where the book has it, the listed one otherwise."""
    entry = (book.get("routes") or {}).get(route_id) or {}
    out = dict(listed)
    for k in ("usd", "usd_audio"):
        if isinstance(entry.get(k), (int, float)) and entry[k] > 0:
            out[k] = entry[k]
    return out


def _sane(got: float, listed: float) -> bool:
    return listed > 0 and listed / SANE <= got <= listed * SANE


async def refresh(routes: dict[str, tuple[str, dict]]) -> dict:
    """Ask every service for today's prices. `routes` maps a route id ("wan-3:replicate") to its
    service and catalog entry. Saves and returns the new book."""
    async with _lock:
        old = await load(fresh=True)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new = {"checked": now, "checked_ts": time.time(), "routes": {}}
        limit = asyncio.Semaphore(4)

        async def one(route_id: str, service: str, route: dict) -> None:
            listed, prev = route["price"], old["routes"].get(route_id) or {}
            kept = {"usd": prev.get("usd"), "usd_audio": prev.get("usd_audio"), "status": "kept",
                    "checked": prev.get("checked")}
            async with limit:
                try:
                    got = await READERS[service](route.get("source") or {}, route)
                except Exception as e:  # noqa: BLE001
                    logger.info("price for %s not read: %s", route_id, type(e).__name__)
                    new["routes"][route_id] = kept | {"note": f"could not be read ({type(e).__name__})"}
                    return
            if got is None:
                new["routes"][route_id] = kept | {"note": "no key to ask with"}
                return
            off = [k for k in ("usd", "usd_audio") if got.get(k) is not None
                   and not _sane(got[k], listed.get(k) or listed["usd"])]
            if off:
                new["routes"][route_id] = kept | {"note": f"read ${got['usd']:g}, far from the listed ${listed['usd']:g}"}
                return
            new["routes"][route_id] = {"usd": got["usd"], "usd_audio": got.get("usd_audio"), "status": "ok",
                                       "checked": now}

        await asyncio.gather(*(one(rid, service, route) for rid, (service, route) in routes.items()))
        if r2.configured():
            await r2.put_bytes_async(BOOK_KEY, json.dumps(new, indent=1).encode(), "application/json")
        _cache.update(book=new, at=time.monotonic())
        return new


# -------------------------------------------------------------------------------------------
# One reader per service: (the route's `source`, the route) -> {"usd": ..., "usd_audio": ...},
# or None when the service needs a key the server does not have
# -------------------------------------------------------------------------------------------

_FAL_UNITS = {"mp": ("megapixels", "processed megapixels"), "image": ("images", "image"),
              "second": ("seconds", "second")}


async def _read_fal(src: dict, route: dict) -> dict | None:
    key = svc._key("fal")
    if not key:
        return None
    data = await fetch_json(f"{svc.FAL_API}/models/pricing?endpoint_id={quote(src['fal'], safe='/')}",
                            {"Authorization": f"Key {key}"})
    price = next(p for p in data.get("prices") or [] if p.get("endpoint_id") == src["fal"])
    if price.get("unit") not in _FAL_UNITS[route["price"]["unit"]]:
        raise ValueError(f"fal bills {src['fal']} by {price.get('unit')}")
    return {"usd": round(float(price["unit_price"]) * src.get("factor", 1), 6)}


async def _read_runware(src: dict, route: dict) -> dict:
    doc = await fetch_json(f"https://runware.ai/docs/models/{src['runware']}/schema.json")
    pricing = doc["info"]["x-pricing"]

    def rate(label: str) -> float:
        return next(float(r["amount"]) for r in pricing.get("rates") or [] if r.get("label", "") == label)
    if "measured" in src:
        usd = next(float(m["price"]) for m in pricing.get("measured") or [] if m.get("configuration") == src["measured"])
    else:
        usd = rate(src.get("rate", ""))
    out = {"usd": usd}
    if "rate_audio" in src:
        out["usd_audio"] = rate(src["rate_audio"])
    return out


async def _read_wavespeed(src: dict, route: dict) -> dict | None:
    if not svc._key("wavespeed"):
        return None
    data = await svc.wavespeed_call("POST", "/model/price", {"model_id": src["wavespeed"], "inputs": src["inputs"]})
    usd = float(data.get("discounted_price") or data.get("price"))
    if usd > 20:   # the catalog counts in millionths of a dollar; a quote above $20 is in those units
        usd /= 1_000_000
    return {"usd": round(usd / src.get("per", 1), 6)}


async def _read_replicate(src: dict, route: dict) -> dict:
    page = html.unescape(await fetch_text(f"https://replicate.com/{src['replicate']}"))
    at = page.index('"billingConfig"')
    config, _ = json.JSONDecoder().raw_decode(page, page.index("{", at))
    for tier in config.get("current_tiers") or []:
        criteria = {c.get("title"): c.get("value") for c in tier.get("criteria") or []}
        if all(criteria.get(k) == v for k, v in src["criteria"].items()):
            price = tier["prices"][0]
            if price.get("metric") != src.get("metric", "video_output_duration_seconds"):
                raise ValueError(f"Replicate bills {src['replicate']} by {price.get('metric')}")
            return {"usd": float(str(price["price"]).replace("$", "").replace(",", ""))}
    raise ValueError("no tier matches")


async def _read_own_gpu(src: dict, route: dict) -> dict:
    """The maker's own GPU has no price list to read: a second of video costs the GPU's hourly rate
    times the render time measured for a clip, over the clip's length."""
    return {"usd": round(src["usd_hour"] / 3600 * src["render_seconds"] / src["clip_seconds"], 4)}


READERS = {"fal": _read_fal, "runware": _read_runware, "wavespeed": _read_wavespeed, "replicate": _read_replicate,
           "baseten": _read_own_gpu}
