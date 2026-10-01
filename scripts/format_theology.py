"""Per-book beautification helpers for the Reading Room's Theology (CCEL) titles.

NOT a batch job — I run this per title, after personally inspecting the book, passing that
book's specific decisions (drops, renames). The mechanical baseline it applies to every book:
  - inject the chapter title as an <h2> heading when the chapter has none (CCEL chapters start
    straight into <p>, so the reader shows no chapter header without this);
  - strip stray entities/artifacts leaked into a title ("&gt;…");
  - normalize hard-wrapped source whitespace into flowing paragraphs (no leading/trailing space
    inside block tags; inline <i>/<b> spacing preserved);
  - drop the sections I flag as pure boilerplate and renumber the rest contiguously.
The historical text (archaic spelling, orthography) is never altered.

Usage (from a per-book heredoc):
    from scripts.format_theology import apply_baseline, qa
    apply_baseline(con, bid, drops={45}, renames={1: "Title Page"})
    qa(con, bid)
"""
from __future__ import annotations

import html as _html
import re

_BLOCK = r"(?:p|blockquote|li|ul|ol|h[1-6])"


def clean_title(t: str) -> str:
    t = re.sub(r"^\s*(?:&gt;|>)\s*", "", t or "")
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"[.,;:]+$", "", t).strip()  # drop trailing heading punctuation (keeps ? and !)


def norm_body(h: str) -> str:
    b = re.sub(r"\s+", " ", (h or "").strip())
    b = re.sub(r"<p>\s*(?:<br\s*/?>\s*)*</p>", "", b)     # drop wholly-empty paragraphs (<p><br/></p>)
    b = re.sub(r"<(sup|sub|i|b|em|strong)>\s*</\1>", "", b)  # drop empty inline tags (footnote-marker residue)
    b = re.sub(rf"(<{_BLOCK}\b[^>]*>)\s+", r"\1", b)     # no leading space inside a block tag
    b = re.sub(rf"\s+(</{_BLOCK}>)", r"\1", b)            # no trailing space inside a block tag
    return b.replace("</p>", "</p>\n").strip()


def apply_baseline(con, bid: int, drops: set[int] | None = None, renames: dict[int, str] | None = None) -> tuple[int, int]:
    """Rewrite a book's chapters in place. drops/renames are keyed by the CURRENT section_number.
    Returns (chapter_count, word_count)."""
    drops, renames = drops or set(), renames or {}
    rows = con.execute(
        "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
    ).fetchall()
    con.execute("delete from book_chapters where book_id=?", (bid,))
    num = total = 0
    for n, title, hbody in rows:
        if n in drops:
            continue
        num += 1
        t = renames.get(n) or clean_title(title)
        body = norm_body(hbody)
        body = re.sub(r"^\s*<h[1-6]>.*?</h[1-6]>\s*", "", body, flags=re.S | re.I)  # drop any prior injected heading
        body = f"<h2>{_html.escape(t)}</h2>\n{body}"                                  # always (re)inject to match the title
        words = len(re.sub(r"<[^>]+>", " ", body).split())
        total += words
        con.execute(
            "insert into book_chapters(book_id, section_number, title, html, words) values(?,?,?,?,?)",
            (bid, num, t, body, words),
        )
    con.execute("update books set chapter_count=?, word_count=? where id=?", (num, total, bid))
    con.commit()
    return num, total


def qa(con, bid: int) -> None:
    rows = con.execute(
        "select section_number, title, html, words from book_chapters where book_id=? order by section_number", (bid,)
    ).fetchall()
    allh = "\n".join(r[2] for r in rows)
    tags = sorted(set(re.findall(r"<(\w+)", allh)))
    print(f"  chapters: {len(rows)} | words: {sum(r[3] for r in rows):,}")
    print(f"  all start with <h#>: {all(r[2].lstrip().lower().startswith('<h') for r in rows)}")
    print(f"  entity leaks &gt;/&lt;: {len(re.findall(r'&gt;|&lt;', allh))} | U+FFFD: {allh.count(chr(0xfffd))}")
    print(f"  tags used: {tags}")
    thin = [(r[0], r[1][:30]) for r in rows if r[3] < 15]
    print(f"  thin chapters (<15w): {thin[:15]}")
