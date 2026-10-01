"""Seed John Duncan's *Colloquia Peripatetica* (ed. William Knight, 5th ed., enlarged, 1879) into the Reading Room.

Source: archive.org `colloquiaperipat02dunciala` (ABBYY OCR), hand-corrected against the page scans and a
second independent scan (`colloquiaperipat00knig`) into `.seed_cache/duncan/work.md`. This script only
converts that proofed working file into chapter HTML and stores it.

work.md conventions
  <!-- idxN -->        scan page marker (dropped)
  ## Title            new chapter (one per colloquy; Prefatory Note, Preface, Biographical Sketch first)
  ### Title           sub-heading inside a chapter
  > line              verse / displayed quotation (consecutive lines form one block)
  [fn] \\* text       footnote (collected to the chapter end, renumbered 1, 2, ... in marker order)
  [sig] text          right-aligned signature line
  *text*              italics; \\* is a literal asterisk = footnote marker in running text; † likewise

    python scripts/seed_duncan_colloquia.py [--dry-run] [--db db/books.db]
"""
import argparse
import html as _html
import json
import re
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
WORK = _ROOT / ".seed_cache" / "duncan" / "work.md"
ITEM = {
    "slug": "john-duncan_colloquia-peripatetica-ia",
    "title": "Colloquia Peripatetica",
    "raw_title": "Colloquia Peripatetica: Deep-Sea Soundings, Being Notes of Conversations with the Late "
                 "John Duncan, LL.D. (ed. William Knight, 5th ed., enlarged, 1879)",
    "author": "John Duncan",
    "author_sort": "Duncan, John",
    "source": "archive.org",
    "license": "PD-US",
    "subjects": ["Theology", "Philosophy and religion", "Table-talk"],
    "cover": "https://archive.org/download/colloquiaperipat02dunciala/page/n6.jpg",
}
SECTION = ["Christianity"]
MARK = "\u0000M\u0000"  # placeholder for a footnote marker while italics are converted


def _quotes(s: str) -> str:
    """Straight quotes -> typographic. Runs on escaped HTML text without tags."""
    s = re.sub(r'(^|[\s(\[—–‘/])"', "\\1“", s)
    s = s.replace('"', "”")
    s = re.sub(r"(^|\s)\*”", "\\1*“", s)  # opening quote just inside an italic span
    s = re.sub(r"(^|[\s(\[—–“/])'(?=[\w*<])", "\\1‘", s)
    return s.replace("'", "’")


def _inline(s: str, marks: list) -> str:
    """Markdown-ish inline -> HTML. Footnote markers become numbered <sup>; returns html."""
    s = s.replace("\\*", MARK).replace("†", MARK)
    s = _html.escape(s, quote=False)
    s = _quotes(s)
    if s.count("*") % 2:
        raise ValueError(f"unbalanced italics: {s[:120]!r}")
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    while MARK in s:
        marks.append(1)
        s = s.replace(MARK, f"<sup>{len(marks)}</sup>", 1)
    return s


def _words(h: str) -> int:
    return len(re.findall(r"[\w’']+", re.sub(r"<[^>]+>", " ", h)))


def build_chapters(text: str) -> list[dict]:
    chapters, cur = [], None
    lines = [ln for ln in text.split("\n") if not ln.startswith("<!--")]
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("## "):
            cur = {"raw": ln[3:].strip(), "body": [], "notes": [], "marks": []}
            chapters.append(cur)
            i += 1
            continue
        if cur is None or not ln.strip():
            i += 1
            continue
        if ln.startswith("### "):
            cur["body"].append(f"<h3>{_inline(ln[4:].strip(), [])}</h3>")
        elif ln.startswith("> "):
            block = []
            while i < len(lines) and lines[i].startswith("> "):
                block.append(_inline(lines[i][2:].strip(), cur["marks"]))
                i += 1
            cur["body"].append("<blockquote><p>" + "<br>\n".join(block) + "</p></blockquote>")
            continue
        elif ln.startswith("[fn]"):
            note = re.sub(r"^\[fn\]\s*(\\\*|†)\s*", "", ln)
            cur["notes"].append(_inline(note, []))
        elif ln.startswith("[sig]"):
            cur["body"].append(f'<p style="text-align:right">{_inline(ln[5:].strip(), [])}</p>')
        else:
            cur["body"].append(f"<p>{_inline(ln.strip(), cur['marks'])}</p>")
        i += 1

    out = []
    for n, c in enumerate(chapters, 1):
        head_marks: list = []
        head_html = _inline(c["raw"], head_marks)
        title = re.sub(r"<[^>]+>", "", _inline(c["raw"].replace("\\*", ""), []))
        title = _html.unescape(title)
        # a marker on the heading itself is note 1; body markers follow it
        body_marks = len(c["marks"])
        total = len(head_marks) + body_marks
        if total != len(c["notes"]):
            raise ValueError(f"{title}: {total} markers vs {len(c['notes'])} notes")
        body = "\n".join(c["body"])
        if head_marks:  # shift body numbering by one
            body = re.sub(r"<sup>(\d+)</sup>", lambda m: f"<sup>{int(m.group(1)) + 1}</sup>", body)
        h = f"<h2>{head_html}</h2>\n{body}"
        if c["notes"]:
            h += "\n<hr>\n" + "\n".join(
                f"<p><small><sup>{k}</sup> {t}</small></p>" for k, t in enumerate(c["notes"], 1))
        out.append({"section_number": n, "title": title, "html": h, "words": _words(h)})
    return out


def _store(con, chapters):
    wc = sum(c["words"] for c in chapters)
    cur = con.cursor()
    row = cur.execute("select id from books where slug=?", (ITEM["slug"],)).fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,section,genres_backup,title_backup,cover_url,
                             chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ITEM["slug"], ITEM["title"], ITEM["author"], ITEM["author_sort"], ITEM["source"],
         ITEM["license"], 1, "en", json.dumps(ITEM["subjects"]), json.dumps(SECTION),
         json.dumps(SECTION), json.dumps(SECTION), ITEM["raw_title"], ITEM["cover"],
         len(chapters), wc))
    bid = cur.lastrowid
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in chapters])
    con.commit()
    return bid, wc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--dump", help="write the assembled HTML to this file for review")
    args = p.parse_args()
    chapters = build_chapters(WORK.read_text(encoding="utf-8"))
    wc = sum(c["words"] for c in chapters)
    notes = sum(c["html"].count("<small>") for c in chapters)
    print(f"{ITEM['title']}: {len(chapters)} chapters, {wc:,} words, {notes} footnotes")
    if args.dump:
        Path(args.dump).write_text(
            "<meta charset=utf-8><style>body{max-width:44em;margin:2em auto;font:17px/1.6 Georgia}"
            "blockquote{font-style:italic;border-left:3px solid #ccc;padding-left:1em}</style>\n"
            + "\n<hr style='margin:3em 0'>\n".join(c["html"] for c in chapters), encoding="utf-8")
    if args.dry_run:
        return
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    bid, wc = _store(con, chapters)
    con.close()
    print(f"stored book id {bid} ({wc:,} words)")


if __name__ == "__main__":
    main()
