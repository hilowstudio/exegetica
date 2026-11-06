"""False-positive cleanup for the psychology-candidate list (psych_candidates_semantic_filtered.csv).

Separates genuine psychology titles from the abstract noise the upstream semantic contrast
couldn't remove (philosophy, economics, education-policy, devotional, fiction, etc.). Title-only
judgment, favouring recall of real psychology.

Pass 1 (this file): a lexicon buckets each row into
  KEEP   - a strong psychology term is present
  DROP   - no psychology term AND a strong non-psychology category term is present
  AMBIG  - neither (abstract titles needing per-title judgment)
Pass 2 (downstream): LLM judgment on the AMBIG residue.

    python scripts/psych/psych_cleanup.py --measure          # bucket counts + samples
    python scripts/psych/psych_cleanup.py --emit-ambig FILE   # write the AMBIG rows for judgment
    python scripts/psych/psych_cleanup.py --write             # write keep/drop/ambig CSVs
"""
from __future__ import annotations
import argparse, csv, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))   # the lists live beside these scripts
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(HERE, "psych_candidates_semantic_filtered.csv")

# --- STRONG psychology stems: presence => KEEP, overrides any exclusion term in the title ---
PSYCH_STRONG = [
    r"psycholog", r"psychoanaly", r"psychiatr", r"psychotherap", r"psychosomatic", r"psychopath",
    r"psychos[ei]s\b", r"psychoses", r"psychotic", r"neuros[ei]s\b", r"neuroses", r"neurotic",
    r"psychoneur", r"psychodynam", r"psychometr", r"parapsycholog", r"metapsycholog",
    r"subconscious", r"unconscious", r"mental hygiene", r"mental health", r"mental disorder",
    r"mental illness", r"mentally ill", r"mental disease", r"feeble.?minded", r"feeble.?mindedness",
    r"\binsanit", r"schizophren", r"paranoi", r"hysteria", r"neurasthen", r"\bmania\b", r"manic",
    r"inferiority complex", r"\blibido\b", r"superego", r"\bfreud", r"\bjung(ian)?\b", r"adlerian",
    r"repression\b", r"\bphobia", r"rorschach", r"introver", r"extrover", r"psychical research",
    r"hypnos", r"hypnot", r"mental test", r"intelligence test", r"mental measure", r"mental age",
    r"human behavior", r"human behaviour", r"behavior[ai]", r"behaviour[ai]", r"conditioned reflex",
    r"abnormal psych", r"clinical psych", r"social psych", r"child psych", r"the unconscious",
    r"mentally retard", r"mental retard", r"mental deficien", r"subnormal", r"mental defect",
    r"nervous breakdown", r"nervous disorder", r"stammer", r"stutter", r"amnesia", r"\bdementia",
]
# --- MEDIUM psychology stems: psychology-adjacent; KEEP unless a strong exclusion term is present ---
PSYCH_MED = [
    r"\bmental\b", r"\bmind\b", r"\bemotion", r"personalit", r"temperament", r"\binstinct",
    r"motivation", r"perception", r"\bsensation", r"cognit", r"\bmemory\b", r"consciousness",
    r"conscious", r"\bdream", r"the will\b", r"will power", r"self.?esteem", r"self.?consciousness",
    r"self.?analysis", r"self.?knowledge", r"\bnervous", r"reflexe?s", r"\banxiety", r"neuro",
    r"\battitude", r"adolescen", r"\bhabit", r"\bfatigue\b", r"\bfeeling", r"suggestibilit",
    r"\bbrain\b", r"human nature", r"human behavior", r"maladjust", r"adjustment", r"delinquen",
    r"\bcounsel", r"guidance", r"intelligen", r"gifted child", r"\bfear\b", r"\banger\b",
    r"\bwill\b", r"thinking", r"\bthought\b", r"\bgenius\b", r"\bmorale\b", r"character\b",
    r"\bbehavio", r"\btherap", r"aggressi", r"\bfrustrat", r"\bego\b", r"\bguilt\b",
    r"\bfantasy\b", r"\bphobi", r"compulsi", r"obsessi", r"\bstress\b", r"\bmoods?\b",
]

# --- Non-psychology category stems: with NO psych term => DROP ---
EXCL = {
    "commerce": [r"\bbusiness", r"\bmarket", r"salesman", r"\bsales\b", r"advertis", r"accounting",
                 r"bookkeep", r"\bfinanc", r"banking", r"investment", r"insurance", r"real estate",
                 r"\bmanagement\b", r"econom", r"\bcommerce", r"retail", r"merchandis", r"\bprofit",
                 r"\btax(es|ation)?\b", r"\bcredit\b", r"corporat", r"\btrade\b"],
    "sci_tech": [r"engineer", r"chemistr", r"\bphysics\b", r"geolog", r"mathematic", r"algebra",
                 r"geometr", r"calculus", r"electric", r"\bmechanic", r"\bradio\b", r"television",
                 r"aviation", r"aircraft", r"automobile", r"\bmachine", r"architectur", r"astronom",
                 r"\bchemical", r"\bphysical chemistry"],
    "bio_med": [r"\bsurger", r"anatom", r"\bnursing\b", r"obstetric", r"nutrition", r"\bdiet\b",
                r"\bcook", r"recipe", r"\bgarden", r"agricultur", r"\bfarm", r"botan", r"zoolog",
                r"veterinar", r"dentist", r"pharmac", r"\bcancer\b", r"tuberculos"],
    "humanities": [r"\bpoem", r"\bpoetr", r"\bverse\b", r"\bnovel\b", r"\bdrama\b", r"\bfiction",
                   r"grammar", r"spelling", r"\bvocabular", r"dictionar", r"shorthand", r"typewrit",
                   r"antholog", r"\bplays\b"],
    "religion": [r"\bsermon", r"\bgospel", r"\bbible", r"biblical", r"\bprayer", r"\bworship",
                 r"devotion", r"\bhymn", r"\bchrist\b", r"christian", r"\bjesus", r"\bchurch",
                 r"salvation", r"scriptur", r"theolog", r"catholic", r"protestant", r"methodist",
                 r"\bbaptist", r"\bgospel", r"\bcreed", r"\bsaint", r"\bpsalm"],
    "edu_admin": [r"curriculum", r"\btextbook", r"school administ", r"higher education",
                  r"\blesson", r"course of study", r"teachers? college", r"classroom",
                  r"\bkindergarten", r"physical education"],
    "law_pol": [r"\blaw\b", r"\blegal\b", r"\bgovernment", r"political", r"\bpolitics\b",
                r"democracy", r"communis", r"socialis", r"citizenship", r"diplomac", r"\btreaty",
                r"legislat", r"\bparliament", r"foreign policy"],
    "domestic": [r"etiquette", r"\bsewing", r"needlework", r"\bknitting", r"housekeep", r"laundr"],
    "geo_hist": [r"geograph", r"\btravelogue", r"\bguidebook"],
}
EXCL_FLAT = [(cat, re.compile("|".join(pats))) for cat, pats in EXCL.items()]
PSYCH_STRONG_RE = re.compile("|".join(PSYCH_STRONG))
PSYCH_MED_RE = re.compile("|".join(PSYCH_MED))


def classify(title: str):
    t = (title or "").lower()
    if PSYCH_STRONG_RE.search(t):
        return "KEEP", "psych-strong"
    excl = next((cat for cat, rx in EXCL_FLAT if rx.search(t)), None)
    if PSYCH_MED_RE.search(t):
        return ("AMBIG", f"psych-med vs {excl}") if excl else ("KEEP", "psych-med")
    if excl:
        return "DROP", excl
    return "AMBIG", ""


def load():
    return list(csv.DictReader(open(SRC, encoding="utf-8")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--emit-ambig")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rows = load()
    for r in rows:
        r["_bucket"], r["_reason"] = classify(r["Title"])
    from collections import Counter
    b = Counter(r["_bucket"] for r in rows)
    if a.measure:
        print("buckets:", dict(b))
        drop_by = Counter(r["_reason"] for r in rows if r["_bucket"] == "DROP")
        print("drop categories:", dict(drop_by))
        for bk in ("KEEP", "DROP", "AMBIG"):
            print(f"\n=== {bk} sample ===")
            for r in [x for x in rows if x["_bucket"] == bk][:14]:
                print(f"   {r['cosine']} {r['_reason']:11} {(r['Title'] or '')[:58]}")
    if a.emit_ambig:
        amb = [r for r in rows if r["_bucket"] == "AMBIG"]
        with open(a.emit_ambig, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["idx", "cosine", "tier", "Title", "Author", "Reg. No."])
            for i, r in enumerate(rows):
                if r["_bucket"] == "AMBIG":
                    w.writerow([i, r["cosine"], r["tier"], r["Title"], r["Author"], r["Reg. No."]])
        print(f"wrote {len(amb)} AMBIG rows to {a.emit_ambig}")


if __name__ == "__main__":
    main()
