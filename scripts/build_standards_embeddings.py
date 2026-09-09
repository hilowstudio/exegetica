"""Precompute semantic embeddings for the standards spine.

Static, owned-data pipeline: embed every node in the standards search index
(subject, strand, topic, sub-topic, objective) once, at build time, with a
small local model, and store the L2-normalized matrix next to the standards
index. The web app loads that matrix and embeds only the live query at request
time, so search runs with no external service.

Run:  .venv/Scripts/python.exe scripts/build_standards_embeddings.py

Rebuild whenever the standards taxonomy changes (the app validates a signature
and silently falls back to fuzzy-only search if the matrix is stale).
"""

import hashlib
import json
from pathlib import Path

import click
import numpy as np
from model2vec import StaticModel

from webapp import generator

MODEL = "minishlab/potion-retrieval-32M"
OUT_DIR = Path(__file__).resolve().parent.parent / "webapp" / "standards"
NPY = OUT_DIR / "standards-embeddings.npy"
MANIFEST = OUT_DIR / "standards-embeddings.json"


def signature(records: list[dict]) -> str:
    """A hash of the ordered node ids, so the app can detect a stale matrix."""
    joined = "\n".join(json.dumps(r["ids"], sort_keys=True) for r in records)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


@click.command()
def main() -> None:
    records = generator._SEARCH
    texts = [r["label"] for r in records]
    click.echo(f"Embedding {len(texts)} standards nodes with {MODEL} …")

    model = StaticModel.from_pretrained(MODEL)
    emb = np.asarray(model.encode(texts, show_progress_bar=True), dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9

    np.save(NPY, emb)
    MANIFEST.write_text(json.dumps({
        "model": MODEL,
        "count": len(records),
        "dim": int(emb.shape[1]),
        "sig": signature(records),
    }, indent=2), encoding="utf-8")

    click.echo(f"Wrote {NPY.name} ({emb.shape[0]}×{emb.shape[1]}, "
               f"{NPY.stat().st_size/1e6:.1f} MB) and {MANIFEST.name}.")


if __name__ == "__main__":
    main()
