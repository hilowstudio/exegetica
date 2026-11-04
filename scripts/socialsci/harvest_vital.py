"""Wikipedia's Vital Articles for people (levels 4 and 5): the articles editors judge most important, chosen
for importance rather than traffic. Each list page is read once as raw wikitext (about 35 requests, slowly);
the linked titles are matched to Wikidata items through QLever, so the Wikipedia API is never queried.
Saved as (qid, level, list, title) for the significance measure.

    .venv/Scripts/python.exe scripts/socialsci/harvest_vital.py
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harvest_wikidata as H  # noqa: E402

RAW = "https://en.wikipedia.org/w/index.php?action=raw&title="
CACHE = H.OUT / "significance" / "vital"
OUT = H.OUT / "significance" / "vital_people.tsv"
LISTS = {
    4: ["", "Artists, musicians, and composers", "Entertainers, directors, producers, and screenwriters",
        "Explorers and businesspeople", "Jurists, law enforcement, and criminals",
        "Military personnel, revolutionaries, and activists", "Miscellaneous",
        "Philosophers, historians, political and social scientists", "Politicians and leaders", "Religious figures",
        "Scientists, inventors, and mathematicians", "Sports figures", "Writers and journalists"],
    5: ["", "Artists", "Artists, musicians, and composers", "Authorities and leadership figures",
        "Creative and cultural figures", "Entertainers, directors, producers, and screenwriters",
        "Explorers and businesspeople", "Jurists, law enforcement, and criminals",
        "Military personnel, revolutionaries, and activists", "Miscellaneous",
        "Philosophers, historians, political and social scientists", "Politicians and leaders", "Religious figures",
        "Scientists, inventors, and mathematicians", "Sports figures", "Writers and journalists"],
}


def raw(title: str) -> str:
    """One list page's wikitext, cached; a polite pace, and long waits when Wikipedia asks for them."""
    # the old and new page names ('Level/5', 'Level 5') differ only in punctuation, so the file name carries a hash
    f = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", title)[-80:] + "_" + hashlib.sha1(title.encode()).hexdigest()[:8] + ".wiki")
    if f.exists():
        return f.read_text(encoding="utf-8")
    for attempt in range(6):
        time.sleep(4)
        try:
            req = urllib.request.Request(RAW + urllib.parse.quote(title), headers={"User-Agent": H.UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8")
            if "too many requests" in text[:300].lower():
                raise urllib.error.HTTPError(RAW, 429, "rate limited", None, None)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
            return text
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            wait = 120 * (attempt + 1)
            print(f"  {title}: HTTP {e.code}; waiting {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"gave up on {title}")


def titles(text: str) -> list[str]:
    out = []
    for link in re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", text):
        t = link.strip().replace("_", " ")
        if ":" in t or not t:
            continue
        out.append(t[0].upper() + t[1:])
    return out


def to_items(names: list[str]) -> dict[str, str]:
    """English Wikipedia titles -> Wikidata items, through QLever's copy of the sitelinks."""
    out: dict[str, str] = {}
    for i in range(0, len(names), 2000):
        chunk = names[i:i + 2000]
        vals = " ".join('"' + n.replace("\\", "\\\\").replace('"', '\\"') + '"@en' for n in chunk)
        dest = CACHE / f"items_{i // 2000:03d}.tsv"
        H.run(f"""SELECT ?t ?x WHERE {{ VALUES ?t {{ {vals} }}
                  ?a schema:name ?t ; schema:isPartOf <https://en.wikipedia.org/> ; schema:about ?x }}""", dest)
        for r in H.read(dest):
            if len(r) >= 2:
                out[H.lit(r[0])] = H.qid(r[1])
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    found: list[tuple[int, str, str]] = []
    done: set[str] = set()
    for level, lists in LISTS.items():
        for sub in lists:
            title = f"Wikipedia:Vital articles/Level/{level}/People" + (f"/{sub}" if sub else "")
            text = raw(title)
            for _ in range(2):  # the lists moved ('Level/4/People' -> 'Level 4/People'); follow the redirect
                m = re.match(r"\s*#REDIRECT\s*\[\[([^\]#|]+)", text or "", re.I)
                if not m:
                    break
                title = m.group(1).strip()
                text = "" if title in done else raw(title)
            if not text or title in done:
                continue
            done.add(title)
            ts = titles(text)
            found += [(level, title.split("/People")[-1].strip("/ ") or "People", t) for t in ts]
            print(f"level {level} {title}: {len(ts):,} links", flush=True)
    names = sorted({t for _, _, t in found})
    items = to_items(names)
    rows = sorted({(items[t], lv, sub, t) for lv, sub, t in found if t in items})
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["qid", "level", "list", "title"])
        w.writerows(rows)
    print(f"{len(names):,} titles, {len(items):,} matched to items; {len({r[0] for r in rows}):,} items -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
