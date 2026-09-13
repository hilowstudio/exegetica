"""Enumerate ccel-paragraphs works (title -> author, paragraph count, rights, published, chars)
by reading only the small columns from the HF parquet shards (never the 384-d embedding).
Writes .seed_cache/ccel_titles.json for the Phase B curation/forecast."""
import json, pathlib, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pyarrow.parquet as pq
import pyarrow.compute as pc
from huggingface_hub import HfApi, HfFileSystem

ROOT = pathlib.Path(r"C:\Users\adam\study-bible")
fs = HfFileSystem()
files = [f for f in HfApi().list_repo_files("jncraton/ccel-paragraphs", repo_type="dataset") if f.endswith(".parquet")]
agg = {}  # title -> dict
COLS = ["title", "author", "rights", "published", "text"]
for i, rel in enumerate(files):
    path = f"datasets/jncraton/ccel-paragraphs/{rel}"
    with fs.open(path, "rb") as fh:
        pf = pq.ParquetFile(fh)
        for batch in pf.iter_batches(columns=COLS, batch_size=20000):
            titles = batch.column("title").to_pylist()
            authors = batch.column("author").to_pylist()
            rights = batch.column("rights").to_pylist()
            pubs = batch.column("published").to_pylist()
            lens = pc.utf8_length(batch.column("text")).to_pylist()
            for t, a, r, p, L in zip(titles, authors, rights, pubs, lens):
                d = agg.get(t)
                if d is None:
                    d = agg[t] = {"author": a, "n": 0, "chars": 0, "rights": r, "published": p}
                d["n"] += 1
                d["chars"] += (L or 0)
    print(f"shard {i+1}/{len(files)} done; titles so far: {len(agg)}", flush=True)
out = ROOT / ".seed_cache" / "ccel_titles.json"
out.write_text(json.dumps(agg, ensure_ascii=False), encoding="utf-8")
print(f"WROTE {out} — {len(agg)} distinct titles", flush=True)
