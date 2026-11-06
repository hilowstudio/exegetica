"""Ingest real K-12 academic standards from the Common Standards Project API
into a local, owned corpus (the non-Bible analog to the confessions/lexicon data).

Each standard carries a verified code (statementNotation), an authoritative grade
(from its standard set), the full statement text, and hierarchy. We "own the data":
download once into standards/raw/, no runtime API dependency thereafter.

Usage:  python scripts/download_standards.py        (resumable; skips cached sets)
Requires ACADEMIC_STANDARDS_API_KEY in .env (Common Standards Project free key).
"""
import json, os, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "standards"
RAW = OUT / "raw"
BASE = "https://api.commonstandardsproject.com/api/v1"

# quill subject -> [(jurisdiction_id, standards-body label), ...]
JURISDICTIONS = {
    "MAT": [("67810E9EF6944F9383DCC602A3484C23", "Common Core State Standards")],   # Math sets filtered below
    "ELA": [("67810E9EF6944F9383DCC602A3484C23", "Common Core State Standards")],   # ELA sets filtered below
    "SCI": [("71E5AA409D894EB0B43A8CD82F727BFE", "Next Generation Science Standards")],
    "HSS": [("63B92F2164654D019589410B6CA225EA", "National Council for the Social Studies")],
    "GEO": [("B93E61C2A9784FB5B8E7D086E78913B9", "National Council for Geographic Education"),
            ("6636E00751DC45F09DB863381C757EA1", "National Geography Education Standards")],
    "CPT": [("C2D26B5D03E74C7B9AFFE6F592601728", "Computer Science Teachers Association")],
    "ART": [("4F7824964E604BBB8210E4E1EF10A2EF", "National Core Arts Standards")],
    "DST": [("EC07EA64CD834C2B97F2A54AB80DB89B", "International Technology and Engineering Educators Association")],
    "LIF": [("E2FE94A450A646FF935C27B0EC868E48", "National Assoc of State Administrators of Family and Consumer Sciences"),
            ("0918E6D0F9114840BF95A0493A245DD8", "Common Career Technical Core (CCTC)"),
            ("22534454CF994FF1B3A67EB930C782A5", "Jump$tart Coalition for Personal Financial Literacy")],
    "PER": [("C5FF5D77B40D4C15B04C95B872723EFB", "Collaborative for Academic, Social, and Emotional Learning"),
            ("A66ADAD3FB044D2F9B81C67CE1C6E7C3", "National Health Education Standards")],
    "CFL": [("2FEC7EA742444416BC3E0E955468251D", "ACTFL")],
    # The AFNR Career Cluster Content Standards, 2024 edition only (filtered below). Added 2026-11-05
    # for the Agriculture subject, which FFA makes central at the school.
    "AGR": [("2F48212D5B0F4352805BD0D1A9911263", "National Council for Agricultural Education")],
}


def load_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ACADEMIC_STANDARDS_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("ACADEMIC_STANDARDS_API_KEY not found in .env")


KEY = load_key()


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Api-Key": KEY, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1)); continue
            raise
    return None


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    seen_jur = {}
    total_sets = total_std = 0
    for subject, jlist in JURISDICTIONS.items():
        for jid, label in jlist:
            if jid not in seen_jur:
                jd = get(f"/jurisdictions/{jid}")
                seen_jur[jid] = (jd.get("data", jd) or {}).get("standardSets", [])
                time.sleep(0.15)
            sets = seen_jur[jid]
            for s in sets:
                sid = s.get("id")
                subj = (s.get("subject") or "")
                # For Common Core, split Math vs ELA by which quill subject we're filling
                if jid == "67810E9EF6944F9383DCC602A3484C23":
                    if subject == "MAT" and "math" not in subj.lower():
                        continue
                    if subject == "ELA" and "english" not in subj.lower() and "literacy" not in subj.lower():
                        continue
                if jid == "2F48212D5B0F4352805BD0D1A9911263" and "(2024-)" not in subj:
                    continue
                jdir = RAW / jid
                jdir.mkdir(exist_ok=True)
                fp = jdir / f"{sid}.json"
                if fp.exists():
                    setobj = json.loads(fp.read_text(encoding="utf-8"))
                else:
                    sd = get(f"/standard_sets/{sid}")
                    setobj = sd.get("data", sd)
                    fp.write_text(json.dumps(setobj, ensure_ascii=False), encoding="utf-8")
                    time.sleep(0.15)
                stds = setobj.get("standards") or {}
                n = len(stds) if isinstance(stds, (dict, list)) else 0
                total_sets += 1; total_std += n
                manifest.setdefault(subject, []).append({
                    "jurisdiction": label, "jurisdictionId": jid, "setId": sid,
                    "subject": subj, "title": s.get("title"), "standards": n,
                })
                print(f"  {subject} | {label[:34]:34} | {s.get('title','')[:40]:40} | {n} standards")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDONE. standard sets: {total_sets} | standards: {total_std}")
    print(f"Corpus at {RAW}  ·  manifest at {OUT/'manifest.json'}")
    for subj in JURISDICTIONS:
        rows = manifest.get(subj, [])
        print(f"  {subj}: {len(rows)} sets, {sum(r['standards'] for r in rows)} standards")


if __name__ == "__main__":
    main()
