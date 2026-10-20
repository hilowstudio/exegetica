"""Harvest the Yale Avalon Project once, politely, into .seed_cache/socialsci/avalon/ (raw HTML).

Avalon has no bulk export, but its pages are static and its reuse is open (confirmed through
Adam's Yale contact, 2026-10-19). This crawler starts from the century menus and the major
document collections, follows links that stay on avalon.law.yale.edu, and saves each page once.
It is resumable: a page already in the cache is never fetched again.

    .venv/Scripts/python.exe scripts/socialsci/harvest_avalon.py [--delay 1.0] [--max 20000]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".seed_cache" / "socialsci" / "avalon"
HOST = "avalon.law.yale.edu"
BASE = f"https://{HOST}/"
UA = "YorkvilleChristianSchool-HistoryResearch/1.0 (one-time archival harvest for classroom use)"
SEEDS = [BASE + "subject_menus/major.asp"] + [
    BASE + f"subject_menus/{p}.asp"
    for p in ("ancient", "medieval", "15th", "16th", "17th", "18th", "19th", "20th", "21st")
]
SKIP = re.compile(r"\.(pdf|jpe?g|gif|png|zip|doc|mp3|wav|css|js)$", re.I)


def key(url: str) -> str:
    path = urllib.parse.urlsplit(url).path.lstrip("/") or "index"
    safe = re.sub(r"[^A-Za-z0-9._/-]", "_", path)
    return safe if len(safe) < 180 else hashlib.sha1(path.encode()).hexdigest() + ".html"


def norm(url: str) -> str | None:
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or u.netloc.lower() not in (HOST, "www." + HOST):
        return None
    path = re.sub(r"/+", "/", u.path)
    if SKIP.search(path) or not path.lower().endswith((".asp", ".htm", ".html", "/")):
        return None
    return f"https://{HOST}{path}"


def fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:  # noqa: BLE001
            time.sleep(5 * (attempt + 1))
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--max", type=int, default=20000)
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    index_path = CACHE / "_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    seen, queue = set(), deque(SEEDS)
    fetched = 0
    while queue and len(seen) < a.max:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        f = CACHE / key(url)
        if f.exists():
            body = f.read_bytes()
        else:
            body = fetch(url)
            time.sleep(a.delay)
            if body is None:
                index[url] = None
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(body)
            fetched += 1
            if fetched % 100 == 0:
                index_path.write_text(json.dumps(index, indent=0), encoding="utf-8")
                print(f"  fetched {fetched:,} · seen {len(seen):,} · queued {len(queue):,}", flush=True)
        index[url] = key(url)
        html = body.decode("latin-1", errors="replace")
        # Follow links and frame sources: some documents (Magna Carta) are framesets.
        for href in re.findall(r'(?:href|<i?frame\b[^>]*?\bsrc)\s*=\s*["\']?([^"\'\s>#]+)', html, re.I):
            n = norm(urllib.parse.urljoin(url, href))
            if n and n not in seen:
                queue.append(n)
    index_path.write_text(json.dumps(index, indent=0), encoding="utf-8")
    print(f"done: {fetched:,} new pages fetched, {sum(1 for v in index.values() if v):,} pages cached")


if __name__ == "__main__":
    main()
