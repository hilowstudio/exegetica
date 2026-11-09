"""Bring a school-provided book (a PDF in book-copies/) into the Reading Room as a school-only title.

Yorkville Christian's principal and curriculum lead provide these copies for use with YCS school accounts (Adam,
2026-11-09). They are in copyright, so the files stay out of git (.gitignore: /book-copies/) and the working files
stay in .seed_cache/ (also ignored). Nothing here calls a model or the network.

Four steps, each re-runnable, each reading the last one's output from .seed_cache/school/<slug>/:

    python scripts/ingest_school_copy.py extract <pdf> --slug <slug> [--ocr-all]
        pages.jsonl: every page's lines with their positions. The PDF's own text layer is used wherever it has one
        (rule: text layer first); a page without one is rendered and read with Tesseract OCR.
    python scripts/ingest_school_copy.py propose <slug> --title T --author A [--isbn I --edition E --rights R]
        book.json: the chapter list (from the PDF's outline, else its printed contents page), the page offset,
        and the front and back matter. Edit book.json by hand where it's wrong; build reads it.
    python scripts/ingest_school_copy.py build <slug>
        work.md (the text, cleaned: running heads, page numbers and scan footers dropped, line-end hyphens
        rejoined, paragraphs rebuilt, <!-- pN --> page markers kept for proofing) and proof.md (the worklist).
    python scripts/ingest_school_copy.py load <slug> [--db db/books.db]
        stores the chapters in books.db with access 'school' (served only to YCS accounts and admin).

work.md follows scripts/seed_duncan_colloquia.py: "## Title" starts a chapter, "### " a sub-heading, "> " a
displayed quotation, and <!-- ... --> lines are dropped at load.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import html as _html
import json
import re
import sqlite3
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "school"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_WIDTH = 2000          # pixels across a rendered page for OCR
MIN_LAYER_WORDS = 15      # fewer words than this in the text layer and the page is OCR'd (if it has an image)


# ---------------------------------------------------------------- extract

def _space(c: str) -> bool:
    """Whitespace, except the four separator codes (\x1c-\x1f), which Python counts as space: a PDF that encodes
    its text with shifted codes uses them for characters (The Hiding Place sets 9 as \x1c)."""
    return c.isspace() and c not in "\x1c\x1d\x1e\x1f"


def _word_lines(tp, w, h) -> list[dict] | None:
    """A scan's OCR layer gives one box per word, but not always in reading order. Group the words by where they
    sit: words that share a height form a line, read left to right. None when the layer's boxes aren't words (a
    born-digital PDF boxes whole blocks; the character method below reads those)."""
    k = tp.count_rects()
    if k < 20:
        return None
    # Words come from the characters, so every letter is kept: the layer's own word boxes can leave out the end of
    # a word hyphenated across a line. A word ends at a space, or where its letters jump to another line.
    n = tp.count_chars()
    text = tp.get_text_range(0, n)
    words, cur = [], []

    def end_word():
        if cur:
            xs0 = [b[0] for _, b in cur]; xs1 = [b[2] for _, b in cur]
            ys0 = [b[1] for _, b in cur]; ys1 = [b[3] for _, b in cur]
            words.append({"x0": min(xs0) / w, "x1": max(xs1) / w, "y0": (h - max(ys1)) / h, "y1": (h - min(ys0)) / h,
                          "t": "".join(c for c, _ in cur).replace("\ufffe", "-")})
            cur.clear()

    for i, ch in enumerate(text[:n]):
        if _space(ch):
            end_word()
            continue
        b = tp.get_charbox(i)
        if b[3] <= b[1]:
            continue
        if cur:
            pb = cur[-1][1]
            size = max(pb[3] - pb[1], b[3] - b[1])
            jumped = abs((b[1] + b[3]) / 2 - (pb[1] + pb[3]) / 2) > size * 0.8 and ch.isalnum()
            if jumped or b[0] < pb[0] - size * 2:
                end_word()
        cur.append((ch, b))
    end_word()
    if len(words) < 20:
        return None
    hs = sorted(wd["y1"] - wd["y0"] for wd in words)
    med = hs[len(hs) // 2]
    if sum(1 for wd in words if (wd["y1"] - wd["y0"]) > med * 2.2) > len(words) * 0.2:
        return None                                   # boxes span several lines: not word boxes
    words.sort(key=lambda wd: (wd["y0"] + wd["y1"]) / 2)
    lines = []
    for wd in words:
        cy = (wd["y0"] + wd["y1"]) / 2
        for ln in reversed(lines[-3:]):               # the line whose middle band this word's middle falls in
            if abs(cy - ln["cy"]) < max(med, ln["h"]) * 0.55:
                ln["w"].append(wd)
                ln["cy"] = sum((x["y0"] + x["y1"]) / 2 for x in ln["w"]) / len(ln["w"])
                ln["h"] = statistics.median(x["y1"] - x["y0"] for x in ln["w"])
                break
        else:
            lines.append({"w": [wd], "cy": cy, "h": wd["y1"] - wd["y0"]})
    out = []
    for ln in lines:
        ws = sorted(ln["w"], key=lambda x: x["x0"])
        out.append({"x0": ws[0]["x0"], "x1": max(x["x1"] for x in ws), "y0": min(x["y0"] for x in ws),
                    "y1": max(x["y1"] for x in ws), "bh": ln["h"], "fs": ln["h"], "fh": ln["h"],
                    "t": " ".join(x["t"] for x in ws), "conf": None})
    out.sort(key=lambda l: (round(l["y0"], 3), l["x0"]))
    return out


def _layer_lines(page) -> list[dict]:
    """The page's text layer as positioned lines (fractions of the page, y measured from the top)."""
    w, h = page.get_size()
    tp = page.get_textpage()
    n = tp.count_chars()
    if not n:
        return []
    by_word = _word_lines(tp, w, h)
    if by_word is not None:
        return by_word
    import pypdfium2.raw as pdfium_c
    text = tp.get_text_range(0, n)
    lines, cur = [], []

    def flush():
        boxes = [(b, fs) for c, b, fs in cur if not _space(c)]
        if boxes:
            t = "".join(c for c, _, _ in cur).strip(" ").replace("\ufffe", "-")
            hs = [b[3] - b[1] for b, _ in boxes]
            lines.append({"x0": min(b[0] for b, _ in boxes) / w, "x1": max(b[2] for b, _ in boxes) / w,
                          "y0": (h - max(b[3] for b, _ in boxes)) / h, "y1": (h - min(b[1] for b, _ in boxes)) / h,
                          "bh": statistics.median(hs) / h, "fs": statistics.median(fs for _, fs in boxes) / h,
                          "t": re.sub(r"[^\S\x1c-\x1f]+", " ", t), "conf": None})
        cur.clear()

    # Lines come from where the characters sit, not from the layer's own line breaks: a scan's OCR layer can leave
    # a break out and run two printed lines together, and that would read as a paragraph break.
    chars = []
    for i, ch in enumerate(text[:n]):
        if ch in "\r\n":
            chars.append((" ", None, 0.0))
            continue
        chars.append((ch, tp.get_charbox(i), pdfium_c.FPDFText_GetFontSize(tp.raw, i)))
    hs = [b[3] - b[1] for c, b, _ in chars if b and not _space(c) and b[3] > b[1]]
    ch_h = statistics.median(hs) if hs else 10.0
    line_cy, last_x1 = None, None
    for c, b, fs in chars:
        if b is None or _space(c) or b[3] <= b[1]:
            if cur:
                cur.append((" ", b or (0, 0, 0, 0), fs))
            continue
        cy = (b[1] + b[3]) / 2
        small = (b[3] - b[1]) < ch_h * 0.7 or not c.isalnum()     # a comma, a quotation mark: it joins its line
        # a jump back to the left is always a new line (an opening quotation mark included); otherwise only a full-size
        # character that leaves the line's height starts one
        if line_cy is not None and (b[0] < last_x1 - ch_h * 3 or (not small and abs(cy - line_cy) > ch_h * 0.6)):
            flush()
            line_cy = None
        cur.append((c, b, fs))
        if not small:
            line_cy = cy if line_cy is None else (line_cy * 0.8 + cy * 0.2)
        last_x1 = b[2]
    flush()
    lines.sort(key=lambda l: (round(l["y0"], 3), l["x0"]))
    # The type size is the font size where the layer varies it. An invisible OCR layer often sets every word at
    # one size and scales it; then the glyph boxes are the better measure.
    sizes = {round(l["fs"], 5) for l in lines}
    for l in lines:
        l["fh"] = l["fs"] if len(sizes) > 1 else l["bh"]
    return lines


def _ocr_lines(page) -> list[dict]:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT
    w, _ = page.get_size()
    img = page.render(scale=OCR_WIDTH / w).to_pil().convert("L")
    W, H = img.size
    d = pytesseract.image_to_data(img, lang="eng", config="--psm 3", output_type=pytesseract.Output.DICT)
    groups: dict = collections.OrderedDict()
    for i, word in enumerate(d["text"]):
        if not (word or "").strip():
            continue
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        groups.setdefault(key, []).append(i)
    lines = []
    for idx in groups.values():
        x0 = min(d["left"][i] for i in idx); x1 = max(d["left"][i] + d["width"][i] for i in idx)
        y0 = min(d["top"][i] for i in idx); y1 = max(d["top"][i] + d["height"][i] for i in idx)
        confs = [float(d["conf"][i]) for i in idx if float(d["conf"][i]) >= 0]
        lines.append({"x0": x0 / W, "x1": x1 / W, "y0": y0 / H, "y1": y1 / H,
                      "fh": statistics.median(d["height"][i] for i in idx) / H,
                      "t": " ".join(d["text"][i].strip() for i in idx),
                      "conf": round(sum(confs) / len(confs), 1) if confs else None})
    lines.sort(key=lambda l: (round(l["y0"], 3), l["x0"]))
    return lines


def cmd_extract(a):
    if a.pdf.lower().endswith(".epub"):
        return _extract_epub(a)
    import pypdfium2 as pdfium
    pdf_path = Path(a.pdf)
    out = CACHE / a.slug
    out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    toc = []
    for item in pdf.get_toc():          # pypdfium2 5: PdfBookmark with get_title() and get_dest().get_index()
        dest = item.get_dest()
        idx = dest.get_index() if dest is not None else None
        if idx is not None:
            toc.append({"title": (item.get_title() or "").strip(), "page": idx + 1, "level": item.level})
    prior = {}
    if (out / "pages.jsonl").exists() and not a.fresh:   # pages already read by OCR are kept, not read again
        with open(out / "pages.jsonl", encoding="utf-8") as f:
            prior = {r["n"]: r for r in map(json.loads, f) if r.get("src") == "ocr"}
    t0, rows, ocrd = time.time(), [], 0
    for i in range(len(pdf)):
        page = pdf[i]
        lines = _layer_lines(page)
        words = sum(len(l["t"].split()) for l in lines)
        has_img = any(obj.type == 3 for obj in page.get_objects(max_depth=1))   # FPDF_PAGEOBJ_IMAGE
        src = "text"
        if a.ocr_all or (words < MIN_LAYER_WORDS and has_img):
            ocr = prior[i + 1]["lines"] if (i + 1) in prior else _ocr_lines(page)
            if a.ocr_all and lines:
                rows_extra = {"layer": lines}
            else:
                rows_extra = {}
            lines, src, ocrd = ocr, "ocr", ocrd + 1
        else:
            rows_extra = {}
        rows.append({"n": i + 1, "src": src if lines else "none", "lines": lines, **rows_extra})
        if (i + 1) % 20 == 0:
            print(f"  page {i + 1}/{len(pdf)}  ({ocrd} by OCR, {time.time() - t0:.0f}s)", flush=True)
    with open(out / "pages.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {"pdf": str(pdf_path.resolve()), "pages": len(rows), "ocr_pages": ocrd, "outline": toc,
            "pdf_meta": {k: str(v) for k, v in (pdf.get_metadata_dict() or {}).items()}}
    (out / "extract.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{a.slug}: {len(rows)} pages, {ocrd} read by OCR, {sum(1 for r in rows if r['src'] == 'none')} empty,"
          f" outline {len(toc)} entries, {time.time() - t0:.0f}s")


# ---------------------------------------------------------------- EPUB (born-digital: no pages, no OCR)

_BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "div", "blockquote"]


def _epub_blocks(path):
    """The book as ordered blocks (heading, paragraph, quotation) across its reading order, with where each element
    id falls, so the contents list's links can be placed."""
    import warnings
    warnings.filterwarnings("ignore")
    import ebooklib
    from bs4 import BeautifulSoup
    from ebooklib import epub
    book = epub.read_epub(str(path))
    blocks, anchors, spine_files = [], {}, []
    for k, (idref, _) in enumerate(book.spine):
        item = book.get_item_with_id(idref)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        name = item.get_name()
        base = name.split("/")[-1]
        spine_files.append(base)
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for br in soup.find_all("br"):
            br.replace_with("\n")
        body = soup.body or soup
        first_of_file = len(blocks)
        pos = []                                              # (sourceline, sourcepos, block index)
        for el in body.find_all(_BLOCK_TAGS):
            if el.name in ("div", "blockquote") and el.find(_BLOCK_TAGS):
                continue                                      # a container: its children are the blocks
            if el.name in ("p", "div", "li") and el.find_parent(["p", "li"]):
                continue
            t = re.sub(r"[ \t\r\f\v]+", " ", el.get_text("")).replace("\u00a0", " ")
            t = re.sub(r"\s*\n\s*", "\n", t).strip()
            if not t:
                continue
            kind = "h" if re.fullmatch(r"h\d", el.name) else ("q" if el.name == "blockquote" or el.find_parent("blockquote") else "p")
            blocks.append({"k": kind, "lv": int(el.name[1]) if kind == "h" else None, "f": len(spine_files),
                           "cls": " ".join(el.get("class") or []), "t": t})
            pos.append((el.sourceline or 0, el.sourcepos or 0, len(blocks) - 1))
        anchors[base] = first_of_file
        for el in body.find_all(id=True):                    # an id points at the first block at or after it
            at = (el.sourceline or 0, el.sourcepos or 0)
            nxt = next((i for sl, sp, i in pos if (sl, sp) >= at), None)
            if nxt is not None:
                anchors[f"{base}#{el['id']}"] = nxt

    def walk(items, depth=0, out=None):
        out = [] if out is None else out
        for it in items:
            sec, kids = (it[0], it[1]) if isinstance(it, (list, tuple)) else (it, [])
            href = (getattr(sec, "href", "") or "").split("/")[-1]
            idx = anchors.get(href, anchors.get(href.split("#")[0]))
            out.append({"title": (getattr(sec, "title", "") or "").strip(), "depth": depth, "block": idx})
            walk(kids, depth + 1, out)
        return out
    toc = walk(book.toc)
    meta = lambda k: (book.get_metadata("DC", k) or [[""]])[0][0]
    return blocks, toc, {"title": meta("title"), "creator": meta("creator"), "publisher": meta("publisher"),
                         "date": meta("date"), "rights": meta("rights"), "spine": spine_files}


def _extract_epub(a):
    out = CACHE / a.slug
    out.mkdir(parents=True, exist_ok=True)
    blocks, toc, meta = _epub_blocks(a.pdf)
    with open(out / "blocks.jsonl", "w", encoding="utf-8") as f:
        for b in blocks:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    with open(out / "pages.jsonl", "w", encoding="utf-8") as f:      # one record per file, for the proof tools' counts
        for i in range(len(meta["spine"])):
            f.write(json.dumps({"n": i + 1, "src": "epub", "lines": []}) + "\n")
    (out / "extract.json").write_text(json.dumps({"kind": "epub", "pdf": str(Path(a.pdf).resolve()), "pages": len(meta["spine"]),
                                                  "ocr_pages": 0, "outline": toc, "meta": meta}, indent=1, ensure_ascii=False),
                                      encoding="utf-8")
    heads = collections.Counter(f"h{b['lv']}" for b in blocks if b["k"] == "h")
    print(f"{a.slug}: EPUB, {len(blocks)} blocks, {sum(len(b['t'].split()) for b in blocks):,} words, "
          f"contents {len(toc)} entries, headings {dict(heads)}; metadata: {meta['title']!r} / {meta['creator']!r}")


def _load_blocks(slug):
    with open(CACHE / slug / "blocks.jsonl", encoding="utf-8") as f:
        return [json.loads(x) for x in f]


_EPUB_SKIP = re.compile(r"^(cover|title ?page|copyright|contents|table of contents|dedication|epigraph|"
                        r"also by|by [a-z]|about the (co)?authors?|acknowledg|pottermore|praise|credits|"
                        r"(a )?(reader'?s? )?guide|discussion questions|excerpt|preview|newsletter|sign up)", re.I)


def _propose_epub(a, ex):
    blocks = _load_blocks(a.slug)
    toc = [e for e in ex["outline"] if e["block"] is not None]
    lo, hi = 0, len(blocks) - 1
    if a.toc_under:                                           # one book of a collection: the entries under it
        want = _norm(a.toc_under)
        top = next((i for i, e in enumerate(toc) if _norm(e["title"]).startswith(want)), None)
        if top is None:
            sys.exit(f"no contents entry starts with {a.toc_under!r}")
        d0 = toc[top]["depth"]
        lo = toc[top]["block"]
        nxt = next((e for e in toc[top + 1:] if e["depth"] <= d0), None)
        hi = (nxt["block"] - 1) if nxt else hi
        toc = [e for e in toc[top + 1:] if e["depth"] > d0 and lo <= e["block"] <= hi]
    heads = collections.Counter(f"h{b['lv']}" for b in blocks[lo:hi + 1] if b["k"] == "h")
    if a.headings:                                            # the book's own headings, e.g. --headings h2
        tags = set(a.headings.split(","))
        starts = [(blocks[i]["t"].replace("\n", " "), i) for i in range(lo, hi + 1)
                  if blocks[i]["k"] == "h" and f"h{blocks[i]['lv']}" in tags]
        how = f"the book's {a.headings} headings"
    else:
        depths = collections.Counter(e["depth"] for e in toc)
        depth = a.toc_depth if a.toc_depth is not None else max(depths, key=lambda d: (depths[d], d)) if depths else 0
        starts = [(e["title"], e["block"]) for e in toc if e["depth"] == depth]
        how = f"the contents list (depth {depth})"
    starts = sorted({b: t for t, b in starts}.items())
    chapters = []
    for k, (b, t) in enumerate(starts):
        end = (starts[k + 1][0] - 1) if k + 1 < len(starts) else hi
        c = {"title": _title_case(re.sub(r"\s+", " ", t)), "start": b, "end": end}
        if _EPUB_SKIP.search(c["title"]):
            c["skip"] = True
        chapters.append(c)
    if chapters and chapters[0]["start"] > lo:                # anything before the first chapter is front matter
        chapters.insert(0, {"title": "Front matter", "start": lo, "end": chapters[0]["start"] - 1, "skip": True})
    meta = ex.get("meta", {})
    book = {"slug": a.slug, "title": a.title or meta.get("title", ""), "author": a.author or meta.get("creator", ""),
            "isbn": a.isbn or "", "edition": a.edition or meta.get("publisher", ""), "rights": a.rights or "",
            "rights_hint": " / ".join(x for x in (meta.get("rights"), meta.get("publisher"), meta.get("date")) if x),
            "access": "school", "kind": "epub", "chapters_from": how, "text_ends": hi, "dedication": "",
            "headings_in_range": dict(heads), "chapters": chapters,
            "note": "Starts and ends are block numbers in blocks.jsonl. Check each title and start; mark front and "
                    "back matter \"skip\": true; or re-run propose with --headings h2 (or h1,h2) to use the book's "
                    "own headings."}
    (CACHE / a.slug / "book.json").write_text(json.dumps(book, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{a.slug}: {len(chapters)} chapters from {how}; headings in range {dict(heads)}")
    for c in chapters:
        print(f"   b{c['start']:>5}-{c['end']:<5} {'(skip) ' if c.get('skip') else ''}{c['title'][:60]}")


_NUMBER = re.compile(r"(chapter|part|book)?\s*([0-9]+|[ivxlc]+|(one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
                     r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)"
                     r"(one|two|three|four|five|six|seven|eight|nine)?)")


def _requote(t):
    """Double quotation marks set by pairing within the paragraph: the first opens, the next closes, and so on. A
    conversion from a scan sets many the wrong way round and spaces them wrongly ("son, ”Jessica said"); pairing is
    right wherever none was lost, and a paragraph that runs on into the next speech keeps its last mark open."""
    out, n = [], 0
    for ch in t:
        if ch in "\"“”":
            out.append("“" if n % 2 == 0 else "”"); n += 1
        else:
            out.append(ch)
    t = "".join(out)
    t = re.sub(r"“\s+", "“", t)
    t = re.sub(r"(?<=[^\s—–-])\s+”", "”", t)
    return re.sub(r"”(?=[A-Za-z])", "” ", t)


def _epub_label(t, tn):
    """A chapter's own label set as a paragraph (its number, its title, a separator), not its first words. A one-word
    first paragraph ("Hagrid?") is text."""
    n = _norm(t)
    return len(t.split()) <= 8 and (not n or n == tn or (len(n.split()) >= 2 and n in tn) or bool(_NUMBER.fullmatch(n)) or
                                    bool(re.fullmatch(r"(chapter|part|book)\s+\w+", n)))


def _epub_md(slug, book):
    """Chapters of an EPUB as work.md lines (the same conventions as a scan's)."""
    blocks = _load_blocks(slug)
    vocab = _vocab(" ".join(b["t"] for b in blocks))
    md = [f"<!-- {book['title']} by {book['author']}: built {time.strftime('%Y-%m-%d')} from the EPUB -->"]
    rows, total = [], 0
    book_norm = _norm(book["title"])
    drop_text = set(book.get("drop_text") or [])   # a file's furniture set as paragraphs ("Contents - Prev / Next")
    for c in book["chapters"]:
        if c.get("skip"):
            continue
        part = blocks[c["start"]:c["end"] + 1]
        tn = _norm(c["title"])
        k = 0                                                 # the opener's own headings give way to "## Title"
        while k < len(part) and k < 4 and (part[k]["k"] == "h" or _epub_label(part[k]["t"], tn)):
            k += 1
        md += ["", f"## {_curly(c['title'])}"]
        items = []                                            # [kind, text, file]
        for b in part[k:]:
            if (b["k"] == "h" and _norm(b["t"]) == book_norm) or b["t"].strip() in drop_text:  # running heads, link bars
                continue
            # a hard-wrapped file (a text conversion) breaks lines inside paragraphs; a word split at a line end is
            # rejoined whole when the whole word is known, and keeps its hyphen otherwise ("implant-legends")
            t = re.sub(r"(\w+)-\n(\w+)", lambda m: m[1] + m[2] if (m[1] + m[2]).lower() in vocab else m[1] + "-" + m[2],
                       _curly(_html.unescape(b["t"])))
            t = t.replace("\n", " ").strip()
            if book.get("requote"):
                t = t.replace("-?", "-")                      # a conversion's mark inside compounds ("Alia-?of-?the-?Knife")
            if not items:
                t = re.sub(r"^(= ){2,}=\s*", "", t)          # a section separator run into the first paragraph
            if not t:
                continue
            if b["k"] == "p" and items and items[-1][0] == "p" and re.match(r"[a-z]", t):
                items[-1][1] += " " + t                       # a paragraph split at a page break of the scanned book
                continue
            items.append([b["k"], t, b["f"]])
        if book.get("requote") or book.get("split_dialogue") or book.get("dashes") or book.get("patterns"):
            whole = []
            for kind, t, bf in items:
                if kind != "p":
                    whole.append([kind, t, bf]); continue
                if book.get("dashes"):                       # a conversion that set every dash as a spaced hyphen
                    t = re.sub(r"\s+-\s+-\s+|\s+-\s+|\s+-(?=[”’])", "—", t)
                for pat, rep in book.get("patterns") or []:  # a book's own systematic misreads, as [regex, replacement]
                    t = re.sub(pat, rep, t)
                if book.get("requote"):
                    t = _requote(t)
                # speeches run together by the conversion: a closing mark, a space, an opening mark
                for x in (re.split(r"(?<=”)\s+(?=“)", t) if book.get("split_dialogue") else [t]):
                    whole.append(["p", x, bf])
            items = whole
        words, f = 0, None
        for kind, t, bf in items:
            if bf != f:
                f = bf
                md.append(f"<!-- p{f} -->")
            if kind == "h":
                md += ["", f"### {_title_case(t)}"]
            elif kind == "q":
                md += ["", "> " + t]
                words += len(t.split())
            else:
                md += ["", t]
                words += len(t.split())
        total += words
        rows.append((c["title"], c["start"], c["end"], words, 0))
    return md, rows, total, vocab


# ---------------------------------------------------------------- shared helpers

def _load_pages(slug):
    with open(CACHE / slug / "pages.jsonl", encoding="utf-8") as f:
        return [json.loads(x) for x in f]


_NUM_WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WORD_OF = {i: w for w, i in _NUM_WORDS.items()}


def _number_word(n: int) -> str:
    if n in _WORD_OF:
        return _WORD_OF[n].capitalize()
    tens = {2: "Twenty", 3: "Thirty", 4: "Forty", 5: "Fifty"}
    return f"{tens.get(n // 10, str(n // 10))}-{_WORD_OF[n % 10]}" if n % 10 else tens.get(n // 10, str(n))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("’", "'")).strip()


def _head_number(t: str):
    """The page number a running head or foot carries, or None ("18 / Be Daring", "Excitement in Ephesus / 19",
    "19")."""
    m = re.match(r"^\s*(\d{1,3})\s*(?:[/|•·]\s*\S.*)?$", t) or re.match(r"^.*\S\s*[/|•·]\s*(\d{1,3})\s*$", t)
    return int(m.group(1)) if m else None


def _is_furniture(line: dict, title_norm: str) -> bool:
    """A running head or foot, a bare page number, or a scan's footer."""
    t = line["t"].strip()
    if not t:
        return True
    if "archive.org" in t.lower() or "digitized by" in t.lower():
        return True
    in_margin = line["y0"] < 0.10 or line["y1"] > 0.92
    if not in_margin:
        return False
    if re.fullmatch(r"[\divxlcIVXLC]{1,5}\.?", t):
        return True
    if _head_number(t) is not None and len(t.split()) <= 12:
        return True
    if title_norm and _norm(t) == title_norm:
        return True
    return False


# ---------------------------------------------------------------- propose

def _contents_from_page(pages):
    """Find the printed contents page in the first 20 pages and read 'Title .... 123' entries from it."""
    for p in pages[:20]:
        texts = [l["t"] for l in p["lines"]]
        if not any(re.fullmatch(r"\s*(table of )?contents\s*", t, re.I) for t in texts):
            continue
        entries, pending = [], None
        for t in texts:
            if re.fullmatch(r"\s*(table of )?contents\s*", t, re.I):
                continue
            two = re.match(r"^\s*\(([^)]+)\)\s*[\"”']?\s*(\d{1,3})\s*$", t)          # "(John 13:1-35) 13"
            if two and pending:
                entries.append({**pending, "passage": two.group(1).strip(), "printed": int(two.group(2))})
                pending = None
                continue
            m = re.match(r"^\s*(?:(\d{1,2})[.)]\s+)?(.+?)[\s.·…_-]*\b(\d{1,3})\s*$", t)
            if m and len(m.group(2).strip(" .")) > 2:
                entries.append({"title": m.group(2).strip(" ."), "number": int(m.group(1)) if m.group(1) else None,
                                "printed": int(m.group(3))})
                pending = None
                continue
            n = re.match(r"^\s*(\d{1,2})[.)]\s+(.+?)\s*$", t)                       # "1. The Sovereign Servant"
            pending = {"title": n.group(2).strip(), "number": int(n.group(1))} if n else None
        if entries:
            return p["n"], entries
    return None, []


def _page_offset(pages):
    """PDF page number minus printed page number, from the numbers in running heads and feet."""
    votes = collections.Counter()
    for p in pages:
        for l in p["lines"]:
            if l["y0"] < 0.10 or l["y1"] > 0.92:
                k = _head_number(l["t"])
                if k is not None and 0 < k < 2000:
                    votes[p["n"] - k] += 1
    return votes.most_common(1)[0][0] if votes else 0, dict(votes.most_common(3))


_SKIP = re.compile(r"^(table of )?contents$|endorsements|praise for|what (people|others) are saying|acknowledg|"
                   r"about the (co)?authors?|also by|other books|books by|copyright|index$", re.I)
_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "with"}


def _title_case(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    if t != t.upper():
        return t
    words = t.lower().split()
    return " ".join(w if (i and w in _SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def _metrics(lines):
    """The page's measure: its text size, leading, left edge, right edge, and whether its lines are justified."""
    fhs = [l["fh"] for l in lines if l.get("fh")]
    fh = statistics.median(fhs) if fhs else 0.012
    ys = sorted(l["y0"] for l in lines)
    steps = [b - a for a, b in zip(ys, ys[1:]) if 0.5 * fh < b - a < 4 * fh]
    lead = statistics.median(steps) if steps else fh * 1.6
    full = [l for l in lines if l["x1"] - l["x0"] > 0.55]
    left = statistics.median(l["x0"] for l in full) if full else (min(l["x0"] for l in lines) if lines else 0.1)
    right = statistics.median(l["x1"] for l in full) if full else (max(l["x1"] for l in lines) if lines else 0.9)
    justified = len(full) >= 5 and statistics.pstdev(l["x1"] for l in full) < 0.012
    return {"fh": fh, "lead": lead, "left": left, "right": right, "justified": justified}


def _is_heading(l: dict, fh: float, gap=None, lead=None) -> bool:
    """Display type: clearly bigger than the page's text AND set apart (centered, or short of the measure), with
    space above it unless it opens the page. A paragraph's short last line sits at the normal leading, so it never
    qualifies."""
    w = l["x1"] - l["x0"]
    centered = abs((l["x0"] + l["x1"]) / 2 - 0.5) < 0.07 and w < 0.75
    if not (l.get("fh") and (centered or w < 0.55) and len(l["t"].split()) <= 12
            and not re.search(r"[,;.]$", l["t"].strip()) and not l["t"].strip().startswith(("—", "–"))):
        return False
    if gap is None or lead is None:
        return l["fh"] > fh * 1.4
    return l["fh"] > fh * 1.3 and gap > lead * 1.4


def _opener_heading(page) -> str:
    lines = page["lines"]
    if not lines:
        return ""
    fhs = [l["fh"] for l in lines if l.get("fh")]
    fh = statistics.median(fhs) if fhs else 0.012
    tops = [l for l in lines if l["y0"] < 0.35 and (_is_heading(l, fh) or abs((l["x0"] + l["x1"]) / 2 - 0.5) < 0.05)]
    return tops[0]["t"].strip() if tops else ""


def cmd_propose(a):
    ex = json.loads((CACHE / a.slug / "extract.json").read_text(encoding="utf-8"))
    if ex.get("kind") == "epub":
        return _propose_epub(a, ex)
    pages = _load_pages(a.slug)
    offset, votes = _page_offset(pages)
    chapters, how, contents_page = [], "", None
    outline = [o for o in ex.get("outline", []) if o.get("level", 0) == 0]
    if len(outline) >= 3:
        how = "PDF outline"
        chapters = [{"title": o["title"], "start": o["page"]} for o in outline]
    else:
        contents_page, entries = _contents_from_page(pages)
        how = f"printed contents (PDF page {contents_page}), page offset {offset}"
        chapters = [{"title": e["title"], "start": e["printed"] + offset, "printed": e["printed"],
                     **({"number": e["number"]} if e.get("number") else {}),
                     **({"passage": e["passage"]} if e.get("passage") else {})} for e in entries]
    dedication = ""
    if chapters and contents_page:
        front = []
        for n in range(contents_page + 1, chapters[0]["start"]):
            lines = pages[n - 1]["lines"]
            words = sum(len(l["t"].split()) for l in lines)
            text = " ".join(l["t"] for l in lines)
            if 0 < words < 45 and re.search(r"dedicated|this book is for|\bto my\b|in memory", text, re.I):
                dedication = "\n".join(l["t"].strip() for l in lines if not _is_furniture(l, _norm(a.title)))
                continue
            head = _opener_heading(pages[n - 1])
            if words >= 40 and head:
                front.append({"title": _title_case(head), "start": n, "front": True})
        chapters = front + chapters
    last = len(pages)
    # the text ends at the last page of prose; what follows (blank leaves, reader surveys, ads, the cover) is left out
    _ADS = re.compile(r"would like to know your opinion|other books (in|by)|available at your|leader's guide|"
                      r"order (form|today)|power to become", re.I)
    while last > 1:
        lines = pages[last - 1]["lines"]
        words = sum(len(l["t"].split()) for l in lines)
        if words >= 60 and not _ADS.search(" ".join(l["t"] for l in lines)):
            break
        last -= 1
    import difflib
    for c, nxt in zip(chapters, chapters[1:] + [None]):
        c["end"] = (nxt["start"] - 1) if nxt else last
        own = _opener_heading(pages[c["start"] - 1]) if 0 < c["start"] <= last else ""
        if not c.get("number") and own and (difflib.SequenceMatcher(None, _norm(own), _norm(c["title"])).ratio() > 0.75
                                            or _norm(c["title"]) in _norm(own) or re.match(r"chapter\s", _norm(c["title"]))):
            c["title"] = own                     # the heading as the book sets it (the outline can misspell)
        c["title"] = _title_case(c["title"])
        if _SKIP.search(c["title"]):
            c["skip"] = True                     # contents, praise, ads: left out unless the proof says otherwise
    book = {"slug": a.slug, "title": a.title, "author": a.author, "isbn": a.isbn or "", "edition": a.edition or "",
            "rights": a.rights or "", "access": "school", "chapters_from": how, "page_offset": offset,
            "offset_votes": votes, "front_matter_pages": [1, (chapters[0]["start"] - 1) if chapters else 0],
            "drop_pages": [], "text_ends": last, "dedication": dedication, "chapters": chapters,
            "note": "Check every chapter's title and start page against the book. Mark chapters to leave out with "
                    "\"skip\": true (praise pages, ads, the back cover). Add page numbers to drop_pages for "
                    "pages inside a chapter that aren't text (plates, blank pages)."}
    (CACHE / a.slug / "book.json").write_text(json.dumps(book, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{a.slug}: {len(chapters)} chapters from {how}")
    for c in chapters:
        print(f"   p{c['start']:>3}-{c['end']:<3} {c['title'][:70]}")


# ---------------------------------------------------------------- build

def _vocab(pages_text: str) -> collections.Counter:
    return collections.Counter(w.lower() for w in re.findall(r"[A-Za-z]+(?:'[a-z]+)?", pages_text))


def _body_lines(page, title_norm, drop_heading_above=None):
    lines = [l for l in page["lines"] if not _is_furniture(l, title_norm)]
    return lines


def _paragraphs(pages_lines, vocab):
    """Rebuild paragraphs from positioned lines across pages. Returns a list of (kind, text, page) with kind in
    p, quote, head, mark (a page marker)."""
    out, para, para_kind, para_page = [], [], "p", None

    def end():
        nonlocal para, para_kind
        if para:
            out.append((para_kind, _join_lines(para, vocab), para_page))
        para, para_kind = [], "p"

    for pn, lines, big in pages_lines:
        out.append(("mark", f"p{pn}", pn))
        if not lines:
            continue
        m = _metrics(lines)
        prev = None
        for k, l in enumerate(lines):
            t = l["t"].strip()
            gap = (l["y0"] - prev["y0"]) if prev else None
            nxt = lines[k + 1]["t"].strip() if k + 1 < len(lines) else ""
            if re.match(r"^[—–]\s*\S", t) and len(t.split()) <= 14 and (para or out):
                # "—Psalm 19:1–4" under a block: the block was a displayed quotation and this is its attribution
                end()
                for j in range(len(out) - 1, -1, -1):
                    if out[j][0] in ("p", "quote"):
                        out[j] = ("quote", out[j][1] + "\n[sig] " + t, out[j][2])
                        break
                prev = l
                continue
            if _is_heading(l, m["fh"], gap, m["lead"]) and not re.match(r"^[a-z]", nxt):
                end()
                out.append(("head", t, pn))
                prev = l
                continue
            indent = l["x0"] - m["left"]
            quote = indent > 0.06 and (m["right"] - l["x1"]) > 0.04
            spaced = gap is not None and gap > m["lead"] * 1.45
            ended = bool(para) and para[-1]["ends"]
            goes_on = bool(para) and bool(re.match(r"^[a-z]", t)) and (
                para[-1]["t"].endswith("-") or not re.search(r"[.!?:]['\"”’)]*$", para[-1]["t"]))
            if para and not goes_on and (indent > 0.02 or spaced or quote != (para_kind == "quote") or ended):
                end()
            if not para:
                para_kind, para_page = ("quote" if quote else "p"), pn
            short = m["right"] - l["x1"]
            # a line that stops short ends its paragraph: on a justified page any visible shortfall does; on a
            # ragged page only a clear one after a sentence's end does
            para.append({"t": t, "ends": (m["justified"] and short > 0.05)
                         or (short > 0.18 and bool(re.search(r"[.!?:”\"’)]$", t)))})
            prev = l
    end()
    return out


def _curly(t: str) -> str:
    """Straight quotation marks from a scan's text layer, set as the house sets them (rule G7)."""
    t = re.sub(r'(^|[\s(\[{—–-])"', r"\1“", t).replace('"', "”")
    t = re.sub(r"(^|[\s(\[{—–-])'", r"\1‘", t).replace("'", "’")
    return t


def _join_lines(lines, vocab) -> str:
    s = ""
    for l in lines:
        t = re.sub(r"^[_|~¦]+\s+", "", l["t"])
        if t.startswith("[sig] "):
            s = s + "\n[sig] " + t[6:]
            continue
        if not s:
            s = t
            continue
        if s.endswith("¬"):                     # Tesseract writes a line-end hyphen as the not sign
            s = s[:-1] + "-"
        # OCR can lose a line-end hyphen ("admoni" / "tion"): two pieces that are only a word together are one word
        a0, b0 = re.search(r"([A-Za-z]+)$", s), re.match(r"([a-z]+)", t)
        if a0 and b0 and not s.endswith("-"):
            joined = (a0.group(1) + b0.group(1)).lower()
            left, right = a0.group(1).lower(), b0.group(1)
            fragments = not _common(left) and not _common(right) and vocab[right] <= 1    # "inacces" / "sible"
            if ((vocab[joined] > 0 or _common(joined)) and not (_common(left) and _common(right))) or fragments:
                s = s + t
                continue
        if s.endswith("-") and not s.endswith("--") and re.match(r"[a-z]", t):
            a = re.search(r"([A-Za-z]+)-$", s)
            b = re.match(r"([a-z]+)", t)
            if a and b:
                joined = (a.group(1) + b.group(1)).lower()
                hyph = f"{a.group(1)}-{b.group(1)}".lower()
                left, right = a.group(1).lower(), b.group(1).lower()
                if vocab[hyph] > 0 and vocab[joined] == 0:
                    s = s + t                       # the book writes it hyphenated elsewhere
                elif vocab[joined] > 0 or _common(joined):
                    s = s[:-1] + t                  # a word broken at the line's end
                elif len(left) > 2 and len(right) > 2 and _common(left) and _common(right):
                    s = s + t                       # two words joined by a hyphen: all-powerful
                else:
                    s = s[:-1] + t
                continue
        if s.endswith(("—", "–")):
            s = s + t
        else:
            s = s + " " + t
    return re.sub(r"\s+", " ", s).strip()


def _vision_md(slug, book):
    """A textbook transcribed page by page (scripts/vision_transcribe.py: Markdown with TeX) as work.md. Chapters are
    page ranges, as for a scan. A page's own headings sit under the chapter's (## becomes ###); a heading repeated at
    the top of many pages is a running head and goes; a page the transcription could not give falls back to its OCR
    text, marked for the proof."""
    d = CACHE / slug
    vis = d / "vision"
    pages = {p["n"]: p for p in _load_pages(slug)} if (d / "pages.jsonl").exists() else {}
    title_norm = _norm(book["title"])
    heads = [_norm(x) for x in book.get("running_heads") or []] + [title_norm]
    ocr_vocab = _vocab(" ".join(l["t"] for p in pages.values() for l in p["lines"]))

    def ocr_text(n):
        # the page's OCR, rebuilt into paragraphs as a scan's would be, without its running heads and feet
        lines = [l for l in _body_lines(pages[n], title_norm) if not (
            (l["y0"] < 0.10 or l["y1"] > 0.92) and any(
                difflib.SequenceMatcher(None, re.sub(r"(\s+[0-9ivxlc|]{1,4})+$", "", _norm(l["t"])), h).ratio() > 0.8
                or (h and h in _norm(l["t"])) for h in heads))]
        return "\n\n".join(_curly(t) for kind, t, _ in _paragraphs([(n, lines, None)], ocr_vocab) if kind != "mark")

    texts, fallback = {}, []
    for c in book["chapters"]:
        for n in range(c["start"], c["end"] + 1):
            f = vis / f"p{n:04d}.md"
            if f.exists():
                texts[n] = f.read_text(encoding="utf-8").strip()
            elif n in pages and pages[n]["lines"]:
                texts[n] = ocr_text(n)
                fallback.append(n)
    tex = re.compile(r"(\\\(.*?\\\)|\\\[.*?\\\])", re.S)

    def normal_tex(s):
        # outside formulas: $...$ holding maths becomes \( \); an escaped \$ \% \& in prose is the plain sign
        parts = tex.split(s)
        for k in range(0, len(parts), 2):
            p = re.sub(r"(?<![\\$\w])\$(?!\s)([^$\n]{1,200}?)(?<!\s)\$(?![\w$])",
                       lambda m: f"\\({m.group(1)}\\)" if re.search(r"[\\^_=<>]|^[A-Za-z]$|^[A-Za-z]\(", m.group(1))
                       else m.group(0), parts[k])
            parts[k] = re.sub(r"\\([$%&#])", r"\1", p)
        return "".join(parts)

    texts = {n: normal_tex(t) for n, t in texts.items()}
    first_heads = collections.Counter()
    for t in texts.values():
        m = re.match(r"#+ (.+)", t)
        if m:
            first_heads[_norm(m.group(1))] += 1
    running = {h for h, k in first_heads.items() if k > 5}
    running |= {_norm(x) for x in book.get("running_heads") or []}
    md = [f"<!-- {book['title']}: built {time.strftime('%Y-%m-%d')} from a page-by-page transcription -->"]
    rows, total = [], 0
    for c in book["chapters"]:
        if c.get("skip"):
            continue
        md += ["", f"## {c['title']}"]
        words = 0
        for n in range(c["start"], c["end"] + 1):
            if n not in texts or n in set(book.get("drop_pages") or []):
                continue
            md.append(f"<!-- p{n}{' ocr' if n in fallback else ''} -->")
            body = []
            for ln in texts[n].split("\n"):
                # a note that the page is blank or unreadable, which is the transcriber's, not the book's
                if re.match(r"\s*\[?(Blank page|The page (appears|is|seems) (to be )?(blank|empty|mostly blank|too faded|"
                            r"unreadable)|This page (is|appears) (blank|empty)|Figure: (An? |The )?(blank|plain|empty)\b)",
                            ln, re.I):
                    continue
                # a running foot the transcription kept: a page number and a title in capitals ("LIFE OF CHRIST | 31")
                if re.fullmatch(r"\s*(\d{1,4}\s*[|•·]\s*[A-Z][A-Z0-9 ’'&:,.-]+|[A-Z][A-Z0-9 ’'&:,.-]+\s*[|•·]\s*\d{1,4})\s*", ln):
                    continue
                # or a page number beside the chapter's name ("332 Chapter 5 Polynomials and Polynomial Functions")
                if len(ln) < 90 and re.fullmatch(r"\s*(\d{1,4}\s+(Chapter|Lesson|Unit)\s+\d+\b[^.!?]*|"
                                                 r"(Chapter|Lesson|Unit)\s+\d+\b[^.!?]*\s\d{1,4})\s*", ln):
                    continue
                m = re.match(r"(#+) (.+)", ln)
                if m:
                    if _norm(m.group(2)) in running or _norm(m.group(2)) == _norm(c["title"]):
                        continue
                    ln = "### " + m.group(2).strip()
                body.append(ln)
            md += ["", "\n".join(body).strip()]
            words += len(" ".join(body).split())
        total += words
        rows.append((c["title"], c["start"], c["end"], words, 0))
    if fallback:
        print(f"  {len(fallback)} pages from OCR (the transcription was blocked or missing): {fallback[:20]}")
    vocab = _vocab(" ".join(texts.values()))
    return md, rows, total, vocab


def cmd_build(a):
    d = CACHE / a.slug
    book = json.loads((d / "book.json").read_text(encoding="utf-8"))
    if book.get("kind") == "vision":
        md, proof_rows, total_words, vocab = _vision_md(a.slug, book)
        return _finish_build(a, d, book, md, proof_rows, total_words, vocab, [])
    if book.get("kind") in ("epub", "flow"):
        md, proof_rows, total_words, vocab = _epub_md(a.slug, book)
        return _finish_build(a, d, book, md, proof_rows, total_words, vocab, [])
    pages = _load_pages(a.slug)
    title_norm = _norm(book["title"])
    by_n = {p["n"]: p for p in pages}
    vocab = _vocab(" ".join(l["t"] for p in pages for l in p["lines"]))
    drop = set(book.get("drop_pages") or [])
    md, proof_rows, total_words = [f"<!-- {book['title']} by {book['author']}: built {time.strftime('%Y-%m-%d')} from "
                                      f"{Path(json.loads((d / 'extract.json').read_text(encoding='utf-8'))['pdf']).name} -->"], [], 0
    low_conf = []
    for c in book["chapters"]:
        if c.get("skip"):
            continue
        pls = []
        for n in range(c["start"], c["end"] + 1):
            if n in drop or n not in by_n:
                continue
            p = by_n[n]
            lines = _body_lines(p, title_norm)
            # a running head that carries the chapter's title (or one the book names in book.json), read with or
            # without small slips by OCR
            heads = [_norm(c["title"])] + [_norm(x) for x in book.get("running_heads") or []]
            def head_like(l):                   # top or bottom margin, the page number beside it allowed
                n = re.sub(r"(\s+[0-9ivxlco]{1,4})+$", "", _norm(l["t"]))
                return ((l["y0"] < 0.10 or l["y1"] > 0.92) and bool(n) and
                        any(difflib.SequenceMatcher(None, n, h).ratio() > 0.85 for h in heads if h))
            lines = [l for l in lines if not head_like(l)]
            if n == c["start"] and lines and book.get("opener") == "after_title":
                # a book whose first line carries a drop cap OCR can't read: drop only the chapter's label and title
                # lines, keep the rest for a hand fix against the page image
                words, last = set(_norm(c["title"]).split()), -1
                for i, l in enumerate(lines[:6]):
                    ln = _norm(l["t"])
                    if l["y0"] < 0.35 and ln and (re.match(r"(chapter|part|epilogue|introduction|prologue)\b", ln)
                                                  or len(set(ln.split()) - words) <= 1
                                                  or difflib.SequenceMatcher(None, ln.replace(" ", ""), "".join(
                                                      sorted(words, key=_norm(c["title"]).find))).ratio() > 0.8):
                        last = i
                lines = lines[last + 1:]
            elif n == c["start"] and lines:  # the opener's display lines give way to the "## Title" heading
                fhs = [l["fh"] for l in lines if l.get("fh")]
                fh0 = statistics.median(fhs) if fhs else 0.012

                def display(l):
                    # set apart from the text: centred and clearly narrower than the measure, an ornament OCR read as
                    # letters, or type much larger than the text's
                    centered = abs((l["x0"] + l["x1"]) / 2 - 0.5) < 0.06 and (l["x1"] - l["x0"]) < 0.6
                    junk = l.get("conf") is not None and (l["conf"] < 45 or (l["conf"] < 60 and len(l["t"].split()) <= 3))
                    big = bool(l.get("fh")) and l["fh"] > fh0 * 1.6
                    return l["y0"] < 0.35 and (centered or junk or big or _is_heading(l, fh0))

                def texty(l):
                    t = l["t"]
                    return (len(t.split()) >= 4 and (l.get("conf") is None or l["conf"] >= 60)
                            and sum(ch.isalpha() for ch in t) / max(1, len(t)) > 0.6)
                k = 0
                while k < len(lines) and display(lines[k]):
                    k += 1
                lines = lines[k:]
                # a scan's opener (a chapter number set as an ornament, the title and passage over several lines)
                # can defeat that test; the running text starts at the first line that runs the full measure
                full = [i for i, l in enumerate(lines) if (l["x1"] - l["x0"]) > 0.6 and l["y0"] < 0.75 and texty(l)]
                if not c.get("front") and full and full[0] > 0 and lines[full[0]]["y0"] > 0.2:
                    lines = lines[full[0]:]
                tn = _norm(c["title"])
                while lines and lines[0]["y0"] < 0.35 and _norm(lines[0]["t"]) and _norm(lines[0]["t"]) in tn:
                    lines = lines[1:]                # the chapter's own title, repeated as its first line
            pls.append((n, lines, None))
            for l in lines:
                if l.get("conf") is not None and l["conf"] < 70:
                    low_conf.append((c["title"], n, l["conf"], l["t"]))
        blocks = _paragraphs(pls, vocab)
        # the opener's title, set over two or three lines, can survive as "subheads" on its first page: drop them
        tnorm = _norm(c["title"])
        blocks = [bk for bk in blocks if not (bk[0] == "head" and bk[2] == c["start"] and _norm(bk[1])
                                              and _norm(bk[1]) in tnorm)]
        md.append("")
        head = _curly(f"Chapter {_number_word(c['number'])}: {c['title']}" if c.get("number") else c["title"])
        md.append(f"## {head}")
        if c.get("passage"):
            md.append("")
            md.append("### " + re.sub(r"(?<=\d)-(?=\d)", "–", c["passage"]))
        words = 0
        for kind, text, pn in blocks:
            text = _curly(text) if kind != "mark" else text
            if kind == "mark":
                md.append(f"<!-- {text} -->")
            elif kind == "head":
                md.append("")
                md.append(f"### {text}")
            elif kind == "quote":
                md.append("")
                md.append("> " + text)
                words += len(text.split())
            else:
                md.append("")
                md.append(text)
                words += len(text.split())
        total_words += words
        srcs = collections.Counter(by_n[n]["src"] for n in range(c["start"], c["end"] + 1) if n in by_n)
        proof_rows.append((c["title"], c["start"], c["end"], words, srcs.get("ocr", 0)))
    return _finish_build(a, d, book, md, proof_rows, total_words, vocab, low_conf)


def _finish_build(a, d, book, md, proof_rows, total_words, vocab, low_conf):
    # Hand corrections from the proof, kept in book.json so a rebuild keeps them: each is an exact [from, to] read in
    # its sentence (and against the page image where the sentence wasn't enough). A fix that no longer matches is
    # reported, never silently dropped.
    text = "\n".join(md)
    missed = []
    for frm, to in book.get("fixes") or []:
        if frm in text:
            text = text.replace(frm, to)
        else:
            missed.append(frm)
    if missed:
        print(f"  {len(missed)} fixes no longer match: {missed[:5]}")
    if book.get("fixes"):                       # the hand corrections, readable, for whoever reviews them
        show = lambda s: s.replace("\n", " ⏎ ")
        rows = [f"# Hand corrections: {book['title']}", "",
                f"{len(book['fixes'])} corrections, each read in its sentence and, where text was garbled or missing, "
                "against the page image. Applied in this order by the build.", "",
                "| # | Built text | Corrected |", "|---|---|---|"]
        for k, (frm, to) in enumerate(book["fixes"], 1):
            x, z = show(frm), show(to)
            rows.append(f"| {k} | {x if len(x) < 140 else x[:70] + ' … ' + x[-60:]} | {z if len(z) < 140 else z[:70] + ' … ' + z[-60:]} |")
        (d / "corrections.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    md = text.split("\n")
    (d / "work.md").write_text(text + "\n", encoding="utf-8")

    # the proof worklist: what to check, with page numbers
    unknown = collections.Counter()
    for w in re.findall(r"\b[a-z]{4,}\b", text):
        if vocab[w] <= 1 and not _common(w):
            unknown[w] += 1
    glued = re.findall(r"\b[a-z]+[.,;:!?”\"’]\d{1,2}\b", re.sub(r"<!--.*?-->", "", text))
    pr = [f"# Proof worklist: {book['title']}", "",
          f"Chapters from {book.get('chapters_from', 'the hand map in book.json')}. {total_words:,} words. OCR pages: "
          f"{sum(r[4] for r in proof_rows)}.", "",
          "| Chapter | PDF pages | Words | OCR pages |", "|---|---|---|---|"]
    pr += [f"| {t} | {s}-{e} | {w:,} | {o} |" for t, s, e, w, o in proof_rows]
    pr += ["", f"## OCR lines read with low confidence ({len(low_conf)})", ""]
    pr += [f"- p{n} ({cf:.0f}) {t}" for _, n, cf, t in low_conf[:200]]
    # a likely reading for each: the one common word (or word this book uses) one letter away, or one of OCR's usual
    # confusions (ry/iy, y/v, li/h, rn/m). These are suggestions for the proof; nothing here changes the text.
    known = {w for w, k in vocab.items() if k >= 2} | (_COMMON or set())

    def suggest(w):
        swaps = [("iy", "ry"), ("v", "y"), ("hv", "lw"), ("rn", "m"), ("ii", "u"), ("cl", "d"), ("li", "h"), ("f", "t"),
                 ("1", "l"), ("0", "o"), ("io", "lo"), ("fiff", "fift")]
        for a_, b_ in swaps:
            if a_ in w and w.replace(a_, b_) in known:
                return w.replace(a_, b_)
        letters = "abcdefghijklmnopqrstuvwxyz"
        cands = {w[:i] + c + w[i + 1:] for i in range(len(w)) for c in letters} | \
                {w[:i] + w[i + 1:] for i in range(len(w))} | {w[:i] + c + w[i:] for i in range(len(w) + 1) for c in letters}
        hits = sorted(x for x in cands if x != w and x in known)
        return hits[0] if len(hits) == 1 else ""
    sug = {w: suggest(w) for w in unknown}
    pr += ["", f"## Words that appear once and aren't common English ({len(unknown)})", "",
           "Most are fine (names, modern words). Where a likely reading exists it follows the arrow; check it against "
           "the page.", "",
           ", ".join((f"{w} → {sug[w]}" if sug[w] else w) for w in sorted(unknown))[:8000], "",
           f"## Numbers stuck to words, possible note markers ({len(glued)})", "", ", ".join(glued[:200])]
    (d / "proof.md").write_text("\n".join(pr) + "\n", encoding="utf-8")
    print(f"{a.slug}: {len([r for r in proof_rows])} chapters, {total_words:,} words, {len(low_conf)} low-confidence "
          f"OCR lines, {len(unknown)} unusual words -> {d / 'work.md'}")


_COMMON = None


def _common(w: str) -> bool:
    """A word the Reading Room's own books use often (built once from books.db, cached)."""
    global _COMMON
    if _COMMON is None:
        cache = CACHE / "vocab.txt"
        if cache.exists():
            _COMMON = set(cache.read_text(encoding="utf-8").split())
        else:
            con = sqlite3.connect(ROOT / "db" / "books.db")
            cnt = collections.Counter()
            rows = con.execute("select c.html from book_chapters c join books b on b.id=c.book_id "
                               "where b.source='standardebooks' and c.book_id % 7 = 0 limit 4000")
            for (h,) in rows:
                cnt.update(w.lower() for w in re.findall(r"[A-Za-z]+", re.sub(r"<[^>]+>", " ", h or "")))
            _COMMON = {w for w, k in cnt.items() if k >= 3}
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text("\n".join(sorted(_COMMON)), encoding="utf-8")
    return w in _COMMON


# ---------------------------------------------------------------- load (after the proof)

def _chapters_from_work(text: str, rich: bool = False) -> list[dict]:
    """work.md -> chapter HTML for book_chapters. The house typesetting pass (webapp/typeset.py) makes the opener,
    the drop cap and the epigraph from this plain structure; nothing here styles anything."""
    esc = lambda t: _html.escape(t, quote=False)
    tex = re.compile(r"(\\\(.*?\\\)|\\\[.*?\\\])")

    def sup(t):
        # a note marker after a word's punctuation stays visible as a superscript; never inside TeX (rendered by KaTeX)
        parts = tex.split(t)
        for k in range(0, len(parts), 2):
            p = re.sub(r"(?<=[a-z][.,;:!?”’\"])(\d{1,2})\b", r"<sup>\1</sup>", parts[k])
            if not rich:                                 # bold and italics come only from a textbook transcription
                parts[k] = p
                continue
            p = re.sub(r"\*\*(\S(?:.*?\S)?)\*\*", r"<strong>\1</strong>", p)   # a term the book sets in bold
            parts[k] = re.sub(r"(?<![*\w])\*(\S(?:.*?\S)?)\*(?![*\w])", r"<em>\1</em>", p)
        return "".join(parts)

    def cells(row):
        return [c.strip() for c in row.strip().strip("|").split("|")]

    lines = [ln.rstrip() for ln in text.split("\n") if not ln.strip().startswith("<!--")]
    chapters, cur, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            cur = {"title": ln[3:].strip(), "body": []}
            chapters.append(cur)
        elif cur is None or not ln.strip():
            pass
        elif rich and ln.strip() == "\\[":             # a displayed equation set over several lines
            block = []
            i += 1
            while i < len(lines) and lines[i].strip() != "\\]":
                block.append(lines[i].strip())
                i += 1
            cur["body"].append("<p>\\[ " + esc(" ".join(block)) + " \\]</p>")
        elif rich and ln.lstrip().startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", lines[i + 1]):
            head = cells(ln)                            # a table: header row, separator row, body rows
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            cur["body"].append("<table><thead><tr>" + "".join(f"<th>{sup(esc(c))}</th>" for c in head) + "</tr></thead>"
                               "<tbody>" + "".join("<tr>" + "".join(f"<td>{sup(esc(c))}</td>" for c in r) + "</tr>"
                                                   for r in rows) + "</tbody></table>")
            continue
        elif rich and re.match(r"\s*[-*] \S", ln):     # a bulleted list
            items = []
            while i < len(lines) and re.match(r"\s*[-*] \S", lines[i]):
                items.append(sup(esc(re.sub(r"^\s*[-*] ", "", lines[i]).strip())))
                i += 1
            cur["body"].append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        elif rich and re.match(r"\[Figure\b", ln.strip()):   # a figure the transcription describes: its caption stays
            cur["body"].append(f'<p class="ex-figure"><em>{sup(esc(ln.strip()[1:-1] if ln.strip().endswith("]") else ln.strip()))}</em></p>')
        elif ln.startswith("### "):
            cur["body"].append(f"<h3>{esc(ln[4:].strip())}</h3>")
        elif ln.startswith("> "):
            block = []
            while i < len(lines) and lines[i].startswith("> "):
                block.append(sup(esc(lines[i][2:].strip())))
                i += 1
            # consecutive short lines are verse (a hymn's stanza): line breaks, which the house pass sets as a stanza
            verse = len(block) > 1 and all(len(x) < 70 for x in block)
            cur["body"].append("<blockquote><p>" + ("<br>" if verse else " ").join(block) + "</p></blockquote>")
            continue
        elif ln.startswith("[sig] "):
            cur["body"].append(f'<p class="ex-cite">{esc(ln[6:].strip())}</p>')   # the quotation's attribution
        else:
            cur["body"].append(f"<p>{sup(esc(ln.strip()))}</p>")
        i += 1
    out = []
    for n, c in enumerate(chapters, 1):
        h = f'<h2 class="ex-keep">{esc(c["title"])}</h2>\n' + "\n".join(c["body"])   # the book's own heading
        words = len(re.sub(r"<[^>]+>", " ", h).split())
        out.append({"section_number": n, "title": c["title"], "html": h, "words": words})
    return out


def cmd_load(a):
    d = CACHE / a.slug
    book = json.loads((d / "book.json").read_text(encoding="utf-8"))
    if not book.get("rights"):
        raise SystemExit("book.json needs a 'rights' line (from the book's copyright page) before loading.")
    chapters = _chapters_from_work((d / "work.md").read_text(encoding="utf-8"), rich=book.get("kind") == "vision")
    if not chapters:
        raise SystemExit("work.md has no chapters.")
    con = sqlite3.connect(a.db)
    try:
        cols = {c[1] for c in con.execute("pragma table_info(books)")}
        if "access" not in cols:
            con.execute("alter table books add column access text")      # NULL = everyone; 'school' = YCS accounts
        cur = con.cursor()
        row = cur.execute("select id from books where slug=?", (book["slug"],)).fetchone()
        if row:
            cur.execute("delete from book_chapters where book_id=?", (row[0],))
            cur.execute("delete from books where id=?", (row[0],))
        author = book["author"]
        parts = author.rsplit(" ", 1)
        author_sort = book.get("author_sort") or (f"{parts[1]}, {parts[0]}" if len(parts) == 2 else author)
        shelf = json.dumps(book.get("shelf") or ["Christianity"])
        wc = sum(c["words"] for c in chapters)
        ded = (book.get("dedication") or "").strip()
        front = ('<div class="ex-dedication">' + "".join(f"<p>{_html.escape(x, quote=False)}</p>" for x in ded.split("\n") if x.strip())
                 + "</div>") if ded else ""
        for ep in book.get("epigraphs") or []:      # {"lines": [...], "cite": "..."}: verse or prose set before the text
            esc = lambda x: _html.escape(x, quote=False)
            body = "".join(f"<span>{esc(x)}</span>" for x in ep["lines"]) if len(ep["lines"]) > 1 else esc(ep["lines"][0])
            front += (f'<div class="ex-epigraph"><blockquote><p>{body}</p>'
                      + (f"<cite>{esc(ep['cite'])}</cite>" if ep.get("cite") else "") + "</blockquote></div>")
        front = front or None
        cur.execute(
            """insert into books(slug,title,author,author_sort,source,license,us_clear,language,subjects,genres,section,
                                 genres_backup,title_backup,cover_url,chapter_count,word_count,access,front_html,added_at)
               values(?,?,?,?,?,?,0,'en','[]',?,?,?,?,null,?,?,?,?,datetime('now'))""",
            (book["slug"], book["title"], author, author_sort, "school", book["rights"], shelf, shelf, shelf,
             book["title"], len(chapters), wc, book.get("access") or "school", front))
        bid = cur.lastrowid
        cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                        [(bid, c["section_number"], c["title"], c["html"], c["words"]) for c in chapters])
        con.commit()
    finally:
        con.close()
    print(f"{book['slug']}: loaded {len(chapters)} chapters, {wc:,} words, {book.get('access') or 'school'}-only, into {a.db}")


def cmd_flow(a):
    """A PDF whose chapters start mid-page (a text file set as a PDF): rebuild the paragraphs across every page into a
    block stream, the same one an EPUB gives, so chapters are mapped by the paragraph they start at. Writes
    blocks.jsonl and a book.json of kind "flow" with one chapter for the whole text, to be divided by hand."""
    d = CACHE / a.slug
    pages = _load_pages(a.slug)
    title_norm = _norm(a.title or a.slug)
    vocab = _vocab(" ".join(l["t"] for p in pages for l in p["lines"]))
    lo, hi = a.first or pages[0]["n"], a.last or pages[-1]["n"]
    pls = [(p["n"], _body_lines(p, title_norm), None) for p in pages if lo <= p["n"] <= hi]
    out = []
    for kind, text, pn in _paragraphs(pls, vocab):
        if kind == "mark":
            continue
        out.append({"k": {"head": "h", "quote": "q"}.get(kind, "p"), "lv": None, "f": pn, "cls": "", "t": text})
    with open(d / "blocks.jsonl", "w", encoding="utf-8") as f:
        for b in out:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    bp = d / "book.json"
    book = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    book.update({"slug": a.slug, "title": a.title or book.get("title", ""), "author": a.author or book.get("author", ""),
                 "access": "school", "kind": "flow", "chapters_from": f"paragraph stream, PDF pages {lo}-{hi}",
                 "text_ends": len(out) - 1})
    book.setdefault("rights", ""); book.setdefault("dedication", ""); book.setdefault("isbn", "")
    book["chapters"] = [{"title": "Whole text", "start": 0, "end": len(out) - 1}]
    bp.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.slug}: {len(out)} paragraphs from PDF pages {lo}-{hi} -> blocks.jsonl; map the chapters in book.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("pdf"); e.add_argument("--slug", required=True)
    e.add_argument("--ocr-all", action="store_true", help="OCR every page too (to compare with the text layer)")
    e.add_argument("--fresh", action="store_true", help="redo OCR even for pages already read")
    p = sub.add_parser("propose"); p.add_argument("slug"); p.add_argument("--title")
    p.add_argument("--author")
    p.add_argument("--toc-under", help="EPUB: one book of a collection, by the start of its contents entry")
    p.add_argument("--toc-depth", type=int, help="EPUB: which level of the contents list holds the chapters")
    p.add_argument("--headings", help="EPUB: use the book's own headings instead, e.g. h2 or h1,h2"); p.add_argument("--isbn"); p.add_argument("--edition"); p.add_argument("--rights")
    fl = sub.add_parser("flow", help="a PDF whose chapters start mid-page: paragraphs across all pages as blocks")
    fl.add_argument("slug"); fl.add_argument("--title"); fl.add_argument("--author")
    fl.add_argument("--first", type=int, help="first PDF page of the text"); fl.add_argument("--last", type=int)
    b = sub.add_parser("build"); b.add_argument("slug")
    l = sub.add_parser("load"); l.add_argument("slug"); l.add_argument("--db", default=str(ROOT / "db" / "books.db"))
    a = ap.parse_args()
    {"extract": cmd_extract, "propose": cmd_propose, "flow": cmd_flow, "build": cmd_build, "load": cmd_load}[a.cmd](a)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
