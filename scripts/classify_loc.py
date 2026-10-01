"""Resolve a Dewey Decimal (DDC) class for Reading-Room books via OpenLibrary
(which carries LOC's MARC-derived classifications). DDC-primary; LCC kept only as
a diagnostic. Aggressive multi-pass matching + work-editions fallback + local cache.

    from scripts.classify_loc import resolve
    ddc, lcc, subjects, how = resolve(title, author)
"""
from __future__ import annotations
import json, os, re, time, urllib.parse, urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE = os.path.join(_ROOT, ".seed_cache", "loc_classify.json")
_UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (classification cross-ref; contact hello@hilowstudio.dev)"}

_cache: dict | None = None
def _load():
    global _cache
    if _cache is None:
        try: _cache = json.load(open(_CACHE, encoding="utf-8"))
        except Exception: _cache = {}
    return _cache
def _save():
    os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
    json.dump(_cache, open(_CACHE, "w", encoding="utf-8"))

_VOL = re.compile(r"\b(vol(ume|\.)?\s*[ivxlcdm\d]+|part\s*\d+|\(of\s*\d+\)|—\s*complete|,\s*complete|complete)\b", re.I)
# run-on subtitle / report-metadata markers that start a descriptive tail
_TAIL = re.compile(r"\b(being |rewritten |personal narratives|annual report|report of the|"
                   r"a (?:paper|series of|narrative|tale) |no\.\s*\d|"
                   r"\d+(?:st|nd|rd|th) annual|to which (?:is|are)|with (?:an?|the) (?:introduction|preface|account|memoir|history|notes?)\b|"
                   r"government printing office|bureau of)", re.I)
def clean_title(t: str) -> str:
    t = re.split(r"[:;]|—| - |, or,| or, ", t, 1)[0]     # drop subtitle
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t)           # drop parentheticals/brackets
    m = _TAIL.search(t)
    if m and m.start() > 8:                               # cut a run-on descriptive tail
        t = t[:m.start()]
    t = _VOL.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.-—")
    return " ".join(t.split()[:10])                       # cap length
def surname(a: str) -> str:
    a = re.sub(r"\([^)]*\)", " ", a or "")       # drop parenthetical alt-name
    a = re.sub(r"\b\d{3,4}\b", " ", a)           # drop life-dates
    toks = re.findall(r"[A-Za-z][A-Za-z'\-]{1,}", a)
    drop = {"Lord", "Sir", "Mrs", "Mr", "Dr", "Rev", "Saint", "St", "Jr", "Esq", "Hon"}
    toks = [t for t in toks if t not in drop]
    return toks[-1] if toks else ""              # "Alfred, Lord Tennyson" -> "Tennyson"

def _norm_ddc(v: str):
    if not v: return None
    v = str(v).strip()
    m = re.search(r"\d{1,3}(\.\d+)?", v.lstrip("j[").replace("Fic", "999"))
    if v.strip().lower().startswith("[fic") or v.strip().lower() == "fic":
        return "FIC"
    return m.group(0) if m else None

def _get(url):
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        return None

def _search(q, limit=40):
    u = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(
        {"q": q, "limit": limit, "fields": "key,title,author_name,ddc,lcc,subject"})
    return _get(u)

def _toks(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {"the","a","an","of","and","or","to","in"}

def _matches(doc, wt, wa):
    dt = _toks(doc.get("title")); ct = _toks(wt)
    anames = " ".join(doc.get("author_name") or []).lower()
    share = ct & dt
    if wa and anames:
        # strong guard: our surname must appear among the record's authors;
        # then a single shared title token confirms it's the right work.
        if wa.lower() not in anames:
            return False
        return bool(share) or not ct
    # record lists no author (or we have none): fall back to solid title agreement
    return bool(ct) and len(share) >= max(1, int(0.6 * len(ct)))

def _scan(docs, wt, wa):
    ddc = lcc = None; subj = []; workkey = None
    for d in docs or []:
        if not _matches(d, wt, wa):
            continue
        if not workkey: workkey = d.get("key")
        if not ddc and d.get("ddc"):
            for v in d["ddc"]:
                nd = _norm_ddc(v)
                if nd: ddc = nd; break
        if not lcc and d.get("lcc"): lcc = d["lcc"][0]
        if not subj and d.get("subject"): subj = d["subject"][:8]
    return ddc, lcc, subj, workkey

def resolve(title: str, author: str):
    c = _load()
    ct, sa = clean_title(title), surname(author)
    ckey = f"{ct}|{sa}".lower()
    if ckey in c:
        r = c[ckey]; return r.get("ddc"), r.get("lcc"), r.get("subj", []), r.get("how")
    ddc = lcc = None; subj = []; how = "miss"; workkey = None
    passes = [(f"{ct} {sa}", "t+a"), (ct, "t"), (f'title:"{ct}"', "texact")]
    for q, tag in passes:
        d = _search(q)
        rddc, rlcc, rsubj, wk = _scan((d or {}).get("docs"), ct, sa)
        workkey = workkey or wk
        lcc = lcc or rlcc; subj = subj or rsubj
        if rddc:
            ddc, how = rddc, tag; break
        time.sleep(0.15)
    if not ddc and workkey and workkey.startswith("/works/"):   # editions fallback
        ed = _get(f"https://openlibrary.org{workkey}/editions.json?limit=50")
        for e in (ed or {}).get("entries", []):
            for v in e.get("dewey_decimal_class", []) or []:
                nd = _norm_ddc(v)
                if nd: ddc, how = nd, "editions"; break
            if ddc: break
    c[ckey] = {"ddc": ddc, "lcc": lcc, "subj": subj, "how": how}; _save()
    return ddc, lcc, subj, how


def run_all(dbpath):
    """Resolve+store ddc/lcc/subjects for every book. Resumable: skips rows already done."""
    import sqlite3
    from collections import Counter
    con = sqlite3.connect(dbpath)
    rows = con.execute("select id,title,author,ddc,lcc,loc_how from books order by id").fetchall()
    todo = [r for r in rows if not (r[3] or r[4] or r[5])]
    print(f"total={len(rows)} already-done={len(rows)-len(todo)} to-fetch={len(todo)}", flush=True)
    hows = Counter(); done = 0
    for bid, t, a, *_ in todo:
        ddc, lcc, subj, how = resolve(t or "", a or "")
        con.execute("update books set ddc=?, lcc=?, loc_subjects=?, loc_how=? where id=?",
                    (ddc, lcc, json.dumps(subj) if subj else None, how, bid))
        hows[how] += 1; done += 1
        if done % 25 == 0:
            con.commit(); print(f"  {done}/{len(todo)}  {dict(hows)}", flush=True)
        time.sleep(0.1)
    con.commit()
    ddc_n = con.execute("select count(*) from books where ddc is not null and ddc!='FIC'").fetchone()[0]
    lcc_n = con.execute("select count(*) from books where lcc is not null").fetchone()[0]
    either = con.execute("select count(*) from books where ddc is not null or lcc is not null").fetchone()[0]
    tot = con.execute("select count(*) from books").fetchone()[0]
    print(f"DONE. total={tot} DDC={ddc_n} LCC={lcc_n} DDC-or-LCC={either} ({100*either//tot}%)", flush=True)
    print("how:", dict(hows), flush=True)


if __name__ == "__main__":
    import sqlite3, sys
    _DB = os.path.join(_ROOT, "db", "books.db")
    if "--all" in sys.argv:
        run_all(_DB); raise SystemExit
    con = sqlite3.connect(_DB)
    rows = con.execute("select id,title,author from books").fetchall()
    stride = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 350
    sample = rows[::stride] if "--sample" in sys.argv else rows
    from collections import Counter; hows = Counter()
    hit = fic = 0
    for i, t, a in sample:
        ddc, lcc, subj, how = resolve(t, a or "")
        if ddc and ddc != "FIC": hit += 1
        if ddc == "FIC": fic += 1
        hows[how] += 1
        if "--quiet" not in sys.argv:
            print(f"{t[:36]:36} | ddc={(ddc or '-'):7} lcc={(lcc or '-')[:6]:6} [{how}]")
    n = len(sample)
    print(f"\nsample={n} | real DDC={hit} | FIC={fic} | none={n-hit-fic} | DDC/FIC-coverage={100*(hit+fic)//n}%")
    print("how:", dict(hows))
