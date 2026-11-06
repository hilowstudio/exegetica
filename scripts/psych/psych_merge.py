"""Merge the lexicon buckets (psych_cleanup.classify) with the 10 agent decision files for the
AMBIG residue into the final cleaned psychology list.

Final label:
  lexicon KEEP  -> keep   (strong/medium psych term)
  lexicon DROP  -> drop   (clear non-psychology category, no psych term)
  lexicon AMBIG -> the agent's keep/drop judgment (missing idx defaults to keep — recall-safe)

Emits:
  psych_cleaned_keep.csv   kept rows, original columns + keep_reason
  psych_dropped.csv        dropped rows, original columns + drop_reason
"""
from __future__ import annotations
import csv, glob, os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psych_cleanup import load, classify

HERE = os.path.dirname(os.path.abspath(__file__))   # the lists live beside these scripts
ROOT = os.path.dirname(os.path.dirname(HERE))
DECISIONS_GLOB = os.path.join(ROOT, ".seed_cache", "psych_slices", "decisions_*.csv")


def main():
    rows = load()
    for r in rows:
        r["_bucket"], r["_reason"] = classify(r["Title"])

    # agent decisions for AMBIG rows, keyed by original idx
    agent = {}
    files = sorted(glob.glob(DECISIONS_GLOB))
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            for d in csv.DictReader(f):
                try:
                    agent[int(d["idx"])] = (d["decision"].strip().lower(), (d.get("reason") or "").strip())
                except (ValueError, KeyError):
                    pass
    print(f"decision files: {len(files)} | agent decisions: {len(agent)}")

    ambig_total = sum(1 for r in rows if r["_bucket"] == "AMBIG")
    ambig_missing = [i for i, r in enumerate(rows) if r["_bucket"] == "AMBIG" and i not in agent]
    print(f"AMBIG rows: {ambig_total} | missing agent decision: {len(ambig_missing)} (default to keep)")
    if ambig_missing[:5]:
        print("  first missing idx:", ambig_missing[:10])

    keep, drop = [], []
    for i, r in enumerate(rows):
        if r["_bucket"] == "KEEP":
            r["keep_reason"] = r["_reason"]; keep.append(r)
        elif r["_bucket"] == "DROP":
            r["drop_reason"] = r["_reason"]; drop.append(r)
        else:
            dec, why = agent.get(i, ("keep", "no-decision"))
            if dec == "drop":
                r["drop_reason"] = f"ambig:{why}"; drop.append(r)
            else:
                r["keep_reason"] = f"ambig:{why}"; keep.append(r)

    cols = ["cosine", "tier", "Title", "Author", "Reg. No.", "Status"]
    with open(os.path.join(HERE, "psych_cleaned_keep.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["keep_reason"], extrasaction="ignore")
        w.writeheader(); w.writerows(keep)
    with open(os.path.join(HERE, "psych_dropped.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["drop_reason"], extrasaction="ignore")
        w.writeheader(); w.writerows(drop)

    from collections import Counter
    print(f"\nKEEP {len(keep)}  |  DROP {len(drop)}  |  total {len(rows)}")
    print("keep by tier:", dict(Counter(r["tier"] for r in keep)))
    print("keep sources:", dict(Counter((r.get("keep_reason") or "").split(":")[0] for r in keep)))
    print("wrote psych_cleaned_keep.csv, psych_dropped.csv")


if __name__ == "__main__":
    main()
