#!/usr/bin/env python3
"""
Download sermonindex/early-church-fathers (HuggingFace dataset, CC BY 4.0) into .seed_cache/.

68,240 verse-keyed patristic quotations (book/chapter/verse + father + source_work + url).
Only quotation.jsonl is needed (father.jsonl/verse.jsonl carry no dates we lack). CC BY 4.0
→ attribute SermonIndex; import_sermonindex_fathers.py then adds only the ~1.7k rows that are
genuinely new against the existing HistoricalChristianFaith catena.

    .venv\\Scripts\\python.exe scripts\\download_sermonindex.py

Then run import_sermonindex_fathers.py.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from huggingface_hub import hf_hub_download

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_DEST = _ROOT / ".seed_cache" / "sermonindex_quotation.jsonl"


def main() -> None:
    _DEST.parent.mkdir(parents=True, exist_ok=True)
    print("downloading sermonindex/early-church-fathers → quotation.jsonl …")
    cached = hf_hub_download("sermonindex/early-church-fathers", "quotation.jsonl", repo_type="dataset")
    shutil.copy(cached, _DEST)
    n = sum(1 for _ in _DEST.open(encoding="utf-8"))
    print(f"done — {n:,} quotations at {_DEST}. Now run import_sermonindex_fathers.py.")


if __name__ == "__main__":
    main()
