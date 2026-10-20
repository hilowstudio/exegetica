"""Restore a Standard Ebooks title's endnotes into its baked edition (direct, logged edits to one book).

Our Standard Ebooks import dropped each book's endnotes.xhtml and stripped the note links, leaving the bare
note numbers glued to the text ("Unborrow'd from the eye”3"). For one baked book, this:

  * reads the endnotes and every note reference (with the words just before it) from the book's Standard
    Ebooks source (cloned by review_title.py ref);
  * finds each reference's bare numeral in our edition by those preceding words, turns it into a note marker,
    and gathers the note at the end of that chapter, the way every Exegetica footnote is set.

Edits edition_chapters only; logs each restored note to docs/edition-corrections.csv. A numeral that cannot
be located unambiguously is reported, not guessed.

    python scripts/restore_se_endnotes.py <slug> [--dry-run]
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
DB = ROOT / "db" / "books.db"
LOG = ROOT / "docs" / "edition-corrections.csv"
SHY = "­"


def plain(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))).strip()


def se_notes(repo: Path) -> tuple[dict, list]:
    """-> ({n: note inner html}, [(n, words-before) in reading order])."""
    en = (repo / "src" / "epub" / "text" / "endnotes.xhtml").read_text(encoding="utf-8")
    notes = {}
    for m in re.finditer(r'(?s)<li\b[^>]*id="note-(\d+)"[^>]*>(.*?)</li>', en):
        inner = re.sub(r'(?s)\s*<a\b[^>]*epub:type="backlink"[^>]*>.*?</a>', "", m.group(2))
        inner = re.sub(r'\s(?:epub:type|xml:lang|lang|id)="[^"]*"', "", inner)
        inner = re.sub(r"(?s)^\s*<p>(.*)</p>\s*$", r"\1", inner.strip()) if inner.count("<p") == 1 else inner
        notes[m.group(1)] = re.sub(r">\s+<", "><", inner.strip())
    opf = (repo / "src" / "epub" / "content.opf").read_text(encoding="utf-8")
    spine = re.findall(r'<itemref\b[^>]*\bidref="([^"]+)"', opf)
    refs = []
    for item in spine:
        p = repo / "src" / "epub" / "text" / item
        if not p.exists() or item == "endnotes.xhtml":
            continue
        x = p.read_text(encoding="utf-8")
        for m in re.finditer(r'<a\b[^>]*href="endnotes\.xhtml#note-(\d+)"[^>]*>\d+</a>', x):
            before = plain(x[max(0, m.start() - 600):m.start()])
            refs.append((m.group(1), before[-80:]))
    return notes, refs


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    slug, dry = sys.argv[1], "--dry-run" in sys.argv
    repo = ROOT / ".seed_cache" / "refs" / "se" / slug
    if not (repo / "src" / "epub" / "text" / "endnotes.xhtml").exists():
        raise SystemExit(f"{slug}: no Standard Ebooks endnotes (run review_title.py ref first)")
    notes, refs = se_notes(repo)
    con = sqlite3.connect(DB)
    bid, = con.execute("select id from books where slug=?", (slug,)).fetchone()
    chapters = {sn: h for sn, h in con.execute("select section_number, html from edition_chapters where book_id=?", (bid,))}
    if not chapters:
        raise SystemExit(f"{slug}: not baked")
    placed: dict[int, list] = {}
    log, missing = [], []
    for n, before in refs:
        words = re.findall(r"[^\W\d_]+", before)[-3:]
        if not words or n not in notes:
            missing.append(n)
            continue
        soft = lambda w: (SHY + "?").join(re.escape(c) for c in w)  # noqa: E731 — tolerate soft hyphens
        sep = r"(?:[^\w<]|<[^>]+>)+?"                          # spaces, punctuation and tags between words
        pat = re.compile(r"(?s)" + sep.join(soft(w) for w in words) + r"((?:[^\w<]|<[^>]+>){0,12}?)" + re.escape(n) + r"(?!\d)")
        hits = [(sn, m) for sn, h in chapters.items() for m in pat.finditer(h)]
        if not hits:                                          # the numeral itself was lost: place after the words
            words5 = re.findall(r"[^\W\d_]+", before)[-5:]
            bare = re.compile(r"(?s)" + sep.join(soft(w) for w in words5) + r"(?:[^\w<\s]|</[a-z]+>)*")
            hits = [(sn, m) for sn, h in chapters.items() for m in bare.finditer(h)]
            if len(hits) == 1:
                sn, m = hits[0]
                placed.setdefault(sn, []).append((m, n, 0))
                continue
        if len(hits) != 1:
            missing.append(f"{n} ({len(hits)} matches)")
            continue
        sn, m = hits[0]
        placed.setdefault(sn, []).append((m, n, len(n)))
    for sn, items in placed.items():
        h = chapters[sn]
        existing = len(re.findall(r'class="ex-note"', h))
        for k, (m, n, glued) in enumerate(sorted(items, key=lambda x: x[0].start(), reverse=True)):
            num = existing + len(items) - k
            ref = f'<a class="ex-ref" href="#fn{num}" data-fn="{num}" role="doc-noteref">{num}</a>'
            h = h[:m.end() - glued] + ref + h[m.end():]          # replace the bare numeral, or insert where it was lost
        block = "".join(f'<p class="ex-note" id="fn{existing + i + 1}"><span class="ex-note-n">{existing + i + 1}</span> {notes[n]}</p>'
                        for i, (m, n, _g) in enumerate(sorted(items, key=lambda x: x[0].start())))
        if '<section class="ex-notes"' in h:
            h = h.replace("</section>", block + "</section>", 1) if h.count('<section class="ex-notes"') == 1 else h + \
                f'<section class="ex-notes" role="doc-endnotes">{block}</section>'
        else:
            h = h + f'<section class="ex-notes" role="doc-endnotes">{block}</section>'
        chapters[sn] = h
        for m, n, _g in items:
            log.append([datetime.date.today().isoformat(), slug, sn, "note (edition)",
                        f"endnote {n} restored from the Standard Ebooks source", f"…{m.group(0)[-40:]}", notes[n][:160]])
        if not dry:
            con.execute("update edition_chapters set html=? where book_id=? and section_number=?", (h, bid, sn))
    if not dry:
        con.commit()
        with open(LOG, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(log)
    print(f"{slug}: {len(log)} of {len(refs)} notes restored{' (dry run)' if dry else ''}"
          + (f"; not located: {', '.join(map(str, missing))}" if missing else ""))


if __name__ == "__main__":
    main()
