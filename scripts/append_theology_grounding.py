#!/usr/bin/env python3
"""
Incrementally sync theology.db to the current curation in build_theology_grounding.py —
append works that the curation now keeps but the DB doesn't yet have, WITHOUT re-streaming the
whole 8.8 GB CCEL corpus or rebuilding the 2.4 GB DB from scratch.

Use after widening the curation (e.g. un-denying Wesley, allow-listing Chesterton's PD works):
    .venv\\Scripts\\python.exe scripts\\append_theology_grounding.py --dry-run   # what would append
    .venv\\Scripts\\python.exe scripts\\append_theology_grounding.py             # append (FTS synced)
    .venv\\Scripts\\python.exe scripts\\build_theology_vectors.py                # THEN rebuild vectors
    .venv\\Scripts\\python.exe scripts\\publish_db.py theology                   # THEN republish to R2

Reads CCEL paragraph rows from the locally-cached HF snapshot (jncraton/ccel-paragraphs).
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from build_theology_grounding import curated_from_inventory, _DB  # noqa: E402


def _parquet_files() -> list[str]:
    from huggingface_hub import snapshot_download
    p = snapshot_download("jncraton/ccel-paragraphs", repo_type="dataset", allow_patterns=["*.parquet"])
    return sorted(glob.glob(p + "/**/*.parquet", recursive=True))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not _DB.exists():
        sys.exit("db/theology.db not found — run build_theology_grounding.py for a full build first.")

    target = curated_from_inventory()  # title -> {author, rights, published, ...}
    con = sqlite3.connect(_DB)
    existing = {t for (t,) in con.execute("select title from theology_works")}
    new = sorted(set(target) - existing)
    print(f"curation keeps {len(target)} titles; db has {len(existing)}; {len(new)} to append")
    for t in new:
        print(f"    + [{(target[t].get('author') or '?')}] {t[:60]}")
    if args.dry_run or not new:
        print("(dry run)" if args.dry_run else "nothing to append.")
        con.close()
        return

    import duckdb
    files = _parquet_files()
    d = duckdb.connect()
    d.execute("SET threads TO 1")  # keep per-file scan order ~= document order

    next_wid = con.execute("select coalesce(max(work_id), 0) from theology_works").fetchone()[0] + 1
    next_id = con.execute("select coalesce(max(id), 0) from theology_texts").fetchone()[0] + 1
    appended_p = 0
    for title in new:
        rows = d.execute(
            "select author, rights, published, text, refs from read_parquet(?) where title = ?",
            [files, title],
        ).fetchall()
        if not rows:
            print(f"  [warn] not found in parquet, skipped: {title}")
            continue
        author, rights, published = rows[0][0], rows[0][1], rows[0][2]
        con.execute("insert into theology_works values (?,?,?,?,?,?)",
                    (next_wid, title, author, rights, published, len(rows)))
        batch = []
        for seq, (_a, _r, _p, text, refs) in enumerate(rows):
            batch.append((next_id, next_wid, seq, text or "",
                          json.dumps(list(refs)) if refs else None))
            next_id += 1
        con.executemany(
            "insert into theology_texts (id, work_id, seq, text, refs) values (?,?,?,?,?)", batch)
        con.execute(
            "insert into theology_fts(rowid, text) select id, text from theology_texts where work_id = ?",
            (next_wid,))
        appended_p += len(rows)
        print(f"  + {title[:52]:52} {len(rows):>6}p  [{author}]")
        next_wid += 1

    con.commit()
    nw = con.execute("select count(*) from theology_works").fetchone()[0]
    npar = con.execute("select count(*) from theology_texts").fetchone()[0]
    con.close()
    print(f"\n[ok] appended {appended_p:,} paragraphs; theology.db now {nw} works / {npar:,} paragraphs.")
    print("Next: build_theology_vectors.py (rebuild semantic layer), then publish_db.py theology.")


if __name__ == "__main__":
    main()
