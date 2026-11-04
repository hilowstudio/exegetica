"""Who the open textbooks students use name: OpenStax U.S. History, World History (volumes 1 and 2), and
American Government, read from the books' CNXML source (CC BY-NC-SA 4.0). Only the mentions are kept, as a
significance signal (the person appears in a textbook); none of the books' text goes into the database.

    .venv/Scripts/python.exe -I scripts/socialsci/textbook_mentions.py
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_history_graph as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / ".seed_cache" / "socialsci" / "openstax"
OUT = B.H.OUT / "significance" / "textbook_mentions.tsv"
NS = "{http://cnx.rice.edu/cnxml}"


def modules(repo: Path):
    """(book, module title, text) for every module, in the order the book's collections list them."""
    for coll in sorted((repo / "collections").glob("*.xml")):
        book = re.sub(r"\.collection\.xml$", "", coll.name)
        ids = re.findall(r'document="(m\d+)"', coll.read_text(encoding="utf-8"))
        for m in ids:
            f = repo / "modules" / m / "index.cnxml"
            if not f.exists():
                continue
            doc = ET.parse(f).getroot()
            title = (doc.findtext(f"{NS}title") or "").strip()
            content = doc.find(f"{NS}content")
            text = " ".join(t.strip() for t in content.itertext()) if content is not None else ""
            yield book, title, re.sub(r"\s+", " ", text)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(f"file:{B.DB.as_posix()}?mode=ro", uri=True)
    import ahocorasick
    firsts, lasts = Counter(), Counter()
    for (nm,) in con.execute("select name from h_entities where kind = 'person'"):
        w = re.findall(r"[A-Za-z']+", nm)
        if len(w) >= 2:
            firsts[w[0]] += 1
            lasts[w[-1]] += 1
    common_first = {w for w, _ in firsts.most_common(400)}
    common_last = {w for w, _ in lasts.most_common(1500)}
    cands: dict[str, list[tuple]] = {}
    for q, name, aliases, sl in con.execute("select qid, name, aliases, sitelinks from h_entities where kind = 'person'"):
        for n, is_label in {(name, True), *[(a.strip(), False) for a in (aliases or "").split(";")]}:
            if not n or not B._usable(n, is_label):
                continue
            if not is_label and n.split()[-1].lower() != name.split()[-1].lower():
                continue
            w = [x for x in re.findall(r"[A-Za-z']+", n) if len(x) > 1]
            need = 40 if len(w) == 2 and w[0] in common_first and w[1] in common_last else 0
            cands.setdefault(n, []).append((q, sl or 0, need))
    # one-word names (Confucius, Charlemagne): well known, the only entity of that name, and never an
    # ordinary lower-case word in the books (so not 'Homer' or 'Mark')
    texts = [(book, title, txt) for repo in sorted(BOOKS.glob("osbooks-*")) for book, title, txt in modules(repo)]
    lower = {w for _, _, t in texts for w in re.findall(r"\b[a-z]+\b", t)}
    shared = Counter(nm for (nm,) in con.execute("select name from h_entities"))
    inside = Counter(w for (nm,) in con.execute("select name from h_entities") for w in set(re.findall(r"[A-Z][a-z]+", nm or "")) if " " in (nm or ""))
    for q, name, sl in con.execute("select qid, name, sitelinks from h_entities where kind = 'person' and sitelinks >= 30"):
        if (re.fullmatch(r"[A-Z][a-z]{3,}", name or "") and shared[name] == 1 and name.lower() not in lower
                and name not in common_first and (sl >= 100 or inside[name] <= 2)):
            # not 'Stephen'; not 'Seljuk' (inside 'Seljuk Empire'), while Confucius (Confucius Institute) stays
            cands.setdefault(name, []).append((q, sl, 0))
    auto = ahocorasick.Automaton()
    for n, cs in cands.items():
        auto.add_word(n, (n, cs))
    auto.make_automaton()

    def pick(cs):  # one person by that name, or one far better known than any namesake (as for documents)
        if len(cs) == 1:
            return cs[0][0] if cs[0][1] >= max(3, cs[0][2]) else None
        cs = sorted(cs, key=lambda c: -c[1])
        return cs[0][0] if cs[0][1] >= 50 and cs[0][1] >= 10 * max(cs[1][1], 1) else None

    found: Counter = Counter()
    for book_name in sorted({b for b, _, _ in texts}):
        n_mod = 0
        for book, title, txt in (t for t in texts if t[0] == book_name):
            n_mod += 1
            for end, (n, cs) in auto.iter(txt):
                start = end - len(n) + 1
                nxt = txt[end + 1] if end + 1 < len(txt) else ""
                if (start > 0 and (txt[start - 1].isalnum() or txt[start - 1] in "-'’")) or nxt.isalnum() or nxt == "-":
                    continue
                if re.match(r"\s+(?:[A-Z][a-z]+|&|Co\b|Inc\b|Company\b|Junior\b)", txt[end + 1:end + 25]):
                    continue  # the head of a longer name
                before = re.search(r"([A-Za-z]+)\s+$", txt[max(0, start - 30):start])
                if before and before.group(1)[0].isupper() and before.group(1).lower() not in B.TITLES:
                    continue  # the tail of a longer name
                q = pick(cs)
                if q:
                    found[(q, book, title)] += 1
        print(f"{book_name}: {n_mod} modules", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["qid", "book", "chapter", "times"])
        w.writerows((q, b, t, n) for (q, b, t), n in sorted(found.items()))
    people = {q for q, _, _ in found}
    print(f"{len(found):,} mentions of {len(people):,} people -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
