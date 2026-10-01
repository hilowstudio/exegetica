"""Horror titles not on Project Gutenberg or Standard Ebooks, sourced from other clean
public-domain repositories:
  - Project Gutenberg Australia (single-file HTML)  -> The Maker of Moons, The Beast with Five Fingers
  - Wikisource, via the ws-export EPUB tool         -> The Italian (Radcliffe), complete in 3 volumes

Same book/chapter shape and Horror & Gothic shelving as seed_horror.py. HTML items reuse the
heading-split + _clean_chapter path; the EPUB item walks the OPF spine (one XHTML per chapter,
already correctly ordered — no heuristic segmentation). No cover art at these sources, so
cover_url is left null (the reader shows the cloth fallback).

    .venv\\Scripts\\python.exe scripts\\seed_horror_alt.py --dry-run
    .venv\\Scripts\\python.exe scripts\\seed_horror_alt.py
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.standardebooks import _clean_chapter  # noqa: E402

UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (Reading Room corpus; hello@hilowstudio.dev)"}
SECTION = ["Horror & Gothic"]

ITEMS = [
    {
        "slug": "robert-w-chambers_the-maker-of-moons-pgau0605441",
        "kind": "html", "split": ("heading", "h2"),
        "url": "https://gutenberg.net.au/ebooks06/0605441h.html",
        "title": "The Maker of Moons", "raw_title": "The Maker of Moons and Other Stories",
        "author": "Robert W. (Robert William) Chambers",
        "author_sort": "Chambers, Robert W. (Robert William)",
        "source": "gutenberg-au", "license": "PD-US",
        "subjects": ["Horror tales", "Short stories"],
        "skip_titles": ("robert w. chambers",),   # the author-name front-matter section
    },
    {
        "slug": "william-fryer-harvey_the-beast-with-five-fingers-pgau0609231",
        "kind": "html", "split": ("heading", "h2"),
        "url": "https://gutenberg.net.au/ebooks06/0609231h.html",
        "title": "The Beast with Five Fingers", "raw_title": "The Beast with Five Fingers",
        "author": "William Fryer Harvey", "author_sort": "Harvey, William Fryer",
        "source": "gutenberg-au", "license": "PD-US",
        "subjects": ["Horror tales"],
    },
    {
        "slug": "ann-radcliffe_the-italian-ws",
        "kind": "epub",
        "url": "https://ws-export.wmcloud.org/?lang=en&format=epub-3&page=The_Italian_(Radcliffe)",
        "title": "The Italian", "raw_title": "The Italian; or, the Confessional of the Black Penitents",
        "author": "Ann Radcliffe", "author_sort": "Radcliffe, Ann",
        "source": "wikisource", "license": "PD-US",
        "subjects": ["Gothic fiction", "Horror tales"],
        # spine hrefs whose page is front/back matter, not a readable chapter
        "epub_skip": ("nav", "title", "about", "cover"),
    },
]


def _forced_nodes(body, kind, sel):
    html = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
    if kind == "heading":
        pat = rf"(<{sel}\b[^>]*>.*?</{sel}>)"
    else:
        pat = rf'(<p\b[^>]*class="[^"]*\b{re.escape(sel)}\b[^"]*"[^>]*>.*?</p>)'
    toks = re.split(pat, html, flags=re.I | re.S)
    nodes, i = [], 1
    while i < len(toks):
        nodes.append(BeautifulSoup(toks[i] + (toks[i + 1] if i + 1 < len(toks) else ""), "html.parser"))
        i += 2
    return nodes


def _title_from_href(href: str) -> str:
    """Derive a navigable chapter title from a ws-export filename, e.g.
    'c3_The_Italian__Radcliffe__Volume_1_Chapter_1.xhtml' -> 'Volume 1 · Chapter 1'."""
    stem = re.sub(r"\.[^.]+$", "", href.rsplit("/", 1)[-1])
    stem = re.sub(r"^c\d+_", "", stem)
    m = re.search(r"(Volume.*)$", stem)
    core = (m.group(1) if m else stem).replace("__", " ").replace("_", " ")
    core = re.sub(r"\s+", " ", core).strip()
    return re.sub(r"(Volume \d+) (Chapter|Preface|Introduction|Dedication)", r"\1 · \2", core)


def _chapters_from_html(client, item) -> list[dict]:
    r = client.get(item["url"])
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    body = soup.body or soup
    skip_titles = {t.lower() for t in item.get("skip_titles", ())}
    chapters = []
    for node in _forced_nodes(body, *item["split"]):
        title, chtml, words = _clean_chapter(node)
        if words < 30 or gb._SKIP_TITLE.match(title or "") or (title or "").strip().lower() in skip_titles:
            continue
        chapters.append({"section_number": len(chapters) + 1, "title": title, "html": chtml, "words": words})
    return chapters


def _chapters_from_epub(client, item) -> list[dict]:
    r = client.get(item["url"])
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//{*}rootfile").get("full-path")
    base = opf_path.rsplit("/", 1)[0] if "/" in opf_path else ""
    opf = ET.fromstring(z.read(opf_path))
    manifest = {it.get("id"): it.get("href") for it in opf.find("{*}manifest")}
    order = [manifest[ref.get("idref")] for ref in opf.find("{*}spine") if manifest.get(ref.get("idref"))]
    skip = item.get("epub_skip", ())
    chapters = []
    for href in order:
        stem = href.rsplit("/", 1)[-1].lower()
        if any(s in stem for s in skip):
            continue
        full = f"{base}/{href}" if base else href
        try:
            raw = z.read(full)
        except KeyError:
            continue
        node = BeautifulSoup(raw, "html.parser")
        bodyn = node.body or node
        title, chtml, words = _clean_chapter(bodyn)
        if words < 30 or gb._SKIP_TITLE.match(title or ""):
            continue
        if not (title or "").strip():          # ws-export chapters carry no <h*>; title from filename
            title = _title_from_href(href)
        chapters.append({"section_number": len(chapters) + 1, "title": title, "html": chtml, "words": words})
    return chapters


def _store(con, item, chapters):
    wc = sum(c["words"] for c in chapters)
    cur = con.cursor()
    cur.execute("select id from books where slug=?", (item["slug"],))
    row = cur.fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,section,genres_backup,title_backup,cover_url,
                             chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item["slug"], item["title"], item["author"], item["author_sort"], item["source"],
         item["license"], 1, "en", json.dumps(item["subjects"]), json.dumps(SECTION),
         json.dumps(SECTION), json.dumps(SECTION), item["raw_title"], None,
         len(chapters), wc))
    bid = cur.lastrowid
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in chapters])
    con.commit()
    return wc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    ok = fail = 0
    with httpx.Client(timeout=120, headers=UA, follow_redirects=True) as client:
        for item in ITEMS:
            try:
                chapters = _chapters_from_html(client, item) if item["kind"] == "html" \
                    else _chapters_from_epub(client, item)
            except Exception as e:  # noqa: BLE001
                print(f"  SKIP {item['title']}  ({e!r})"); fail += 1; continue
            if not chapters:
                print(f"  SKIP {item['title']}  (no chapters)"); fail += 1; continue
            wc = sum(c["words"] for c in chapters)
            print(f"  {item['title'][:36]:36} {wc:>7,}w {len(chapters):>3}ch  {item['source']:12} {item['author'][:22]}")
            if not args.dry_run:
                _store(con, item, chapters)
            ok += 1
    print(f"\n{'(dry-run) ' if args.dry_run else ''}{ok} ingested, {fail} skipped")
    con.close()


if __name__ == "__main__":
    main()
