"""Seed the Reading Room with the CCEL theology corpus (reconstructed from ccel-paragraphs).

theology.db stores each work as a flat paragraph stream built for grounding search — no chapter
structure. But the upstream dataset (jncraton/ccel-paragraphs) carries, per paragraph, the CCEL
ThML division id (e.g. 'c1', 'FP_Q1_A1') and the original ThML markup. This rebuilds readable,
chapter-structured books from that: group paragraphs by division into chapters (grain-capped by
word count), clean the ThML to portable HTML, and write into db/books.db as source='ccel' — shelved
alongside the Standard Ebooks under a 'Theology' genre.

Licensing (see the triage in-line): the curated set is theology.db's 985 works. CCEL marks ~579 of
them public domain -> serve. 3 are genuinely in-copyright modern editions -> exclude. The 403 CCEL
never tagged get a RISK-BASED DATE GATE: served unless a copyright/publication year >= 1930 is found
in the text (a modern-edition signal), in which case the work is HELD for manual review. Low residual
risk by design; held works are listed so a human can clear them.

    .venv\\Scripts\\python.exe scripts\\seed_theology_reader.py --shards 1 --db db/books_test.db  # smoke
    .venv\\Scripts\\python.exe scripts\\seed_theology_reader.py                                    # full
    .venv\\Scripts\\python.exe scripts\\seed_theology_reader.py --dry-run                          # buckets only
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys

os.environ.pop("HF_HUB_OFFLINE", None)
_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from bs4 import BeautifulSoup  # noqa: E402

from webapp.sources.standardebooks import _KEEP_TAGS, _sort_key_from_name  # noqa: E402

_THEO_DB = _ROOT / "db" / "theology.db"
_DATASET = "jncraton/ccel-paragraphs"
SOURCE = "ccel"
LICENSE = "Public Domain (CCEL)"
GENRE = "Theology"

_GATE_YEAR = 1930          # untagged work is HELD if a copyright/pub year >= this appears in it
_CHAP_CAP = 7000           # split a division subtree into finer chapters above this many words
_MAXDEPTH = 4
_MIN_CHAP_WORDS = 20       # drop title/copyright/blank front-matter pages

# ThML elements to remove with their contents (footnotes, page breaks, popups).
_DROP_WHOLE = {"script", "style", "nav", "aside", "note", "pb", "scripcom"}


# --------------------------------------------------------------------------- #
# license triage (mirrors scripts/theology_triage.py) -> serve / exclude / gate
# --------------------------------------------------------------------------- #
def _death_years(r): return [int(y) for y in re.findall(r"(?:died|dod)\s*(\d{4})", r)]

def bucket(rights: str | None) -> str:
    r = (rights or "").strip().lower()
    if not r:
        return "gate"                                   # the 403 untagged -> date gate
    if "renewed" in r and "not renewed" not in r:
        return "exclude"                                 # copyright note renewed
    if ("translator" in r or "editor" in r) and any(y >= 1956 for y in _death_years(r)):
        return "exclude"                                 # modern translation/apparatus
    if "by permission" in r:
        return "exclude"                                 # permission-only e-text
    if "public domain" in r:
        return "serve"
    if any(k in r for k in ("all rights reserved", "copyrighted", "©")):
        return "exclude"
    return "gate"                                        # unknown phrasing -> be cautious


def curated(con) -> dict:
    """title -> {author_slug, rights, published, bucket} for the 985 curated works."""
    out = {}
    for title, author, rights, published in con.execute(
            "select title, author, rights, published from theology_works"):
        out[title] = {"author_slug": author, "rights": rights, "published": published,
                      "bucket": bucket(rights)}
    return out


# --------------------------------------------------------------------------- #
# ThML -> clean chapter HTML
# --------------------------------------------------------------------------- #
def clean_chapter(thml: str) -> tuple[str, int]:
    soup = BeautifulSoup("<article>" + thml + "</article>", "html.parser")
    root = soup.find("article")
    for t in root.find_all(_DROP_WHOLE):
        t.decompose()
    for l in root.find_all("l"):                          # poetry line -> keep text + line break
        l.insert_after(soup.new_tag("br"))
    for a in root.find_all("a"):                          # cross-file anchors don't resolve
        a.unwrap()
    for tag in root.find_all(True):
        if tag.name in _KEEP_TAGS:
            tag.attrs = {}
        else:                                            # scripture/scripref/span/name/sync/… -> keep text
            tag.unwrap()
    html = root.decode_contents().strip()
    html = re.sub(r"<p>\s*</p>", "", html)               # drop empty paragraphs
    html = re.sub(r"\n{3,}", "\n\n", html).strip()
    words = len(re.sub(r"<[^>]+>", " ", html).split())
    return html, words


_ROMAN = re.compile(r"^[ivxlcdm]{1,6}$", re.I)
_PART = {"FP": "Part I", "FS": "Part I-II", "SS": "Part II-II", "TP": "Part III", "XP": "Supplement"}


def div_label(comps: list[str]) -> str | None:
    """A readable chapter label from a CCEL division key (e.g. ['FP','Q1'] -> 'Part I, Question 1',
    ['c','12']? no — 'c12' -> 'Chapter 12'). Returns None if nothing matched a known pattern."""
    parts, matched = [], False
    for c in comps:
        if c in _PART:
            parts.append(_PART[c]); matched = True
        elif re.fullmatch(r"[Qq]\d+", c):
            parts.append("Question " + c[1:]); matched = True
        elif re.fullmatch(r"[Aa]\d+", c):
            parts.append("Article " + c[1:]); matched = True
        elif re.fullmatch(r"[Cc]\d+", c):
            parts.append("Chapter " + c[1:]); matched = True
        elif _ROMAN.fullmatch(c):
            parts.append("Chapter " + c.upper()); matched = True
        elif re.fullmatch(r"\d+", c):
            parts.append(c); matched = True
        else:
            parts.append(c)
    return ", ".join(parts) if matched else None


# CCEL marks headings by paragraph class (chaptertitle / SectionInfo / psalmTitle / …). The raw
# thml keeps these even though clean_chapter strips them, so titles come straight from the source.
_HEAD_CLASS = re.compile(r"title|head|sectioninfo", re.I)


def heading_from_run(run) -> str | None:
    for _c, text, thml in run:
        m = re.search(r'class="([^"]+)"', thml or "")
        if m and _HEAD_CLASS.search(m.group(1)) and (text or "").strip():
            return re.sub(r"\s+", " ", text.strip())
    return None


def _components(divid: str) -> list[str]:
    return [c for c in re.split(r"[._]", divid) if c]


def _divid(paragraph_id: str) -> str:
    frag = paragraph_id.split(":", 1)[1] if ":" in paragraph_id else paragraph_id
    return re.sub(r"[-.]p\d+(?:\.\d+)*$", "", frag) or frag


def build_chapters(rows: list[tuple[str, str, str]]) -> list[dict]:
    """rows: [(division, text, thml)] in reading order. Group by division subtree, splitting any
    subtree over the word cap one level deeper. Returns [{title, html, words}] (front matter dropped)."""
    items = [(_components(d), text, thml) for d, text, thml in rows]

    def wc(text): return len(text.split())

    def group(seq, depth):
        runs, out = [], []
        for comps, text, thml in seq:
            key = tuple(comps[:depth])
            if runs and runs[-1][0] == key:
                runs[-1][1].append((comps, text, thml))
            else:
                runs.append((key, [(comps, text, thml)]))
        for key, run in runs:
            words = sum(wc(t) for _c, t, _h in run)
            if words > _CHAP_CAP and depth < _MAXDEPTH and any(len(c) > depth for c, _t, _h in run):
                out.extend(group(run, depth + 1))
            else:
                out.append((list(key), run))              # (division-prefix, paragraphs)
        return out

    chapters = []
    for prefix, run in group(items, 1):
        html, words = clean_chapter("\n".join(h for _c, _t, h in run))
        if words < _MIN_CHAP_WORDS:
            continue
        head = heading_from_run(run)                      # a class="chaptertitle"/… paragraph
        first = next((t.strip() for _c, t, _h in run if t and t.strip()), "")  # first non-empty line
        if head:
            title = head
        elif 0 < len(first.split()) <= 12:
            title = first                                 # a short leading line is a heading
        else:
            title = div_label(prefix) or f"Section {len(chapters) + 1}"
        title = re.sub(r"\s+", " ", title).strip(" .")
        if _norm_title(title) in _FRONT_TITLES:           # front matter in the heuristic path too
            continue
        chapters.append({"title": title[:120], "html": html, "words": words})
    return chapters


# --------------------------------------------------------------------------- #
# TOC-driven chaptering (authoritative titles + front-matter drop, from CCEL ThML)
# --------------------------------------------------------------------------- #
_TOC_CACHE = _ROOT / ".seed_cache" / "ccel_toc"
# Divisions that are front matter — the reader supplies its own title page, so these are dropped.
# Prefaces / introductions / forewords / prologues are real content and kept.
_FRONT_TITLES = {
    "title page", "title pages", "titlepage", "title", "cover", "cover page", "copyright",
    "contents", "table of contents", "colophon", "index", "indexes", "endnotes",
    "advertisements", "advertisement", "half title", "half-title", "frontispiece", "imprint",
    "dedication", "errata", "publisher's note", "publishers note", "publishers' note",
    "publisher's foreword", "publisher's foreward", "list of illustrations", "illustrations",
    "prefatory material", "pefatory material", "prefatory", "prefatory note", "approbations",
    "approbation", "transcriber's note", "transcriber's notes", "preface to online edition",
    "preface to the online edition", "online edition", "online preface",
    "introductory note", "introductory notice", "translator's preface", "translators preface",
}


def _norm_title(s: str) -> str:
    """For front-matter matching: collapse whitespace, drop trailing '.', unify curly quotes."""
    s = re.sub(r"\s+", " ", s or "").strip().strip(" .")
    return s.replace("’", "'").replace("‘", "'").lower()


def _toc_key(workpath: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", workpath or "")


def load_toc(workpath: str):
    p = _TOC_CACHE / (_toc_key(workpath) + ".json")
    if not p.exists():
        return None
    try:
        toc = json.loads(p.read_text(encoding="utf-8"))
        return toc or None
    except Exception:  # noqa: BLE001
        return None


def _ancestors(divid: str) -> list[str]:
    # Hierarchy separator in CCEL ThML ids is '.' only; '_' is part of a single segment
    # (e.g. 'ii_1' is a top-level work id, NOT a child of front-matter 'ii'). Splitting on '_'
    # too made whole works inherit a front-matter ancestor and get dropped.
    cur, out = divid, [divid]
    while True:
        m = re.match(r"^(.*)\.[^.]+$", cur)
        if not m:
            break
        cur = m.group(1)
        out.append(cur)
    return out


def _trim_title(t: str) -> str:
    t = re.sub(r"\s+", " ", (t or "").strip()).strip(" .")
    if len(t) <= 120:
        return t
    cut = t[:120].rsplit(" ", 1)[0]
    return cut + "…"


def toc_chapters(rows: list[tuple[str, str, str]], toc: list[dict]) -> list[dict] | None:
    """Chapter the work by its CCEL ThML div tree: real titles, front matter dropped, grain capped
    by word count (a big div splits into its children). Returns None if the TOC doesn't fit the data."""
    node = {n["id"]: n for n in toc if n.get("id")}
    if not node:
        return None

    def is_front(divid):
        for a in _ancestors(divid):
            n = node.get(a)
            if not n:
                continue
            t = _norm_title(n["title"])
            if (t in _FRONT_TITLES or "copyright" in t
                    or n.get("cls", "") in ("TitlePage", "Copyright", "Contents", "Cover")):
                return True
        return False

    # paragraphs -> nearest TOC node (in reading order)
    from collections import OrderedDict
    para_by_div: "OrderedDict[str, list]" = OrderedDict()
    for div, text, thml in rows:
        nid = next((a for a in _ancestors(div) if a in node), div)
        para_by_div.setdefault(nid, []).append((text or "", thml or ""))
    if not any(nid in node for nid in para_by_div):
        return None                                       # ids don't line up with this TOC

    # children map (parent = nearest present ancestor) over ids that actually carry paragraphs' lineage
    all_ids = [n["id"] for n in toc]
    children = {i: [] for i in all_ids}
    roots = []
    for nid in all_ids:
        parent = next((a for a in _ancestors(nid)[1:] if a in node), None)
        (children[parent].append(nid) if parent else roots.append(nid))

    def subtree_paras(nid):
        return [p for d, ps in para_by_div.items() if nid in _ancestors(d) for p in ps]

    def words(nid):
        return sum(len(t.split()) for t, _ in subtree_paras(nid))

    chapters = []

    def emit(paras, title):
        if not paras:
            return
        html_, w = clean_chapter("\n".join(th for _t, th in paras))
        if w < _MIN_CHAP_WORDS:
            return
        chapters.append({"title": _trim_title(title) or f"Section {len(chapters) + 1}",
                         "html": html_, "words": w})

    def walk(nid):
        if is_front(nid):
            return
        kids = [c for c in children.get(nid, []) if not is_front(c)]
        title = node[nid]["title"] if nid in node else ""
        if words(nid) <= _CHAP_CAP or not kids:
            emit(subtree_paras(nid), title)
        else:
            emit(para_by_div.get(nid, []), title)         # this div's own lead text, if any
            for c in kids:
                walk(c)

    for r in roots:
        walk(r)
    # orphan paragraphs whose leaf had no TOC ancestor — keep them so nothing is lost
    for nid, ps in para_by_div.items():
        if nid not in node:
            emit(ps, "")
    return chapters or None


# --------------------------------------------------------------------------- #
# books.db writer
# --------------------------------------------------------------------------- #
_SCHEMA = """
create table if not exists books (
    id integer primary key autoincrement, slug text unique not null, title text not null,
    author text, author_sort text, source text not null, license text, us_clear integer not null default 1,
    language text, subjects text, genres text, chapter_count integer not null default 0,
    word_count integer not null default 0, added_at text not null default (datetime('now')));
create table if not exists book_chapters (
    book_id integer not null, section_number integer not null, title text, html text not null,
    words integer not null default 0, primary key (book_id, section_number));
create index if not exists book_chapters_book_idx on book_chapters(book_id);
"""


def _slug(workpath: str) -> str:
    stem = re.sub(r"\.xml$", "", workpath)                # ccel/a/aaberg/hymnsdenmark.xml
    parts = [p for p in stem.split("/") if p not in ("ccel",) and len(p) > 1]
    return "ccel-" + "-".join(parts[-2:]) if len(parts) >= 2 else "ccel-" + re.sub(r"\W+", "-", stem)


def write_book(con, slug, title, author, chapters):
    author_sort = _sort_key_from_name(author) if author else ""
    row = con.execute("select id from books where slug=?", (slug,)).fetchone()
    if row:
        con.execute("delete from book_chapters where book_id=?", (row[0],))
        con.execute("delete from books where id=?", (row[0],))
    cur = con.execute(
        """insert into books(slug, title, author, author_sort, source, license, us_clear,
                             language, subjects, genres, chapter_count, word_count)
           values(?,?,?,?,?,?,1,?,?,?,?,?)""",
        (slug, title, author, author_sort, SOURCE, LICENSE, "en", "[]",
         json.dumps([GENRE]), len(chapters), sum(c["words"] for c in chapters)))
    bid = cur.lastrowid
    con.executemany(
        "insert into book_chapters(book_id, section_number, title, html, words) values(?,?,?,?,?)",
        [(bid, i, c["title"], c["html"], c["words"]) for i, c in enumerate(chapters, 1)])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="db/books.db")
    ap.add_argument("--shards", type=int, default=0, help="cap shards (0=all) — smoke test")
    ap.add_argument("--limit", type=int, default=0, help="cap works built (0=all)")
    ap.add_argument("--dry-run", action="store_true", help="report buckets/gate only")
    ap.add_argument("--rebuild", action="store_true",
                    help="skip download/staging; rebuild books.db from the existing stage db (fast title iteration)")
    ap.add_argument("--toc", action=argparse.BooleanOptionalAction, default=True,
                    help="use cached CCEL ThML TOC for authoritative titles + front-matter drop (default on)")
    args = ap.parse_args()

    con_t = sqlite3.connect(_THEO_DB)
    works = curated(con_t)
    con_t.close()
    counts = {"serve": 0, "exclude": 0, "gate": 0}
    for w in works.values():
        counts[w["bucket"]] += 1
    print(f"curated works: {len(works)}  |  serve {counts['serve']}  exclude {counts['exclude']}  "
          f"gate(untagged) {counts['gate']}", flush=True)

    stage_path = _ROOT / ".seed_cache" / "ccel_reader_stage.db"
    if args.rebuild:
        if not stage_path.exists():
            sys.exit("no stage db — run once without --rebuild to download/stage first.")
        st = sqlite3.connect(stage_path)
        print("rebuild: using existing stage db (no download)", flush=True)
    else:
        import pyarrow.parquet as pq
        from huggingface_hub import HfApi, hf_hub_download
        files = sorted(f for f in HfApi().list_repo_files(_DATASET, repo_type="dataset") if f.endswith(".parquet"))
        if args.shards:
            files = files[: args.shards]
        stage_path.parent.mkdir(exist_ok=True)
        if stage_path.exists():
            stage_path.unlink()
        st = sqlite3.connect(stage_path)
        st.execute("pragma journal_mode=off"); st.execute("pragma synchronous=off")
        st.execute("create table stage(sid integer primary key autoincrement, title text, workpath text, "
                   "division text, text text, thml text)")
        st.execute("create table meta(title text primary key, author text, workpath text)")
        keep = {t for t, w in works.items() if w["bucket"] != "exclude"}
        for i, rel in enumerate(files):
            print(f"  shard {i+1}/{len(files)}: downloading…", flush=True)
            path = hf_hub_download(_DATASET, rel, repo_type="dataset")
            pf = pq.ParquetFile(path)
            n = 0
            for b in pf.iter_batches(columns=["id", "title", "text", "thml", "author-short-form"], batch_size=20000):
                ids = b.column("id").to_pylist(); tis = b.column("title").to_pylist()
                txs = b.column("text").to_pylist(); ths = b.column("thml").to_pylist()
                aus = b.column("author-short-form").to_pylist()
                rows, metas = [], {}
                for idv, ti, tx, th, au in zip(ids, tis, txs, ths, aus):
                    if ti not in keep:
                        continue
                    rows.append((ti, idv.split(":", 1)[0], _divid(idv), tx or "", th or ""))
                    if ti not in metas:
                        metas[ti] = (au or "", idv.split(":", 1)[0])
                if rows:
                    st.executemany("insert into stage(title, workpath, division, text, thml) values(?,?,?,?,?)", rows)
                    n += len(rows)
                for ti, (au, wp) in metas.items():
                    st.execute("insert or ignore into meta(title, author, workpath) values(?,?,?)", (ti, au, wp))
            st.commit()
            print(f"    staged {n:,} paragraphs", flush=True)
        st.execute("create index if not exists stage_title_idx on stage(title)")
        st.commit()

    st.execute("create index if not exists stage_title_idx on stage(title)")

    # ---- gate decisions (copyright/pub year scan over the untagged works, from the stage) ----
    gate_year = {}
    yr_re = re.compile(r"(?:copyright|©)[^\d]{0,12}(19\d\d|20\d\d)", re.I)
    for t, w in works.items():
        if w["bucket"] != "gate":
            continue
        mx = 0
        for (txt,) in st.execute("select text from stage where title=?", (t,)):
            m = yr_re.search(txt or "")
            if m:
                mx = max(mx, int(m.group(1)))
        if mx:
            gate_year[t] = mx
    served_titles, held = [], []
    for t, w in works.items():
        if w["bucket"] == "exclude":
            continue
        if w["bucket"] == "gate":
            y = gate_year.get(t)
            pub = None
            m = re.search(r"(1[5-9]\d\d|20\d\d)", w["published"] or "")
            if m:
                pub = int(m.group(0))
            latest = max([x for x in (y, pub) if x] or [0])
            if latest >= _GATE_YEAR:
                held.append((t, latest)); continue
        served_titles.append(t)

    print(f"\ngate: {len(held)} untagged works HELD (modern-edition year >= {_GATE_YEAR}); "
          f"{sum(1 for t in served_titles if works[t]['bucket']=='gate')} untagged served", flush=True)
    if held:
        for t, y in sorted(held, key=lambda x: -x[1])[:40]:
            print(f"    HOLD [{y}] {t[:60]!r}", flush=True)

    if args.dry_run:
        print("\n(dry run — no build)"); st.close(); return

    # ---- build chapters per served work, write to books.db ----
    out = _ROOT / args.db
    con = sqlite3.connect(out)
    con.executescript(_SCHEMA)
    con.execute("delete from book_chapters where book_id in (select id from books where source=?)", (SOURCE,))
    con.execute("delete from books where source=?", (SOURCE,))
    con.commit()

    built = skipped = used_toc = 0
    order = served_titles[: args.limit] if args.limit else served_titles
    for t in order:
        rows = st.execute("select division, text, thml from stage where title=? order by sid", (t,)).fetchall()
        if not rows:
            skipped += 1; continue
        meta = st.execute("select author, workpath from meta where title=?", (t,)).fetchone()
        author, workpath = (meta or ("", t))
        chapters = None
        if args.toc and workpath:
            toc = load_toc(workpath)
            if toc:
                chapters = toc_chapters(rows, toc)     # authoritative titles + front-matter drop
                if chapters:
                    used_toc += 1
        if not chapters:
            chapters = build_chapters(rows)            # heuristic fallback (no/partial TOC)
        if not chapters:
            skipped += 1; continue
        write_book(con, _slug(workpath or t), t, author, chapters)
        built += 1
        if built % 100 == 0:
            con.commit()
            print(f"    built {built}…", flush=True)
    con.commit()
    print(f"  titled from CCEL TOC: {used_toc} / {built}", flush=True)
    n_books = con.execute("select count(*) from books where source=?", (SOURCE,)).fetchone()[0]
    n_ch = con.execute("select count(*) from book_chapters where book_id in "
                       "(select id from books where source=?)", (SOURCE,)).fetchone()[0]
    con.close(); st.close()
    print(f"\nbuilt {built} theology books ({skipped} skipped) — {n_books} in db, {n_ch:,} chapters "
          f"→ {args.db} ({out.stat().st_size/1e6:.0f} MB)")
    print("publish with: .venv\\Scripts\\python.exe scripts\\publish_db.py books")


if __name__ == "__main__":
    main()
