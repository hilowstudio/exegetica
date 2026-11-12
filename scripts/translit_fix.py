"""Propose corrections for transliterated Greek that OCR misread (macrons: gnōsis read "gndsis", sōma "s6ma").

Every Greek word form in study_bible.db (New Testament + Septuagint) is transliterated the way the Pillar and NICNT
commentaries print Greek (η ē, ω ō, υ y, ου ou, rough breathing h). An OCR word that is not English and matches
one form closely, counting a long vowel read as d, 6, é, ó, 0 or a plain vowel as a near miss, is proposed.

    python scripts/translit_fix.py <work>          writes .seed_cache/school/<cache>/translit.tsv for review
"""
from __future__ import annotations

import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import seed_pd_scan as sps  # noqa: E402

BASE = {"α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "ē", "θ": "th", "ι": "i", "κ": "k",
        "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
        "υ": "y", "φ": "ph", "χ": "ch", "ψ": "ps", "ω": "ō"}


def translit(word: str) -> str:
    """One Greek word -> the commentaries' transliteration."""
    nfd = unicodedata.normalize("NFD", word.lower())
    rough = "̔" in nfd                              # rough breathing anywhere marks an initial h
    letters = "".join(c for c in nfd if c in BASE)
    out, i = [], 0
    while i < len(letters):
        c, nx = letters[i], letters[i + 1] if i + 1 < len(letters) else ""
        if c == "γ" and nx in "γκξχ":
            out.append("n"); i += 1; continue
        if c in "αεηο" and nx == "υ":
            out.append({"α": "au", "ε": "eu", "η": "ēu", "ο": "ou"}[c]); i += 2; continue
        out.append(BASE[c]); i += 1
    t = "".join(out)
    if rough:
        t = ("rh" + t[1:]) if t.startswith("r") else "h" + t
    return t


def vocab() -> Counter:
    con = sqlite3.connect(f"file:{ROOT / 'db' / 'study_bible.db'}?mode=ro", uri=True)
    v = Counter()
    for (t,) in con.execute("select text_original from verses where text_original is not null"):
        for w in re.findall(r"[Ͱ-Ͽἀ-῿]+", t):
            v[translit(w)] += 1
    for (t,) in con.execute("select text_greek from lxx_verses where text_greek is not null"):
        for w in re.findall(r"[Ͱ-Ͽἀ-῿]+", t):
            v[translit(w)] += 1
    for (w,) in con.execute("select word from lexicon where language = 'greek'"):   # dictionary forms: agapaō
        if w:
            v[translit(w)] += 1
    return v


LONG = {"ō": set("d6óòôö0oé"), "ē": set("éèêëe")}       # OCR reads ō as é too (phétizei, houtés)


def cost(ocr: str, cand: str) -> float:
    """Edit distance where a long vowel read as one of its usual misreadings is a near miss."""
    a, b = ocr, cand
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            x, y = a[i - 1], b[j - 1]
            sub = 0 if x == y else (0.25 if y in LONG and x in LONG[y] else (0.5 if x in "éèêë" and y == "e" or
                                                                              x in "óòôö" and y == "o" else 1))
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub)
        prev = cur
    return prev[-1]


def main():
    work = sys.argv[1]
    s = sps.spec(work)
    sps.autocorrect("x")
    v = vocab()
    # index by consonant skeleton: vowels (long or short) and d/6/0, which OCR confuses with ō, dropped
    skel = lambda w: re.sub(r"[aeiouyōēéèêëóòôöd60]", "", w.lower())
    by_skel: dict = {}
    for w in v:
        by_skel.setdefault(skel(w), []).append(w)
    text = (s["dir"] / "work.md").read_text(encoding="utf-8")
    seen, rows = set(), []
    for m in re.finditer(r"(?<![A-Za-zĀ-ſ])[a-zA-Zéèêëóòôöōē0-9]{2,}(?![A-Za-zĀ-ſ])", text):
        tok = m.group(0).strip(" ’'‘")
        low = tok.lower()
        if " " in tok or len(low) < 3 or not re.search(r"[a-zéóò]", low) or tok[:1].isupper():
            continue
        plain = re.sub(r"[^a-z]", "", low)
        odd = bool(re.search(r"[éèêëóòôö6]|(?<=[a-z])0(?=[a-z])", low))
        if not odd and (plain in sps._english or sps._known[plain] >= 3):
            continue
        if low in seen:
            continue
        seen.add(low)
        best = sorted(((cost(low, c), -v[c], c) for c in by_skel.get(skel(low), [])
                       if abs(len(c) - len(low)) <= 1), key=lambda x: (x[0], x[1]))[:2]
        if best and best[0][0] <= 0.75 and best[0][2] != low:
            if len(best) < 2 or best[1][0] > best[0][0]:
                rows.append((tok, best[0][2], round(best[0][0], 2)))
            else:                                       # a tie: the scan decides
                rows.append((tok, best[0][2] + "|" + best[1][2], round(best[0][0], 2)))
    out = s["dir"] / "translit.tsv"
    out.write_text("\n".join(f"{a}\t{b}\t{c}" for a, b, c in rows), encoding="utf-8")
    print(f"{work}: {len(rows)} proposed transliteration fixes -> {out}")


if __name__ == "__main__":
    main()
