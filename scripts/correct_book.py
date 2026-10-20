"""Apply a title's reviewed corrections to the stored text (books.db), logged and repeatable.

Each title under review keeps its corrections in docs/corrections/<slug>.json, a list of operations:

  {"op": "insert", "chapter": 1, "at": "start" | "end", "html": "<p class=\"ex-ded\">To …</p>",
   "why": "dedication omitted at import; restored from the Standard Ebooks source"}
  {"op": "insert", "chapter": 21, "after": "exact text in the stored html", "html": "<p>…</p>", "why": "…"}
  {"op": "replace", "chapter": 21, "find": "exact text", "with": "replacement", "why": "…"}
  {"op": "delete", "chapter": 21, "find": "exact text", "why": "…"}

A baked edition (scripts/bake_edition.py) is edited in edition_chapters: that is the text the reader serves.
Books not yet baked are edited in book_chapters (the source the typesetting pass reads).

Operations are idempotent: an insert whose html is already present, or a replace whose `with` is already
there and `find` is gone, is skipped. Every applied change is appended to docs/edition-corrections.csv.

    python scripts/correct_book.py <slug> [--dry-run]
"""
from __future__ import annotations

import csv
import datetime
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "books.db"
LOG = ROOT / "docs" / "edition-corrections.csv"


def main() -> None:
    slug, dry = sys.argv[1], "--dry-run" in sys.argv
    ops = json.loads((ROOT / "docs" / "corrections" / f"{slug}.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(DB)
    bid, = con.execute("select id from books where slug=?", (slug,)).fetchone()
    try:
        baked = con.execute("select count(*) from edition_chapters where book_id=?", (bid,)).fetchone()[0] > 0
    except sqlite3.OperationalError:
        baked = False
    table = "edition_chapters" if baked else "book_chapters"
    log, today = [], datetime.date.today().isoformat()
    for op in ops:
        if op["op"] == "front":                               # a dedication / epigraph for the book's front page
            cur = con.execute("select coalesce(front_html, '') from books where id=?", (bid,)).fetchone()[0]
            if op["html"] in cur:
                continue
            new = op["html"] + cur if op.get("at") == "start" else cur + op["html"]
            log.append([today, slug, 0, "front", op.get("why", ""), "front_html", op["html"][:200]])
            if not dry:
                con.execute("update books set front_html=? where id=?", (new, bid))
            continue
        if op["op"] in ("name", "label"):                     # a baked edition's contents name / numeral for one chapter
            col = op["op"]
            cur = con.execute(f"select {col} from edition_chapters where book_id=? and section_number=?", (bid, op["chapter"])).fetchone()
            if not cur or cur[0] == op[col]:
                continue
            log.append([today, slug, op["chapter"], f"{col} (edition)", op.get("why", ""), cur[0], op[col]])
            if not dry:
                con.execute(f"update edition_chapters set {col}=? where book_id=? and section_number=?", (op[col], bid, op["chapter"]))
            continue
        n = op["chapter"]
        row = con.execute(f"select html from {table} where book_id=? and section_number=?", (bid, n)).fetchone()
        if not row:
            raise SystemExit(f"{slug}: no chapter {n}")
        h, new = row[0], None
        if op["op"] == "insert":
            if op["html"] in h:
                continue
            if op.get("at") == "start":
                new = op["html"] + h
            elif op.get("at") == "end":
                new = h + op["html"]
            else:
                anchor = op["after"]
                if h.count(anchor) != 1:
                    raise SystemExit(f"{slug} ch{n}: anchor found {h.count(anchor)} times: {anchor[:60]!r}")
                i = h.index(anchor) + len(anchor)
                new = h[:i] + op["html"] + h[i:]
        elif op["op"] == "replace":
            if op["find"] not in h and op["with"] in h:
                continue
            if h.count(op["find"]) != 1:
                raise SystemExit(f"{slug} ch{n}: text found {h.count(op['find'])} times: {op['find'][:60]!r}")
            new = h.replace(op["find"], op["with"])
        elif op["op"] == "delete":
            if op["find"] not in h:
                continue
            if h.count(op["find"]) != 1:
                raise SystemExit(f"{slug} ch{n}: text found {h.count(op['find'])} times: {op['find'][:60]!r}")
            new = h.replace(op["find"], "")
        if new is None or new == h:
            continue
        log.append([today, slug, n, op["op"] + (" (edition)" if baked else ""), op.get("why", ""), (op.get("find") or op.get("after") or op.get("at") or "")[:120],
                    (op.get("html") or op.get("with") or "")[:200]])
        if not dry:
            words = len(new.split())
            con.execute(f"update {table} set html=? where book_id=? and section_number=?", (new, bid, n))
            if not baked:
                con.execute("update books set word_count=(select sum(words) from book_chapters where book_id=?) where id=?", (bid, bid))
            del words
    if not dry:
        con.commit()
        new_file = not LOG.exists()
        with open(LOG, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new_file:
                w.writerow(["date", "slug", "chapter", "op", "why", "anchor", "change"])
            w.writerows(log)
    print(f"{slug}: {len(log)} correction(s) {'would be ' if dry else ''}applied")


if __name__ == "__main__":
    main()
