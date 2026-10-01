"""Disambiguate duplicate chapter titles in Standard Ebooks books using the SE Table of Contents.

SE books are richly + cleanly formatted (h2 parts / h3 chapters, semantic HTML). Our flat
book_chapters extraction lost the part context, so numbered chapters collide in the reader's TOC
("I, II … I, II …" across parts). This fetches the book's toc.xhtml from the SE GitHub org, reads
the part → chapter hierarchy, aligns it to our chapters in order, and for chapters whose title is a
duplicate, rewrites the title (and its leading heading) as "Part Name · Chapter". SE markup is
otherwise preserved untouched.

    .venv\\Scripts\\python.exe scripts\\requalify_se.py <slug> [<slug> ...] [--commit]
"""
from __future__ import annotations

import html as _html
import re
import sqlite3
import sys
import urllib.request
from collections import Counter

from bs4 import BeautifulSoup

_ROOT = __file__.rsplit("\\", 2)[0] if "\\" in __file__ else __file__.rsplit("/", 2)[0]
_BOOKS = _ROOT + "/db/books.db"
_MID = " · "
_BOILER = {"titlepage", "title page", "imprint", "colophon", "uncopyright", "halftitle",
           "half-title", "half title", "endnotes"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _clean_part(p: str) -> str:
    # "Part I : Childhood" -> "Part I: Childhood"
    return re.sub(r"\s*:\s*", ": ", re.sub(r"\s+", " ", p).strip())


def fetch_toc_leaves(slug: str):
    """Ordered [(label, part_or_None)] for content leaves, excluding SE boilerplate."""
    data = None
    for branch in ("master", "main"):
        url = f"https://raw.githubusercontent.com/standardebooks/{slug}/{branch}/src/epub/toc.xhtml"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                if r.status == 200:
                    data = r.read().decode("utf-8", "replace"); break
        except Exception:  # noqa: BLE001
            continue
    if not data:
        return None
    soup = BeautifulSoup(data, "html.parser")
    nav = next((n for n in soup.find_all("nav")
                if "toc" in (n.get("epub:type", "") + " " + (n.get("id") or ""))), None) \
        or (soup.find_all("nav") or [None])[0]
    root_ol = nav.find("ol") if nav else None
    if not root_ol:
        return None
    leaves: list[tuple[str, str | None]] = []

    def walk(ol, part):
        for li in ol.find_all("li", recursive=False):
            a = li.find(["a", "span"], recursive=False)
            label = a.get_text(" ", strip=True) if a else ""
            sub = li.find("ol", recursive=False)
            if sub:
                # a node with children is a part/section; its label becomes the part for its leaves
                walk(sub, _clean_part(label) if label else part)
            else:
                if _norm(label) and label.strip().lower() not in _BOILER:
                    leaves.append((label.strip(), part))

    walk(root_ol, None)
    return leaves


def requalify(con, slug: str) -> tuple[int, int]:
    bid = con.execute("select id from books where slug=?", (slug,)).fetchone()[0]
    rows = con.execute(
        "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
    ).fetchall()
    leaves = fetch_toc_leaves(slug)
    if not leaves:
        print(f"  {slug}: could not fetch/parse SE ToC — skipped")
        return 0, len(rows) - len({r[1].strip() for r in rows})

    def chapnum(lbl: str) -> str:
        # leading number token: "I : When Wolves…" -> "I"
        return re.split(r"\s*:\s*", lbl, maxsplit=1)[0].strip()

    def clean_label(lbl: str) -> str:
        return re.sub(r"\s*:\s*", ": ", re.sub(r"\s+", " ", lbl).strip())

    # Prefix by part only for genuinely multi-part books. A book with ≥2 distinct part-nodes gets
    # every part-nested chapter prefixed (uniform within each part); a lone wrapper node (SE nests
    # the whole book under one node = the title) adds no prefix — we just enrich the bare label.
    n_parts = len({p for _, p in leaves if p})
    multi_part = n_parts >= 2

    ren: dict[int, str] = {}
    ti = 0
    for sn, title, _ in rows:
        base = title.split(_MID)[-1].strip()  # strip any prior prefix → idempotent re-runs
        j = next((k for k in range(ti, len(leaves))
                  if _norm(leaves[k][0]) == _norm(base) or _norm(chapnum(leaves[k][0])) == _norm(base)), None)
        if j is None:
            continue
        label, part = leaves[j]; ti = j + 1
        full = clean_label(label)
        if multi_part and part and _norm(part) not in _norm(full):
            newt = f"{part}{_MID}{full}"
        else:
            newt = full  # single-wrapper or top-level → richest bare label (drops redundant prefix)
        if newt != title.strip():
            ren[sn] = newt

    for sn, newt in ren.items():
        old = con.execute("select html from book_chapters where book_id=? and section_number=?", (bid, sn)).fetchone()[0]
        # rewrite the leading heading's text to the disambiguated title (keep its tag)
        new = re.sub(r"(<(h[1-6])\b[^>]*>).*?(</\2>)", lambda m: m.group(1) + _html.escape(newt) + m.group(3),
                     old, count=1, flags=re.S | re.I)
        con.execute("update book_chapters set title=?, html=? where book_id=? and section_number=?",
                    (newt, new, bid, sn))
    r2 = con.execute("select title from book_chapters where book_id=?", (bid,)).fetchall()
    return len(ren), len(r2) - len({x[0].strip() for x in r2})


def main() -> None:
    args = sys.argv[1:]
    commit = "--commit" in args
    slugs = [a for a in args if not a.startswith("--")]
    con = sqlite3.connect(_BOOKS)
    for slug in slugs:
        if not con.execute("select 1 from books where slug=?", (slug,)).fetchone():
            print(f"{slug}: not found"); continue
        n, dups = requalify(con, slug)
        print(f"{slug}: retitled={n} remaining_dups={dups}")
    if commit:
        con.commit(); print("committed")
    else:
        con.rollback(); print("(dry-run; pass --commit to save)")


if __name__ == "__main__":
    main()
