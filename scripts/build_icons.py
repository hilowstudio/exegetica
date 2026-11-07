#!/usr/bin/env python3
"""Build Exegetica's browser and home-screen icons from one square source image.

Writes webapp/static/icons/: favicon.ico (16, 32 and 48 px), favicon-16/32/48.png, apple-touch-icon.png
(180 px, for iPhone and iPad home screens), and icon-192.png and icon-512.png (for the web app manifest
that Android home screens read). The source is kept at assets/brand/favicon-source.jpg.

    .venv/Scripts/python.exe scripts/build_icons.py [source image]

After a new source, bump ICON_VERSION in the pages' icon links so browsers drop the cached icon.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "brand" / "favicon-source.jpg"
OUT = ROOT / "webapp" / "static" / "icons"
PNGS = {"favicon-16.png": 16, "favicon-32.png": 32, "favicon-48.png": 48,
        "apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512}


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE
    im = Image.open(src).convert("RGB")   # opaque: iOS shows transparency as black
    if im.width != im.height:
        side = min(im.size)
        im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                      (im.width + side) // 2, (im.height + side) // 2))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in PNGS.items():
        im.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    im.resize((256, 256), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"built {len(PNGS) + 1} icons in {OUT.relative_to(ROOT)} from {src.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
