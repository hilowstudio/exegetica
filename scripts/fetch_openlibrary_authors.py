"""Each author's most-republished work on Open Library: the evidence for "this author wrote a classic".

For every (author name, birth year) in .seed_cache/pd_sources/fiction_scope.json: find the Open
Library author (birth year breaks ties between namesakes, e.g. Winston Churchill the American
novelist vs. Sir Winston), then their work with the most editions. Cached in
.seed_cache/pd_sources/ol_authors.json  {"name|born": {key, name, birth, top_title, top_editions} | {}}.

    python scripts/fetch_openlibrary_authors.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

from fetch_openlibrary_signals import UA, fold

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".seed_cache" / "pd_sources"
CACHE = SRC / "ol_authors.json"


def clean(name: str) -> str:
    """'R. M. (Robert Michael) Ballantyne' -> 'R. M. Ballantyne'."""
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)|\[.*?\]", "", name or "")).strip()


def find(c: httpx.Client, name: str, born: str) -> dict:
    r = c.get("https://openlibrary.org/search/authors.json", params={"q": clean(name), "limit": 10}).json()
    docs = r.get("docs") or []
    surname = fold(clean(name)).split()[-1:] or [""]
    docs = [d for d in docs if surname[0] and surname[0] in fold(d.get("name"))]
    if not docs:
        return {}
    if born:
        dated = [d for d in docs if born in (d.get("birth_date") or "")]
        if dated:
            docs = dated
    d = max(docs, key=lambda d: d.get("work_count") or 0)
    top = c.get("https://openlibrary.org/search.json", params={
        "author_key": d["key"], "sort": "editions", "limit": 1, "fields": "title,edition_count"}).json()
    t = (top.get("docs") or [{}])[0]
    return {"key": d["key"], "name": d.get("name"), "birth": d.get("birth_date"),
            "top_title": t.get("title"), "top_editions": t.get("edition_count") or 0}


def main():
    scope = json.loads((SRC / "fiction_scope.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = sorted({(x["author"], x["born"]) for x in scope if x["author"]} - {tuple(k.split("|", 1)) for k in cache})
    print(f"{len(todo):,} authors to look up", flush=True)
    with httpx.Client(headers=UA, timeout=30) as c:
        for i, (name, born) in enumerate(todo, 1):
            try:
                cache[f"{name}|{born}"] = find(c, name, born)
            except Exception as e:  # noqa: BLE001
                print(f"  {name}: {e}")
            if i % 100 == 0:
                CACHE.write_text(json.dumps(cache), encoding="utf-8")
                print(f"  {i}/{len(todo)}", flush=True)
            time.sleep(0.4)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
