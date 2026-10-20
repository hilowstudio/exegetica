"""Import one Reading Room shelf's approved additions from the curation ledger.

The shelf-by-shelf curation pass wrote every Gutenberg candidate's decision to
.seed_cache/reading_room/candidate_decisions.csv (gutenberg, decision, shelf, title, authors,
reason, batch). This script ingests the `add` rows for ONE shelf per run, through the same
clean-chapter path as seed_horror.py (gb.fetch_book), so a long import can go shelf by shelf
instead of as one huge run.

One work = one book:
  * split volumes of one work (same author + base title, each marked Vol./Part/Book N) are
    fetched in volume order and merged into a single book;
  * volumes listed in carry_adds.json (approved on this shelf but recorded under another)
    join their set's merge;
  * pulp magazine stories by the named pulp authors (2019+ Gutenberg releases) are merged into
    one "Pulp Stories" book per author.

Resumable: a work whose `-pg{id}` slug is already in books.db is skipped. Covers point at the
PG cover jpeg; self-host them afterwards like the rest of the corpus.

    .venv\\Scripts\\python.exe scripts\\import_shelf_adds.py --list
    .venv\\Scripts\\python.exe scripts\\import_shelf_adds.py --shelf "Fantasy" --dry-run
    .venv\\Scripts\\python.exe scripts\\import_shelf_adds.py --shelf "Fantasy"
    .venv\\Scripts\\python.exe scripts\\build_covers_db.py && .venv\\Scripts\\python.exe scripts\\build_covers_db.py --finalize
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from build_pulp_eligibility import norm, surname  # noqa: E402
from format_gutenberg import clean_book, dedup_book  # noqa: E402
from webapp.sources import gutenberg as gb  # noqa: E402
from webapp.sources.matching import BROWSER_UA  # noqa: E402

_CACHE = _ROOT / ".seed_cache" / "reading_room"
_LEDGER = _CACHE / "candidate_decisions.csv"
_CARRY = _CACHE / "carry_adds.json"
_CATALOG = _CACHE / "pg_catalog_en.csv"

# named pulp authors whose 2019+ Gutenberg releases are single magazine stories
_PULP = re.compile(r"Tuttle, W|Bedford-Jones|Smith, Arthur D. Howden|Burtis, Thomson|Coburn, Walt|"
                   r"Savage, Les|Dunning, Hal|Dunn, J. Allan|McCreagh|Packard, Frank|Gardner, Erle|"
                   r"Powers, Paul S|Drago, Harry|Mundy, Talbot|Marshall, Edison")
_VOL = re.compile(r"[\s,;.—-]*\(?\b(?:vol(?:ume)?|part|book|no)\.?\s*([\divxlc]+)\b.*$", re.I)
_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def _roman(s: str) -> int | None:
    s = s.lower()
    if s.isdigit():
        return int(s)
    if not s or any(ch not in _ROMAN for ch in s):
        return None
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = _ROMAN[a]
        total += -v if b != " " and _ROMAN.get(b, 0) > v else v
    return total


def _first_author(authors: str) -> str:
    a = (authors or "").split(";")[0]
    a = re.sub(r"\s*\[[^\]]*\]", "", a)                      # role tags: [Illustrator]
    parts = [x.strip() for x in a.split(",")]
    while len(parts) > 1 and re.search(r"\d|^(?:active|fl\.|approximately|b\.|d\.)", parts[-1]):
        parts.pop()                                         # life dates: "1859-1930", "106 BCE-43 BCE"
    return ", ".join(parts).strip() or "Anonymous"


_HONORIFIC = re.compile(r"^(?:Sir|Lady|Dame|Saint|Rev\.|Mrs\.|Mr\.|Dr\.|graf|hrabě|Baron.*|Earl.*|Lord.*)$", re.I)


def _display(author: str) -> tuple[str, str]:
    """'Surname, Given[, Jr.|, Sir]' → ('Given Surname[ Jr.]', 'Surname, Given'). Honorifics drop."""
    parts = [x.strip() for x in author.split(",") if x.strip()]
    if len(parts) < 2:
        return author, author
    surname, given, rest = parts[0], parts[1], parts[2:]
    suffix = " ".join(r for r in rest if re.fullmatch(r"(?:Jr|Sr)\.?|I{1,3}|IV", r))
    display = f"{given} {surname}" + (f" {suffix}" if suffix else "")
    if _HONORIFIC.match(given):                     # "Gregory, Lady" → "Lady Gregory"
        display = f"{given} {surname}"
    return display.strip(), f"{surname}, {given}"


def _clean_title(raw: str) -> str:
    t = (raw or "").splitlines()[0].strip()
    t = re.sub(r"\s*[—-]+\s*Complete$|,\s*Complete$", "", t, flags=re.I)
    t = re.split(r";\s*or,?\s", t, flags=re.I)[0]
    if ":" in t and len(t.split(":")[0].split()) >= 1:
        t = t.split(":")[0]
    return t.strip(" ,;.[(") or raw


def _base(raw: str) -> tuple[str, int | None]:
    """(base title, volume number) — volume is None for a whole work."""
    first = (raw or "").splitlines()[0]
    m = _VOL.search(first)
    if not m:
        return _clean_title(first).lower(), None
    return _clean_title(first[:m.start()]).lower(), _roman(m.group(1))


def _surname(author: str) -> str:
    return author.split(",")[0].strip().lower()


def _load(shelf: str) -> list[dict]:
    """The shelf's works: each {gids:[…], title, author, subjects, pulp:bool}."""
    cat = {r["Text#"]: r for r in csv.DictReader(open(_CATALOG, encoding="utf-8"))}
    adds = [r for r in csv.DictReader(open(_LEDGER, encoding="utf-8"))
            if r["decision"] == "add" and r["shelf"] == shelf]
    carry = list(json.load(open(_CARRY, encoding="utf-8")))

    def info(gid):
        c = cat.get(gid, {})
        raw = c.get("Title") or ""
        author = _first_author(c.get("Authors") or "")
        base, vol = _base(raw)
        return {"gid": gid, "raw": raw, "author": author, "base": base, "vol": vol,
                "issued": c.get("Issued") or "", "subjects": c.get("Subjects") or ""}

    items = [info(r["gutenberg"]) for r in adds]
    keys = {(_surname(i["author"]), i["base"]) for i in items if i["vol"] is not None}
    for gid in carry:                                   # carry volumes join their set's group
        i = info(gid)
        if i["vol"] is not None and (_surname(i["author"]), i["base"]) in keys:
            items.append(i)

    works, groups, pulp = [], {}, {}
    for i in items:
        if shelf == "Adventure" and _PULP.search(i["author"]) and i["issued"][:4] >= "2019":
            pulp.setdefault(i["author"], []).append(i)
        elif i["vol"] is not None:
            groups.setdefault((_surname(i["author"]), i["base"]), []).append(i)
        else:
            works.append({"gids": [i["gid"]], "title": _clean_title(i["raw"]), "author": i["author"],
                          "subjects": i["subjects"], "raw": i["raw"], "pulp": False})
    for members in groups.values():
        members.sort(key=lambda m: (m["vol"] or 0, int(m["gid"])))
        first = members[0]
        title = _clean_title(first["raw"][:_VOL.search(first["raw"].splitlines()[0]).start()]
                             if _VOL.search(first["raw"].splitlines()[0]) else first["raw"])
        works.append({"gids": [m["gid"] for m in members], "title": title, "author": first["author"],
                      "subjects": first["subjects"], "raw": first["raw"], "pulp": False})
    for author, stories in pulp.items():
        stories.sort(key=lambda s: int(s["gid"]))
        works.append({"gids": [s["gid"] for s in stories], "title": "Pulp Stories", "author": author,
                      "subjects": "Pulp literature", "raw": "Pulp Stories", "pulp": True,
                      "story_titles": [_clean_title(s["raw"]) for s in stories]})
    return works


def _cover(gid: str) -> str:
    return f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.cover.medium.jpg"


async def _fetch_work(client, work: dict, timeout: float) -> dict | None:
    merged, wc, src, missing = [], 0, 0, []
    for n, gid in enumerate(work["gids"]):
        meta = {"author": work["author"], "title": work["title"], "genre": None,
                "subjects": work["subjects"].replace(" -- ", " — ")}
        try:
            vol = await asyncio.wait_for(gb.fetch_book(client, gid, meta), timeout=timeout)
        except Exception:  # noqa: BLE001 — one bad volume never kills the run
            vol = None
        if not vol:
            missing.append(gid)
            continue
        story = work.get("story_titles", [None] * len(work["gids"]))[n]
        for ch in vol["chapters"]:
            title = ch["title"]
            if story:                                   # pulp: label chapters by story
                title = story if len(vol["chapters"]) == 1 else f"{story}: {title}"
            merged.append({"section_number": len(merged) + 1, "title": title,
                           "html": ch["html"], "words": ch["words"]})
        wc += vol["word_count"]
        src += vol.get("source_words") or vol["word_count"]
    if not merged:
        return None
    display, sort = _display(work["author"])
    return {
        "slug": (f"{gb._slugify(display)}_{gb._slugify(work['title'])}"[:78] or "book") + f"-pg{work['gids'][0]}",
        "title": work["title"], "author": display, "author_sort": sort, "language": "en",
        "subjects": [s.strip() for s in work["subjects"].split(";") if s.strip()],
        "chapters": merged, "word_count": wc, "source_words": src, "missing": missing,
    }


def _store(con, book: dict, section: list[str], cover: str, raw_title: str) -> None:
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
         1, "en", json.dumps(book["subjects"]), json.dumps(section), json.dumps(section),
         json.dumps(section), raw_title, cover, len(book["chapters"]), book["word_count"]))
    bid = cur.lastrowid
    cur.executemany(
        "insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
        [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in book["chapters"]])
    con.commit()
    n = con.execute("select count(*) from book_chapters where book_id=?", (bid,)).fetchone()[0]
    if n != len(book["chapters"]):
        raise RuntimeError(f"{book['slug']}: wrote {n} of {len(book['chapters'])} chapters")
    _finish(con, bid)


def _finish(con, bid: int) -> None:
    """The bulk importers' post-store pass: strip Gutenberg cruft, open each chapter on its
    heading, and disambiguate repeated chapter titles (merged volumes each restart at Chapter I)."""
    clean_book(con, bid)
    dedup_book(con, bid)


# titles too generic to prove two books are the same work
_GENERIC = {"poems", "essays", "letters", "works", "sermons", "tales", "stories", "plays", "miscellanies",
            "poetical works", "complete works", "collected poems", "selected poems", "speeches", "journal"}


def _work_key(title: str, author_display: str) -> tuple[str, str]:
    return norm(re.split(r"[:;]", title or "")[0]), surname(author_display or "")


def _flags(book: dict) -> list[str]:
    out = []
    if len(book["chapters"]) == 1 and book["word_count"] > 20000:
        out.append(f"one {book['word_count']:,}-word chapter")
    if book["word_count"] < 3000:
        out.append(f"only {book['word_count']:,} words")
    if book["source_words"] and book["word_count"] < 0.8 * book["source_words"]:
        out.append(f"kept {book['word_count'] / book['source_words']:.0%} of the page text")
    if book["missing"]:
        out.append(f"volumes not fetched: {', '.join(book['missing'])}")
    return out


async def _run(args) -> None:
    works = _load(args.shelf)
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    have = {m.group(1) for (s,) in con.execute("select slug from books")
            for m in [re.search(r"-pg(\d+)$", s or "")] if m}
    if args.clean_existing:                         # re-run the post-store pass on this shelf's imports
        firsts = {w["gids"][0] for w in works}
        ids = [bid for (bid, s) in con.execute("select id, slug from books")
               if (m := re.search(r"-pg(\d+)$", s or "")) and m.group(1) in firsts]
        for bid in ids:
            _finish(con, bid)
        print(f"{args.shelf}: cleaned {len(ids)} imported books")
        con.close()
        return
    mine = {g for w in works for g in w["gids"]}
    held = {_work_key(t, a) for (s, t, a) in con.execute("select slug, title, author from books")
            if not ((m := re.search(r"-pg(\d+)$", s or "")) and m.group(1) in mine)}
    imported = [] if args.refresh else [w for w in works if any(g in have for g in w["gids"])]
    rest = [w for w in works if w not in imported]
    dupes = [w for w in rest if not w["pulp"]
             and (k := _work_key(w["title"], _display(w["author"])[0]))[0] not in _GENERIC and k in held]
    todo = [w for w in rest if w not in dupes]
    if args.only:                                   # just these works (first Gutenberg id of each)
        only = set(args.only.split(","))
        todo = [w for w in todo if w["gids"][0] in only]
    merged = sum(1 for w in works if len(w["gids"]) > 1)
    print(f"{args.shelf}: {len(works)} works ({merged} merged from multiple files); "
          f"{len(imported)} already imported; {len(dupes)} already held in another edition; "
          f"{len(todo)} to fetch", flush=True)
    for w in dupes:
        print(f"  held elsewhere: pg{w['gids'][0]}  {w['title'][:50]}  ({w['author'][:30]})")
    if args.limit:
        todo = todo[:args.limit]
    section = [args.shelf]
    timeout = httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=15.0)
    ok = fail = 0
    failed, flagged = [], []
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": BROWSER_UA},
                                 follow_redirects=True) as client:
        sem = asyncio.Semaphore(args.concurrency)

        async def worker(work):
            async with sem:
                return work, await _fetch_work(client, work, args.timeout)

        tasks = [asyncio.create_task(worker(w)) for w in todo]
        for fut in asyncio.as_completed(tasks):
            work, book = await fut
            n = ok + fail + 1
            if not book:
                fail += 1
                failed.append(work["gids"][0])
                print(f"  [{n}/{len(todo)}] SKIP pg{work['gids'][0]}  {work['title'][:44]}", flush=True)
                continue
            note = f"  vols={len(work['gids'])}" if len(work["gids"]) > 1 else ""
            if book["missing"]:
                note += f"  missing={','.join(book['missing'])}"
            print(f"  [{n}/{len(todo)}] {book['title'][:40]:40} {book['word_count']:>8,}w "
                  f"{len(book['chapters']):>4}ch  {book['author'][:22]}{note}", flush=True)
            if not args.dry_run:
                _store(con, book, section, _cover(work["gids"][0]), work["raw"].splitlines()[0])
            flagged += [f"pg{work['gids'][0]} {book['title'][:44]}: {f}" for f in _flags(book)]
            ok += 1
    print(f"\n{'(dry-run) ' if args.dry_run else ''}{args.shelf}: {ok} imported, {fail} skipped "
          f"in {time.monotonic() - start:.0f}s" + (f"; failed: {' '.join(failed)}" if failed else ""))
    for f in flagged:
        print("  check:", f)
    con.close()


def _list() -> None:
    c = Counter(r["shelf"] for r in csv.DictReader(open(_LEDGER, encoding="utf-8")) if r["decision"] == "add")
    for shelf, n in sorted(c.items(), key=lambda kv: kv[1]):
        print(f"{n:>5}  {shelf}")


def main() -> None:
    p = argparse.ArgumentParser(description="Import one Reading Room shelf's approved additions.")
    p.add_argument("--shelf", help='exact shelf name, e.g. "Literary & Classics"')
    p.add_argument("--list", action="store_true", help="show add counts per shelf and exit")
    p.add_argument("--db", default="db/books.db")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", help="comma-separated first Gutenberg ids of the works to (re)import")
    p.add_argument("--refresh", action="store_true",
                   help="re-fetch and replace this shelf's already-imported books (after a parser fix)")
    p.add_argument("--clean-existing", action="store_true",
                   help="re-run cleanup on this shelf's already-imported books, then exit")
    args = p.parse_args()
    if args.list or not args.shelf:
        _list()
        return
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
