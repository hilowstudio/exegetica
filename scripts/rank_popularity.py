"""Rank every Reading Room book by how much people actually read it, to order the edition reviews.

Signals:
  * Project Gutenberg downloads in the last 30 days (pgterms:downloads in the catalog RDF archive,
    .seed_cache/popularity/rdf-files.tar.bz2). Standard Ebooks and CCEL books are matched to their
    Gutenberg twin by normalised title + author surname.
  * Open Library readers: want-to-read + already-read + 5 x ratings, and edition count (staying power),
    from .seed_cache/pd_sources/ol_signals.json (scripts/fetch_openlibrary_signals.py).

score = 0.55 * log-downloads + 0.35 * log-readers + 0.10 * log-editions, each scaled 0..1 by the library max.

    python scripts/rank_popularity.py [--shelf "Horror & Gothic"] [--top 50]
Writes rank/score into db/reviews.db (titles) and .seed_cache/popularity/ranking.csv.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
import sys
import tarfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from review_title import rdb, now  # noqa: E402

POP = ROOT / ".seed_cache" / "popularity"
RDF = POP / "rdf-files.tar.bz2"
DL_CACHE = POP / "pg_downloads.json"
OL = ROOT / ".seed_cache" / "pd_sources" / "ol_signals.json"


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.split(r"[:;(]", s)[0]
    s = re.sub(r"^(the|a|an)\s+", "", s.strip())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def surname(a: str) -> str:
    a = re.sub(r"\(.*?\)|\[.*?\]|\d{3,4}\??-?\d*", "", a or "")
    if "," in a:
        a = a.split(",")[0]
    ws = re.findall(r"[A-Za-zÀ-ÿ'-]+", a)
    return fold(ws[-1] if ws else "")


def pg_downloads() -> dict[str, dict]:
    """{gid: {downloads, title, author}} from the RDF archive (cached as JSON after the first read)."""
    if DL_CACHE.exists():
        return json.loads(DL_CACHE.read_text(encoding="utf-8"))
    out = {}
    with tarfile.open(RDF, "r:bz2") as tf:
        for m in tf:
            if not m.name.endswith(".rdf"):
                continue
            x = tf.extractfile(m).read().decode("utf-8", "replace")
            gid = re.search(r'pgterms:ebook rdf:about="ebooks/(\d+)"', x)
            dl = re.search(r"<pgterms:downloads[^>]*>(\d+)<", x)
            if not gid:
                continue
            t = re.search(r"<dcterms:title>(.*?)</dcterms:title>", x, re.S)
            a = re.search(r"<pgterms:name>(.*?)</pgterms:name>", x, re.S)
            out[gid.group(1)] = {"downloads": int(dl.group(1)) if dl else 0,
                                 "title": (t.group(1) if t else "").strip(), "author": (a.group(1) if a else "").strip()}
    DL_CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    shelf = sys.argv[sys.argv.index("--shelf") + 1] if "--shelf" in sys.argv else None
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 40
    dls = pg_downloads()
    twin: dict[tuple, int] = {}                              # (title, surname) -> best Gutenberg downloads
    for gid, d in dls.items():
        k = (fold(d["title"]), surname(d["author"]))
        twin[k] = max(twin.get(k, 0), d["downloads"])
    ol = json.loads(OL.read_text(encoding="utf-8")) if OL.exists() else {}
    con = sqlite3.connect(ROOT / "db" / "books.db")
    rows = []
    for slug, title, author, genres in con.execute("select slug, title, coalesce(author,''), genres from books"):
        shelves = json.loads(genres or "[]")
        m = re.search(r"-pg(\d+)$", slug)
        dl = dls.get(m.group(1), {}).get("downloads", 0) if m else 0
        dl = max(dl, twin.get((fold(title), surname(author)), 0))
        o = ol.get(slug) or {}
        readers = (o.get("want") or 0) + (o.get("read") or 0) + 5 * (o.get("ratings") or 0)
        rows.append({"slug": slug, "title": title, "author": author, "shelf": shelves[0] if shelves else "",
                     "shelves": shelves, "downloads": dl, "readers": readers, "editions": o.get("edition_count") or 0})
    mx = {k: math.log1p(max(r[k] for r in rows)) or 1 for k in ("downloads", "readers", "editions")}
    for r in rows:
        r["score"] = round(0.55 * math.log1p(r["downloads"]) / mx["downloads"] + 0.35 * math.log1p(r["readers"]) / mx["readers"]
                           + 0.10 * math.log1p(r["editions"]) / mx["editions"], 5)
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    rc = rdb()
    for r in rows:
        rc.execute("""insert into titles(slug, title, author, shelf, rank, score, updated_at) values(?,?,?,?,?,?,?)
                      on conflict(slug) do update set rank=excluded.rank, score=excluded.score, title=excluded.title,
                      author=excluded.author, shelf=excluded.shelf, updated_at=excluded.updated_at""",
                   (r["slug"], r["title"], r["author"], r["shelf"], r["rank"], r["score"], now()))
    rc.commit()
    with open(POP / "ranking.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank", "score", "slug", "title", "author", "shelf", "downloads", "readers", "editions"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    view = [r for r in rows if not shelf or shelf in r["shelves"]]
    print(f"ranked {len(rows):,} books; showing {'shelf ' + shelf if shelf else 'library'} top {top}")
    for r in view[:top]:
        print(f"{r['rank']:>6}  {r['score']:.3f}  dl {r['downloads']:>6}  rd {r['readers']:>6}  {r['title'][:46]:46} {r['author'][:22]}")


if __name__ == "__main__":
    main()
