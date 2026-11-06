"""Delete Reading Room books by slug, and log each one so it can be found (and re-imported) later.

Removes the book's chapters and row from db/books.db and its cover from db/covers.db, then appends
one line per book to docs/reading-room/reading-room-deletions.csv (date, slug, title, author, gutenberg id,
reason). Reads a CSV with at least `slug` and `reason` columns.

    python scripts/delete_books.py approved.csv [--dry-run]
"""
from __future__ import annotations

import csv
import datetime
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "reading-room" / "reading-room-deletions.csv"


def main():
    path, dry = sys.argv[1], "--dry-run" in sys.argv
    todo = list(csv.DictReader(open(path, encoding="utf-8")))
    books = sqlite3.connect(ROOT / "db" / "books.db")
    covers = sqlite3.connect(ROOT / "db" / "covers.db")
    today = datetime.date.today().isoformat()
    new_log = not LOG.exists() or LOG.stat().st_size == 0
    done = 0
    # a dry run must not touch the log (creating it empty would drop the header on the real run)
    with open(os.devnull if dry else LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_log and not dry:
            w.writerow(["date", "slug", "title", "author", "gutenberg", "reason"])
        for r in todo:
            row = books.execute("select id, title, author from books where slug=?", (r["slug"],)).fetchone()
            if not row:
                print(f"  not found: {r['slug']}")
                continue
            if not dry:
                books.execute("delete from book_chapters where book_id=?", (row[0],))
                books.execute("delete from books where id=?", (row[0],))
                covers.execute("delete from covers where slug=?", (r["slug"],))
                m = re.search(r"-pg(\d+)$", r["slug"])
                w.writerow([today, r["slug"], row[1], row[2], m.group(1) if m else "", r["reason"]])
            done += 1
    if not dry:
        books.commit()
        covers.commit()
    print(f"{'would delete' if dry else 'deleted'} {done} of {len(todo)}")


if __name__ == "__main__":
    main()
