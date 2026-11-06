#!/usr/bin/env python3
"""
Seed the Reading Room with Weird Tales and Fantastic Adventures as issue collections.

One book per magazine issue ("Weird Tales, October 1936"), built from
docs/reading-room/pulp-eligible-stories.csv (scripts/build_pulp_eligibility.py). Each collection holds the
issue's stories that are public domain now and have clean text, in page order:

  - Text comes from our own library when the story is already a standalone book there (already
    formatted; the standalone stays), otherwise from Project Gutenberg.
  - A serialized novel goes, complete, into every issue that carried one of its installments,
    with a note saying which part that issue ran. A serial is included only when every
    installment's issue is public domain.
  - The first chapter lists the issue's whole fiction contents and marks each item: in this
    collection, public domain but not yet transcribed, public domain from January 1, 2027, or
    still under copyright. Issues with one story today fill in as more are transcribed: re-run.
  - The cover is the issue's own cover (Galactic Central); run build_covers_db.py afterwards.

    .venv\\Scripts\\python.exe scripts\\seed_pulp_issues.py --dry-run   # plan only, no downloads
    .venv\\Scripts\\python.exe scripts\\seed_pulp_issues.py             # build into db/books.db
    .venv\\Scripts\\python.exe scripts\\build_covers_db.py && .venv\\Scripts\\python.exe scripts\\build_covers_db.py --finalize
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import html
import json
import re
import sqlite3
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402

from build_magazine_covers import _gc_series  # noqa: E402
from build_pulp_eligibility import MAGS, issue_key, norm, surname  # noqa: E402
from format_gutenberg import _norm_ws, _strip_pg  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402

CSV_PATH = ROOT / "docs" / "reading-room" / "pulp-eligible-stories.csv"
DB = ROOT / "db" / "books.db"
TEXT_CACHE = ROOT / ".seed_cache" / "pulp" / "texts"
# Magazines (slug stem, shelf, cover checklist) come from the shared config in build_pulp_eligibility.
STEMS = tuple(cfg["stem"] + "_" for cfg in MAGS.values())
SEASON_CODE = {1: "win", 4: "spr", 7: "sum", 10: "fal"}
# FictionMags length bands (words), with slack for front matter; a Gutenberg text far past its
# band is probably a whole collection that happens to share the story's title.
MAX_WORDS = {"short story": 7500, "vignette": 3000, "poem": 2000, "novelette": 17500, "novella": 40000}
SERIAL = re.compile(r"\[Part (\d+) of (\d+)")
PAGE_MARK = re.compile(r"<p>\s*(?:<span[^>]*>)?\s*p\.[\s\u00a0]?\d+\s*(?:</span>)?\s*</p>|<span[^>]*>\s*p\.[\s\u00a0]?\d+\s*</span>", re.I)
# Gutenberg's transcriber apparatus (not the magazine's text): note blocks, "Transcriber's Note"
# headings, the copyright-research boilerplate, and "errors have been corrected" lists.
TN_DIV = re.compile(r'<div\b[^>]*class="[^"]*(?:transnote|tnote|trans-note|transcriber)[^"]*"[^>]*>.*?</div>', re.S | re.I)
TN_BLOCK = re.compile(r"<(p|h[1-6]|li)\b[^>]*>(?:(?!</\1>).)*?(?:Transcriber.{0,3}s?\s+Notes?|Extensive research did not "
                      r"uncover|copyright on this publication was renewed|typographical errors|silently corrected|"
                      r"spelling (?:and|&amp;|&) typograph)(?:(?!</\1>).)*?</\1>", re.S | re.I)
TN_TAIL = re.compile(r"<b>\s*(?:<span[^>]*>)?\s*Transcriber.{0,3}s?\s+Notes?:?\s*(?:</span>)?\s*</b>(?:(?!<h[1-6]\b).)*\Z", re.S | re.I)   # bare note at the end
NOTE_P = re.compile(r"<p\b[^>]*>(?:(?!</p>).)*(?:e-?text|e-?book) was produced from(?:(?!</p>).)*</p>", re.I | re.S)


SCAN_DIR = ROOT / ".seed_cache" / "pulp" / "scan"
SCAN_NOTE = ('<p class="source-note"><i>This text was recovered from a scan of the magazine at the Internet '
             'Archive, machine-read and corrected.</i></p>')


def scan_file(r: dict) -> Path:
    """The scan-recovered text for a story (scripts/scan_pulp_issue.py), if one was made."""
    y, m = issue_key(r["issue"])
    stem = MAGS[r["magazine"]]["stem"]
    slug = re.sub(r"[^a-z0-9]+", "-", norm(re.sub(r"\[.*?\]", "", r["title"]))).strip("-")[:60]
    return SCAN_DIR / f"{stem}_{y}-{m:02d}" / f"{slug}.json"


def text_key(r: dict) -> str:
    if r["gutenberg"]:
        return r["gutenberg"]
    if r["in_reading_room"]:
        return f"lib:{norm(r['title'])}:{surname(r['author'])}"
    return f"scan:{scan_file(r)}"


def display_title(t: str) -> str:
    return re.sub(r"\s*\[.*?\]\s*", " ", t).strip()


def _library_index(con) -> dict[str, list[tuple[int, str]]]:
    idx: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for bid, slug, title, author in con.execute("select id, slug, title, author from books"):
        if slug.startswith(STEMS):
            continue
        idx[norm(re.split(r"[:;]", title or "")[0])].append((bid, norm(author or "")))
    return idx


def _library_book(idx, title: str, author: str):
    sn = surname(author)
    for bid, auth in idx.get(norm(display_title(title)), []):
        if sn and sn in auth:
            return bid
    return None


# Fiction genres an issue can be shelved under besides its magazine's own. A story's genres come
# from its standalone copy in the library when there is one (already hand-shelved), otherwise
# from its Gutenberg subject headings.
GENRES = ("Horror & Gothic", "Fantasy", "Science Fiction", "Mystery & Crime", "Adventure")
SUBJECT_GENRE = (("horror", "Horror & Gothic"), ("ghost", "Horror & Gothic"), ("supernatural", "Horror & Gothic"),
                 ("vampire", "Horror & Gothic"), ("werewol", "Horror & Gothic"), ("gothic", "Horror & Gothic"),
                 ("fantasy", "Fantasy"), ("sword and sorcery", "Fantasy"), ("conan (fictitious", "Fantasy"),
                 ("science fiction", "Science Fiction"), ("space opera", "Science Fiction"), ("interplanetary", "Science Fiction"),
                 ("detective", "Mystery & Crime"), ("mystery", "Mystery & Crime"), ("crime", "Mystery & Crime"),
                 ("adventure", "Adventure"))


def _pg_subjects() -> dict[str, str]:
    path = ROOT / ".seed_cache" / "pulp" / "pg_catalog.csv"
    if not path.exists():
        return {}
    # Subjects (LCSH) only: the Bookshelves field's "Science-Fiction & Fantasy" category lumps
    # every pulp story together and would tag horror as fantasy
    return {r["Text#"]: (r.get("Subjects") or "").lower()
            for r in csv.DictReader(open(path, encoding="utf-8"))}


def _library_sections(con) -> dict[str, list[tuple[str, list[str]]]]:
    idx: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for slug, title, author, section in con.execute("select slug, title, author, section from books"):
        if slug.startswith(STEMS):
            continue
        try:
            secs = json.loads(section or "[]")
        except ValueError:
            secs = []
        idx[norm(re.split(r"[:;]", title or "")[0])].append((norm(author or ""), secs))
    return idx


def story_genres(r: dict, lib: dict, pg: dict) -> list[str]:
    sn = surname(r["author"])
    for auth, secs in lib.get(norm(display_title(r["title"])), []):
        if sn and sn in auth and any(g in GENRES for g in secs):
            return [g for g in secs if g in GENRES]
    subj = pg.get(r["gutenberg"].rsplit("/", 1)[1], "") if r["gutenberg"] else ""
    return list(dict.fromkeys(g for kw, g in SUBJECT_GENRE if kw in subj))


def plan(rows: list[dict]) -> "OrderedDict[tuple, dict]":
    """Issue -> {magazine, label, year, month, contents[], stories[]}; stories are text units."""
    issues: "OrderedDict[tuple, dict]" = OrderedDict()
    for r in rows:
        y, m = issue_key(r["issue"])
        key = (r["magazine"], y, m)
        issues.setdefault(key, {"magazine": r["magazine"], "printed": r.get("issue_title") or r["magazine"],
                                "label": r["issue"], "year": y, "month": m,
                                "contents": [], "stories": []})["contents"].append(r)

    # serials: every installment of one novel, across issues
    serials: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if SERIAL.search(r["title"]):
            serials[(r["magazine"], norm(display_title(r["title"])), surname(r["author"]))].append(r)

    for key, iss in issues.items():
        for r in iss["contents"]:
            has_text = r["gutenberg"] or r["in_reading_room"]
            sm = SERIAL.search(r["title"])
            if sm:
                parts = sorted(serials[(r["magazine"], norm(display_title(r["title"])), surname(r["author"]))],
                               key=lambda p: issue_key(p["issue"]))
                if not all(p["public_domain_from"] == "now" for p in parts):
                    continue                                   # some installment still protected
                if not any(p["gutenberg"] or p["in_reading_room"] for p in parts):
                    continue
                src = next((p for p in parts if p["gutenberg"] or p["in_reading_room"]), r)
                first, last = parts[0]["issue"], parts[-1]["issue"]
                iss["stories"].append({"row": r, "src": src, "serial": (int(sm.group(1)), int(sm.group(2)), first, last)})
            elif r["public_domain_from"] == "now" and (has_text or scan_file(r).exists()):
                iss["stories"].append({"row": r, "src": r, "serial": None})
    return OrderedDict((k, v) for k, v in issues.items() if v["stories"])


def status_label(r: dict, included: bool) -> str:
    if included:
        return "In this collection"
    p = r["public_domain_from"]
    if p == "now":
        return "Public domain; not yet in the Reading Room"
    if p.startswith("2027"):
        return "Public domain from January 1, 2027"
    if p == "unverified":
        return "Copyright renewal not yet verified"
    return f"Under copyright through {int(p[:4]) - 1}"


def contents_html(iss: dict, included: set[int]) -> str:
    mag = iss["printed"]
    lines = [f"<h3>Contents</h3>",
             f"<p>The fiction and verse from the {html.escape(iss['label'])} issue of <i>{mag}</i>. "
             f"Stories marked “In this collection” follow in page order; the others are listed so the "
             f"issue reads whole, and are added as they’re transcribed.</p>", "<ul>"]
    for i, r in enumerate(iss["contents"]):
        lines.append(f"<li><b>{html.escape(display_title(r['title']))}</b> · {html.escape(r['author'])} "
                     f"<i>({html.escape(r['type'])}, p. {html.escape(r['page'].lstrip('_'))})</i><br>"
                     f"{status_label(r, i in included)}</li>")
    lines.append("</ul>")
    return "\n".join(lines)


async def fetch_texts(units: list[dict], con) -> dict[str, list[dict]]:
    """source key -> cleaned chapters. Library copies first; Gutenberg fetched once per id."""
    idx, out, need = _library_index(con), {}, {}
    for u in units:
        r = u["src"]
        k = text_key(r)
        if k in out or k in need:
            continue
        if k.startswith("scan:"):
            d = json.loads(Path(k[5:]).read_text(encoding="utf-8"))
            verse = d.get("type") == "poem"
            if d["paragraphs"] and not verse:   # the magazine set the opening word in capitals: "AND so"
                first, _, rest = d["paragraphs"][0].partition(" ")
                if len(first) > 1 and first.isupper() and first.isalpha():
                    d["paragraphs"][0] = first.capitalize() + " " + rest
            body = "\n".join(f"<p>{html.escape(t).replace(chr(10), '<br>') if verse else html.escape(t)}</p>"
                             for t in d["paragraphs"])
            out[k] = [{"title": display_title(d["title"]), "html": body + "\n" + SCAN_NOTE}]
            continue
        bid = _library_book(idx, r["title"], r["author"]) if r["in_reading_room"] else None
        chs = [{"title": t, "html": h} for t, h in con.execute(
            "select title, html from book_chapters where book_id=? order by section_number", (bid,))] if bid else []
        if chs:
            out[k] = chs
        elif r["gutenberg"]:                           # not in our library, or our copy has no text
            gid = r["gutenberg"].rsplit("/", 1)[1]
            cached = TEXT_CACHE / f"pg{gid}.json"
            if cached.exists():
                out[k] = json.loads(cached.read_text(encoding="utf-8"))
            else:
                need[k] = r
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as client:
        sem = asyncio.Semaphore(4)

        async def one(k, r):
            async with sem:
                gid = r["gutenberg"].rsplit("/", 1)[1]
                try:
                    book = await asyncio.wait_for(gb.fetch_book(client, gid, {"title": r["title"], "author": r["author"]}), 120)
                except Exception:  # noqa: BLE001
                    book = None
                return k, book

        TEXT_CACHE.mkdir(parents=True, exist_ok=True)
        for k, book in await asyncio.gather(*(one(k, r) for k, r in need.items())):
            if book:
                out[k] = [{"title": c["title"], "html": _norm_ws(_strip_pg(c["html"]))} for c in book["chapters"]]
                (TEXT_CACHE / f"pg{k.rsplit('/', 1)[1]}.json").write_text(json.dumps(out[k]), encoding="utf-8")
    for k in out:   # drop Gutenberg's provenance notes; the collection says where each story ran
        out[k] = [{"title": c["title"],
                   "html": TN_TAIL.sub("", TN_BLOCK.sub("", TN_DIV.sub("", PAGE_MARK.sub("", NOTE_P.sub("", c["html"])))))}
                  for c in out[k]]
        out[k] = [c for c in out[k] if words(c["html"]) >= 20] or out[k]   # a chapter that was only a note
    return out


def strip_byline(body: str, author: str, title: str = "") -> str:
    """Clear the source's own opening furniture from the top of a story, which the collection
    already shows: its byline ("By NELSON S. BOND", "by Wallace West"), a heading that only
    repeats the title, a "Transcribed from ..." note, rule lines, and blank paragraphs.
    Stops at the first thing that is the story itself (or an illustration caption)."""
    sn = surname(author)
    token = re.compile(r"\s*(?:<hr\b[^>]*/?>|<(p|h[1-6]|div|figure)\b[^>]*>(.*?)</\1>|([^<]+))", re.S | re.I)
    for _ in range(10):
        m = token.match(body)
        if not m or m.end() == 0:
            break
        tag = (m.group(1) or "").lower()
        text = " ".join(re.sub(r"<[^>]+>", " ", m.group(2) if tag else (m.group(3) or "")).split())
        is_rule = not tag and m.group(3) is None
        byline = re.match(r"(?i)by\s", text) and len(text) < 90 and sn and sn in norm(text)
        repeat_title = tag.startswith("h") and title and norm(text) == norm(title)
        note = re.match(r"(?i)transcribed from\b", text)
        if is_rule or not text or byline or repeat_title or note:
            body = body[m.end():]
            continue
        break
    return body


def words(h: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", h).split())


def build_book(key, iss, texts, covers, lib, pg) -> tuple[dict | None, list[str]]:
    family, mag = iss["magazine"], iss["printed"]
    stem, section = MAGS[family]["stem"], MAGS[family]["section"]
    y, m = iss["year"], iss["month"]
    chapters, included, skipped, authors, genres = [], set(), [], [], []
    order = {id(r): i for i, r in enumerate(iss["contents"])}
    for u in sorted(iss["stories"], key=lambda u: int(re.sub(r"\D", "", u["row"]["page"]) or 0)):
        r, src = u["row"], u["src"]
        k = text_key(src)
        chs = texts.get(k)
        if not chs:
            skipped.append(f"{display_title(r['title'])} (no text)")
            continue
        total = sum(words(c["html"]) for c in chs)
        cap = MAX_WORDS.get(r["type"])
        if not u["serial"] and cap and total > cap * 2.5:
            skipped.append(f"{display_title(r['title'])} ({total:,} words; looks like a whole collection)")
            continue
        title = display_title(r["title"])
        while len(chs) > 1 and words(chs[0]["html"]) < 60 and (
                (chs[0]["title"] or "").lower().startswith("by ") or norm(chs[0]["title"] or "") == norm(title)):
            chs = chs[1:]                                  # a title page, not part of the story
        head = f"<h2>{html.escape(title)}</h2>\n<p><i>by {html.escape(r['author'])}</i></p>\n"
        if u["serial"]:
            part, of, first, last = u["serial"]
            head += (f"<p><i>Serialized in {mag} in {of} parts, {html.escape(first)} to {html.escape(last)}. "
                     f"This issue carried part {part}; the complete novel follows.</i></p>\n")
        for i, c in enumerate(chs):
            body = c["html"]
            if i == 0 and len(chs) == 1:   # a lone chapter that repeats the story title as its heading
                body = re.sub(r"^\s*<h[1-6][^>]*>\s*(?:<[^>]+>\s*)*" + re.escape(html.escape(title)) + r".*?</h[1-6]>",
                              "", body, count=1, flags=re.I | re.S)
            if i == 0:
                body = strip_byline(body, r["author"], title)
            sub = (c["title"] or "").strip()
            if sub.lower().startswith("by ") or norm(sub) == norm(title):
                sub = ""                                  # a byline or the title again, not a chapter name
            ct = title if len(chs) == 1 or (i == 0 and not sub) else f"{title}: {sub or i + 1}"
            chapters.append({"title": ct, "html": (head if i == 0 else "") + body})
        included.add(order[id(r)])
        genres.extend(story_genres(src, lib, pg))
        if r["author"] not in authors:
            authors.append(r["author"])
    if not chapters:
        return None, skipped
    all_ch = [{"title": "Contents", "html": contents_html(iss, included)}] + chapters
    for n, c in enumerate(all_ch, 1):
        c["section_number"], c["words"] = n, words(c["html"])
    ym = f"{y}{m:02d}"
    cover = covers.get(family, {}).get(ym) or covers.get(family, {}).get(f"{y}{SEASON_CODE.get(m, '')}")
    byline = ", ".join(authors[:3]) + (" and others" if len(authors) > 3 else "")
    return {
        "slug": f"{stem}_{y}-{m:02d}", "title": f"{mag}, {iss['label']}",
        "author": byline, "author_sort": f"{family} {y}-{m:02d}",
        "sections": list(dict.fromkeys([section] + genres)),   # the magazine's shelf first
        "subjects": [f"{family} (magazine)", "Pulp fiction"] + authors,
        "cover_url": cover[0] if cover else None, "chapters": all_ch,
        "word_count": sum(c["words"] for c in all_ch), "n_stories": len(included),
    }, skipped


def store(con, b: dict) -> None:
    cur = con.cursor()
    row = cur.execute("select id from books where slug=?", (b["slug"],)).fetchone()
    if row:
        cur.execute("delete from book_chapters where book_id=?", (row[0],))
        cur.execute("delete from books where id=?", (row[0],))
    cols = {r[1] for r in con.execute("pragma table_info(books)")}
    data = {"slug": b["slug"], "title": b["title"], "author": b["author"], "author_sort": b["author_sort"],
            "source": gb.SOURCE, "license": gb.LICENSE, "us_clear": 1, "language": "en",
            "subjects": json.dumps(b["subjects"]), "genres": json.dumps(b["sections"]),
            "section": json.dumps(b["sections"]), "cover_url": b["cover_url"],
            "chapter_count": len(b["chapters"]), "word_count": b["word_count"]}
    data = {k: v for k, v in data.items() if k in cols}
    cur.execute(f"insert into books({','.join(data)}) values({','.join('?' * len(data))})", list(data.values()))
    bid = cur.lastrowid
    cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                    [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in b["chapters"]])
    con.commit()


async def main_async(args) -> None:
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    issues = plan(rows)
    units = [u for iss in issues.values() for u in iss["stories"]]
    print(f"{len(issues)} issues with text, {len(units)} story placements "
          f"({sum(1 for u in units if u['serial'])} serial installments)")
    if args.dry_run:
        for (mag, y, m), iss in list(issues.items())[:8]:
            print(f"  {mag}, {iss['label']}: {[display_title(u['row']['title']) for u in iss['stories']]}")
        return
    con = sqlite3.connect(DB, timeout=120)
    texts = await fetch_texts(units, con)
    print(f"texts: {len(texts)} distinct works ready")
    covers = {}
    for mag, cfg in MAGS.items():
        covers[mag] = {}
        for ref in cfg["gc"].split("|"):
            for ym, v in _gc_series(ref, False, mag).items():
                covers[mag].setdefault(ym, v)
    lib, pg = _library_sections(sqlite3.connect(f"file:{DB}?mode=ro", uri=True)), _pg_subjects()
    made = skipped_n = 0
    for key, iss in issues.items():
        b, skipped = build_book(key, iss, texts, covers, lib, pg)
        for s in skipped:
            print(f"  skip in {iss['magazine']}, {iss['label']}: {s}")
        skipped_n += len(skipped)
        if b:
            store(con, b)
            made += 1
    con.close()
    print(f"\nbuilt {made} issue collections ({skipped_n} story placements skipped). Covers next:\n"
          f"  .venv\\Scripts\\python.exe scripts\\build_covers_db.py && .venv\\Scripts\\python.exe scripts\\build_covers_db.py --finalize")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed Weird Tales / Fantastic Adventures issue collections")
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
