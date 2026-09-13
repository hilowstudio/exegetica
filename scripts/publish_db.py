"""Publish a local SQLite DB to R2 (+ a content-hash version marker) so the Fly app boot-fetches
it onto its volume. Shows upload progress. Run on a dev machine.

    .venv\\Scripts\\python.exe scripts\\publish_db.py theology
    .venv\\Scripts\\python.exe scripts\\publish_db.py study-bible
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import threading

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import asyncio  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env", override=True)

from webapp import r2  # noqa: E402

# name -> (local path, R2 key). Keys match _R2_DBS in webapp/app.py.
DBS = {
    "theology": ("db/theology.db", "theology/theology.db"),
    "study-bible": ("db/study_bible.db", "study-bible/study_bible.db"),
}


def _hash(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


class _Progress:
    def __init__(self, total: int):
        self.total, self.seen, self.lock = total, 0, threading.Lock()

    def __call__(self, n: int):
        with self.lock:
            self.seen += n
            pct = 100 * self.seen / self.total if self.total else 0
            sys.stdout.write(f"\r  uploading… {self.seen/1e6:7.0f} / {self.total/1e6:.0f} MB ({pct:5.1f}%)")
            sys.stdout.flush()


async def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in DBS:
        sys.exit(f"usage: publish_db.py [{'|'.join(DBS)}]")
    rel, key = DBS[sys.argv[1]]
    path = _ROOT / rel
    if not path.exists():
        sys.exit(f"{rel} not found — build it first.")
    if not r2.configured():
        sys.exit("R2 is not configured (R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / bucket).")
    size = path.stat().st_size
    print(f"hashing {rel} ({size/1e6:.0f} MB)…", flush=True)
    version = _hash(path)
    print(f"version {version}; uploading to r2://{r2._bucket()}/{key}", flush=True)
    await r2.upload_file_async(key, str(path), content_type="application/x-sqlite3", callback=_Progress(size))
    await r2.put_bytes_async(key + ".version", version.encode(), "text/plain")
    print(f"\ndone. version={version}.")


if __name__ == "__main__":
    asyncio.run(main())
