#!/usr/bin/env python3
"""
Ingest John Owen's *An Exposition of the Epistle to the Hebrews* (7 vols, Adam's own PD EPUBs)
into the theology.db GROUNDING corpus, so the chat model — which is instructed to ground on
`search_theology` before answering — automatically surfaces Owen when a user asks about Hebrews.

Owen is far too verbose for verse-keyed get_commentary (Heb 1:3 alone is ~105k chars → would be
truncated to a stub). Grounding chunks + embeds the full text and returns the relevant passages
untruncated. Each verse-section paragraph is tagged with its Hebrews `refs` (e.g. "Bible:Heb.1.3"),
so keyword hits show "Scripture cited: Bible:Heb.1.3" and the resource is unmistakably located.

Idempotent: re-running replaces the Owen-Hebrews works only. NON-CCEL source, so it is a
post-`build_theology_grounding.py` importer — re-run it (and build_theology_vectors.py) after any
full theology.db rebuild, then publish_db.py theology.

    .venv\\Scripts\\python.exe scripts\\import_owen_hebrews.py --dry-run
    .venv\\Scripts\\python.exe scripts\\import_owen_hebrews.py
    .venv\\Scripts\\python.exe scripts\\build_theology_vectors.py   # THEN rebuild the vector layer
    .venv\\Scripts\\python.exe scripts\\publish_db.py theology       # THEN republish to R2
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

_DB = _ROOT / "db" / "theology.db"
_AUTHOR = "John Owen"
_TITLE_BASE = "An Exposition of the Epistle to the Hebrews"

# Section header inside the body: "Hebrews 1:3", "Hebrews 1: 1, 2", "Hebrews 3: 7-11".
_VERSE_HDR = re.compile(r"^Hebrews\s+(\d+)\s*:\s*(\d+)(?:\s*[-–,]\s*(?:\d+\s*:\s*)?(\d+))?", re.I)
# Whole-line nav/TOC/running-head duplicates to skip. Anchored so it never eats exposition prose
# (Owen numbers his observations "I."/"II."/"III." — those must be KEPT).
_SKIP_P = re.compile(
    r"^(Hebrews\s+\d+\s*:[\d,\s–-]*|CHAPTERS?\s+[\d,:\s–-]+|Contents|Cover|Title Page)\s*$",
    re.I)


def _clean(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", html.unescape(text)).strip()


def _epubs() -> list[tuple[int, pathlib.Path]]:
    """The 7 volumes, ordered by volume number (from filename: ''=1, '2'=2, …)."""
    out = []
    for p in _ROOT.glob("An Exposition of the Epistle to - John Owen*.epub"):
        m = re.search(r"Owen(\d*)\.epub$", p.name)
        out.append((int(m.group(1)) if m and m.group(1) else 1, p))
    return sorted(out)


def _volume_rows(path: pathlib.Path):
    """Yield (seq, text, refs_json_or_None) for one volume, tagging paragraphs with the current
    Hebrews verse ref; skips nav/TOC/running-head lines."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(path))
    idmap = {it.get_id(): it for it in book.get_items()}
    cur_ref = None
    seq = 0
    for sid, _ in book.spine:
        it = idmap.get(sid)
        if it is None or it.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(it.get_content(), "html.parser")
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            t = " ".join(el.get_text().split())
            if not t:
                continue
            if el.name.startswith("h"):
                m = _VERSE_HDR.match(t)
                if m:
                    ch, vs, ve = m.group(1), m.group(2), m.group(3)
                    cur_ref = f"Bible:Heb.{ch}.{vs}" + (f"-Heb.{ch}.{ve}" if ve else "")
                else:
                    cur_ref = None  # chapter/exercitation/front-matter header
                continue
            if _SKIP_P.match(t):  # nav / TOC / running head, not exposition
                continue
            yield seq, t, (json.dumps([cur_ref]) if cur_ref else None)
            seq += 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vols = _epubs()
    if not vols:
        sys.exit("Owen Hebrews EPUBs not found in the repo root.")
    if not _DB.exists():
        sys.exit("db/theology.db not found — build_theology_grounding.py first.")

    con = sqlite3.connect(_DB)
    # Idempotent: drop any prior Owen-Hebrews works + their paragraphs.
    old = [wid for (wid,) in con.execute(
        "select work_id from theology_works where author = ? and title like ?",
        (_AUTHOR, _TITLE_BASE + "%"))]
    if old and not args.dry_run:
        con.executemany("delete from theology_texts where work_id = ?", [(w,) for w in old])
        con.executemany("delete from theology_works where work_id = ?", [(w,) for w in old])

    next_wid = con.execute("select coalesce(max(work_id), 0) from theology_works").fetchone()[0] + 1
    next_id = con.execute("select coalesce(max(id), 0) from theology_texts").fetchone()[0] + 1

    total_p = tagged = 0
    plan = []
    for volnum, path in vols:
        rows = list(_volume_rows(path))
        tagged += sum(1 for _s, _t, r in rows if r)
        total_p += len(rows)
        plan.append((next_wid + len(plan), volnum, path, rows))

    print(f"{len(vols)} volumes → {total_p:,} paragraphs ({tagged:,} tagged with a Hebrews verse)")
    for wid, volnum, path, rows in plan:
        vrefs = sum(1 for _s, _t, r in rows if r)
        print(f"  Vol {volnum}: {len(rows):>5}p, {vrefs:>4} verse-tagged  ({path.name[-14:]})")
    if args.dry_run:
        print("(dry run — nothing written)")
        con.close()
        return

    for wid, volnum, path, rows in plan:
        title = f"{_TITLE_BASE}, Vol. {volnum}"
        con.execute("insert into theology_works values (?,?,?,?,?,?)",
                    (wid, title, _AUTHOR, "Public Domain", None, len(rows)))
        batch = []
        for seq, t, refs in rows:
            batch.append((next_id, wid, seq, t, refs))
            next_id += 1
        con.executemany("insert into theology_texts (id, work_id, seq, text, refs) values (?,?,?,?,?)", batch)

    con.execute("insert into theology_fts(theology_fts) values('rebuild')")  # resync external-content FTS
    con.commit()
    nw = con.execute("select count(*) from theology_works").fetchone()[0]
    npar = con.execute("select count(*) from theology_texts").fetchone()[0]
    con.close()
    print(f"\n[ok] ingested Owen's Hebrews ({total_p:,} paragraphs); theology.db now {nw} works / {npar:,} paragraphs.")
    print("Next: build_theology_vectors.py (rebuild semantic layer), then publish_db.py theology.")


if __name__ == "__main__":
    main()
