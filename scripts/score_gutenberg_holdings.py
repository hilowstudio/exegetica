"""Score the Reading Room's Gutenberg books on whether they've earned their shelf space.

The original harvest (harvest_gutenberg.py) admitted any book on a named Gutenberg bookshelf, but
most of those shelves are volunteer topic folders (Technology, Physiology, Crafts), not quality
picks — which is how a TRS-80 operator's manual got in. This scores each held book on signals of a
work that lasted, then sorts it into keep / review / remove.

Signals (all cached under .seed_cache/pd_sources):
  editions    Open Library edition count: how often the work has been republished (the strongest
              single signal; fetch_openlibrary_signals.py -> ol_signals.json)
  readers     Open Library want-to-read + already-read shelvings
  canon       on a Gutenberg list that IS a quality judgment: Harvard Classics, Best Books Ever
              Listings, Bestsellers American 1895-1923
  article     the work itself has a Wikipedia article (Wikidata P2034 -> sitelinks; sparse)
  author      the author's Wikipedia language count (Wikidata P1938, people only: a corporate
              "author" like Radio Shack isn't notability); it only softens a removal into a
              review, never keeps a book alone
  downloads   Gutenberg 30-day downloads; ~300 is a crawler floor, so only far-above-floor counts
Thresholds are calibrated on the canon books (see --calibrate), not on our holdings, which were
never curated for quality.

Writes docs/reading-room/gutenberg-holdings-review.csv.

    python scripts/score_gutenberg_holdings.py [--calibrate]
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".seed_cache" / "pd_sources"
CATALOG = ROOT / ".seed_cache" / "pg_catalog_2026-10-05.csv"
OUT = ROOT / "docs" / "reading-room" / "gutenberg-holdings-review.csv"
CANON = ("Harvard Classics", "Best Books Ever Listings", "Bestsellers, American, 1895-1923")
csv.field_size_limit(10**8)

# keep: any one of these; remove: none of the softer ones either
KEEP_EDITIONS = 8
KEEP_READERS = 5
KEEP_DOWNLOADS = 1500
REVIEW_EDITIONS = 3
REVIEW_READERS = 1
REVIEW_AUTHOR = 15


def load():
    rdf = json.loads((SRC / "pg_rdf_signals.json").read_text())
    authors = {a["pga"]: int(a["sl"]) for a in json.loads((SRC / "wd_pg_authors.json").read_text())}
    works = {}
    for w in json.loads((SRC / "wd_pg_works.json").read_text()):
        works[w["pg"]] = max(int(w["sl"]), int(w.get("wsl") or 0), works.get(w["pg"], 0))
    ol = json.loads((SRC / "ol_signals.json").read_text(encoding="utf-8")) if (SRC / "ol_signals.json").exists() else {}
    cat = {r["Text#"]: r for r in csv.DictReader(open(CATALOG, encoding="utf-8"))}
    return rdf, authors, works, ol, cat


def signals(gid: str, key: str, rdf, authors, works, ol, cat) -> dict:
    r = rdf.get(gid, {})
    o = ol.get(key) or {}
    c = cat.get(gid, {})
    return dict(
        editions=o.get("edition_count", 0), readers=(o.get("want", 0) + o.get("read", 0)),
        ol_matched=bool(o), first_year=o.get("first_year") or "",
        canon=any(x in (c.get("Bookshelves") or "") for x in CANON),
        article=works.get(gid, 0),
        author=max([authors.get(a, 0) for a in r.get("agents", [])] or [0]),
        downloads=r.get("dl", 0),
        shelves="; ".join(s.strip() for s in (c.get("Bookshelves") or "").split(";")
                          if s.strip() and not s.strip().startswith("Category:")),
        locc=c.get("LoCC") or "")


def tier(s: dict) -> tuple[str, str]:
    why = []
    if s["canon"]:
        why.append("on a canon list")
    if s["article"]:
        why.append(f"work has Wikipedia article ({s['article']} langs)")
    if s["editions"] >= KEEP_EDITIONS:
        why.append(f"{s['editions']} editions")
    if s["readers"] >= KEEP_READERS:
        why.append(f"{s['readers']} readers shelved it")
    if s["downloads"] >= KEEP_DOWNLOADS:
        why.append(f"{s['downloads']} downloads/30d")
    if why:
        return "keep", "; ".join(why)
    soft = []
    # Print-on-demand reprints give obscure practical titles several editions (The Sewerage of
    # Sea Coast Towns: 6, no readers). In applied classes - science, medicine, agriculture,
    # technology - editions only count alongside some readership; literature/history keep it.
    applied = (s["locc"] or "")[:1] in ("Q", "R", "S", "T")
    if s["editions"] >= REVIEW_EDITIONS and (s["readers"] >= 1 or not applied):
        soft.append(f"{s['editions']} editions")
    if s["readers"] >= REVIEW_READERS:
        soft.append(f"{s['readers']} readers")
    if s["author"] >= REVIEW_AUTHOR:
        soft.append(f"notable author ({s['author']} langs)")
    if soft:
        return "review", "; ".join(soft)
    return "remove", (f"{s['editions']} editions, {s['readers']} readers, author {s['author']} langs"
                      + ("" if s["ol_matched"] else ", not found on Open Library"))


def calibrate(rdf, authors, works, ol, cat, held):
    """How the canon books and our holdings would tier under the current thresholds."""
    canon_held = [(g, k) for g, k in held if any(x in (cat.get(g, {}).get("Bookshelves") or "") for x in CANON)]
    print("canon books we hold, scored WITHOUT the canon flag (should be nearly all keep):")
    c = Counter()
    for g, k in canon_held:
        s = signals(g, k, rdf, authors, works, ol, cat)
        s["canon"] = False
        c[tier(s)[0]] += 1
    print("  ", dict(c), f"of {len(canon_held)}")


def main():
    rdf, authors, works, ol, cat = load()
    con = sqlite3.connect(f"file:{ROOT / 'db' / 'books.db'}?mode=ro", uri=True)
    books = con.execute("select slug, title, author, genres, word_count from books where source='gutenberg'").fetchall()
    held = [(m.group(1), slug) for slug, *_ in books if (m := re.search(r"-pg(\d+)$", slug))]
    if "--calibrate" in sys.argv:
        calibrate(rdf, authors, works, ol, cat, held)
        return
    pulp = set()
    for r in csv.DictReader(open(ROOT / "docs" / "reading-room" / "pulp-eligible-stories.csv", encoding="utf-8")):
        pulp.update(re.findall(r"\d+", r.get("gutenberg") or ""))
    out = []
    for slug, title, author, genres, words in books:
        m = re.search(r"-pg(\d+)$", slug)
        if not m:
            continue
        s = signals(m.group(1), slug, rdf, authors, works, ol, cat)
        t, why = tier(s)
        c = cat.get(m.group(1), {})
        # collections Adam added on purpose, so a removal there is his call, not the score's
        if re.search(r"dime novel", f"{c.get('Subjects', '')} {c.get('Bookshelves', '')}", re.I):
            group = "dime novel"
        elif m.group(1) in pulp:
            group = "magazine story (also in a pulp issue)"
        elif (words or 0) < 10000:
            group = "short (<10k words)"
        else:
            group = ""
        # Adam's rulings (2026-10-06): magazine SF standalones stay; dime novels and short works
        # are judged one by one on their merits, never dropped on score or length alone
        if group.startswith("magazine story"):
            t, why = "keep", f"magazine standalone kept by policy; {why}"
        elif group in ("dime novel", "short (<10k words)") and t == "remove":
            t = "evaluate"
        out.append(dict(tier=t, group=group, reason=why, title=title, author=author, genres=genres, words=words or 0,
                        editions=s["editions"], readers=s["readers"], first_year=s["first_year"],
                        canon=int(s["canon"]), work_article_langs=s["article"], author_langs=s["author"],
                        downloads=s["downloads"], shelves=s["shelves"], locc=s["locc"], gutenberg=m.group(1),
                        slug=slug))
    order = {"remove": 0, "evaluate": 1, "review": 2, "keep": 3}
    out.sort(key=lambda x: (order[x["tier"]], x["genres"] or "", x["title"] or ""))
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out):,} books)")
    print(Counter(x["tier"] for x in out))


if __name__ == "__main__":
    main()
