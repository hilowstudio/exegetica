"""House covers: the Exegetica cloth edition, built in code.

The image model draws only the motif, one black-on-white silhouette. Everything else is code:
the cloth, the double-rule border, the half-drop pattern, and the title and author, typeset in
Spectral and IBM Plex Mono. So spelling, palette and grid are always exact, and one motif yields
both editions (light: parchment cloth; dark: ink cloth).

Motifs resolve from most to least specific, so the library can be covered in layers:
    assets/cover-motifs/book/<slug>.png
    assets/cover-motifs/subgenre/<key>.png
    assets/cover-motifs/section/<section>.png
    assets/cover-motifs/universal.png

    # draw candidate motifs (Gemini), cleaned to masks under .seed_cache/house_covers/motifs/<name>/
    python scripts/house_covers.py motif --name universal --subject "a single garden blossom ..." --n 4
    # adopt one candidate as the motif for a level
    python scripts/house_covers.py adopt .seed_cache/house_covers/motifs/universal/cand-2.png universal
    # render covers (masters to .seed_cache/house_covers/out/) and a contact sheet
    python scripts/house_covers.py render --sample 16 --sheet
    python scripts/house_covers.py render --slugs a,b,c
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import random
import re
import sqlite3
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(_ROOT / "scripts"))
from cover_text import resolve_all  # noqa: E402

FONTS = _ROOT / "assets" / "cover-fonts"
MOTIFS = _ROOT / "assets" / "cover-motifs"
CACHE = _ROOT / ".seed_cache" / "house_covers"

PARCHMENT, INK, ROSE, SOFT_ROSE = "#f0e8dc", "#1e2026", "#c05a64", "#dd8089"
# Color themes (assets/cover-themes.json): each is a cloth and a foil, lit as a light or a dark cloth.
# "light" and "dark" are the Exegetica Rose defaults; any theme key can stand in for them.
THEMES: dict[str, dict] = {}
for _mode, _ts in json.loads((_ROOT / "assets" / "cover-themes.json").read_text(encoding="utf-8")).items():
    if not _mode.startswith("_"):                            # groups: light, dark, pastel (lit as light)
        for _k, _t in _ts.items():
            THEMES[_k] = _t | {"mode": "dark" if _mode.startswith("dark") else "light", "group": _mode}
# The board is always the house cloth (parchment for light themes, ink for dark); a theme only colors
# the pattern. The lettering takes the pattern's primary color, darkened on parchment and lightened on ink
# by the group's SHIFT (light 30%; pastel and dark 60%).
BOARD = {"light": PARCHMENT, "dark": INK}


SHIFT = {"light": 0.30, "pastel": 0.60, "dark": 0.60, "dark-duo": 0.60}   # how far the lettering moves from the foil, per theme group


def _shift(c: str, mode: str, amount: float) -> str:
    """The foil darkened (on parchment) or lightened (on ink) by `amount` for the lettering."""
    r, g, b_ = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    if mode == "light":
        return "#%02x%02x%02x" % tuple(round(v * (1 - amount)) for v in (r, g, b_))
    return "#%02x%02x%02x" % tuple(round(v + (255 - v) * amount) for v in (r, g, b_))


for _t in THEMES.values():
    _t["cloth"] = BOARD[_t["mode"]]
    _t["text"] = _shift(_t["foil"], _t["mode"], SHIFT[_t["group"]])
THEMES["light"] = THEMES["exegetica-rose"]
THEMES["dark"] = THEMES["exegetica-rose-dark"]
EDITIONS = {k: (t["cloth"], t["foil"]) for k, t in THEMES.items()}


def _mode(theme: str) -> str:
    return THEMES[theme]["mode"]

# Render scale: 1.0 is the 1600 x 2400 master; the web server renders smaller (COVER_SCALE, e.g. 0.375 ->
# 600 x 900) to fit its memory. Every pixel measure below goes through _s(); heights scale too, so the
# lighting's slopes, and so the look, stay the same at any size.
import os as _os
S = float(_os.environ.get("COVER_SCALE", "1"))


def _s(v: float) -> float:
    return v * S


def _si(v: float) -> int:
    return max(1, round(v * S))


# COVER_ASPECT (height / width, default 2:3) lets a printed book use the same design at its page
# shape, e.g. 1.294 for US Letter; grid rows, title band and author band all follow H.
W, H = round(1600 * S), round(1600 * S * float(_os.environ.get("COVER_ASPECT", "1.5")))
INSET = _si(80)                 # border inset, 5% of the width
AUTHOR_BAND = float(_os.environ.get("COVER_AUTHOR_BAND", "0.09"))   # clear band at the bottom for the author line (0: none)
TITLE_AT = 0.5                  # the title panel's center, as a share of the cover height from the bottom
COLS = 9                        # half-drop grid columns (odd, so the pattern is symmetric); rows follow
MOTIF_FILL = 0.72               # motif size as a share of the grid cell

MOTIF_MODEL = "gemini-nano-banana-2.1"
MOTIF_PROMPT = """A single {subject}, drawn as one flat silhouette in solid black on a plain pure white background.

Style: hand-painted gouache screen print. A few bold flat shapes with soft dry-brush edges. Inner detail is shown only as thin gaps of white between the shapes, like a papercut. No outlines, no shading, no gradients, no gray, no texture in the background.

The silhouette is centered, shown whole, and fills about 70% of the square, with clear white space on every side. Simple and bold enough to recognize at a small size, like an emblem stamped into the cloth cover of a Victorian book. Use bold, chunky shapes with no hairline details: every stroke, stem and white gap must be thick enough to read when the whole image is shrunk to one centimeter wide. Compact and upright, with a balanced, roughly square outline: a recognizable silhouette with some papercut detail inside, neither a solid blob nor a tangle of fine parts.

Only black and white. No text, letters, numbers, signature, border, frame, ground line, shadow, or second object."""


# ---------------------------------------------------------------- motifs
def _gemini_key() -> str:
    for line in (_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("GEMINI_API_KEY missing from .env")


def draw_motif(subject: str, model: str = MOTIF_MODEL) -> Image.Image:
    body = {"contents": [{"parts": [{"text": MOTIF_PROMPT.format(subject=subject)}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), headers={"x-goog-api-key": _gemini_key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    for part in d["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            import io
            return Image.open(io.BytesIO(base64.b64decode(part["inlineData"]["data"]))).convert("RGB")
    raise RuntimeError("no image in response: " + json.dumps(d)[:300])


def to_mask(img: Image.Image) -> tuple[Image.Image, dict]:
    """Black-on-white drawing -> 'L' mask (255 = ink), cropped to the motif with a small margin.
    Keeps the soft edge (a short ramp instead of a hard threshold) so dry-brush texture survives."""
    g = np.asarray(img.convert("L"), dtype=np.float32)
    ink = np.clip((200 - g) / (200 - 80), 0, 1)              # 80 and darker = full ink, 200+ = paper
    m = Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(3))
    a = np.asarray(m) > 64
    h, w = a.shape
    edge = bool(a[:3].any() or a[-3:].any() or a[:, :3].any() or a[:, -3:].any())
    rgb = np.asarray(img, dtype=np.int16)
    tinted = float((np.abs(rgb[..., 0] - rgb[..., 1]) + np.abs(rgb[..., 1] - rgb[..., 2]) > 40).mean())
    stats = {"coverage": round(float(a.mean()), 3), "touches_edge": edge, "tinted": round(tinted, 3)}
    box = m.point(lambda v: 255 if v > 64 else 0).getbbox()
    if box:
        pad = int(0.04 * max(box[2] - box[0], box[3] - box[1]))
        m = m.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad)))
    stats["ok"] = 0.06 <= stats["coverage"] <= 0.6 and not edge and tinted < 0.02
    return m, stats


def resolve_motif(slug: str, section: str | None, subgenre: str | None = None) -> pathlib.Path:
    for p in ([MOTIFS / "book" / f"{slug}.png"]
              + ([MOTIFS / "subgenre" / f"{_key(subgenre)}.png"] if subgenre else [])
              + ([MOTIFS / "section" / f"{_key(section)}.png"] if section else [])
              + [MOTIFS / "universal.png"]):
        if p.exists():
            return p
    raise SystemExit("no motif found; adopt one as universal first")


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- text
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Spring|Summer|Fall|Autumn|Winter)"


_TEXTS: dict[str, tuple[str, str]] = {}


def cover_texts() -> dict[str, tuple[str, str]]:
    """{slug: (cover title, author line)} for the whole library, made once per process (the rules
    look across books to keep two covers from coming out the same)."""
    if not _TEXTS:
        con = sqlite3.connect(_os.environ.get("BOOKS_DB") or str(_ROOT / "db" / "books.db"))
        _TEXTS.update(resolve_all(con.execute("select slug, title, author from books").fetchall()))
        con.close()
    return _TEXTS


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


# the title face: file, variable-font axes, all caps or not, letter-spacing (em), line height
# Font sets (assets/cover-font-sets.json): a title face and an author pairing. use_fonts(key) switches.
FONT_SETS = json.loads((_ROOT / "assets" / "cover-font-sets.json").read_text(encoding="utf-8"))
_TITLE_DEF = {"axes": {}, "upper": False, "track": 0.0, "lh": 1.05, "scale": 1.0}
_AUTHOR_DEF = {"axes": {}, "upper": True, "track": 0.16}
TITLE_STYLE = _TITLE_DEF | FONT_SETS["house"]["title"]
AUTHOR_STYLE = _AUTHOR_DEF | FONT_SETS["house"]["author"]


def use_fonts(key: str = "house") -> None:
    global TITLE_STYLE, AUTHOR_STYLE
    TITLE_STYLE = _TITLE_DEF | FONT_SETS[key]["title"]
    AUTHOR_STYLE = _AUTHOR_DEF | FONT_SETS[key]["author"]
_TF: dict[tuple, ImageFont.FreeTypeFont] = {}
_AXIS_NAMES = {"wght": "weight", "opsz": "optical", "SOFT": "soft", "WONK": "wonk", "wdth": "width"}


def _title_font(size: int) -> ImageFont.FreeTypeFont:
    return _styled_font(TITLE_STYLE, size)


def _styled_font(st: dict, size: int) -> ImageFont.FreeTypeFont:
    key = (st["file"], tuple(sorted(st["axes"].items())), size)
    if key not in _TF:
        f = ImageFont.truetype(str(FONTS / st["file"]), size)
        if st["axes"]:
            axes = f.get_variation_axes()
            vals = []
            for ax in axes:
                nm = ax["name"].decode() if isinstance(ax["name"], bytes) else str(ax["name"])
                v = ax["default"]
                for k, want in st["axes"].items():
                    if nm.lower().startswith(_AXIS_NAMES.get(k, k).lower()):
                        v = want
                vals.append(v)
            f.set_variation_by_axes(vals)
        _TF[key] = f
    return _TF[key]


def _width(font, s: str, tracking: float = 0.0) -> float:
    return font.getlength(s) + tracking * font.size * max(0, len(s) - 1)


def _balanced(words: list[str], n: int, font, track: float = 0.0) -> list[str]:
    """Split words into n lines minimizing the widest line."""
    n = min(n, len(words))
    if n <= 1:
        return [" ".join(words)]
    ww = [_width(font, w, track) for w in words]
    sp = font.getlength(" ") + 2 * track * font.size
    pre = [0.0]
    for w in ww:
        pre.append(pre[-1] + w)
    def span(j, i):                                          # width of words[j:i] on one line
        return pre[i] - pre[j] + sp * (i - j - 1)
    L = len(words)
    INF = float("inf")
    best = [[INF] * (n + 1) for _ in range(L + 1)]           # best[i][k]: words[:i] in k lines
    cut = [[0] * (n + 1) for _ in range(L + 1)]
    best[0][0] = 0.0
    for i in range(1, L + 1):
        for k in range(1, min(n, i) + 1):
            for j in range(k - 1, i):
                v = max(best[j][k - 1], span(j, i))
                if v < best[i][k]:
                    best[i][k], cut[i][k] = v, j
    lines, i = [], L
    for k in range(n, 0, -1):
        j = cut[i][k]
        lines.append(" ".join(words[j:i]))
        i = j
    return lines[::-1]


def fit_title(title: str, box_w: int, box_h: int):
    words = title.split()
    tr, lh, sc = TITLE_STYLE["track"], TITLE_STYLE["lh"], TITLE_STYLE.get("scale", 1.0)
    for size in range(int(_s(210) * sc), int(_s(64) * sc), -_si(4)):   # sc: faces with a small x-height (scripts) set larger
        font = _title_font(size)
        for n in range(1, 6):
            lines = _balanced(words, n, font, tr)
            if max(_width(font, l, tr) for l in lines) <= box_w and n * size * lh <= box_h * sc:
                return font, lines
    font = _title_font(int(_s(64) * sc))
    return font, _balanced(words, 5, font, tr)


# ---------------------------------------------------------------- small words
# Articles, short conjunctions and prepositions can be set smaller than the title's main words, as on
# old title pages. SMALL_WORDS: "off" (one size), "inline" (smaller, on the same baseline), "stack"
# (smaller, on a line of their own) or "italic" (smaller italic, inline).
SMALL_WORDS = "italic"
SMALL_SET = set("a an the and or nor but of in on at to by for with from as into upon".split())
SMALL_RATIO = {"inline": 0.58, "stack": 0.52, "italic": 0.66}


def _is_small(w: str) -> bool:
    if w == "&":                                            # the ampersand sets small, with the small words
        return True
    return w.lower().strip(",.;:!?'’\"“”") in SMALL_SET


def _line_ok(flags: list[bool], first: bool, nwords: int) -> bool:
    """Adam's two rules. (1) Small words never stand alone on the first line, unless the title is two words
    ("The Graduate"). (2) A line holding any large word must begin or end with a large word."""
    if all(flags):
        return not first or nwords == 2
    return not flags[0] or not flags[-1]


def _small_font(size: int) -> ImageFont.FreeTypeFont:
    if SMALL_WORDS == "italic" and TITLE_STYLE.get("italic"):
        return _styled_font(_TITLE_DEF | TITLE_STYLE | {"file": TITLE_STYLE["italic"]}, size)
    return _title_font(size)


def _split_runs(widths: list[float], space: float, box_w: float) -> list[tuple[int, int]]:
    """Fewest lines that fit box_w, then balanced: (start, end) token ranges."""
    n = len(widths)
    for k in range(1, n + 1):
        best = None
        def rec(i, left, acc, wmax):
            nonlocal best
            if left == 1:
                w = sum(widths[i:]) + space * (n - i - 1)
                m = max(wmax, w)
                if w <= box_w and (best is None or m < best[0]):
                    best = (m, acc + [(i, n)])
                return
            for j in range(i + 1, n - left + 2):
                w = sum(widths[i:j]) + space * (j - i - 1)
                if w <= box_w:
                    rec(j, left - 1, acc + [(i, j)], max(wmax, w))
        if n <= 14:
            rec(0, k, [], 0)
        if best:
            return best[1]
    return [(0, n)]


def layout_title(t: str, box_w: float, box_h: float):
    """[(segments, line_height, big_size)], total height. segments: [(text, font)] on one baseline."""
    words = t.split()
    small = [_is_small(w) for w in words]
    if all(small) or len(words) < 2:
        small = [False] * len(words)
    tr, lh, sc = TITLE_STYLE["track"], TITLE_STYLE["lh"], TITLE_STYLE.get("scale", 1.0)
    ratio = SMALL_RATIO[SMALL_WORDS]
    out = None
    for size in range(int(_s(230) * sc), int(_s(64) * sc), -_si(4)):
        big, sm = _title_font(size), _small_font(max(_si(20), round(size * ratio)))
        f = [sm if s else big for s in small]
        wd = [_width(fi, w, tr) for fi, w in zip(f, words)]
        sp = big.getlength(" ") + 2 * tr * size
        lines = []
        if SMALL_WORDS == "stack":
            i = 0
            lead = []
            if small[0] and len(words) > 2:                   # rule 1: "The" rides with the first big word
                while i < len(words) and small[i]:
                    i += 1
                lead = list(range(i))
            while i < len(words):
                j = i
                while j < len(words) and small[j] == small[i]:
                    j += 1
                run_sp = (sm.getlength(" ") + 2 * tr * sm.size) if small[i] else sp
                if lead:
                    lw = sum(wd[q] for q in lead) + sp * len(lead)
                    runs = _split_runs(wd[i:j], run_sp, box_w - lw)
                else:
                    runs = _split_runs(wd[i:j], run_sp, box_w)
                for a, b in runs:
                    idx = (lead if lead else []) + list(range(i + a, i + b))
                    lines.append([(words[k], f[k]) for k in idx])
                    lead = []
                i = j
        else:
            for k in range(1, 7):
                best = None
                def rec(i, left, acc, wmax):
                    nonlocal best
                    if left == 1:
                        if not _line_ok(small[i:], not acc, len(words)):
                            return
                        w = sum(wd[i:]) + sp * (len(words) - i - 1)
                        m = max(wmax, w)
                        if best is None or m < best[0]:
                            best = (m, acc + [(i, len(words))])
                        return
                    for j in range(i + 1, len(words) - left + 2):
                        if small[j - 1] and small[j]:                # never break inside a run of small words ("of | the")
                            continue
                        if _line_ok(small[i:j], not acc, len(words)):
                            rec(j, left - 1, acc + [(i, j)], max(wmax, sum(wd[i:j]) + sp * (j - i - 1)))
                if k <= len(words) and len(words) <= 14:
                    rec(0, k, [], 0)
                if best and best[0] <= box_w:
                    lines = [[(words[q], f[q]) for q in range(a, b)] for a, b in best[1]]
                    break
        if not lines:
            continue
        out, total = [], 0.0
        for segs in lines:
            top = max(fi.size for _, fi in segs)
            h = top * lh
            out.append((segs, h, top))
            total += h
        widest = max(sum(_width(fi, w, tr) for w, fi in segs) + sp * (len(segs) - 1) for segs, _, _ in out)
        if widest <= box_w and total <= box_h * sc and len(out) <= 7:
            return out, total
    if out is not None:
        return out, total
    # no layout at any size (titles over 14 words skip the search): fill lines greedily at the smallest size
    size = int(_s(64) * sc)
    big, sm = _title_font(size), _small_font(max(_si(20), round(size * ratio)))
    sp = big.getlength(" ") + 2 * tr * size
    lines, cur, cw = [], [], 0.0
    for w, fi in zip(words, [sm if s else big for s in small]):
        ww = _width(fi, w, tr)
        if cur and cw + sp + ww > box_w:
            lines.append(cur)
            cur, cw = [], 0.0
        cw += (sp if cur else 0) + ww
        cur.append((w, fi))
    if cur:
        lines.append(cur)
    out = [(segs, max(fi.size for _, fi in segs) * lh, max(fi.size for _, fi in segs)) for segs in lines]
    return out, sum(h for _, h, _ in out)


def draw_title(d: ImageDraw.ImageDraw, lines, cx: float, y: float) -> None:
    tr = TITLE_STYLE["track"]
    for segs, h, top in lines:
        big = max((fi for _, fi in segs), key=lambda q: q.size)
        sp = big.getlength(" ") + 2 * tr * big.size
        w = sum(_width(fi, t, tr) for t, fi in segs) + sp * (len(segs) - 1)
        x = cx - w / 2
        base = y + h / 2 + 0.36 * top                       # centre the line on its cap height
        for t, fi in segs:
            if tr:
                _draw_tracked(d, x + _width(fi, t, tr) / 2, base, t, fi, 255, tr, anchor="ls")
            else:
                d.text((x, base), t, font=fi, fill=255, anchor="ls")
            x += _width(fi, t, tr) + sp
        y += h


def fit_author(author: str, box_w: int):
    """The author line at the largest size that fits; a role ('Translated by') goes before the line
    drops below a readable size, and a long list of names becomes the first name '& OTHERS'."""
    track = AUTHOR_STYLE["track"]
    bare = re.sub(r"^(?:EDITED|TRANSLATED|COMPILED) BY ", "", author, flags=re.I)
    cands = [(author, _si(46)), (bare, _si(46)), (bare, _si(36))]
    if " & " in bare:
        cands.append((bare.split(" & ")[0] + (" & OTHERS" if AUTHOR_STYLE["upper"] else " & others"), _si(36)))
    for cand, floor in cands:
        for size in range(_si(72), floor - 1, -_si(2)):
            font = _styled_font(AUTHOR_STYLE, size)
            if _width(font, cand, track) <= box_w:
                return font, cand, track
    return _styled_font(AUTHOR_STYLE, _si(36)), bare[:36], track


def _draw_tracked(d: ImageDraw.ImageDraw, cx: float, y: float, s: str, font, fill, tracking: float, anchor: str = "la"):
    x = cx - _width(font, s, tracking) / 2
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill, anchor=anchor)
        x += font.getlength(ch) + tracking * font.size


# ---------------------------------------------------------------- material and light
# The cover is rendered as an object, not a flat print: a height map (board edges rounded over, a
# hinge groove beside the spine, foil pressed into the cloth) is lit from the
# top left over woven, slightly mottled cloth, and the foil gets a metallic sheen and glint.

HINGE_X = _s(46)                    # the hinge groove's distance from the spine edge
EDGE_R, EDGE_D = _s(26), _s(12)         # board edges: rounding radius and drop
INNER_RULES = False             # the faint inner frame and band rules (off: only the outer border)
TITLE_GOLD = False              # the engraved title is laid in gold foil instead of the theme's lettering color
GOLD = {"light": "#dcb767", "dark": "#e3c070"}   # bright, reflective gold; legibility comes from the cut, not the color
ENGRAVE_D = _s(8.0)                 # how deep the title is cut into the board (0: the shallow ink stamp)
ENGRAVE_SHADOW = _si(4)              # how far the walls' shadow falls across the cut (px on the master)
ENGRAVE_DARK = 0.45             # how dark that shadow is
OUTER_D = _s(9.0)                   # how deep the outer foil border is pressed into the board
BAND = "flat"                   # the title band: "flat", "raised" (stands off the board) or "deep" (pressed into it)
BAND_D = _s(7.0)                    # how far it stands out or sinks in
RULE_INK = 0.4                  # the border rules are a faint stamp: this much ink, the full pressed groove
DEBOSS = _s(3.0)                    # how deep the foil is pressed into the cloth
WEAVE_P = max(3.0, _s(10.0))                  # thread spacing of the cloth
# per edition: weave strength; light on slopes (multiplicative, additive); a broad luster where the
# light falls on the cloth; the foil's metallic sheen and glint. Dark cloth shows little shading by
# multiplication alone, so it leans on additive light, luster and a brighter glint.
TUNE = {"light": {"weave": 9.0, "light": (0.13, 12.0), "luster": 9.0, "sheen": 0.45, "spec": 130.0},
        "dark": {"weave": 10.0, "light": (0.14, 30.0), "luster": 24.0, "sheen": 0.50, "spec": 170.0}}


def _hex(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _blur(a: np.ndarray, r: float) -> np.ndarray:
    """Approximate Gaussian blur of a 2-D float array (three box passes)."""
    k = max(1, int(round(r)))
    out = a.astype(np.float32)
    n = 2 * k + 1
    for _ in range(3):
        for axis in (0, 1):
            pad = [(k + 1, k) if ax == axis else (0, 0) for ax in range(2)]
            c = np.cumsum(np.pad(out, pad, mode="edge"), axis=axis, dtype=np.float32)
            out = ((c[n:] - c[:-n]) if axis == 0 else (c[:, n:] - c[:, :-n])) / n
    return out


def _shade(h: np.ndarray) -> np.ndarray:
    """Slope toward the light (top left): positive faces the light, negative turns away."""
    gy, gx = np.gradient(h)
    return np.clip(gx + gy, -3, 3)


def _light(col: np.ndarray, s: np.ndarray, edition: str) -> np.ndarray:
    k, add = TUNE[_mode(edition)]["light"]
    return col * (1 + k * s)[..., None] + (add * s)[..., None]


_MAT: dict[str, dict] = {}


_FIELDS: dict[str, np.ndarray] = {}


def _fields() -> dict[str, np.ndarray]:
    """The theme-independent textures, made once: weave, mottle, light falloff, foil sheen and grain,
    and the board's relief (rounded edges, the hinge)."""
    if _FIELDS:
        return _FIELDS
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x, y = np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32)
    warp = np.cos(2 * np.pi * x / WEAVE_P)[None, :] * (1 + 0.35 * rng.normal(0, 1, W).astype(np.float32))[None, :]
    weft = np.cos(2 * np.pi * y / WEAVE_P)[:, None] * (1 + 0.35 * rng.normal(0, 1, H).astype(np.float32))[:, None]
    over = np.sign(np.cos(np.pi * x / WEAVE_P)[None, :] * np.cos(np.pi * y / WEAVE_P)[:, None])
    weave = 0.5 * (warp + weft) + 0.3 * over * (warp - weft)
    weave = weave + 0.5 * rng.normal(0, 1, (H, W)).astype(np.float32)
    weave /= weave.std()
    mottle = _blur(rng.normal(0, 1, (H // 8, W // 8)).astype(np.float32), 6)
    mottle = mottle / (np.abs(mottle).max() + 1e-6)
    mottle = np.asarray(Image.fromarray(mottle, "F").resize((W, H), Image.BILINEAR), dtype=np.float32)
    vign = 1.04 - 0.08 * (0.6 * xx / W + 0.4 * yy / H) - 0.12 * ((xx / W - 0.45) ** 2 + (yy / H - 0.45) ** 2)
    pool = np.exp(-((xx / W - 0.22) ** 2 + (yy / H - 0.18) ** 2) / 0.16)
    sheen = 0.5 + 0.5 * np.cos(2 * np.pi * (0.62 * xx + 0.38 * yy) / (1.25 * W) + 0.8) + 0.25 * mottle
    grain = 1 + 0.025 * rng.normal(0, 1, (H, W)).astype(np.float32)
    d = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
    relief = -EDGE_D * np.clip(1 - d / EDGE_R, 0, 1) ** 2
    relief += _s(-4.0) * np.exp(-((xx - HINGE_X) / _s(7)) ** 2) + _s(1.5) * np.exp(-((xx - HINGE_X - _s(16)) / _s(9)) ** 2)
    relief += _s(2.5) * np.exp(-((xx - HINGE_X / 2) / (HINGE_X / 3)) ** 2)        # the spine side rounds over
    _FIELDS.update({k: v.astype(np.float32) for k, v in dict(weave=weave, mottle=mottle, vign=vign, pool=pool,
                                                              sheen=sheen, grain=grain, relief=relief).items()})
    return _FIELDS


def _material(edition: str) -> dict:
    """Per theme: the cloth (woven, mottled, falling off from the light) and the foil's color field
    (a metallic sheen), plus the shared board relief. Kept for the few most recent themes."""
    if edition in _MAT:
        return _MAT[edition]
    f = _fields()
    tune = TUNE[_mode(edition)]
    cloth = np.array(_hex(EDITIONS[edition][0]), np.float32)
    cloth_lit = (cloth[None, None, :] + (tune["weave"] * f["weave"] + 5.0 * f["mottle"]
                                         + tune["luster"] * f["pool"])[..., None]) * f["vign"][..., None]
    foil = np.array(_hex(EDITIONS[edition][1]), np.float32)
    foilf = foil[None, None, :] * ((1 - tune["sheen"] / 2 + tune["sheen"] * f["sheen"]) * f["vign"] * f["grain"])[..., None]
    if len(_MAT) >= 4:
        _MAT.pop(next(iter(_MAT)))
    text = THEMES[edition].get("text")                      # lettering in its own color, or in the foil
    textf = foilf if not text else np.array(_hex(text), np.float32)[None, None, :] * (
        (0.94 + 0.12 * f["sheen"]) * f["vign"] * f["grain"])[..., None]
    foil2 = THEMES[edition].get("foil2")
    foil2f = foilf if not foil2 else np.array(_hex(foil2), np.float32)[None, None, :] * (
        (1 - tune["sheen"] / 2 + tune["sheen"] * f["sheen"]) * f["vign"] * f["grain"])[..., None]
    # polished foil: broad diagonal bands of reflected light sweep across the letters, so the gold reads
    # as metal (bright where it faces the light, deep amber in the troughs)
    goldf = textf
    if TITLE_GOLD:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        band = 0.5 + 0.5 * np.cos(2 * np.pi * (0.78 * xx + 0.42 * yy) / (0.42 * W) + 1.1)
        band = band ** 2.2 + 0.18 * f["mottle"]
        goldf = np.array(_hex(GOLD[_mode(edition)]), np.float32)[None, None, :] * (
            (0.52 + 0.80 * band) * f["vign"] * (1 + 0.04 * (f["grain"] - 1) * 12))[..., None]
    _MAT[edition] = {"cloth": cloth_lit.astype(np.float32), "foil": foilf.astype(np.float32),
                     "foil2": foil2f.astype(np.float32), "text": textf.astype(np.float32),
                     "gold": goldf.astype(np.float32), "relief": f["relief"]}
    return _MAT[edition]


_G = INSET + _si(20)                                              # the inner rule
_INNER_TOP, _INNER_BOT = _G, H - _G
_AUTHOR_TOP = _INNER_BOT - int(AUTHOR_BAND * (_INNER_BOT - _INNER_TOP))
_PANEL_INSET = _si(60)                                            # title panel's side margin inside the inner rule
_BASES: dict[tuple, np.ndarray] = {}


def _stamp(col, region_h, layers, edition):
    """Stamp each (alpha, color field, glint) layer into col, then light the whole region from its
    height map; slopes facing the light glint in proportion to each layer's glint."""
    for a, field, _ in layers:
        col = col * (1 - a[..., None]) + field * a[..., None]
    s = _shade(region_h)
    col = _light(col, s, edition)
    glint = np.clip(s, 0, 2) ** 1.5
    for a, _, spec in layers:
        col = col + (spec * glint * a)[..., None]
    return col


def _foil_pass(col, region_h, foil_a, mat_foil, edition):
    return _stamp(col, region_h, [(foil_a, mat_foil, TUNE[_mode(edition)]["spec"])], edition)


def _engrave(col, a, field, edition, metal: bool = False):
    """The title cut into the board: a deep, sharp-walled groove with the ink lying in its floor. The
    letters' top and left walls throw a shadow onto the floor; their bottom and right edges catch the light."""
    if ENGRAVE_D <= 0:
        return _text_pass(col, -DEBOSS * _blur(a, _s(1.5)), a, field, edition)
    col = col * (1 - a[..., None]) + field * a[..., None]
    sh = np.zeros_like(a)                                   # the floor in the lee of the top-left walls
    o = ENGRAVE_SHADOW
    sh[o:, o:] = 1 - a[:-o, :-o]
    shadow = np.clip(_blur(sh, _s(1.2)), 0, 1) * a
    col = col * (1 - ENGRAVE_DARK * shadow)[..., None]
    k, add = TUNE[_mode(edition)]["light"]
    s = _shade(-ENGRAVE_D * _blur(a, _s(0.9)))
    col = col * (1 + 1.6 * k * s)[..., None] + (1.6 * add * s)[..., None]
    if metal:                                               # foil in the floor of the cut catches the light hard
        lip = np.clip(_shade(-ENGRAVE_D * _blur(a, 2.0)), 0, 3)     # the far walls, facing the light
        col = col + (95.0 * lip ** 1.3 * a)[..., None]
        floor = _blur(a, 3.0) * a                                    # the open middle of each stroke
        col = col + (28.0 * floor)[..., None]
    return col


def _text_pass(col, region_h, a, field, edition):
    """Title, panel frame and author: the foil, or a pigment (satin glint) when the theme letters in its own color."""
    spec = TUNE[_mode(edition)]["spec"] if not THEMES[edition].get("text") else 40.0
    return _stamp(col, region_h, [(a, field, spec)], edition)


def _grid() -> tuple[float, float, float, int]:
    """The pattern's half-drop grid: left edge, cell size, top, rows. Motif centers fall on 'levels'
    every half cell: level k is y = top + (k + 1) * cell / 2 (even columns on even k, odd on odd k)."""
    x0, x1 = _G + _s(24), W - _G - _s(24)
    y0, y1 = _G + _s(24), _AUTHOR_TOP - _s(24)
    cell = (x1 - x0) / COLS
    rows = int((y1 - y0) // cell)
    return x0, cell, y0 + ((y1 - y0) - rows * cell) / 2, rows


def _level_y(k: int) -> float:
    _x0, cell, top, _rows = _grid()
    return top + (k + 1) * cell / 2


def _base(motif: Image.Image, edition: str, gap: tuple[int, int] | None = None) -> np.ndarray:
    """Cloth, rules and the all-over pattern, lit: everything but the lettering. gap = (a, b) leaves
    pattern levels a..b empty for the title, with a faint rule at each edge. The same for every book
    that shares a motif, theme and gap, so it's built once and copied."""
    key = (motif.info.get("key") or id(motif), edition, gap)  # set info["key"]: ids are reused once an image is freed
    if key in _BASES:
        return _BASES[key]
    if len(_BASES) >= 16:                                     # each base is ~11 MB; keep only the recent few
        _BASES.pop(next(iter(_BASES)))
    mat = _material(edition)
    outer = Image.new("L", (W, H), 0)                         # the outer border: a heavy rule in the pattern's foil
    ImageDraw.Draw(outer).rectangle((INSET, INSET, W - INSET, H - INSET), outline=255, width=_si(6))
    rules = Image.new("L", (W, H), 0)                         # the inner rules: faint, in the neutral
    d = ImageDraw.Draw(rules)
    if INNER_RULES:                                           # faint rules: inner frame, author band, title band
        d.rectangle((_G, _G, W - _G, H - _G), outline=255, width=_si(2))
        d.line((_G, _AUTHOR_TOP, W - _G, _AUTHOR_TOP), fill=255, width=_si(2))
        if gap:
            for k in gap:
                y = round(_level_y(k))
                d.line((_G, y, W - _G, y), fill=255, width=_si(2))

    # a small motif in a half-drop grid over the whole field above the author band; odd columns
    # sit half a cell lower and are mirrored, like a printed binding cloth
    x0, cell, top, rows = _grid()
    size = int(MOTIF_FILL * cell)
    mw, mh = motif.size
    sc = size / max(mw, mh)
    m = motif.resize((max(1, int(mw * sc)), max(1, int(mh * sc))), Image.LANCZOS)
    mirrored = m.transpose(Image.FLIP_LEFT_RIGHT)
    solid = Image.new("L", m.size, 255)
    cols = [Image.new("L", (W, H), 0), Image.new("L", (W, H), 0)]   # even and odd columns: a two-color theme alternates
    for c in range(COLS):
        odd = c % 2 == 1
        for r in range(rows - 1 if odd else rows):
            k = 2 * r + (1 if odd else 0)
            if gap and gap[0] <= k <= gap[1]:
                continue
            cx = x0 + (c + 0.5) * cell
            cy = _level_y(k)
            cols[c % 2].paste(solid, (int(cx - m.width / 2), int(cy - m.height / 2)), mirrored if odd else m)
    a_outer, a_rules, a_even, a_odd = (np.asarray(im, dtype=np.float32) / 255 for im in (outer, rules, *cols))
    spec = TUNE[_mode(edition)]["spec"]
    rule_field, rule_spec = (mat["text"], 40.0) if THEMES[edition].get("text") else (mat["foil"], spec)
    h = (mat["relief"] - DEBOSS * _blur(np.maximum.reduce([a_rules, a_even, a_odd]), _s(1.5))
         - OUTER_D * _blur(a_outer, _s(2.5)))                     # the outer border is pressed deeper than the pattern
    col = _stamp(mat["cloth"], h, [(a_outer, mat["foil"], spec), (a_even, mat["foil"], spec), (a_odd, mat["foil2"], spec),
                                   (a_rules * RULE_INK, rule_field, rule_spec)], edition)
    _BASES[key] = np.clip(col, 0, 255).astype(np.uint8)
    return _BASES[key]


def build_cover(title: str, author: str, motif: Image.Image, edition: str = "light", inset: float = 0.0) -> Image.Image:
    """`inset` narrows the title's box on both sides, so it stays centered and clear of anything
    stamped near an edge (a studio folder's clasp)."""
    mat = _material(edition)

    # the title sits in a band where the pattern stops, between a faint rule above and below; the band
    # is snapped to the pattern's own rows so no motif is ever cut
    t, a = title, ((author or "").upper() if AUTHOR_STYLE["upper"] else (author or ""))   # already resolved by cover_text
    px0, px1 = int(_G + _s(24) + inset), int(W - _G - _s(24) - inset)
    pad_x, pad_y = _s(70), _s(56)
    if TITLE_STYLE["upper"]:
        t = t.upper()
    if SMALL_WORDS != "off":
        tlines, th = layout_title(t, (px1 - px0) - 2 * pad_x, _s(600))
    else:
        font, lines = fit_title(t, (px1 - px0) - 2 * pad_x, _s(560))
        lh = font.size * TITLE_STYLE["lh"]
        th = lh * len(lines)
    cy = H * (1 - TITLE_AT) - (_INNER_BOT - _AUTHOR_TOP)          # raised by the author band's height
    _x0, cell, top, rows = _grid()
    kmax = 2 * rows - 2
    ka = max(0, int(np.floor((cy - th / 2 - pad_y - top) / (cell / 2) - 1)))
    kb = min(kmax, int(np.ceil((cy + th / 2 + pad_y - top) / (cell / 2) - 1)))
    out = _base(motif, edition, (ka, kb)).copy()
    ya, yb = _level_y(ka), _level_y(kb)

    if BAND in ("raised", "deep"):                           # light the band as a raised or sunken panel
        rx0, rx1, ry0, ry1 = _G - 30, W - _G + 30, int(ya) - 60, int(yb) + 60
        bm = np.zeros((ry1 - ry0, rx1 - rx0), np.float32)
        bm[int(ya) - ry0:int(yb) - ry0, _G - rx0:W - _G - rx0] = 1
        sgn = 1 if BAND == "raised" else -1
        reg = out[ry0:ry1, rx0:rx1].astype(np.float32)
        sh = np.zeros_like(bm)                                # a soft shadow, down and to the right
        if BAND == "raised":
            sh[12:, 9:] = bm[:-12, :-9]
            reg *= (1 - 0.30 * _blur(sh, 9) * (1 - bm))[..., None]
        else:
            sh[12:, 9:] = 1 - bm[:-12, :-9]
            sh[:12, :] = 1
            sh[:, :9] = 1
            reg *= (1 - 0.26 * _blur(sh, 8) * bm)[..., None]
        reg = _light(reg, _shade(sgn * BAND_D * _blur(bm, 3)), edition)
        out[ry0:ry1, rx0:rx1] = np.clip(reg, 0, 255).astype(np.uint8)

    M = _si(8)
    by0, by1 = int(ya) + M, int(yb) - M
    bx0, bx1 = px0, px1
    tm = Image.new("L", (bx1 - bx0, by1 - by0), 0)
    d = ImageDraw.Draw(tm)
    y = (yb + ya) / 2 - th / 2 - by0
    if SMALL_WORDS != "off":
        draw_title(d, tlines, (bx1 - bx0) / 2, y)
        lines = []
    for line in lines:
        if TITLE_STYLE["track"]:
            _draw_tracked(d, (bx1 - bx0) / 2, y + lh / 2, line, font, 255, TITLE_STYLE["track"], anchor="lm")
        else:
            d.text(((bx1 - bx0) / 2, y + lh / 2), line, font=font, fill=255, anchor="mm")
        y += lh
    ta = np.asarray(tm, dtype=np.float32) / 255
    region = out[by0:by1, bx0:bx1].astype(np.float32)
    col = _engrave(region, ta, mat["gold" if TITLE_GOLD else "text"][by0:by1, bx0:bx1], edition, metal=TITLE_GOLD)
    out[by0:by1, bx0:bx1] = np.clip(col, 0, 255).astype(np.uint8)

    if a:
        afont, aline, track = fit_author(a, W - 2 * _G - _s(160))
        ax0, ay0, ax1, ay1 = _G + _si(4), _AUTHOR_TOP + _si(4), W - _G - _si(4), _INNER_BOT - _si(4)
        am = Image.new("L", (ax1 - ax0, ay1 - ay0), 0)
        ay = (_AUTHOR_TOP + (_INNER_BOT - _AUTHOR_TOP) / 2 - afont.size * 0.62) - ay0
        _draw_tracked(ImageDraw.Draw(am), (ax1 - ax0) / 2, ay, aline, afont, 255, track)
        aa = np.asarray(am, dtype=np.float32) / 255
        region = out[ay0:ay1, ax0:ax1].astype(np.float32)
        col = _text_pass(region, -DEBOSS * _blur(aa, _s(1.2)), aa, mat["text"][ay0:ay1, ax0:ax1], edition)
        out[ay0:ay1, ax0:ax1] = np.clip(col, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


# ---------------------------------------------------------------- Media Studio folders
# A studio folder is the house cover laid landscape (COVER_ASPECT below 1, COVER_AUTHOR_BAND 0): its
# name engraved as the title and no other words. A protected folder adds a diary lock in the same
# material: a strap in the binding's color, dyed deep like leather, raised off the cloth with pressed
# stitching, running off the fore-edge into a foil clasp plate with the keyhole cut into it. While the
# folder is open the clasp is undone: the strap is gone over the edge and only the foil catch remains.
CLASP_X, CLASP_W, CLASP_H, STRAP_H = 0.905, 0.07, 0.30, 0.15   # the plate's center and size, the strap's height (of W, H)


def _mask(draw) -> np.ndarray:
    im = Image.new("L", (W, H), 0)
    draw(ImageDraw.Draw(im))
    return np.asarray(im, dtype=np.float32) / 255


def build_folder(title: str, edition: str, state: str = "plain") -> Image.Image:
    """state: "plain", "locked" (strap fastened) or "open" (a protected folder, unfastened)."""
    px, pw, ph, sh, cy = CLASP_X * W, CLASP_W * W, CLASP_H * H, STRAP_H * H, H * 0.5
    inset = 0.0 if state == "plain" else max(0.0, (W - _G - _s(24)) - (px - pw / 2) + _s(20))   # title clear of the clasp
    base = np.asarray(build_cover(title, "", motif_image("universal"), edition, inset), dtype=np.float32)
    if state == "plain":
        return Image.fromarray(base.astype(np.uint8))
    mat = _material(edition)
    spec = TUNE[_mode(edition)]["spec"]
    if state == "open":                                  # only the catch: a small foil keeper with a slot
        kw, kh = pw * 0.62, ph * 0.46
        keeper = _mask(lambda d: d.rounded_rectangle((px - kw / 2, cy - kh / 2, px + kw / 2, cy + kh / 2), radius=kw * 0.3, fill=255))
        slot = _mask(lambda d: d.rounded_rectangle((px - kw * 0.14, cy - kh * 0.30, px + kw * 0.14, cy + kh * 0.30), radius=kw * 0.1, fill=255))
        shadow = np.zeros_like(keeper)
        shadow[5:, 4:] = keeper[:-5, :-4]
        base = base * (1 - 0.30 * _blur(shadow, 4) * (1 - keeper))[..., None]
        height = _s(9) * _blur(keeper, _s(1.6)) - _s(8) * _blur(slot, _s(0.8))
        out = _stamp(base, height, [(keeper, mat["foil"], spec), (slot, np.full_like(mat["foil"], 22.0), 0.0)], edition)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    strap = _mask(lambda d: d.rounded_rectangle((px, cy - sh / 2, W + 40, cy + sh / 2), radius=sh * 0.2, fill=255))
    stitch = _mask(lambda d: [d.line((x, y, x + W * 0.012, y), fill=255, width=2)
                              for y in (cy - sh * 0.32, cy + sh * 0.32)
                              for x in np.arange(px + pw * 0.6, W, W * 0.022)])
    plate = _mask(lambda d: d.rounded_rectangle((px - pw / 2, cy - ph / 2, px + pw / 2, cy + ph / 2), radius=pw * 0.28, fill=255))
    bevel = _mask(lambda d: d.rounded_rectangle((px - pw / 2 + 5, cy - ph / 2 + 5, px + pw / 2 - 5, cy + ph / 2 - 5),
                                                radius=pw * 0.22, outline=255, width=2))
    r = pw * 0.16
    key = _mask(lambda d: (d.ellipse((px - r, cy - ph * 0.10 - r, px + r, cy - ph * 0.10 + r), fill=255),
                           d.polygon([(px - r * 0.55, cy - ph * 0.10), (px + r * 0.55, cy - ph * 0.10),
                                      (px + r * 0.95, cy + ph * 0.20), (px - r * 0.95, cy + ph * 0.20)], fill=255)))
    strap = strap * (1 - plate)
    raised = np.maximum(strap, plate)                    # strap and plate stand off the board and cast a shadow
    shadow = np.zeros_like(raised)
    shadow[7:, 5:] = raised[:-7, :-5]
    base = base * (1 - 0.38 * _blur(shadow, 5) * (1 - raised))[..., None]
    height = (_s(10) * _blur(strap, _s(2.5)) + _s(14) * _blur(plate, _s(2.0)) - _s(4) * _blur(bevel, 1.2)
              - _s(10) * _blur(key, _s(1.0)) - _s(2.5) * _blur(stitch, 0.8))
    leather = mat["foil"] * 0.42 + mat["cloth"] * 0.18
    out = _stamp(base, height, [(strap, leather, 18.0), (stitch * strap, mat["foil"], 30.0),
                                (plate, mat["foil"], spec), (key, np.full_like(leather, 22.0), 0.0)], edition)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def render_folder(title: str, theme: str, state: str = "plain") -> Image.Image:
    if theme not in THEMES or state not in ("plain", "locked", "open"):
        raise KeyError((theme, state))
    with _RENDER_LOCK:
        use_fonts("house")
        return build_folder(title, theme, state)


# ---------------------------------------------------------------- the web renderer
# Covers drawn on request by the web app (webapp/house_cover.py): one book in one style. Styles are a
# theme key, a font set key and a motif key ("universal", or "<shelf-key>/<motif>" from the library).
import threading as _threading

RENDER_VERSION = "r2"           # bump when the design changes, so cached covers are redrawn
MOTIF_LIBRARY: dict[str, dict] = json.loads((MOTIFS / "library.json").read_text(encoding="utf-8"))
_MOTIF_IMG: dict[str, Image.Image] = {}
_RENDER_LOCK = _threading.Lock()   # the renderer's caches and font settings are module state


def motif_path(key: str) -> pathlib.Path:
    if key == "universal":
        return MOTIFS / "universal.png"
    if key not in MOTIF_LIBRARY:
        raise KeyError(key)
    return MOTIFS / "library" / f"{key}.png"


def motif_image(key: str) -> Image.Image:
    if key not in _MOTIF_IMG:
        m = Image.open(motif_path(key)).convert("L")
        m.info["key"] = key
        _MOTIF_IMG[key] = m
    return _MOTIF_IMG[key]


def shelf_motif(shelf: str | None) -> str:
    """A shelf's own motif: the first of its library motifs (the order in generate_motifs.SHELVES)."""
    if shelf:
        try:
            from generate_motifs import SHELVES
            for k in SHELVES.get(shelf, {}):
                mk = f"{_key(shelf)}/{k}"
                if mk in MOTIF_LIBRARY:
                    return mk
        except Exception:  # noqa: BLE001
            pass
    return "universal"


def render(title: str, author: str, theme: str, font: str, motif: str) -> Image.Image:
    if theme not in THEMES or font not in FONT_SETS or font.startswith("_"):
        raise KeyError((theme, font))
    with _RENDER_LOCK:
        use_fonts(font)
        return build_cover(title, author, motif_image(motif), theme)


# ---------------------------------------------------------------- commands
def cmd_motif(args):
    out = CACHE / "motifs" / args.name
    out.mkdir(parents=True, exist_ok=True)
    start = len(list(out.glob("raw-*.png")))
    for i in range(start, start + args.n):
        raw = draw_motif(args.subject, args.model)
        raw.save(out / f"raw-{i}.png")
        mask, st = to_mask(raw)
        mask.save(out / f"cand-{i}.png")
        print(f"cand-{i}: {st}")


def cmd_adopt(args):
    src = pathlib.Path(args.src)
    level = args.level
    dest = MOTIFS / (f"{level}.png" if level == "universal" else f"{level.split('/')[0]}/{_key(level.split('/', 1)[1])}.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("L").save(dest)
    print("adopted", dest.relative_to(_ROOT))


def _books(con, slugs=None, sample=0):
    q = "select slug, title, author, section from books where source != 'standardebooks'"
    rows = con.execute(q).fetchall()
    if slugs:
        want = set(slugs)
        rows = [r for r in rows if r[0] in want]
    elif sample:
        random.seed(args_seed)
        rows = random.sample(rows, sample)
    return rows


args_seed = 3


def _section(sec_json: str | None) -> str | None:
    try:
        s = json.loads(sec_json or "[]")
        return s[0] if s else None
    except Exception:  # noqa: BLE001
        return None


def cmd_render(args):
    global args_seed
    args_seed = args.seed
    con = sqlite3.connect(_ROOT / "db" / "books.db")
    rows = _books(con, args.slugs.split(",") if args.slugs else None, args.sample)
    out = CACHE / "out"
    out.mkdir(parents=True, exist_ok=True)
    cache: dict[pathlib.Path, Image.Image] = {}
    tiles = []
    texts = cover_texts()
    for slug, title, author, sec in rows:
        title, author = texts.get(slug, (title, author))
        mp = resolve_motif(slug, _section(sec))
        motif = cache.setdefault(mp, Image.open(mp).convert("L"))
        motif.info["key"] = str(mp)
        pair = []
        for ed in args.editions.split(","):
            im = build_cover(title, author, motif, ed)
            im.save(out / f"{slug}-{ed}.png")
            pair.append(im)
        tiles.append(pair)
        print(f"{slug}: {title} / {author}")
    if args.sheet and tiles:
        tw, th, gap = 300, 450, 24
        per_row = 8
        cells = [t for pair in tiles for t in pair]
        nrows = (len(cells) + per_row - 1) // per_row
        sheet = Image.new("RGB", (per_row * (tw + gap) + gap, nrows * (th + gap) + gap), (120, 118, 114))
        for i, im in enumerate(cells):
            r, c = divmod(i, per_row)
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (gap + c * (tw + gap), gap + r * (th + gap)))
        p = CACHE / "sheet.png"
        sheet.save(p)
        print("sheet:", p)


VERSION = "v2"
_REPLACE = ("gutenberg.org", "openlibrary.org", "archive.org")   # cover sources the house edition replaces


def scope(con_books, con_covers) -> list[tuple]:
    """Books whose current cover is Gutenberg's generated art, an Open Library photo, or nothing.
    Standard Ebooks and real art (pulp scans, Google Books) keep theirs. Admin overrides live in
    Neon and win at serve time, so they're not consulted here."""
    src = dict(con_covers.execute("select slug, src_url from covers"))
    out = []
    for slug, title, author, sec, url in con_books.execute(
            "select slug, title, author, section, cover_url from books where source != 'standardebooks'"):
        s = src.get(slug) or (url if (url or "").startswith("http") else "")
        if not s or any(h in s for h in _REPLACE):
            out.append((slug, title, author, sec, s))
    return out


_WM: dict[pathlib.Path, Image.Image] = {}


def _render_webps(job):
    import io
    slug, title, author, sec = job
    title, author = cover_texts().get(slug, (title, author))
    mp = resolve_motif(slug, _section(sec))
    motif = _WM.setdefault(mp, Image.open(mp).convert("L"))
    motif.info["key"] = str(mp)
    out = []
    for ed in ("light", "dark"):
        im = build_cover(title, author, motif, ed).resize((400, 600), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, "WEBP", quality=82, method=6)
        out.append(b.getvalue())
    return slug, out[0], out[1], str(mp.relative_to(MOTIFS)).replace("\\", "/")


def cmd_build(args):
    from concurrent.futures import ProcessPoolExecutor
    cb = sqlite3.connect(_ROOT / "db" / "books.db")
    cc = sqlite3.connect(_ROOT / "db" / "covers.db", timeout=120)
    cc.execute("""create table if not exists house_covers (
        slug text primary key, light blob not null, dark blob not null,
        motif text, ver text, replaced text, built_at text default current_timestamp)""")
    rows = scope(cb, cc)
    done = set() if args.force else {s for (s,) in cc.execute("select slug from house_covers where ver=?", (VERSION,))}
    todo = [r for r in rows if r[0] not in done]
    if args.limit:
        todo = todo[:args.limit]
    was = {r[0]: r[4] for r in rows}
    print(f"in scope: {len(rows)} | built: {len(done)} | to build: {len(todo)}", flush=True)
    n = 0
    with ProcessPoolExecutor(args.workers) as ex:
        for slug, light, dark, motif in ex.map(_render_webps, [r[:4] for r in todo], chunksize=16):
            cc.execute("insert or replace into house_covers(slug, light, dark, motif, ver, replaced) values (?,?,?,?,?,?)",
                       (slug, light, dark, motif, VERSION, was.get(slug) or ""))
            n += 1
            if n % 500 == 0:
                cc.commit()
                print(f"  {n}/{len(todo)}", flush=True)
    cc.commit()
    print(f"built {n}; house_covers rows: {cc.execute('select count(*) from house_covers').fetchone()[0]}")


MIN_TITLE = 120                 # the smallest title size (px on the 1600-wide master) that still reads on the shelf


def title_size(title: str) -> int:
    """The size the title panel would set this title at."""
    px0, px1 = int(_G + _s(24)), int(W - _G - _s(24))
    font, _lines = fit_title(title.upper() if TITLE_STYLE["upper"] else title, (px1 - px0) - 140, 560)
    return font.size


def cmd_review(args):
    """Every book's cover title and author beside the catalog's, for checking before a rebuild."""
    import csv
    con = sqlite3.connect(_ROOT / "db" / "books.db")
    rows = con.execute("select slug, title, author, source from books").fetchall()
    texts = cover_texts()
    mv = set()
    mvp = _ROOT / ".seed_cache" / "reading_room" / "multivolume_sets.csv"
    if mvp.exists():
        with open(mvp, encoding="utf-8-sig", newline="") as f:
            mv = {r["slug"] for r in csv.DictReader(f)}
    out = []
    for slug, title, author, src in rows:
        ct, ca = texts[slug]
        size = title_size(ct)
        out.append({"slug": slug, "source": src, "multivolume": "yes" if slug in mv else "",
                    "fits": "yes" if size >= MIN_TITLE else "NO", "title_size": size,
                    "title_changed": "yes" if ct != (title or "") else "", "author_changed": "yes" if ca != (author or "") else "",
                    "catalog_title": title, "cover_title": ct, "catalog_author": author, "cover_author": ca})
    out.sort(key=lambda r: (r["fits"] == "yes", r["title_size"]))
    p = CACHE / "cover_text_review.csv"
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    n = len(out)
    print(f"{n} books | title changed: {sum(r['title_changed'] == 'yes' for r in out)} | author changed: "
          f"{sum(r['author_changed'] == 'yes' for r in out)} | too long to fit: {sum(r['fits'] == 'NO' for r in out)} "
          f"(of which multi-volume: {sum(r['fits'] == 'NO' and r['multivolume'] == 'yes' for r in out)})")
    print("review sheet:", p)


def cmd_one(args):
    im = render(args.title, args.author, args.theme, args.font, args.motif).convert("RGB")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=92) if out.suffix.lower() in (".jpg", ".jpeg") else im.save(out)
    print(f"[cover] {out}  {im.size[0]}x{im.size[1]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("motif"); m.add_argument("--name", required=True); m.add_argument("--subject", required=True)
    m.add_argument("--n", type=int, default=2); m.add_argument("--model", default=MOTIF_MODEL)
    a = sub.add_parser("adopt"); a.add_argument("src"); a.add_argument("level", help="universal | section/<name> | subgenre/<key> | book/<slug>")
    r = sub.add_parser("render"); r.add_argument("--slugs"); r.add_argument("--sample", type=int, default=0)
    r.add_argument("--seed", type=int, default=3); r.add_argument("--editions", default="light,dark")
    r.add_argument("--sheet", action="store_true")
    b = sub.add_parser("build"); b.add_argument("--limit", type=int, default=0)
    b.add_argument("--workers", type=int, default=8); b.add_argument("--force", action="store_true")
    sub.add_parser("review")
    o = sub.add_parser("one", help="one cover for any title (e.g. a printed book); set COVER_ASPECT for its page shape")
    o.add_argument("--title", required=True); o.add_argument("--author", default="")
    o.add_argument("--theme", default="light"); o.add_argument("--font", default="house")
    o.add_argument("--motif", default="universal"); o.add_argument("--out", required=True)
    args = ap.parse_args()
    {"motif": cmd_motif, "adopt": cmd_adopt, "render": cmd_render, "build": cmd_build, "review": cmd_review,
     "one": cmd_one}[args.cmd](args)


if __name__ == "__main__":
    main()
