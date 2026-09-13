"""Add the model2vec + sqlite-vec semantic layer to theology.db (fuzzy-recall complement to FTS).

Chunks the corpus into ~1.5k-char passages (within work boundaries), embeds each with
minishlab/potion-retrieval-32M (the CPU-static model already in the stack), L2-normalizes and
int8-quantizes, and stores them in a sqlite-vec `vec0` virtual table right inside theology.db:
  theology_passages(id, work_id, text)  — passage text to return + cite
  theology_vec  (vec0, int8[DIM])       — the vectors; KNN-queried from the mmap'd DB (low RAM)
  theology_vecmeta(model, dim, count)   — so the MCP knows which model to embed queries with
Query time (in the MCP) L2-normalizes the query embedding and runs one vec0 KNN — no big array
held in Python RAM, which matters on the 1 GB Fly machine.

    .venv\\Scripts\\python.exe scripts\\build_theology_vectors.py
"""
from __future__ import annotations

import pathlib
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import numpy as np  # noqa: E402
import sqlite_vec  # noqa: E402

_DB = _ROOT / "db" / "theology.db"
_MODEL = "minishlab/potion-retrieval-32M"
_CHUNK_CHARS = 1500


def passages(con):
    """(work_id, text): consecutive paragraphs of a work packed to ~_CHUNK_CHARS."""
    cur = con.execute("select work_id, seq, text from theology_texts order by work_id, seq")
    cur_work, buf, blen = None, [], 0
    for work_id, _seq, text in cur:
        if work_id != cur_work and buf:
            yield cur_work, "\n".join(buf)
            buf, blen = [], 0
        cur_work = work_id
        t = (text or "").strip()
        if not t:
            continue
        buf.append(t)
        blen += len(t)
        if blen >= _CHUNK_CHARS:
            yield cur_work, "\n".join(buf)
            buf, blen = [], 0
    if buf:
        yield cur_work, "\n".join(buf)


def int8_quantize(vecs: np.ndarray) -> np.ndarray:
    """L2-normalize then int8-quantize (unit vectors → scale 1/127; cosine == dot / 127)."""
    v = vecs.astype(np.float32)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n == 0] = 1.0
    v /= n
    return np.clip(np.round(v * 127.0), -127, 127).astype(np.int8)


def main() -> None:
    if not _DB.exists():
        sys.exit("db/theology.db not found — run build_theology_grounding.py first.")
    from model2vec import StaticModel

    con = sqlite3.connect(_DB)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    # keep default journaling — this mutates the R2-restorable theology.db in place, and an
    # interrupted write must not corrupt it (unlike the earlier journal_mode=off attempt).
    con.executescript("""
        drop table if exists theology_passages;
        drop table if exists theology_vec;
        drop table if exists theology_vecmeta;
        create table theology_passages (id integer primary key, work_id integer, text text);
    """)

    print("collecting passages…", flush=True)
    rows = list(passages(con))
    con.executemany("insert into theology_passages (id, work_id, text) values (?,?,?)",
                    [(i + 1, w, t) for i, (w, t) in enumerate(rows)])
    print(f"  {len(rows):,} passages; loading {_MODEL} …", flush=True)

    model = StaticModel.from_pretrained(_MODEL)
    embs = int8_quantize(model.encode([t for _, t in rows], show_progress_bar=True))
    dim = embs.shape[1]
    print(f"  embedded → int8[{dim}]; writing vec0 …", flush=True)

    con.execute(f"create virtual table theology_vec using vec0(id integer primary key, emb int8[{dim}])")
    con.executemany("insert into theology_vec(id, emb) values (?, vec_int8(?))",
                    [(i + 1, embs[i].tobytes()) for i in range(embs.shape[0])])
    con.execute("create table theology_vecmeta (id integer primary key, model text, dim integer, count integer)")
    con.execute("insert into theology_vecmeta values (1,?,?,?)", (_MODEL, dim, embs.shape[0]))
    con.commit()
    mb = _DB.stat().st_size / 1e6
    con.close()
    print(f"\nstored {embs.shape[0]:,} × {dim} int8 vectors in theology.db (now {mb:.0f} MB). "
          f"Re-publish: scripts/publish_db.py theology")


if __name__ == "__main__":
    main()
