#!/usr/bin/env python3
"""
Import Charles Hodge's *Commentary on the Epistle to the Romans* from a local EPUB into
`commentaries` (source hodge-romans), served by get_commentary as passage-keyed exposition.
Hodge d.1878 → public domain (Adam's own copy).

The EPUB is cleanly structured: real section headers are <h3> ("ROMANS 1:1-17", "CHAPTER 2"),
while the front table-of-contents is <p> — so we key off heading tags and ignore the TOC. Each
ROMANS <h3> begins a passage; its body (ANALYSIS + COMMENTARY + the inline "VERSE N." notes) runs
to the next <h3>. Hodge weaves the verse text into his verse notes, so there is no separate
Scripture block to strip. PREFACE / INTRODUCTION / chapter overviews are not verse-keyable and are
skipped.

    .venv\\Scripts\\python.exe scripts\\import_hodge_romans.py --dry-run
    .venv\\Scripts\\python.exe scripts\\import_hodge_romans.py

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
from studybible_mcp.database import create_schema  # noqa: E402
from studybible_mcp.parsers.commentaries import COMMENTARIES  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EPUB = _ROOT / "A Commentary on Romans - Hodge (1).epub"
_DB = _ROOT / "db" / "study_bible.db"
_SOURCE = "hodge-romans"
_BOOK = "Rom"

_REF = re.compile(
    r"^ROMANS\s+(\d+):(\d+)"
    r"(?:\s*[-–—]\s*(?:(\d+):)?(\d+))?\s*\.?\s*$",
    re.I,
)


def _clean(text: str) -> str:
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# A per-verse note marker inside the COMMENTARY, e.g. "VERSE 1.", "VERSES 6, 7.", "VERSES 3-5.".
_VMARK = re.compile(r"(?im)^VERSES?\s+(\d+(?:\s*(?:[,–\-]|and)\s*\d+)*)\s*\.")


def _split_section(ch: int, vs: int, ve: int, body: str):
    """Yield fine-grained rows for one section: a section-range ANALYSIS overview + one row per
    'VERSE N.' note in the COMMENTARY. Falls back to a single section row if unstructured."""
    ci = body.find("COMMENTARY")
    analysis = body[:ci] if ci != -1 else ""
    commentary = body[ci + len("COMMENTARY"):] if ci != -1 else ""

    analysis = re.sub(r"^\s*ANALYSIS\s*", "", analysis).strip()
    if analysis:
        yield (_BOOK, ch, vs, ve, _clean(analysis))  # section overview, keyed to the whole range

    marks = list(_VMARK.finditer(commentary))
    if not marks:
        if ci == -1:  # no ANALYSIS/COMMENTARY structure at all → keep the section whole
            yield (_BOOK, ch, vs, ve, _clean(body))
        return
    for i, mk in enumerate(marks):
        nums = [int(x) for x in re.findall(r"\d+", mk.group(1))]
        v_s, v_e = min(nums), max(nums)
        seg = commentary[mk.end(): marks[i + 1].start() if i + 1 < len(marks) else len(commentary)]
        text = _clean(seg)
        if text:
            yield (_BOOK, ch, v_s, v_e, text)


def _elements():
    """Yield (is_heading, text) for h*/p elements across the book in spine order."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(_EPUB))
    idmap = {it.get_id(): it for it in book.get_items()}
    for sid, _ in book.spine:
        it = idmap.get(sid)
        if it is None or it.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(it.get_content(), "html.parser")
        for el in soup.find_all(["h1", "h2", "h3", "h4", "p"]):
            t = " ".join(el.get_text().split())
            if t:
                yield el.name.startswith("h"), t


def parse():
    rows = []
    cur = None
    buf: list[str] = []

    def flush():
        if cur and buf:
            body = _clean("\n\n".join(buf))
            if body:
                rows.extend(_split_section(*cur, body))

    for is_heading, t in _elements():
        if is_heading:
            m = _REF.match(t)
            flush()
            buf = []
            if m:  # real passage header (only ever an <h3>, never the <p> TOC)
                ch, vs, ch2, ve = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
                verse_end = 999 if (ch2 and int(ch2) != ch) else (int(ve) if ve else vs)
                cur = (ch, vs, verse_end)
            else:  # CHAPTER n / PREFACE / INTRODUCTION / title → reset; skip until next passage
                cur = None
        elif cur is not None:
            buf.append(t)
    flush()
    return rows


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

    rows = parse()
    chapters = sorted({r[1] for r in rows})
    print(f"parsed {len(rows)} passages across chapters {chapters[0]}-{chapters[-1]} "
          f"({len(chapters)} of 16)")
    cross = sum(1 for r in rows if r[3] == 999)
    if cross:
        print(f"  {cross} cross-chapter passage(s)")

    if args.dry_run:
        for bk, ch, vs, ve, body in rows[:4]:
            print(f"    {bk} {ch}:{vs}-{ve} ({len(body)}c)  {body[:70]}")
        print("(dry run — nothing written)")
        return

    name = COMMENTARIES[_SOURCE]
    conn = sqlite3.connect(_DB)
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
        print(f"[ok] imported {n} Hodge-on-Romans passages into commentaries (source={_SOURCE}).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
