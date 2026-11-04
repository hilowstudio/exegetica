"""Seed an original Exegetica book (one written in-house as Markdown, e.g. docs/books/<name>/) into the Reading Room.

Reads the same folder scripts/book_pdf.py renders: its *.md parts in name order and book.json. The
book.json "library" entry gives the catalog fields:

    "library": {"slug": "...", "title": "Main: Subtitle", "author_sort": "Surname, Given",
                "section": ["Christianity"], "subjects": [...], "license": "© 2026 Name"}

Structure follows the Markdown headings, as in the PDF: a "#" part becomes a section of its own (its
title page), a "##" chapter becomes "Chapter N: Title" (the reader's typesetting pass turns that into the
"Chapter Ten" label over the title), and "##" sections before the first part or in "Back Matter" stay
unnumbered. The cover is the book's own cover-2x3.jpg (drawn by book_pdf.py), stored in covers.db.
Idempotent: re-running replaces the book.

    python scripts/seed_original_book.py docs/books/between-the-brackets [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

from markdown_it import MarkdownIt

_ROOT = Path(__file__).resolve().parent.parent
_MD = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "smartquotes"])  # no "replacements": (C) -> ©
_NUM = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty"]


def _words(h: str) -> int:
    return len(re.findall(r"[\w’']+", re.sub(r"<[^>]+>", " ", h)))


def build_sections(md_text: str) -> list[dict]:
    out, cur, in_part, back, n_ch = [], None, False, False, 0
    for line in md_text.splitlines():
        if line.startswith("# "):
            head = line[2:].strip()
            back, in_part, cur = head.lower() == "back matter", True, None
            if not back:                                    # a part: its own section, the title page
                out.append({"title": head, "head": head, "body": []})
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            if in_part and not back:
                n_ch += 1
                head = f"Chapter {_NUM[n_ch] if n_ch < len(_NUM) else n_ch}: {title}"
            else:
                head = title
            cur = {"title": head, "head": head, "body": []}
            out.append(cur)
            continue
        if cur is not None:
            cur["body"].append(line)
    for n, s in enumerate(out, 1):
        h = f"<h2>{_MD.renderInline(s['head'])}</h2>\n" + _MD.render("\n".join(s["body"]))
        s.update(section_number=n, html=h.strip(), words=_words(h))
    return out


def _cover_webp(book_dir: Path) -> tuple[bytes, int, int]:
    from PIL import Image
    im = Image.open(book_dir / "cover-2x3.jpg").convert("RGB")
    if im.width > 400:
        im = im.resize((400, round(im.height * 400 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=80)
    return buf.getvalue(), im.width, im.height


def store(book_dir: Path, meta: dict, sections: list[dict], books_db: Path, covers_db: Path) -> int:
    lib = meta["library"]
    wc = sum(s["words"] for s in sections)
    con = sqlite3.connect(books_db, timeout=120)
    cur = con.cursor()
    row = cur.execute("select id from books where slug=?", (lib["slug"],)).fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    section = json.dumps(lib["section"])
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,section,genres_backup,title_backup,cover_url,
                             chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (lib["slug"], lib["title"], meta["byline"], lib["author_sort"], "exegetica", lib["license"], 1, "en",
         json.dumps(lib.get("subjects", [])), section, section, section, lib["title"],
         f"/api/cover/{lib['slug']}", len(sections), wc))
    bid = cur.lastrowid
    cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                    [(bid, s["section_number"], s["title"], s["html"], s["words"]) for s in sections])
    con.commit()
    con.close()

    webp, w, h = _cover_webp(book_dir)
    ccon = sqlite3.connect(covers_db, timeout=120)
    ccon.execute("insert or replace into covers(slug,webp,src_url,w,h,bytes) values(?,?,?,?,?,?)",
                 (lib["slug"], webp, f"local:{(book_dir / 'cover-2x3.jpg').relative_to(_ROOT).as_posix()}", w, h, len(webp)))
    ccon.commit()
    ccon.close()
    return bid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("book_dir")
    ap.add_argument("--books-db", default="db/books.db")
    ap.add_argument("--covers-db", default="db/covers.db")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    book_dir = (_ROOT / a.book_dir).resolve()
    meta = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    md_text = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(book_dir.glob("*.md")))
    sections = build_sections(md_text)
    print(f"{meta['library']['title']}: {len(sections)} sections, {sum(s['words'] for s in sections):,} words")
    for s in sections:
        print(f"  {s['section_number']:>2}  {s['words']:>5}  {s['title']}")
    if a.dry_run:
        return
    bid = store(book_dir, meta, sections, _ROOT / a.books_db, _ROOT / a.covers_db)
    print(f"stored book id {bid} as {meta['library']['slug']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
