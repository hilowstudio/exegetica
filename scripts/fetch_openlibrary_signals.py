"""Open Library reader signals for books, by title + author: how many editions a work has had
(republication = staying power), how many readers shelved it, its first publication year.

Reads a TSV of `key<TAB>title<TAB>author` on stdin-or-path, writes/extends the cache
.seed_cache/pd_sources/ol_signals.json  {key: {key, title, edition_count, want, read, ratings,
first_year} | {}}. Resumable; ~3 requests/second.

    python scripts/fetch_openlibrary_signals.py books.tsv
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import unicodedata
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "pd_sources" / "ol_signals.json"
UA = {"User-Agent": "ExegeticaLibrary/1.0 (https://exegetica.fly.dev; public-domain curation)"}
FIELDS = "key,title,author_name,edition_count,want_to_read_count,already_read_count,ratings_count,first_publish_year"


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


VOL = re.compile(r"[,.]?\s*(?:[-—]\s*)?\b(?:vol(?:ume)?\.?|part|book|tome)\s+[\divxlc]+\b.*$|\s*[,—-]\s*complete\b.*$", re.I)


def short_title(t: str) -> str:
    """The searchable title: no subtitle, and no volume/part label ('Richard Carvel, Volume 3',
    'The Bible, King James Version, Book 19: Psalms' -> 'The Bible, King James Version')."""
    t = VOL.sub("", t or "")
    return re.split(r"[:;(\[]|--|—", t)[0].strip(" ,.")


def surname(a: str) -> str:
    a = re.sub(r"\(.*?\)", "", a or "")
    a = a.split(",")[0] if "," in a else a
    w = fold(a).split()
    return w[-1] if w else ""


async def one(c: httpx.AsyncClient, title: str, author: str) -> dict:
    t = short_title(title)
    sn = surname(author)
    params = {"title": t, "fields": FIELDS, "limit": 10}
    if sn and sn not in ("anonymous", "unknown", "various"):
        params["author"] = sn
    for attempt in range(4):
        try:
            r = await c.get("https://openlibrary.org/search.json", params=params)
            if r.status_code == 200:
                break
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(2 * (attempt + 1))
    else:
        return None
    want = fold(t)
    best = None
    for d in r.json().get("docs", []):
        dt = fold(d.get("title"))
        if not (dt == want or dt.startswith(want) or want.startswith(dt)):
            continue
        if sn and params.get("author") and not any(sn in fold(a) for a in d.get("author_name") or []):
            continue
        if best is None or (d.get("edition_count") or 0) > (best.get("edition_count") or 0):
            best = d
    if not best:
        return {}
    return {"key": best.get("key"), "title": best.get("title"), "edition_count": best.get("edition_count") or 0,
            "want": best.get("want_to_read_count") or 0, "read": best.get("already_read_count") or 0,
            "ratings": best.get("ratings_count") or 0, "first_year": best.get("first_publish_year")}


async def main(path: str):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rows = [ln.split("\t") for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    todo = [r for r in rows if r[0] not in cache]
    print(f"{len(todo):,} to fetch ({len(cache):,} cached)", flush=True)
    sem = asyncio.Semaphore(3)
    done = 0
    async with httpx.AsyncClient(headers=UA, timeout=30) as c:
        async def run(r):
            nonlocal done
            async with sem:
                res = await one(c, r[1], r[2] if len(r) > 2 else "")
                await asyncio.sleep(0.5)
            if res is not None:
                cache[r[0]] = res
            done += 1
            if done % 250 == 0:
                CACHE.write_text(json.dumps(cache), encoding="utf-8")
                print(f"  {done:,}/{len(todo):,}", flush=True)
        await asyncio.gather(*(run(r) for r in todo))
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    print(f"done; {sum(1 for v in cache.values() if v):,}/{len(cache):,} matched")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
