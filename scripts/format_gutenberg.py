"""Per-book cleanup for Project Gutenberg titles in the Reading Room.

Gutenberg HTML is content-rich but carries production cruft the SE/CCEL recipes don't address:
  - PG license / "*** START|END OF THE PROJECT GUTENBERG EBOOK ***" markers and the boilerplate
    licence block, plus transcriber's notes ("Transcribed from … by … pglaf.org");
  - chapters that begin with such a provenance <p> instead of their heading (so the reader shows
    no chapter title);
  - inert <span>, stray leading/trailing whitespace.
Rich markup (tables, blockquote, lists, <i>/<b>, headings h1–h6) is preserved. Chapter STRUCTURE
is left alone here (splitting blobs / dedup are separate, judged per book).

    from scripts.format_gutenberg import clean_book, qa
    clean_book(con, book_id)          # strips PG cruft, normalizes each chapter's leading heading
"""
from __future__ import annotations

import html as _html
import re

# lines/paragraphs that are pure Project Gutenberg production cruft
_PG_LINE = re.compile(
    r"project\s+gutenberg|gutenberg[‑-]tm|pglaf\.org|www\.gutenberg|gutenberg literary archive"
    r"|this e-?book is for the use of anyone|\bproduced by\b|\btranscribed (from|by)\b"
    r"|\*\*\*\s*(start|end) of th",
    re.I,
)


def _strip_pg(html: str) -> str:
    # drop whole <p>/<div> blocks that are PG cruft
    def drop(m: str) -> str:
        return "" if _PG_LINE.search(re.sub(r"<[^>]+>", " ", m)) else m

    html = re.sub(r"<p\b[^>]*>.*?</p>", lambda m: drop(m.group(0)), html, flags=re.S | re.I)
    html = re.sub(r"<div\b[^>]*>\s*(?:<[^>]+>\s*)*</div>", "", html, flags=re.S | re.I)  # emptied divs
    # a bare "*** START/END OF …" marker line not wrapped in <p>
    html = re.sub(r"\*\*\*\s*(START|END) OF TH.*?\*\*\*", "", html, flags=re.S | re.I)
    return html


def _norm_ws(html: str) -> str:
    html = re.sub(r"</?span>", "", html)                    # inert spans
    html = re.sub(r"<span[^>]*>\s*</span>", "", html)
    html = re.sub(r"(?:<br\s*/?>\s*){3,}", "<br/><br/>", html)  # runs of <br>
    return re.sub(r"\s+", " ", html).strip()


def clean_book(con, bid: int) -> None:
    rows = con.execute(
        "select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)
    ).fetchall()
    for n, title, html in rows:
        h = _strip_pg(html)
        h = _norm_ws(h)
        # drop any leading now-orphaned inline/empty tags
        h = re.sub(r"^(?:\s*<(?:br|hr)\s*/?>\s*)+", "", h)
        # ensure the chapter opens on a heading: if it doesn't, and we have a title, inject one
        if not re.match(r"\s*<h[1-6]\b", h, re.I):
            h = f"<h2>{_html.escape(title.strip())}</h2>\n{h}"
        h = re.sub(r"</p>", "</p>\n", h).strip()
        words = len(re.sub(r"<[^>]+>", " ", h).split())
        con.execute("update book_chapters set html=?, words=? where book_id=? and section_number=?",
                    (h, words, bid, n))
    tot = con.execute("select coalesce(sum(words),0), count(*) from book_chapters where book_id=?", (bid,)).fetchone()
    con.execute("update books set word_count=?, chapter_count=? where id=?", (tot[0], tot[1], bid))
    con.commit()


def dedup_book(con, bid: int) -> int:
    """Disambiguate duplicate chapter titles (no ToC available): prefix each repeat with the
    nearest preceding non-repeated title; anything still colliding gets a sequential (n) suffix.
    Updates the title column and the chapter's leading heading. Returns count changed."""
    rows = con.execute("select section_number, title from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
    from collections import Counter
    rep = {t for t, n in Counter(r[1].strip() for r in rows).items() if n > 1}
    if not rep:
        return 0
    ren: dict[int, str] = {}
    last = None
    for sn, t in rows:
        ts = t.strip()
        if ts in rep and last:
            ren[sn] = f"{last} · {ts}"
        elif ts not in rep:
            last = ts
    # sequential fallback for whatever the context pass didn't separate
    proposed = {sn: ren.get(sn, dict(rows)[sn].strip() if False else next(t for s, t in rows if s == sn).strip()) for sn, _ in rows}
    cnt = Counter(proposed.values())
    seen: dict[str, int] = {}
    for sn, t in rows:
        v = proposed[sn]
        if cnt[v] > 1:
            seen[v] = seen.get(v, 0) + 1
            ren[sn] = f"{v} ({seen[v]})"
    for sn, newt in ren.items():
        h = con.execute("select html from book_chapters where book_id=? and section_number=?", (bid, sn)).fetchone()[0]
        nh = re.sub(r"(<(h[1-6])\b[^>]*>).*?(</\2>)", lambda m: m.group(1) + _html.escape(newt) + m.group(3),
                    h, count=1, flags=re.S | re.I)
        con.execute("update book_chapters set title=?, html=? where book_id=? and section_number=?", (newt, nh, bid, sn))
    con.commit()
    return len(ren)


def qa(con, bid: int) -> None:
    rows = con.execute("select title, html, words from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
    allh = "\n".join(r[1] for r in rows)
    print(f"  chapters: {len(rows)} | words: {sum(r[2] for r in rows):,}")
    print(f"  all start <h#>: {all(r[1].lstrip().lower().startswith('<h') for r in rows)}")
    print(f"  PG cruft left: {bool(_PG_LINE.search(re.sub(r'<[^>]+>',' ',allh)))} | leaks: {len(re.findall(r'&gt;|&lt;', allh))}")
    print(f"  dup titles: {len(rows) - len({r[0].strip() for r in rows})}")
