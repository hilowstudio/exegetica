#!/usr/bin/env python3
"""
Pilot: turn an Internet Archive pulp-magazine scan into clean story text.

Reads the item's ABBYY layout (paragraphs with positions) and IA's page-number map, drops the
furniture (running heads, folios, ads, letters), rejoins words hyphenated across lines, and cuts
the issue into stories using the FictionMags contents' start pages, following "(Continued on
page N)" jumps into the back of the magazine.

    from ia_pulp_ocr import load_issue
    pages = load_issue(".seed_cache/iapilot/wt192710")   # -> {printed page: [paragraph, ...]}
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from xml.etree.ElementTree import iterparse

NS = "{http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml}"


def _paragraphs(page_el, height: int) -> list[dict]:
    out = []
    for block in page_el.iter(f"{NS}block"):
        if block.get("blockType") != "Text":
            continue
        for par in block.iter(f"{NS}par"):
            lines, tops, italic = [], [], 0
            for line in par.iter(f"{NS}line"):
                chars = []
                for fmt in line.iter(f"{NS}formatting"):
                    t = "".join(c.text or "" for c in fmt.iter(f"{NS}charParams"))
                    if fmt.get("italic") == "1":
                        italic += len(t)
                    chars.append(t)
                text = "".join(chars).strip()
                if text:
                    lines.append(text)
                    tops.append(int(line.get("t") or 0))
            if not lines:
                continue
            out.append({"lines": lines, "top": min(tops) / max(height, 1),
                        "italic": italic > 0.6 * sum(len(l) for l in lines)})
    return out


def load_issue(stem: str) -> dict[int, list[dict]]:
    """Printed page number -> paragraphs in reading order (furniture removed)."""
    nums = json.loads(Path(stem + "_page_numbers.json").read_text())["pages"]
    leaf_to_page = {p["leafNum"]: int(p["pageNumber"]) for p in nums if str(p["pageNumber"]).isdigit()}
    pages: dict[int, list[dict]] = {}
    leaf = -1
    with gzip.open(stem + "_abbyy.gz") as f:
        for _ev, el in iterparse(f, events=("end",)):
            if el.tag != f"{NS}page":
                continue
            leaf += 1
            pnum = leaf_to_page.get(leaf)
            if pnum is not None:
                pars = [p for p in _paragraphs(el, int(el.get("height") or 1)) if not _furniture(p)]
                pages.setdefault(pnum, []).extend(pars)
            el.clear()
    return pages


_HEAD = re.compile(r"^(?:\d{1,4}\s+)?WEIRD\s+TALES(?:\s+\d{1,4})?$|^\d{1,4}$", re.I)


def _furniture(p: dict) -> bool:
    """Running heads and folios: a short line at the very top of the page that is the
    magazine's name, a page number, or a story title set in capitals ("LOUP-GAROU")."""
    text = " ".join(p["lines"]).strip()
    if p["top"] >= 0.09 or len(text) >= 80:
        return False
    letters = re.sub(r"[^A-Za-z]", "", text)
    return bool(_HEAD.match(text)) or (len(text.split()) <= 8 and letters.isupper() and len(letters) >= 3)


def par_text(p: dict) -> str:
    """Lines -> one paragraph. ABBYY marks a word broken across lines with "¬" (always rejoin:
    "twin¬" + "kled"); a real hyphen at a line end stays ("dust-" + "colored"). Lines that are
    only a page number (a folio caught inside a paragraph) are dropped."""
    out = ""
    for line in p["lines"]:
        if re.fullmatch(r"\d{1,4}", line.strip()):
            continue
        if out.endswith("¬"):
            out = out[:-1] + line
        elif out.endswith("-") and not out.endswith("--") and line[:1].islower():
            out = out + line
        else:
            out = (out + " " + line) if out else line
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------- stories
_JUMP_ON = re.compile(r"\s*\(\s*Con\w{4,8}\s+on\s+(?:page|next\s+page)\s*(\d+)?\s*\)\s*", re.I)
_JUMP_FROM = re.compile(r"\(\s*Con\w{4,8}\s+from\s+page\s*(\d+)\s*\)", re.I)


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def _merge(texts: list[str]) -> list[str]:
    """Rejoin a paragraph split by a column or page break: the first half ends in a hyphen
    (ABBYY's soft "¬") or with no closing punctuation, and the second half starts lowercase."""
    out: list[str] = []
    for t in texts:
        if out:
            prev = out[-1]
            if prev.endswith(("¬", "-")) and t[:1].islower():
                out[-1] = prev.rstrip("¬-") + t
                continue
            if not re.search(r"[.!?\"'”’:;)—–]$", prev) and t[:1].islower():
                out[-1] = prev + " " + t
                continue
        out.append(t)
    return [t.replace("¬", "") for t in out]


def story_text(pages: dict[int, list[dict]], start: int, end: int, title: str, author: str,
               next_title: str | None = None, verse: bool = False) -> list[str]:
    """Paragraphs of the story printed from page `start` up to page `end` (where the next item
    begins: up to its title when that falls mid-page), plus any "(Continued on page N)" run in
    the back of the issue. `verse` keeps a poem's line breaks."""
    surname = _norm(author).split()[-1] if author else ""
    render = (lambda p: "\n".join(p["lines"])) if verse else par_text
    texts: list[str] = []
    for pn in range(start, end + 1):
        pars = pages.get(pn, [])
        lo, hi = 0, len(pars)
        if pn == start:
            i = boundary_cut(pages, start, title)
            lo = i if i is not None else 0
        if pn == end:
            j = boundary_cut(pages, end, next_title) if next_title else None
            if j is None and next_title and pn != start:
                j = caps_lead(pars)              # the next piece's title wasn't read; find its opening
            hi = j if j is not None and j >= lo else (0 if pn != start else hi)
        chunk = pars[lo:hi]
        if pn > start:                  # the back pages: another story's continuation ends this one
            stop = next((k for k, p in enumerate(chunk) if _JUMP_FROM.search(par_text(p))), None)
            if stop is not None:
                kept = [render(p) for p in chunk[:stop]]
                while kept and len(kept[-1].split()) <= 6 and not kept[-1].rstrip().endswith((".", "!", "?", "\"", "\u201d")):
                    kept.pop()                  # that continuation's heading ("The Eyrie")
                texts += kept
                break
        texts += [render(p) for p in chunk]
    # drop the title, byline and other short furniture before the first real paragraph
    while texts and (len(texts[0].split()) < 12 and (_norm(title) in _norm(texts[0]) or
                     (surname and surname in _norm(texts[0])) or len(texts[0].split()) < 4)):
        texts.pop(0)
    # follow jumps into the back pages
    out: list[str] = []
    for t in texts:
        m = _JUMP_ON.search(t)
        out.append(_JUMP_ON.sub(" ", t).strip())
        if m and m.group(1):
            out += _continuation(pages, int(m.group(1)), start, end, came_from=None)
    final = [t for t in _merge([t for t in out if t]) if t and re.search(r"[A-Za-z]", t)]
    # a story ends on a sentence; short unpunctuated lines after it are the next piece's
    # heading, a blurb lead-in ("Here Are the Final Chapters of"), or an ad title
    while final and len(final[-1].split()) < 10 and not re.search(r"[.!?\"\u201d\u2019')]\s*$", final[-1]):
        final.pop()
    return final


def _ad_page(pars: list[dict]) -> bool:
    """A page of advertisements: many short fragments rather than columns of prose."""
    sizes = sorted(len(par_text(p).split()) for p in pars)
    return len(sizes) >= 5 and sizes[len(sizes) // 2] < 10


def _continuation(pages, page: int, start: int, end: int, came_from: int | None = None) -> list[str]:
    """Paragraphs after "(Continued from page X)" (X inside this story). The run carries on
    to the next page when it ends mid-text, and stops at the next jump marker or at another
    story's continuation. Advertisement blocks it passes are left for the correction pass."""
    out, on = [], False
    for pn in range(page, page + 4):   # ads met on the way are dropped by the correction pass
        for p in pages.get(pn, []):
            t = par_text(p)
            m = _JUMP_FROM.search(t)
            if m:
                if on:                               # another story's continuation begins
                    while out and len(out[-1].split()) <= 6 and not out[-1].rstrip().endswith((".", "!", "?", "\"", "\u201d")):
                        out.pop()                    # ...drop its heading ("The Bride of Osiris")
                    return out
                if start <= int(m.group(1)) < end or int(m.group(1)) == came_from:   # chained jumps
                    on = True
                    t = _JUMP_FROM.sub(" ", t).strip()
            if on:
                if _JUMP_ON.search(t):
                    nxt = _JUMP_ON.search(t).group(1)
                    out.append(_JUMP_ON.sub(" ", t).strip())
                    return out + (_continuation(pages, int(nxt), start, end, came_from=pn) if nxt else [])
                if t:
                    out.append(t)
    return out


def caps_lead(pars: list[dict]) -> int | None:
    """Index of the first paragraph that opens a new piece in pulp typography: a long
    paragraph whose first word is set in capitals. Used when the title is decorative
    lettering the scanner didn't read."""
    for i, p in enumerate(pars):
        t = par_text(p)
        first = re.sub(r"[^A-Za-z]", "", t.split()[0]) if t.split() else ""
        if len(first) >= 2 and first.isupper() and len(t.split()) >= 30:
            return i
    return None


def boundary_cut(pages: dict[int, list[dict]], page: int, next_title: str) -> int | None:
    """Index of the paragraph on `page` where the next item's title appears (it starts
    mid-page), or None if it isn't found there."""
    want = _norm(re.sub(r"\[.*?\]", "", next_title))
    if not want:
        return None
    for i, p in enumerate(pages.get(page, [])):
        t = _norm(par_text(p))
        if len(t.split()) <= 14 and (want in t or (len(t) > 4 and t in want)):
            return i
    return None
