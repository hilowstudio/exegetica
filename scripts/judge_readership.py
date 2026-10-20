"""Ask Claude Adam's keep-or-delete question about every Gutenberg book in the Reading Room.

The question (Adam, 2026-10-06): "What is the probability that if our pre-loaded e-reader app had
100,000 American users of all ages and backgrounds who read ten books a year, that 5-10 users
would click this book and read it in the first five years of owning the app?"

Download counts can't answer it: the bar (about 1 user in 20,000) sits far inside Gutenberg's
per-book crawler noise. So each book is judged on what a reader would see and know: title, author,
year, subjects, length, plus the evidence of a lasting audience (Open Library editions/readers,
a Wikipedia article for the work, the author's Wikipedia reach).

Reads docs/gutenberg-holdings-review.csv (score_gutenberg_holdings.py), writes
docs/gutenberg-readership.csv {slug, p, reason}. Cached per slug in
.seed_cache/pd_sources/readership_judgments.json, so reruns only judge new books.

    python scripts/judge_readership.py --sample 150     # pilot on a mixed sample
    python scripts/judge_readership.py                  # every book
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "gutenberg-holdings-review.csv"
OUT = ROOT / "docs" / "gutenberg-readership.csv"
CACHE = ROOT / ".seed_cache" / "pd_sources" / "readership_judgments.json"
MODEL = "claude-sonnet-5-5"
PRICE = (2.0, 10.0)   # $/MTok in, out
BATCH = 40

SYSTEM = """You estimate readership for books in the Reading Room, the built-in library of a free \
e-reader app. Every book is in the public domain; the library holds about 11,400 of them: classic \
literature, theology, children's books, science fiction, mysteries, westerns, history, biography, \
poetry, travel, and more. Readers browse by section, search, and see cover art.

Imagine the app pre-loaded for 100,000 American users of all ages and backgrounds (children, teens, \
adults, retirees; every region and education level), each reading ten books a year from this \
library. Over the first five years that is 5,000,000 book-reads spread across the ~11,400 titles.

For each book, give the probability (0.00-1.00) that at least 5-10 different users would click it \
and actually read it in those five years.

Judge it as a real person meeting the book in the app would: is the title or author recognizable; \
would the subject draw anyone today (including hobbyists, students, history buffs, kids, people of \
faith); is it readable now; is it a complete work or an odd fragment (a single volume of a set, a \
government bulletin, a trade catalog, a technical report, a regional directory)? A well-known \
author's lesser work, a still-loved children's series, a lively memoir or a page-turning genre \
novel can clear the bar; a 1920s municipal report, a parts manual or a taxonomic paper on one frog \
genus usually cannot. Use the evidence given (editions = times republished; readers = Open Library \
users who shelved it; article = the work has a Wikipedia article; author_langs = Wikipedia language \
editions about the author) but rely on your own knowledge of the book where you have it. Be \
calibrated, not generous or harsh.

Answer with JSON only: a list of {"id": <id>, "p": <probability>, "why": "<at most 12 words>"}, one \
entry per book, in the order given."""


def client():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip().strip('"').strip("'")
    import anthropic
    return anthropic.Anthropic()


def describe(i: int, r: dict) -> str:
    parts = [f"id {i}", f"title: {r['title']}", f"author: {r['author'] or 'unknown'}"]
    if r.get("first_year"):
        parts.append(f"first published: {r['first_year']}")
    parts.append(f"words: {r['words']}")
    if r.get("genres"):
        parts.append(f"shelf: {', '.join(json.loads(r['genres']))}")
    if r.get("shelves"):
        parts.append(f"gutenberg shelves: {r['shelves'][:120]}")
    parts.append(f"editions {r['editions']}, readers {r['readers']}, article {'yes' if int(r['work_article_langs'] or 0) else 'no'}, "
                 f"author_langs {r['author_langs']}")
    return " | ".join(parts)


def judge(c, batch: list[dict]) -> tuple[dict, float]:
    text = "\n".join(describe(i, r) for i, r in enumerate(batch))
    msg = c.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM, output_config={"effort": "low"},
                            messages=[{"role": "user", "content": text}])
    out = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"\[.*\]", out, re.S)
    got = {}
    for e in json.loads(m.group(0)) if m else []:
        try:
            got[batch[int(e["id"])]["slug"]] = {"p": float(e["p"]), "why": str(e.get("why", ""))[:120]}
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    return got, (msg.usage.input_tokens * PRICE[0] + msg.usage.output_tokens * PRICE[1]) / 1e6


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    if "--sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--sample") + 1])
        random.seed(1)
        by = {t: [r for r in rows if r["tier"] == t] for t in ("keep", "review", "evaluate", "remove")}
        canon = [r for r in rows if r["canon"] == "1"]
        pick = random.sample(canon, n // 5) + sum((random.sample(v, min(len(v), n // 5)) for v in by.values()), [])
        rows = list({r["slug"]: r for r in pick}.values())
    todo = [r for r in rows if r["slug"] not in cache]
    print(f"{len(todo):,} to judge ({len(rows) - len(todo):,} cached)")
    c = client()
    cost = 0.0
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with cf.ThreadPoolExecutor(4) as ex:
        for k, fut in enumerate(cf.as_completed([ex.submit(judge, c, b) for b in batches]), 1):
            try:
                got, usd = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  batch failed: {e}")
                continue
            cache.update(got)
            cost += usd
            if k % 10 == 0 or k == len(batches):
                CACHE.write_text(json.dumps(cache), encoding="utf-8")
                print(f"  {k}/{len(batches)} batches, ${cost:.2f}", flush=True)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["slug", "title", "author", "tier", "group", "canon", "p", "why"])
        for r in rows:
            j = cache.get(r["slug"])
            if j:
                w.writerow([r["slug"], r["title"], r["author"], r["tier"], r["group"], r["canon"], j["p"], j["why"]])
    print(f"wrote {OUT.relative_to(ROOT)}; spent ${cost:.2f}")


if __name__ == "__main__":
    main()
