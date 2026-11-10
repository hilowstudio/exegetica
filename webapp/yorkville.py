"""Yorkville Christian School's class texts by course (webapp/data/yorkville.json, built from the
school's 2026-27 book list with no names in it), and the outlines Exegetica keeps for the works whose
text it doesn't have yet (webapp/data/outlines/<key>.json).

An outline is a table of contents typed from a publisher's or retailer's page, with a sentence on what
each part covers. Each sentence is marked "page" (the page said so) or "general" (written from general
knowledge of the subject). Drafts are told it is an outline, not the book (generator._outline_material)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data"
_OUTLINES = _DATA / "outlines"


@lru_cache(maxsize=1)
def _catalog() -> dict:
    try:
        return json.loads((_DATA / "yorkville.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"courses": [], "works": []}


def courses() -> list[dict]:
    return _catalog()["courses"]


def course_name(key: str | None) -> str | None:
    return next((c["name"] for c in courses() if c["key"] == key), None)


@lru_cache(maxsize=128)
def outline(key: str) -> dict | None:
    if not re.fullmatch(r"[a-z0-9-]{1,80}", key or ""):
        return None
    try:
        data = json.loads((_OUTLINES / f"{key}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    return data if (data.get("toc") or data.get("summary")) else None   # a novella may have a summary alone


def works(course_keys: list[str] | None = None) -> list[dict]:
    """The works for these courses (all when None), each with its state: 'text' (in the Reading Room),
    'outline' (an outline exists), or 'none'."""
    out = []
    for w in _catalog()["works"]:
        if course_keys is not None and not set(w["courses"]) & set(course_keys):
            continue
        w = dict(w)
        if w["state"] == "outline" and not outline(w["outline"]):
            w["state"] = "none"
            w["note"] = "No outline yet."
        out.append(w)
    return out


def search_outlines(q: str, limit: int = 8) -> list[dict]:
    """Outline-only works whose title, author or course matches the query, for the source picker."""
    words = [w for w in re.findall(r"[a-z0-9]+", (q or "").lower()) if len(w) > 1]
    if not words:
        return []
    names = {c["key"]: c["name"] for c in courses()}
    hits = []
    for w in works():
        if w["state"] != "outline":
            continue
        o = outline(w["outline"]) or {}
        hay = " ".join([w.get("title") or "", " ".join(o.get("authors") or []), o.get("publisher") or "",
                        " ".join(names.get(k, "") for k in w["courses"])]).lower()
        if all(x in hay for x in words):
            hits.append({"key": w["outline"], "title": o.get("title") or w["title"],
                         "authors": o.get("authors") or [], "edition": o.get("edition"),
                         "courses": [names.get(k, k) for k in w["courses"]],
                         "parts": [_part_label(e) for e in o.get("toc") or []]})
    return hits[:limit]


def _part_label(e: dict) -> str:
    return " ".join(x for x in (e.get("label"), e.get("title")) if x)


def outline_material(key: str, parts: list[str] | None = None) -> dict | None:
    """The outline as a draft's material, cut to the chosen top-level parts when any are named."""
    o = outline(key)
    if not o:
        return None
    entries = o["toc"]
    if parts:
        keep = set(parts)
        chosen = [e for e in entries if _part_label(e) in keep]
        entries = chosen or entries
    return {"type": "outline", "work": {k: o.get(k) for k in ("title", "authors", "publisher", "edition", "summary")},
            "entries": entries}
