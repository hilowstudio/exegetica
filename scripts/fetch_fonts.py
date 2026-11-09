#!/usr/bin/env python3
"""
Self-host the course fonts. Downloads the exact .woff2 files Google Fonts serves
(Fraunces, Source Serif 4, Inter — all SIL OFL 1.1, free to self-host) into
webapp/static/fonts/, and writes:

  - webapp/static/fonts.css            @font-face rules (url form) for the web view
  - webapp/static/fonts/fonts.json     manifest the PDF renderer reads to base64-embed

With --pages it self-hosts the app pages' typefaces instead (Spectral, Public Sans,
IBM Plex Mono, and the Reading Room's EB Garamond, Literata, Fraunces and Libre
Baskerville), writing webapp/static/fonts/<sheet>.css and webapp/static/fonts/pages/.

With --orig it self-hosts the original-language faces every page loads: EB Garamond's
Greek (polytonic) as "Exegetica Greek" and Noto Serif Hebrew (vowel points and accents)
as "Exegetica Hebrew", both SIL OFL 1.1, writing webapp/static/fonts/orig.css. Their
unicode-range keeps them to Greek and Hebrew characters, so a page downloads them only
when one appears.

Re-run to refresh. Idempotent (skips files already present unless --force).

    python scripts/fetch_fonts.py [--pages] [--force]
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "webapp" / "static" / "fonts"
FONTS_CSS = ROOT / "webapp" / "static" / "fonts.css"
MANIFEST = FONTS_DIR / "fonts.json"

# Variable-range requests -> one variable woff2 per subset (keeps weights + optical
# sizes in a single file). Italic requested only where we use it (Source Serif body).
CSS2 = {
    "Fraunces": "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..700&display=swap",
    "Source Serif 4": "https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700&display=swap",
    "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400..700&display=swap",
}
# Only the subsets our English + ESV content needs (curly quotes, en/em dashes,
# middot live in 'latin'; accented Latin in 'latin-ext').
KEEP_SUBSETS = {"latin", "latin-ext"}
# A modern browser UA is required or css2 serves legacy ttf instead of woff2.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

BLOCK = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{([^}]*)\}", re.S)

# The app pages' typefaces: one stylesheet per distinct Google request the pages made, so
# each page keeps exactly the faces and weights it had. Every subset is kept, so a Greek,
# Cyrillic or Vietnamese character still renders in the typeface it did on Google's copy.
#   app: index, memory, generate, studio. The rest are one page each.
PAGE_SHEETS = {
    "app": "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap",
    "corpus": "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,500&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap",
    "covers": "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap",
    "library": "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap",
    # Printed documents (the Prep Room's PDF): EB Garamond text and Fraunces headings, as the books use.
    "doc": "https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..800,0..100;1,9..144,300..800,0..100&display=swap",
    "reader": "https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..800,0..100;1,9..144,300..800,0..100&family=Libre+Baskerville:ital@0;1&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap",
}
PAGE_FONTS = FONTS_DIR / "pages"
# Greek and Hebrew for every page, under names of their own so they never replace a page's faces.
ORIG = {
    "Exegetica Greek": ("https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800&display=swap",
                        {"greek", "greek-ext"}),
    "Exegetica Hebrew": ("https://fonts.googleapis.com/css2?family=Noto+Serif+Hebrew:wght@400..700&display=swap",
                         {"hebrew"}),
}
GSTATIC = re.compile(r"url\((https://fonts\.gstatic\.com/s/([^)]+\.woff2))\)")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def _field(body: str, name: str) -> str:
    m = re.search(rf"{name}\s*:\s*([^;]+);", body)
    return m.group(1).strip() if m else ""


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main(force: bool) -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for family, url in CSS2.items():
        css = _get(url)
        for subset, body in BLOCK.findall(css):
            if subset not in KEEP_SUBSETS:
                continue
            style = _field(body, "font-style") or "normal"
            weight = _field(body, "font-weight") or "400"
            urange = _field(body, "unicode-range")
            src = re.search(r"url\((https://[^)]+\.woff2)\)", body)
            if not src:
                continue
            fname = f"{_slug(family)}-{style}-{subset.replace('-', '')}.woff2"
            dest = FONTS_DIR / fname
            if force or not dest.exists():
                dest.write_bytes(urllib.request.urlopen(
                    urllib.request.Request(src.group(1), headers={"User-Agent": UA}),
                    timeout=30).read())
                print(f"[font] {fname}  ({dest.stat().st_size // 1024} KB)")
            else:
                print(f"[skip] {fname} (exists)")
            manifest.append({"family": family, "style": style, "weight": weight,
                             "subset": subset, "file": fname, "unicode_range": urange})

    # web-view stylesheet (url form)
    rules = []
    for e in manifest:
        rules.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;"
            "src:url('/static/fonts/%s') format('woff2');unicode-range:%s;}"
            % (e["family"], e["style"], e["weight"], e["file"], e["unicode_range"]))
    FONTS_CSS.write_text("/* Self-hosted course fonts (SIL OFL 1.1). Generated by "
                         "scripts/fetch_fonts.py — do not edit by hand. */\n"
                         + "\n".join(rules) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nwrote {FONTS_CSS.relative_to(ROOT)} ({len(manifest)} faces) + "
          f"{MANIFEST.relative_to(ROOT)}")


def pages(force: bool) -> None:
    """Google's stylesheet for each sheet, kept as served, with its font URLs pointed here."""
    PAGE_FONTS.mkdir(parents=True, exist_ok=True)
    fetched = 0
    for sheet, url in PAGE_SHEETS.items():
        def local(m: re.Match) -> str:
            nonlocal fetched
            fname = m.group(2).replace("/", "-")
            dest = PAGE_FONTS / fname
            if force or not dest.exists():
                dest.write_bytes(urllib.request.urlopen(
                    urllib.request.Request(m.group(1), headers={"User-Agent": UA}), timeout=30).read())
                fetched += 1
            return f"url(/static/fonts/pages/{fname})"

        css = GSTATIC.sub(local, _get(url))
        if "fonts.gstatic.com" in css or "fonts.googleapis.com" in css:
            raise SystemExit(f"{sheet}: a Google URL survived the rewrite")
        out = FONTS_DIR / f"{sheet}.css"
        out.write_text(f"/* Self-hosted page fonts (SIL OFL 1.1). Generated by scripts/fetch_fonts.py --pages\n"
                       f"   from {url} */\n" + css, encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({css.count('@font-face')} faces)")
    files = list(PAGE_FONTS.glob("*.woff2"))
    print(f"{fetched} downloaded, {len(files)} files, {sum(f.stat().st_size for f in files) // 1024} KB "
          f"in {PAGE_FONTS.relative_to(ROOT)}")


def orig(force: bool) -> None:
    """The Greek and Hebrew faces as webapp/static/fonts/orig.css, renamed so they only fill in."""
    PAGE_FONTS.mkdir(parents=True, exist_ok=True)
    blocks, fetched = [], 0
    for family, (url, keep) in ORIG.items():
        for subset, body in BLOCK.findall(_get(url)):
            if subset not in keep:
                continue
            m = GSTATIC.search(body)
            fname = m.group(2).replace("/", "-")
            dest = PAGE_FONTS / fname
            if force or not dest.exists():
                dest.write_bytes(urllib.request.urlopen(
                    urllib.request.Request(m.group(1), headers={"User-Agent": UA}), timeout=30).read())
                fetched += 1
            body = re.sub(r"font-family:[^;]+;", f"font-family: '{family}';", body)
            body = body.replace(m.group(1), f"/static/fonts/pages/{fname}")
            blocks.append(f"/* {family}, {subset} */\n@font-face {{{body}}}")
    css = "\n".join(blocks)
    if "fonts.gstatic.com" in css or "fonts.googleapis.com" in css:
        raise SystemExit("orig: a Google URL survived the rewrite")
    out = FONTS_DIR / "orig.css"
    out.write_text("/* Greek and Hebrew for every page (SIL OFL 1.1): EB Garamond's Greek as 'Exegetica Greek' and\n"
                   "   Noto Serif Hebrew as 'Exegetica Hebrew'. Generated by scripts/fetch_fonts.py --orig. */\n" + css + "\n",
                   encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(blocks)} faces, {fetched} downloaded)")


if __name__ == "__main__":
    if "--orig" in sys.argv:
        orig("--force" in sys.argv)
    elif "--pages" in sys.argv:
        pages("--force" in sys.argv)
    else:
        main("--force" in sys.argv)
