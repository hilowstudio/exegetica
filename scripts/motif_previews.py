"""One preview page per library motif: its light and dark cloth covers side by side, large and clean,
each lettered with a real title from that motif's shelf.

    .venv\\Scripts\\python.exe scripts\\motif_previews.py            # all motifs
    .venv\\Scripts\\python.exe scripts\\motif_previews.py --shelf Poetry
Pages land in .seed_cache/house_covers/previews/<shelf>/<motif>.png
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sqlite3
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import house_covers as hc  # noqa: E402
import generate_motifs as g  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = hc.CACHE / "previews"
CW, CH = 800, 1200                 # each cover on the page
PAD, CAP = 60, 70                  # page margin; caption band above the covers


def _sample_titles() -> dict[str, list[tuple[str, str]]]:
    """Per shelf, a shuffled list of real (cover title, author) pairs that set well on a cover."""
    con = sqlite3.connect(hc._ROOT / "db" / "books.db")
    texts = hc.cover_texts()
    by: dict[str, list] = {}
    for slug, genres in con.execute("select slug, genres from books where source != 'standardebooks'"):
        t, a = texts.get(slug, ("", ""))
        if not t or not a or not (8 <= len(t) <= 40) or " and others" in a:
            continue
        for sec in json.loads(genres or "[]")[:1]:
            by.setdefault(sec, []).append((t, a))
    rng = random.Random(7)
    for v in by.values():
        rng.shuffle(v)
    return by


def _page(job) -> str:
    shelf, key, title, author = job
    mk = f"{hc._key(shelf)}/{key}"
    motif = Image.open(g.LIB / f"{mk}.png").convert("L")
    motif.info["key"] = mk
    page = Image.new("RGB", (PAD * 3 + CW * 2, PAD * 2 + CAP + CH), (226, 222, 214))
    for i, ed in enumerate(("light", "dark")):
        cover = hc.build_cover(title, author, motif, ed).resize((CW, CH), Image.LANCZOS)
        page.paste(cover, (PAD + i * (CW + PAD), PAD + CAP))
    d = ImageDraw.Draw(page)
    f = ImageFont.truetype(str(hc.FONTS / "IBMPlexMono-Medium.ttf"), 26)
    subject = g.SHELVES[shelf][key]
    d.text((PAD, PAD - 6), f"{shelf.upper()}  ·  {key}", font=f, fill=(60, 56, 52))
    d.text((PAD, PAD + 30), subject, font=ImageFont.truetype(str(hc.FONTS / "IBMPlexMono-Medium.ttf"), 20), fill=(120, 114, 106))
    out = OUT / hc._key(shelf) / f"{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    page.save(out, optimize=True)
    return str(out.relative_to(hc._ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shelf")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--missing", action="store_true", help="only motifs without a preview page yet")
    args = ap.parse_args()
    titles = _sample_titles()
    jobs = []
    for shelf, motifs in g.SHELVES.items():
        if args.shelf and shelf != args.shelf:
            continue
        pool = titles.get(shelf) or [("The Sample Title", "Author Name")]
        for i, key in enumerate(motifs):
            if args.missing and (OUT / hc._key(shelf) / f"{key}.png").exists():
                continue
            if (g.LIB / f"{hc._key(shelf)}/{key}.png").exists():
                t, a = pool[i % len(pool)]
                jobs.append((shelf, key, t, a))
    print(f"rendering {len(jobs)} preview pages", flush=True)
    with ProcessPoolExecutor(args.workers) as ex:
        for p in ex.map(_page, jobs):
            print(" ", p, flush=True)


if __name__ == "__main__":
    main()
