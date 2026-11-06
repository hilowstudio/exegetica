"""Normalize the owned Common Standards Project corpus (standards/raw/) into a
compact, queryable index the remediation matcher can use.

Output: standards/standards-index.json  — {subject: [ {code, grades[], statement,
jurisdiction, set, depth, asnId} ... ]} — every standard with its VERIFIED code and
AUTHORITATIVE grade span. This is what quill objectives get matched/re-graded against.
"""
import json, re
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "standards" / "raw"
OUT = ROOT / "standards"

# subject <- jurisdictionId  (reverse of the download map; a few subjects share CCSS)
JUR2SUBJ = {
    "71E5AA409D894EB0B43A8CD82F727BFE": "SCI",
    "63B92F2164654D019589410B6CA225EA": "HSS",
    "B93E61C2A9784FB5B8E7D086E78913B9": "GEO",
    "6636E00751DC45F09DB863381C757EA1": "GEO",
    "C2D26B5D03E74C7B9AFFE6F592601728": "CPT",
    "4F7824964E604BBB8210E4E1EF10A2EF": "ART",
    "EC07EA64CD834C2B97F2A54AB80DB89B": "DST",
    "E2FE94A450A646FF935C27B0EC868E48": "LIF",
    "0918E6D0F9114840BF95A0493A245DD8": "LIF",
    "22534454CF994FF1B3A67EB930C782A5": "LIF",
    "C5FF5D77B40D4C15B04C95B872723EFB": "PER",
    "A66ADAD3FB044D2F9B81C67CE1C6E7C3": "PER",
    "2FEC7EA742444416BC3E0E955468251D": "CFL",
    "2F48212D5B0F4352805BD0D1A9911263": "AGR",   # AFNR, 2024 edition (download_standards.py)
}
CCSS = "67810E9EF6944F9383DCC602A3484C23"


def grade_int(tok):
    tok = str(tok).strip()
    if tok in ("K", "Pre-K", "PK", "Kindergarten"):
        return 0
    m = re.match(r"0?(\d{1,2})$", tok)
    return int(m.group(1)) if m else None


def grades_from_set(setobj):
    lv = setobj.get("educationLevels") or []
    out = sorted({g for g in (grade_int(t) for t in lv) if g is not None and 0 <= g <= 12})
    if out:
        return out
    # fall back to parsing the title
    t = (setobj.get("title") or "")
    if re.search(r"high school|grades?\s*9", t, re.I):
        return [9, 10, 11, 12]
    nums = [int(n) for n in re.findall(r"\b(1[0-2]|\d)\b", t)]
    nums = [n for n in nums if 0 <= n <= 12]
    if re.search(r"\bgrade\s*k\b|kindergarten|pre-?k", t, re.I):
        nums.append(0)
    return sorted(set(nums))


def main():
    index = defaultdict(list)
    per_subj_grades = defaultdict(Counter)
    total = 0
    for jdir in sorted(RAW.iterdir()):
        if not jdir.is_dir():
            continue
        jid = jdir.name
        for fp in jdir.glob("*.json"):
            setobj = json.loads(fp.read_text(encoding="utf-8"))
            subj = (setobj.get("subject") or "")
            if jid == CCSS:
                quill = "MAT" if "math" in subj.lower() else "ELA"
            else:
                quill = JUR2SUBJ.get(jid)
            if not quill:
                continue
            grades = grades_from_set(setobj)
            jname = (setobj.get("jurisdiction") or {}).get("title") or jid
            stds = setobj.get("standards") or {}
            items = stds.values() if isinstance(stds, dict) else stds
            for st in items:
                desc = (st.get("description") or "").strip()
                if not desc:
                    continue
                rec = {
                    "code": st.get("statementNotation") or st.get("asnIdentifier"),
                    "grades": grades,
                    "statement": desc,
                    "jurisdiction": jname,
                    "set": setobj.get("title"),
                    "depth": st.get("depth"),
                    "asnId": st.get("asnIdentifier"),
                }
                index[quill].append(rec)
                total += 1
                for g in grades:
                    per_subj_grades[quill][g] += 1
    (OUT / "standards-index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote standards-index.json — {total} standards across {len(index)} subjects\n")
    print(f"{'SUBJ':4} {'stds':6}  grade coverage (K..12; . = none)")
    for s in sorted(index):
        cov = "".join(("#" if per_subj_grades[s].get(g) else ".") for g in range(13))
        leaf = sum(1 for r in index[s] if r.get("depth", 0) and r["depth"] >= 1)
        print(f"{s:4} {len(index[s]):6}  K{cov[0]} 1{cov[1]} 2{cov[2]} 3{cov[3]} 4{cov[4]} 5{cov[5]} 6{cov[6]} 7{cov[7]} 8{cov[8]} 9{cov[9]} 10{cov[10]} 11{cov[11]} 12{cov[12]}")


if __name__ == "__main__":
    main()
