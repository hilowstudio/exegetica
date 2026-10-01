"""Audit the Reading Room's Theology corpus for under-ingested / shell books.

Three signals (root causes differ, so does the fix):
  1. books.db words  vs  theology_texts words (the local source) — if books.db has far fewer,
     it UNDER-INGESTED content the source has  → re-extractable (see --reextract / the
     chaptering fix in seed_theology_reader._ancestors).
  2. theology_texts words themselves tiny  → the HF source dataset is thin for this work
     → needs a CCEL re-fetch (can't be fixed from local data).
  3. theology_texts paragraphs  vs  cached CCEL TOC entry count — a big shortfall means the
     upstream dataset dropped divisions → also a CCEL re-fetch.

Prints a categorized report. Optional --reextract re-runs the (fixed) chaptering from the
stage db to confirm which are recoverable without CCEL (slow: ~8 min for the full corpus).

    .venv\\Scripts\\python.exe scripts\\audit_theology_ingestion.py
    .venv\\Scripts\\python.exe scripts\\audit_theology_ingestion.py --reextract
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOKS = os.path.join(_ROOT, "db", "books.db")
_THEO = os.path.join(_ROOT, "db", "theology.db")
_STAGE = os.path.join(_ROOT, ".seed_cache", "ccel_reader_stage.db")
_TOC = os.path.join(_ROOT, ".seed_cache", "ccel_toc")


def _n(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", (s or "").lower())).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reextract", action="store_true", help="confirm recoverability by re-chaptering the stage (slow)")
    args = ap.parse_args()

    b = sqlite3.connect(_BOOKS)
    t = sqlite3.connect(_THEO)
    # source words per work (chars/6 estimate), indexed by normalized title
    srcwords = {}
    for wid, ch in t.execute("select work_id, coalesce(sum(length(text)),0) from theology_texts group by work_id"):
        srcwords[wid] = (ch or 0) / 6.0
    title_wid = {}
    for wid, title in t.execute("select work_id, title from theology_works"):
        title_wid.setdefault(_n(title), []).append(wid)

    books = b.execute("select slug, title, chapter_count, word_count from books "
                      "where genres like '%Theology%'").fetchall()
    under, thin = [], []
    for slug, title, cc, wc in books:
        wids = title_wid.get(_n(title))
        if not wids:
            continue
        sw = max(srcwords.get(w, 0) for w in wids)
        if sw < 10:
            continue
        if sw < 1200 and wc < 1200:
            thin.append((slug, title[:44], wc, int(sw)))         # source itself thin → CCEL
        elif wc < 0.5 * sw and (sw - wc) > 3000:
            under.append((slug, title[:44], wc, int(sw)))        # source has more → re-extract

    print(f"Theology books: {len(books)}\n")
    print(f"=== UNDER-INGESTED — local source has more, re-extractable ({len(under)}) ===")
    for slug, title, wc, sw in sorted(under, key=lambda x: x[2] - x[3]):
        print(f"  db:{wc:>7}w  src~:{sw:>7}w  {title:44} {slug}")
    print(f"\n=== SOURCE-THIN — needs CCEL re-fetch ({len(thin)}) ===")
    for slug, title, wc, sw in sorted(thin, key=lambda x: x[2]):
        print(f"  db:{wc:>6}w  src~:{sw:>5}w  {title:44} {slug}")

    if args.reextract:
        import importlib.util
        spec = importlib.util.spec_from_file_location("s", os.path.join(_ROOT, "scripts", "seed_theology_reader.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        st = sqlite3.connect(_STAGE)
        meta = {ti: wp for ti, wp in st.execute("select title, workpath from meta")}
        print("\n=== re-extraction recovery check (stage → fixed chaptering) ===")
        for slug, title, wc, sw in under:
            rows = st.execute("select division, text, thml from stage where title=(select title from books where slug=?) order by sid", (slug,)).fetchall()
            wp = meta.get(next((r[1] for r in b.execute("select 1,title from books where slug=?", (slug,))), title))
            try:
                ch = (m.toc_chapters(rows, m.load_toc(wp)) if wp and m.load_toc(wp) else None) or m.build_chapters(rows)
                new = sum(c["words"] for c in ch)
            except Exception:
                new = -1
            verdict = "RECOVERABLE" if new > wc * 1.3 else "needs CCEL / other"
            print(f"  {wc:>7}w -> {new:>7}w  {verdict:18} {slug}")


if __name__ == "__main__":
    main()
