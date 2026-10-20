"""Audit every Reading Room book as the reader serves it: the opening and closing pages after the
Exegetica typesetting pass, plus every contents entry. Writes one row per finding.

    python scripts/audit_interior.py [--limit N]   -> .seed_cache/reading_room/interior_audit.csv
"""
from __future__ import annotations

import collections
import csv
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from webapp import typeset as T  # noqa: E402

DB = ROOT / "db" / "books.db"
OUT = ROOT / ".seed_cache" / "reading_room" / "interior_audit.csv"

_OPEN_JUNK = re.compile(
    r"(?:Copyright|COPYRIGHT),?\s*(?:©|\(c\))?\s*(?:by\s+)?\d{4}|©\s*\d{4}|All rights reserved|Library of Congress|"
    r"\b(?:PUBLISHERS?|Publishers)\b|\b(?:Author|AUTHOR) of\b|\bC\s?O\s?N\s?T\s?E\s?N\s?T\s?S\b|\bContents\b|"
    r"List of Illustrations|LIST OF ILLUSTRATIONS|Printed (?:by|for|in)\b|PRINTED (?:BY|FOR|IN)\b|\bISBN\b|"
    r"Gutenberg|Transcriber|transcriber|Distributed Proofread|archive\.org|Internet Archive")
_CLOSE_JUNK = re.compile(
    r"Printed by|PRINTED BY|Printers?\b|Press of|Popular Copyright|BOOKS BY|Books by|Uniform with|Catalogue|CATALOGUE|"
    r"Price \$|\$\d+\.\d\d|net\.|Publishers?,|PUBLISHERS|Transcriber|Gutenberg|Advertisement|ADVERTISEMENT|"
    r"Each volume|Cloth, \d|12mo|8vo|16mo")


def main() -> None:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    con = sqlite3.connect(DB)
    books = con.execute("select id, slug, title, chapter_count, genres from books order by id").fetchall()
    if limit:
        books = books[:limit]
    rows, t0 = [], time.time()
    for k, (bid, slug, title, n, genres) in enumerate(books):
        if "Poetry" in (genres or ""):
            continue                                          # poetry is a later, separate pass
        try:
            audit_book(con, rows, bid, slug, n)
        except Exception as e:  # noqa: BLE001 — one bad book never stops the audit
            rows.append({"slug": slug, "section": 0, "kind": "typeset error", "detail": f"{type(e).__name__}: {e}"[:160]})
        if k % 500 == 0:
            print(f"{k}/{len(books)} books, {len(rows)} findings, {time.time() - t0:.0f}s", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["slug", "section", "kind", "detail"])
        w.writeheader()
        w.writerows(rows)
    print("books with findings:", len({r["slug"] for r in rows}))
    for kind, c in collections.Counter(r["kind"] for r in rows).most_common():
        print(f"{c:6}  {kind}")


def audit_book(con, rows: list, bid: int, slug: str, n: int) -> None:
    if True:
        toc = con.execute("select section_number, title, substr(html, 1, case when section_number = 1 then 30000 else 700 end) "
                          "from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
        for sn, t, head in toc:
            label, name = T.toc_entry(t, head or "", sn == 1)
            name, _syn = T.synopsis(name)                     # the reader shows the first clause as the name
            issue = None
            if not name:
                issue = "empty contents name"
            elif name.strip(" .:").lower() in T._FRAGMENTS:
                issue = "fragment contents name"
            elif " · " in name and not label:
                issue = "prefix left in contents name"
            elif len(name) > 140:
                issue = "very long contents name"
            elif sum(c.isupper() for c in name) > 0.8 * max(1, sum(c.isalpha() for c in name)) and len(name) > 12:
                issue = "capitals in contents name"
            if issue:
                rows.append({"slug": slug, "section": sn, "kind": issue, "detail": name[:160]})
        first = con.execute("select title, html from book_chapters where book_id=? and section_number=1", (bid,)).fetchone()
        if first:
            html, label, name = T.typeset(first[1], first[0], True)
            body = T._html_text(re.sub(r"(?s)<header.*?</header>", "", html))[:1500]
            m = _OPEN_JUNK.search(body)
            if m:
                rows.append({"slug": slug, "section": 1, "kind": "front matter left in opening",
                             "detail": body[max(0, m.start() - 60):m.end() + 80]})
            if not name:
                rows.append({"slug": slug, "section": 1, "kind": "untitled opening", "detail": body[:120]})
        last = con.execute("select title, html from book_chapters where book_id=? and section_number=?", (bid, n)).fetchone()
        if last and n > 1:
            html, _l, _n = T.typeset(last[1], last[0], False)
            body = T._html_text(html)
            tail = body[-1800:]
            m = _CLOSE_JUNK.search(tail)
            if m:
                rows.append({"slug": slug, "section": n, "kind": "back matter left at the end",
                             "detail": tail[max(0, m.start() - 80):m.end() + 80]})
            end = re.search(r"\bTHE END\b\.?|\bFINIS\b\.?", body)
            if end and len(body) - end.end() > 300:
                rows.append({"slug": slug, "section": n, "kind": "text after THE END",
                             "detail": body[end.end():end.end() + 200]})


if __name__ == "__main__":
    main()
