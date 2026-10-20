"""One cover per font set (assets/cover-font-sets.json), in the house theme, each on a motif and a title
from the first shelf it suits; plus a glyph check of the characters real titles use.

    .venv\\Scripts\\python.exe scripts\\font_previews.py
Writes .seed_cache/house_covers/fonts/<NN>-<set>.png and prints any missing glyphs per face.
"""
from __future__ import annotations

import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import house_covers as hc  # noqa: E402
from cover_text import cover_title  # noqa: E402
from PIL import Image  # noqa: E402

OUT = hc.CACHE / "fonts"
SIZE = (1000, 1500)
TEST = "&’“”—–éèêëàâçñöüóáíúÉ"            # punctuation and accents that real catalog titles and authors use
SAMPLE = {
    "all": ("The Wind in the Willows", "Kenneth Grahame", "universal.png"),
    "Romance": ("Pride and Prejudice", "Jane Austen", "library/romance/honeysuckle.png"),
    "Literary & Classics": ("Wuthering Heights", "Emily Brontë", "library/literary-classics/ornate-key.png"),
    "Mystery & Crime": ("The Hound of the Baskervilles", "Arthur Conan Doyle", "library/mystery-crime/escutcheon.png"),
    "Short Stories": ("Dubliners", "James Joyce", "library/short-stories/fleuron.png"),
    "Philosophy": ("Meditations", "Marcus Aurelius", "library/philosophy/owl.png"),
    "Health & Medicine": ("Notes on Nursing", "Florence Nightingale", "library/health-medicine/foxglove.png"),
    "Children's": ("The Velveteen Rabbit", "Margery Williams", "library/children-s/kite.png"),
    "Fantasy": ("The Princess and the Goblin", "George MacDonald", "library/fantasy/dragon.png"),
    "Science Fiction": ("The War of the Worlds", "H. G. Wells", "library/science-fiction/diving-helmet.png"),
    "Horror & Gothic": ("Dracula", "Bram Stoker", "library/horror-gothic/hawkmoth.png"),
    "History": ("The Decline and Fall of the Roman Empire", "Edward Gibbon", "library/history/galleon.png"),
    "Society, Politics & Economics": ("The Wealth of Nations", "Adam Smith", "library/society-politics-economics/beehive.png"),
    "Science & Nature": ("On the Origin of Species", "Charles Darwin", "library/science-nature/ammonite.png"),
    "Poetry": ("Leaves of Grass", "Walt Whitman", "library/poetry/nightingale.png"),
    "Adventure": ("Treasure Island", "Robert Louis Stevenson", "library/adventure/ships-wheel.png"),
    "Christianity": ("The Pilgrim’s Progress", "John Bunyan", "library/christianity/vine.png"),
    "Biography & Memoir": ("Up from Slavery", "Booker T. Washington", "library/biography-memoir/pen-nib.png"),
    "Language & Reference": ("A Dictionary of the English Language", "Samuel Johnson", "library/language-reference/lectern.png"),
    "Travel & Places": ("Around the World in Eighty Days", "Jules Verne", "library/travel-places/balloon.png"),
    "Plays & Drama": ("The Importance of Being Earnest", "Oscar Wilde", "library/plays-drama/masquerade-mask.png"),
    "Art, Music & Performance": ("The Gentle Art of Making Enemies", "James McNeill Whistler", "library/art-music-performance/violin.png"),
    "Humor & Satire": ("Three Men in a Boat", "Jerome K. Jerome", "library/humor-satire/dodo.png"),
    "World Religions & Spirituality": ("The Song Celestial", "Edwin Arnold", "library/world-religions-spirituality/lotus.png"),
}


def missing_glyphs(file: str) -> str:
    from fontTools.ttLib import TTFont
    cmap = TTFont(str(hc.FONTS / file), lazy=True).getBestCmap()
    return "".join(ch for ch in TEST if ord(ch) not in cmap)


def _job(args):
    i, key = args
    fs = hc.FONT_SETS[key]
    t, a, motif = SAMPLE.get(fs["genres"][0], SAMPLE["all"])
    t, _ = cover_title(t, a)                            # the cover's own title rules (ampersands, trimming)
    hc.use_fonts(key)
    m = Image.open(hc.MOTIFS / motif).convert("L")
    m.info["key"] = motif
    out = OUT / f"{i:02d}-{key}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    hc.build_cover(t, a, m, "light").resize(SIZE, Image.LANCZOS).save(out, optimize=True)
    return key, str(out)


def main():
    keys = [k for k in hc.FONT_SETS if not k.startswith("_")]
    for k in keys:
        fs = hc.FONT_SETS[k]
        miss = {f: missing_glyphs(f) for f in {fs["title"]["file"], fs["author"]["file"]}}
        miss = {f: m for f, m in miss.items() if m}
        if miss:
            print(f"glyphs  {k:18} " + "  ".join(f"{f}: {m}" for f, m in miss.items()))
    with ProcessPoolExecutor(6) as ex:
        for key, p in ex.map(_job, list(enumerate(keys, 1))):
            print(" ", p, flush=True)


if __name__ == "__main__":
    main()
