"""Living Library search adapters.

Catalog lookups used by the "Add a resource" flows. All are read-only metadata
searches; nothing here ingests or stores. Books come from OpenLibrary (keyless)
enriched by Google Books when GOOGLE_BOOKS_API_KEY is set; podcasts come from the
keyless iTunes Search API (the same source Podcatch uses).
"""

import asyncio
import os
import re
from urllib.parse import urlparse

import httpx

_OL_SEARCH = "https://openlibrary.org/search.json"
_GB_SEARCH = "https://www.googleapis.com/books/v1/volumes"
_ITUNES = "https://itunes.apple.com/search"
_YT_OEMBED = "https://www.youtube.com/oembed"
_UA = {"User-Agent": "StudyBibleLivingLibrary/1.0 (+study-bible app)"}


def _key(title: str, author: str) -> str:
    return (title or "").strip().lower() + "|" + (author or "").strip().lower()


async def _openlibrary(client: httpx.AsyncClient, q: str, limit: int) -> list[dict]:
    try:
        r = await client.get(_OL_SEARCH, headers=_UA, params={
            "q": q, "limit": limit,
            "fields": "title,author_name,first_publish_year,cover_i,isbn,key",
        })
        if r.status_code != 200:
            return []
        out = []
        for d in (r.json().get("docs") or []):
            cover = d.get("cover_i")
            out.append({
                "title": d.get("title") or "",
                "author": (d.get("author_name") or [""])[0],
                "year": str(d.get("first_publish_year") or ""),
                "cover": f"https://covers.openlibrary.org/b/id/{cover}-M.jpg" if cover else None,
                "isbn": (d.get("isbn") or [None])[0],
                "source": "openlibrary",
            })
        return out
    except Exception:
        return []


async def _googlebooks(client: httpx.AsyncClient, q: str, limit: int) -> list[dict]:
    key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    if not key:
        return []
    try:
        r = await client.get(_GB_SEARCH, headers=_UA, params={
            "q": q, "maxResults": min(limit, 20), "printType": "books", "key": key,
        })
        if r.status_code != 200:
            return []
        out = []
        for v in (r.json().get("items") or []):
            info = v.get("volumeInfo") or {}
            img = (info.get("imageLinks") or {}).get("thumbnail")
            if img:
                img = img.replace("http://", "https://")
            isbn = None
            for ident in (info.get("industryIdentifiers") or []):
                if ident.get("type") in ("ISBN_13", "ISBN_10"):
                    isbn = ident.get("identifier")
                    break
            out.append({
                "title": info.get("title") or "",
                "author": (info.get("authors") or [""])[0],
                "year": (info.get("publishedDate") or "")[:4],
                "cover": img,
                "isbn": isbn,
                "source": "googlebooks",
            })
        return out
    except Exception:
        return []


async def _gb_cover(client: httpx.AsyncClient, title: str, author: str) -> str | None:
    """Best cover thumbnail for one work from Google Books (keyless works; the key just
    raises quota). Queries by intitle/inauthor for a precise match on the seeded book."""
    q = f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else "")
    params = {"q": q, "maxResults": 5, "printType": "books", "country": "US"}
    key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    if key:
        params["key"] = key
    try:
        r = await client.get(_GB_SEARCH, headers=_UA, params=params)
        if r.status_code != 200:
            return None
        for v in (r.json().get("items") or []):
            img = ((v.get("volumeInfo") or {}).get("imageLinks") or {}).get("thumbnail")
            if img:
                img = img.replace("http://", "https://").replace("&edge=curl", "")
                return re.sub(r"zoom=\d+", "zoom=1", img)
    except Exception:  # noqa: BLE001
        return None
    return None


async def _ol_cover(client: httpx.AsyncClient, title: str, author: str) -> str | None:
    """Fallback cover from Open Library's cover service (large size)."""
    params = {"title": title, "limit": 1, "fields": "cover_i"}
    if author:
        params["author"] = author
    try:
        r = await client.get(_OL_SEARCH, headers=_UA, params=params)
        if r.status_code != 200:
            return None
        docs = r.json().get("docs") or []
        if docs and docs[0].get("cover_i"):
            return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg"
    except Exception:  # noqa: BLE001
        return None
    return None


async def resolve_cover(client: httpx.AsyncClient, title: str, author: str = "") -> str | None:
    """Cover-art URL for a seeded book: Google Books first, Open Library as fallback.
    Tries title+author for precision, then falls back to a title-only query (recovers works
    whose stored author string doesn't match the catalog's, e.g. abbreviated first names).
    Returns None when neither source has one. Reusable by the backfill and the seeder."""
    title = (title or "").strip()
    author = (author or "").strip()
    if not title:
        return None
    passes = [(title, author)] + ([(title, "")] if author else [])
    for t, a in passes:
        url = await _gb_cover(client, t, a) or await _ol_cover(client, t, a)
        if url:
            return url
    return None


async def search_books(q: str, limit: int = 10) -> list[dict]:
    """Merged book search: Google Books (if keyed) first, then OpenLibrary,
    deduped by title+author, cover-bearing results floated to the top."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    async with httpx.AsyncClient(timeout=12.0) as client:
        gb, ol = await asyncio.gather(
            _googlebooks(client, q, limit), _openlibrary(client, q, limit))
    merged: list[dict] = []
    seen: set[str] = set()
    for item in gb + ol:
        if not item["title"]:
            continue
        k = _key(item["title"], item["author"])
        if k in seen:
            continue
        seen.add(k)
        merged.append(item)
    merged.sort(key=lambda x: 0 if x.get("cover") else 1)
    return merged[:limit]


def _is_youtube(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host.endswith("youtube.com") or host.endswith("youtu.be")


async def preview_video(url: str) -> dict | None:
    """Keyless YouTube preview via the oEmbed endpoint: title, channel, thumbnail.
    No duration (oEmbed does not provide it). Returns None for non-YouTube or bad URLs."""
    url = (url or "").strip()
    if not url or not _is_youtube(url):
        return None
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(_YT_OEMBED, headers=_UA, params={"url": url, "format": "json"})
        if r.status_code != 200:
            return None
        j = r.json()
        return {
            "title": j.get("title") or "",
            "author": j.get("author_name") or "",
            "author_url": j.get("author_url"),
            "thumbnail": j.get("thumbnail_url"),
            "provider": j.get("provider_name") or "YouTube",
            "url": url,
        }
    except Exception:
        return None


_YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
_YT_VIDEOS = "https://www.googleapis.com/youtube/v3/videos"


def _fmt_duration(iso: str) -> str:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return ""
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi}:{s:02d}"


async def search_youtube(q: str, limit: int = 12) -> list[dict]:
    """YouTube discovery via the Data API, then a semantic re-rank of the
    candidate set by the local static embedding model (title + description)."""
    q = (q or "").strip()
    key = os.environ.get("YOUTUBE_API_KEY")
    if len(q) < 2 or not key:
        return []
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(_YT_SEARCH, headers=_UA, params={
                "key": key, "q": q, "part": "snippet", "type": "video",
                "maxResults": 25, "safeSearch": "moderate"})
            if r.status_code != 200:
                return []
            ids, snip = [], {}
            for it in (r.json().get("items") or []):
                vid = (it.get("id") or {}).get("videoId")
                if vid:
                    ids.append(vid)
                    snip[vid] = it.get("snippet") or {}
            if not ids:
                return []
            r2 = await client.get(_YT_VIDEOS, headers=_UA, params={
                "key": key, "id": ",".join(ids), "part": "snippet,contentDetails"})
        details = {}
        if r2.status_code == 200:
            for v in (r2.json().get("items") or []):
                details[v.get("id")] = v
        cand = []
        for vid in ids:
            d = details.get(vid) or {}
            sd = d.get("snippet") or snip.get(vid, {})
            thumbs = sd.get("thumbnails") or {}
            thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
            title = sd.get("title") or ""
            if not title:
                continue
            cand.append({
                "title": title,
                "author": sd.get("channelTitle") or "",
                "thumbnail": thumb,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "duration": _fmt_duration((d.get("contentDetails") or {}).get("duration")),
                "_text": title + ". " + ((sd.get("description") or "")[:300]),
            })
        try:
            from webapp import generator
            vecs = generator.embed([c["_text"] for c in cand])
            qv = generator.embed([q])
            if vecs is not None and qv is not None:
                import numpy as np
                order = list(np.argsort(-(vecs @ qv[0])))
                cand = [cand[i] for i in order]
        except Exception:
            pass
        for c in cand:
            c.pop("_text", None)
        return cand[:limit]
    except Exception:
        return []


async def search_podcasts(q: str, limit: int = 10) -> list[dict]:
    """Podcast search via the keyless iTunes Search API."""
    q = (q or "").strip()
    if len(q) < 2:
        return []
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(_ITUNES, headers=_UA, params={
                "media": "podcast", "term": q, "limit": limit,
            })
        if r.status_code != 200:
            return []
        out = []
        for res in (r.json().get("results") or []):
            title = res.get("collectionName") or res.get("trackName") or ""
            if not title:
                continue
            out.append({
                "title": title,
                "author": res.get("artistName") or "",
                "artwork": res.get("artworkUrl600") or res.get("artworkUrl100"),
                "feed": res.get("feedUrl"),
                "episodes": res.get("trackCount"),
                "genre": res.get("primaryGenreName"),
            })
        return out
    except Exception:
        return []
