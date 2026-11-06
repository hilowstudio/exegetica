"""Restore a Standard Ebooks title's part / book / volume divisions into its baked edition (direct, logged edits).

Standard Ebooks sets each division title on a page of its own (part-1.xhtml: "Book I · The House with the Open
Window"). Our import skipped those files, which carry no body text, so the divisions vanished. For one baked
book this finds each division file in the reading order and the chapter that follows it, and puts a part-title
page at the start of that chapter (chapter numbering and reading positions are unchanged).

    python scripts/restore_se_parts.py <slug> [--dry-run]
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
from webapp.typeset import split_heading  # noqa: E402

DB = ROOT / "db" / "books.db"
LOG = ROOT / "docs" / "reading-room" / "edition-corrections.csv"


def plain(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))).strip()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    slug, dry = sys.argv[1], "--dry-run" in sys.argv
    repo = ROOT / ".seed_cache" / "refs" / "se" / slug
    opf = (repo / "src" / "epub" / "content.opf").read_text(encoding="utf-8")
    spine = re.findall(r'<itemref\b[^>]*\bidref="([^"]+)"', opf)
    con = sqlite3.connect(DB)
    bid, = con.execute("select id from books where slug=?", (slug,)).fetchone()
    chapters = dict(con.execute("select section_number, html from edition_chapters where book_id=?", (bid,)).fetchall())
    log, done = [], 0
    for i, item in enumerate(spine):
        if not re.match(r"(?:part|book|volume|division)-\d+\.xhtml$", item):
            continue
        x = (repo / "src" / "epub" / "text" / item).read_text(encoding="utf-8")
        hd = re.search(r"(?is)<(?:header|hgroup)\b[^>]*>(.*?)</(?:header|hgroup)>|<(h[1-6])\b[^>]*>(.*?)</\2>", x.split("<body", 1)[-1])
        if not hd:
            continue
        inner = hd.group(1) if hd.group(1) is not None else hd.group(3)
        hx = re.search(r"(?is)<(h[1-6])\b[^>]*>(.*?)</\1>", inner)
        heading = plain(hx.group(2)) if hx else plain(inner)     # 'Book I' (its spans read together)
        subs = [plain(p) for p in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", inner)]
        lab, tit = split_heading(heading)                         # house style: 'Book One', not 'Book I'
        label, title = (lab, tit or (subs[0] if subs else "")) if lab else (heading, subs[0] if subs else "")
        nxt = next((s for s in spine[i + 1:] if (repo / "src" / "epub" / "text" / s).exists()
                    and not re.match(r"(?:part|book|volume|division)-\d+\.xhtml$", s)), None)
        if not nxt:
            continue
        body = (repo / "src" / "epub" / "text" / nxt).read_text(encoding="utf-8").split("<body", 1)[-1].split(">", 1)[-1]
        body = re.sub(r"(?is)<(header|hgroup|h[1-6])\b.*?</\1>", " ", body)
        probe = " ".join(re.findall(r"[a-z]+", plain(body).lower())[:10])
        target = next((sn for sn, h in sorted(chapters.items())
                       if probe and probe in " ".join(re.findall(r"[a-z]+", plain(h.replace("­", "")).lower())[:300])), None)
        if target is None:
            print(f"  {item}: following chapter not found")
            continue
        block = (f'<div class="ex-parthead"><p class="ex-pl">{_html.escape(label)}</p>'
                 + (f'<p class="ex-pt">{_html.escape(title)}</p>' if title else "") + '<i class="ex-orn" aria-hidden="true"></i></div>')
        if block in chapters[target]:
            continue
        chapters[target] = block + chapters[target]
        done += 1
        log.append([datetime.date.today().isoformat(), slug, target, "part (edition)",
                    f"division title restored from Standard Ebooks ({item})", "chapter start", f"{label} {title}".strip()])
        if not dry:
            con.execute("update edition_chapters set html=? where book_id=? and section_number=?", (chapters[target], bid, target))
        print(f"  ch {target}: {label} {title}")
    if not dry:
        con.commit()
        with open(LOG, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(log)
    print(f"{slug}: {done} division(s) restored{' (dry run)' if dry else ''}")


if __name__ == "__main__":
    main()
