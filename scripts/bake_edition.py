"""Bake a title's Exegetica edition: run the typesetting pass once and store the result as the book's own
text, so the reader serves it as stored and no later change to the shared scripts can alter it.

A baked edition lives in edition_chapters (one row per chapter: the finished house HTML, its label and
name). From then on every review fix is a direct edit to that stored text (scripts/correct_book.py),
and once Adam's review is done the edition is marked verified and is final.

    python scripts/bake_edition.py <slug> […]            # bake (or re-bake a draft); refuses verified editions
    python scripts/bake_edition.py --verify <slug> […]   # mark reviewed editions final
    python scripts/bake_edition.py --status <slug> […]

books.edition_status: NULL (served live by the typesetting pass) · 'draft' (baked, under review) · 'verified'.
"""
from __future__ import annotations

import datetime
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from webapp import typeset as T  # noqa: E402

DB = ROOT / "db" / "books.db"

SCHEMA = """
create table if not exists edition_chapters (
  book_id integer not null, section_number integer not null,
  label text, name text, html text not null, words integer,
  primary key (book_id, section_number)
);
"""


def ensure(con) -> None:
    con.executescript(SCHEMA)
    cols = [r[1] for r in con.execute("pragma table_info(books)")]
    for col in ("edition_status", "edition_baked_at", "front_html"):
        if col not in cols:
            con.execute(f"alter table books add column {col} text")
    con.commit()


def bake(con, slug: str) -> str:
    row = con.execute("select id, chapter_count, edition_status from books where slug=?", (slug,)).fetchone()
    if not row:
        return "not in library"
    bid, n, status = row
    if status == "verified":
        return "verified; left untouched"
    con.execute("delete from edition_chapters where book_id=?", (bid,))
    words = 0
    for sn, title, h in con.execute("select section_number, title, html from book_chapters where book_id=? order by section_number",
                                    (bid,)).fetchall():
        html, label, name = T.typeset.__wrapped__(h, title or "", sn == 1, sn == n and n > 1)
        if not name:                                          # contents name for an untitled opening
            label, name = T.toc_entry(title or "", h[:30000] if sn == 1 else h[:700], sn == 1)
        w = len(T._html_text(html).split())
        words += w
        con.execute("insert into edition_chapters(book_id, section_number, label, name, html, words) values(?,?,?,?,?,?)",
                    (bid, sn, label, name, html, w))
    con.execute("update books set edition_status='draft', edition_baked_at=? where id=?",
                (datetime.datetime.now().isoformat(timespec="seconds"), bid))
    con.commit()
    return f"baked {n} chapters, {words:,} words"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(DB)
    ensure(con)
    args = [a.strip() for a in sys.argv[1:] if a.strip()]
    if args and args[0] == "--verify":
        for slug in args[1:]:
            n = con.execute("update books set edition_status='verified' where slug=? and edition_status='draft'", (slug,)).rowcount
            print(slug, "verified" if n else "not a baked draft")
        con.commit()
        return
    if args and args[0] == "--status":
        for slug in args[1:]:
            print(slug, con.execute("select edition_status, edition_baked_at from books where slug=?", (slug,)).fetchone())
        return
    for slug in args:
        print(f"{slug}: {bake(con, slug)}", flush=True)


if __name__ == "__main__":
    main()
