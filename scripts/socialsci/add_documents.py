"""Add supplementary documents to db/social_sciences.db in place, without a full rebuild.

Reads the builder's supplements() and inserts any document whose title isn't already in the database:
the documents row, its passages, the full-text index rows, and one meaning vector per passage. The next
full build includes them anyway (they live in build_social_sciences_db.SUPPLEMENTS).

    .venv/Scripts/python.exe scripts/socialsci/add_documents.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import build_social_sciences_db as B  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    import numpy as np
    import sqlite_vec
    from model2vec import StaticModel
    con = sqlite3.connect(B.DB)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    have = {t for (t,) in con.execute("select title from documents")}
    model = StaticModel.from_pretrained(B.MODEL)
    added = 0
    for meta, text in B.supplements():
        if meta["title"] in have:
            continue
        cur = con.execute("insert into documents (source, collection, title, author, date, year, url, citation, rights, text, words) "
                          "values (?,?,?,?,?,?,?,?,?,?,?)",
                          (meta["source"], meta["collection"], meta["title"], meta["author"], meta["date"], meta["year"],
                           meta["url"], meta["citation"], meta["rights"], text, len(text.split())))
        doc_id = cur.lastrowid
        parts = list(B.chunks(text))
        ids = []
        for i, c in enumerate(parts):
            pid = con.execute("insert into passages (doc_id, seq, title, text) values (?,?,?,?)", (doc_id, i, meta["title"], c)).lastrowid
            con.execute("insert into passages_fts (rowid, title, text) values (?,?,?)", (pid, meta["title"], c))
            ids.append(pid)
        v = model.encode([meta["title"] + "\n" + c for c in parts]).astype(np.float32)
        v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        q = np.clip(np.round(v * 127.0), -127, 127).astype(np.int8)
        con.executemany("insert into passages_vec(id, emb) values (?, vec_int8(?))", [(pid, q[k].tobytes()) for k, pid in enumerate(ids)])
        print(f"  added {meta['title']} ({len(parts)} passages)")
        added += 1
    con.commit()
    con.close()
    print(f"{added} document(s) added")


if __name__ == "__main__":
    main()
