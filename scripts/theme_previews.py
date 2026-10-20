"""Preview the cover color themes (assets/cover-themes.json).

    .venv\\Scripts\\python.exe scripts\\theme_previews.py
Writes .seed_cache/house_covers/themes/<mode>/<theme>.png (two covers per page: the library sprig and
a shelf motif) and an overview sheet per mode, .seed_cache/house_covers/themes/<mode>.png.
"""
from __future__ import annotations

import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import house_covers as hc  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = hc.CACHE / "themes"
CW, CH, PAD, CAP = 800, 1200, 60, 70
SAMPLES = [("universal.png", "The Wind in the Willows", "Kenneth Grahame"),
           ("library/fantasy/winged-key.png", "The Princess and the Goblin", "George MacDonald")]


def _motif(rel: str) -> Image.Image:
    m = Image.open(hc.MOTIFS / rel).convert("L")
    m.info["key"] = rel
    return m


def _page(theme: str) -> tuple[str, str]:
    t = hc.THEMES[theme]
    page = Image.new("RGB", (PAD * 3 + CW * 2, PAD * 2 + CAP + CH), (226, 222, 214))
    for i, (rel, title, author) in enumerate(SAMPLES):
        cover = hc.build_cover(title, author, _motif(rel), theme).resize((CW, CH), Image.LANCZOS)
        page.paste(cover, (PAD + i * (CW + PAD), PAD + CAP))
    d = ImageDraw.Draw(page)
    d.text((PAD, PAD - 6), f"{t['group'].upper()}  ·  {t['name']}", font=ImageFont.truetype(str(hc.FONTS / "IBMPlexMono-Medium.ttf"), 26), fill=(60, 56, 52))
    d.text((PAD, PAD + 30), f"cloth {t['cloth']}   foil {t['foil']}   ({theme})",
           font=ImageFont.truetype(str(hc.FONTS / "IBMPlexMono-Medium.ttf"), 20), fill=(120, 114, 106))
    out = OUT / t["group"] / f"{theme}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    page.save(out, optimize=True)
    return theme, str(out)


def _sheet(mode: str, keys: list[str]):
    tw, th, gap, lab, cols = 300, 450, 22, 34, 6
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (gap + cols * (tw + gap), gap + rows * (th + lab + gap)), (226, 222, 214))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(str(hc.FONTS / "IBMPlexMono-Medium.ttf"), 16)
    for i, k in enumerate(keys):
        page = Image.open(OUT / mode / f"{k}.png")
        cover = page.crop((PAD, PAD + CAP, PAD + CW, PAD + CAP + CH)).resize((tw, th), Image.LANCZOS)
        r, c = divmod(i, cols)
        x, y = gap + c * (tw + gap), gap + r * (th + lab + gap)
        sheet.paste(cover, (x, y))
        d.text((x, y + th + 8), f"{i + 1}. {hc.THEMES[k]['name']}", font=f, fill=(40, 40, 40))
    sheet.save(OUT / f"{mode}.png", optimize=True)


def main():
    spec = json.loads((hc._ROOT / "assets" / "cover-themes.json").read_text(encoding="utf-8"))
    groups = [g for g in spec if not g.startswith("_") and (len(sys.argv) < 2 or g in sys.argv[1:])]
    keys = [k for g in groups for k in spec[g]]
    with ProcessPoolExecutor(6) as ex:
        for theme, p in ex.map(_page, keys):
            print(" ", p, flush=True)
    for mode in groups:
        _sheet(mode, list(spec[mode]))
        print("sheet:", OUT / f"{mode}.png")


if __name__ == "__main__":
    main()
