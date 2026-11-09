"""Proof a school copy built by scripts/ingest_school_copy.py. Everything is local: no model, no network.
Outputs go to .seed_cache/school/<slug>/ (gitignored, like the copies themselves).

    python scripts/proof_school_copy.py measure <slug>
        The structure in numbers, and the gates that say whether the book needs a closer look (see the skill
        .claude/skills/school-copies/SKILL.md).
    python scripts/proof_school_copy.py suspects <slug>
        Every word outside a wide English vocabulary, in its context -> suspects.txt. The vocabulary is built once
        from the Reading Room's own public books (a few minutes the first time).
    python scripts/proof_school_copy.py second <slug> [--first N] [--last N]
        A second, independent reading of every text page (Tesseract against the scan's own text layer, or Tesseract
        at another width against the first OCR). Disagreements -> second.txt. Slow: about 5 seconds a page.
    python scripts/proof_school_copy.py triage <slug>
        second.txt cut down to the disagreements worth reading -> triage.txt.
    python scripts/proof_school_copy.py marks <slug>
        Stray marks left by pen strokes and OCR -> marks.txt.
    python scripts/proof_school_copy.py crop <slug> <page> "<text on the line>" [--up N] [--down N]
        The scan around that line, as an image to read -> crops/.
    python scripts/proof_school_copy.py fix <slug> "<from>" "<to>"
    python scripts/proof_school_copy.py fix <slug> --near "<start>" "<end>" "<to>"
        Record a hand correction in book.json, checked against the built text. --near takes the text from <start> to
        the first <end> after it (for spots holding characters that are hard to type); <start> must occur once and
        the span must be short, so a fix can never swallow a chapter. Rebuild after fixing.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".seed_cache" / "school"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _dir(slug):
    d = CACHE / slug
    if not (d / "work.md").exists():
        sys.exit(f"{slug}: no work.md; run ingest_school_copy.py extract/propose/build first")
    return d


def _work(slug):
    return (_dir(slug) / "work.md").read_text(encoding="utf-8")


def _pages(slug):
    with open(_dir(slug) / "pages.jsonl", encoding="utf-8") as f:
        return [json.loads(x) for x in f]


def _pdf(slug):
    return json.loads((_dir(slug) / "extract.json").read_text(encoding="utf-8"))["pdf"]


def _vocab() -> set:
    """A wide English vocabulary: words used at least twice in the Reading Room's public books."""
    p = CACHE / "vocab-wide.txt"
    if not p.exists():
        print("building the vocabulary from books.db (once; a few minutes)…", flush=True)
        con = sqlite3.connect(ROOT / "db" / "books.db")
        cols = {c[1] for c in con.execute("pragma table_info(books)")}
        not_school = "and coalesce(b.access,'')<>'school'" if "access" in cols else ""
        cnt = collections.Counter()
        for (h,) in con.execute("select c.html from book_chapters c join books b on b.id=c.book_id "
                                f"where b.source in ('standardebooks','ccel') {not_school}"):
            cnt.update(w.lower() for w in re.findall(r"[A-Za-z]+", re.sub(r"<[^>]+>", " ", h or "")))
        CACHE.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(w for w, k in cnt.items() if k >= 2), encoding="utf-8")
    return set(p.read_text(encoding="utf-8").split())


def _lines_with_pages(text):
    page = "?"
    for ln in text.split("\n"):
        m = re.match(r"<!-- p(\d+) -->", ln)
        if m:
            page = m.group(1)
            continue
        if ln.startswith("<!--"):
            continue
        yield page, ln


# ---------------------------------------------------------------- measure

def cmd_measure(a):
    text = _work(a.slug)
    book = json.loads((_dir(a.slug) / "book.json").read_text(encoding="utf-8"))
    chapters, cur = [], None
    for ln in text.split("\n"):
        if ln.startswith("## "):
            cur = {"t": ln[3:], "p": [], "h3": 0, "q": [], "first": None}
            chapters.append(cur)
        elif cur is None or not ln.strip() or ln.startswith("<!--"):
            continue
        elif ln.startswith("### "):
            cur["h3"] += 1
        elif ln.startswith("> "):
            cur["q"].append(ln[2:])
        elif not ln.startswith("[sig]"):
            cur["p"].append(ln)
            cur["first"] = cur["first"] or ln
    body = [p for c in chapters for p in c["p"]]
    words = sum(len(p.split()) for p in body)
    lower = sum(1 for p in body if re.match(r"^[a-z]", p))
    short_q = sum(1 for c in chapters for q in c["q"] if len(q.split()) <= 12)
    vocab = _vocab()
    toks = re.findall(r"\b[a-z]{3,}\b", "\n".join(body))
    freq = collections.Counter(toks)
    unusual = sum(1 for w in toks if w not in vocab and freq[w] <= 1)
    pages = _pages(a.slug)
    ocr = sum(1 for p in pages if p["src"] == "ocr")
    print(f"{a.slug}: {len(chapters)} chapters, {len(body)} paragraphs, {words:,} words; "
          f"{ocr} of {len(pages)} pages read by OCR; {len(book.get('fixes') or [])} hand corrections")
    for c in chapters:
        pw = [len(p.split()) for p in c["p"]]
        print(f"   {c['t'][:44]:44} paras {len(pw):3}  median {statistics.median(pw) if pw else 0:4.0f}  "
              f"subheads {c['h3']:2}  quotations {len(c['q']):2}  opens: {(c['first'] or '')[:24]!r}")
    gates = []
    if body and lower / len(body) > 0.01:
        gates.append(f"{lower} paragraphs start in lowercase ({lower / len(body):.1%}): paragraph breaks are wrong")
    bad_open = [c["t"] for c in chapters if c["first"] and re.match(r"^[a-z]", c["first"])]
    if bad_open:
        gates.append(f"chapters opening mid-sentence: {bad_open}")
    if short_q > 5:
        gates.append(f"{short_q} short quotations: these may be subheadings (centred, bold, text size)")
    if words and unusual / words * 1000 > 2:
        gates.append(f"{unusual} unusual words ({unusual / words * 1000:.1f} per 1,000): a heavy proof")
    if any(c["h3"] > 15 for c in chapters):
        gates.append("a chapter with more than 15 subheadings: body lines may be read as headings")
    print("GATES:", "none tripped" if not gates else "")
    for g in gates:
        print("  -", g)


# ---------------------------------------------------------------- suspects

def cmd_suspects(a):
    text = _work(a.slug)
    known = _vocab()
    vocab = collections.Counter(w.lower() for w in re.findall(r"[A-Za-z]+", text))
    rows = []
    for page, ln in _lines_with_pages(text):
        if ln.startswith("## "):
            continue
        for mm in re.finditer(r"[A-Za-z0-9’'\-]+", ln):
            w = mm.group(0).strip("’'-")
            if not re.search(r"[A-Za-z]", w) or re.fullmatch(r"\d+(st|nd|rd|th|s|ff|f|a|b)", w):
                continue
            if "-" in w and re.fullmatch(r"[A-Za-z]+(-[A-Za-z]+)+", w) and \
                    all(x.lower() in known or vocab[x.lower()] > 1 for x in w.split("-")):
                continue
            core = re.sub(r"[’'].*$", "", w)
            lw = core.lower()
            if len(core) == 1 and core in "vQaAIO":
                continue
            bad = (re.search(r"[A-Za-z]\d|\d[A-Za-z]", w)
                   or (len(core) == 1 and not re.search(r"\(\w\)|\b[A-Z]\.", ln[max(0, mm.start() - 2):mm.end() + 2]))
                   or (len(lw) >= 3 and lw not in known and vocab[lw] <= 1)
                   or (len(lw) >= 6 and core[:1].islower() and re.search(r"[a-z][A-Z]", core)))
            if bad:
                rows.append(f"p{page} [{w}]  …{ln[max(0, mm.start() - 70):mm.start()]}⟦{mm.group(0)}⟧"
                            f"{ln[mm.end():mm.end() + 70]}…")
    out = _dir(a.slug) / "suspects.txt"
    out.write_text("\n".join(rows), encoding="utf-8")
    print(f"{a.slug}: {len(rows)} suspects -> {out}")


# ---------------------------------------------------------------- second reading, triage

def cmd_second(a):
    import pypdfium2 as pdfium
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT
    rows = _pages(a.slug)
    book = json.loads((_dir(a.slug) / "book.json").read_text(encoding="utf-8"))
    chs = [c for c in book["chapters"] if not c.get("skip")]
    first = a.first or min(c["start"] for c in chs)
    last = a.last or book.get("text_ends") or max(c["end"] for c in chs)
    pdf = pdfium.PdfDocument(_pdf(a.slug))
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower().replace("¬", "").replace("\ufffe", ""))
    out = []
    for n in range(first, last + 1):
        r = rows[n - 1]
        if not r["lines"]:
            continue
        page = pdf[n - 1]
        w, _ = page.get_size()
        img = page.render(scale=(3000 if r["src"] == "ocr" else 2000) / w).to_pil().convert("L")
        other = pytesseract.image_to_string(img, lang="eng", config="--psm 3")
        x = [t for t in " ".join(l["t"] for l in r["lines"]).split() if norm(t)]
        y = [t for t in other.split() if norm(t)]
        sm = difflib.SequenceMatcher(None, [norm(t) for t in x], [norm(t) for t in y], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            mine, theirs = " ".join(x[i1:i2]), " ".join(y[j1:j2])
            if op == "replace" and len(mine) > 60:
                continue
            ctx = " ".join(x[max(0, i1 - 6):i1]) + " ⟦" + mine + "⟧ " + " ".join(x[i2:i2 + 6])
            out.append(f"p{n} | built: {mine!r} | second read: {theirs!r} | {ctx}")
        print(f"  p{n}: {len(out)} disagreements so far", flush=True)
    (_dir(a.slug) / "second.txt").write_text("\n".join(out), encoding="utf-8")
    print(f"{a.slug}: {len(out)} disagreements -> second.txt; next: triage")


def cmd_triage(a):
    d = _dir(a.slug)
    known = _vocab()
    book = json.loads((d / "book.json").read_text(encoding="utf-8"))
    fixed_from = " ".join(f for f, _ in book.get("fixes") or [])
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    words = lambda s: re.findall(r"[A-Za-z]+", s)
    isknown = lambda w: w.lower() in known or len(w) == 1
    keep, why = [], collections.Counter()
    for ln in (d / "second.txt").read_text(encoding="utf-8").split("\n"):
        m = re.match(r"p(\d+) \| built: (.*?) \| second read: (.*?) \| (.*)$", ln)
        if not m:
            continue
        page, x, y, ctx = m.group(1), eval(m.group(2)), eval(m.group(3)), m.group(4)   # noqa: S307 (our own repr)
        wx, wy = words(x), words(y)
        if norm(x) == norm(y):
            why["same letters (hyphens, spacing)"] += 1
        elif x and x in fixed_from:
            why["already corrected"] += 1
        elif wx and all(isknown(w) for w in wx) and wy and not all(isknown(w) for w in wy):
            why["second read garbled"] += 1
        elif not wy and wx and all(isknown(w) for w in wx):
            why["second read dropped words"] += 1
        elif re.fullmatch(r"[\d\s:,;.\-–—()]*", x + y):
            why["numbers and punctuation"] += 1
        else:
            keep.append(f"p{page} | {x!r} vs {y!r} | {ctx}")
    (d / "triage.txt").write_text("\n".join(keep), encoding="utf-8")
    print(f"{a.slug}: {len(keep)} worth reading -> triage.txt; set aside: {dict(why)}")


# ---------------------------------------------------------------- stray marks

_MARKS = [
    ("odd character", r"[|\\_^~°¢¬*<>=#]"),
    ("lone quotation mark", r"(?<=\s)[‘’“”'\"](?=\s)|(?<=[a-z])[‘“](?=\s)|(?<=\s)[’”](?=[A-Za-z])"),
    ("quotation mark inside a word", r"(?<=[a-z])[‘“”](?=[a-z])"),
    ("doubled half-word", r"\b([A-Za-z]{2,})[:;,]?\s+(\1[a-z]{2,})\b"),
    ("space before punctuation", r"(?<=[a-z]) [,;:](?=\s)|(?<=[a-z]) \.(?= [a-z])"),
    ("doubled word", r"\b(\w+) \1\b"),
]


def cmd_marks(a):
    hits = []
    for page, ln in _lines_with_pages(_work(a.slug)):
        body = re.sub(r"^(### |> |## )", "", ln)
        for name, pat in _MARKS:
            for mm in re.finditer(pat, body):
                if name == "doubled word" and mm.group(1).lower() in ("that", "had", "is", "love"):
                    continue
                hits.append(f"p{page} [{name}] …{body[max(0, mm.start() - 50):mm.end() + 40]}…")
    out = _dir(a.slug) / "marks.txt"
    out.write_text("\n".join(hits), encoding="utf-8")
    print(f"{a.slug}: {len(hits)} spots -> {out}")


# ---------------------------------------------------------------- crop

def cmd_crop(a):
    import pypdfium2 as pdfium
    rows = _pages(a.slug)
    for pg in (a.page, a.page + 1, a.page - 1, a.page + 2):   # a paragraph's marker can sit a page before its words
        if 0 < pg <= len(rows):
            lines = rows[pg - 1]["lines"]
            hit = [i for i, l in enumerate(lines) if a.text in l["t"]]
            if hit:
                break
    else:
        sys.exit(f"'{a.text}' is not on or near p{a.page}")
    i = hit[0]
    lo, hi = max(0, i - a.up), min(len(lines) - 1, i + a.down)
    y0 = max(0.0, lines[lo]["y0"] - 0.012)
    y1 = min(1.0, lines[hi]["y1"] + 0.012)
    page = pdfium.PdfDocument(_pdf(a.slug))[pg - 1]
    w, _ = page.get_size()
    img = page.render(scale=1400 / w).to_pil()
    W, H = img.size
    out = _dir(a.slug) / "crops"
    out.mkdir(exist_ok=True)
    f = out / f"p{pg}-{i}.png"
    img.crop((int(W * 0.03), int(H * y0), int(W * 0.99), int(H * y1))).save(f)
    print(f)


# ---------------------------------------------------------------- fix

def cmd_fix(a):
    d = _dir(a.slug)
    text = _work(a.slug)
    if a.near:
        start, end, to = a.near[0], a.near[1], a.to_or_from
        if text.count(start) != 1:
            sys.exit(f"'{start}' occurs {text.count(start)} times; give a start that occurs once")
        i = text.index(start)
        j = text.find(end, i)
        if j < 0 or j + len(end) - i > 600:
            sys.exit("the end isn't within 600 characters of the start; a fix must stay short")
        frm = text[i:j + len(end)]
    else:
        frm, to = a.to_or_from, a.to
        if to is None:
            sys.exit("give <from> and <to>")
        if frm not in text:
            sys.exit("that text isn't in the built book (rebuild first if earlier fixes changed it)")
        if text.count(frm) > 1 and not a.all:
            sys.exit(f"that text occurs {text.count(frm)} times; add words around it, or --all to correct every one")
    book = json.loads((d / "book.json").read_text(encoding="utf-8"))
    book.setdefault("fixes", []).append([frm, to])
    (d / "book.json").write_text(json.dumps(book, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"fix {len(book['fixes'])}: {frm[:80]!r} -> {to[:80]!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("measure", "suspects", "triage", "marks"):
        sub.add_parser(name).add_argument("slug")
    s = sub.add_parser("second"); s.add_argument("slug"); s.add_argument("--first", type=int); s.add_argument("--last", type=int)
    c = sub.add_parser("crop"); c.add_argument("slug"); c.add_argument("page", type=int); c.add_argument("text")
    c.add_argument("--up", type=int, default=1); c.add_argument("--down", type=int, default=1)
    f = sub.add_parser("fix"); f.add_argument("slug"); f.add_argument("to_or_from"); f.add_argument("to", nargs="?")
    f.add_argument("--near", nargs=2, metavar=("START", "END")); f.add_argument("--all", action="store_true")
    a = ap.parse_args()
    {"measure": cmd_measure, "suspects": cmd_suspects, "second": cmd_second, "triage": cmd_triage,
     "marks": cmd_marks, "crop": cmd_crop, "fix": cmd_fix}[a.cmd](a)


if __name__ == "__main__":
    main()
