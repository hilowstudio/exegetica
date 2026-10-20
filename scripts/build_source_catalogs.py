"""Catalogs of more public-domain sources, in the shape build_nonrenewal_eligibility.py reads.

Writes .seed_cache/pd_sources/<source>_catalog.json, one row per work:
  {id, t (title), a (author, "Given Surname"), y (year or null), died (null), lib, pg, cleared, note}

  standardebooks  GitHub org repo list (.seed_cache/pd_sources/se_repos.tsv); SE clears every book
                  under US law, so cleared=True.
  wikisource      English Wikisource "Validated texts" + "Proofread texts" top-level works
                  (ws_book.json from the 2026-10-05 spike); author and year from each page's
                  {{header}}. Wikisource hosts only works PD in the US, so cleared=True.
  exclassics      exclassics.com title index (exc_titles.htm). Irish site, own transcriptions,
                  dedicated to the public domain; every text predates 1900, so cleared=True.
  runeberg        runeberg.org/katalog.html, English-flagged books only. Swedish site (life+70),
                  so checked.

lib = already in books.db; pg = on gutenberg.org (pg_catalog.csv). Matched on main title + author
surname, the same way build_pulp_eligibility.py matches holdings.

    python scripts/build_source_catalogs.py
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_nonrenewal_eligibility import fold, main_title  # noqa: E402

SRC = ROOT / ".seed_cache" / "pd_sources"
UA = {"User-Agent": "ExegeticaLibrary/1.0 (https://exegetica.fly.dev; public-domain catalog)"}
csv.field_size_limit(10**8)


def surname_of(author: str) -> str:
    a = re.sub(r"\(.*?\)|\[.*?\]", "", author or "")
    a = a.split(",")[0] if "," in a and len(a.split(",")[0].split()) == 1 else a
    w = fold(a).split()
    return w[-1] if w else ""


class Holdings:
    """(main title, surname) index over books.db and pg_catalog.csv."""

    def __init__(self):
        self.lib, self.pg = set(), set()
        con = sqlite3.connect(f"file:{ROOT / 'db' / 'books.db'}?mode=ro", uri=True)
        for t, a in con.execute("select title, author from books"):
            self.lib.add((main_title(t), surname_of(a)))
        with open(ROOT / ".seed_cache" / "pg_catalog.csv", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("Type") != "Text":
                    continue
                first = (r.get("Authors") or "").split(";")[0]
                first = re.sub(r",\s*\d.*$", "", first)          # "Surname, Given, 1850-1920"
                self.pg.add((main_title(r.get("Title") or ""), surname_of(first.split(",")[0])))

    def flags(self, title: str, author: str) -> tuple[bool, bool]:
        k = (main_title(title), surname_of(author))
        return k in self.lib, k in self.pg


def standardebooks(h: Holdings) -> list[dict]:
    con = sqlite3.connect(f"file:{ROOT / 'db' / 'books.db'}?mode=ro", uri=True)
    have = {s for (s,) in con.execute("select slug from books where source='standardebooks'")}
    rows = []
    for line in (SRC / "se_repos.tsv").read_text(encoding="utf-8").splitlines():
        name = line.split("\t")[0]
        if "_" not in name:
            continue                                            # tooling repos
        author, title = name.split("_")[0], name.split("_")[1]
        rows.append(dict(id=name, t=title.replace("-", " ").title(), a=author.replace("-", " ").title(),
                         y=None, died=None, lib=name in have, pg=False, cleared=True, note="SE-cleared"))
    return rows


def _header(text: str, field: str) -> str:
    """A {{header}} parameter's value, with wiki links reduced to their text."""
    m = re.search(rf"\|\s*{field}\s*=\s*(.*?)(?=\n\s*\||\n\s*}}}}|\|\s*[a-z_]+\s*=|}}}}|$)", text, flags=re.S)
    v = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", m.group(1) if m else "")
    return re.sub(r"^(?:Author|Portal):", "", v.strip())


def wikisource(h: Holdings) -> list[dict]:
    titles = json.loads((SRC / "ws_book.json").read_text(encoding="utf-8"))
    cache_f = SRC / "wikisource_headers.json"
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    todo = [t for t in titles if t not in cache]
    with httpx.Client(headers=UA, timeout=60) as c:
        for i in range(0, len(todo), 50):
            batch = todo[i:i + 50]
            r = c.get("https://en.wikisource.org/w/api.php", params=dict(
                action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(batch),
                format="json", formatversion=2, redirects=1)).json()
            for p in r.get("query", {}).get("pages", []):
                text = ((p.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content")) or ""
                cache[p["title"]] = {"author": _header(text, "author") or _header(text, "contributor"),
                                     "year": _header(text, "year"), "override": _header(text, "override_author")}
            for t in batch:
                cache.setdefault(t, {})
            cache_f.write_text(json.dumps(cache), encoding="utf-8")
            print(f"  wikisource headers {min(i + 50, len(todo))}/{len(todo)}")
            time.sleep(1)
    lens = json.loads((SRC / "ws_len.json").read_text(encoding="utf-8")) if (SRC / "ws_len.json").exists() else {}
    rows = []
    for t in titles:
        hd = cache.get(t) or {}
        author = hd.get("author") or hd.get("override") or ""
        y = re.match(r"\d{4}", hd.get("year") or "")
        lib, pg = h.flags(t, author)
        rows.append(dict(id=t, t=t, a=author, y=int(y.group()) if y else None, died=None, lib=lib, pg=pg,
                         cleared=True, note=f"WS-cleared; page bytes {lens.get(t, '')}"))
    return rows


NAV = re.compile(r"^(Author Index|Subject Index|Latest Additions|In preparation|Ex-classics at Other)", re.I)


def exclassics(h: Holdings) -> list[dict]:
    """Every ExClassics text is a pre-1900 work (Civil War pamphlets, 18th-c. memoirs, Foxe, Gerard),
    so the whole catalog is pre-1931; Wikidata lacks most of these authors, so no per-author check."""
    s = (SRC / "exc_titles.htm").read_text(encoding="utf-8", errors="replace")
    rows, seen = [], set()
    for href, inner in re.findall(r'<a[^>]+href="([^"#][^"]*)"[^>]*>(.*?)</a>', s, flags=re.S):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>|&nbsp;", " ", inner)).strip()
        if not text or href in seen or href.startswith("http") or NAV.match(text):
            continue
        seen.add(href)
        m = re.match(r"(.*?),?\s+[Bb]y\s+(.*)$", text)
        title, author = (m.group(1), m.group(2)) if m else (text, "")
        author = re.sub(r'^"[^"]*"\s*\((.*)\)$', r"\1", author)  # 'By "Democritus Junior" (Robert Burton)'
        lib, pg = h.flags(title, author)
        rows.append(dict(id=href, t=title.strip(), a=author.strip(), y=None, died=None, lib=lib, pg=pg,
                         cleared=True, note="historic text (site scope 1500s-1900)"))
    return rows


def runeberg(h: Holdings) -> list[dict]:
    s = (SRC / "runeberg_katalog.html").read_text(encoding="latin-1")
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S):
        if 'flags/us.gif' not in tr or 'alt="Book"' not in tr:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        link = re.search(r'<a href="(/[^"]+/)">(.*?)</a>', tr, flags=re.S)
        if not link:
            continue
        auth = re.search(r'<a href="/authors/[^"]+">(.*?)</a>', tr, flags=re.S)
        year = next((c.strip() for c in cells if re.fullmatch(r"\s*\d{4}\s*", c)), None)
        a = re.sub(r"<[^>]+>", "", auth.group(1)).strip() if auth else ""
        if "," in a:
            sur, _, given = a.partition(",")
            a = f"{given.strip()} {sur.strip()}"
        title = re.sub(r"<[^>]+>", "", link.group(2)).strip()
        lib, pg = h.flags(title, a)
        rows.append(dict(id=link.group(1).strip("/"), t=title, a=a, y=int(year) if year else None, died=None,
                         lib=lib, pg=pg, cleared=False, note=""))
    return rows


def main():
    h = Holdings()
    for name, fn in (("standardebooks", standardebooks), ("exclassics", exclassics),
                     ("runeberg", runeberg), ("wikisource", wikisource)):
        rows = fn(h)
        (SRC / f"{name}_catalog.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        new = [r for r in rows if not r["lib"] and not r["pg"]]
        print(f"{name}: {len(rows):,} works, {len(new):,} not in library or on PG")


if __name__ == "__main__":
    main()
