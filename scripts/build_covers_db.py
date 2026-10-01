"""Own the cover art: download every book's cover (the external URLs in books.cover_url),
convert to WebP, and store the bytes in a dedicated db/covers.db — distributed via R2 to the
Fly volume like books.db, and served by the app at /api/cover/{slug}. No call-time URL fetch.

    .venv\\Scripts\\python.exe scripts\\build_covers_db.py            # download+convert (resumable)
    .venv\\Scripts\\python.exe scripts\\build_covers_db.py --finalize  # point books.cover_url at /api/cover/{slug}
    .venv\\Scripts\\python.exe scripts\\build_covers_db.py --stats

WebP tuned for a ~150px grid tile at 2x (max width 400, quality 80).
"""
from __future__ import annotations
import io, os, sqlite3, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BOOKS = os.path.join(_ROOT, "db", "books.db")
_COVERS = os.path.join(_ROOT, "db", "covers.db")
_UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (self-hosted covers; hello@hilowstudio.dev)"}
_MAXW = 400


def _covers_con():
    con = sqlite3.connect(_COVERS, timeout=120)
    con.execute("""create table if not exists covers (
        slug text primary key, webp blob not null, src_url text, w int, h int, bytes int)""")
    return con


def _fetch_webp(slug, url):
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = im.size
        if w < 80 or h < 80:            # skip placeholders / blanks
            return slug, None, None
        if w > _MAXW:
            im = im.resize((_MAXW, round(h * _MAXW / w)))
        out = io.BytesIO()
        im.save(out, "WEBP", quality=80, method=6)
        b = out.getvalue()
        return slug, b, (im.size[0], im.size[1])
    except Exception:
        return slug, None, None


def build():
    bcon = sqlite3.connect(_BOOKS)
    rows = bcon.execute(
        "select slug, cover_url from books where cover_url is not null and cover_url like 'http%'"
    ).fetchall()
    bcon.close()
    ccon = _covers_con()
    have = {s for (s,) in ccon.execute("select slug from covers")}
    todo = [(s, u) for (s, u) in rows if s not in have]
    print(f"covers with a source URL: {len(rows)} | already stored: {len(have)} | to fetch: {len(todo)}", flush=True)
    ok = fail = done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_fetch_webp, s, u) for (s, u) in todo]
        src = {s: u for (s, u) in todo}
        for fut in as_completed(futs):
            slug, b, size = fut.result()
            done += 1
            if b:
                ccon.execute("insert or replace into covers(slug, webp, src_url, w, h, bytes) values(?,?,?,?,?,?)",
                             (slug, b, src[slug], size[0], size[1], len(b)))
                ok += 1
            else:
                fail += 1
            if done % 100 == 0:
                ccon.commit()
                print(f"  {done}/{len(todo)} | stored={ok} failed={fail}", flush=True)
    ccon.commit()
    tot = ccon.execute("select count(*), coalesce(sum(bytes),0) from covers").fetchone()
    ccon.close()
    print(f"DONE. stored={ok} failed={fail} | covers.db has {tot[0]} images, {tot[1]/1048576:.0f} MB", flush=True)


def finalize():
    """Repoint books.cover_url at our own /api/cover/{slug} for stored covers; NULL the rest
    (a dead external URL becomes the cloth fallback). Then publish books.db + covers.db."""
    ccon = sqlite3.connect(_COVERS)
    stored = {s for (s,) in ccon.execute("select slug from covers")}
    ccon.close()
    bcon = sqlite3.connect(_BOOKS, timeout=120)
    changed = nulled = 0
    for slug, url in bcon.execute("select slug, cover_url from books where cover_url is not null").fetchall():
        if slug in stored:
            local = "/api/cover/" + slug
            if url != local:
                bcon.execute("update books set cover_url=? where slug=?", (local, slug)); changed += 1
        elif url.startswith("http"):
            bcon.execute("update books set cover_url=null where slug=?", (slug,)); nulled += 1
    bcon.commit(); bcon.execute("PRAGMA wal_checkpoint(TRUNCATE)"); bcon.close()
    print(f"finalized: {changed} -> /api/cover/*, {nulled} dead externals nulled. "
          f"Now: publish_db.py books && publish_db.py covers")


def stats():
    if not os.path.exists(_COVERS):
        print("no covers.db yet"); return
    ccon = sqlite3.connect(_COVERS)
    n, sz = ccon.execute("select count(*), coalesce(sum(bytes),0) from covers").fetchone()
    avg = ccon.execute("select avg(bytes) from covers").fetchone()[0] or 0
    print(f"covers.db: {n} images, {sz/1048576:.0f} MB total, {avg/1024:.1f} KB avg")


if __name__ == "__main__":
    if "--finalize" in sys.argv:
        finalize()
    elif "--stats" in sys.argv:
        stats()
    else:
        build()
