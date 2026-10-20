"""Restore the dedications and epigraphs our Standard Ebooks import skipped.

Standard Ebooks keeps a book's dedication and epigraph in their own files (dedication.xhtml,
epigraph.xhtml, sometimes several), placed in the reading order. Our original import dropped them.
This fetches each book's content.opf and those files from github.com/standardebooks/<slug> and:

  * front pieces (before the first chapter) -> books.front_html, which the reader sets as a page of its
    own between the colophon and the contents;
  * a piece placed before a later part/chapter -> prepended to that chapter, as an epigraph.

Logged to docs/edition-corrections.csv. Idempotent: front_html is rebuilt; chapter inserts are skipped
when already present.

    python scripts/restore_se_frontmatter.py <slug> […]      # or --all for every Standard Ebooks book
"""
from __future__ import annotations

import csv
import datetime
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "db" / "books.db"
LOG = ROOT / "docs" / "edition-corrections.csv"
RAW = "https://raw.githubusercontent.com/standardebooks/{slug}/{branch}/src/epub/{path}"
UA = {"User-Agent": "ExegeticaLibrary/1.0 (public-domain edition review)"}
FRONT = re.compile(r"(?:titlepage|halftitlepage|imprint|toc|introduction|preface|foreword|dedication|epigraph|"
                   r"note|notes|author-s-note|translator-s-note|editor-s-note|prefatory-note|frontispiece|letter-to|"
                   r"advertisement|argument|contents|loi|preamble)[\w-]*\.xhtml$")


def fetch(slug: str, path: str) -> str | None:
    for branch in ("master", "main"):
        try:
            req = urllib.request.Request(RAW.format(slug=slug, branch=branch, path=path), headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    return None


def section_inner(xhtml: str) -> str:
    body = xhtml.split("<body", 1)[-1].split(">", 1)[-1].rsplit("</body>", 1)[0]
    m = re.search(r"(?s)<section\b[^>]*>(.*)</section>", body)
    inner = m.group(1) if m else body
    inner = re.sub(r'\s(?:epub:type|xml:lang|lang|id)="[^"]*"', "", inner)   # our markup carries no EPUB semantics
    return re.sub(r">\s+<", "><", inner).strip()


def words_of(xhtml: str) -> list[str]:
    body = re.sub(r"(?is)<(header|hgroup|h[1-6])\b.*?</\1>", " ", xhtml.split("<body", 1)[-1])
    t = re.sub(r"(?s)<[^>]+>", " ", body)
    return re.findall(r"[a-z]+", t.lower())


def restore(con, slug: str, log: list) -> str:
    opf = fetch(slug, "content.opf")
    if not opf:
        return "no source"
    hrefs = {m.group(1): m.group(2) for m in re.finditer(r'<item\b[^>]*\bid="([^"]+)"[^>]*\bhref="([^"]+)"', opf)}
    hrefs.update({m.group(2): m.group(1) for m in re.finditer(r'<item\b[^>]*\bhref="([^"]+)"[^>]*\bid="([^"]+)"', opf)})
    spine = [hrefs.get(i, i) for i in re.findall(r'<itemref\b[^>]*\bidref="([^"]+)"', opf)]
    pieces = [i for i, h in enumerate(spine) if re.search(r"(?:^|/)(?:dedication|epigraph)[\w-]*\.xhtml$", h)]
    if not pieces:
        return "none"
    row = con.execute("select id from books where slug=?", (slug,)).fetchone()
    bid = row[0]
    front, inserted = [], 0
    chapters = con.execute("select section_number, html from book_chapters where book_id=? order by section_number", (bid,)).fetchall()
    for i in pieces:
        x = fetch(slug, "text/" + spine[i].split("/")[-1])
        if not x:
            continue
        kind = "dedication" if "dedication" in spine[i] else "epigraph"
        block = f'<div class="ex-{kind}">{section_inner(x)}</div>'
        if all(FRONT.search(h.split("/")[-1]) for h in spine[:i]):
            front.append(block)
            continue
        nxt = next((h for h in spine[i + 1:] if not re.search(r"(?:dedication|epigraph)", h)), None)
        target = None
        if nxt:
            nx = fetch(slug, "text/" + nxt.split("/")[-1]) or ""
            probe = " ".join(words_of(nx)[:10])
            for sn, h in chapters:
                if probe and probe in " ".join(re.findall(r"[a-z]+", re.sub(r"(?s)<[^>]+>", " ", h).lower())[:400]):
                    target = sn
                    break
        if target is None:
            front.append(block)
            continue
        h = next(h for sn, h in chapters if sn == target)
        if block in h:
            continue
        m = re.search(r"(?is)</(?:h[1-4]|hgroup|header)>", h[:3000])
        new = h[:m.end()] + block + h[m.end():] if m else block + h
        con.execute("update book_chapters set html=? where book_id=? and section_number=?", (new, bid, target))
        inserted += 1
        log.append([datetime.date.today().isoformat(), slug, target, "insert", f"{kind} restored from Standard Ebooks ({spine[i]})", "after heading", block[:200]])
    html = "".join(front)
    old = con.execute("select front_html from books where id=?", (bid,)).fetchone()[0]
    if html and html != old:
        con.execute("update books set front_html=? where id=?", (html, bid))
        log.append([datetime.date.today().isoformat(), slug, 0, "front", "dedication/epigraph restored from Standard Ebooks", "front_html", html[:200]])
    con.commit()
    return f"{len(front)} front, {inserted} in chapters"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(DB)
    if "front_html" not in [r[1] for r in con.execute("pragma table_info(books)")]:
        con.execute("alter table books add column front_html text")
        con.commit()
    slugs = ([s for (s,) in con.execute("select slug from books where source='standardebooks' order by slug")]
             if "--all" in sys.argv else [a.strip() for a in sys.argv[1:] if a.strip() and not a.startswith("--")])
    log = []
    for k, slug in enumerate(slugs, 1):
        try:
            res = restore(con, slug, log)
        except Exception as e:  # noqa: BLE001
            res = f"FAILED {type(e).__name__}: {e}"
        if res not in ("none",) or len(slugs) < 50:
            print(f"{k}/{len(slugs)} {slug}: {res}", flush=True)
        time.sleep(0.15)
    new = not LOG.exists()
    with open(LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "slug", "chapter", "op", "why", "anchor", "change"])
        w.writerows(log)
    print(f"logged {len(log)} restorations")


if __name__ == "__main__":
    main()
