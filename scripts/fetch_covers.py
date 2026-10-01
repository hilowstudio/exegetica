"""Import cover art URLs for Reading-Room books from Open Library (primary) and Google
Books (fallback, quota-bounded). Matched author-first (a wrong cover is worse than none),
cached + resumable, written to books.cover_url. The reader hotlinks these with the
typographic cloth cover as the fallback when a book has none.

    .venv\\Scripts\\python.exe scripts\\fetch_covers.py            # fetch missing, write column
    .venv\\Scripts\\python.exe scripts\\fetch_covers.py --stats     # coverage report only
"""
from __future__ import annotations
import json, os, re, sqlite3, sys, time, urllib.parse, urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB = os.path.join(_ROOT, "db", "books.db")
_CACHE = os.path.join(_ROOT, ".seed_cache", "covers.json")
sys.path.insert(0, _ROOT)
from scripts.classify_loc import clean_title, surname, _matches, _get, _UA  # reuse matcher  # noqa: E402

_GB_DAILY = 900  # stay under the 1000/day Books API cap

def _gb_key():
    for l in open(os.path.join(_ROOT, ".env"), encoding="utf-8"):
        if l.startswith("GOOGLE_BOOKS_API_KEY="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def ol_cover(title, author):
    ct, sa = clean_title(title), surname(author)
    for q in (f"{ct} {sa}", ct):
        u = "https://openlibrary.org/search.json?" + urllib.parse.urlencode(
            {"q": q, "limit": 8, "fields": "key,title,author_name,cover_i"})
        d = _get(u)
        for doc in (d or {}).get("docs", []):
            ci = doc.get("cover_i")
            if ci and ci > 0 and _matches(doc, ct, sa):
                return f"https://covers.openlibrary.org/b/id/{ci}-L.jpg"
        time.sleep(0.2)
    return None

def gb_cover(title, author, key):
    ct, sa = clean_title(title), surname(author)
    q = "intitle:" + ct[:60] + ((" inauthor:" + sa) if sa else "")
    u = "https://www.googleapis.com/books/v1/volumes?" + urllib.parse.urlencode(
        {"q": q, "maxResults": 4, "key": key})
    try:
        req = urllib.request.Request(u, headers=_UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.load(r)
    except Exception:
        return None
    ctoks = set(re.findall(r"[a-z0-9]+", ct.lower()))
    for it in d.get("items", []):
        vi = it.get("volumeInfo", {})
        links = vi.get("imageLinks") or {}
        img = links.get("thumbnail") or links.get("smallThumbnail")
        if not img:
            continue
        # author + light title agreement (avoid a wrong-book cover)
        anames = " ".join(vi.get("authorlist", []) or vi.get("authors", []) or []).lower()
        vtoks = set(re.findall(r"[a-z0-9]+", (vi.get("title") or "").lower()))
        if sa and anames and sa.lower() not in anames:
            continue
        if ctoks and not (ctoks & vtoks):
            continue
        return re.sub(r"&edge=curl", "", img).replace("http://", "https://")
    return None

def run():
    con = sqlite3.connect(_DB, timeout=120)
    if "cover_url" not in {c[1] for c in con.execute("pragma table_info(books)")}:
        con.execute("alter table books add column cover_url TEXT")
        con.commit()
    cache = json.load(open(_CACHE, encoding="utf-8")) if os.path.exists(_CACHE) else {}
    key = _gb_key()
    rows = con.execute("select slug, title, author, cover_url from books order by id").fetchall()
    todo = [(s, t, a) for (s, t, a, cur) in rows if not cur and s not in cache]
    print(f"total={len(rows)} already={len(rows)-len(todo)} to-fetch={len(todo)}", flush=True)
    ol_hits = gb_hits = gb_calls = done = 0
    for slug, title, author in todo:
        url = ol_cover(title, author or "")
        src = "ol" if url else None
        if not url and key and gb_calls < _GB_DAILY:
            gb_calls += 1
            url = gb_cover(title, author or "", key)
            if url:
                src = "gb"
            time.sleep(1.1)  # GB: 1 req/sec
        cache[slug] = url
        if url:
            con.execute("update books set cover_url=? where slug=?", (url, slug))
            ol_hits += (src == "ol"); gb_hits += (src == "gb")
        done += 1
        if done % 50 == 0:
            con.commit(); json.dump(cache, open(_CACHE, "w", encoding="utf-8"))
            print(f"  {done}/{len(todo)} | OL={ol_hits} GB={gb_hits} (gb_calls={gb_calls})", flush=True)
    con.commit(); json.dump(cache, open(_CACHE, "w", encoding="utf-8"))
    have = con.execute("select count(*) from books where cover_url is not null").fetchone()[0]
    tot = con.execute("select count(*) from books").fetchone()[0]
    con.close()
    print(f"DONE. OL={ol_hits} GB={gb_hits} | covers={have}/{tot} ({100*have//tot}%)", flush=True)

def stats():
    con = sqlite3.connect(_DB)
    have = con.execute("select count(*) from books where cover_url is not null").fetchone()[0]
    tot = con.execute("select count(*) from books").fetchone()[0]
    print(f"covers: {have}/{tot} ({100*have//max(tot,1)}%)")

if __name__ == "__main__":
    stats() if "--stats" in sys.argv else run()
