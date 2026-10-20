#!/usr/bin/env python3
"""
Recover the public-domain stories of one pulp issue from its Internet Archive scan.

For each story in the issue that is public domain now (docs/pulp-eligible-stories.csv) and has
no clean text yet (not on Gutenberg, not in our library), this:
  1. downloads the scan's ABBYY layout and page-number map (cached, .seed_cache/iapilot/),
  2. cuts the story out by the FictionMags contents' page numbers (ia_pulp_ocr),
  3. corrects scanner misreads with Claude, conservatively (no rewriting; cached),
  4. saves it to .seed_cache/pulp/scan/<issue>/, where seed_pulp_issues.py picks it up.
Serial installments are skipped: a scan carries only one part, and a serialized novel goes
into an issue complete.

    .venv\\Scripts\\python.exe scripts\\scan_pulp_issue.py "Weird Tales" 1927 10
    .venv\\Scripts\\python.exe scripts\\scan_pulp_issue.py "Weird Tales" 1927 10 --no-correct   # cut only
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

import build_pulp_eligibility as B  # noqa: E402
import ia_pulp_ocr as O  # noqa: E402

IA_COLLECTION = {"Weird Tales": "weirdtalesmagazine", "Fantastic Adventures": "fantasticadventures"}
UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (public-domain pulp recovery; hello@hilowstudio.dev)"}
SCAN_DIR = ROOT / ".seed_cache" / "pulp" / "scan"
IA_DIR = ROOT / ".seed_cache" / "iapilot"
MODEL = "claude-sonnet-5"
PRICE = (2.0, 10.0)   # $/MTok in, out (Sonnet 5)
SYSTEM = """You correct OCR errors in scanned pulp-magazine fiction from the 1920s to 1950s. Change ONLY what the scanner misread:
- letters misread as similar shapes (c/e, rn/m, li/h, cl/d, ii/u, t/f, b/h), broken or run-together words, stray page numbers, running heads, or advertisement fragments caught in the text
- punctuation only when it is clearly a scanning artifact
- hyphens left inside ordinary words by a line break (cult-ists becomes cultists); keep real compound hyphens (dust-colored)
Never rewrite, modernize spelling, change dialect or slang, fix the author's grammar, or alter style. Keep invented names consistent across the story (if a name appears correctly most of the time, correct the misread instances to match). Keep line breaks inside a paragraph exactly where they are (they matter in verse).
Pages at the back of a magazine mix the end of a story with advertisements, subscription offers, and blurbs for other stories. If a whole paragraph is one of those, a picture caption, a quoted line from an advertisement, or clearly belongs to a different article, output [OMIT] as its text. Be especially alert after the story's final line: anything that follows the ending (a caption, a teaser, an ad) is not part of the story.
Each paragraph arrives on its own line, prefixed by its number like ⟦12⟧. Return every paragraph, in order, each on its own line with the same number prefix. Never merge, split, skip, or renumber paragraphs. Output nothing else."""


def ia_item(mag: str, y: int, m: int) -> str:
    q = f"collection:{IA_COLLECTION[mag]} AND date:[{y}-{m:02d}-01 TO {y}-{m:02d}-28]"
    u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {"q": q, "fl[]": ["identifier", "title"], "rows": 10, "output": "json"}, doseq=True)
    docs = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())["response"]["docs"]
    docs = [d for d in docs if not re.search(r"modified|missing|uk|british", d["identifier"], re.I)]
    if not docs:
        raise SystemExit(f"no scan of {mag} {y}-{m:02d} in {IA_COLLECTION[mag]}")
    return docs[0]["identifier"]


def download(ident: str) -> str:
    stem = IA_DIR / ident
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://archive.org/metadata/{ident}/files", headers=UA), timeout=60).read())["result"]
    for suffix in ("_abbyy.gz", "_page_numbers.json"):
        target = Path(str(stem) + suffix)
        if target.exists():
            continue
        name = next((f["name"] for f in meta if f["name"].endswith(suffix)), None)
        if not name:
            raise SystemExit(f"{ident} has no {suffix}")
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
        IA_DIR.mkdir(parents=True, exist_ok=True)
        target.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300).read())
        time.sleep(2)
    return str(stem)


CHUNK = 60   # paragraphs per request: short enough that alignment can't drift


def _correct_chunk(client, start: int, chunk: list[str]) -> tuple[dict[int, str], float]:
    text = "\n".join(f"⟦{start + i}⟧ " + t.replace("\n", " ⏎ ") for i, t in enumerate(chunk))
    with client.messages.stream(model=MODEL, max_tokens=32000, system=SYSTEM, output_config={"effort": "low"},
                                messages=[{"role": "user", "content": text}]) as s:
        msg = s.get_final_message()
    out = "".join(b.text for b in msg.content if b.type == "text")
    got = {int(m.group(1)): m.group(2).strip().replace(" ⏎ ", "\n").replace("⏎", "\n")
           for m in re.finditer(r"⟦(\d+)⟧\s?(.*?)(?=\n⟦\d+⟧|\Z)", out, re.S)}
    return got, (msg.usage.input_tokens * PRICE[0] + msg.usage.output_tokens * PRICE[1]) / 1e6


def correct(client, paragraphs: list[str]) -> tuple[list[str], float, int]:
    """Correct paragraph by paragraph (numbered, in chunks). A paragraph the model drops, or
    whose length it changes by more than a fifth, keeps its raw text; [OMIT] removes ads."""
    fixed: dict[int, str] = {}
    cost = 0.0
    for start in range(0, len(paragraphs), CHUNK):
        got, c = _correct_chunk(client, start, paragraphs[start:start + CHUNK])
        fixed.update(got)
        cost += c
    out, fallbacks = [], 0
    for i, raw in enumerate(paragraphs):
        new = fixed.get(i)
        if new == "[OMIT]":
            continue
        if new is None or abs(len(new.split()) - len(raw.split())) > max(3, 0.2 * len(raw.split())):
            out.append(raw)
            fallbacks += 1
        else:
            out.append(new)
    return out, cost, fallbacks


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", B.norm(s)).strip("-")[:60]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("magazine")
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("--no-correct", action="store_true")
    a = ap.parse_args()
    mag, y, m = a.magazine, a.year, a.month
    cfg = B.MAGS[mag]

    items = [i for i in B.contents(mag, cfg["magid"], y, y, False, cfg["title"]) if (i["year"], i["month"]) == (y, m)]
    items.sort(key=lambda i: int(re.sub(r"\D", "", i["page"]) or 0))
    rows = {(r["title"], r["author"]): r for r in csv.DictReader(open(ROOT / "docs" / "pulp-eligible-stories.csv", encoding="utf-8"))
            if r["magazine"] == mag and B.issue_key(r["issue"]) == (y, m)}
    ident = ia_item(mag, y, m)
    pages = O.load_issue(download(ident))
    pages = {k: [p for p in v if not O.par_text(p).isdigit()] for k, v in pages.items()}
    out_dir = SCAN_DIR / f"{cfg['stem']}_{y}-{m:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{mag}, {y}-{m:02d}: scan {ident}, {len(pages)} pages, {len(items)} contents items")

    client = None
    if not a.no_correct:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        os.environ["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"].strip().strip('"').strip("'")
        import anthropic
        client = anthropic.Anthropic()
    total = 0.0
    for n, it in enumerate(items):
        r = rows.get((it["title"], it["author"]))
        if not r or r["public_domain_from"] != "now" or r["gutenberg"] or r["in_reading_room"]:
            continue                                     # protected, not fiction, or already have clean text
        if re.search(r"\[Part \d+ of \d+", it["title"]):
            print(f"  skip serial installment: {it['title'][:50]}")
            continue
        target = out_dir / f"{slugify(re.sub(r'\[.*?\]', '', it['title']))}.json"
        if target.exists():
            continue
        start = int(re.sub(r"\D", "", it["page"]))
        nxt = items[n + 1] if n + 1 < len(items) else None
        end = int(re.sub(r"\D", "", nxt["page"])) if nxt else max(pages)
        verse = r["type"] == "poem"
        pars = O.story_text(pages, start, end, re.sub(r"\[.*?\]", "", it["title"]), it["author"],
                            nxt["title"] if nxt else None, verse=verse)
        words = sum(len(p.split()) for p in pars)
        corrected, cost = False, 0.0
        fallbacks = 0
        if client and pars:
            try:
                pars, cost, fallbacks = correct(client, pars)
                corrected = True
            except Exception as e:  # noqa: BLE001
                print(f"  ! {it['title'][:40]}: {e}")
        total += cost
        target.write_text(json.dumps({"title": it["title"], "author": it["author"], "type": r["type"], "page": it["page"],
                                      "source": f"https://archive.org/details/{ident}", "corrected": corrected,
                                      "paragraphs": pars}, ensure_ascii=False, indent=1), encoding="utf-8")
        note = f" ({fallbacks} paragraphs kept raw)" if fallbacks else ""
        print(f"  {it['page']:>4} {r['type']:11} {B.strip(it['title'])[:40]:40} {words:>6,} words "
              f"{'corrected' if corrected else 'raw'} ${cost:.3f}{note}")
    print(f"done; correction cost ${total:.2f}; files in {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
