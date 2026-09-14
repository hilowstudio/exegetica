"""Wave 1 — build the local theological grounding corpus for the MCP from ccel-paragraphs.

Loads the curated PD theology subset (full text + scripture refs, paragraph-level) into
db/study_bible.db as `theology_texts` + an FTS5 index `theology_fts`, plus a `theology_works`
catalog. This is grounding data the chat model + generators read at call time — no derivation.
model2vec semantic vectors are a follow-up step (build_theology_vectors.py).

Curation: exclude authors the MCP already serves (Calvin/Henry/JFB/Gill/Barnes/Wesley commentaries,
Bible translations), non-PD (Robertson, renewed 1960), and fiction/secular/liberal; drop
translation/dictionary/foreign-Bible titles by pattern. Everything else is net-new theology.

    .venv\\Scripts\\python.exe scripts\\build_theology_grounding.py --dry-run   # show curated set
    .venv\\Scripts\\python.exe scripts\\build_theology_grounding.py             # extract + load
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

_DB = _ROOT / "db" / "theology.db"   # SEPARATE file — distributed via R2, ATTACHed by the MCP
_INVENTORY = _ROOT / ".seed_cache" / "ccel_titles.json"

# Authors the MCP already serves, or that don't belong in a Reformed PD grounding treasury.
DENY_AUTHORS = {
    "bible",                                             # translations (have)
    "calvin", "henry", "jamieson", "gill", "barnes",    # commentaries (in get_commentary)
    "nave",                                              # topical dict (have)
    "robertson", "robertson_at",                        # NON-PD (Word Pictures, renewed 1960)
    "macdonald", "tolstoy", "dostoevsky",               # fiction
    "gibbon", "renan", "harnack",                       # secular / liberal history
    "chesterton",                                        # d.1936: fiction + some (c); PD works allow-listed
    "white",                                            # uncertain author
}
# Titles that override an author-level deny — specific PD, US-clear, theologically relevant works.
ALLOW_TITLES = {
    # G.K. Chesterton apologetics/theology, all first published <=1929 (US public domain). His
    # fiction (Father Brown, The Man Who Was Thursday, …) stays denied, as does the 1933
    # "St. Thomas Aquinas" (still under US copyright until 2029).
    "Orthodoxy", "Heretics", "The Everlasting Man", "What's Wrong With the World",
    "All Things Considered", "Eugenics and Other Evils", "The Defendant",
    "The Superstition of Divorce",
}
# Title patterns to drop (translations, dictionaries, foreign-language Bibles).
DENY_TITLE = re.compile(
    r"(Holy Bible|Ang Biblia|Version of the Holy|Douay|Septuagint|Vulgate|"
    r"Nave'?s Topical|Strong'?s|Concordance|\bTranslation\b|Terjemahan)",
    re.I,
)


def curated_from_inventory():
    inv = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    keep = {}
    for title, v in inv.items():
        author = (v.get("author") or "").strip()
        if title in ALLOW_TITLES:
            keep[title] = v
            continue
        if author in DENY_AUTHORS or DENY_TITLE.search(str(title)):
            continue
        keep[title] = v
    return keep


def report(keep):
    by_author = {}
    for t, v in keep.items():
        a = by_author.setdefault(v["author"] or "?", {"titles": 0, "chars": 0})
        a["titles"] += 1
        a["chars"] += v["chars"]
    chars = sum(v["chars"] for v in keep.values())
    print(f"curated theology works: {len(keep)} titles across {len(by_author)} authors")
    print(f"  ~{chars/1e6:.0f}M chars  (~{chars//4/1e6:.0f}M tokens; FTS index roughly 0.4-0.6x the text size)")
    print("  top authors:")
    for a, x in sorted(by_author.items(), key=lambda z: -z[1]["chars"])[:20]:
        print(f"    {a[:20]:20} {x['titles']:>4} titles  {x['chars']/1e6:>6.1f}M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--shards", type=int, default=0, help="cap shards read (0 = all) — for a smoke test")
    args = ap.parse_args()

    keep = curated_from_inventory()
    report(keep)
    if args.dry_run:
        print("\n(dry run — no extraction/load)")
        return

    # ---- extract text+refs for curated titles from the HF parquet, load into SQLite ----
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, HfFileSystem

    keep_titles = set(keep)
    _DB.parent.mkdir(exist_ok=True)
    if _DB.exists():
        _DB.unlink()
    con = sqlite3.connect(_DB)
    con.execute("pragma journal_mode=off")
    con.execute("pragma synchronous=off")
    con.executescript("""
        create table theology_works (work_id integer primary key, title text, author text,
            rights text, published text, n_paragraphs integer);
        create table theology_texts (id integer primary key, work_id integer, seq integer,
            text text, refs text);
        create virtual table theology_fts using fts5(text, content='theology_texts', content_rowid='id');
    """)
    work_ids, work_seq, next_wid, next_id = {}, {}, 1, 1
    fs = HfFileSystem()
    files = [f for f in HfApi().list_repo_files("jncraton/ccel-paragraphs", repo_type="dataset") if f.endswith(".parquet")]
    if args.shards:
        files = files[:args.shards]
    for i, rel in enumerate(files):
        with fs.open(f"datasets/jncraton/ccel-paragraphs/{rel}", "rb") as fh:
            pf = pq.ParquetFile(fh)
            for b in pf.iter_batches(columns=["title", "author", "rights", "published", "text", "refs"], batch_size=20000):
                cols = {c: b.column(c).to_pylist() for c in ("title", "author", "rights", "published", "text", "refs")}
                text_rows, work_rows = [], []
                for t, a, r, p, txt, refs in zip(cols["title"], cols["author"], cols["rights"], cols["published"], cols["text"], cols["refs"]):
                    if t not in keep_titles:
                        continue
                    wid = work_ids.get(t)
                    if wid is None:
                        wid = work_ids[t] = next_wid
                        work_seq[wid] = 0
                        next_wid += 1
                        work_rows.append((wid, t, a, r, p, 0))
                    text_rows.append((next_id, wid, work_seq[wid], txt or "", json.dumps(refs) if refs else None))
                    work_seq[wid] += 1
                    next_id += 1
                if work_rows:
                    con.executemany("insert into theology_works values (?,?,?,?,?,?)", work_rows)
                if text_rows:
                    con.executemany("insert into theology_texts (id, work_id, seq, text, refs) values (?,?,?,?,?)", text_rows)
        print(f"  shard {i+1}/{len(files)}; paragraphs so far {next_id-1:,}; works {next_wid-1}", flush=True)
    con.execute("update theology_works set n_paragraphs = (select count(*) from theology_texts where work_id=theology_works.work_id)")
    print("  building FTS5 index…", flush=True)
    con.execute("insert into theology_fts(rowid, text) select id, text from theology_texts")
    con.commit()
    n_w = con.execute("select count(*) from theology_works").fetchone()[0]
    n_p = con.execute("select count(*) from theology_texts").fetchone()[0]
    con.close()
    mb = _DB.stat().st_size / 1e6
    print(f"\nloaded {n_w} works / {n_p:,} paragraphs into {_DB.name} ({mb:.0f} MB, +FTS5). model2vec vectors: next step.")


if __name__ == "__main__":
    main()
