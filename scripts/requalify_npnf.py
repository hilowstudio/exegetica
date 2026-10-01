"""Fine-dedup the NPNF/ANF multi-work patristic volumes in the Reading Room.

The earlier patristics pass (qualify_patristics) prefixed chapters "Work · Chapter", but works
subdivided into Books/Dialogues/Homilies still collided ("Dialogues · Chapter I" x3), as did
distinct letters to the same recipient ("Letters · To Flavian" x6). This finishes the job:

  1. Re-align each chapter to the cached CCEL TOC and rebuild its title as the full path
     "Work · Book · Chapter" (inserting the Book/Dialogue level the earlier pass skipped).
  2. For any residual dups, pull the canonical number ("Letter XXIII", "Epistle IV", "Homily L")
     from the chapter body and insert it.
  3. Any final residual dups get a sequential "(n)" suffix.

Idempotent: step 1 strips a chapter's existing " · " prefix before rebuilding, so re-running is safe.

    .venv\\Scripts\\python.exe scripts\\requalify_npnf.py ccel-schaff-npnf101 [--commit]
    .venv\\Scripts\\python.exe scripts\\requalify_npnf.py --all [--commit]
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOKS = os.path.join(_ROOT, "db", "books.db")
_TOC = os.path.join(_ROOT, ".seed_cache", "ccel_toc")

sys.path.insert(0, _ROOT)
from scripts.format_theology import apply_baseline  # noqa: E402

_MID = "·"  # ·


def _toc_file(slug: str) -> str | None:
    # slug "ccel-<author>-<work..>" -> cached TOC "ccel_<a>_<author>_<work..>_xml.json"
    parts = slug.split("-")
    if len(parts) >= 3 and parts[0] == "ccel":
        author, work = parts[1], "_".join(parts[2:])
        p = os.path.join(_TOC, f"ccel_{author[0]}_{author}_{work}_xml.json")
        if os.path.exists(p):
            return p
    return None


def _flatten(tocfile: str):
    d = json.load(open(tocfile, encoding="utf-8"))
    flat = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            flat.append((n.get("id", ""), (n.get("title") or "").strip()))
            for k in ("children", "sections", "items"):
                for c in n.get(k, []) or []:
                    walk(c)

    walk(d)
    byid = {i: t for i, t in flat}
    ids = set(byid)
    has_child = lambda p: any(x != p and x.startswith(p + ".") for x in ids)  # noqa: E731
    leaves = [(i, t) for i, t in flat if not has_child(i)]

    def path(i):  # ancestor titles, skipping the volume root (level 1)
        parts = i.split(".")
        return [byid[".".join(parts[:k])] for k in range(2, len(parts) + 1) if ".".join(parts[:k]) in byid]

    return leaves, path


def _shorten(a: str) -> str | None:
    a = a.strip().rstrip(".")
    m = re.match(r"^((?:Book|Dialogue|Homily|Sermon|Part|Discourse|Oration|Letter|Tractate|Chapter)\s+[IVXLCM0-9]+)\b", a, re.I)
    if m:
        return m.group(1)
    if re.match(r"^the works of\b", a, re.I):
        return None  # drop the umbrella grouping
    return a if len(a) <= 48 else a[:46].rstrip() + "…"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def requalify(con, slug: str) -> tuple[int, int]:
    bid = con.execute("select id from books where slug=?", (slug,)).fetchone()[0]
    tf = _toc_file(slug)
    rows = con.execute(
        "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
    ).fetchall()

    ren: dict[int, str] = {}
    # --- step 1: TOC path realignment (Work · Book · Chapter) ---
    if tf:
        leaves, path = _flatten(tf)
        tc = 0
        for sn, t, _ in rows:
            chp = t.split(f" {_MID} ")[-1]
            found = next((k for k in range(tc, len(leaves)) if _norm(leaves[k][1]) == _norm(chp)), None)
            if found is None:
                continue
            tc = found + 1
            ctx = [p for p in (_shorten(a) for a in path(leaves[found][0])) if p][:-1]
            newt = (f" {_MID} ".join(ctx) + f" {_MID} " + chp) if ctx else chp
            if newt != t:
                ren[sn] = newt
        if ren:
            apply_baseline(con, bid, renames=ren)
        rows = con.execute(
            "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
        ).fetchall()

    # --- step 2: canonical number from body for repeated titles ---
    cnt = Counter(t.strip() for _, t, _ in rows)
    dupset = {t for t, n in cnt.items() if n > 1}
    ren2: dict[int, str] = {}
    for sn, t, h in rows:
        if t.strip() not in dupset:
            continue
        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
        m = re.search(r"\b(Letter|Epistle|Homily|Sermon|Oration|Discourse|Tractate)\s+([IVXLCM]+|\d+)\b", body[:280])
        if m:
            num = f"{m.group(1)} {m.group(2)}"
            parts = t.split(f" {_MID} ")
            ren2[sn] = f" {_MID} ".join(parts[:-1] + [num, parts[-1]]) if len(parts) > 1 else f"{num} {_MID} {t.strip()}"
    if ren2:
        apply_baseline(con, bid, renames=ren2)
        rows = con.execute(
            "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
        ).fetchall()

    # --- step 3: sequential fallback for anything still duplicated ---
    cnt = Counter(t.strip() for _, t, _ in rows)
    ren3: dict[int, str] = {}
    for t, n in cnt.items():
        if n > 1:
            for i, sn in enumerate([s for s, tt, _ in rows if tt.strip() == t]):
                ren3[sn] = f"{t} ({i + 1})"
    if ren3:
        apply_baseline(con, bid, renames=ren3)

    r2 = con.execute("select title from book_chapters where book_id=?", (bid,)).fetchall()
    dups = len(r2) - len({x[0].strip() for x in r2})
    return len(ren) + len(ren2) + len(ren3), dups


_ALL = (
    [f"ccel-schaff-anf{n:02d}" for n in range(1, 10)]
    + [f"ccel-schaff-npnf1{n:02d}" for n in range(1, 15)]
    + [f"ccel-schaff-npnf2{n:02d}" for n in range(1, 14)]
)


def main() -> None:
    args = sys.argv[1:]
    commit = "--commit" in args
    targets = _ALL if "--all" in args else [a for a in args if not a.startswith("--")]
    con = sqlite3.connect(_BOOKS)
    for slug in targets:
        if not con.execute("select 1 from books where slug=?", (slug,)).fetchone():
            continue
        # unwrap inert spans first
        for n, h in con.execute("select section_number, html from book_chapters where book_id=(select id from books where slug=?)", (slug,)).fetchall():
            con.execute(
                "update book_chapters set html=? where book_id=(select id from books where slug=?) and section_number=?",
                (re.sub(r"</?span>", "", h), slug, n),
            )
        changed, dups = requalify(con, slug)
        print(f"{slug}: retitled={changed} remaining_dups={dups}")
    if commit:
        con.commit()
        print("committed")
    else:
        con.rollback()
        print("(dry-run; pass --commit to save)")


if __name__ == "__main__":
    main()
