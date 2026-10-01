"""Phase 2 source-finding: match the kept psychology candidates against archive.org.

Reads psych_sources.csv (produced by psych_find_sources.py --gutenberg, which already tagged the
few Gutenberg hits). For every row not yet sourced, queries the archive.org advancedsearch API by
title + author surname (mediatype:texts), scores the results with the same prefix-aware
title-token overlap + surname guard, and records the best match:

  archive_id, archive_title, archive_year, archive_access, and source set to:
    "archive"            - a text item whose full text is publicly available
    "archive-restricted" - a scan exists but is lending/print-disabled (not freely downloadable)
  (source left as-is for rows already tagged "gutenberg"; "" means no source found)

Threaded + resumable: re-running only queries rows whose `_archived` flag is empty, and it
checkpoints psych_sources.csv every 200 lookups.

    python scripts/psych_archive.py            # run/continue
    python scripts/psych_archive.py --workers 12
"""
from __future__ import annotations
import argparse, csv, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import httpx
from psych_find_sources import sig_tokens, surname, tok_subset_score

SRC = "psych_sources.csv"
UA = {"User-Agent": "ExegeticaReadingRoom/1.0 (library sourcing; hello@hilowstudio.dev)"}
ADV = "https://archive.org/advancedsearch.php"
_lock = threading.Lock()


def _q(title_tokens, sn):
    title = " ".join(title_tokens[:6])
    q = f'mediatype:(texts) AND title:({title})'
    if sn:
        q += f' AND creator:({sn})'
    return q


def lookup(client, cand_tokens, sn):
    params = [("q", _q(cand_tokens, sn)),
              ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "creator"),
              ("fl[]", "year"), ("fl[]", "access-restricted-item"),
              ("rows", "8"), ("output", "json")]
    for attempt in range(4):
        try:
            r = client.get(ADV, params=params, timeout=25)
            if r.status_code == 200:
                docs = r.json().get("response", {}).get("docs", [])
                break
            if r.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1)); continue
            return None
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    else:
        return None
    best = (0.0, None)
    for d in docs:
        toks = set(sig_tokens(d.get("title") or ""))
        sc = tok_subset_score(cand_tokens, toks)
        cr = (d.get("creator") or "")
        cr = " ".join(cr) if isinstance(cr, list) else cr
        if sn and sn not in cr.lower():
            sc -= 0.25            # penalise creator mismatch (title-only can still win if strong)
        if sc > best[0]:
            best = (sc, d)
    if best[0] >= 0.75 and best[1]:
        d = best[1]
        restricted = str(d.get("access-restricted-item", "")).lower() == "true"
        return {"id": d.get("identifier"), "title": (d.get("title") or "")[:120],
                "year": d.get("year", ""), "restricted": restricted}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    for r in rows:
        r.setdefault("archive_id", ""); r.setdefault("archive_title", "")
        r.setdefault("archive_year", ""); r.setdefault("archive_access", "")
        r.setdefault("_archived", "")
    cols = list(rows[0].keys())

    todo = [r for r in rows if r["source"] != "gutenberg" and not r["_archived"]]
    if a.limit:
        todo = todo[:a.limit]
    print(f"total {len(rows)} | to query archive.org: {len(todo)} | workers {a.workers}", flush=True)

    client = httpx.Client(headers=UA, follow_redirects=True)
    done = found = restricted = 0

    def work(r):
        res = lookup(client, sig_tokens(r["Title"]), surname(r["Author"]))
        return r, res

    def flush():
        with open(SRC + ".tmp", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        os.replace(SRC + ".tmp", SRC)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for fut in as_completed(futs):
            r, res = fut.result()
            r["_archived"] = "1"
            if res:
                r["archive_id"] = res["id"]; r["archive_title"] = res["title"]
                r["archive_year"] = res["year"]
                if res["restricted"]:
                    r["archive_access"] = "restricted"; r["source"] = r["source"] or "archive-restricted"; restricted += 1
                else:
                    r["archive_access"] = "public"; r["source"] = r["source"] or "archive"; found += 1
            done += 1
            if done % 200 == 0:
                with _lock: flush()
                print(f"  {done}/{len(todo)} | public={found} restricted={restricted}", flush=True)
    flush()
    from collections import Counter
    print(f"\nDONE. queried {done} | public archive={found} | restricted={restricted}")
    print("source column:", dict(Counter(r["source"] or "(none)" for r in rows)))


if __name__ == "__main__":
    main()
