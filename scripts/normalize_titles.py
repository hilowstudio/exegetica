"""Normalize Reading Room book titles to title case.

Gutenberg's newer releases (and some CCEL records) carry library-catalog sentence case —
"The tin god of Twisted River" — while the rest of the shelf is title case. This rewrites only
titles whose major words are lowercase, using standard English title case:

  * capitalize major words, the first and last word, and the word after : — ; ? ! or an opening quote;
  * lowercase articles, conjunctions and short prepositions (a, the, and, of, in, with, from…);
  * never touch a word that already has internal capitals (MacDonald, McGraw, o'Day), an
    acronym, or text inside parentheses/brackets (original-language titles like "(Tache d'encre)");
  * uppercase Roman numerals (ii -> II).

Standard Ebooks titles are skipped (hand-edited, already correct). Every change is logged to
.seed_cache/reading_room/title_changes.csv (id, slug, old, new) so it can be reverted.

    .venv\\Scripts\\python.exe scripts\\normalize_titles.py --dry-run
    .venv\\Scripts\\python.exe scripts\\normalize_titles.py
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sqlite3
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

_LOG = _ROOT / ".seed_cache" / "reading_room" / "title_changes.csv"

SMALL = set("a an the and but or nor for so yet as at by in of off on per to up via vs v versus "
            "from into onto with upon than".split())
PARTICLES = {"de", "del", "della", "di", "da", "du", "des", "la", "le", "van", "von", "der", "den",
             "ter", "ten", "o'", "o’", "et"}   # name particles: Mademoiselle de Maupin, Alexander von Humboldt
ROMAN = re.compile(r"^(?=[ivxlc]+$)c{0,3}(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$", re.I)
NOT_ROMAN = {"civil", "mix", "lid", "dix", "liv", "vi", "xi"}   # real words / ambiguous; "vi"/"xi" handled below
_TOKEN = re.compile(r"(\([^)]*\)|\[[^\]]*\]|[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’\-.]*|[^A-Za-zÀ-ÿ(\[]+)")
_BREAK = re.compile(r"[:;—–!?]|\s-\s|^\s*['\"“‘]|['\"“‘]\s*$")


def _cap(word: str, first: bool = False) -> str:
    """Capitalize a word, and each part of a hyphenated compound (Side-Issue) — except to-day /
    to-morrow / to-night (one word) and a mid-title Arabic article (Kashf al-Mahjúb)."""
    parts = word.split("-")
    out = []
    for i, p in enumerate(parts):
        if not p:
            out.append(p)
        elif i == 0 and p.lower() == "al" and not first and len(parts) > 1:
            out.append("al")
        elif i > 0 and (p.lower() in SMALL or parts[0].lower() == "to"):
            out.append(p.lower())
        else:
            out.append(p[0].upper() + p[1:])
    return "-".join(out)


def _keep_as_is(word: str) -> bool:
    core = word.strip(".'’")
    if len(core) > 1 and any(ch.isupper() for ch in core[1:]):       # McGraw, o'Day, U.S., ODTAA
        return True
    return False


def title_case(title: str) -> str:
    tokens = _TOKEN.findall(title)
    word_idx = [i for i, t in enumerate(tokens) if t[:1].isalpha()]
    out = list(tokens)
    for n, i in enumerate(word_idx):
        w = tokens[i]
        first = n == 0 or bool(_BREAK.search("".join(tokens[word_idx[n - 1] + 1:i])))
        if n >= 2 and tokens[word_idx[n - 1]].lower() in ("or", "and") \
                and ";" in "".join(tokens[word_idx[n - 2] + 1:word_idx[n - 1]]):
            first = True                    # "…; or, The Modern Prometheus"
        last = n == len(word_idx) - 1 and not re.search(r"[0-9]", "".join(tokens[i + 1:]))
        bare = w.rstrip(".").lower()
        if _keep_as_is(w):
            continue
        before = tokens[i - 1] if i else ""
        if before.endswith(("'", "’")) and w.lower() in ("s", "t", "d", "ll", "re", "ve", "m", "em"):
            out[i] = w.lower()          # B-12's, Treat 'em Rough
            continue
        if ROMAN.match(bare) and bare not in NOT_ROMAN and len(bare) <= 6 and (bare not in ("vi", "xi") or not first):
            out[i] = w.upper()
            continue
        gap = "".join(tokens[word_idx[n - 1] + 1:i]) if n else ""
        if bare in ("or", "and") and ";" in gap:      # double titles: "…; or, The Modern Prometheus"
            out[i] = w.lower()
        elif (bare in SMALL or w.lower() in PARTICLES) and not first and not last:
            out[i] = w.lower()
        else:
            out[i] = _cap(w, first)
    return "".join(out)


def needs_fixing(title: str) -> bool:
    """Title has lowercase major words (sentence case or partly so)."""
    words = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’\-]*", re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", title))
    if not words:
        return False
    if words[0][0].islower():
        return True
    return any(w[0].islower() and w.lower() not in SMALL for w in words[1:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="db/books.db")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sample", type=int, default=60)
    args = ap.parse_args()
    con = sqlite3.connect(_ROOT / args.db, timeout=120)
    rows = con.execute("select id, slug, title, source from books where source != 'standardebooks'").fetchall()
    changes = []
    for bid, slug, title, _src in rows:
        if title and needs_fixing(title):
            new = title_case(title)
            if new != title:
                changes.append((bid, slug, title, new))
    print(f"{len(changes)} titles to change (of {len(rows)} non-Standard-Ebooks books)")
    step = max(1, len(changes) // max(1, args.sample))
    for bid, slug, old, new in changes[::step][:args.sample]:
        print(f"  {old[:60]:60} -> {new}")
    if args.dry_run:
        return
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["id", "slug", "old", "new"])
        w.writerows(changes)
    con.executemany("update books set title=? where id=?", [(new, bid) for bid, _s, _o, new in changes])
    con.commit()
    con.close()
    print(f"updated {len(changes)} titles; log: {_LOG}")


if __name__ == "__main__":
    main()
