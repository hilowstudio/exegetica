"""Qualify chapters in the ANF/NPNF patristics volumes with their parent work.

Each of these ~37 CCEL volumes is a multi-work collection (dozens of Fathers' works, each
with its own "Chapter I" run), so a flat TOC of repeated "Chapter I" is unnavigable. This
aligns each DB section to the cached CCEL TOC by title sequence (both are in reading order),
then prefixes chapter sections with their work — e.g. "Against Heresies: Book I · Chapter III".

The CCEL TOC is a flat list of {id (dotted path), level, title}; ancestry comes from the
dotted id. L1 = Father, L2 = Work, L3 = Chapter. We prefix a matched chapter (level ≥ 3) with
its level-2 (work) ancestor; work/father headers (level ≤ 2) keep their own title.

Idempotent: strips any previously-injected <h2> and re-injects the qualified title.

    .venv\\Scripts\\python.exe scripts\\qualify_patristics.py --slug ccel-schaff-anf01
    .venv\\Scripts\\python.exe scripts\\qualify_patristics.py --all
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from scripts.format_theology import apply_baseline, clean_title, qa  # noqa: E402

_TOC_DIR = os.path.join(_ROOT, ".seed_cache", "ccel_toc")
_BOOKS_DB = os.path.join(_ROOT, "db", "books.db")


def _norm(t: str) -> str:
    t = re.sub(r"[‐-―‘’]", " ", t or "")   # dashes / curly quotes → space
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def _find_toc(slug: str) -> str | None:
    parts = slug.split("-")
    work = "".join(parts[2:]) if len(parts) > 2 else parts[-1]
    for f in os.listdir(_TOC_DIR):
        if work.lower() in f.lower().replace("-", "").replace("_", ""):
            return os.path.join(_TOC_DIR, f)
    return None


def _load_toc(path: str) -> list[dict]:
    raw = json.load(open(path, encoding="utf-8"))
    byid = {e["id"]: e for e in raw}

    def ancestor(e, lvl):
        parts = e["id"].split(".")
        for k in range(len(parts), 0, -1):
            p = byid.get(".".join(parts[:k]))
            if p and p["level"] == lvl:
                return p["title"]
        return None

    out = []
    for e in raw:
        l2, l1 = ancestor(e, 2), ancestor(e, 1)
        # Prefer the most-specific ancestor that reads like a label (short), not a descriptive
        # sentence. ANF: L2 = "Against Heresies: Book I". NPNF: L2 books are long descriptions →
        # fall back to the L1 work ("The Confessions", "Letters of St. Augustin").
        work = l2 if (l2 and len(l2) <= 55) else (l1 or l2)
        out.append({"norm": _norm(e["title"]), "level": e["level"], "work": work})
    return out


def _qualify(con, bid: int, toc: list[dict]) -> tuple[dict, int]:
    """Return (renames by section_number, unmatched_count) from an in-order title alignment."""
    db = con.execute("select section_number, title from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
    renames, j, unmatched = {}, 0, 0
    for n, title in db:
        base = title.rsplit(" · ", 1)[-1]     # recover the original title if already qualified (idempotent)
        tn = _norm(base)
        hit = None
        for k in range(j, min(j + 120, len(toc))):
            e = toc[k]
            if e["norm"] == tn or (len(tn) > 12 and e["norm"].startswith(tn)) or (len(e["norm"]) > 12 and tn.startswith(e["norm"])):
                hit = k
                break
        if hit is None:
            unmatched += 1
            renames[n] = clean_title(base)      # keep the recovered original, un-prefixed
            continue
        e = toc[hit]
        j = hit + 1
        if e["level"] >= 3 and e["work"] and _norm(e["work"]) != tn:
            renames[n] = f"{clean_title(e['work'])} · {clean_title(base)}"
        else:
            renames[n] = clean_title(base)      # work/father header → its own title
    return renames, unmatched


def process(con, slug: str) -> None:
    row = con.execute("select id, title from books where slug=?", (slug,)).fetchone()
    if not row:
        print(f"  {slug}: NOT FOUND"); return
    bid, title = row
    toc_path = _find_toc(slug)
    if not toc_path:
        print(f"  {slug}: NO TOC"); return
    toc = _load_toc(toc_path)
    # idempotent pre-step: strip any injected <h2> and unwrap spans
    for n, h in con.execute("select section_number, html from book_chapters where book_id=?", (bid,)).fetchall():
        h = re.sub(r"^\s*<h[1-6]>.*?</h[1-6]>\s*", "", h, flags=re.S)
        h = re.sub(r"</?span>", "", h)
        con.execute("update book_chapters set html=? where book_id=? and section_number=?", (h, bid, n))
    con.commit()
    renames, unmatched = _qualify(con, bid, toc)
    nch, nw = apply_baseline(con, bid, renames=renames)
    print(f"\n{slug}  ({title[:40]})")
    print(f"  sections={nch} qualified={len(renames)} unmatched={unmatched} words={nw:,}")
    qa(con, bid)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(_BOOKS_DB)
    if args.all:
        slugs = [r[0] for r in con.execute(
            "select slug from books where genres like '%Theology%' and (title like 'ANF%' or title like 'NPNF%') order by title")]
    else:
        slugs = [args.slug]
    for s in slugs:
        process(con, s)
    con.close()


if __name__ == "__main__":
    main()
