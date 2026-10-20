"""One cover per image for every color theme, each on a different library motif and a real title.

    .venv\\Scripts\\python.exe scripts\\theme_singles.py
Writes .seed_cache/house_covers/theme-singles/<group>/<NN>-<theme>.png
"""
from __future__ import annotations

import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import house_covers as hc  # noqa: E402
from PIL import Image  # noqa: E402

OUT = hc.CACHE / "theme-singles"
SIZE = (1000, 1500)
BOOKS = [("The Wind in the Willows", "Kenneth Grahame"), ("The Princess and the Goblin", "George MacDonald"),
         ("Treasure Island", "Robert Louis Stevenson"), ("The Secret Garden", "Frances Hodgson Burnett"),
         ("The War of the Worlds", "H. G. Wells"), ("Pride and Prejudice", "Jane Austen"),
         ("The Pilgrim's Progress", "John Bunyan"), ("Dracula", "Bram Stoker"),
         ("The Hound of the Baskervilles", "Arthur Conan Doyle"), ("Leaves of Grass", "Walt Whitman"),
         ("Twenty Thousand Leagues Under the Sea", "Jules Verne"), ("Little Women", "Louisa May Alcott")]


def _job(args):
    group, i, key, motif_rel = args
    t, a = BOOKS[i % len(BOOKS)]
    m = Image.open(hc.MOTIFS / motif_rel).convert("L")
    m.info["key"] = motif_rel
    out = OUT / group / f"{i + 1:02d}-{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    hc.build_cover(t, a, m, key).resize(SIZE, Image.LANCZOS).save(out, optimize=True)
    return str(out)


def main():
    spec = json.loads((hc._ROOT / "assets" / "cover-themes.json").read_text(encoding="utf-8"))
    motifs = sorted(json.loads((hc.MOTIFS / "library.json").read_text(encoding="utf-8")))
    motifs = ["universal.png"] + [f"library/{k}.png" for k in motifs[::7]]
    jobs, n = [], 0
    for group, themes in spec.items():
        if group.startswith("_"):
            continue
        for i, key in enumerate(themes):
            jobs.append((group, i, key, motifs[n % len(motifs)]))
            n += 1
    with ProcessPoolExecutor(6) as ex:
        for p in ex.map(_job, jobs, chunksize=4):
            print(p, flush=True)


if __name__ == "__main__":
    main()
