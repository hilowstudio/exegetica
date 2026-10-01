"""Enrich the sparse Reading-Room sections with Google Books BISAC categories.

Fetch phase (safe anytime): read the members of sparse sections, query Google Books
(1 req/sec, <=1000/day), map BISAC -> our taxonomy, cache suggestions to a file.
Apply phase (DB write): update section/genres where BISAC clearly indicates a better,
more-specific section. Run apply ONLY when nothing else holds db/books.db open.

    python scripts/enrich_sections.py --fetch    # read-only + cache
    python scripts/enrich_sections.py --apply     # writes db + reports changes
"""
from __future__ import annotations
import json, os, re, sqlite3, sys, time, urllib.parse, urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB = os.path.join(_ROOT, "db", "books.db")
_CACHE = os.path.join(_ROOT, ".seed_cache", "bisac_enrich.json")
_SPARSE_MAX = 150
_DAILY_CAP = 1000

def _key():
    for l in open(os.path.join(_ROOT, ".env"), encoding="utf-8"):
        if l.startswith("GOOGLE_BOOKS_API_KEY="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no key")

# BISAC category substring -> our section (specific first; bare 'Fiction' intentionally excluded)
_RULES = [
    ("juvenile", "Children's"), ("young adult", "Young Adult"),
    ("romance", "Romance"), ("horror", "Horror & Gothic"), ("ghost", "Horror & Gothic"),
    ("fantasy", "Fantasy"), ("science fiction", "Science Fiction"),
    ("mystery", "Mystery & Crime"), ("detective", "Mystery & Crime"), ("crime", "Mystery & Crime"), ("thriller", "Mystery & Crime"),
    ("short stories", "Short Stories"), ("fairy tale", "Fantasy"),
    ("poetry", "Poetry"), ("drama", "Plays & Drama"), ("plays", "Plays & Drama"),
    ("humor", "Humor & Satire"), ("satire", "Humor & Satire"),
    ("biography", "Biography & Memoir"), ("autobiography", "Biography & Memoir"), ("memoir", "Biography & Memoir"),
    ("travel", "Travel & Places"),
    ("cooking", "Cooking & Home"), ("gardening", "Cooking & Home"), ("crafts", "Cooking & Home"), ("house & home", "Cooking & Home"), ("hobbies", "Cooking & Home"),
    ("health", "Health & Medicine"), ("medical", "Health & Medicine"), ("fitness", "Health & Medicine"),
    ("psychology", "Psychology"),
    ("sports", "Sports & Recreation"), ("games", "Sports & Recreation"), ("recreation", "Sports & Recreation"),
    ("technology", "Technology & How-To"), ("engineering", "Technology & How-To"),
    ("nature", "Science & Nature"), ("science", "Science & Nature"),
    ("music", "Art, Music & Performance"), ("performing arts", "Art, Music & Performance"), ("photography", "Art, Music & Performance"), (" art", "Art, Music & Performance"),
    ("philosophy", "Philosophy"), ("ethics", "Philosophy"),
    ("social science", "Society, Politics & Economics"), ("political", "Society, Politics & Economics"), ("business", "Society, Politics & Economics"), ("economics", "Society, Politics & Economics"), ("law", "Society, Politics & Economics"), ("education", "Society, Politics & Economics"),
    ("language arts", "Language & Reference"), ("foreign language", "Language & Reference"), ("literary criticism", "Language & Reference"), ("reference", "Reference & Knowledge"),
    ("history", "History"),
]

def bisac_to_section(cats):
    joined = " || ".join(cats).lower()
    for kw, sec in _RULES:
        if kw in joined:
            return sec
    if "religion" in joined:
        return "Christianity" if "christian" in joined else "World Religions & Spirituality"
    return None  # only bare Fiction / unmapped -> no confident suggestion

def surname(a):
    a = re.sub(r"\([^)]*\)", " ", a or ""); toks = re.findall(r"[A-Za-z][A-Za-z'\-]+", a)
    return toks[-1] if toks else ""

def gb_categories(key, title, author):
    q = "intitle:" + title[:60] + ((" inauthor:" + author) if author else "")
    u = "https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode({"q": q, "maxResults": 3, "key": key})
    try:
        with urllib.request.urlopen(u, timeout=25) as r:
            d = json.load(r)
    except Exception:
        return []
    cats = []
    for it in d.get("items", []):
        for c in it.get("volumeInfo", {}).get("categories", []) or []:
            if c not in cats:
                cats.append(c)
    return cats

def sparse_members(con):
    from collections import Counter
    cnt = Counter()
    for (g,) in con.execute("select genres from books"):
        for x in json.loads(g):
            cnt[x] += 1
    sparse = {s for s, n in cnt.items() if n <= _SPARSE_MAX}
    rows = []
    for i, t, a, g in con.execute("select id,title,author,genres from books"):
        secs = json.loads(g)
        if any(s in sparse for s in secs):
            rows.append((i, t, a or "", secs[0] if secs else None))
    return sparse, rows

def fetch():
    key = _key(); con = sqlite3.connect(_DB, timeout=60)
    sparse, rows = sparse_members(con)
    print(f"sparse sections ({len(sparse)}): {sorted(sparse)}")
    print(f"members to query: {len(rows)} (cap {_DAILY_CAP})", flush=True)
    cache = {}
    if os.path.exists(_CACHE):
        cache = json.load(open(_CACHE, encoding="utf-8"))
    n = 0
    for i, t, a, cur in rows:
        if str(i) in cache:
            continue
        if n >= _DAILY_CAP:
            print(f"hit daily cap at {n}", flush=True); break
        cats = gb_categories(key, t, surname(a))
        sug = bisac_to_section(cats)
        cache[str(i)] = {"title": t, "current": cur, "cats": cats, "suggested": sug}
        n += 1
        if n % 25 == 0:
            json.dump(cache, open(_CACHE, "w", encoding="utf-8")); print(f"  fetched {n}", flush=True)
        time.sleep(1.1)  # 1 req/sec cap
    json.dump(cache, open(_CACHE, "w", encoding="utf-8"))
    got = sum(1 for v in cache.values() if v["cats"])
    chg = sum(1 for v in cache.values() if v["suggested"] and v["suggested"] != v["current"])
    print(f"DONE fetch: cached={len(cache)} with-categories={got} would-change={chg}", flush=True)

def apply():
    con = sqlite3.connect(_DB, timeout=120)
    cache = json.load(open(_CACHE, encoding="utf-8"))
    from collections import Counter
    moves = Counter(); changed = 0
    for sid, v in cache.items():
        sug, cur = v.get("suggested"), v.get("current")
        if sug and sug != cur:
            con.execute("update books set genres=?, section=? where id=?",
                        (json.dumps([sug]), json.dumps([sug]), int(sid)))
            moves[f"{cur} -> {sug}"] += 1; changed += 1
    con.commit()
    print(f"applied {changed} section changes")
    for m, c in moves.most_common(30):
        print(f"  {c:4d}  {m}")

if __name__ == "__main__":
    if "--apply" in sys.argv:
        apply()
    else:
        fetch()
