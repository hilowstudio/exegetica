"""House cloth-edition covers for the Reading Room's Book Wrap, drawn on request in each reader's style.

A style is a light theme, a dark theme, a font set and a motif, chosen for the whole library, a shelf or
one book (the most specific wins; the browser resolves which applies). The renderer is
scripts/house_covers.py at COVER_SCALE (600 x 900 by default); every drawn cover is cached on disk by
book and style, and long-cached in the browser.

    GET /api/house-cover/{slug}?t=<theme>&f=<font>&m=<motif>   one cover (WebP)
    GET /api/house-cover/options                                themes, fonts, motifs and the house default
    GET /api/house-cover/motif/{shelf}/{key}.png                a motif swatch for the picker
    GET/PUT /api/cover-prefs                                    a signed-in reader's settings
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import pathlib
import sqlite3
import sys
import threading
import uuid

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from webapp import auth, db, reader

os.environ.setdefault("COVER_SCALE", "0.375")
_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
logger = logging.getLogger("study-bible-web")

_hc = None
_hc_lock = threading.Lock()


def _renderer():
    """scripts/house_covers.py, imported on first use (it loads fonts, themes and the motif manifest)."""
    global _hc
    if _hc is None:
        with _hc_lock:
            if _hc is None:
                import house_covers  # noqa: PLC0415
                _hc = house_covers
    return _hc


OUT_W = 400                     # served width; the woven cloth compresses poorly, so not larger
HOUSE = {"light": "exegetica-rose", "dark": "exegetica-rose-dark", "font": "house", "motif": "universal"}

# ---------------------------------------------------------------- titles
_TEXTS: dict = {"mtime": None, "map": {}, "shelf": {}}
_texts_lock = threading.Lock()


def _texts() -> tuple[dict, dict]:
    """{slug: (cover title, author)} and {slug: first shelf}, rebuilt when books.db changes."""
    path = reader._db_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}, {}
    if _TEXTS["mtime"] != mtime:
        with _texts_lock:
            if _TEXTS["mtime"] != mtime:
                import json
                from cover_text import resolve_all  # noqa: PLC0415
                con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                try:
                    rows = con.execute("select slug, title, author, genres from books").fetchall()
                finally:
                    con.close()
                _TEXTS["map"] = resolve_all([(s, t, a) for s, t, a, _g in rows])
                _TEXTS["shelf"] = {s: (json.loads(g or "[]") or [None])[0] for s, _t, _a, g in rows}
                _TEXTS["mtime"] = mtime
    return _TEXTS["map"], _TEXTS["shelf"]


# ---------------------------------------------------------------- covers
def _cache_dir() -> pathlib.Path:
    d = os.environ.get("COVER_CACHE") or str(pathlib.Path(reader._db_path()).parent / "cover-cache")
    p = pathlib.Path(d)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cover_sync(slug: str, theme: str, font: str, motif: str) -> bytes | None:
    hc = _renderer()
    texts, shelves = _texts()
    if slug not in texts:
        return None
    if motif == "shelf" or motif.startswith("shelf:"):          # a shelf's own motif: the named shelf, or the book's first
        motif = hc.shelf_motif(motif[6:] or shelves.get(slug))
    title, author = texts[slug]                               # the text is in the key, so a retitled book redraws
    key = hashlib.sha1(f"{slug}|{title}|{author}|{theme}|{font}|{motif}|{hc.RENDER_VERSION}|{hc.S}|{OUT_W}".encode()).hexdigest()
    path = _cache_dir() / key[:2] / f"{key}.webp"
    if path.exists():
        return path.read_bytes()
    im = hc.render(title, author, theme, font, motif)
    if im.width > OUT_W:                                   # tiles show ~300px wide at 2x; 400px matches the cover art
        from PIL import Image  # noqa: PLC0415
        im = im.resize((OUT_W, round(im.height * OUT_W / im.width)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "WEBP", quality=80, method=4)
    data = out.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return data


async def cover(request):
    if not reader.available():
        return JSONResponse({"error": "unavailable"}, status_code=503)
    slug = request.path_params["slug"]
    q = request.query_params
    theme, font, motif = q.get("t") or HOUSE["light"], q.get("f") or HOUSE["font"], q.get("m") or HOUSE["motif"]
    try:
        data = await run_in_threadpool(_cover_sync, slug, theme, font, motif)
    except KeyError:
        return JSONResponse({"error": "unknown style"}, status_code=400)
    except Exception:  # noqa: BLE001
        logger.exception("house cover failed: %s", slug)
        return JSONResponse({"error": "render failed"}, status_code=500)
    if data is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return Response(data, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ---------------------------------------------------------------- options for the picker
_SWATCH: dict[str, bytes] = {}


def _options_sync() -> dict:
    hc = _renderer()
    groups = {"light": "Light", "pastel": "Pastel duo", "dark": "Dark", "dark-duo": "Dark duo"}
    themes = []
    for k, t in hc.THEMES.items():
        if k in ("light", "dark"):
            continue
        themes.append({"key": k, "name": t["name"], "group": t["group"], "groupName": groups.get(t["group"], t["group"]),
                       "mode": t["mode"], "foil": t["foil"], "foil2": t.get("foil2"), "text": t["text"], "cloth": t["cloth"]})
    fonts = [{"key": k, "name": v["name"], "genres": [g for g in v["genres"] if g != "all"]}
             for k, v in hc.FONT_SETS.items() if not k.startswith("_")]
    motifs = [{"key": "universal", "shelf": "Library", "subject": "the Exegetica sprig"}]
    try:
        from generate_motifs import SHELVES  # noqa: PLC0415
        order = [f"{hc._key(s)}/{k}" for s, ms in SHELVES.items() for k in ms]
    except Exception:  # noqa: BLE001
        order = list(hc.MOTIF_LIBRARY)
    for k in order:
        if k in hc.MOTIF_LIBRARY:
            v = hc.MOTIF_LIBRARY[k]
            motifs.append({"key": k, "shelf": v["shelf"], "subject": v["subject"]})
    return {"themes": themes, "fonts": fonts, "motifs": motifs, "house": HOUSE, "version": hc.RENDER_VERSION}


async def options(request):
    return JSONResponse(await run_in_threadpool(_options_sync), headers={"Cache-Control": "public, max-age=3600"})


def _swatch_sync(key: str) -> bytes:
    """The motif as a transparent PNG in the house rose, for the picker's grid."""
    if key not in _SWATCH:
        from PIL import Image  # noqa: PLC0415
        hc = _renderer()
        m = Image.open(hc.motif_path(key)).convert("L")
        m.thumbnail((160, 160), Image.LANCZOS)
        im = Image.new("RGBA", m.size, (192, 90, 100, 0))
        im.putalpha(m)
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        _SWATCH[key] = out.getvalue()
    return _SWATCH[key]


async def motif_swatch(request):
    p = request.path_params
    key = "universal" if p["shelf"] == "library" else f"{p['shelf']}/{p['key']}"
    try:
        data = await run_in_threadpool(_swatch_sync, key)
    except (KeyError, FileNotFoundError):
        return JSONResponse({"error": "not found"}, status_code=404)
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


_FONT_SAMPLE: dict[str, bytes] = {}
SAMPLE_TITLE = "The Secret Garden"


def _font_sample_sync(key: str) -> bytes:
    """A sample title set in this font set exactly as a cover sets it (small italic words, tracked
    capitals), as black glyphs on transparency, for the picker's font tiles."""
    if key not in _FONT_SAMPLE:
        from PIL import Image, ImageDraw  # noqa: PLC0415
        hc = _renderer()
        if key not in hc.FONT_SETS or key.startswith("_"):
            raise KeyError(key)
        with hc._RENDER_LOCK:
            hc.use_fonts(key)
            t = SAMPLE_TITLE.upper() if hc.TITLE_STYLE["upper"] else SAMPLE_TITLE
            lines, h = hc.layout_title(t, 2000, 400)              # one line
            m = Image.new("L", (2100, int(h) + 60), 0)
            hc.draw_title(ImageDraw.Draw(m), lines, 1050, 30)
        box = m.getbbox() or (0, 0, 1, 1)
        m = m.crop((max(0, box[0] - 6), max(0, box[1] - 6), box[2] + 6, box[3] + 6))
        im = Image.new("RGBA", m.size, (0, 0, 0, 0))
        im.putalpha(m)
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        _FONT_SAMPLE[key] = out.getvalue()
    return _FONT_SAMPLE[key]


async def font_sample(request):
    try:
        data = await run_in_threadpool(_font_sample_sync, request.path_params["key"])
    except KeyError:
        return JSONResponse({"error": "not found"}, status_code=404)
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------- a reader's settings
_EMPTY = {"library": {}, "shelves": {}, "books": {}}


def _clean(prefs) -> dict:
    """Keep only known fields, in the shape {library: style, shelves: {name: style}, books: {slug: style}}."""
    fields = ("light", "dark", "font", "motif")
    def style(v):
        return {k: str(v[k])[:80] for k in fields if isinstance(v, dict) and v.get(k)}
    p = prefs if isinstance(prefs, dict) else {}
    return {"library": style(p.get("library")),
            "shelves": {str(k)[:120]: style(v) for k, v in (p.get("shelves") or {}).items() if style(v)},
            "books": {str(k)[:200]: style(v) for k, v in (p.get("books") or {}).items() if style(v)}}


async def prefs_get(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    row = await db.fetchrow("select prefs from cover_prefs where user_id=$1", uuid.UUID(user["id"]))
    return JSONResponse(_clean(row["prefs"]) if row and row["prefs"] else dict(_EMPTY))


async def prefs_put(request):
    user = auth.current_user(request)
    if not user:
        return JSONResponse({"error": "authentication required"}, status_code=401)
    if not db.ready():
        return JSONResponse({"error": "database unavailable"}, status_code=503)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    prefs = _clean(body)
    await db.execute(
        """insert into cover_prefs (user_id, prefs, updated_at) values ($1, $2, now())
           on conflict (user_id) do update set prefs=excluded.prefs, updated_at=now()""",
        uuid.UUID(user["id"]), prefs)
    return JSONResponse({"ok": True})
