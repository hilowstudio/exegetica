"""Fetch each CCEL work's ThML table-of-contents (the <divN id title> tree) and cache it.

The ccel-paragraphs dataset dropped CCEL's real chapter titles (they live in <div title="…">
structure, not in <p> rows). But CCEL still serves the full ThML at https://ccel.org/<workpath>,
whose div ids match our paragraph division ids exactly. This grabs just the div tree per work so
scripts/seed_theology_reader.py can title chapters authoritatively and drop front matter.

Cached as .seed_cache/ccel_toc/<key>.json ([{id, level, title, cls}] in reading order). Resumable:
re-running skips works already cached. One-time; then rebuild the reader with --toc.

    .venv\\Scripts\\python.exe scripts\\fetch_ccel_toc.py
"""
from __future__ import annotations

import asyncio
import html
import json
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from webapp.sources.matching import BROWSER_UA  # noqa: E402

_STAGE = _ROOT / ".seed_cache" / "ccel_reader_stage.db"
_CACHE = _ROOT / ".seed_cache" / "ccel_toc"
_DIV = re.compile(r"<div(\d)\b([^>]*)>")
_RETRY = {429, 500, 502, 503, 504}


def _key(workpath: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", workpath)


def parse_toc(body: str) -> list[dict]:
    out = []
    for m in _DIV.finditer(body):
        lvl, a = int(m.group(1)), m.group(2)
        did = re.search(r'\bid="([^"]*)"', a)
        if not did:
            continue
        tit = re.search(r'\btitle="([^"]*)"', a)
        cls = re.search(r'\bclass="([^"]*)"', a)
        out.append({"id": did.group(1), "level": lvl,
                    "title": html.unescape(tit.group(1)).strip() if tit else "",
                    "cls": cls.group(1) if cls else ""})
    return out


async def fetch_one(client, sem, workpath: str) -> tuple[str, str]:
    cache = _CACHE / (_key(workpath) + ".json")
    if cache.exists():
        return workpath, "cached"
    url = "https://ccel.org/" + workpath
    async with sem:
        for i in range(3):
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    toc = parse_toc(r.text)
                    cache.write_text(json.dumps(toc, ensure_ascii=False), encoding="utf-8")
                    return workpath, f"ok ({len(toc)} divs)"
                if r.status_code not in _RETRY:
                    return workpath, f"http {r.status_code}"
            except httpx.HTTPError:
                pass
            await asyncio.sleep(1.5 * (2 ** i))
    return workpath, "failed"


async def main():
    _CACHE.mkdir(parents=True, exist_ok=True)
    st = sqlite3.connect(_STAGE)
    workpaths = sorted({r[0] for r in st.execute("select workpath from meta where workpath is not null")})
    st.close()
    print(f"{len(workpaths)} works to TOC-fetch (cached ones skipped)", flush=True)

    sem = asyncio.Semaphore(6)
    timeout = httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=15.0)
    ok = cached = fail = 0
    async with httpx.AsyncClient(headers={"User-Agent": BROWSER_UA}, follow_redirects=True, timeout=timeout) as client:
        tasks = [asyncio.create_task(fetch_one(client, sem, wp)) for wp in workpaths]
        for n, fut in enumerate(asyncio.as_completed(tasks), 1):
            wp, status = await fut
            if status == "cached":
                cached += 1
            elif status.startswith("ok"):
                ok += 1
            else:
                fail += 1
                print(f"  MISS [{status}] {wp}", flush=True)
            if n % 100 == 0:
                print(f"  {n}/{len(workpaths)} (ok {ok}, cached {cached}, fail {fail})", flush=True)
    print(f"\ndone: {ok} fetched, {cached} already cached, {fail} failed → {_CACHE}", flush=True)
    if fail:
        print("  re-run to retry failures (cached ones are skipped).", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
