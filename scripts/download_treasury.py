#!/usr/bin/env python3
"""
Clone Spurgeon's *Treasury of David* (lyteword/chspurgeon-tod, CC0) into .seed_cache/.

The repo is 7 volumes of per-Psalm Markdown (volume-N/psalm-M.md), a verse-by-verse
exposition of all 150 Psalms. CC0 (public-domain dedication) — freely usable, and the
underlying work is US-clear (Spurgeon d. 1892), so full_text may be stored/served.

    .venv\\Scripts\\python.exe scripts\\download_treasury.py            # shallow clone / refresh

Then run import_treasury.py to load it into `commentaries` (source spurgeon-treasury).
This is a post-`build_database.py --rebuild` importer (re-run after any rebuild).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

_REPO = "https://github.com/lyteword/chspurgeon-tod"
_DEST = _ROOT / ".seed_cache" / "chspurgeon-tod"


def main() -> None:
    _DEST.parent.mkdir(parents=True, exist_ok=True)
    if (_DEST / ".git").exists():
        print(f"refreshing {_DEST} …")
        subprocess.run(["git", "-C", str(_DEST), "pull", "--ff-only"], check=True)
    else:
        print(f"cloning {_REPO} → {_DEST} …")
        subprocess.run(["git", "clone", "--depth", "1", _REPO, str(_DEST)], check=True)

    psalms = sorted(_DEST.glob("volume-*/psalm-*.md"))
    print(f"done — {len(psalms)} psalm files present. Now run import_treasury.py.")


if __name__ == "__main__":
    main()
