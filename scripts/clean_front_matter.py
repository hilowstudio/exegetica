"""Remove source front and back matter that an Exegetica edition replaces or that means nothing in it.

Every book now opens on our own title page, colophon and contents, and has no printed pages, so these
source chapters go: old contents lists, lists of illustrations/maps, page-number indexes, errata,
transcriber's notes, publishers' advertisements, and the "By …" title-page chapters. Real content stays:
notes, prefaces, dedications, dramatis personae, epigraphs, part titles, the issue notes we wrote for
magazine collections, and argument summaries titled "Contents".

    python scripts/clean_front_matter.py            # classify -> .seed_cache/reading_room/front_matter.csv
    python scripts/clean_front_matter.py --apply    # drop the "drop" rows, renumber, log

Dropped chapters are logged to docs/reading-room/reading-room-chapter-removals.csv. Reading positions saved by
chapter number shift for affected books (by the number of chapters removed before them).
"""
from __future__ import annotations

import csv
import datetime
import html as _html
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = ROOT / "db" / "books.db"
OUT = ROOT / ".seed_cache" / "reading_room" / "front_matter.csv"
LOG = ROOT / "docs" / "reading-room" / "reading-room-chapter-removals.csv"

_MAGAZINE = re.compile(r"_\d{4}-\d{2}$")
_PREFIX = re.compile(r"^.{1,80}? · ")


def _text(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _blocks(h: str) -> list[str]:
    return [b for b in (_text(x) for x in re.split(r"(?i)</?(?:p|div|li|h\d|tr|br)\b[^>]*>", h or "")) if b]


def _listlike(h: str) -> bool:
    """Mostly short lines: a list of titles, not prose."""
    bs = _blocks(h)
    if not bs:
        return True
    short = sum(1 for b in bs if len(b) < 90)
    return short >= 0.75 * len(bs)


def _digit_dense(t: str) -> bool:
    words = t.split()
    nums = sum(1 for w in words if re.match(r"^\(?[\divxlc]+[,.;)]?$", w, re.I) and re.search(r"\d", w))
    return bool(words) and nums / len(words) > 0.08


def _no_prose(h: str) -> bool:
    from webapp.typeset import _prose  # noqa: PLC0415
    return not any(_prose(b) for b in _blocks(h))


_STRONG = re.compile(
    r"\bC\s?O\s?N\s?T\s?E\s?N\s?T\s?S\b|\bContents\b|(?:Copyright|COPYRIGHT),?\s*(?:©|\(c\))?\s*(?:by\s+)?\d{4}|©\s*\d{4}|"
    r"All rights reserved|ALL RIGHTS RESERVED|\b(?:PUBLISHERS?|Publishers?)\b|\b(?:Author|AUTHOR) of\b|Library of Congress|"
    r"\b(?:LONDON|NEW YORK|BOSTON|PHILADELPHIA|EDINBURGH|CHICAGO)\b[:,.]?\s|\bPress\b|\bPRESS\b|\b& (?:Co|Sons|Company)\b|ISBN")


def _imprint(t: str) -> bool:
    """A strong title-page signal: a contents heading or real imprint text (not a stray 'PAGE')."""
    return bool(_STRONG.search(t))


def _poetry_slugs() -> set[str]:
    import json  # noqa: PLC0415
    con = sqlite3.connect(DB)
    return {s for s, g in con.execute("select slug, genres from books") if "Poetry" in json.loads(g or "[]")}


_POETRY: set[str] = set()


def classify(slug: str, n: int, sn: int, title: str, words: int, html: str) -> tuple[str, str] | None:
    """-> (decision, rule) for a front/back chapter, or None to leave it alone."""
    tl = _PREFIX.sub("", (title or "").strip()).lower().strip(" .:[]*")
    tl = re.sub(r"^(?:\[?\s*p(?:age|g)?\.?\s*[\divxlc]+\s*\]?\s+|[ivxlc]+\s+|\d+\s+)(?=\S)", "", tl).strip(" .:[]*")
    front, back = sn <= 4, sn > n - 3
    t = _text(html)
    if re.search(r"transcriber", tl):
        return "drop", "transcriber's note"
    if re.fullmatch(r"(?:the |detailed |expanded |chief |analytical |full |general )?(?:table of )?contents?(?: of (?:the )?(?:volume|book|vol\.?) ?\w*)?|contents of this volume|index of contents", tl):
        if _MAGAZINE.search(slug):
            return None                                   # our own issue note
        if _listlike(html) or _digit_dense(t):
            return "drop", "source contents list"
        return "review", "titled contents but reads as prose"
    if re.fullmatch(r"(?:list of |table of )?(?:illustrations?|plates|maps(?: and (?:plans|illustrations))?|figures|portraits|engravings|"
                    r"full-page illustrations|maps and plans|illustrations and maps|charts)(?: in (?:the )?(?:text|colou?r))?", tl):
        return ("drop", "list of illustrations") if words < 2500 else ("review", "illustration list, long")
    if re.match(r"(?:general |alphabetical |analytical )?index(?:es)?\b|index to\b|index of (?!first lines)", tl) and "first lines" not in tl:
        return ("drop", "page-number index") if _digit_dense(t) or words < 60 else ("review", "index without page numbers")
    if re.match(r"(?:errata|corrigenda)", tl):
        return "drop", "errata"
    if re.search(r"books by|other books|by the same author|also by|popular copyright|works by|catalogue of|publishers?'? announcement|"
                 r"^advertisements?$|new books|recent fiction|standard library|uniform with this", tl):
        if back or re.search(r"books by|by the same author|also by|other books", tl):
            return "drop", "publisher's advertisement"
        return None                                       # a front "Advertisement" is the author's preface
    if front and re.fullmatch(r"by|title|title page|title-page|frontispiece|half-title|half title|the", tl):
        return ("drop", "source title page") if words < 800 else ("review", "title page with more text")
    if (front and sn <= 2 and words < 1500 and slug not in _POETRY and _no_prose(html) and _imprint(t)
            and not re.search(r"(?i)character|persons|dramatis|cast\b|abbreviation|key to", tl + " " + t[:400])):
        # dedications on these pages are carried into the next chapter by _keepsakes()
        return "drop", "source title page and contents"
    if front and sn <= 2 and words < 150 and not re.search(r"(?i)dedicat|^to\b", t) and re.search(
            r"\b(?:London|New York|Boston|Philadelphia|Edinburgh|Chicago|Toronto|Publishers?|Printed (?:by|for|at|in)|"
            r"Copyright|All rights reserved|Author of|Illustrated by|Library of Congress)\b", t) and not re.search(
            r"(?i)preface|foreword|introduction|dedicat|note|prologue|dramatis|persons|characters|cast|part|book|section|period|epigraph|to\b", tl):
        return "drop", "source title page"
    return None


def survey() -> list[dict]:
    _POETRY.update(_poetry_slugs())                       # poetry is done last, on its own
    con = sqlite3.connect(DB)
    rows = []
    q = """select b.slug, b.chapter_count, ch.section_number, ch.title, ch.words, ch.html
           from books b join book_chapters ch on ch.book_id = b.id
           where ch.section_number <= 4 or ch.section_number > b.chapter_count - 3"""
    for slug, n, sn, title, words, html in con.execute(q):
        if n <= 1:
            continue
        r = classify(slug, n, sn, title, words, html)
        if r:
            rows.append({"slug": slug, "section": sn, "chapters": n, "title": title, "words": words,
                         "decision": r[0], "rule": r[1], "sample": _text(html)[:160]})
    return rows


_EPIGRAPH = re.compile(r"[“\"‘'].{12,}[”\"’']\s*[,.]?\s*[—–-]+\s*\S|^[“\"].{12,}[”\"]$")
_DEDICATION = re.compile(r"^(?:(?:affectionately|respectfully|gratefully|lovingly|reverently|(?:most|very) respectfully)\s+)?"
                         r"(?:dedicated|inscribed)\s+to\s+\S|^(?:to|for|in (?:loving |affectionate )?memory of)\s+\S", re.I)


def _keepsakes(h: str) -> str:
    """The dedication and epigraph blocks of a source title page, as house blocks."""
    out = []
    for m in re.finditer(r"(?is)<(p|blockquote|div)\b[^>]*>(.*?)</\1>", h or ""):
        t = _text(m.group(2))
        if not t or len(t) > 400 or re.search(r"(?i)contents|copyright|publisher|author of|london|new york", t):
            continue
        if re.search(r"[”\"’']\s*[,.]?\s*[—–-]+\s*[A-Z]", t) or (m.group(1).lower() == "blockquote" and len(t) > 12):
            out.append(f'<blockquote class="ex-epi">{m.group(2).strip()}</blockquote>')
        elif _DEDICATION.match(t):
            out.append(f'<p class="ex-ded">{m.group(2).strip()}</p>')
    return "".join(out)


def _insert_after_heading(h: str, block: str) -> str:
    m = re.search(r"(?is)</(?:h[1-4]|hgroup|header)>", h[:3000])
    return h[:m.end()] + block + h[m.end():] if m else block + h


def apply(rows: list[dict]) -> None:
    con = sqlite3.connect(DB)
    today = datetime.date.today().isoformat()
    by_book: dict[str, list[int]] = {}
    for r in rows:
        if r["decision"] == "drop":
            by_book.setdefault(r["slug"], []).append(int(r["section"]))
    log = []
    for slug, secs in by_book.items():
        bid, n = con.execute("select id, chapter_count from books where slug=?", (slug,)).fetchone()
        if len(secs) >= n:
            continue                                      # never empty a book
        for sn in secs:
            t, w, h = con.execute("select title, words, html from book_chapters where book_id=? and section_number=?", (bid, sn)).fetchone()
            rule = next(r["rule"] for r in rows if r["slug"] == slug and int(r["section"]) == sn)
            keep = _keepsakes(h) if rule.startswith("source title page") else ""
            if keep:                                      # a dedication or epigraph moves to the next chapter
                nxt = con.execute("select section_number, html from book_chapters where book_id=? and section_number>? "
                                  "order by section_number limit 1", (bid, sn)).fetchone()
                if nxt and nxt[0] not in secs:
                    con.execute("update book_chapters set html=? where book_id=? and section_number=?",
                                (_insert_after_heading(nxt[1], keep), bid, nxt[0]))
            log.append([today, slug, sn, t, w, rule + (" (dedication/epigraph kept)" if keep else "")])
            con.execute("delete from book_chapters where book_id=? and section_number=?", (bid, sn))
        kept = [s for (s,) in con.execute("select section_number from book_chapters where book_id=? order by section_number", (bid,))]
        for i, s in enumerate(kept, 1):                   # renumber in two steps to dodge the unique key
            con.execute("update book_chapters set section_number=? where book_id=? and section_number=?", (-i, bid, s))
        con.execute("update book_chapters set section_number=-section_number where book_id=?", (bid,))
        con.execute("""update books set chapter_count=(select count(*) from book_chapters where book_id=?),
                       word_count=(select coalesce(sum(words),0) from book_chapters where book_id=?) where id=?""", (bid, bid, bid))
    con.commit()
    new = not LOG.exists()
    with open(LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "slug", "section", "title", "words", "reason"])
        w.writerows(log)
    print(f"dropped {len(log)} chapters from {len(by_book)} books")


def main() -> None:
    if "--apply" in sys.argv:
        rows = list(csv.DictReader(open(OUT, encoding="utf-8")))
        apply(rows)
        return
    rows = survey()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    for (d, r), k in Counter((x["decision"], x["rule"]) for x in rows).most_common():
        print(f"{k:6}  {d:7} {r}")


if __name__ == "__main__":
    main()
