"""Upload the locally-built theology.db to R2 so the Fly app can fetch it to its volume.

Writes two objects: the DB (theology/theology.db) and a tiny version marker
(theology/theology.db.version = a content hash). The app's boot-fetch compares that marker
to the copy on its volume and only re-downloads when it changed. Run on a dev machine (has
the RAM/bandwidth); the app never uploads.

    .venv\\Scripts\\python.exe scripts\\upload_theology_db.py
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

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

_DB = _ROOT / "db" / "theology.db"
_KEY = "theology/theology.db"
_VER_KEY = _KEY + ".version"


def _hash(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


async def main() -> None:
    if not _DB.exists():
        sys.exit("db/theology.db not found — run scripts/build_theology_grounding.py first.")
    if not r2.configured():
        sys.exit("R2 is not configured (need R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / bucket).")
    mb = _DB.stat().st_size / 1e6
    print(f"hashing theology.db ({mb:.0f} MB)…", flush=True)
    version = _hash(_DB)
    print(f"version {version}; uploading to r2://{r2._bucket()}/{_KEY} …", flush=True)
    await r2.upload_file_async(_KEY, str(_DB), content_type="application/x-sqlite3")
    await r2.put_bytes_async(_VER_KEY, version.encode(), "text/plain")
    print(f"done. version={version}. Set THEOLOGY_DB=/data/theology.db on Fly; the app boot-fetches it.")


if __name__ == "__main__":
    asyncio.run(main())
