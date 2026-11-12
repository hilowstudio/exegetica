"""Bring a public-domain commentary that exists only as an archive.org scan into the Reading Room (first: Westcott,
Godet and Ryle on John for the Bible II shelf, 2026-11-11).

Each page is read by scripts/vision_transcribe.py --style commentary (Claude Haiku: Greek, italics, footnotes as
[^n], the printed Bible text between <scripture> tags). A page the API's content filter blocks is read by Tesseract
with the English and Ancient Greek models instead (.seed_cache/tessdata holds eng + grc from tessdata_best), which
keeps the Greek but not italics. The steps, each re-runnable:

    python scripts/seed_pd_scan.py ocr <work>        Tesseract (eng+grc) for every page vision could not give
    python scripts/seed_pd_scan.py heads <work>      every heading with its page: the raw material for the chapter map
    python scripts/seed_pd_scan.py build <work>      work.md (the book) and proof.md (what to check by eye)
    python scripts/seed_pd_scan.py page <work> <n>   the page image, to read a spot against the scan
    python scripts/seed_pd_scan.py load <work>       into db/books.db, for everyone (PD-US)

What the build does:
- drops the printed Bible text (the Reading Room serves Scripture itself; house rule since 2026-09-19): <scripture>
  blocks on vision pages, and on OCR pages any paragraph whose word 4-grams are mostly KJV John;
- drops running heads, page numbers, marginal references, and the pages the work's spec leaves out (title pages,
  contents, a translator's preface: no translator or editor credit in our books, indexes, publisher's lists);
- joins a paragraph a page break split, and a word a page break hyphenated;
- splits chapters where the spec's chapter map says, and numbers footnotes per chapter as [n] markers with
  "[n] text" paragraphs at the chapter's end, which webapp/typeset.py turns into notes;
- applies the spec's corrections ([from, to] pairs in .seed_cache/school/<cache>/fixes.json), refusing any that no
  longer match.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import html
import io
import json
import re
import sqlite3
import statistics
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "school"
SCANS = ROOT / ".seed_cache" / "pd_scans"
TESSDATA = ROOT / ".seed_cache" / "tessdata"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SPECS = ROOT / "scripts" / "pd_scan_works.json"     # per work: slug, title, author, pdf, pages to drop, chapter map


def spec(work: str) -> dict:
    works = json.loads(SPECS.read_text(encoding="utf-8"))
    if work not in works:
        raise SystemExit(f"no work {work!r} in {SPECS.name}: {', '.join(works)}")
    s = works[work]
    s["dir"] = CACHE / s["cache"]
    return s


def dropped(s: dict) -> set[int]:
    out = set()
    for r in s.get("drop", []):
        a, b = (r, r) if isinstance(r, int) else r
        out |= set(range(a, b + 1))
    return out


def pdf_path(s: dict) -> Path:
    """The work's PDF: a bare name lives in .seed_cache/pd_scans; a path (book-copies/...) is relative to the repo."""
    return ROOT / s["pdf"] if "/" in s["pdf"] else SCANS / s["pdf"]


def n_pages(s: dict) -> int:
    import pypdfium2 as pdfium
    return len(pdfium.PdfDocument(str(pdf_path(s))))


# ---------------------------------------------------------------- ocr

def cmd_ocr(a):
    import pypdfium2 as pdfium
    s = spec(a.work)
    vis, out = s["dir"] / "vision", s["dir"] / "ocr"
    out.mkdir(parents=True, exist_ok=True)
    skip = dropped(s)
    # every page for a school copy (no transcription is run); otherwise the pages the content filter blocked
    todo = [n for n in range(1, n_pages(s) + 1) if n not in skip and (s.get("ocr_all") or (vis / f"p{n:04d}.blocked").exists())
            and not (vis / f"p{n:04d}.md").exists() and not (out / f"p{n:04d}.tsv").exists()]
    print(f"{a.work}: {len(todo)} pages to OCR", flush=True)
    lock, local = threading.Lock(), threading.local()

    def tess(im, psm: str) -> str:
        buf = io.BytesIO()
        im.save(buf, "PNG")
        r = subprocess.run([TESSERACT, "stdin", "stdout", "--tessdata-dir", str(TESSDATA), "-l", s.get("ocr_lang", "eng+grc"),
                            "--psm", psm, "-c", "tessedit_create_tsv=1"], input=buf.getvalue(), capture_output=True)
        return r.stdout.decode("utf-8", errors="replace")

    def one(n):
        with lock:                                   # pdfium is not thread-safe: open, load and render one at a time
            if not hasattr(local, "pdf"):
                local.pdf = pdfium.PdfDocument(str(pdf_path(s)))
            pg = local.pdf[n - 1]
            w, h = pg.get_size()
            im = pg.render(scale=3000 / max(w, h)).to_pil().convert("L")
        if s.get("columns") != 2:
            (out / f"p{n:04d}.tsv").write_text(tess(im, "3"), encoding="utf-8")
            return
        # Two columns: Tesseract run over the whole page merges lines across the gutter, so each column is read
        # alone. The gutter is the least-inked vertical strip near the middle (below the running head).
        W, H = im.size
        px = im.load()
        band = range(int(H * 0.08), int(H * 0.95), 4)
        ink = {x: sum(px[x, y] < 128 for y in band) for x in range(int(W * 0.42), int(W * 0.58), 2)}
        g = min(ink, key=ink.get)
        rows = []
        for half, (x0, x1) in enumerate(((0, g), (g, W))):
            tsv = tess(im.crop((x0, 0, x1, H)), "4")
            for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
                if r.get("level") == "1":
                    if half == 0:
                        r["width"], r["height"] = str(W), str(H)
                        rows.append(r)
                    continue
                r["left"] = str(int(r["left"]) + x0)
                r["block_num"] = str(int(r["block_num"]) + 500 * half)
                rows.append(r)
        f = io.StringIO()
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t", quoting=csv.QUOTE_NONE,
                            escapechar="\\")
        wr.writeheader()
        wr.writerows(rows)
        (out / f"p{n:04d}.tsv").write_text(f.getvalue(), encoding="utf-8")

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for k, f in enumerate(cf.as_completed([ex.submit(one, n) for n in todo]), 1):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001  the page stays to do on a rerun
                print("  page failed:", repr(e)[:160], flush=True)
            if k % 25 == 0:
                print(f"  {k}/{len(todo)}", flush=True)
    print("done", flush=True)


# ---------------------------------------------------------------- pages -> blocks

_kjv: set | None = None


def kjv_grams() -> set:
    global _kjv
    if _kjv is None:
        con = sqlite3.connect(f"file:{ROOT / 'db' / 'study_bible.db'}?mode=ro", uri=True)
        words = []
        for (t,) in con.execute("select text from translations where translation='KJV' and book='Jhn' "
                                "order by chapter, verse"):
            words += re.findall(r"[a-z]+", t.lower())
        _kjv = {tuple(words[i:i + 4]) for i in range(len(words) - 3)}
    return _kjv


def is_kjv(text: str) -> bool:
    w = re.findall(r"[a-z]+", text.lower())
    grams = [tuple(w[i:i + 4]) for i in range(len(w) - 3)]
    return len(grams) >= 3 and sum(g in kjv_grams() for g in grams) / len(grams) >= 0.6


META = re.compile(r"(nothing (else )?to transcribe|no (legible |other )?printed text|no text to transcribe|"
                  r"output is empty|^the (page|image) (appears|is|shows|contains)|^this page (appears|is|contains)|"
                  r"^#*\s*\(?(left|right) column\)?\s*$|running head omitted)", re.I)
LOOKALIKE = str.maketrans("ΑΒΕΗΙΚΜΝΟΡΤΥΧΖ", "ABEHIKMNOPTYXZ")


def is_head(t: str, heads: list[str]) -> bool:
    """A running head the transcriber kept: the book's or chapter's title, maybe with a page number or verse range.
    OCR may read its capitals as Greek lookalikes (ΤΗΕ) and its page number as letters."""
    x = t.translate(LOOKALIKE)
    x = re.sub(r"\[?\b[vV]\.\s*\d+.*$|\b\d+\b|^\W*[ivxlcIVXLC]+\b\W*(?=[A-Z])|\b[ivxlc]+\b\s*$", "", x)
    x = re.sub(r"[^A-Za-z]+", " ", x).strip().upper()
    return bool(x) and len(t) < 60 and any(re.fullmatch(h, x) for h in heads)


def vision_page(n: int, text: str, heads: list[str] | None = None) -> tuple[list, list]:
    """A transcribed page -> (blocks, notes). Blocks are [kind, text]; notes [key, text] with page-unique keys."""
    text = re.sub(r"<scripture>.*?(</scripture>|\Z)", "", text, flags=re.S)
    text = re.sub(r"\A.*?</scripture>", "", text, flags=re.S)        # a closing tag alone: the block began earlier
    notes, keep = [], []
    # The transcriber sometimes writes a footnote as "¹ text" (with "word¹" in the text) instead of "[^1]: text".
    # A superscript-numbered line in the lower part of the page is a note; its mark in the text becomes [^k].
    lines = text.split("\n")
    # "\* note" / "† note" lines in the lower part of the page are symbol footnotes; "\*" / "†" after a word marks them
    sym = {}
    for i, ln in enumerate(lines):
        m = re.match(r"\s*(\\\*\\\*|\\\*|†|‡|§)\s+(\S.*)", ln)
        if m and i >= len(lines) * 0.4:
            key = {"\\*": "s1", "\\*\\*": "s2", "†": "s3", "‡": "s4", "§": "s5"}[m.group(1)]
            sym[m.group(1)] = key
            lines[i] = f"[^{key}]: {m.group(2)}"
    for mark, key in sorted(sym.items(), key=lambda x: -len(x[0])):
        rx = re.compile(r"(?<=[A-Za-zÀ-ÿ.,;:!?”’\"')\]])" + re.escape(mark))
        lines = [ln if ln.startswith("[^") else rx.sub(f"[^{key}]", ln) for ln in lines]
    sup = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    sup_keys = set()
    for i, ln in enumerate(lines):
        m = re.match(r"\s*([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s+(\S.*)", ln)
        if m and i >= len(lines) * 0.4:
            k = m.group(1).translate(sup)
            sup_keys.add(m.group(1))
            lines[i] = f"[^{k}]: {m.group(2)}"
    if sup_keys:
        rx = re.compile(r"(?<=[A-Za-zÀ-ÿͰ-Ͽἀ-῿.,;:!?”’\"')\]*])(" +
                        "|".join(sorted(map(re.escape, sup_keys), key=len, reverse=True)) + r")(?![⁰¹²³⁴⁵⁶⁷⁸⁹])")
        lines = [ln if ln.startswith("[^") else rx.sub(lambda m: f"[^{m.group(1).translate(sup)}]", ln)
                 for ln in lines]
    for ln in lines:
        m = re.match(r"\s*\[\^([^\]]+)\]:\s*(.*)", ln)
        if m:
            notes.append([f"{n}-{m.group(1)}", m.group(2).strip()])
            continue
        if re.match(r"\s*\^[a-z]\b", ln):                              # a marginal reference to the Bible text
            continue
        keep.append(ln)
    body = re.sub(r"\[\^([^\]]+)\]", lambda m: f"[^{n}-{m.group(1)}]", "\n".join(keep))
    blocks = []
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para or META.search(para):
            continue
        if not blocks and heads and is_head(para.lstrip("# "), heads):
            continue
        m = re.match(r"(#+)\s+(.*)", para, re.S)
        if m:
            blocks.append(["h2" if len(m.group(1)) <= 2 else "h3", " ".join(m.group(2).split())])
        elif all(l.startswith(">") for l in para.split("\n")):
            blocks.append(["quote", " ".join(l.lstrip("> ").strip() for l in para.split("\n"))])
        else:
            blocks.append(["p", " ".join(l.strip() for l in para.split("\n"))])
    return blocks, notes


NOTE_START = re.compile(r"^[\d‘'?*¹²³⁴⁵⁶⁷⁸⁹]{1,3}\s?(?=[A-Z“‘(])")


def reconcile(n: int, blocks: list, notes: list, want: int, numbered: bool = False) -> None:
    """Bring the page's notes to the number of marks the page image shows (`want`), in place: recover notes the zone
    test left in the body, split notes set side by side on one line, and merge a note split at an indented line."""
    own = [x for x in notes if not x[0].endswith("-cont")]
    cont = [x for x in notes if x[0].endswith("-cont")]
    # notes the zone test missed: the page's last body paragraphs, each starting with a misread note number
    moved = []
    # (not where notes print their numbers: there the zone is reliable, and a verse comment "28 The…" looks like one)
    while (not numbered and len(own) + len(moved) < want and blocks and blocks[-1][0] == "p"
           and NOTE_START.match(blocks[-1][1])):
        moved.insert(0, blocks.pop()[1])
    own = [[None, NOTE_START.sub("", t, count=1)] for t in moved] + own
    # two short notes set on one line: "Ibid., p. 25. 2Ibid., p. 26."
    i = 0
    while len(own) < want and i < len(own):
        m = re.search(r"(?<=[.)])\s+(?:[\d?‘'*]{1,2}(?=[A-Z][a-z])|\d(?=[A-Z]{2,}\b|[A-Z]\d)|\*(?=Ibid))", own[i][1])
        if m:
            own[i:i + 1] = [[None, own[i][1][:m.start()].strip()], [None, own[i][1][m.end():].strip()]]
        else:
            i += 1
    # a note split at an indented line: the second part starts in lower case or the first does not end a sentence
    i = 1
    while len(own) > want and i < len(own):
        prev, cur = own[i - 1][1], own[i][1]
        if cur[:1].islower() or cur[:1] in ",;:)" or not re.search(r"[.!?”’)]\s*$", prev):
            own[i - 1][1] = prev + " " + cur
            del own[i]
        else:
            i += 1
    notes[:] = cont + [[f"{n}-{k}", t] for k, (_, t) in enumerate(own, 1)]


def link_marks(n: int, blocks: list, notes: list, marks: list, numbered: bool = False) -> None:
    """Footnote marks located on the page image (scripts/note_marks.py: each mark and the words just before it):
    find those words in the OCR text, after the previous mark, and put [^n-k] there for the page's k-th note."""
    nk = lambda w: re.sub(r"[^a-z0-9Ͱ-Ͽἀ-῿]", "", w.lower())
    reconcile(n, blocks, notes, len(marks), numbered)
    toks = []                                          # (block index, start, end, normalized) for every word
    # the mark itself, read as a digit after the word's closing punctuation ("25).1", "significant,1"), is not
    # part of the word
    raised = re.compile(r"(?<=[.,;:!?)’”'\"])[!*°¹²³⁴⁵⁶⁷⁸⁹0-9?]{1,2}$")
    for bi, b in enumerate(blocks):
        for m in re.finditer(r"\S+", b[1]):
            if nk(m.group(0)):
                toks.append((bi, m.start(), m.end(), nk(raised.sub("", m.group(0)))))
    keys = [k for k, _ in notes if not k.endswith("-cont")]
    pos, inserts = 0, []
    for i, mk in enumerate(marks):
        raw = [w for w in str(mk.get("before", "")).split() if nk(w)]
        want = [nk(w) for w in raw]
        broken = bool(raw) and raw[-1].endswith("-")     # "put for-": the mark follows the whole word, "forward"
        # a word joined to the one before it in print ("El-Azariyeh." for "Azariyeh.") matches at its end
        same = lambda got, exp, last, first=False: (got.startswith(exp) if (last and broken) else
                                                     got == exp or (first and len(exp) >= 5 and got.endswith(exp)))
        hit = None
        for size in (min(4, len(want)), 3, 2, 1):      # the last few words, fewer if OCR misread one of them
            if size < 1 or size > len(want):
                continue
            tail = want[-size:]
            for j in range(pos, len(toks) - size + 1):
                if all(same(toks[j + q][3], tail[q], q == size - 1, q == 0) for q in range(size)):
                    hit = j + size - 1
                    break
            if hit is not None:
                break
        if hit is None or i >= len(keys):
            continue
        pos = hit + 1
        inserts.append((toks[hit], keys[i], raw[-1] if raw else ""))
    for (bi, st, en, _), key, exp in sorted(inserts, key=lambda x: (x[0][0], -x[0][2])):
        word = blocks[bi][1][st:en]
        q = lambda w: len(w) - len(w.rstrip("’'”\""))
        if q(word) > q(exp):                           # a quote mark that is really the misread mark
            word = word[:len(word) - (q(word) - q(exp))]
        # the mark OCR read as a stray character at the word's end ("Self.’!", "God’.*", "eaten’).!")
        word = re.sub(r"(?<=[.,;:!?)’”'\"])[!*°¹²³⁴⁵⁶⁷⁸⁹0-9?]{1,3}$|(?<=[a-z])[*°¹²³⁴⁵⁶⁷⁸⁹]{1,2}$", "", word)
        blocks[bi][1] = blocks[bi][1][:st] + word + f"[^{key}]" + blocks[bi][1][en:]
    if len(inserts) != len(keys) or len(marks) != len(keys):
        MARK_MISMATCH.append((n, len(marks), len(keys), len(inserts)))


MARK = "⁣"                                    # a placeholder for a footnote mark found on an OCR page
MARK_MISMATCH: list = []                             # (page, marks found, notes) where they could not be paired


# a section heading's closing reference: "(3:22-30)", "(10:6)", "(15:17 — 16:4a)", with a speck or two after it
REF_END = r"\(\d{1,2}:\d{1,2}[a-z]?(?:\s*[-–—]+\s*\d{1,2}(?::\d{1,2})?[a-z]?)?\)(?:\s+\S{1,2})?$"
ENUM = r"^(\d{1,2}|[A-Za-z]|[IVX]{1,4})[.,]\s+\S"
NOTE_NUM = r"^\d{1,3}\s?[.,]\s?(?=\S)"            # a footnote's printed number: "36. ", "77, ", "37.5ΒΚ" (SBk)


def ocr_page(n: int, tsv: str, heads: list[str], scripture_larger: bool = False,
             note_zone: bool = False, raised_marks: bool = False, marks: list | None = None,
             top_heads: list | None = None, table: float = 0, num_heads: bool = False,
             outline: bool = False, numbered: bool = False) -> tuple[list, list]:
    by_order = raised_marks or marks is not None     # notes keyed by their order on the page
    """A Tesseract TSV page -> (blocks, notes)."""
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE))
    words = [r for r in rows if r.get("level") == "5" and (r.get("text") or "").strip()]
    if not words:
        return [], []
    H = max(int(r["top"]) + int(r["height"]) for r in rows if r.get("level") == "1") or 1
    W = max(int(r["left"]) + int(r["width"]) for r in rows if r.get("level") == "1") or 1
    lines: dict = {}
    for r in words:
        k = (int(r["block_num"]), int(r["par_num"]), int(r["line_num"]))
        lines.setdefault(k, []).append(r)
    L = []
    for k, ws in lines.items():
        if raised_marks:
            # a footnote mark: a raised character OCR read as ’ ! * ° or a digit, stuck to a word; set a placeholder
            mt = statistics.median(int(w["top"]) for w in ws)
            mh = statistics.median(int(w["height"]) for w in ws)
            for w in ws:
                m = re.match(r"^(.*?[A-Za-z.,;:)’”'\]])([’'!*°\"”¹²³⁴1-9]{1,2})$", w["text"])
                up = int(w["top"]) < mt - 0.12 * mh
                if m and (m.group(2)[0] in "!*°¹²³⁴" or up):
                    w["text"] = m.group(1) + MARK
        t = " ".join(w["text"] for w in ws)
        top = min(int(w["top"]) for w in ws)
        left = min(int(w["left"]) for w in ws)
        right = max(int(w["left"]) + int(w["width"]) for w in ws)
        hgt = sorted(int(w["height"]) for w in ws)[len(ws) // 2]
        L.append({"k": k, "t": t, "top": top, "left": left, "right": right, "h": hgt})
    L.sort(key=lambda x: x["k"])
    body_h = sorted(l["h"] for l in L)[len(L) // 2]
    if numbered and not isinstance(numbered, bool):   # the work's text height: on a page mostly notes the median
        body_h = numbered                             # line is a note's
    lefts = sorted(l["left"] for l in L)
    main_left = lefts[len(lefts) // 10]
    keep = []
    for l in L:
        letters = sum(c.isalpha() for c in l["t"])
        ns = l["t"].replace(" ", "")
        refs = re.search(r"\d", ns) and (len(ns) >= 10 or (letters and len(ns) >= 4 and l["top"] < 0.9 * H))
        if num_heads and re.search(r"\d", ns):        # a modern book's notes: short last lines are text too
            refs = refs or ((letters and len(ns) >= 4) or re.fullmatch(r"\(?\d{1,4}[-–—]\d{1,4}\)?[.,;:)]*", ns)
                            or re.fullmatch(r"\d{1,4}[.,;:)]{1,2}", ns))        # "29-63.", a note's "409." (not "679")
        if (letters < 0.35 * len(ns) or letters < 2) and not refs and not re.search(REF_END, l["t"].strip()):
            continue          # margin specks, rules, page numbers; not references ("2:4; 3:3, 5, 15-16;", "v. 18a.")
        if top_heads is not None:
            if l["top"] < 0.075 * H and any(re.search(h, l["t"]) for h in top_heads):
                continue                                               # one of the work's running heads
        elif l["top"] < 0.075 * H and len(l["t"]) < 30:
            continue                                                   # a running head, or half of one
        if l["top"] < 0.09 * H and (re.search(r"^\d+\s|\s\d+$|^\[", l["t"]) or is_head(l["t"], heads)):
            continue                                                   # the running head
        if l["right"] < main_left + 0.01 * W and len(l["t"]) < 20:
            continue                                                   # a marginal reference
        keep.append(l)
    if numbered and keep:
        # the NIV's translation notes under its printed text ("a. 22 That is, Hanukkah", "c. 29 Many early
        # manuscripts … / all"): small lines from a lettered one until text-size type or a footnote's number
        drop_ids, run = set(), False
        for l in sorted(keep, key=lambda l: l["top"]):
            small_ = l["h"] < 0.92 * body_h
            if small_ and re.match(r"^[a-z]\.\s+\d{1,2}(:\d{1,2})?\s", l["t"].strip()):
                run = True
            elif not small_ or re.match(NOTE_NUM, l["t"].strip()):
                run = False
            if run:
                drop_ids.add(id(l))
        keep = [l for l in keep if id(l) not in drop_ids]
    if table and keep:
        # a two-column list (abbreviation | entry with a hanging indent): pair each entry with the abbreviation
        # set level with its first line; OCR reads the two columns as separate blocks
        # the split: the widest gap between line starts, the abbreviation column's and the entries'
        ls = sorted(l["left"] for l in keep if len(l["t"].strip()) >= 6)   # not a page number ("xvi")
        gaps = [(b - a, (a + b) / 2) for a, b in zip(ls, ls[1:]) if (a + b) / 2 < 0.5 * W]
        split = max(gaps)[1] if gaps and max(gaps)[0] > 0.08 * W else table * W
        left = sorted((l for l in keep if l["left"] < split), key=lambda l: l["top"])
        right = sorted((l for l in keep if l["left"] >= split), key=lambda l: l["top"])
        rl = sorted(l["left"] for l in right)
        start = rl[len(rl) // 4] if rl else 0          # the hanging line's edge, not a stray fragment's
        entries = []
        for l in right:
            level = any(abs(a["top"] - l["top"]) < 0.6 * body_h for a in left)
            # a list without a hanging indent (Morris): an entry starts only beside its abbreviation
            if not entries or (level if numbered else l["left"] < start + 0.02 * W):
                entries.append([l["top"], l["t"].strip()])
            else:
                prev = entries[-1][1]
                entries[-1][1] = prev[:-1] + l["t"].strip() if prev.endswith("-") and l["t"][:1].islower() \
                    else prev + " " + l["t"].strip()
        out = []
        for top, text in entries:
            near = [a for a in left if abs(a["top"] - top) < 0.6 * body_h]
            ab = near[0]["t"].strip() if near else ""
            out.append(["p", (f"**{ab}** " if ab else "") + text])
        return out, []
    zone_notes = []
    if note_zone and keep:
        # Footnotes in small type at the foot of the page, read apart from the body (Tesseract can interleave the
        # two): the zone starts after a wider-than-usual gap, below mid-page, where most lines are small.
        by_top = sorted(keep, key=lambda l: l["top"])
        lead = sorted(b["top"] - a["top"] for a, b in zip(by_top, by_top[1:]) if b["top"] > a["top"])
        lead = lead[len(lead) // 2] if lead else body_h * 1.5
        for i in range(1, len(by_top)):
            zone = by_top[i:]
            gap = by_top[i]["top"] - by_top[i - 1]["top"]
            # mostly footnote type: italics and a line run into the rule above the notes measure tall, so the
            # zone's middle line height decides as well as the count
            small = (sum(l["h"] < 0.88 * body_h for l in zone) >= 0.75 * len(zone)
                     or sorted(l["h"] for l in zone)[len(zone) // 2] < 0.85 * body_h)
            # a raised note number OCR misread at the start of the zone's first line: "1For", "‘Raymond", "ἮΝ."
            marked = re.match(r"^(\d{1,3}(?=[A-Z‘“(])|[‘’'*¹²³⁴⁵⁶⁷⁸⁹†]|[Ͱ-Ͽἀ-῿]{1,2}\.?\s)",
                              by_top[i]["t"].strip())
            # a raised "1" read as a straight or curly double quote ('"Cf. I. Abrahams'): a note only where the
            # zone is set smaller than the text, since a quotation can open a paragraph too
            marked = marked or (re.match(r'^["“](?=[A-Z])', by_top[i]["t"].strip())
                                and sorted(l["h"] for l in zone)[len(zone) // 2] < 0.97 * body_h)
            first_small = by_top[i]["h"] < 0.88 * body_h      # the zone's own first line is footnote type
            # a wide gap (two blank lines and more) low on the page, over type a little smaller than the text's:
            # Carson's notes measure 0.87-0.9 of the body, so the tests above miss them
            # (a line or two of italics measures tall, so the zone's lower quarter decides; a one-line note needs a
            # wider gap still)
            zh = sorted(l["h"] for l in zone)
            ft = by_top[i]["t"].strip()
            fl = [c for c in ft if c.isalpha()]
            opens_text = (re.match(r"^(\d{1,2}(-\d{1,2})?|[A-Z]|[IVX]{1,4})[.,]\s", ft)   # "25. It is", "C. THE"
                          or (len(fl) >= 6 and sum(c.isupper() for c in fl) >= 0.85 * len(fl)))
            wide = (by_order and not opens_text and gap > 2.5 * lead and by_top[i]["top"] > 0.6 * H
                    and ((len(zone) >= 2 and zh[len(zone) // 4] <= 0.92 * body_h)
                         or (len(zone) == 1 and gap > 2.8 * lead and zh[0] <= 0.92 * body_h)))
            # notes that print their own numbers ("36. Among the Qumran…", Morris): the zone is the page's foot
            # set in smaller type (0.85-0.88 of the text), after a gap, opening at a numbered note or carrying one
            # over from the page before
            nsmall = sum(l["h"] < 0.92 * body_h for l in zone)
            num_zone = (numbered and gap > 1.3 * lead
                        and ((by_top[i]["top"] > 0.4 * H and nsmall >= 0.8 * len(zone))
                             or (by_top[i]["top"] > 0.2 * H and nsmall >= 0.85 * len(zone) and len(zone) >= 6))
                        and (re.match(NOTE_NUM, ft) or by_top[i]["h"] < 0.92 * body_h)
                        and not re.match(r"^[a-z]\.\s+\d", ft))           # the NIV's own "a. 22 That is…"
            if num_zone or (not numbered and by_top[i]["top"] > 0.5 * H and (
                    (gap > 1.25 * lead and small and first_small) or (by_order and gap > 1.8 * lead and marked)
                    or wide)):
                mid = (min(l["left"] for l in zone) + max(l["right"] for l in zone)) / 2
                two = sum(l["left"] > mid - 10 for l in zone) >= 2 and all(l["right"] < mid + 60 or l["left"] > mid - 60
                                                                          for l in zone)
                zone.sort(key=lambda l: ((l["left"] > mid - 10) if two else 0, l["top"]))
                ids = {id(l) for l in zone}
                keep = [l for l in keep if id(l) not in ids]
                cur = None
                zl = min(l["left"] for l in zone)
                seq = 0
                for l in zone:
                    t = l["t"].strip()
                    m = re.match(r"^([*†‡]|§(?!\s?[IVX]+\b)|\?(?=[A-Z])|\d{1,2})\s?(?=[A-Z“\"‘(*])(.*)", t)
                    indented = l["left"] > zl + 0.012 * W
                    cont = (cur is None and not indented and not m and len(zone) > 1
                            and any(zl + 0.012 * W < z["left"] < zl + 0.15 * W for z in zone[1:])  # an indent, not a
                            and not marked)                                                     # speck at the right
                    # "Ibid." opens a note even set level with the note above (its raised number lost)
                    ibid = cur is not None and re.match(r"^\W{0,2}(Ibid|Idem)\b", t) and re.search(r"[.)]$", cur[1])
                    if numbered:                # a note starts only at its printed number; quotations indent too
                        nm = re.match(NOTE_NUM, t) if indented or cur is None else None
                        if nm:
                            seq += 1
                            cur = [f"{n}-{seq}", t[nm.end():].strip()]
                            zone_notes.append(cur)
                        elif cur is None:
                            cur = [f"{n}-cont", t]
                            zone_notes.append(cur)
                        elif cur[1].endswith("-") and t[:1].islower():
                            cur[1] = cur[1][:-1] + t
                        else:
                            cur[1] += " " + t
                        continue
                    if by_order and (indented or m or cur is None or ibid) and not cont:
                        # a note starts at an indented line (its raised number is seldom read right): keyed by order
                        seq += 1
                        body = re.sub(r"^[\d‘’'*!°¹²³⁴⁵Ͱ-Ͽἀ-῿]{1,2}\.?\s?(?=[A-Z“\"‘(])", "", t) if not m else m.group(2)
                        cur = [f"{n}-{seq}", body.strip()]
                        zone_notes.append(cur)
                    elif m and not by_order:
                        cur = [f"{n}-{m.group(1)}", m.group(2).strip()]
                        zone_notes.append(cur)
                    elif cur is None:
                        cur = [f"{n}-cont", t]
                        zone_notes.append(cur)
                    elif cur[1].endswith("-") and t[:1].islower():
                        cur[1] = cur[1][:-1] + t
                    elif (re.search(r"\d[-–—]$", cur[1]) and t[:1].isdigit()    # "pp. 408-" + "409."
                          and not re.match(r"\d{1,2}\.\s+[A-Z]", t)):
                        cur[1] += t
                    else:
                        cur[1] += " " + t
                break
    own = [z for z in zone_notes if not z[0].endswith("-cont")]
    if (marks is not None and own and zone_notes[0] is own[0] and len(own) > len(marks)
            and (own[0][1][:1].islower() or not marks)):
        # the zone opens mid-sentence ("elevate this signal…", "p. 416. Against…") and the page image shows one
        # mark fewer than the notes read: the first is the page before's last note, carried over
        own[0][0] = f"{n}-cont"
        for k, z in enumerate(own[1:], 1):
            z[0] = f"{n}-{k}"
    # Paragraphs from the lines' geometry, not Tesseract's own guess: a new one starts at a first-line indent, after a
    # short line that ends a sentence, at a centred line, or where the Bible text ends. Tesseract's blocks are the
    # columns (or parts of them), read in its order.
    # a column's edges from its typical full lines, so a stray mark in the margin doesn't move them
    by_block: dict = {}
    for l in keep:
        by_block.setdefault(l["k"][0], []).append(l)
    edges: dict = {}
    for b, ls in by_block.items():
        full = [l for l in ls if len(l["t"]) >= 25] or ls
        lefts, rights = sorted(l["left"] for l in full), sorted(l["right"] for l in full)
        edges[b] = [lefts[len(lefts) // 4], rights[(3 * len(rights)) // 4]]
    # the Bible text set larger above the notes: judged by a Tesseract block's median line height, since a single
    # line with accented Greek measures tall too
    bh: dict = {}
    for l in keep:
        bh.setdefault(l["k"][0], []).append(l["h"])
    bmed = {b: sorted(v)[len(v) // 2] for b, v in bh.items()}
    big = ((lambda l: bmed[l["k"][0]] > 1.12 * body_h and l["top"] < 0.5 * H) if scripture_larger
           else (lambda l: False))
    tops = sorted(l["top"] for l in keep)
    lead_ = sorted(b - a for a, b in zip(tops, tops[1:]) if b > a)
    lead_ = lead_[len(lead_) // 2] if lead_ else body_h * 1.5
    groups, prev, prev_c, prev_caps = [], None, False, False
    gapped: set = set()                               # groups that open after extra space: a heading may lead them
    for l in keep:
        bl, br = edges[l["k"][0]]
        wid = max(br - bl, 1)
        indent = l["left"] - bl
        centred = indent > 0.12 * wid and br - l["right"] > 0.12 * wid and len(l["t"]) < 70
        letters_ = [c for c in l["t"] if c.isalpha()]
        caps = (len(letters_) >= 6 and sum(c.isupper() for c in letters_) >= 0.85 * len(letters_)
                and len(l["t"].split()) >= 2)          # a heading set in capitals: a block of its own
        centred = centred or caps
        if outline:
            # an outline (Carson's Analysis): one entry per line, each closing with its reference; a line that
            # opens with "(", or follows a line without one and is not numbered, carries on the entry above it
            centred = caps = False
            t_ = l["t"].strip()
            new = prev is None or not (t_.startswith("(") or (not re.search(r"\)\W{0,2}$", prev["t"].strip())
                                                                and not re.match(ENUM, t_)))
        elif prev is None:
            new = True
        else:
            pbl, pbr = edges[prev["k"][0]]
            short = prev["right"] < pbr - 0.06 * (pbr - pbl)
            ends = re.search(r"[.!?:;”\"’')\]]$", prev["t"].strip())
            new = (indent > 0.025 * wid or (short and ends) or centred or prev_c
                   or big(l) != big(prev))
            if caps and prev_caps:                  # a heading set in capitals over two or three lines
                new = False
            elif (num_heads and prev_caps and len(l["t"]) < 40
                  and re.fullmatch(r"[A-Z’' ,:;-]*" + REF_END[:-1] + "$", l["t"].strip())):
                new, caps, centred = False, True, False    # its last line: "WORDS (5:1 — 7:52)", "(2:1 — 4:54)"
            if (num_heads and l["top"] - prev["top"] > 1.6 * lead_ and l["top"] > prev["top"]
                    and re.match(ENUM, l["t"].strip())):
                new = True
                gapped.add(len(groups))
        if new:
            groups.append([])
        groups[-1].append(l)
        prev, prev_c, prev_caps = l, centred, caps
    if num_heads:
        # a numbered section heading ("7. John the Baptist's continuing witness concerning Jesus (3:22-30)"), set
        # after extra space with its text flush left below it: the heading ends at its first line that closes a
        # chapter-and-verse reference, or (a heading with none: "1. The early church") at a short line without
        # closing punctuation that the next line does not carry on; one to three lines, or it was no heading
        split = []
        for gi, ls in enumerate(groups):
            if gi in gapped:
                bl, br = edges[ls[0]["k"][0]]
                end = None
                for j, l in enumerate(ls[:3]):
                    t_ = l["t"].strip()
                    nxt = ls[j + 1]["t"].strip() if j + 1 < len(ls) else ""
                    short = l["right"] < br - 0.06 * (br - bl)
                    if re.search(REF_END, t_) or (short and not re.search(r"[.,;:)’”]$", t_)
                                                  and not re.match(r"^[(a-z]", nxt)):
                        end = j
                        break
                if end is not None:
                    split.append(("head", ls[:end + 1]))
                    if ls[end + 1:]:
                        split.append(("p", ls[end + 1:]))
                    continue
            split.append(("", ls))
        groups = split
    else:
        groups = [("", ls) for ls in groups]
    if outline:
        groups = [("p", ls) for _, ls in groups]
    # a speck at the foot read as a note ("aL,") is not one
    # a speck at the foot read as a note ("aL,") is not one; a short citation is ("Ibid.", "ST 19, 1965, pp. 213-220.")
    blocks, notes = [], [z for z in zone_notes if numbered or sum(c.isalpha() for c in z[1]) >= 6
                         or re.search(r"\b(1[5-9]|20)\d\d\b|\bpp?\. ?\d|^\W{0,2}(Ibid|Idem)\b", z[1])]
    for kind, ls in groups:
        if all(big(l) for l in ls) and not (len(ls) == 1 and ls[0]["t"].isupper()):
            continue                                                   # the Bible text, set larger above the notes
        t = ""
        for l in ls:
            x = l["t"].strip()
            if t.endswith("-") and x[:1].islower():
                t = t[:-1] + x if not keep_hyphen(t, x) else t + x
            elif (re.search(r"\d[-–—]$", t) and x[:1].isdigit()              # a range broken at the line end,
                  and not re.match(r"\d{1,2}\.\s+[A-Z]", x)):                # not a list's "2. The …"
                t += x
            else:
                t = (t + " " + x).strip()
        small = sorted(l["h"] for l in ls)[len(ls) // 2] < 0.82 * body_h
        bottom = ls[0]["top"] > 0.6 * H
        m = re.match(r"^([*†‡§]|\d{1,2})\s+(\S.*)", t)
        if small and bottom and m:
            notes.append([f"{n}-{m.group(1)}", m.group(2)])
            continue
        if kind:                                    # a numbered heading, or an outline entry ("b. Jesus the Son
            t = re.sub(r"(?<=\))\s+\S{1,2}$", "", t)          # of God (10:31-39)" reads as Bible text)
            blocks.append(["h3" if kind == "head" else "p", t])
            continue
        if is_kjv(t):
            continue
        if numbered:
            ind = sum(l["left"] > main_left + 0.05 * W for l in ls)
            glued = len(re.findall(r"(?:^|\s)\d{1,2}(?=[A-Za-z“‘\"])", t))
            if (ind >= 0.6 * len(ls) and glued >= 1 and (glued >= 2 or re.match(r"^\d{1,2}[A-Za-z“‘\"]", t)))                     or re.match(r"^[a-z]\.\s+\d{1,2}(:\d{1,2})?\s+\S", t):
                continue                  # Scripture printed with the commentary, and its translation notes
        lt_ = [c for c in t if c.isalpha()]
        if (len(ls) <= 3 and len(t) < 160 and len(lt_) >= 6 and sum(c.isupper() for c in lt_) >= 0.85 * len(lt_)) or                 (len(ls) == 1 and len(t) < 70 and (t.isupper() or re.match(r"^(CHAPTER|CHAP\.|JOHN|[IVXL]+\.)", t))):
            blocks.append(["h3", t])
        elif (num_heads and len(t) < 130 and re.match(ENUM, t) and re.search(REF_END, t)
              and not re.search(r"[.!?]\s", re.sub(r"^\S+\s+", "", t, count=1).split("(")[0])):
            # a numbered heading with no space above it to tell it by (at the top of a page): "5. Jesus and
            # Nicodemus (3:1-15)", one line or two, closed by its reference
            blocks.append(["h3", re.sub(r"(?<=\))\s+\S{1,2}$", "", t)])
        else:
            blocks.append(["p", t])
    if marks is not None:
        link_marks(n, blocks, notes, marks, numbered)
        return blocks, notes
    if raised_marks:
        nums = sorted((k for k, _ in notes if k.split("-", 1)[1].isdigit()), key=lambda k: int(k.split("-", 1)[1]))
        found = sum(b[1].count(MARK) for b in blocks)
        if found == len(nums):                 # one mark per note: link them in order
            it = iter(nums)
            for b in blocks:
                b[1] = re.sub(MARK, lambda m: f"[^{next(it)}]", b[1])
        elif nums or found:
            MARK_MISMATCH.append((n, found, len(nums)))
        for b in blocks:
            b[1] = b[1].replace(MARK, "")
        return blocks, notes
    keys = {k.split("-", 1)[1] for k, _ in notes} - {"cont"}
    if keys:                                                           # "Weiss1" -> "Weiss[^n-1]"
        for b in blocks:
            b[1] = re.sub(r"(?<=[A-Za-z.,;:”’\"])(\d{1,2}|[*†‡§])(?=[\s,.;:)]|$)",
                          lambda m: f"[^{n}-{m.group(1)}]" if m.group(1) in keys else m.group(0), b[1])
    return blocks, notes


_known: Counter | None = None
_english: set = set()
KEEP_WORDS = {"facta", "ipsa", "rore", "foris", "undis", "aboth", "philon", "orat", "glossa", "testa", "latina",
              "propheta", "interpreta", "argumenta", "weil", "ipse", "illas"}
CORRECTED: list = []                                 # (page, from, to): every autocorrection, for the proof list
SWAPS = [("II", "H"), ("IT", "H"), ("c", "e"), ("e", "c"), ("I", "l"), ("l", "I"), ("Il", "H"), ("IH", "H"), ("li", "h"), ("rn", "m"),
         ("m", "rn"), ("ii", "ü"), ("i", "l"), ("l", "i"), ("vv", "w"), ("tl", "d"), ("f", "t"), ("t", "f"),
         ("Z", "Th"), ("u", "n"), ("n", "u"), ("h", "b"), ("b", "h"), ("y", "v"),
         ("S", "f"), ("F", "J"), ("z", "æ"), ("ze", "æ")]


def autocorrect(w: str, page: int = 0, after: str = "") -> str:
    """An OCR word that never occurs in the clean pages, but would after one common misreading is undone (c for e,
    Il for H, a lost space...), becomes that word. `after` is the character that follows it. Each change is logged
    in CORRECTED for the proof list."""
    global _known, _english
    if _known is None:
        _known = known_words()
        voc = CACHE / "vocab.txt"                      # Standard Ebooks vocabulary (ingest_school_copy._common)
        _english = set(voc.read_text(encoding="utf-8").split()) if voc.exists() else set()
    lw = w.lower()
    roman = re.compile(r"(?i)(c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})")
    if (after in ".," and re.fullmatch(r"[ivxlIVXL]+", w) and "l" in w and not roman.fullmatch(w)
            and lw not in ("ill", "il")):
        c = w.replace("l", "i")                        # a reference's Roman numeral with i read as l: vili., xvil,
        c = c.upper() if w[0].isupper() else c
        if roman.fullmatch(c):
            CORRECTED.append((page, w, c))
            return c
    if (len(w) < 3 or _known[lw] or lw in _english or not w.isalpha() or (after == "." and len(w) <= 5)
            or lw in KEEP_WORDS):
        return w
    cands = Counter()
    for a, b in SWAPS:
        i = w.find(a)
        while i >= 0:
            c = w[:i] + b + w[i + len(a):]
            inner_cap = any(ch.isupper() for ch in c[1:]) and not any(ch.isupper() for ch in w[1:])
            if _known[c.lower()] >= (50 if len(w) <= 3 else 3) and not inner_cap:
                cands[c] = _known[c.lower()]
            i = w.find(a, i + 1)
    small = {"is", "it", "in", "the", "to", "at", "of", "as", "and", "for", "that", "on", "by", "be", "we", "he",
             "his", "not", "this", "with", "was", "are", "or", "from", "him", "but", "so", "all", "which", "an"}
    for i in range(2, len(w) - 1):                      # two words run together: "isit", "nameof", "Christin"
        x, y = w[:i], w[i:]
        if ((x.lower() in small and _known[y.lower()] >= 50 and (len(y) >= 3 or y.lower() in small)) or
                (y.lower() in small and _known[x.lower()] >= 50 and len(x) >= 3)):
            cands[x + " " + y] = min(_known[x.lower()], _known[y.lower()]) // 10
    if not cands:
        return w
    best = cands.most_common(1)[0][0]
    CORRECTED.append((page, w, best))
    return best


COMMON_OCR = [  # misreads Tesseract makes in every one of these 19th-century faces (OCR pages only)
    (r"\bIam\b", "I am"), (r"\bLam\b(?= [a-z])", "I am"), (r"\bIle\b", "He"), (r"\bTle\b", "He"), (r"\bIIe\b", "He"),
    (r"\bIlis\b", "His"), (r"\bIlim\b", "Him"), (r"\blim\b", "him"), (r"\blis\b", "his"), (r"\bJf\b", "If"),
    (r"\bTf\b", "If"), (r"\bJoun\b", "John"), (r"\bJOuN\b", "JOHN"), (r"\bJobn\b", "John"), (r"\bJolin\b", "John"),
    (r"\b(Nores|Norrs|Notres|Nortes)\b", "Notes"), (r"\bNOTES?\b", "NOTES"), (r"\biu\b", "in"), (r"\bard\b", "and"),
    (r"\bfroin\b", "from"), (r"\bnuinber\b", "number"), (r"\bJast\b", "last"), (r"\bIdo\b", "I do"), (r"\bIgo\b", "I go"),
    (r"\bIhave\b", "I have"), (r"\bButI\b", "But I"), (r"\bItisa\b", "It is a"), (r"\bIfthe\b", "If the"),
    (r"\b(t|T)oa\b", r"\1o a"), (r"\b(i|I)na\b", r"\1n a"), (r"\b(o|O)fa\b", r"\1f a"), (r"\b(f|F)ora\b", r"\1or a"),
    (r"\b(o|O)na\b", r"\1n a"), (r"\bbea\b", "be a"), (r"\btodo\b", "to do"), (r"\bgoto\b", "go to"), (r"\btous\b", "to us"),
    (r"\bete\.", "etc."), (r"\bCesar\b", "Cæsar"), (r"\bwellknown\b", "well-known"), (r"\bali\b", "all"),
]


def is_junk(text: str) -> bool:
    toks = text.split()
    if _known is None:
        autocorrect("x")
    def word(w):
        if re.fullmatch(r"[\W\d]*[Ͱ-Ͽἀ-῿]*[ά-ώἀ-῿][Ͱ-Ͽἀ-῿]+[\W\d]*", w):
            return True                              # a Greek word in lower case, not a run of capitals
        x = re.sub(r"[^A-Za-zÀ-ÿ]", "", w).lower()
        two = {"a", "i", "o", "of", "to", "in", "is", "it", "be", "by", "he", "we", "as", "at", "an", "or", "on", "no",
               "so", "do", "my", "me", "us", "up", "if", "ye", "vv", "cf", "ii", "iv", "vi", "ix", "xi"}
        return x in two or (len(x) >= 3 and (x in _english or _known[x] >= 20))
    good = sum(1 for w in toks if word(w))
    if len(toks) < 3:                                # a short line: junk only if nothing in it is a word or a number
        return good == 0 and not any(re.search(r"\d", w) for w in toks)
    return good < 0.3 * len(toks)


BLANK_PAGES: list = []


def keep_hyphen(left: str, right: str) -> bool:
    """A word broken at a line end: keep the hyphen when it belongs to the word ("self-conscious", "source-
    criticism"), i.e. the joined form is not a word but both halves are."""
    if _known is None:
        autocorrect("x")
    a = re.sub(r"[^A-Za-z]", "", left.split()[-1]).lower() if left.split() else ""
    b = re.sub(r"[^A-Za-z].*$", "", right).lower()
    if not a or not b:
        return False
    if _hyph[f"{a}-{b}"] >= 2 and _hyph[f"{a}-{b}"] > _plain[a + b]:   # the book prints it so mid-line, mostly
        return True
    word = lambda w: w in _english or _known[w] >= 3
    # otherwise only after a compound's usual first half: a misread ("eli-mate") or an old form ("for-giveth")
    # joins
    return a in COMPOUND_HEADS and not word(a + b) and word(b) and len(b) >= 3


COMPOUND_HEADS = {"self", "well", "half", "non", "ill", "ever", "so", "high", "fellow", "co", "quasi", "semi",
                  "anti", "pre", "post", "neo", "pseudo", "proto", "sub", "inter", "extra", "ultra", "god", "man",
                  "first", "second", "third", "long", "short", "old", "new", "all", "one", "two", "three", "early",
                  "late", "mid", "world", "life", "law", "source", "form", "redaction", "tradition", "text",
                  "word", "son", "father", "mother", "brother", "sister", "after", "fore"}
_hyph: Counter = Counter()
_plain: Counter = Counter()
_hyph_dir = None


def load_hyph(s: dict) -> None:
    """The work's compounds printed hyphenated mid-line (OCR words, transcribed pages), against the same words
    printed joined: which line-end hyphens to keep. A transcriber now and then keeps a line-break hyphen
    ("concern-ing"), so a form counts only when the book prints it so more often than joined."""
    global _hyph, _plain, _hyph_dir
    if _hyph_dir == s["dir"]:
        return
    _hyph_dir, _hyph, _plain = s["dir"], Counter(), Counter()
    rx = re.compile(r"(?<![A-Za-z-])([A-Za-z]{2,})-([A-Za-z]{2,})(?![A-Za-z-])")
    for f in (s["dir"] / "vision").glob("p*.md"):
        text = f.read_text(encoding="utf-8")
        _hyph.update(f"{a}-{b}".lower() for a, b in rx.findall(text))
        _plain.update(re.findall(r"[a-z]+", text.lower()))
    for f in (s["dir"] / "ocr").glob("p*.tsv"):
        rows = csv.DictReader(io.StringIO(f.read_text(encoding="utf-8", errors="replace")), delimiter="\t",
                              quoting=csv.QUOTE_NONE)
        line, last = [], None
        for r in rows:
            if r.get("level") != "5":
                continue
            k = (r["block_num"], r["par_num"], r["line_num"])
            if k != last:
                line, last = [], k
            line.append(r["text"] or "")
            _plain.update(re.findall(r"[a-z]+", line[-1].lower()) if "-" not in line[-1] else [])
            if len(line) >= 2:                      # a word with words after it on its line is not broken
                m = rx.fullmatch(line[-2].strip(".,;:’”'\"()"))
                if m:
                    _hyph[f"{m.group(1)}-{m.group(2)}".lower()] += 1


def is_junk_page(text: str) -> bool:
    """Most of the page's words are not words: show-through on a blank page, or a picture read as letters."""
    if _known is None:
        autocorrect("x")
    toks = text.split()
    good = sum(1 for w in toks if re.search(r"[ά-ώἀ-῿]{2,}", w)
               or (lambda x: len(x) >= 2 and (x in _english or _known[x] >= 3))(re.sub(r"[^A-Za-z]", "", w).lower()))
    return good < 0.4 * len(toks)


def rejoin(m, page: int) -> str:
    """A word split at a line end whose hyphen OCR lost ("manifes tation"): joined when only the joined form is a
    word of these books."""
    x, y = m.group(1), m.group(2)
    if _known is None:
        autocorrect("x")
    xy = (x + y).lower()
    if _known[xy] >= 3 and (not _known[x.lower()] or not _known[y.lower()]) and x.lower() not in _english | {"a"}:
        CORRECTED.append((page, f"{x} {y}", x + y))
        return x + y
    return m.group(0)


def tidy(s: dict, blocks: list, n: int = 0, ocr: bool = False) -> list:
    """Per-work clean-ups on a page's blocks: printer's signature lines, the work's systematic OCR misreads
    (`ocr_patterns`, OCR pages only), and (Westcott) a verse lemma the transcriber set as a heading, which is really
    the opening of the note it introduces."""
    drop = [re.compile(x) for x in s.get("drop_lines", [])]
    if ocr:
        pats = [(re.compile(a), b) for a, b in COMMON_OCR + [tuple(x) for x in s.get("ocr_patterns", [])]]
        for blk in blocks:
            for rx, to in pats:
                blk[1] = rx.sub(to, blk[1])
            if s.get("autocorrect", True):
                blk[1] = re.sub(r"\b([A-Za-z]+)\s+([a-z]+)\b", lambda m: rejoin(m, n), blk[1])
            if s.get("autocorrect", True):       # off for a school copy: its full proof reads every suspect
                blk[1] = re.sub(r"[A-Za-zÀ-ÿ]+(?=(.?))", lambda m: autocorrect(m.group(0), n, m.group(1)), blk[1])
        # on pages the work names (a rotated table read as letters): drop blocks that are mostly not words
        if n in s.get("junk_pages", []):
            blocks = [b for b in blocks if not is_junk(b[1])]
    # a running head the transcriber kept: one of the work's heads, alone, with text (not a heading) after it
    if (blocks and blocks[0][0] in ("h2", "h3") and s.get("running_heads")
            and is_head(blocks[0][1], s["running_heads"]) and (len(blocks) == 1 or blocks[1][0] not in ("h2", "h3"))):
        blocks = blocks[1:]
    out = []
    starts = s.get("page_starts", {})               # {page: regex}: the page's text begins at the first match
    if str(n) in starts:
        rx = re.compile(starts[str(n)])
        at = next((i for i, (_, t) in enumerate(blocks) if rx.search(t)), 0)
        blocks = blocks[at:]
    ends = s.get("page_ends", {})                   # {page: regex}: the page's text ends with the first match
    if str(n) in ends:
        rx = re.compile(ends[str(n)])
        at = next((i for i, (_, t) in enumerate(blocks) if rx.search(t)), len(blocks) - 1)
        blocks = blocks[:at + 1]
    for i, (k, t) in enumerate(blocks):
        if any(d.fullmatch(t.strip()) for d in drop):
            continue
        if (s.get("lemma_heads") and k == "h3" and re.match(r"\d+\.\s+\S", t)
                and not re.search(r"[A-Z]{4}", t) and not re.match(r"\d+\.\s+\*", t)):
            lemma = re.sub(r"^(\d+\.)\s+(.*?)\]?$", lambda m: f"{m.group(1)} *{m.group(2).strip('* ')}*]", t)
            out.append(["lemma", lemma])
            continue
        if out and out[-1][0] == "lemma" and k == "p":
            out[-1] = ["p", out[-1][1] + " " + t]
            continue
        out.append([k, t])
    out = [["p", t] if k == "lemma" else [k, t] for k, t in out]
    if s.get("split_heads"):                         # a run-in heading ("Notes. JOHN XII. 20—26. 20.—[...") on its own
        rx, split = re.compile(s["split_heads"]), []
        for k, t in out:
            m = rx.match(t) if k == "p" else None
            if m:
                split += [["h3", f"NOTES. {m.group(2).strip()}"]] + ([["p", t[m.end():]]] if t[m.end():].strip() else [])
            else:
                split.append([k, t])
        out = split
    return out


def page_blocks(s: dict, n: int) -> tuple[list, list, str]:
    """A page's blocks: a hand-typed page (manual/) wins, then the transcription, then OCR."""
    load_hyph(s)
    m = s["dir"] / "manual" / f"p{n:04d}.md"
    if m.exists():
        b, notes = vision_page(n, m.read_text(encoding="utf-8"))
        return tidy(s, b, n), notes, "manual"
    v = s["dir"] / "vision" / f"p{n:04d}.md"
    if v.exists():
        b, notes = vision_page(n, v.read_text(encoding="utf-8"), s.get("heads", []))
        return tidy(s, b, n), notes, "vision"
    o = s["dir"] / "ocr" / f"p{n:04d}.tsv"
    if o.exists():
        mk = s["dir"] / "marks" / f"p{n:04d}.json"
        marks = json.loads(mk.read_text(encoding="utf-8")).get("marks", []) if mk.exists() else None
        if marks is not None and s.get("numbered_notes"):        # "Dedicationᵃ": the NIV's own notes, dropped
            marks = [m for m in marks if str(m.get("mark", "")).strip().isdigit()]
        b, notes = ocr_page(n, o.read_text(encoding="utf-8", errors="replace"), s.get("heads", []),
                            s.get("scripture_larger", False), s.get("note_zone", False),
                            s.get("raised_marks", False) and marks is None, marks, s.get("top_heads"),
                            s.get("table_split", 0) if n in set(s.get("table_pages", [])) else 0,
                            s.get("num_heads", False), n in set(s.get("outline_pages", [])),
                            s.get("numbered_notes", False))
        text = " ".join([x[1] for x in b] + [x[1] for x in notes])     # the notes too: a zone can take it all
        if len(text.split()) >= 20 and is_junk_page(text):
            BLANK_PAGES.append(n)                    # a blank page reading the other side's text through the paper
            return [], [], "blank"
        pats = [(re.compile(a), r) for a, r in COMMON_OCR + [tuple(x) for x in s.get("ocr_patterns", [])]]
        for note in notes:                           # the work's OCR rules hold in its footnotes too
            for rx, to in pats:
                note[1] = rx.sub(to, note[1])
        return tidy(s, b, n, ocr=True), notes, "ocr"
    return [], [], "missing"


# ---------------------------------------------------------------- build

def stream(s: dict):
    """Every kept block in reading order, with its page; paragraphs a page break split are joined."""
    skip, out, notes, kinds = dropped(s), [], {}, {}
    last_note = None
    starts_at = {c["page"] for c in s.get("chapters", [])}   # a chapter's first page never joins the one before
    # pages from another copy of the edition, appended to the PDF, read where they belong ({after: [pages]})
    extra = {int(k): v for k, v in s.get("insert_after", {}).items()}
    moved = {p for v in extra.values() for p in v}
    order = []
    for n in range(1, n_pages(s) + 1):
        if n not in moved:
            order += [n] + extra.get(n, [])
    for n in order:
        if n in skip:
            continue
        blocks, pnotes, kind = page_blocks(s, n)
        kinds[n] = kind
        for key, t in pnotes:
            if key.endswith("-cont") and last_note:
                notes[last_note] += " " + t
                continue
            notes[key] = t
            last_note = key
        for i, (k, t) in enumerate(blocks):
            if (i == 0 and k == "p" and out and out[-1][1] == "p" and n not in starts_at and
                    (not re.search(r"[.!?:;”’\"')\]*]$", out[-1][2]) or t[:1].islower())):
                prev = out[-1][2]
                out[-1][2] = (prev[:-1] + t) if prev.endswith("-") and t[:1].islower() else prev + " " + t
                continue
            out.append([n, k, t])
    return out, notes, kinds


def chapters_of(s: dict, items: list) -> list[dict]:
    """Split the stream by the chapter map: each entry {title, page, match} starts at the first block on or after
    `page` whose text matches `match` (a regex); that heading block is consumed by the chapter's own title."""
    cmap = s["chapters"]
    starts, i = [], 0
    for c in cmap:
        rx = re.compile(c["match"])
        while i < len(items) and not (items[i][0] >= c["page"] and rx.search(items[i][2])):
            i += 1
        if i >= len(items):
            raise SystemExit(f"chapter {c['title']!r}: no block on or after p{c['page']} matches {c['match']!r}")
        starts.append(i)
    out = []
    for j, c in enumerate(cmap):
        # the heading block the chapter starts at becomes its title, unless the map keeps it: a chapter named for
        # its passage ("John 6") keeps the book's own section heading under it
        a = starts[j] + (1 if items[starts[j]][1] in ("h2", "h3") and not c.get("keep_head") else 0)
        b = starts[j + 1] if j + 1 < len(cmap) else len(items)
        if c.get("end_page"):
            b = min(b, next((k for k in range(a, len(items)) if items[k][0] > c["end_page"]), len(items)))
        out.append({"title": c["title"], "items": items[a:b], "page": items[starts[j]][0],
                    "move_before": c.get("move_before")})
    for c in [c for c in out if c["move_before"]]:     # a part the edition printed out of place (Godet's preface)
        out.remove(c)
        out.insert(next(i for i, x in enumerate(out) if x["title"] == c["move_before"]), c)
    return out


def split_notes(s: dict, items: list, notes: dict) -> None:
    """Two footnotes OCR read as one, the second one's mark lost: `split_notes.json` lists [where the second note
    starts (text found in exactly one note), body text (exactly once), the same with "{mark}" where its mark goes].
    Done before the notes are numbered, so the chapter's numbers follow; `fixes.json` then corrects the words."""
    f = s["dir"] / "split_notes.json"
    if not f.exists():
        return
    for at, find, repl in json.loads(f.read_text(encoding="utf-8")):
        keys = [k for k, v in notes.items() if at in v]
        hits = [i for i, x in enumerate(items) if find in x[2]]
        if len(keys) != 1 or len(hits) != 1 or items[hits[0]][2].count(find) != 1:
            print(f"split_notes: {at!r} in {len(keys)} notes, {find!r} in {len(hits)} blocks; skipped")
            continue
        k = keys[0]
        head, tail = notes[k].split(at, 1)
        new = f"{k}-split"
        rebuilt = {}
        for kk, vv in notes.items():          # the new note sits right after the one it came out of
            rebuilt[kk] = head.rstrip() if kk == k else vv
            if kk == k:
                rebuilt[new] = (at + tail).strip()
        notes.clear()
        notes.update(rebuilt)
        items[hits[0]][2] = items[hits[0]][2].replace(find, repl.replace("{mark}", f"[^{new}]"))


def move_notes(s: dict, items: list, notes: dict) -> None:
    """A footnote OCR ran into the body text (one line under a wide gap, set as large as the text): `move_notes.json`
    lists [the body text to take out (exactly once), the note as printed, body text (exactly once), the same with
    "{mark}" where its mark goes]. The new note belongs to the page the text was on."""
    f = s["dir"] / "move_notes.json"
    if not f.exists():
        return
    for k, (cut, note, find, repl) in enumerate(json.loads(f.read_text(encoding="utf-8")), 1):
        hits = [i for i, x in enumerate(items) if cut in x[2]]
        if len(hits) != 1 or items[hits[0]][2].count(cut) != 1:
            print(f"move_notes: {cut[:40]!r} in {len(hits)} blocks; skipped")
            continue
        key = f"{items[hits[0]][0]}-moved{k}"
        items[hits[0]][2] = items[hits[0]][2].replace(cut, "")
        notes[key] = note
        marks = [i for i, x in enumerate(items) if find in x[2]]
        if len(marks) == 1 and items[marks[0]][2].count(find) == 1:
            items[marks[0]][2] = items[marks[0]][2].replace(find, repl.replace("{mark}", f"[^{key}]"))
        else:
            print(f"move_notes: mark place {find!r} in {len(marks)} blocks; the note is placed by page")


def cont_notes(s: dict, notes: dict) -> None:
    """A note carried over from the page before that OCR ran into the page's first note: `cont_notes.json` lists
    [the carried-over text's start, the start of the page's own note]. The first part joins the note before it."""
    f = s["dir"] / "cont_notes.json"
    if not f.exists():
        return
    for start, own in json.loads(f.read_text(encoding="utf-8")):
        keys = [k for k, v in notes.items() if v.startswith(start) and own in v]
        if len(keys) != 1:
            print(f"cont_notes: {start[:30]!r} starts {len(keys)} notes; skipped")
            continue
        order = list(notes)
        i = order.index(keys[0])
        if i == 0:
            continue
        head, tail = notes[keys[0]].split(own, 1)
        notes[order[i - 1]] = notes[order[i - 1]].rstrip() + " " + head.strip()
        notes[keys[0]] = (own + tail).strip()


def place_marks(s: dict, items: list, notes: dict) -> None:
    """A mark the page image shows but OCR misread past finding ("xchanges.!"): `place_marks.json` lists [text
    found in exactly one note, body text (exactly once), the same with "{mark}" where that note's mark goes]."""
    f = s["dir"] / "place_marks.json"
    if not f.exists():
        return
    for at, find, repl in json.loads(f.read_text(encoding="utf-8")):
        keys = [k for k, v in notes.items() if v.startswith(at)] or [k for k, v in notes.items() if at in v]
        hits = [i for i, x in enumerate(items) if find in x[2]]
        if len(keys) != 1 or len(hits) != 1 or items[hits[0]][2].count(find) != 1:
            print(f"place_marks: {at!r} in {len(keys)} notes, {find!r} in {len(hits)} blocks; skipped")
            continue
        items[hits[0]][2] = items[hits[0]][2].replace(find, repl.replace("{mark}", f"[^{keys[0]}]"))


def apply_fixes(s: dict, text: str) -> tuple[str, list]:
    f = s["dir"] / "fixes.json"
    bad = []
    if f.exists():
        for frm, to in json.loads(f.read_text(encoding="utf-8")):
            k = text.count(frm)
            if k != 1:
                bad.append((frm, k))
                continue
            text = text.replace(frm, to)
    return text, bad


def cmd_build(a):
    s = spec(a.work)
    CORRECTED.clear(); MARK_MISMATCH.clear(); BLANK_PAGES.clear()
    items, notes, kinds = stream(s)
    cont_notes(s, notes)
    split_notes(s, items, notes)
    move_notes(s, items, notes)
    place_marks(s, items, notes)
    chs = chapters_of(s, items)
    md = []
    marked = {k for _, _, t in items for k in re.findall(r"\[\^([^\]]+)\]", t)}
    placed: set = set()
    for c in chs:
        md += ["", f"## {c['title']}"]
        order = []
        for n, k, t in c["items"]:
            if re.fullmatch(r"(CHAPTER|CHAP\.)\s+([IVXL]+|FIRST|SECOND|THIRD|FOURTH|FIFTH)\.?", t.strip()):
                continue                        # a chapter heading the map didn't split on: the map titles chapters
            def mark(m):
                key = m.group(1)
                if key not in notes:
                    return ""
                if key not in order:
                    order.append(key)
                return f"[^{order.index(key) + 1}]"
            t = re.sub(r"\[\^([^\]]+)\]", mark, t)
            md.append(f"<!-- p{n}{' ocr' if kinds.get(n) == 'ocr' else ''} -->")
            md.append({"h2": "### ", "h3": "### ", "quote": "> "}.get(k, "") + t)
        pages = {n for n, _, _ in c["items"]}
        for key in notes:                       # a note whose mark OCR missed still belongs to its chapter (the
            if (key not in order and key not in marked and key not in placed   # first, on a page two share)
                    and key.split("-", 1)[0].isdigit() and int(key.split("-", 1)[0]) in pages):
                order.append(key)
        placed.update(order)
        for j, key in enumerate(order, 1):
            md.append(f"[^{j}]: {notes[key]}")
    text = "\n".join(md).strip() + "\n"
    text, bad = apply_fixes(s, text)
    (s["dir"] / "work.md").write_text(text, encoding="utf-8")
    ocr_pages = sorted(n for n, k in kinds.items() if k == "ocr")
    missing = sorted(n for n, k in kinds.items() if k == "missing")
    report = [f"# {s['title']}: proof", "", f"{len(chs)} chapters; {len(ocr_pages)} OCR pages; "
              f"{len(missing)} pages with no text: {missing[:40]}", ""]
    for c in chs:
        w = sum(len(t.split()) for _, _, t in c["items"])
        report.append(f"- {c['title']} (p{c['page']}): {w:,} words")
    if bad:
        report += ["", "## Fixes that no longer match exactly once", *[f"- {k}×: {f!r}" for f, k in bad]]
    report += ["", "## OCR pages", ", ".join(map(str, ocr_pages))]
    blanks = sorted(n for n, k in kinds.items() if k == "blank")
    report += ["", f"## Pages read as blank (check none held text): {blanks}"]
    report += ["", f"## Footnote marks that could not all be placed (page, marks, notes, placed): {MARK_MISMATCH}"]
    seen = Counter((a, b) for _, a, b in CORRECTED)
    report += ["", f"## Automatic OCR corrections ({sum(seen.values())}; check any that look wrong)", ""]
    report += [f"- {a} → {b}" + (f" (×{k})" if k > 1 else "") for (a, b), k in seen.most_common()]
    (s["dir"] / "proof.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:4 + len(chs)]))
    if bad:
        print(f"{len(bad)} fixes no longer match; see proof.md")


def cmd_heads(a):
    s = spec(a.work)
    items, _, kinds = stream(s)
    for n, k, t in items:
        if k in ("h2", "h3") or (a.all and k == "p" and len(t) < 60):
            print(f"p{n:<5}{k:<4}{'ocr ' if kinds.get(n) == 'ocr' else ''}{t[:110]}")


def cmd_page(a):
    import pypdfium2 as pdfium
    s = spec(a.work)
    pg = pdfium.PdfDocument(str(pdf_path(s)))[a.n - 1]
    w, h = pg.get_size()
    im = pg.render(scale=2200 / max(w, h)).to_pil()
    if a.part:
        W, H = im.size
        top, bot = {"top": (0, 0.55), "bottom": (0.45, 1.0), "middle": (0.25, 0.75)}[a.part]
        im = im.crop((0, int(H * top), W, int(H * bot)))
    p = SCANS / f"view_{a.work}_{a.n}{'_' + a.part if a.part else ''}.png"
    im.save(p)
    print(p)


# ---------------------------------------------------------------- load

def md_html(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(\S(?:.*?\S)?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*(\S(?:.*?\S)?)\*(?![*\w])", r"<i>\1</i>", t)
    t = re.sub(r"\\?\*+", "", t)                       # an italic the page left open, or a mark without its note
    t = re.sub(r"\s*\[\^(\d+)\]", r"[\1]", t)
    # typeset links a marker only when a letter precedes it in the same text: after "<i>…</i>" it goes inside
    return re.sub(r"((?:</(?:i|b)>)+)(\[\d+\])", r"\2\1", t)


def cmd_load(a):
    s = spec(a.work)
    text = (s["dir"] / "work.md").read_text(encoding="utf-8")
    chapters, cur = [], None
    for ln in text.split("\n"):
        if ln.startswith("<!--") or not ln.strip():
            continue
        if ln.startswith("## "):
            cur = {"title": ln[3:].strip(), "body": [], "notes": []}
            chapters.append(cur)
        elif cur is None:
            continue
        elif m := re.match(r"\[\^(\d+)\]:\s*(.*)", ln):
            cur["notes"].append(f"<p>[{m.group(1)}] {md_html(m.group(2))}</p>")
        elif ln.startswith("### "):
            cur["body"].append(f"<h3>{md_html(ln[4:])}</h3>")
        elif ln.startswith("> "):
            cur["body"].append(f"<blockquote><p>{md_html(ln[2:])}</p></blockquote>")
        else:
            cur["body"].append(f"<p>{md_html(ln)}</p>")
    rows = []
    for i, c in enumerate(chapters, 1):
        h = "\n".join([f"<h2>{html.escape(c['title'], quote=False)}</h2>", *c["body"], *c["notes"]])
        rows.append((i, c["title"], h, len(re.sub(r"<[^>]+>", " ", h).split())))
    wc = sum(r[3] for r in rows)
    shelf = json.dumps(s.get("shelf") or ["Christianity"])
    ded = (s.get("dedication") or "").strip()      # front matter, as ingest_school_copy sets it
    front = ('<div class="ex-dedication">' + "".join(f"<p>{html.escape(x, quote=False)}</p>"
                                                    for x in ded.split("\n") if x.strip()) + "</div>") if ded else None
    con = sqlite3.connect(a.db)
    try:
        cur = con.cursor()
        old = cur.execute("select id from books where slug=?", (s["slug"],)).fetchone()
        if old:
            cur.execute("delete from book_chapters where book_id=?", old)
            cur.execute("delete from books where id=?", old)
        cur.execute(
            """insert into books(slug,title,author,author_sort,source,license,us_clear,language,subjects,genres,section,
                                 genres_backup,title_backup,cover_url,chapter_count,word_count,access,front_html,added_at)
               values(?,?,?,?,?,?,?,'en','[]',?,?,?,?,null,?,?,?,?,datetime('now'))""",
            (s["slug"], s["title"], s["author"], s["author_sort"], s.get("source", "archive.org"),
             s.get("rights", "PD-US"), 0 if s.get("access") else 1, shelf, shelf, shelf, s["title"], len(rows), wc,
             s.get("access"), front))
        bid = cur.lastrowid
        cur.executemany("insert into book_chapters(book_id,section_number,title,html,words) values(?,?,?,?,?)",
                        [(bid, *r) for r in rows])
        con.commit()
    finally:
        con.close()
    print(f"{s['slug']}: loaded {len(rows)} chapters, {wc:,} words into {a.db}")


def known_words() -> collections.Counter:
    """Every word in the clean (vision) pages of all the works: what an OCR word should look like."""
    known = Counter()
    for w in json.loads(SPECS.read_text(encoding="utf-8")).values():
        for f in (CACHE / w["cache"] / "vision").glob("p*.md"):
            known.update(re.findall(r"[A-Za-zÀ-ÿ']+", f.read_text(encoding="utf-8").lower()))
    return known


def cmd_suspects(a):
    """Words on OCR pages that never occur in the clean pages, and Greek mixed with Latin letters, in context."""
    s = spec(a.work)
    known = known_words()
    voc = CACHE / "vocab.txt"
    ignore = set(s.get("known_words", [])) | (set(voc.read_text(encoding="utf-8").split()) if voc.exists() else set())
    page, rows = None, []
    layer = {}                                     # a word the PDF's own layer also reads on that page is confirmed
    if s.get("ocr_all"):
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(pdf_path(s)))
    for ln in (s["dir"] / "work.md").read_text(encoding="utf-8").split("\n"):
        m = re.match(r"<!-- p(\d+)( ocr)? -->", ln)
        if m:
            page = (int(m.group(1)), bool(m.group(2)))
            if s.get("ocr_all") and page[0] not in layer:
                layer[page[0]] = set(re.findall(r"[A-Za-zÀ-ÿ']+", pdf[page[0] - 1].get_textpage().get_text_range()))
            continue
        if not page or not page[1]:
            continue
        for mm in re.finditer(r"[A-Za-zÀ-ÿĀ-ſ']+|\S*[Ͱ-Ͽἀ-῿]\S*", ln):
            w = mm.group(0)
            greek = bool(re.search(r"[Ͱ-Ͽἀ-῿]", w))
            # a transliteration with its macrons restored (ō, ē, š) and an all-capital abbreviation (NIV, JBL)
            # are not suspects: both are set right by rules, and the layer misreads small capitals
            settled = bool(re.search(r"[Ā-ſ]", w)) or bool(re.fullmatch(r"[A-Z]{2,6}", w))
            bad = (greek and re.search(r"[A-Za-z]", w)) or (not greek and not settled and len(w) > 1 and
                                                             known[w.lower().strip("'")] == 0 and w.lower() not in ignore)
            if bad and not (page[0] in layer and w in layer[page[0]]):
                rows.append((page[0], w, ln[max(0, mm.start() - 50):mm.end() + 30]))
    for p, w, ctx in rows[: a.limit]:
        print(f"p{p:<5}{w:<18}{ctx}")
    print(f"{len(rows)} suspects")


collections = __import__("collections")


def cmd_second(a):
    """The full proof's second reading: each page of the built text against the PDF's own text layer (archive.org's
    ABBYY, an independent engine). Disagreements worth reading go to second.txt; set aside: spacing and punctuation,
    the layer's Greek junk, and spots where the layer is the garbled one."""
    import difflib
    import pypdfium2 as pdfium
    s = spec(a.work)
    autocorrect("x")                                   # loads the vocabularies
    eng = lambda w: (lambda x: len(x) <= 1 or x in _english or _known[x] >= 3)(re.sub(r"[^a-z]", "", w.lower()))
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
    pdf = pdfium.PdfDocument(str(pdf_path(s)))
    pages: dict = collections.OrderedDict()
    cur = None
    for ln in (s["dir"] / "work.md").read_text(encoding="utf-8").split("\n"):
        m = re.match(r"<!-- p(\d+)", ln)
        if m:
            cur = int(m.group(1))
            continue
        if cur and ln.strip() and not ln.startswith("## ") and not ln.startswith("[^"):
            pages.setdefault(cur, []).append(re.sub(r"\[\^\d+\]|^(### |> )|\*", "", ln))
    out, why = [], Counter()
    for n, body in pages.items():
        x = [t for t in " ".join(body).split() if norm(t)]
        y = [t for t in pdf[n - 1].get_textpage().get_text_range().replace("￾", "-").split() if norm(t)]
        sm = difflib.SequenceMatcher(None, [norm(t) for t in x], [norm(t) for t in y], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op in ("equal", "insert"):
                continue
            mine, theirs = x[i1:i2], y[j1:j2]
            if len(mine) > 6 or len(theirs) > 6:
                why["long runs (layout, notes)"] += 1
                continue
            m, t = " ".join(mine), " ".join(theirs)
            if norm(m) == norm(t):
                why["same letters"] += 1
            elif re.search(r"[Ͱ-Ͽἀ-῿֐-׿]", m):
                why["Greek or Hebrew (the layer can't read it)"] += 1
            elif re.fullmatch(r"[\d\s:,;.\-–—()\[\]]*", re.sub(r"[^\d\s:,;.\-–—()\[\]]", "", m + t)) and not re.search(r"[A-Za-z]", m + t):
                why["numbers and punctuation"] += 1
            elif all(eng(w) for w in mine) and theirs and not all(eng(w) for w in theirs):
                why["layer garbled"] += 1
            else:
                ctx = " ".join(x[max(0, i1 - 6):i1]) + " ⟦" + m + "⟧ " + " ".join(x[i2:i2 + 6])
                out.append(f"p{n} | built: {m!r} | layer: {t!r} | {ctx}")
    (s["dir"] / "second.txt").write_text("\n".join(out), encoding="utf-8")
    print(f"{a.work}: {len(out)} disagreements worth reading -> second.txt; set aside: {dict(why)}")


def cmd_sheet(a):
    """A contact sheet of OCR spots to read against the scan: for each "page|word" in --spots (a file, one per line),
    the scan lines around that word, labelled with an index. Several per image, so a proof goes a dozen at a time."""
    import pypdfium2 as pdfium
    from PIL import Image, ImageDraw
    s = spec(a.work)
    pdf = pdfium.PdfDocument(str(pdf_path(s)))
    spots = [ln.split("|", 1) for ln in Path(a.spots).read_text(encoding="utf-8").splitlines() if "|" in ln]
    tiles = []
    for idx, (pg, word) in enumerate(spots, 1):
        n = int(pg)
        tsv = (s["dir"] / "ocr" / f"p{n:04d}.tsv").read_text(encoding="utf-8", errors="replace")
        rows = [r for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
                if r.get("level") == "5" and (r.get("text") or "").strip()]
        W0 = max(int(r["width"]) for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
                 if r.get("level") == "1")
        hit = next((r for r in rows if word.strip() in r["text"]), None)
        if not hit:
            continue
        p = pdf[n - 1]
        w, h = p.get_size()
        im = p.render(scale=3000 / max(w, h)).to_pil().convert("L")
        k = im.size[0] / W0
        x, y, hh = int(hit["left"]) * k, int(hit["top"]) * k, int(hit["height"]) * k
        x0, x1 = max(0, x - 450), min(im.size[0], x + 650)
        tile = im.crop((int(x0), int(max(0, y - 2.2 * hh)), int(x1), int(min(im.size[1], y + 3.2 * hh))))
        tile = tile.resize((tile.size[0] // 2 * 2 // 2, tile.size[1] // 2), Image.LANCZOS) if tile.size[0] > 1100 else tile
        canvas = Image.new("L", (tile.size[0] + 70, tile.size[1] + 6), 255)
        canvas.paste(tile, (70, 3))
        ImageDraw.Draw(canvas).text((6, 6), str(idx), fill=0)
        tiles.append(canvas)
    if not tiles:
        print("no spots found")
        return
    for b in range(0, len(tiles), a.per):
        group = tiles[b:b + a.per]
        sheet = Image.new("L", (max(t.size[0] for t in group), sum(t.size[1] for t in group) + 4 * len(group)), 200)
        y = 0
        for t in group:
            sheet.paste(t, (0, y))
            y += t.size[1] + 4
        out = SCANS / f"sheet_{a.work}_{b // a.per + 1}.png"
        sheet.save(out)
        print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("ocr"); o.add_argument("work"); o.add_argument("--workers", type=int, default=4)
    h = sub.add_parser("heads"); h.add_argument("work"); h.add_argument("--all", action="store_true",
                                                                        help="short paragraphs too")
    b = sub.add_parser("build"); b.add_argument("work")
    p = sub.add_parser("page"); p.add_argument("work"); p.add_argument("n", type=int)
    p.add_argument("--part", choices=["top", "middle", "bottom"])
    l = sub.add_parser("load"); l.add_argument("work"); l.add_argument("--db", default=str(ROOT / "db" / "books.db"))
    su = sub.add_parser("suspects"); su.add_argument("work"); su.add_argument("--limit", type=int, default=400)
    se = sub.add_parser("second"); se.add_argument("work")
    sh = sub.add_parser("sheet"); sh.add_argument("work"); sh.add_argument("--spots", required=True,
                                                                         help='a file of "page|word" lines')
    sh.add_argument("--per", type=int, default=10)
    a = ap.parse_args()
    {"ocr": cmd_ocr, "heads": cmd_heads, "build": cmd_build, "page": cmd_page, "load": cmd_load,
     "suspects": cmd_suspects, "sheet": cmd_sheet, "second": cmd_second}[a.cmd](a)


if __name__ == "__main__":
    main()
