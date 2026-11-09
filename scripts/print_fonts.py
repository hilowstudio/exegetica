"""Fonts and original languages for the offline PDF builders (scripts/course_pdf.py, scripts/book_pdf.py).

The builders render HTML in headless Chromium with no server. This module gives them:

  embedded(sheets)   the self-hosted font sheets in webapp/static/fonts/<sheet>.css with every font file
                     inlined as a data URI, so a render never fetches anything (decision 0013, rule H11)
  LANG_CSS           how tagged Greek and Hebrew are set (rule G6)
  tag_languages(html) the same tagging the pages get from Shell.tagLanguages in webapp/static/js/shell.js:
                     each Greek run becomes <span lang="grc" class="orig">, each Hebrew run
                     <span lang="he" dir="rtl" class="orig">, outside tags, code, styles and runs already tagged
"""
from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "webapp" / "static" / "fonts"

GREEK = "\u0370-\u03FF\u1F00-\u1FFF"
HEBREW = "\u0590-\u05FF\uFB1D-\uFB4F"
RUN = re.compile(rf"([{GREEK}](?:[{GREEK}\u0300-\u036F\u00B7\u2019']|\s(?=[{GREEK}]))*)"
                 rf"|([{HEBREW}](?:[{HEBREW}]|\s(?=[{HEBREW}]))*)")
SKIP = {"script", "style", "title", "code", "pre", "textarea", "svg", "math"}
TAG = re.compile(r"(<[^>]*>)")
NAME = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9]+)")

# Neither subset holds the space, so the builders' own text faces follow to supply it.
LANG_CSS = (':lang(grc){font-family:"Exegetica Greek","EB Garamond","Source Serif 4",serif}'
            ':lang(he){font-family:"Exegetica Hebrew","EB Garamond","Source Serif 4",serif;font-size:1.12em;line-height:1}')


@lru_cache(maxsize=None)
def _data_uri(path: str) -> str:
    return "data:font/woff2;base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def embedded(sheets: tuple[str, ...], families: tuple[str, ...] | None = None) -> str:
    """The named sheets (e.g. ("reader", "orig")) with each url(/static/fonts/pages/...) inlined. With
    `families`, only those faces are kept, so a builder embeds just what it sets."""
    out = []
    for sheet in sheets:
        css = (FONTS / f"{sheet}.css").read_text(encoding="utf-8")
        if families:
            keep = [b for b in re.findall(r"(?:/\*[^*]*\*/\s*)?@font-face\s*\{[^}]*\}", css)
                    if any(f"'{f}'" in b or f'"{f}"' in b for f in families)]
            css = "\n".join(keep)
        css = re.sub(r"url\((/static/fonts/[^)]+)\)",
                     lambda m: f"url({_data_uri(str(ROOT / 'webapp' / m.group(1).lstrip('/')))})", css)
        if re.search(r"url\(\s*['\"]?https?://", css):   # the header comment may name Google; a url() may not
            raise ValueError(f"{sheet}.css still fetches a font from the network")
        out.append(css)
    return "\n".join(out)


def _wrap(text: str) -> str:
    def span(m: re.Match) -> str:
        if m.group(1):
            return f'<span lang="grc" class="orig">{m.group(0)}</span>'
        return f'<span lang="he" dir="rtl" class="orig">{m.group(0)}</span>'
    return RUN.sub(span, text)


def tag_languages(html: str) -> str:
    """Tag Greek and Hebrew runs in an HTML string, leaving tags, attributes, code and styles alone."""
    parts, skipping, out = TAG.split(html), [], []
    for part in parts:
        if part.startswith("<"):
            m = NAME.match(part)
            if m:
                closing, name = m.group(1) == "/", m.group(2).lower()
                orig = 'class="orig"' in part
                if closing and skipping and skipping[-1] == name:
                    skipping.pop()
                elif not closing and not part.rstrip().endswith("/>") and (name in SKIP or (name == "span" and orig)):
                    skipping.append(name)
            out.append(part)
        else:
            out.append(part if skipping else _wrap(part))
    return "".join(out)
