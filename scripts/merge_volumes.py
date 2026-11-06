"""Merge separately held volumes of one work into a single Reading Room book.

The first slug in each set keeps its row (and so its slug, cover and reading positions); the other
volumes' chapters are appended in order, their rows and covers are removed, and each absorbed volume
is logged to docs/reading-room/reading-room-deletions.csv with reason "merged into <slug>". Repeated chapter titles
across volumes (each restarting at Chapter I) are disambiguated by format_gutenberg.dedup_book.

A set can also pull a missing volume straight from Project Gutenberg: "fetch": [gutenberg ids] appends
it after the held volumes, and a "gutenberg:<id>" entry in "slugs" places it in order.

    python scripts/merge_volumes.py sets.json [--dry-run]

sets.json: [{"title": "Myth, Ritual and Religion", "slugs": ["…pg2832", "…pg36794"], "fetch": []}, …]
An optional "author" replaces the keeper's author (a set whose volumes have different authors).

A set too big for one book completes as separate volumes instead:
    {"separate": true, "slug": "<held volume>", "title": "London Labour and the London Poor, Volume {n}",
     "held": 4, "add": {"1": "55998", "2": "60440", "3": "57060"}}
The held volume is retitled; each added Gutenberg volume becomes its own book with the held one's
shelf, author and metadata.
"""
from __future__ import annotations

import asyncio
import csv
import datetime
import json
import html as _html
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from format_gutenberg import dedup_book  # noqa: E402

LOG = ROOT / "docs" / "reading-room" / "reading-room-deletions.csv"


async def _fetch(gids: list[str], author: str, title: str) -> list[dict]:
    import httpx  # noqa: PLC0415
    from webapp.sources import gutenberg as gb  # noqa: PLC0415
    from webapp.sources.matching import BROWSER_UA  # noqa: PLC0415
    out = []
    async with httpx.AsyncClient(timeout=180, headers={"User-Agent": BROWSER_UA}, follow_redirects=True) as client:
        for gid in gids:
            vol = await gb.fetch_book(client, int(gid), {"author": author, "title": title, "genre": None, "subjects": ""})
            if not vol:
                raise RuntimeError(f"could not fetch Gutenberg #{gid}")
            out.extend({"title": c["title"], "html": c["html"], "words": c["words"]} for c in vol["chapters"])
    return out


_PREFIX = re.compile(r"^Vols?\. [\dIVXL–-]+ · ")
_DROP = re.compile(r"^(?:table of )?(?:contents|index)(?: of (?:titles|authors|first lines))?\.?$", re.I)


def _retitle(ch: dict, title: str) -> dict:
    html = re.sub(r"(<(h[1-6])[^>]*>).*?(</>)", lambda m: m.group(1) + _html.escape(title) + m.group(3),
                  ch["html"], count=1, flags=re.S | re.I)
    return {**ch, "title": title, "html": html}


def _join(vols: list[list[dict]], labels: list[str] | None) -> list[dict]:
    """Concatenate volumes: drop the later volumes' title pages (a short leading chunk) and every
    contents page and page-number index, then label chapter titles that recur across volumes
    ("Vol. 2 · CHAPTER I.") so each volume's chapters stay distinct in the table of contents."""
    labels = labels or [f"Vol. {i + 1}" for i in range(len(vols))]
    kept = []
    for v, chs in enumerate(vols):
        chs = [c for c in chs if not _DROP.match(_PREFIX.sub("", c["title"].strip()))]
        while v and chs and chs[0]["words"] < 150:
            chs = chs[1:]
        kept.append([{**c, "title": _PREFIX.sub("", c["title"].strip())} for c in chs])
    seen: dict[str, set] = {}
    for v, chs in enumerate(kept):
        for c in chs:
            seen.setdefault(c["title"], set()).add(v)
    out = []
    for v, chs in enumerate(kept):
        for c in chs:
            out.append(_retitle(c, f"{labels[v]} · {c['title']}") if len(seen[c["title"]]) > 1 else c)
    return out


_COPY = ("author", "source", "license", "us_clear", "language", "subjects", "author_sort", "genres", "ddc", "lcc",
         "loc_subjects", "loc_how", "section", "genres_backup")


def _separate(con, s: dict, dry: bool) -> None:
    """Retitle the held volume and add each missing volume as its own book beside it."""
    from import_shelf_adds import _cover, _finish  # noqa: PLC0415
    held = con.execute(f"select id, {', '.join(_COPY)} from books where slug=?", (s["slug"],)).fetchone()
    if not held:
        raise SystemExit(f"not found: {s['slug']}")
    meta = dict(zip(_COPY, held[1:]))
    base = re.sub(r"-pg\d+$", "", s["slug"])
    print(f"{s['title'].format(n=s['held'])}: held + {len(s['add'])} added as separate volumes")
    if dry:
        return
    con.execute("update books set title=? where id=?", (s["title"].format(n=s["held"]), held[0]))
    for n, gid in s["add"].items():
        title = s["title"].format(n=n)
        chapters = asyncio.run(_fetch([gid], meta["author"], title))
        slug = f"{base}-pg{gid}"
        cols = ("slug", "title", "title_backup", "cover_url", "chapter_count", "word_count") + _COPY
        vals = (slug, title, title, _cover(gid), len(chapters), sum(c["words"] for c in chapters)) + tuple(meta.values())
        cur = con.execute(f"insert into books({', '.join(cols)}) values({', '.join('?' * len(cols))})", vals)
        con.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                        [(cur.lastrowid, i + 1, c["title"], c["html"], c["words"]) for i, c in enumerate(chapters)])
        con.commit()
        _finish(con, cur.lastrowid)
        print(f"  + {title} ({slug})")


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dry = "--dry-run" in sys.argv
    con = sqlite3.connect(ROOT / "db" / "books.db")
    covers = sqlite3.connect(ROOT / "db" / "covers.db")
    today = datetime.date.today().isoformat()
    log_rows = []
    for s in spec:
        if s.get("separate"):
            _separate(con, s, dry)
            continue
        rows = []
        for slug in s["slugs"]:
            if slug.startswith("gutenberg:"):                    # fetched in place: 'gutenberg:42930'
                continue
            r = con.execute("select id, title, author from books where slug=?", (slug,)).fetchone()
            if not r:
                raise SystemExit(f"not found: {slug}")
            rows.append((slug, *r))
        keep_slug, keep_id, _t, author = rows[0]
        held = {slug: bid for slug, bid, _t2, _a in rows}
        vols = []
        for slug in s["slugs"]:
            if slug.startswith("gutenberg:"):
                vols.append(asyncio.run(_fetch([slug.split(":", 1)[1]], author, s["title"])))
                continue
            vols.append([{"title": t, "html": h, "words": w} for t, h, w in con.execute(
                "select title, html, words from book_chapters where book_id=? order by section_number", (held[slug],))])
        for gid in s.get("fetch", []):
            vols.append(asyncio.run(_fetch([gid], author, s["title"])))
        chapters = _join(vols, s.get("labels"))
        words = sum(c["words"] for c in chapters)
        print(f"{s['title']}: {len(rows)} held + {len(vols) - len(rows)} fetched -> {len(chapters)} chapters, {words:,} words")
        if dry:
            continue
        con.execute("delete from book_chapters where book_id=?", (keep_id,))
        con.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                        [(keep_id, i + 1, c["title"], c["html"], c["words"]) for i, c in enumerate(chapters)])
        con.execute("update books set title=?, author=?, chapter_count=?, word_count=? where id=?",
                    (s["title"], s.get("author", author), len(chapters), words, keep_id))
        for slug, bid, title, a in rows[1:]:
            con.execute("delete from book_chapters where book_id=?", (bid,))
            con.execute("delete from books where id=?", (bid,))
            covers.execute("delete from covers where slug=?", (slug,))
            m = re.search(r"-pg(\d+)$", slug)
            log_rows.append([today, slug, title, a, m.group(1) if m else "", f"merged into {keep_slug}"])
        con.commit()
        covers.commit()
        dedup_book(con, keep_id)
    if log_rows:
        with open(LOG, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(log_rows)
    print(("would merge" if dry else "merged"), len(spec), "sets")


if __name__ == "__main__":
    main()
