"""US public-domain eligibility for book catalogs, through 1963, by copyright non-renewal.

US rule: published before 1931 -> public domain; published 1931-63 -> public domain only if the
copyright was not renewed in its 28th year (renewals were filed 1959-91); from 1964 renewal was
automatic, so later books are protected.

Renewals come from NYPL's transcription of the Copyright Office renewal records, 1950-1991
(github.com/NYPL/cce-renewals, cloned to .seed_cache/cce-renewals). A book counts as renewed
when a renewal's main title matches the book's and the author's surname appears in the renewal.
A title match without the surname is reported as `check` (a common title, a pseudonym, or an
anonymous renewal), never silently passed.

Foreign books (URAA). Non-renewal only frees a US work. The 1996 URAA restored US copyright in
foreign works still protected at home on 1996-01-01, renewal or not. Test: a not-renewed book counts
as a US work when the Copyright Office registered a US edition ("A" number) in its year of first
publication (NYPL's registration transcriptions, .seed_cache/cce-registrations, sparse-checked out
for 1930-63). A book by an American author (Wikidata citizenship) also counts as a US work: pulp stories ran in
US magazines and never got book registrations of their own.
Otherwise it is foreign, and public domain only if it was already PD at home in 1996:
author died 1925 or earlier (safe in any life+70 country, e.g. Britain); died 1926-45 and a citizen
of a life+50 country in 1996 (Canada, Australia, New Zealand, South Africa) -> PD; died 1926-45 with
no such citizenship known -> `foreign-check-nationality`; died after 1945 -> `foreign-restored` (not
PD); no death year -> `foreign-needs-dates` (Fadedpage's book header gives the author's dates).
Author facts come from Wikidata (search by name, first human hit), cached in
.seed_cache/pd_sources/authors_wikidata.json.

Catalogs (cached under .seed_cache/pd_sources, from the 2026-10-05 sources spike):
  fp_rows.json   Fadedpage allbooks.php      {pid, a "Surname, Given", t, y, lib, pg}
  pga_rows.json  PG Australia index + pages  {i, a "Given Surname", t, y, d [born, died], lib, pg, fmt}

Writes docs/pd-nonrenewal-candidates.csv.

    python scripts/build_nonrenewal_eligibility.py
"""
from __future__ import annotations

import csv
import difflib
import pickle
import time
import xml.etree.ElementTree as ET

import httpx
import glob
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REN_DIR = ROOT / ".seed_cache" / "cce-renewals" / "data"
REG_DIR = ROOT / ".seed_cache" / "cce-registrations" / "xml"
SRC_DIR = ROOT / ".seed_cache" / "pd_sources"
OUT = ROOT / "docs" / "pd-nonrenewal-candidates.csv"

csv.field_size_limit(10**8)
ARTICLES = {"the", "a", "an"}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def main_title(t: str) -> str:
    """The title before any subtitle, folded, without a leading article or a series tag
    ("The Hamlet (The Snopes Trilogy #1)", "The Lonesome Vigilante [AKA The Vigilante]")."""
    t = re.sub(r"\s*[(\[].*?[)\]]", " ", t or "")
    t = re.split(r"--|—|:\s|;\s|\s/\s|\.\s|,\s+or,?\s", t or "", maxsplit=1)[0]
    w = fold(t).split()
    if w and w[0] in ARTICLES:
        w = w[1:]
    return " ".join(w)


def surname(author: str, comma_first: bool) -> str:
    a = (author or "").strip()
    if comma_first and "," in a:
        s = a.split(",")[0]
    else:
        s = re.sub(r"\(.*?\)", "", a).split()[-1] if a.split() else ""
    s = fold(s).split()
    return s[-1] if s else ""


def title_from_full_text(ft: str) -> str:
    """'R678216. The Lion, the witch and the wardrobe. By C. S. Lewis. © 16Oct50, ...' or
    'HEMINGWAY, ERNEST. To have and have not. © 8Oct37, ...' -> the title part."""
    t = ft.split("©")[0]
    t = re.sub(r"^\s*R[A-Z]?\d+\.\s*", "", t)
    t = re.sub(r"^[A-Z][A-Z' .-]+,[A-Z' .()-]+?\.\s+", "", t)   # leading 'SURNAME, GIVEN.'
    return t.strip()


def load_renewals():
    by_title, by_prefix = defaultdict(list), defaultdict(list)
    n = 0
    for f in sorted(glob.glob(str(REN_DIR / "*.tsv"))):
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                title = row.get("title") or row.get("titl") or ""
                if not title.strip():                  # ~11k rows keep the entry only in full_text
                    title = title_from_full_text(row.get("full_text") or "")
                who = fold(" ".join([row.get("author") or row.get("auth") or "", row.get("claimants") or "",
                                     row.get("full_text") or "", title]))
                for part in title.split("|"):          # one renewal can cover several titles
                    mt = main_title(part)
                    if not mt:
                        continue
                    rec = (mt, who, row.get("id") or "", (row.get("odat") or "")[:4], part.strip())
                    by_title[mt].append(rec)
                    by_prefix[" ".join(mt.split()[:2])].append(rec)
                    n += 1
    print(f"renewal records indexed: {n:,}")
    return by_title, by_prefix


def load_registrations():
    """Book registrations 1930-63 -> {main title: [(who, regnum, year)]}, cached as a pickle."""
    cache = REG_DIR.parent / "index.pkl"
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    idx, n = defaultdict(list), 0
    for y in range(1930, 1964):
        for f in sorted((REG_DIR / str(y)).glob("*.xml")):
            for _, el in ET.iterparse(f, events=("end",)):
                if el.tag != "copyrightEntry":
                    continue
                t = el.find("title")
                regnum = el.get("regnum") or ""
                rd = el.find("regDate")
                year = int((rd.get("date") or "0")[:4]) if rd is not None and (rd.get("date") or "")[:4].isdigit() else 0
                who = fold(" ".join(el.itertext()))
                if t is not None:
                    mt = main_title("".join(t.itertext()))
                    if mt:
                        idx[mt].append((who, regnum, year))
                        n += 1
                el.clear()
    print(f"registrations indexed: {n:,}")
    idx = dict(idx)
    cache.write_bytes(pickle.dumps(idx))
    return idx


def us_edition(title: str, sname: str, year, regs) -> str:
    """'us' when a US ('A') registration by this author exists in the year of first publication,
    'later' when the only US registration came later, '' when none was found."""
    mt = main_title(title)
    found = ""
    for who, regnum, ry in regs.get(mt, []):
        if sname and len(sname) > 2 and not re.search(rf"\b{re.escape(sname)}\b", who):
            continue
        if re.match(r"A-?\d", regnum):
            if year and ry and ry <= year:
                return "us"
            found = "later"
    return found


WD = "https://www.wikidata.org/w/api.php"
WD_UA = {"User-Agent": "ExegeticaLibrary/1.0 (https://exegetica.fly.dev; public-domain eligibility)"}
WD_CACHE = SRC_DIR / "authors_wikidata.json"
US = "Q30"
LIFE50 = {"Q16": "Canada", "Q408": "Australia", "Q664": "New Zealand", "Q258": "South Africa"}


def display_name(author: str, comma_first: bool) -> str:
    """'Johns, W. E. (William Earl)' -> 'W. E. Johns'; 'Steele Rudd' stays."""
    a = re.sub(r"\s*\(.*?\)", "", author or "").strip()
    if comma_first and "," in a:
        sur, _, given = a.partition(",")
        a = f"{given.strip()} {sur.strip()}"
    return a.strip()


def short_name(name: str) -> str:
    w = name.split()
    return f"{w[0]} {w[-1]}" if len(w) > 2 else name


def author_facts(names: list[str]) -> dict:
    """name -> {qid, citizenship [qids], died} from Wikidata; cached, misses cached as {}."""
    cache = json.loads(WD_CACHE.read_text(encoding="utf-8")) if WD_CACHE.exists() else {}
    todo = [n for n in names if n and (n not in cache or (cache[n] == {} and short_name(n) != n))]
    with httpx.Client(headers=WD_UA, timeout=30) as c:
        for i, name in enumerate(todo):
            facts = {}
            try:
                hits = []
                for q in dict.fromkeys([name, short_name(name)]):
                    hits = c.get(WD, params=dict(action="wbsearchentities", search=q, language="en", type="item",
                                                 limit=5, format="json")).json().get("search", [])
                    if hits:
                        break
                ids = [h["id"] for h in hits]
                if ids:
                    ents = c.get(WD, params=dict(action="wbgetentities", ids="|".join(ids), props="claims",
                                                 format="json")).json().get("entities", {})
                    for q in ids:                                   # first human in search order
                        cl = ents.get(q, {}).get("claims", {})
                        if not any(v["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5"
                                   for v in cl.get("P31", [])):
                            continue
                        cit = [v["mainsnak"]["datavalue"]["value"]["id"] for v in cl.get("P27", [])
                               if "datavalue" in v["mainsnak"]]
                        died = None
                        for v in cl.get("P570", []):
                            t = v["mainsnak"].get("datavalue", {}).get("value", {}).get("time", "")
                            if re.match(r"\+\d{4}", t):
                                died = int(t[1:5])
                                break
                        facts = {"qid": q, "citizenship": cit, "died": died}
                        break
            except Exception as e:  # noqa: BLE001
                print(f"  wikidata error for {name!r}: {e}")
                continue
            cache[name] = facts
            if i % 50 == 0:
                WD_CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
                print(f"  wikidata {i}/{len(todo)}")
            time.sleep(0.3)
    WD_CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    return cache


def foreign_status(died, citizenship) -> str:
    if not died:
        return "foreign-needs-dates"
    if died <= 1925:
        return "pd-foreign-home-pd"
    if died <= 1945:
        if set(citizenship) & set(LIFE50):
            return "pd-foreign-home-pd"
        # a known citizenship elsewhere (Britain, Ireland: life+70) kept it protected in 1996
        return "foreign-restored" if citizenship else "foreign-check-nationality"
    return "foreign-restored"


def check(title: str, sname: str, by_title, by_prefix):
    """('renewed'|'check'|'', renewal) for one book."""
    mt = main_title(title)
    if not mt:
        return "", None
    exact = by_title.get(mt, [])
    fuzzy = [r for r in by_prefix.get(" ".join(mt.split()[:2]), [])
             if r[0] != mt and len(mt) >= 12 and difflib.SequenceMatcher(None, mt, r[0]).ratio() >= 0.9]
    for r in exact + fuzzy:
        if sname and len(sname) > 2 and re.search(rf"\b{re.escape(sname)}\b", r[1]):
            return "renewed", r
    if exact and len(mt.split()) <= 2:
        return "check", exact[0]          # short title, different author: probably another book
    if exact:
        return "check", exact[0]
    return "", None


def status_for(year, died, verdict):
    if year and year < 1931:
        return "pd-pre1931"
    if not year and died and died < 1931:
        return "pd-pre1931"               # author died before 1931, so published before it
    if year and year >= 1964:
        return "protected-1964+"
    if not year and not died:
        return "unknown-year"
    if not year and died and died >= 1964:
        return "unknown-year"             # could be a posthumous 1964+ publication
    if verdict == "renewed":
        return "renewed"
    if verdict == "check":
        return "check"
    return "pd-not-renewed"


def main():
    by_title, by_prefix = load_renewals()
    regs = load_registrations()
    rows = []
    fp = json.loads((SRC_DIR / "fp_rows.json").read_text(encoding="utf-8"))
    for b in fp:
        rows.append(dict(source="fadedpage", id=b["pid"], title=b["t"], author=b["a"], year=b.get("y"),
                         died=None, sname=surname(b["a"], True), in_library=b.get("lib"), on_pg=b.get("pg"),
                         fmt=""))
    pga = json.loads((SRC_DIR / "pga_rows.json").read_text(encoding="utf-8"))
    for b in pga:
        d = b.get("d")
        rows.append(dict(source="pg-australia", id=b["i"], title=b["t"], author=b["a"], year=b.get("y"),
                         died=(d[1] if isinstance(d, list) and len(d) > 1 else None),
                         sname=surname(b["a"], False), in_library=b.get("lib"), on_pg=b.get("pg"),
                         fmt=b.get("fmt") or ""))
    # more sources (scripts/build_source_catalogs.py); `cleared` = the source already applies US law
    for cat in sorted(SRC_DIR.glob("*_catalog.json")):
        for b in json.loads(cat.read_text(encoding="utf-8")):
            rows.append(dict(source=cat.stem.replace("_catalog", ""), id=b["id"], title=b["t"], author=b["a"],
                             year=b.get("y"), died=b.get("died"), sname=surname(b["a"], False),
                             in_library=b.get("lib"), on_pg=b.get("pg"), fmt="", cleared=b.get("cleared"),
                             note=b.get("note") or ""))
    for r in rows:
        r["name"] = display_name(r["author"], r["source"] == "fadedpage")
    pre = [r for r in rows if not r.get("cleared")
           and status_for(r["year"], r["died"], "") in ("pd-not-renewed", "unknown-year")]
    facts = author_facts(sorted({r["name"] for r in pre}))
    for r in rows:
        if not r["year"] and not r["died"]:
            r["died"] = (facts.get(r["name"]) or {}).get("died")
    out = []
    for r in rows:
        f = facts.get(r["name"]) or {}
        cit = f.get("citizenship") or []
        verdict, ren = check(r["title"], r["sname"], by_title, by_prefix)
        st = status_for(r["year"], r["died"], verdict)
        us = ""
        if r.get("cleared"):
            verdict, ren = "", None
            # Wikisource also hosts modern US-government documents (PD, but not library books)
            st = "skip-modern-document" if r["year"] and r["year"] >= 1964 else "pd-cleared-by-source"
        elif st == "pd-not-renewed":
            us = us_edition(r["title"], r["sname"], r["year"], regs)
            if us != "us" and US in cit:
                us = "american-author"
            if us not in ("us", "american-author"):
                st = foreign_status(r["died"] or f.get("died"), cit)
        hit = st in ("renewed", "check")
        out.append(dict(source=r["source"], id=r["id"], title=r["title"], author=r["author"], year=r["year"] or "",
                        author_died=r["died"] or f.get("died") or "", status=st, us_basis=us,
                        citizenship=",".join(cit), wikidata=f.get("qid", ""),
                        renewal_id=ren[2] if hit and ren else "", renewal_title=ren[4] if hit and ren else "",
                        renewal_orig_date=ren[3] if hit and ren else "",
                        in_library=int(bool(r["in_library"])), on_gutenberg=int(bool(r["on_pg"])), fmt=r["fmt"],
                        note=r.get("note", "")))
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(sorted(out, key=lambda x: (x["source"], x["status"], x["author"], x["title"])))
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out):,} rows)")
    for src in sorted({x["source"] for x in out}):
        c = Counter(x["status"] for x in out if x["source"] == src)
        new = Counter(x["status"] for x in out if x["source"] == src and not x["in_library"] and not x["on_gutenberg"])
        print(f"\n{src}")
        for k, v in c.most_common():
            print(f"  {k:18} {v:6,}   new (not in library, not on PG): {new[k]:,}")


if __name__ == "__main__":
    main()
