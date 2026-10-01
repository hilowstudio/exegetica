"""Find a clean-text source for each kept psychology candidate (psych_cleaned_keep.csv).

Phase 1 (this file): match against the full Project Gutenberg catalog (.seed_cache/pg_catalog.csv),
the cleanest directly-ingestable source. Conservative match: author-surname agreement + high
prefix-aware title-token overlap (CCE titles are frequently truncated mid-title, so a candidate's
tokens should be a near-subset of the Gutenberg title's tokens).

Emits psych_sources.csv: the input columns + gutenberg_id, gutenberg_title, match_score, source.
Later phases fill `source` for the rest from archive.org etc.

    python scripts/psych_find_sources.py --gutenberg
"""
from __future__ import annotations
import argparse, csv, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

KEEP = "psych_cleaned_keep.csv"
PG = ".seed_cache/pg_catalog.csv"
OUT = "psych_sources.csv"

STOP = set("the a an of and or to in on for with by is are as at from be this that his her its "
           "their our your my we you they it into out about over under between within without "
           "through per no new ed edition vol volume some its being how what when".split())


def sig_tokens(title: str) -> list[str]:
    t = re.split(r"[;:]", (title or ""))[0].lower()          # drop subtitle
    toks = re.findall(r"[a-z0-9]+", t)
    return [w for w in toks if w not in STOP and len(w) > 1]


def surname(author: str) -> str:
    a = (author or "").strip()
    if not a:
        return ""
    first = re.split(r"[,;]", a)[0]                            # "SULLIVAN, HARRY..." -> "SULLIVAN"
    m = re.findall(r"[A-Za-z]+", first)
    return (m[-1] if m else "").lower()                       # last word of the surname field


def pg_surname(authors: str) -> set[str]:
    """Gutenberg 'Authors' may hold several 'Surname, First (dates)' joined by ';'. Return surnames."""
    out = set()
    for part in (authors or "").split(";"):
        m = re.findall(r"[A-Za-z]+", part.split(",")[0])
        if m:
            out.add(m[-1].lower())
    return out


def tok_subset_score(cand: list[str], full: set[str]) -> float:
    """Fraction of candidate tokens present in the full title, prefix-aware (truncation-tolerant)."""
    if not cand:
        return 0.0
    hit = 0
    for c in cand:
        if c in full:
            hit += 1
        elif len(c) >= 4 and any(f.startswith(c) or c.startswith(f) for f in full if len(f) >= 4):
            hit += 1
    return hit / len(cand)


def build_pg_index():
    by_surname = defaultdict(list)   # surname -> [(text#, title, token_set)]
    for r in csv.DictReader(open(PG, encoding="utf-8")):
        if r.get("Type") != "Text" or r.get("Language") != "en":
            continue
        toks = set(sig_tokens(r["Title"]))
        rec = (r["Text#"], r["Title"], toks)
        for sn in pg_surname(r["Authors"]) or {""}:
            by_surname[sn].append(rec)
    return by_surname


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gutenberg", action="store_true")
    ap.add_argument("--min-score", type=float, default=0.85)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(KEEP, encoding="utf-8")))
    pg = build_pg_index()
    print(f"candidates: {len(rows)} | PG surnames indexed: {len(pg)}", flush=True)

    hits = 0
    for r in rows:
        r["gutenberg_id"] = ""; r["gutenberg_title"] = ""; r["match_score"] = ""; r["source"] = ""
        sn = surname(r["Author"])
        cand = sig_tokens(r["Title"])
        if len(cand) < 2 or not sn:      # need a surname + >=2 title tokens for a safe match
            continue
        best = (0.0, None)
        for tid, title, toks in pg.get(sn, ()):
            sc = tok_subset_score(cand, toks)
            if sc > best[0]:
                best = (sc, (tid, title))
        if best[0] >= a.min_score and best[1]:
            r["gutenberg_id"] = best[1][0]; r["gutenberg_title"] = best[1][1]
            r["match_score"] = f"{best[0]:.2f}"; r["source"] = "gutenberg"; hits += 1

    cols = list(rows[0].keys())
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"Gutenberg matches: {hits}/{len(rows)} ({100*hits/len(rows):.1f}%)")
    print(f"wrote {OUT}")
    print("\n--- sample matches ---")
    for r in [x for x in rows if x["source"] == "gutenberg"][:15]:
        print(f"  pg{r['gutenberg_id']:>6} {r['match_score']}  {r['Title'][:40]:40} == {r['gutenberg_title'][:40]}")


if __name__ == "__main__":
    main()
