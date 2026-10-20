"""One-off: source a hand-picked list of public-domain horror/gothic works from Project
Gutenberg and add them to the Reading Room on the "Horror & Gothic" shelf.

Same clean-chapter path as seed_gutenberg.py (gb.fetch_book), but driven by an explicit
manifest (gid + the concise title we want to display) rather than the bulk manifest CSV, and
writing the FULL modern column set (section/genres/backups/cover_url) so each book lands
shelved, titled, and cover-ready.

Per-book author, subjects, and the cover-image URL come from the Gutendex record for that id,
so metadata is accurate. cover_url is set to the external PG cover jpeg; run
    build_covers_db.py         # fetch+webp the new covers
    build_covers_db.py --finalize   # repoint cover_url -> /api/cover/{slug}
afterward to self-host them, exactly like the rest of the corpus.

    .venv\\Scripts\\python.exe scripts\\seed_horror.py --dry-run   # fetch + report, no write
    .venv\\Scripts\\python.exe scripts\\seed_horror.py             # ingest
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
import sqlite3  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from bs4 import BeautifulSoup  # noqa: E402
import re  # noqa: E402

from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402
from webapp.sources.standardebooks import _clean_chapter  # noqa: E402

SECTION = ["Horror & Gothic"]

# Books whose PG HTML defeats the generic div.chapter/heading heuristic in gb._raw_chapters
# (empty <div class="chapter"> anchors, or chapter titles marked by a styled <p> instead of an
# <hN>). Force the correct split here: ("heading", "h2") splits on that heading tag; ("pclass",
# "ph2") splits on <p class="…ph2…">. Verified per book by inspecting the source HTML.
_FORCE_SPLIT: dict[int, tuple[str, str]] = {
    14833: ("heading", "h2"),   # Varney the Vampyre — 227 empty div.chapter anchors; prose in siblings
    77472: ("heading", "h2"),   # Pan's Garden — story titles are <h2>, sub-parts <h3>
    71268: ("pclass", "ph2"),   # Skull-Face — no headings; chapter titles are <p class="ph2">
}


def _forced_nodes(body, kind: str, sel: str) -> list:
    """Split the serialized body at each delimiter element (string split → robust to nesting),
    re-parsing each fragment. Mirrors gb._raw_chapters' heading branch but with an explicit
    delimiter, bypassing the div.chapter detection."""
    html = body.decode_contents() if hasattr(body, "decode_contents") else str(body)
    if kind == "heading":
        pat = rf"(<{sel}\b[^>]*>.*?</{sel}>)"
    else:  # pclass — a <p> carrying the given class token
        pat = rf'(<p\b[^>]*class="[^"]*\b{re.escape(sel)}\b[^"]*"[^>]*>.*?</p>)'
    toks = re.split(pat, html, flags=re.I | re.S)
    nodes, i = [], 1  # toks[0] is the preamble before the first delimiter — dropped
    while i < len(toks):
        frag = toks[i] + (toks[i + 1] if i + 1 < len(toks) else "")
        nodes.append(BeautifulSoup(frag, "html.parser"))
        i += 2
    return nodes


async def _fetch_forced(client, gid, meta: dict, split: tuple[str, str]) -> dict | None:
    """Same as gb.fetch_book but with a forced chapter delimiter for a problem book."""
    r = None
    for tmpl in gb._HTML_URLS:
        r = await gb._get_with_retry(client, tmpl.format(gid=gid))
        if r is not None:
            break
    if r is None:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    for el in soup.select('[class*="pg-boilerplate"], [class*="pgheader"], #pg-header, #pg-footer'):
        el.decompose()
    body = soup.body or soup
    chapters = []
    for node in _forced_nodes(body, *split):
        title, chtml, words = _clean_chapter(node)
        if words < 30 or gb._SKIP_TITLE.match(title or ""):
            continue
        chapters.append({"section_number": len(chapters) + 1, "title": title,
                         "html": chtml, "words": words})
    if not chapters:
        return None
    display, sort = gb._display_name(meta.get("author") or "")
    title = meta.get("title") or ""
    subjects = [s.strip() for s in (meta.get("subjects") or "").split("|") if s.strip()]
    return {
        "slug": (f"{gb._slugify(display)}_{gb._slugify(title)}"[:78] or "book") + f"-pg{gid}",
        "title": title, "author": display, "author_sort": sort, "language": "en",
        "subjects": subjects, "genres": SECTION, "chapters": chapters,
        "word_count": sum(c["words"] for c in chapters),
    }

# gid -> concise display title we want. Author/subjects/cover come from Gutendex.
# (Populated after ID discovery; each id is verified to have a Gutenberg HTML edition.)
MANIFEST: dict[int, str] = {
    35617: "The Terror",                        # Arthur Machen (raw: "The Terror: A Mystery")
    9956:  "Hauntings",                         # Vernon Lee (raw: "Hauntings: Fantastic Stories")
    14833: "Varney the Vampyre",                # Prest / Rymer
    5324:  "The Book of Were-Wolves",           # Sabine Baring-Gould
    17769: "The House by the Churchyard",       # J. Sheridan Le Fanu (raw: "…Church-Yard")
    10832: "Carnacki, the Ghost-Finder",        # William Hope Hodgson
    9629:  "More Ghost Stories of an Antiquary", # M. R. James (the second collection)
    36281: "The Slayer of Souls",               # Robert W. Chambers
    46581: "The Mystery of Choice",             # Robert W. Chambers
    9964:  "The Centaur",                       # Algernon Blackwood
    11988: "The Human Chord",                   # Algernon Blackwood
    43816: "Incredible Adventures",             # Algernon Blackwood
    77472: "Pan's Garden",                      # Algernon Blackwood (raw: "…: a volume of nature stories")
    14471: "The Empty House and Other Ghost Stories",  # Algernon Blackwood
    71268: "Skull-Face",                        # Robert E. Howard
    77782: "Black Magic",                       # Marjorie Bowen (raw: "…: A tale of the rise and fall of Antichrist")
    64701: "The Romance of the Forest",         # Ann Radcliffe
}


async def _gutendex(client: httpx.AsyncClient, gid: int) -> dict | None:
    r = await gb._get_with_retry(client, f"https://gutendex.com/books/{gid}")
    return r.json() if r is not None else None


def _cover_url(formats: dict) -> str | None:
    for k, v in (formats or {}).items():
        if k.startswith("image/") and v and not v.lower().endswith(".zip"):
            return v
    return None


def _open_db(path: pathlib.Path) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=120)
    return con


def _store(con: sqlite3.Connection, book: dict, cover_url: str | None, raw_title: str) -> None:
    cur = con.cursor()
    cur.execute("select id from books where slug=?", (book["slug"],))
    row = cur.fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cur.execute(
        """insert into books(slug,title,author,author_sort,source,license,us_clear,language,
                             subjects,genres,section,genres_backup,title_backup,cover_url,
                             chapter_count,word_count)
           values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (book["slug"], book["title"], book["author"], book["author_sort"], gb.SOURCE, gb.LICENSE,
         1, book["language"], json.dumps(book["subjects"]), json.dumps(SECTION), json.dumps(SECTION),
         json.dumps(SECTION), raw_title, cover_url,
         len(book["chapters"]), book["word_count"]))
    # write the chapters too (this was missing, so the 2026-09-21 batch went in with no text;
    # restored by restore_empty_books.py)
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(cur.lastrowid, c["section_number"], c["title"], c["html"], c["words"]) for c in book["chapters"]])
    con.commit()


async def _run(args) -> None:
    con = _open_db(_ROOT / args.db)
    have = {r[0] for r in con.execute("select slug from books")}
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    ok = fail = 0
    only = {int(x) for x in args.only.split(",")} if args.only else None
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA},
                                 follow_redirects=True) as client:
        for gid, title in MANIFEST.items():
            if only and gid not in only:
                continue
            rec = await _gutendex(client, gid)
            if not rec:
                print(f"  SKIP pg{gid}  (no gutendex record)  {title}"); fail += 1; continue
            authors = rec.get("authors") or []
            pg_author = authors[0]["name"] if authors else ""
            subjects = rec.get("subjects") or rec.get("bookshelves") or []
            cover = _cover_url(rec.get("formats") or {})
            meta = {"author": pg_author, "title": title, "genre": None,
                    "subjects": "|".join(subjects)}
            try:
                if gid in _FORCE_SPLIT:
                    book = await asyncio.wait_for(
                        _fetch_forced(client, gid, meta, _FORCE_SPLIT[gid]), timeout=args.timeout)
                else:
                    book = await asyncio.wait_for(gb.fetch_book(client, gid, meta), timeout=args.timeout)
            except Exception as e:  # noqa: BLE001
                book = None
                err = repr(e)
            if not book:
                print(f"  SKIP pg{gid}  (no HTML/chapters)  {title}"); fail += 1; continue
            book["genres"] = SECTION
            dup = " [dup slug!]" if (book["slug"] in have and not args.dry_run) else ""
            print(f"  pg{gid:<6} {book['title'][:40]:40} {book['word_count']:>7,}w "
                  f"{len(book['chapters']):>3}ch  cover={'Y' if cover else 'n'}  {book['author'][:24]}{dup}")
            if not args.dry_run:
                _store(con, book, cover, rec.get("title") or title)
            ok += 1
    print(f"\n{'(dry-run) ' if args.dry_run else ''}{ok} ingested, {fail} skipped")
    con.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--only", help="comma-separated gids to (re-)ingest, ignoring the rest")
    p.add_argument("--dry-run", action="store_true")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
