#!/usr/bin/env python3
"""
Which pulp-magazine stories can the Reading Room publish (US)?

For every item in every issue of each magazine in MAGS (Weird Tales, Fantastic Adventures, and
the science-fiction magazines our Gutenberg stories came from), within the years in scope, this
joins three sources and writes docs/reading-room/pulp-eligible-stories.csv:

  Contents   The FictionMags / Science Fiction Index contents lists (philsp.com): each issue's
             page, title, author, and item type. One page fetched at a time, a second apart,
             cached under .seed_cache/pulp/.
  Renewals   The Online Books Page's copyright pages for each magazine (compiled from the
             Copyright Office's Catalog of Copyright Entries): which issues had their copyright
             renewed, and which individual stories were renewed by their authors.
  Holdings   Project Gutenberg's catalog (pg_catalog.csv) and our own books.db, matched on
             title + author surname, so stories already transcribed can come in first.

Status rules (US law; research, not legal advice):
  published before 1931                 -> public domain
  issue not renewed and story not renewed -> public domain (renewal was required for 1931-63)
  renewed (issue or story), published N  -> protected through December 31 of N+95; a 1931
                                           item therefore becomes public domain 2027-01-01
  issue on or after a magazine's first renewed issue, where the Online Books Page doesn't list
  every renewal (renewals filed 1978+ "see CPRS", or no list at all)
                                        -> "unverified" (not counted as public domain)
  any story Project Gutenberg has published  -> public domain (Gutenberg clears each story's US
                                           status before publishing; this outranks the above)

Run:
    python scripts/build_pulp_eligibility.py            # uses cached pages
    python scripts/build_pulp_eligibility.py --refresh  # re-fetch contents and renewals
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import re
import sqlite3
import sys
import time
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".seed_cache" / "pulp"
OUT = ROOT / "docs" / "reading-room" / "pulp-eligible-stories.csv"
UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (public-domain story index; hello@hilowstudio.dev)"}
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# One entry per magazine (a renamed run is one magazine: Astounding became Analog in 1960).
#   magid   FictionMags / Science Fiction Index id; the contents walk starts there
#   title   regex for the printed titles to accept on those pages
#   obp     Online Books Page copyright pages (renewed issues + renewed stories); several when the
#           magazine changed names
#   years   in scope. Stops at 1963: from 1964 renewal was automatic, so everything later is
#           still under copyright.
#   stem    book slug stem for its issue collections; section = its Reading Room shelf;
#   gc      Galactic Central checklist anchor(s) for issue covers (build_magazine_covers._gc_series)
SF = "Science Fiction"
MAGS = {
    "Weird Tales": dict(magid="WRT", title=r"^Weird Tales$", obp=["weirdtales"], years=(1923, 1954),
                        stem="weird-tales", section="Horror & Gothic", gc="data616.html#WEIRDTALES1"),
    "Fantastic Adventures": dict(magid="FAD", title=r"^Fantastic Adventures$", obp=["fantasticadventures"],
                                 years=(1939, 1953), stem="fantastic-adventures", section=SF,
                                 gc="data197.html#FANTASTICADVENTURES"),
    "Galaxy": dict(magid="GAL", title=r"^Galaxy", obp=["galaxysf"], years=(1950, 1963), stem="galaxy",
                   section=SF, gc="data231.html#GALAXYSCIENCEFICTION"),
    "Astounding": dict(magid="ASF", title=r"^(Astounding|Analog)", obp=["astounding", "analogsf"],
                       years=(1930, 1963), stem="astounding", section=SF, gc="data028.html#ANALOG"),
    "Amazing Stories": dict(magid="AMZ", title=r"^Amazing(?! Stories (Quarterly|Annual))", obp=["amazingstories"],
                            years=(1926, 1963), stem="amazing-stories", section=SF, gc="data021.html#AMAZINGSTORIES"),
    "Fantastic Universe": dict(magid="FUN", title=r"^Fantastic Universe", obp=["fantasticuniv"], years=(1953, 1960),
                               stem="fantastic-universe", section=SF, gc="data198.html#FANTASTICUNIVERSE"),
    "If": dict(magid="IFS", title=r"^(If|Worlds of If)\b", obp=["if1952"], years=(1952, 1963), stem="if",
               section=SF, gc="data283.html#IF1952"),
    "Imagination": dict(magid="IMG", title=r"^Imagination", obp=["imaginationsf"], years=(1950, 1958),
                        stem="imagination", section=SF, gc="data285.html#IMAGINATION1950"),
    "Planet Stories": dict(magid="PLS", title=r"^Planet Stories", obp=["planetstories"], years=(1939, 1955),
                           stem="planet-stories", section=SF, gc="data437.html#PLANETSTORIES"),
    "Space Science Fiction": dict(magid="SSF", title=r"^Space Science Fiction", obp=["spacescifi", "spacesf1957"],
                                  years=(1952, 1957), stem="space-science-fiction", section=SF,
                                  gc="data525.html#SPACESCIENCEFICTION"),
    "Other Worlds": dict(magid="OWS", title=r"^Other Worlds", obp=["otherworlds"], years=(1949, 1957),
                         stem="other-worlds", section=SF, gc="data409.html#OTHERWORLDSSCIENCESTORIES"),
    "Universe Science Fiction": dict(magid="USF", title=r"^Universe", obp=["universesf"], years=(1953, 1955),
                                     stem="universe-science-fiction", section=SF,
                                     gc="data409.html#OTHERWORLDSSCIENCESTORIES"),
    "Fantastic": dict(magid="FAN", title=r"^Fantastic(?! (Adventures|Universe|Novels|Stor))", obp=["fantastic1952"],
                      years=(1952, 1963), stem="fantastic", section=SF, gc="data197.html#FANTASTIC1952"),
    "Dynamic Science Fiction": dict(magid="DSF", title=r"^Dynamic Science Fiction", obp=["dynamicscifi"],
                                    years=(1952, 1954), stem="dynamic-science-fiction", section=SF,
                                    gc="data172.html#DYNAMICSCIENCEFICTION"),
    "Venture Science Fiction": dict(magid="VSF", title=r"^Venture", obp=["venturesf"], years=(1957, 1958),
                                    stem="venture-science-fiction", section=SF, gc="data605.html#VENTURESCIENCEFICTION"),
    "Worlds of Tomorrow": dict(magid="WOT", title=r"^Worlds of Tomorrow", obp=["worldsoftomw"], years=(1963, 1963),
                               stem="worlds-of-tomorrow", section=SF, gc="data638.html#WORLDSOFTOMORROW"),
    "Comet": dict(magid="CMT", title=r"^Comet", obp=["comet1940"], years=(1940, 1941), stem="comet", section=SF,
                  gc="data124.html#COMET1940A"),
    "Wonder Stories Quarterly": dict(magid="WSQ", title=r"^(Science )?Wonder", obp=["wonderstoriesq"],
                                     years=(1929, 1933), stem="wonder-stories-quarterly", section=SF,
                                     gc="data495.html#SCIENCEWONDERQUARTERLY"),
}
MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
SEASONS = {"winter": 1, "spring": 4, "summer": 7, "fall": 10, "autumn": 10}
FICTION = {"ss": "short story", "nv": "novelette", "na": "novella", "n.": "novel", "sl": "serial part",
           "vi": "vignette", "pm": "poem", "vi/pm": "poem"}


def fetch(url: str, name: str, refresh: bool, delay: float = 1.0) -> str:
    path = CACHE / name
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        raw = r.read()
    text = raw.decode("utf-8") if b"\xc2\xb7" in raw or b"\xe2\x80" in raw else raw.decode("latin-1")
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    time.sleep(delay)
    return text


def norm(s: str) -> str:
    import unicodedata
    s = html.unescape(s or "")
    s = re.sub(r"['‘’`]", "", s)               # Wizard's / Wizard’s -> wizards
    s = re.sub(r"[‐-―-]", " ", s)              # Truly—Jack -> truly jack
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^(the|a|an)\s+", "", s.strip())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def issue_key(text: str) -> tuple[int, int] | None:
    """'February/March 1931', 'February-March 1931', 'Winter 1945', 'Fall 1952' -> (1931, 2)."""
    t = text.lower()
    y = re.search(r"(19\d\d)", t)
    if not y:
        return None
    for w in re.findall(r"[a-z]+", t):
        if w in MONTHS:
            return int(y.group(1)), MONTHS[w]
        if w in SEASONS:
            return int(y.group(1)), SEASONS[w]
    return int(y.group(1)), 0


def surname(author: str) -> str:
    a = re.sub(r"\[.*?\]|\(.*?\)", "", author or "").split(",")[0].strip()   # drop ", M.D."
    a = a.split(" & ")[0].split(" and ")[0].strip()
    parts = a.split()
    return norm(parts[-1]) if parts else ""


# ---------------------------------------------------------------- contents (FictionMags)
def strip(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def contents(mag: str, magid: str, y0: int, y1: int, refresh: bool, title_re: str | None = None) -> list[dict]:
    """Every item of every issue of `mag` published y0..y1, from the FictionMags contents pages
    starting at `magid`'s first page. `title_re` matches the printed titles (default: exactly mag)."""
    accept = re.compile(title_re) if title_re else re.compile(r"^" + re.escape(mag) + r"$")
    first = fetch(f"http://www.philsp.com/homeville/SFI/link.asp?magid={magid}", f"sfi_{magid}_start.htm", refresh)
    page = re.search(r'HREF="(k\d+)\.htm#BOT"><B>Previous', first)
    num = int(page.group(1)[1:]) + 1 if page else None
    items, seen_mag, pages = [], False, 0
    while num and pages < 160:
        text = first if pages == 0 else fetch(f"http://www.philsp.com/homeville/SFI/k{num:05d}.htm", f"sfi_k{num:05d}.htm", refresh)
        pages += 1
        blocks = re.split(r"<table border=\"0\" width=\"100%\"><tr><td valign=\"top\">", text)
        hit = False
        for b in blocks:
            head = re.search(r"<I>([^<]+)</I>(?:</A>)?\s*\[([^\]]+)\]", b)   # title is often linked
            if not head or not accept.search(strip(head.group(1))):
                continue
            key = issue_key(head.group(2).split(",")[-1])
            if not key or not (y0 <= key[0] <= y1):
                hit = hit or bool(key and key[0] < y0)
                continue
            hit = seen_mag = True
            label = strip(head.group(2).split(",")[-1])
            for li in re.findall(r"<LI>(.*?)</LI>", b, re.S):
                parts = [p.strip() for p in strip(li).split("·")]
                if len(parts) < 4 or not parts[0][:1].isdigit():
                    continue
                # the type field can carry credits: "ss; illustrated by C. C. Senf"
                pg, title, author, kind = parts[0], parts[1], parts[2], re.split(r"[;,\s]", parts[3])[0]
                items.append({"magazine": mag, "issue_title": strip(head.group(1)), "issue": label,
                              "year": key[0], "month": key[1],
                              "page": pg, "title": title, "author": author, "type": kind,
                              "note": " · ".join(parts[4:])})
        if seen_mag and not hit:
            break                                            # ran past this magazine's run
        nxt = re.search(r'HREF="(k\d+)\.htm#TOP"><B>Next', text)
        num = int(nxt.group(1)[1:]) if nxt else None
    print(f"  {mag}: {len(items)} items from {pages} contents pages")
    return items


# ---------------------------------------------------------------- renewals (Online Books Page)
def renewals(obp_ids: list[str] | str, refresh: bool) -> tuple[set, list, tuple | None]:
    """(renewed issues, renewed stories, unverified_from): the last is the first renewed issue's
    date when the page's issue list may be incomplete (renewals in the Copyright Office's
    post-1977 records, "see CPRS", or no list given), else None."""
    if isinstance(obp_ids, list):
        issues, contribs, froms = set(), [], []
        for oid in obp_ids:
            i, c, f = renewals(oid, refresh)
            issues |= i
            contribs += c
            if f:
                froms.append(f)
        return issues, contribs, (min(froms) if froms else None)
    obp_id = obp_ids
    t = fetch(f"https://onlinebooks.library.upenn.edu/webbin/cinfo/{obp_id}", f"obp_{obp_id}.html", refresh)
    t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())
    ri, rc = t.find("Renewed issues"), t.find("Renewed contributions")
    end = t.find("still have inadvertent")
    issues = set()
    if ri >= 0:
        seg = t[ri:rc if rc > ri else end]
        for d in re.findall(r"((?:[A-Z][a-z]+(?:\s*-\s*[A-Z][a-z]+)?|Spring|Summer|Fall|Winter)\s+\d{4})\s+\((?:v\.|no\.)", seg):
            k = issue_key(d)
            if k:
                issues.add(k)
    contribs = []
    if rc >= 0:
        seg = t[rc:end]
        for d, title, author in re.findall(
                r"((?:[A-Z][a-z]+(?:\s*-\s*[A-Z][a-z]+)?|Spring|Summer|Fall|Winter)\s+\d{4})\s+\((?:v\.|no\.)[^)]*\):\s+\"([^\"]+)\",\s+by\s+"
                r"(.+?)(?=\s+\[|\s+\(|\s+(?:[A-Z][a-z]+(?:\s*-\s*[A-Z][a-z]+)?|Spring|Summer|Fall|Winter)\s+\d{4}\s+\((?:v\.|no\.)|$)", seg):
            contribs.append({"key": issue_key(d), "title": norm(title), "surname": surname(author)})
    first = re.search(r"First renewed issue: ((?:[A-Z][a-z]+(?:\s*-\s*[A-Z][a-z]+)?|Spring|Summer|Fall|Winter)\s+\d{4})[^;]*;\s*see ([^ ]+)", t)
    unverified_from = None
    if first and (not issues or first.group(2).startswith("CPRS")):
        unverified_from = issue_key(first.group(1))
    return issues, contribs, unverified_from


# ---------------------------------------------------------------- holdings (Gutenberg + ours)
def gutenberg(refresh: bool) -> dict[str, list[tuple[str, str]]]:
    text = fetch("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv", "pg_catalog.csv", refresh, delay=0)
    idx: dict[str, list[tuple[str, str]]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("Type") != "Text":
            continue
        t = norm(re.split(r"[:;]|\n", r.get("Title") or "")[0])
        idx.setdefault(t, []).append((r["Text#"], norm(r.get("Authors") or "")))
    return idx


def ours() -> dict[str, list[str]]:
    con = sqlite3.connect(f"file:{ROOT / 'db' / 'books.db'}?mode=ro", uri=True)
    idx: dict[str, list[str]] = {}
    for t, a in con.execute("select title, author from books"):
        idx.setdefault(norm(re.split(r"[:;]", t or "")[0]), []).append(norm(a or ""))
    return idx


def holder(index: dict, title: str, sname: str):
    for entry in index.get(norm(title), []):
        ident, authors = entry if isinstance(entry, tuple) else (True, entry)
        if sname and sname in authors:
            return ident
    return None


def _same_story(t: str, sn: str, year: int, c: dict, month: int = 0) -> bool:
    """A renewal record names this story: same author, within a year of the issue, and the
    same title allowing for the two sources' spelling slips (Bogy/Bogey, Flirgleflip).
    In the same issue the author may differ: the magazine printed a pen name (Tarleton
    Fiske, Michael West) and the renewal was filed under the real one (Bloch, Derleth)."""
    import difflib
    same_issue = bool(c["key"]) and c["key"] == (year, month)
    if c["surname"] and sn and c["surname"] != sn and not same_issue:
        return False
    if c["key"] and abs(c["key"][0] - year) > 1:
        return False
    ct = c["title"]
    return ct == t or (len(t) > 8 and (t in ct or ct in t)) or difflib.SequenceMatcher(None, t, ct).ratio() >= 0.85


# ---------------------------------------------------------------- main
def status(year: int, renewed: bool) -> tuple[str, str]:
    if year < 1931:
        return "public domain", "now"
    if not renewed:
        return "public domain (not renewed)", "now"
    opens = date(year + 96, 1, 1)
    return ("public domain from " + opens.isoformat(), opens.isoformat()) if opens.year == 2027 else \
           ("protected (renewed)", opens.isoformat())


def main() -> None:
    ap = argparse.ArgumentParser(description="Public-domain status of pulp-magazine stories")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--only", help="comma-separated magazine names to rebuild (others keep their rows)")
    args = ap.parse_args()
    only = {m.strip() for m in args.only.split(",")} if args.only else None
    print("[contents]")
    rows = []
    pg, mine = gutenberg(args.refresh), ours()
    for mag, cfg in MAGS.items():
        if only and mag not in only:
            continue
        y0, y1 = cfg["years"]
        items = contents(mag, cfg["magid"], y0, y1, args.refresh, cfg["title"])
        r_issues, r_contribs, unverified_from = renewals(cfg["obp"], args.refresh)
        print(f"  {mag}: {len(r_issues)} renewed issues, {len(r_contribs)} renewed stories on record"
              + (f"; issues from {unverified_from[0]}-{unverified_from[1]:02d} unverified" if unverified_from else ""))
        for it in items:
            if it["type"] not in FICTION:
                continue                                          # skip articles, letters, editorials
            key, t, sn = (it["year"], it["month"]), norm(it["title"]), surname(it["author"])
            issue_ren = key in r_issues
            story_ren = any(_same_story(t, sn, it["year"], c, it["month"]) for c in r_contribs)
            st, when = status(it["year"], issue_ren or story_ren)
            gid = holder(pg, re.sub(r"\s*\[.*?\]", "", it["title"]), sn)
            if when == "now" and it["year"] >= 1931 and unverified_from and key >= unverified_from:
                st, when = ("renewal status unverified", "unverified")
            if gid and when != "now":
                # Gutenberg clears each story's US status before publishing it (and our library
                # already serves these as standalone books); its clearance outranks our
                # issue-level reading. The renewal flags stay in the CSV for audit.
                st, when = ("public domain (cleared by Project Gutenberg)", "now")
            rows.append({**{k: it[k] for k in ("magazine", "issue_title", "issue", "year", "page", "title", "author")},
                         "type": FICTION[it["type"]], "status": st, "public_domain_from": when,
                         "issue_renewed": "yes" if issue_ren else "", "story_renewed": "yes" if story_ren else "",
                         "gutenberg": f"https://www.gutenberg.org/ebooks/{gid}" if gid else "",
                         "in_reading_room": "yes" if holder(mine, re.sub(r"\s*\[.*?\]", "", it["title"]), sn) else "",
                         "note": it["note"]})
    if only and OUT.exists():           # keep the other magazines' rows as they were
        rows += [r for r in csv.DictReader(open(OUT, encoding="utf-8")) if r["magazine"] not in only]
    rows = [{**r, "issue_title": r.get("issue_title") or r["magazine"]} for r in rows]
    rows.sort(key=lambda r: (r["magazine"], int(r["year"]), r["issue"], r["page"].zfill(4)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["magazine", "issue_title", "issue", "year", "page", "title", "author", "type",
                                          "status", "public_domain_from", "issue_renewed", "story_renewed",
                                          "gutenberg", "in_reading_room", "note"])
        w.writeheader()
        w.writerows(rows)

    print(f"\n{len(rows)} fiction items -> {OUT.relative_to(ROOT)}")
    for mag in MAGS:
        mr = [r for r in rows if r["magazine"] == mag]
        if not mr:
            continue
        c = Counter("now" if r["public_domain_from"] == "now" else "unverified" if r["public_domain_from"] == "unverified" else
                    "2027" if r["public_domain_from"].startswith("2027") else "later" for r in mr)
        print(f"  {mag}: {len(mr)} stories | public domain now {c['now']} | unverified {c['unverified']} | from 2027-01-01 {c['2027']} | "
              f"protected longer {c['later']} | on Gutenberg {sum(1 for r in mr if r['gutenberg'])} | "
              f"already in Reading Room {sum(1 for r in mr if r['in_reading_room'])}")


if __name__ == "__main__":
    main()
