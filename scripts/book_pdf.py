#!/usr/bin/env python3
"""
Render a short book written in Markdown to a book-quality PDF.

A book is a folder of Markdown files (read in name order) plus a book.json with
title, subtitle, byline and output name (optional: running_head, edition, body_pt,
cover). Structure comes from the headings:

    # Part One: The Differences     -> part title page of its own
    ## What the Reader Sees          -> numbered chapter ("Chapter 1"), always on a new page
    ### An inventory                 -> section heading

An `##` before the first `#` is front matter (unnumbered, e.g. a preface); a part
titled "Back Matter" prints no opener and leaves its chapters unnumbered.

House interior (see project memory): EB Garamond text, Fraunces display,
Libre Baskerville tracked capitals; running head + folio via native @page margin
boxes (Edge/Chrome 131+). Fonts load from Google Fonts at render time.

Cover: "cover": {"theme": ..., "motif": ..., "font": "house"} draws a Reading Room house
cover (scripts/house_covers.py, the same cloth/motif/engraved-title design) at Letter
shape as a full-bleed first page, saved beside the book as cover.jpg, plus cover-2x3.jpg
at the Reading Room's 2:3 shape. As in the Reading Room, the interior follows the
cover: ornaments are the cover motif in the theme's foil and accents take its lettering color.
A dark cover theme lends the white pages a light theme instead ("interior", default the house
rose), as the reader does in light mode.

The contents page carries real page numbers from a two-pass render: pass one
stamps an invisible marker at each part/chapter, pypdf finds the page each
marker landed on, and pass two prints those numbers. Markers are absolutely
positioned, so both passes paginate identically.

Run:
    python scripts/book_pdf.py docs/reading-room/books/between-the-brackets
"""
from __future__ import annotations

import asyncio
import base64
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
MOTIFS = ROOT / "assets" / "cover-motifs"
LETTER_ASPECT = 11 / 8.5

_MD = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "smartquotes"])  # no "replacements": it turns "(C)" (Codex Ephraemi) into ©

_NUM_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
              "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen"]

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500"
         "&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600"
         "&family=Libre+Baskerville:wght@400;700&display=block")

CSS = r"""
:root{
  --ink:#1f1b16; --soft:#4a443c; --rule:#cfc6b8; --accent:#7b2d26; --faint:#8a8175;
}
@page{
  size:letter;
  margin:0.9in 1.45in 1.05in 1.45in;
  @top-center{content:"__RUNHEAD__"; font:7.5pt "Libre Baskerville",serif;
    letter-spacing:.22em; color:var(--faint);}
  @bottom-center{content:counter(page); font:9.5pt "EB Garamond",serif; color:var(--soft);}
}
@page :first{ @top-center{content:""} @bottom-center{content:""} }
@page contents{ @top-center{content:""} }
@page cover{ margin:0; @top-center{content:""} @bottom-center{content:""} }
@page plain{ @top-center{content:""} @bottom-center{content:""} }

/* -------------------------------------------------------------------- cover */
.cover{page:cover; width:8.5in; height:11in; margin:0; break-after:page;}
.cover img{display:block; width:8.5in; height:11in;}
.titlepage{page:plain}
.orn img{display:inline-block; vertical-align:middle;}
.titlepage .orn img{height:.5in}
.part-open .orn img{height:.38in}
.orn.orn-img{letter-spacing:0; margin-left:0; margin-right:0;}

*{box-sizing:border-box}
html{font-size:11.5pt}
body{margin:0; font-family:"EB Garamond","Times New Roman",serif; font-size:11.5pt;
  line-height:1.4; color:var(--ink); font-variant-numeric:oldstyle-nums;
  font-kerning:normal; font-feature-settings:"liga","kern";
  -webkit-print-color-adjust:exact; print-color-adjust:exact;
  hyphens:auto; text-align:justify; text-rendering:optimizeLegibility;}

/* ---------------------------------------------------------------- title page */
.titlepage{height:9.0in; display:flex; flex-direction:column; align-items:center;
  justify-content:center; text-align:center; break-after:page; hyphens:none;}
.titlepage .orn{color:var(--accent); font-size:15pt; letter-spacing:.6em; margin:0 0 .45in .6em;}
.titlepage h1{font-family:"Fraunces",serif; font-weight:500; font-size:36pt; line-height:1.05;
  letter-spacing:-.01em; margin:0 0 .22in; color:var(--ink);}
.titlepage .sub{font-style:italic; font-size:14.5pt; line-height:1.35; color:var(--soft);
  max-width:4.4in; margin:0 auto;}
.titlepage .rule{width:1.1in; border-top:.75pt solid var(--accent); margin:.42in auto;}
.titlepage .ed{font-family:"Libre Baskerville",serif; font-size:8pt; letter-spacing:.34em;
  text-transform:uppercase; color:var(--accent); margin-top:.3in;}
.titlepage .by{font-family:"Libre Baskerville",serif; font-size:8.5pt; letter-spacing:.3em;
  text-transform:uppercase; color:var(--soft);}

/* ------------------------------------------------------------------ contents */
.contents{page:contents; break-after:page; hyphens:none; text-align:left;}
.contents h2{font-family:"Libre Baskerville",serif; font-weight:400; font-size:10pt;
  letter-spacing:.32em; text-transform:uppercase; text-align:center; margin:.35in 0 .38in;}
.toc{list-style:none; margin:0; padding:0;}
.toc li{display:flex; align-items:baseline; margin:0; line-height:1.5;}
.toc .t{flex:0 1 auto;}
.toc .dots{flex:1 1 auto; border-bottom:.6pt dotted var(--rule); margin:0 .5em; transform:translateY(-.25em);}
.toc .p{flex:0 0 auto; font-variant-numeric:lining-nums tabular-nums; min-width:1.4em; text-align:right;}
.toc .part{margin-top:.62em; font-family:"Libre Baskerville",serif; font-size:7.8pt;
  letter-spacing:.2em; text-transform:uppercase; color:var(--accent);}
.toc .part .t{padding-top:.15em}
.toc .ch .n{display:inline-block; width:1.7em; color:var(--faint); font-variant-numeric:lining-nums;}
.toc .front{font-style:italic}

/* --------------------------------------------------------------------- parts */
/* Chromium ignores break-after:avoid, so each heading reserves ~4 lines beneath it
   (an unbreakable spacer cancelled by a negative margin): no visible gap, but a
   heading that would land in a page's last lines moves to the next page. */
.keep{break-inside:avoid}
.keep::after{content:""; display:block; height:4.6em; margin-bottom:-4.6em;}
h3{break-inside:avoid}
h3::after{content:""; display:block; height:4.4em; margin-bottom:-4.4em;}
/* back-matter subheads head short lists; there the spacer misfires and pushes the
   final section onto a page of its own, so it is switched off */
.back-matter h3::after{display:none}
/* back matter (glossary, reading list, sources) is set a size down, as books do */
.back-matter{font-size:.92em}
/* each part opens on a page of its own, no running head or folio, title centered */
.part-open{page:plain; break-before:page; break-after:page; height:9in; display:flex;
  flex-direction:column; justify-content:center; align-items:center; text-align:center; hyphens:none;}
.part-open .label{font-family:"Libre Baskerville",serif; font-size:9pt; letter-spacing:.34em;
  text-transform:uppercase; color:var(--accent);}
.part-open h1{font-family:"Fraunces",serif; font-weight:400; font-size:30pt; line-height:1.1;
  margin:.18in 0 0; color:var(--ink);}
.part-open .orn{color:var(--accent); font-size:12pt; letter-spacing:.5em; margin:.3in 0 0 .5em;}

/* ------------------------------------------------------------------ chapters */
/* every chapter (front and back matter too) starts a new page, set a little down */
.chapter{break-before:page; padding-top:.5in;}
.chapter .label{font-family:"Libre Baskerville",serif; font-size:7.6pt; letter-spacing:.3em;
  text-transform:uppercase; color:var(--accent); text-align:center; hyphens:none;}
.chapter h2{font-family:"Fraunces",serif; font-weight:500; font-size:17.5pt; line-height:1.15;
  text-align:center; margin:.05in 0 .2in; hyphens:none; break-after:avoid;}
.chapter h2::after{content:""; display:block; width:.55in; margin:.13in auto 0;
  border-top:.6pt solid var(--accent);}
h3{font-family:"Fraunces",serif; font-weight:500; font-style:normal; font-size:12pt;
  margin:1.05em 0 .25em; text-align:left; hyphens:none; break-after:avoid; color:var(--ink);}
h3 + p{text-indent:0}

p{margin:0; text-indent:1.4em; orphans:2; widows:2;}
h2 + p, h3 + p, .label + h2 + p, table + p, ul + p, ol + p, blockquote + p{text-indent:0}
/* the opening paragraph is never indented, so the drop cap sits close to the rest of its word */
p.lead{text-indent:0}
p.lead::first-letter{float:left; font-family:"Fraunces",serif; font-weight:400;
  font-size:3.05em; line-height:.84; padding:.02em .03em 0 0; color:var(--accent);}   /* box clears in two lines */
p.lead::first-line{font-variant:small-caps; letter-spacing:.04em;}
p.lead + *{clear:left}   /* a short opening paragraph must not leave the next block wrapping the drop cap */

.nw{white-space:nowrap; hyphens:none}
strong{font-weight:600}
em{font-style:italic}
blockquote{margin:.75em 1.6em; font-size:11pt; text-align:left;}
blockquote p{text-indent:0}
blockquote strong{font-weight:600; color:var(--accent);}

ul,ol{margin:.45em 0 .55em; padding-left:1.35em;}
ol{padding-left:1.6em}
li{margin:.18em 0; text-align:left;}
.reading ul{list-style:none; padding-left:1.4em; text-indent:-1.4em;}
.reading li{margin:.12em 0; hyphens:none;}

table{width:100%; border-collapse:collapse; margin:.8em 0 .9em; text-align:left; hyphens:none;
  font-size:9.6pt; line-height:1.3; font-variant-numeric:lining-nums;}
thead th{font-family:"Libre Baskerville",serif; font-weight:400; font-size:6.9pt;
  letter-spacing:.14em; text-transform:uppercase; color:var(--accent);
  border-bottom:.75pt solid var(--ink); padding:.3em .45em .35em; vertical-align:bottom;}
tbody td{padding:.3em .45em; border-bottom:.5pt solid var(--rule); vertical-align:top;}
tbody tr:last-child td{border-bottom:.75pt solid var(--ink);}
th:first-child, td:first-child{padding-left:0}
th:last-child, td:last-child{padding-right:0}
td:first-child{white-space:nowrap;}

.marker{position:absolute; font-size:4px; line-height:1; color:#fff; white-space:nowrap;}
blockquote, tr, li{break-inside:avoid}
thead{display:table-header-group}
h1,h2,h3,.label{break-after:avoid}
"""


def _split(md_text: str) -> list[dict]:
    """Split the joined Markdown into parts/chapters by heading level."""
    blocks: list[dict] = []
    part = None
    for line in md_text.splitlines():
        m1 = re.match(r"^# (.+)$", line)
        m2 = re.match(r"^## (.+)$", line)
        if m1:
            label, _, title = m1.group(1).partition(":")
            part = {"kind": "part", "label": label.strip(), "title": title.strip() or label.strip(),
                    "back": m1.group(1).strip().lower() == "back matter"}
            blocks.append(part)
        elif m2:
            blocks.append({"kind": "chapter", "title": m2.group(1).strip(), "body": [],
                           "front": part is None, "back": bool(part and part["back"])})
        elif blocks and blocks[-1]["kind"] == "chapter":
            blocks[-1]["body"].append(line)
    return blocks


def _smart(s: str) -> str:
    return _MD.renderInline(s)


_SHIFT = {"light": 0.30, "pastel": 0.60, "dark": 0.60, "dark-duo": 0.60}   # as in house_covers.SHIFT


def _theme(theme: str) -> dict:
    """A cover theme's foil, lettering color and mode (assets/cover-themes.json). The lettering is
    the foil darkened (light cloth) or lightened (dark cloth) by the group's shift, as on the covers."""
    key = {"light": "exegetica-rose", "dark": "exegetica-rose-dark"}.get(theme, theme)
    groups = json.loads((ROOT / "assets" / "cover-themes.json").read_text(encoding="utf-8"))
    for g, themes in groups.items():
        if not g.startswith("_") and key in themes:
            foil, mode = themes[key]["foil"], "dark" if g.startswith("dark") else "light"
            rgb = [int(foil[i:i + 2], 16) for i in (1, 3, 5)]
            amt = _SHIFT[g]
            rgb = [v * (1 - amt) if mode == "light" else v + (255 - v) * amt for v in rgb]
            return {"foil": foil, "text": "#%02x%02x%02x" % tuple(round(v) for v in rgb), "mode": mode}
    raise KeyError(theme)


def _render_cover(meta: dict, aspect: float, out: Path) -> None:
    """One house cover via scripts/house_covers.py, drawn at the given height/width shape."""
    c = meta["cover"]
    env = {**os.environ, "COVER_SCALE": "1", "COVER_ASPECT": f"{aspect:.6f}"}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "house_covers.py"), "one",
                    "--title", meta["title"], "--author", meta["byline"], "--theme", c["theme"],
                    "--font", c.get("font", "house"), "--motif", c["motif"], "--out", str(out)],
                   env=env, check=True)


def _ornament(motif: str, color: str) -> str:
    """The cover motif as a transparent PNG in the given color, as a data URI."""
    from PIL import Image
    src = MOTIFS / "universal.png" if motif == "universal" else MOTIFS / "library" / f"{motif}.png"
    alpha = Image.open(src).convert("L")                             # stored as a mask: 255 = ink
    alpha = alpha.crop(alpha.getbbox())
    alpha.thumbnail((300, 300))
    im = Image.new("RGBA", alpha.size, color)
    im.putalpha(alpha)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _decor(meta: dict, book_dir: Path) -> dict:
    """Cover page, ornament and accent for a book with a "cover" entry; empty otherwise."""
    if not meta.get("cover"):
        return {}
    letter, house = book_dir / "cover.jpg", book_dir / "cover-2x3.jpg"
    _render_cover(meta, LETTER_ASPECT, letter)
    _render_cover(meta, 1.5, house)
    # The pages are white, so they take a light theme's colors, as the reader does in light mode:
    # the cover's own theme when it is light, else "interior" (default: the house rose).
    c = meta["cover"]
    th = _theme(c["theme"])
    if th["mode"] == "dark":
        th = _theme(c.get("interior", "light"))
    return {"cover": "data:image/jpeg;base64," + base64.b64encode(letter.read_bytes()).decode("ascii"),
            "orn": _ornament(c["motif"], th["foil"]), "accent": th["text"]}


def _build(meta: dict, md_text: str, pages: dict[str, int] | None, markers: bool,
           decor: dict | None = None) -> str:
    decor = decor or {}
    orn_part = (f'<div class="orn orn-img"><img src="{decor["orn"]}" alt=""></div>' if decor.get("orn")
                else '<div class="orn">&#10086;</div>')
    orn_title = (f'<div class="orn orn-img"><img src="{decor["orn"]}" alt=""></div>' if decor.get("orn")
                 else '<div class="orn">&#10086; &#10086; &#10086;</div>')
    blocks = _split(md_text)
    toc, body = [], []
    n_ch = n_part = 0
    for b in blocks:
        if b["kind"] == "part":
            if b["back"]:
                continue
            n_part += 1
            key = f"P{n_part}"
            mk = f'<span class="marker">@@{key}@@</span>' if markers else ""
            body.append(f'<section class="part-open">{mk}<div class="label">{html.escape(b["label"])}</div>'
                        f'<h1>{_smart(b["title"])}</h1>{orn_part}</section>')
            toc.append(("part", key, b["label"] + " · " + b["title"], None))
            continue
        numbered = not (b["front"] or b["back"])
        if numbered:
            n_ch += 1
            key = f"C{n_ch}"
            label = f"Chapter {_NUM_WORDS[n_ch] if n_ch < len(_NUM_WORDS) else n_ch}"
        else:
            key = "F" + re.sub(r"\W+", "", b["title"])[:12]
            label = ""
        inner = _MD.render("\n".join(b["body"]))
        # pronunciation guides such as (ih-RAZ-mus) must not break at their hyphens
        inner = re.sub(r"\(((?:[A-Za-z]+-)+[A-Za-z]+)\)", r'<span class="nw">(\1)</span>', inner)
        # drop cap on the chapter's first paragraph
        if not b["back"]:
            inner = inner.replace("<p>", '<p class="lead">', 1)
        mk = f'<span class="marker">@@{key}@@</span>' if markers else ""
        cls = "chapter" + (" front-matter" if b["front"] else "") + (" back-matter reading" if b["back"] else "")
        lab = f'<div class="label">{label}</div>' if label else ""
        # chapter label + title travel as one unbreakable block (.keep)
        head = f'<div class="keep">{mk}{lab}<h2>{_smart(b["title"])}</h2></div>'
        body.append(f'<section class="{cls}">{head}{inner}</section>')
        toc.append(("ch", key, b["title"], n_ch if numbered else None))

    items = []
    for kind, key, title, num in toc:
        p = str(pages.get(key, "")) if pages else "00"
        if kind == "part":
            items.append(f'<li class="part"><span class="t">{_smart(title)}</span>'
                         f'<span class="dots"></span><span class="p">{p}</span></li>')
        else:
            n = f'<span class="n">{num}</span>' if num else ""
            cls = "ch" if num else "ch front"
            items.append(f'<li class="{cls}"><span class="t">{n}{_smart(title)}</span>'
                         f'<span class="dots"></span><span class="p">{p}</span></li>')

    edition = f'<div class="ed">{html.escape(meta["edition"])}</div>' if meta.get("edition") else ""
    # a "\n" in the subtitle sets where its lines break
    subtitle = "<br>".join(_smart(part) for part in meta["subtitle"].split("\n"))
    cover = f'<section class="cover"><img src="{decor["cover"]}" alt=""></section>' if decor.get("cover") else ""
    title_page = (f'<section class="titlepage">{orn_title}'
                  f'<h1>{_smart(meta["title"])}</h1><div class="sub">{subtitle}</div>'
                  f'{edition}<div class="rule"></div><div class="by">{html.escape(meta["byline"])}</div></section>')
    contents = f'<section class="contents"><h2>Contents</h2><ol class="toc">{"".join(items)}</ol></section>'
    css = CSS.replace("__RUNHEAD__", meta.get("running_head", meta["title"]).upper())
    if meta.get("body_pt"):   # e.g. a student edition set a size larger
        css = css.replace("font-size:11.5pt", f'font-size:{meta["body_pt"]}pt')
    if decor.get("accent"):   # the interior follows the cover style (lettering color; ornaments in the foil)
        css = css.replace("--accent:#7b2d26", f'--accent:{decor["accent"]}')
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(meta['title'])}</title>"
            f'<link rel="stylesheet" href="{FONTS}"><style>{css}</style></head><body>'
            f"{cover}{title_page}{contents}{''.join(body)}</body></html>")


async def _render(page, doc: str, out: Path) -> None:
    await page.set_content(doc, wait_until="networkidle")
    await page.evaluate("() => document.fonts.ready")
    await page.pdf(path=str(out), prefer_css_page_size=True, print_background=True,
                   tagged=True, outline=True)


def _marker_pages(pdf: Path) -> dict[str, int]:
    from pypdf import PdfReader
    found: dict[str, int] = {}
    for i, pg in enumerate(PdfReader(str(pdf)).pages, start=1):
        for key in re.findall(r"@@([A-Za-z0-9]+)@@", pg.extract_text() or ""):
            found.setdefault(key, i)
    return found


async def _run(book_dir: Path) -> Path:
    from playwright.async_api import async_playwright
    meta = json.loads((book_dir / "book.json").read_text(encoding="utf-8"))
    md_text = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted(book_dir.glob("*.md")))
    out = book_dir / meta["output"]
    decor = _decor(meta, book_dir)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / "probe.pdf"
            await _render(page, _build(meta, md_text, None, markers=True, decor=decor), probe)
            pages = _marker_pages(probe)
        await _render(page, _build(meta, md_text, pages, markers=False, decor=decor), out)
        await browser.close()
    from pypdf import PdfReader
    n = len(PdfReader(str(out)).pages)
    words = len(re.findall(r"\S+", md_text))
    print(f"[book] {out.relative_to(ROOT)}  {n} pages, {words} words")
    return out


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/book_pdf.py <book-folder>")
    asyncio.run(_run((ROOT / sys.argv[1]).resolve()))


if __name__ == "__main__":
    main()
