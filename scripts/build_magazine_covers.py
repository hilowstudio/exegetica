#!/usr/bin/env python3
"""
Build the magazine-issue cover index for the Reading Room's admin cover tool.

Most of our science fiction is Project Gutenberg stories whose transcriber note names the
magazine issue they came from ("This etext was produced from Galaxy Science Fiction July
1958"). That issue's own cover is the right art for the story, and since the issue is in the
public domain for the same reason the story is (the copyright wasn't renewed), the cover
almost always is too. This script finds those notes, matches each to a scan of the issue's
cover, and writes webapp/data/magazine_covers.json, which the admin cover search shows above
the Google results and the bulk review page offers for one-click approval.

Sources, best first:
  Internet Archive  full-resolution scans (pulp magazine collections), via the scrape API.
                    If archive.org won't answer directly, it retries through the Firecrawl
                    CLI; if it's down altogether, earlier cached results are kept and the
                    rest of the index still builds. Re-run when it's back to fill IA in.
  Galactic Central  philsp.com checklist pages: 400-550px covers. No robots.txt; we fetch
                    one checklist page per magazine, a second apart, and cache it.
ISFDB is not used: its robots.txt sets Crawl-delay 1000 (one request per ~17 minutes).

Run:
    python scripts/build_magazine_covers.py            # build (uses caches where present)
    python scripts/build_magazine_covers.py --refresh  # re-fetch IA + Galactic Central
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS_DB = ROOT / "db" / "books.db"
CACHE = ROOT / ".seed_cache" / "magcovers"
OUT = ROOT / "webapp" / "data" / "magazine_covers.json"
UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (magazine cover index; hello@hilowstudio.dev)"}
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
SEASONS = {"winter": "win", "spring": "spr", "summer": "sum", "fall": "fal", "autumn": "fal"}

# Our magazine keys: how notes name them (first match wins, checked against the normalized
# name), the display name, the Galactic Central data-page anchor, and the Internet Archive
# query plus the title words an IA item must contain.
MAGS = [
    # key            note-name pattern                              display name                     GC data page#anchor                       IA query                                                        IA title words
    ("galaxy",       r"^galaxy",                                    "Galaxy Science Fiction",       "data231.html#GALAXYSCIENCEFICTION",        "collection:galaxymagazine",                                   "galaxy"),
    ("analog",       r"^analog",                                    "Analog Science Fact & Fiction","data028.html#ANALOG",                      "collection:pulpmagazinearchive AND title:(analog)",           "analog"),
    ("astounding",   r"^astounding",                                "Astounding",                   "data028.html#ANALOG",                      "collection:astoundingstories",                                "astounding"),
    ("amazing",      r"^amazing",                                   "Amazing Stories",              "data021.html#AMAZINGSTORIES",              "collection:amazingstoriesmagazine",                           "amazing"),
    ("fantastic_universe", r"^fantastic universe",                 "Fantastic Universe",           "data198.html#FANTASTICUNIVERSE",           "collection:pulpmagazinearchive AND title:(fantastic universe)", "fantastic universe"),
    ("if",           r"^(if\b|worlds of if)",                       "If: Worlds of Science Fiction","data283.html#IF1952",                      "collection:ifmagazine",                                       "if"),
    ("imagination",  r"^imagination",                               "Imagination",                  "data285.html#IMAGINATION1950",             "collection:pulpmagazinearchive AND title:(imagination)",      "imagination"),
    ("planet",       r"^planet stories",                            "Planet Stories",               "data437.html#PLANETSTORIES",               "collection:planetstories",                                    "planet stories"),
    ("space_sf",     r"^space science fiction",                     "Space Science Fiction",        "data525.html#SPACESCIENCEFICTION",         "collection:pulpmagazinearchive AND title:(space science fiction)", "space science fiction"),
    ("weird_tales",  r"^weird tales",                               "Weird Tales",                  "data616.html#WEIRDTALES1",                 "collection:pulpmagazinearchive AND title:(weird tales)",      "weird tales"),
    ("other_worlds", r"^other worlds",                              "Other Worlds",                 "data409.html#OTHERWORLDSSCIENCESTORIES",   "collection:pulpmagazinearchive AND title:(other worlds)",     "other worlds"),
    ("fantastic",    r"^fantastic stories",                         "Fantastic Stories of Imagination", "data197.html#FANTASTIC1952",           "collection:pulpmagazinearchive AND title:(fantastic)",        "fantastic"),
    ("future",       r"^(future|science fiction stories$)",          "Future Science Fiction",       "data229.html#FUTURESCIENCEFICTION",        "collection:pulpmagazinearchive AND title:(future)",           "future"),
    ("dynamic",      r"^dynamic science",                           "Dynamic Science Fiction",      "data172.html#DYNAMICSCIENCEFICTION",       "collection:pulpmagazinearchive AND title:(dynamic)",          "dynamic"),
    ("sf_adventures",r"^science fiction adventures",                "Science Fiction Adventures",   "data493.html#SCIENCEFICTIONADVENTURES1952|data493.html#SCIENCEFICTIONADVENTURES1956","collection:pulpmagazinearchive AND title:(science fiction adventures)", "adventures"),
    ("wonder_q",     r"^wonder stories quarterly",                  "Wonder Stories Quarterly",     "data495.html#SCIENCEWONDERQUARTERLY",      "collection:pulpmagazinearchive AND title:(wonder stories quarterly)", "wonder"),
    ("venture",      r"^venture",                                   "Venture Science Fiction",      "data605.html#VENTURESCIENCEFICTION",       "collection:pulpmagazinearchive AND title:(venture)",          "venture"),
    ("worlds_tomorrow", r"^worlds of tomorrow",                     "Worlds of Tomorrow",           "data638.html#WORLDSOFTOMORROW",            "collection:pulpmagazinearchive AND title:(worlds of tomorrow)", "tomorrow"),
    ("universe",     r"^universe science",                          "Universe Science Fiction",     "data409.html#OTHERWORLDSSCIENCESTORIES",   "collection:pulpmagazinearchive AND title:(universe)",         "universe"),
    ("comet",        r"^comet",                                     "Comet",                        "data124.html#COMET1940A",                  "collection:pulpmagazinearchive AND title:(comet)",            "comet"),
]
_FOREIGN = re.compile(r"(^|[_\W])(uk|british|brit|aus|australia|australian|can|canada|canadian|ger|german|ital|fr|french|swe|nl)([_\W]|$)", re.I)


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", html.unescape(s or "").lower().replace("&", " and ")).split())


# ------------------------------------------------------------------ 1. notes in our books
NOTE = re.compile(
    r"(?:etext|e-text|ebook|e-book|text)\s+was\s+produced\s+from\s+(.{3,90}?)[\s,]+"
    r"((?:(?:" + "|".join(list(MONTHS) + list(SEASONS)) + r")\.?[\s,/-]*(?:and\s+)?)+)?(\d{4})", re.I)


def book_issues() -> dict[str, dict]:
    """slug -> {mag, year, month|season, note} for every book whose transcriber note names an issue."""
    con = sqlite3.connect(f"file:{BOOKS_DB}?mode=ro", uri=True)
    out, unmatched = {}, Counter()
    for bid, slug in con.execute("select id, slug from books"):
        h = " ".join(r[0] or "" for r in con.execute(
            "select html from book_chapters where book_id=? order by section_number limit 4", (bid,)))
        if "produced from" not in h:
            continue
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
        m = NOTE.search(text)
        if not m or not m.group(2):
            continue                                   # no month or season: can't pin an issue
        name = norm(re.sub(r"^(the\s+)", "", m.group(1).strip(" \"'“”‘’_,"), flags=re.I))
        key = next((k for k, pat, *_ in MAGS if re.search(pat, name)), None)
        if not key:
            unmatched[name[:40]] += 1
            continue
        when = norm(m.group(2)).split()[0]
        rec = {"mag": key, "year": int(m.group(3)), "note": m.group(0).strip()[:160]}
        if when in MONTHS:
            rec["month"] = MONTHS[when]
        else:
            rec["season"] = SEASONS[when]
        out[slug] = rec
    con.close()
    print(f"[notes] {len(out)} books name a specific issue; unmatched magazine names: "
          f"{sum(unmatched.values())} ({', '.join(k for k, _ in unmatched.most_common(6))})")
    return out


# ------------------------------------------------------------------ fetching
def fetch(url: str, cache_name: str, refresh: bool, delay: float = 1.0, firecrawl: bool = False,
          offline: bool = False) -> str | None:
    path = CACHE / cache_name
    if offline or (path.exists() and not refresh):
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else None
    body = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            body = r.read().decode("utf-8", errors="replace")
        time.sleep(delay)
    except Exception as e:  # noqa: BLE001
        print(f"  direct fetch failed ({type(e).__name__}): {url[:90]}")
    if body is None and firecrawl:
        body = _firecrawl(url)
    if body is None or "Temporarily Offline" in body[:2000]:
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else None
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return body


def _firecrawl(url: str, tries: int = 3) -> str | None:
    """Fallback for archive.org when it refuses our connection: fetch through the Firecrawl CLI."""
    for i in range(tries):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "page.json"
            r = subprocess.run(["firecrawl", "scrape", url, "--format", "rawHtml", "-o", str(out)],
                               capture_output=True, text=True, timeout=180, shell=sys.platform == "win32")
            if r.returncode == 0 and out.exists():
                raw = out.read_text(encoding="utf-8", errors="replace")
                try:
                    raw = json.loads(raw).get("rawHtml", raw)
                except ValueError:
                    pass
                # JSON responses come back wrapped in an HTML <pre>; unwrap to the payload
                inner = re.search(r"<pre[^>]*>(.*)</pre>", raw, re.S)
                return html.unescape(inner.group(1)) if inner else raw
        print(f"  firecrawl try {i + 1} failed: {url[:90]}")
        time.sleep(5)
    return None


# ------------------------------------------------------------------ 2. Galactic Central
def gc_index(refresh: bool) -> dict[str, dict[str, tuple[str, str]]]:
    """mag key -> {"YYYYMM" or "YYYYsea": (image URL, checklist page URL)}."""
    idx: dict[str, dict[str, tuple[str, str]]] = {}
    for key, _pat, _name, data_refs, *_ in MAGS:
        for data_ref in data_refs.split("|"):          # a magazine can span several series
            m = _gc_series(data_ref, refresh, key)
            for ym, url in m.items():
                idx.setdefault(key, {}).setdefault(ym, url)
    return idx


def _gc_series(data_ref: str, refresh: bool, key: str) -> dict[str, tuple[str, str]]:
    page, anchor = data_ref.split("#")
    data = fetch(f"http://www.philsp.com/data/{page}", f"gc_{page}", refresh)
    if not data:
        return {}
    seg = data[data.find(f'"{anchor}"'):] if f'"{anchor}"' in data else ""
    seg = seg[:seg.find('name="', 20) if seg.find('name="', 20) > 0 else 20000]
    link = re.search(r'href="\.\./mags/([a-z0-9_]+\.html)(#[a-z0-9_]+)?"', seg)
    if not link:
        print(f"  [gc] {key}: no checklist link under #{anchor}")
        return {}
    check = fetch(f"http://www.philsp.com/mags/{link.group(1)}", f"gcmags_{link.group(1)}", refresh)
    if not check:
        return {}
    if link.group(2):                                  # a page shared by several titles: our section only
        frag = link.group(2)[1:]
        start = check.find(f'name="{frag}"')
        if start < 0:
            start = check.find(f'name = "{frag}"')
        if start >= 0:
            nxt = re.search(r'<a\s+name\s*=', check[start + 10:], re.I)
            check = check[start:start + 10 + nxt.start()] if nxt else check[start:]
    files = re.findall(r'href="\.\./data/images/([a-z0-9])/([a-z0-9_-]+)\.jpg"', check, re.I)
    prefixes = Counter(re.match(r"(.+?)_(\d{4})", f).group(1) for _l, f in files if re.match(r".+?_\d{4}", f))
    good = {p for p in prefixes if not _FOREIGN.search(p)}
    page_url = f"http://www.philsp.com/mags/{link.group(1)}{link.group(2) or ''}"
    m: dict[str, tuple[str, str]] = {}
    for letter, f in files:
        mm = re.match(r"(.+?)_(\d{4})(\d{2}|win|spr|sum|fal)(?:[_-]|$)", f)   # "-": double issues
        if mm and mm.group(1) in good:
            m.setdefault(mm.group(2) + mm.group(3), (f"http://www.philsp.com/data/images/{letter}/{f}.jpg", page_url))
    print(f"  [gc] {key}: {len(m)} issues from mags/{link.group(1)}{link.group(2) or ''}")
    return m


# ------------------------------------------------------------------ 3. Internet Archive
def ia_index(refresh: bool) -> tuple[dict[str, dict[str, str]], bool]:
    """mag key -> {"YYYYMM": identifier}. Returns (index, reachable)."""
    idx: dict[str, dict[str, str]] = {}
    reachable, down = False, False
    for key, _pat, _name, _gc, query, words in MAGS:
        url = "https://archive.org/services/search/v1/scrape?" + urllib.parse.urlencode(
            {"q": query, "fields": "identifier,title,date", "count": 10000})
        body = fetch(url, f"ia_{key}.json", refresh, delay=2.0, firecrawl=True, offline=down)
        try:
            items = json.loads(body)["items"] if body else []
            reachable = reachable or bool(items)
        except (ValueError, KeyError, TypeError):
            items = []
        if not items and not reachable and not down:
            down = True                                # the first magazine got nothing: IA is down,
            print("  [ia] unreachable; using cached results only")   # don't hammer it for the rest
        best: dict[str, tuple[int, str]] = {}
        for it in items:
            ident, title = it.get("identifier", ""), norm(it.get("title", ""))
            if words not in title and words.replace(" ", "") not in ident.lower().replace("_", ""):
                continue
            if _FOREIGN.search(ident) or _FOREIGN.search(title) or re.search(r"modified|missing|reprint", ident, re.I):
                continue
            ym = None
            d = it.get("date") or ""
            if re.match(r"\d{4}-\d{2}", d):
                ym = d[:4] + d[5:7]
            else:
                g = re.search(r"(19\d{2})[-_ ](\d{2})(?!\d)", ident) or re.search(r"(19\d{2})[-_ ](\d{2})(?!\d)", it.get("title", ""))
                ym = g.group(1) + g.group(2) if g else None
            if not ym:
                continue
            rank = 0 if it.get("date") else 1           # prefer items with a real date field
            if ym not in best or rank < best[ym][0]:
                best[ym] = (rank, ident)
        idx[key] = {ym: ident for ym, (_r, ident) in best.items()}
        print(f"  [ia] {key}: {len(idx[key])} issues" + ("" if items else " (unavailable)"))
    return idx, reachable


# ------------------------------------------------------------------ 4. join + write
def month_label(rec: dict) -> str:
    if "month" in rec:
        return time.strftime("%B", time.strptime(str(rec["month"]), "%m")) + f" {rec['year']}"
    return {"win": "Winter", "spr": "Spring", "sum": "Summer", "fal": "Fall"}[rec["season"]] + f" {rec['year']}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--refresh", action="store_true", help="re-fetch IA and Galactic Central pages")
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    issues = book_issues()
    print("[galactic central]")
    gc = gc_index(args.refresh)
    print("[internet archive]")
    ia, ia_ok = ia_index(args.refresh)

    names = {k: n for k, _p, n, *_ in MAGS}
    out, stats = {}, Counter()
    for slug, rec in sorted(issues.items()):
        ym = f"{rec['year']}{rec['month']:02d}" if "month" in rec else f"{rec['year']}{rec['season']}"
        label = f"{names[rec['mag']]}, {month_label(rec)}"
        cands = []
        ident = ia.get(rec["mag"], {}).get(ym)
        if ident:
            cands.append({"source": "Internet Archive", "image": f"https://archive.org/download/{ident}/page/n0_s4.jpg",
                          "thumb": f"https://archive.org/services/img/{ident}",
                          "page": f"https://archive.org/details/{ident}"})
        img, gc_page = gc.get(rec["mag"], {}).get(ym) or (None, None)
        if img:   # philsp.com has no https; the server proxies previews (reader.cover_preview)
            cands.append({"source": "Galactic Central", "image": img, "thumb": img, "page": gc_page})
        stats["ia" if ident else "no_ia"] += 1
        stats["gc" if img else "no_gc"] += 1
        stats["any" if cands else "none"] += 1
        out[slug] = {"issue": label, "mag": rec["mag"], "ym": ym, "candidates": cands}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print(f"\n{len(out)} books -> {OUT.relative_to(ROOT)}: a cover for {stats['any']} "
          f"(Internet Archive {stats['ia']}, Galactic Central {stats['gc']}), none yet for {stats['none']}.")
    if not ia_ok:
        print("Internet Archive was unreachable; re-run with --refresh when it's back to add its scans.")


if __name__ == "__main__":
    main()
