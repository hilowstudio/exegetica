"""Per-title review tooling for Exegetica editions (see docs/go-to-market-plan.md).

Grounds a title in a reference text and checks, word by word, that what the reader serves (after
the typesetting pass) still carries the whole book and nothing else.

    python scripts/review_title.py ref  <slug>          # fetch the reference text(s)
    python scripts/review_title.py diff <slug>          # fidelity report -> .seed_cache/reviews/<slug>/
    python scripts/review_title.py status [<slug>]      # the tracking table

References, by tier:
  A  Standard Ebooks: the book's own source repo (github.com/standardebooks/<repo>), cloned shallow.
  B  Project Gutenberg: the distributed HTML (pg<id>-images.html), header and licence removed.
  C  scans / OCR: not automated here; noted by hand.

Tracking lives in db/reviews.db (local; never published).
"""
from __future__ import annotations

import datetime
import difflib
import html as _html
import json
import re
import sqlite3
import subprocess
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from webapp import typeset as T  # noqa: E402

BOOKS = ROOT / "db" / "books.db"
REVIEWS = ROOT / "db" / "reviews.db"
REFS = ROOT / ".seed_cache" / "refs"
OUT = ROOT / ".seed_cache" / "reviews"
UA = {"User-Agent": "ExegeticaLibrary/1.0 (public-domain edition review)"}

SCHEMA = """
create table if not exists titles (
  slug text primary key, title text, author text, shelf text,
  rank integer, score real,
  tier text,                 -- A / B / C
  ref_sources text,          -- json list
  coverage real,             -- share of reference words present in our copy
  missing_words integer, extra_words integer, gaps integer,
  status text default 'queued',   -- queued / grounded / diffed / in-review / corrected / ready
  notes text, updated_at text
);
create table if not exists issues (
  id integer primary key, slug text, kind text, chapter integer, words integer,
  detail text, status text default 'open', fix text, created_at text
);
"""


def rdb() -> sqlite3.Connection:
    con = sqlite3.connect(REVIEWS)
    con.executescript(SCHEMA)
    return con


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- text normalisation
def html_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", h or "")
    h = re.sub(r'(?is)<a class="ex-ref"[^>]*>.*?</a>|<sup\b[^>]*>.*?</sup>', " ", h)   # note markers are not text
    h = re.sub(r"(?is)<br\s*/?>|</(p|div|h\d|li|tr|blockquote|section|header|aside)>", "\n", h)
    t = _html.unescape(re.sub(r"(?s)<[^>]+>", " ", h)).replace(T.SHY, "")
    return t


def tokens(t: str) -> list[str]:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = t.replace("’", "'").replace("‘", "'")
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", t)


# ---------------------------------------------------------------- our copy, as served
def our_chapters(slug: str) -> list[dict]:
    con = sqlite3.connect(BOOKS)
    bid, n = con.execute("select id, chapter_count from books where slug=?", (slug,)).fetchone()
    out = []
    front, = con.execute("select coalesce(front_html, '') from books where id=?", (bid,)).fetchone()
    if front:                                                 # the dedication / epigraph page
        out.append({"n": 0, "label": "", "name": "front", "text": html_text(front)})
    try:                                                      # a baked edition is the copy under review
        baked = {r[0]: r[1:] for r in con.execute(
            "select section_number, html, label, name from edition_chapters where book_id=?", (bid,))}
    except sqlite3.OperationalError:
        baked = {}
    for sn, title, h in con.execute("select section_number, title, html from book_chapters where book_id=? order by section_number", (bid,)):
        if sn in baked:
            served, label, name = baked[sn][0], baked[sn][1] or "", baked[sn][2] or ""
        else:
            served, label, name = T.typeset(h, title, sn == 1, sn == n and n > 1)
        body = re.sub(r"(?s)<header class=\"ex-open.*?</header>", " ", served)
        body = re.sub(r"(?is)<header\b[^>]*>(.*?)</header>",                 # inner headings, as for the reference
                      lambda m: " ".join(re.findall(r"(?is)<blockquote\b.*?</blockquote>", m.group(1))), body)
        body = re.sub(r"(?is)<(hgroup|h[1-6])\b.*?</\1>", " ", body)
        out.append({"n": sn, "label": label, "name": name, "text": html_text(body)})
    return out


# ---------------------------------------------------------------- references
def book_row(slug: str):
    con = sqlite3.connect(BOOKS)
    return con.execute("select slug, title, author, source, genres from books where slug=?", (slug,)).fetchone()


def ref_standardebooks(slug: str) -> Path | None:
    dest = REFS / "se" / slug
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "--depth", "1", "--quiet", f"https://github.com/standardebooks/{slug}", str(dest)],
                           capture_output=True, text=True)
        if r.returncode:
            print("  clone failed:", r.stderr.strip()[:200])
            return None
    return dest


def se_text(repo: Path) -> list[dict]:
    """The book's body text in spine order, one entry per file, skipping our-own-apparatus files."""
    opf = (repo / "src" / "epub" / "content.opf").read_text(encoding="utf-8")
    items = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', opf))
    items.update({m[1]: m[0] for m in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', opf)})
    spine = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)
    skip = re.compile(r"(?:titlepage|imprint|colophon|uncopyright|halftitle|loi|endnotes|toc)\.xhtml$")
    out = []
    for idref in spine:
        href = items.get(idref)
        if not href or skip.search(href):
            continue
        p = repo / "src" / "epub" / href
        if p.exists():
            h = p.read_text(encoding="utf-8")
            body = h.split("<body", 1)[-1].split(">", 1)[-1]          # past the <body …> attributes
            # headings are checked apart, but an epigraph inside a chapter header is text we show
            body = re.sub(r"(?is)<header\b[^>]*>(.*?)</header>",
                          lambda m: " ".join(re.findall(r"(?is)<blockquote\b.*?</blockquote>", m.group(1))), body)
            body = re.sub(r"(?is)<(hgroup|h[1-6])\b.*?</\1>", " ", body)
            out.append({"file": href, "text": html_text(body)})
    return out


def ref_gutenberg(gid: str) -> Path | None:
    dest = REFS / "pg" / f"{gid}.html"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        for url in (f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}-images.html",
                    f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.html"):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    dest.write_bytes(r.read())
                break
            except Exception:  # noqa: BLE001
                continue
    return dest if dest.exists() else None


def pg_text(path: Path) -> list[dict]:
    h = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"(?is)<(h[1-6])\b.*?</\1>", " ", h.split("<body", 1)[-1])   # headings are checked apart
    t = html_text(body)
    a = re.search(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", t, re.I | re.S)
    b = re.search(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", t, re.I)
    t = t[a.end() if a else 0: b.start() if b else len(t)]
    return [{"file": path.name, "text": t}]


def references(slug: str) -> tuple[str, list[str], list[dict]]:
    """-> (tier, source list, reference sections)."""
    row = book_row(slug)
    if not row:
        raise SystemExit(f"not in the library: {slug}")
    source = row[3]
    m = re.search(r"-pg(\d+)$", slug)
    if source == "standardebooks":
        repo = ref_standardebooks(slug)
        if repo:
            return "A", [f"https://github.com/standardebooks/{slug}"], se_text(repo)
    if m:
        gids = [m.group(1)] + merged_volumes(slug)            # a merged book is checked against every volume
        secs, srcs = [], []
        for gid in gids:
            p = ref_gutenberg(gid)
            if p:
                secs += pg_text(p)
                srcs.append(f"https://www.gutenberg.org/ebooks/{gid}")
        if secs:
            return "B", srcs, secs
    return "C", [], []


def merged_volumes(slug: str) -> list[str]:
    """Gutenberg ids of volumes merged into this book, in the order they were merged (from the deletion log)."""
    import csv  # noqa: PLC0415
    over = ROOT / "docs" / "review-references.json"         # books merged at import name their volumes here
    if over.exists():
        extra = json.loads(over.read_text(encoding="utf-8")).get(slug)
        if extra:
            return list(extra)
    out = []
    log = ROOT / "docs" / "reading-room-deletions.csv"
    if log.exists():
        for r in csv.reader(open(log, encoding="utf-8")):
            if len(r) >= 6 and r[5].strip() == f"merged into {slug}" and r[4].strip().isdigit():
                out.append(r[4].strip())
    return out


# ---------------------------------------------------------------- the fidelity diff
def _lis(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Longest chain of (i, j) anchors increasing in both coordinates (pairs arrive sorted by i)."""
    import bisect
    tails, tails_j, prev = [], [], [None] * len(pairs)
    for k, (_i, j) in enumerate(pairs):
        p = bisect.bisect_left(tails_j, j)
        if p == len(tails):
            tails.append(k)
            tails_j.append(j)
        else:
            tails[p], tails_j[p] = k, j
        prev[k] = tails[p - 1] if p else None
    out, k = [], tails[-1] if tails else None
    while k is not None:
        out.append(pairs[k])
        k = prev[k]
    return out[::-1]


def align(a: list[str], b: list[str], k: int = 8) -> list[tuple]:
    """Opcodes like difflib's, fast on whole books: lock the texts together at k-word runs that occur exactly
    once in each, then compare only the short stretches between those anchors in detail."""
    def once(seq):
        seen = {}
        for i in range(len(seq) - k + 1):
            g = tuple(seq[i:i + k])
            seen[g] = None if g in seen else i
        return {g: i for g, i in seen.items() if i is not None}
    ga, gb = once(a), once(b)
    pairs = sorted((i, gb[g]) for g, i in ga.items() if g in gb)
    anchors = _lis(pairs)
    ops, i0, j0 = [], 0, 0
    for i, j in anchors + [(len(a), len(b))]:
        if i < i0 or j < j0:
            continue
        if i > i0 or j > j0:                                  # the stretch before this anchor, in detail
            for tag, x1, x2, y1, y2 in difflib.SequenceMatcher(None, a[i0:i], b[j0:j], autojunk=False).get_opcodes():
                ops.append((tag, i0 + x1, i0 + x2, j0 + y1, j0 + y2))
        if i < len(a):
            ops.append(("equal", i, i + k, j, j + k))
        i0, j0 = i + k, j + k
    merged = []                                               # join adjacent equal runs
    for op in ops:
        if merged and op[0] == "equal" == merged[-1][0] and merged[-1][2] == op[1] and merged[-1][4] == op[3]:
            merged[-1] = ("equal", merged[-1][1], op[2], merged[-1][3], op[4])
        else:
            merged.append(op)
    return merged
def diff(slug: str) -> dict:
    tier, sources, ref = references(slug)
    ours = our_chapters(slug)
    ot, oc = [], []                                          # our tokens + their chapter numbers
    for ch in ours:
        tk = tokens(ch["text"])
        ot += tk
        oc += [ch["n"]] * len(tk)
    rt = [w for sec in ref for w in tokens(sec["text"])]
    report = {"slug": slug, "tier": tier, "sources": sources, "our_words": len(ot), "ref_words": len(rt),
              "chapters": len(ours), "ref_sections": len(ref), "missing": [], "extra": []}
    if not rt:
        report["coverage"] = None
        return report
    matched = 0
    for tag, i1, i2, j1, j2 in align(ot, rt):
        if tag == "equal":
            matched += j2 - j1
            continue
        if tag in ("delete", "replace") and i2 - i1 >= 1:
            report["extra"].append({"chapter": oc[i1] if i1 < len(oc) else None, "words": i2 - i1,
                                    "text": " ".join(ot[i1:i2])[:400],
                                    "context": " ".join(ot[max(0, i1 - 8):i1])})
        if tag in ("insert", "replace") and j2 - j1 >= 1:
            report["missing"].append({"chapter": oc[min(i1, len(oc) - 1)] if oc else None, "words": j2 - j1,
                                      "text": " ".join(rt[j1:j2])[:400],
                                      "context": " ".join(rt[max(0, j1 - 8):j1])})
    report["coverage"] = round(matched / len(rt), 5)
    report["missing_words"] = sum(x["words"] for x in report["missing"])
    report["extra_words"] = sum(x["words"] for x in report["extra"])
    # text that only moved (a dedication set on the front page, a note gathered at the chapter's end)
    def toks(x):
        return x["text"].split()

    moved = []
    for e in report["extra"]:                                 # one moved block may hold several missing pieces
        et = " ".join(toks(e))
        for m in report["missing"]:
            mt = " ".join(toks(m))
            if m.get("moved") or min(len(et), len(mt)) < 20:
                continue
            if mt in et or et in mt or difflib.SequenceMatcher(None, et, mt).ratio() > 0.85:
                moved.append((e, m))
                e["moved"] = m["moved"] = True
    for e, m in moved:
        e["moved"] = m["moved"] = True
    report["moved"] = [{"words": e["words"], "text": e["text"][:200], "from_chapter": m["chapter"], "to_chapter": e["chapter"]}
                       for e, m in moved]
    report["missing"] = [x for x in report["missing"] if not x.get("moved")]
    report["extra"] = [x for x in report["extra"] if not x.get("moved")]
    report["missing_words"] = sum(x["words"] for x in report["missing"])
    report["extra_words"] = sum(x["words"] for x in report["extra"])
    report["coverage"] = round(1 - report["missing_words"] / len(rt), 5)
    report["big_missing"] = [x for x in report["missing"] if x["words"] >= 12]
    report["big_extra"] = [x for x in report["extra"] if x["words"] >= 12]
    return report


def ref_headings(slug: str) -> list[str]:
    """The reference's chapter headings in reading order (Standard Ebooks: each body file's header;
    Gutenberg: h2/h3 headings in every referenced volume)."""
    tier, _src, _secs = references(slug)
    out = []
    if tier == "A":
        repo = REFS / "se" / slug
        opf = (repo / "src" / "epub" / "content.opf").read_text(encoding="utf-8")
        for item in re.findall(r'<itemref\b[^>]*\bidref="([^"]+)"', opf):
            p = repo / "src" / "epub" / "text" / item
            if not p.exists() or re.search(r"titlepage|imprint|colophon|uncopyright|endnotes|toc|dedication|epigraph", item):
                continue
            x = p.read_text(encoding="utf-8").split("<body", 1)[-1]
            for m in re.finditer(r"(?is)<(?:header|hgroup)\b[^>]*>(.*?)</(?:header|hgroup)>|<(h[1-6])\b[^>]*>(.*?)</\2>", x):
                inner = m.group(1) if m.group(1) is not None else m.group(3)
                inner = re.sub(r"(?is)<blockquote\b.*?</blockquote>", " ", inner)
                t = re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", inner))).strip()
                if t:
                    out.append(t)
                break
    else:
        for gid in ([re.search(r"-pg(\d+)$", slug).group(1)] + merged_volumes(slug)) if re.search(r"-pg(\d+)$", slug) else []:
            p = REFS / "pg" / f"{gid}.html"
            if p.exists():
                h = p.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r"(?is)<(h[23])\b[^>]*>(.*?)</\1>", h):
                    t = re.sub(r"\s+", " ", _html.unescape(re.sub(r"(?s)<[^>]+>", " ", m.group(2)))).strip()
                    if t and not re.search(r"(?i)gutenberg|contents|^by$|transcriber", t):
                        out.append(t)
    return out


def headings(slug: str) -> list[dict]:
    """Our contents (label · name) against the reference headings, aligned; mismatches only."""
    ours = [c for c in our_chapters(slug) if c["n"] > 0]
    mine = [" ".join(x for x in (c["label"], c["name"]) if x) for c in ours]
    theirs = ref_headings(slug)
    norm = lambda s: " ".join(tokens(s))  # noqa: E731
    a, b = [norm(x) for x in mine], [norm(x) for x in theirs]
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            o = mine[i1 + k] if i1 + k < i2 else ""
            r = theirs[j1 + k] if j1 + k < j2 else ""
            # numerals spelled out ("Chapter One" for "Chapter I") and case are house style, not a mismatch
            if o and r and _same_heading(o, r):
                continue
            out.append({"chapter": ours[i1 + k]["n"] if i1 + k < i2 else None, "ours": o, "reference": r})
    return out


def _same_heading(o: str, r: str) -> bool:
    def core(s):
        s = re.sub(r"(?i)\b(?:chapter|stave|book|part|letter|canto|section)\b", " ", s)
        s = re.sub(r"\b[IVXLCDM]+\b\.?|\b\d+\b", " ", s)
        s = re.sub(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                   r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b", " ", s)
        return " ".join(tokens(s))
    return core(o) == core(r) or (core(o) and core(o) in core(r)) or (core(r) and core(r) in core(o))


def write_report(rep: dict) -> Path:
    d = OUT / rep["slug"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "fidelity.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Fidelity: {rep['slug']}", "",
             f"- Tier {rep['tier']}; reference: {', '.join(rep['sources']) or 'none'}",
             f"- Our words {rep['our_words']:,} · reference words {rep['ref_words']:,} · coverage "
             f"{rep['coverage'] if rep['coverage'] is None else f'{rep['coverage']:.3%}'}",
             f"- Missing {rep.get('missing_words', 0):,} words in {len(rep['missing'])} spans "
             f"({len(rep.get('big_missing', []))} of 12+ words); extra {rep.get('extra_words', 0):,} words in "
             f"{len(rep['extra'])} spans ({len(rep.get('big_extra', []))} of 12+)", "",
             "## Missing from our copy (12+ words)", ""]
    for x in rep.get("big_missing", []):
        lines.append(f"- ch {x['chapter']} · {x['words']} words · after “…{x['context']}”: {x['text'][:300]}")
    lines += ["", "## In our copy but not the reference (12+ words)", ""]
    for x in rep.get("big_extra", []):
        lines.append(f"- ch {x['chapter']} · {x['words']} words · after “…{x['context']}”: {x['text'][:300]}")
    p = d / "fidelity.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def record(rep: dict) -> None:
    row = book_row(rep["slug"])
    con = rdb()
    con.execute("""insert into titles(slug, title, author, shelf, tier, ref_sources, coverage, missing_words, extra_words,
                   gaps, status, updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?)
                   on conflict(slug) do update set tier=excluded.tier, ref_sources=excluded.ref_sources,
                   coverage=excluded.coverage, missing_words=excluded.missing_words, extra_words=excluded.extra_words,
                   gaps=excluded.gaps, status=case when titles.status in ('queued','grounded') then 'diffed' else titles.status end,
                   updated_at=excluded.updated_at""",
                (rep["slug"], row[1], row[2], (json.loads(row[4] or "[]") or [""])[0], rep["tier"], json.dumps(rep["sources"]),
                 rep["coverage"], rep.get("missing_words"), rep.get("extra_words"),
                 len(rep.get("big_missing", [])) + len(rep.get("big_extra", [])), "diffed", now()))
    con.commit()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "status"), sys.argv[2:]
    if cmd == "ref":
        tier, sources, ref = references(args[0])
        print(f"tier {tier}; {len(ref)} sections; {sum(len(tokens(s['text'])) for s in ref):,} words; {sources}")
    elif cmd == "diff":
        for slug in (a.strip() for a in args if a.strip()):
            try:
                rep = diff(slug)
            except (Exception, SystemExit) as e:  # noqa: BLE001 — one title never stops the batch
                print(f"{slug}: FAILED {type(e).__name__}: {e}"[:300], flush=True)
                continue
            record(rep)
            p = write_report(rep)
            cov = rep["coverage"]
            print(f"{slug}: tier {rep['tier']} coverage {cov if cov is None else f'{cov:.3%}'} · missing "
                  f"{rep.get('missing_words', 0):,} words ({len(rep.get('big_missing', []))} big gaps) · extra "
                  f"{rep.get('extra_words', 0):,} words ({len(rep.get('big_extra', []))} big) -> {p.relative_to(ROOT)}")
    elif cmd == "headings":
        for slug in (a.strip() for a in args if a.strip()):
            try:
                hs = headings(slug)
            except (Exception, SystemExit) as e:  # noqa: BLE001
                print(f"{slug}: FAILED {e}"[:200])
                continue
            print(f"== {slug}: {len(hs)} heading difference(s)")
            for h in hs[:40]:
                print(f"   ch {h['chapter']}: ours {h['ours'][:70]!r} | reference {h['reference'][:70]!r}")
    elif cmd == "status":
        con = rdb()
        q = "select slug, rank, tier, coverage, gaps, status from titles" + (" where slug=?" if args else " order by rank")
        for r in con.execute(q, args[:1]):
            print(r)


if __name__ == "__main__":
    main()
