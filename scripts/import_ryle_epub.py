#!/usr/bin/env python3
"""
Import J.C. Ryle's *Expository Thoughts on the Gospels* (all four Gospels) from a local EPUB
into `commentaries` (source ryle-expository), served by get_commentary as passage-keyed
Gospel exposition. Ryle d.1900 → public domain.

The EPUB (Adam's own copy) is cleanly structured: each passage begins with a reference line
like "MARK 1:1-8", followed by Ryle's exposition paragraphs (no embedded KJV block). Passages
are keyed by [verse_start, verse_end] within a chapter, exactly like the section-level HelloAO
commentaries (Matthew Henry etc.), so a verse lookup finds the passage covering it.

    .venv\\Scripts\\python.exe scripts\\import_ryle_epub.py --dry-run   # per-Gospel counts + warnings
    .venv\\Scripts\\python.exe scripts\\import_ryle_epub.py             # write

This is a post-`build_database.py --rebuild` importer (re-run after any rebuild).
"""
from __future__ import annotations

import argparse
import html
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from studybible_mcp.database import create_schema, BOOK_ABBREV_MAP  # noqa: E402
from studybible_mcp.parsers.commentaries import COMMENTARIES  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EPUB = _ROOT / "Expository Thoughts  - J. C. Ryle.epub"
_DB = _ROOT / "db" / "study_bible.db"
_SOURCE = "ryle-expository"

# A passage header, e.g. "MARK 1:1-8", "JOHN 7:53-8:11", "LUKE 1:1-4".
_REF = re.compile(
    r"^(MATTHEW|MARK|LUKE|JOHN)\s+(\d+):(\d+)"
    r"(?:\s*[-–—]\s*(?:(\d+):)?(\d+))?\s*\.?\s*$",
    re.I,
)
_BOOK = {"MATTHEW": "Mat", "MARK": "Mrk", "LUKE": "Luk", "JOHN": "Jhn"}


def _clean(text: str) -> str:
    text = html.unescape(text)
    return re.sub(r"[ \t]*\n[ \t]*", "\n", re.sub(r"\n{3,}", "\n\n", text)).strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def _load_web(conn: sqlite3.Connection):
    """book,chapter,verse -> WEB text, to detect+strip the Scripture block Ryle prints before
    each exposition (the EPUB uses the public-domain WEB for it)."""
    web: dict[tuple, str] = {}
    for bk, ch, v, t in conn.execute(
            "SELECT book, chapter, verse, text FROM translations WHERE translation='WEB' "
            "AND book IN ('Mat','Mrk','Luk','Jhn')"):
        web[(bk, ch, v)] = t
    return web


def _ordered_paragraphs():
    """Yield the book's text blocks in reading order: (kind, text) where kind is 'ref' or 'body'."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(_EPUB))
    # spine order → document items
    id_to_item = {it.get_id(): it for it in book.get_items()}
    for spine_id, _ in book.spine:
        item = id_to_item.get(spine_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for el in soup.find_all(["h1", "h2", "h3", "p"]):
            t = " ".join(el.get_text().split())
            if not t:
                continue
            yield ("ref" if _REF.match(t) else "body"), t


def parse(web: dict):
    rows = []
    stripped = 0
    cur = None  # (book_code, chapter, vstart, vend)
    buf: list[str] = []

    def flush():
        nonlocal stripped
        if not (cur and buf):
            return
        # Drop the leading WEB Scripture block Ryle prints before his exposition. It can span
        # several paragraphs, so pop every leading paragraph whose text is contained in the
        # WEB text of this passage's verse range; stop at Ryle's first (non-Scripture) paragraph.
        bk, ch, vs, ve = cur
        hi = ve if ve < 900 else 200
        # The EPUB prints the passage text (a modernized public-domain edition, close to but not
        # exactly WEB) before Ryle's exposition. Pop leading paragraphs whose words are mostly the
        # passage's WEB words — Scripture scores high, Ryle's own prose scores low — regardless of
        # the exact edition. Stop at the first paragraph that is clearly Ryle.
        web_words = set()
        for v in range(vs, hi + 1):
            web_words.update(_words(web.get((bk, ch, v), "")))
        popped = False
        while buf and web_words:
            toks = _words(buf[0])
            if len(toks) >= 4 and sum(t in web_words for t in toks) / len(toks) >= 0.72:
                buf.pop(0)
                popped = True
            else:
                break
        if popped:
            stripped += 1
        body = _clean("\n\n".join(buf))
        if body:
            rows.append((*cur, body))

    for kind, t in _ordered_paragraphs():
        if kind == "ref":
            m = _REF.match(t)
            book, ch, vs, ch2, ve = m.group(1).upper(), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
            flush()
            buf = []
            if ch2 is not None and int(ch2) != ch:
                verse_end = 999  # cross-chapter (e.g. JOHN 7:53-8:11): open-ended in start chapter
            else:
                verse_end = int(ve) if ve else vs
            cur = (_BOOK[book], ch, vs, verse_end)
        else:
            if cur is not None:  # skip prefaces (body before the first ref)
                buf.append(t)
    flush()
    return rows, stripped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not _EPUB.exists():
        print(f"EPUB not found: {_EPUB}")
        sys.exit(1)
    if not _DB.exists():
        print(f"Database not found: {_DB}. Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(_DB)
    web = _load_web(conn)
    rows, stripped = parse(web)
    by_book: dict[str, int] = {}
    empties = 0
    for bk, ch, vs, ve, body in rows:
        by_book[bk] = by_book.get(bk, 0) + 1
        if not body:
            empties += 1
    print(f"parsed {len(rows):,} passages: " + ", ".join(f"{k}={v}" for k, v in by_book.items()))
    print(f"  stripped leading WEB Scripture block from {stripped}/{len(rows)} passages")
    cross = sum(1 for r in rows if r[3] == 999)
    if cross:
        print(f"  {cross} cross-chapter passage(s) keyed open-ended to their start chapter")
    if empties:
        print(f"  [warn] {empties} empty bodies")

    if args.dry_run:
        for bk, ch, vs, ve, body in rows[:4]:
            print(f"    {bk} {ch}:{vs}-{ve}  {body[:70]}")
        print("(dry run — nothing written)")
        conn.close()
        return

    name = COMMENTARIES[_SOURCE]
    try:
        create_schema(conn)
        conn.execute("DELETE FROM commentaries WHERE source = ?", (_SOURCE,))
        conn.executemany(
            "INSERT INTO commentaries "
            "(source, source_name, book, chapter, verse_start, verse_end, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(_SOURCE, name, bk, ch, vs, ve, body) for bk, ch, vs, ve, body in rows],
        )
        conn.execute("ANALYZE")
        conn.commit()
        n = conn.execute("SELECT count(*) FROM commentaries WHERE source = ?", (_SOURCE,)).fetchone()[0]
        print(f"[ok] imported {n:,} Ryle passages into commentaries (source={_SOURCE}).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
