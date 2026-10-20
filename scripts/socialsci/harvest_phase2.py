"""Phase 2 harvest (Government and Street Law): download once into .seed_cache/socialsci/, politely.

  cap/us/<n>.zip        Harvard Caselaw Access Project, U.S. Reports vols 1-572 (every Supreme Court
                        opinion through about 2018). Released "without restriction on access or use."
  scdb/                 Supreme Court Database: case-centered CSVs (modern 1946- and legacy 1791-1945).
  legislators/          @unitedstates/congress-legislators (CC0): every member of Congress, presidents, VPs.
  ilcs/                 Illinois Compiled Statutes (public domain by statute), the chapters Street Law uses.

Resumable: a file already on disk is never fetched again.

    .venv/Scripts/python.exe scripts/socialsci/harvest_phase2.py [cap|scdb|legislators|ilcs ...]
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / ".seed_cache" / "socialsci"
UA = "YorkvilleChristianSchool-HistoryResearch/1.0 (one-time archival harvest for classroom use)"


def get(url: str, dest: Path, delay: float = 0.5) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.write_bytes(r.read())
                tmp.rename(dest)
            time.sleep(delay)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  404 {url}")
                return False
            time.sleep(5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            print(f"  retry {url}: {e}")
            time.sleep(5 * (attempt + 1))
    print(f"  FAILED {url}")
    return False


def cap() -> None:
    ok = 0
    for n in range(1, 573):
        ok += get(f"https://static.case.law/us/{n}.zip", SEED / "cap" / "us" / f"{n}.zip")
        if n % 50 == 0:
            print(f"  cap: {n}/572", flush=True)
    get("https://static.case.law/us/CasesMetadata.json", SEED / "cap" / "us" / "CasesMetadata.json")
    print(f"cap: {ok}/572 volumes")


def scdb() -> None:
    base = "https://scdb.la.psu.edu/_brickyard/data/2026_01/"
    for name in ("SCDB_2026_01_caseCentered_Citation.csv.zip", "SCDB_Legacy_08_caseCentered_Citation.csv.zip"):
        print("scdb:", name, get(base + name, SEED / "scdb" / name))


def legislators() -> None:
    base = "https://unitedstates.github.io/congress-legislators/"
    for name in ("legislators-current.json", "legislators-historical.json", "executive.json", "committees-current.json"):
        print("legislators:", name, get(base + name, SEED / "legislators" / name))


ILCS_CHAPTERS = (10, 625, 705, 720, 725, 730, 735, 740, 750, 755, 765, 775, 815, 820)
ILCS_BASE = "https://www.ilga.gov/ftp/ILCS/"


def _listing(url: str) -> list[str]:
    import re
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE  # ilga.gov's FTP host serves a mismatched certificate
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; " + UA + ")"})
    for attempt in range(4):  # the server sometimes drops a connection mid-response
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                html = r.read().decode("latin-1")
            break
        except Exception:  # noqa: BLE001
            if attempt == 3:
                print(f"  listing FAILED {url}")
                return []
            time.sleep(5 * (attempt + 1))
    time.sleep(0.3)
    return [h for h in re.findall(r'HREF="([^"]+)"', html, re.I) if not h.rstrip("/").endswith("/ftp/ILCS") and h != "/ftp/"]


def _get_insecure(url: str, dest: Path) -> None:
    import ssl
    if dest.exists():
        return
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; " + UA + ")"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.read())
            time.sleep(0.3)
            return
        except Exception as e:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
    print(f"  FAILED {url}")


def ilcs() -> None:
    """Street Law and Government chapters of the Illinois Compiled Statutes (public domain by statute,
    25 ILCS 135/5.04), one HTML file per section, plus the official section-order file."""
    from urllib.parse import unquote
    out = SEED / "ilcs"
    _get_insecure(ILCS_BASE + "aReadMe/Section%20Sequence.txt", out / "Section Sequence.txt")
    n = 0
    for ch in ILCS_CHAPTERS:
        for act in _listing(f"{ILCS_BASE}Ch%20{ch:04d}/"):
            if not act.endswith("/"):
                continue
            for f in _listing("https://www.ilga.gov" + act):
                if f.endswith("/"):
                    continue
                dest = out / unquote(f.split("/ftp/ILCS/", 1)[1])
                _get_insecure("https://www.ilga.gov" + f, dest)
                n += 1
                if n % 500 == 0:
                    print(f"  ilcs: {n:,} files (chapter {ch})", flush=True)
    print(f"ilcs: {n:,} files")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = sys.argv[1:] or ["cap", "scdb", "legislators"]
    for j in jobs:
        globals()[j]()
