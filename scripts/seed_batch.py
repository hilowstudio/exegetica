"""Bulk-seed the shared Living Library catalog from the public-domain book list using the
Batch API (50% cheaper) on Claude Sonnet 5.

Two batch rounds (the grounding pipeline's derive → propose → verify, minus the redundant
per-objective verify): round 1 = one `derive` per book + one `propose` per section; round 2
= one `verify` per section (all its objectives at once). Prompt caching is OFF here — in
batch, propose and verify land in separate rounds minutes apart, so the 5-min cache never
hits (it would only add a write cost). The interactive path (a teacher clicking Build) keeps
caching on.

Each book is deduped via the shared catalog (find-or-create by dedup key); an already-
`extracted` book is skipped, never reprocessed. Books no PD source carries are skipped with
zero model spend. Actual token usage is summed and reported in dollars at Sonnet batch rates.

Run (needs network + ANTHROPIC_API_KEY + DATABASE_URL; costs real money):
    PYTHONPATH=. .venv/Scripts/python.exe scripts/seed_batch.py --limit 8        # pilot
    PYTHONPATH=. .venv/Scripts/python.exe scripts/seed_batch.py                  # all PD titles
    PYTHONPATH=. .venv/Scripts/python.exe scripts/seed_batch.py --dry-run        # fetch+segment only, no API
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import re
import sys
import time

# Make the script runnable as-is (no PYTHONPATH needed): put the project root on the path
# so `import webapp` resolves, and force UTF-8 stdout so em-dashes/★ in titles print on Windows.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

from webapp import db, extraction as EX  # noqa: E402
from webapp.sources import registry  # noqa: E402
from webapp.sources import text_processing as TP  # noqa: E402

PD_DOC = pathlib.Path(__file__).resolve().parents[1] / "docs" / "classics-lists-pd-split.md"
# Batch API rates (50% of standard), $/MTok input, output. Gemini 3.8 Flash is intro-priced
# through 2026-12-31 (doubles in 2027). Unknown models fall back to Sonnet-5 rates.
_BATCH_RATES = {
    "gemini-3.8-flash": (0.375, 1.875),
    "claude-sonnet-5": (1.0, 5.0),
}
_ENTRY = re.compile(r"^- (.+?) — (.+?)(?:\s*\((?:\d{1,4}(?: BC)?)\))?\s*[★‡]*\s*$")


def _rates(model: str) -> tuple[float, float]:
    return _BATCH_RATES.get(model, _BATCH_RATES["claude-sonnet-5"])


def load_pd(limit: int | None) -> list[dict]:
    """Parse the 'Public domain' section of the PD-split doc into {title, author} rows."""
    lines = PD_DOC.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## Public domain"))
        end = next(i for i, ln in enumerate(lines[start + 1:], start + 1) if ln.startswith("## "))
    except StopIteration:
        end = len(lines)
    books, seen = [], set()
    for ln in lines[start:end]:
        m = _ENTRY.match(ln.rstrip())
        if not m:
            continue
        title, author = m.group(1).strip(), m.group(2).strip()
        key = (title.lower(), author.lower())
        if key in seen:
            continue
        seen.add(key)
        books.append({"title": title, "authors": [author]})
    return books[:limit] if limit else books


# On-disk cache of fetched source text, so re-runs (dry-run iteration especially) are instant
# and don't re-hammer gutendex into throttling. Keyed by dedup; re-segments from cached text
# each run so segmentation improvements still take effect.
_CACHE = _ROOT / ".seed_cache"


def _cache_path(meta: dict) -> pathlib.Path:
    import hashlib
    return _CACHE / (hashlib.sha1(EX.book_dedup_key(meta).encode()).hexdigest()[:16] + ".json")


def cached(meta: dict) -> bool:
    return _cache_path(meta).exists()


async def fetch_book(meta: dict) -> dict | None:
    import json
    cp = _cache_path(meta)
    got = None
    if cp.exists():
        try:
            got = json.loads(cp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            got = None
    if got is None:
        hits = await registry.discover_all(meta)
        g = await registry.fetch_first_available(hits)
        if not g:
            return None
        got = {"text": g["text"], "source": g["source"], "source_id": g["source_id"],
               "us_clear": g["source"] in EX._US_CLEAR_SOURCES}
        try:
            _CACHE.mkdir(exist_ok=True)
            cp.write_text(json.dumps(got), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    sections = TP.segment_into_chapters(got["text"])
    if not sections:
        return None
    return {"meta": meta, "text": got["text"], "sections": sections, "source": got["source"],
            "source_id": got["source_id"], "us_clear": got["us_clear"]}


def _usable(section: dict) -> bool:
    return len(EX._excerpt(section["text"], 6000)) >= TP._MIN_SECTION_CHARS


def _with_model(params: dict, model: str) -> dict:
    params["model"] = model
    return params


def phase1_requests(books: list[dict], model: str) -> list[dict]:
    reqs = []
    for i, b in enumerate(books):
        reqs.append({"custom_id": f"d_{i}", "params": _with_model(EX.derive_params(b["meta"], b["sections"]), model)})
        for s in b["sections"]:
            if _usable(s):
                reqs.append({"custom_id": f"p_{i}_{s['section_number']}",
                             "params": _with_model(EX.propose_params(b["meta"], s, cache=False), model)})
    return reqs


def phase2_requests(books: list[dict], proposals: dict, model: str) -> list[dict]:
    reqs = []
    for (i, sn), objs in proposals.items():
        sec = next(s for s in books[i]["sections"] if s["section_number"] == sn)
        reqs.append({"custom_id": f"v_{i}_{sn}", "params": _with_model(EX.verify_params(sec, objs, cache=False), model)})
    return reqs


def run_batch_provider(model: str, requests: list[dict], label: str, poll: int) -> tuple[dict, dict]:
    """Dispatch a batch to the right provider's Batch API by model prefix."""
    if model.startswith("gemini"):
        from webapp import gemini
        return gemini.run_batch(requests, label, poll)
    import anthropic
    return run_batch(anthropic.Anthropic(), requests, label, poll)


def run_batch(client, requests: list[dict], label: str, poll: int = 30) -> tuple[dict, dict]:
    """Submit one batch, poll to completion, return {custom_id: parsed_json} + usage totals."""
    batch = client.messages.batches.create(requests=requests)
    print(f"  [{label}] batch {batch.id}: {len(requests)} requests submitted")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        time.sleep(poll)
    out, usage = {}, {"in": 0, "out": 0}
    for r in client.messages.batches.results(batch.id):
        if r.result.type == "succeeded":
            msg = r.result.message
            out[r.custom_id] = EX._parse_json(EX._text_of(msg))
            usage["in"] += msg.usage.input_tokens
            usage["out"] += msg.usage.output_tokens
    print(f"  [{label}] succeeded {b.request_counts.succeeded}, errored {b.request_counts.errored}; "
          f"tokens in {usage['in']:,} out {usage['out']:,}")
    return out, usage


async def persist(book: dict, derivative: dict, kept: list[dict]) -> str:
    """Write one fully-processed book to the shared catalog (mirrors the pipeline's derive +
    objectives + finalize, minus the transient full_text_raw hop)."""
    meta, sections = book["meta"], book["sections"]
    exid = await EX.ensure_extraction_row(meta)
    q = EX.compute_quality(book["text"], sections)
    derivative = dict(derivative or {})
    derivative["table_of_contents"] = [{"n": s["section_number"], "title": s["title"]} for s in sections]
    await db.execute(
        """update library_extractions set
             kind='book', derivative=$2, public_domain=true, us_clear=$3, grounding='source_text',
             source_meta=$4, canonical_source=$5, canonical_tier=$6, quality_score=$7,
             full_text = case when $3 then $8 else null end, full_text_raw=null,
             status='extracted', extracted_at=now(), updated_at=now()
           where id=$1""",
        exid, derivative, book["us_clear"], {"source": book["source"], "source_id": book["source_id"]},
        book["source"], EX._TRUSTED_SOURCE_TIER, q["score"], book["text"],
    )
    await db.execute("delete from library_sections where extraction_id=$1", exid)
    for s in sections:
        await db.execute(
            "insert into library_sections (extraction_id, position, label_type, number, title) "
            "values ($1,$2,'chapter',$3,$4)", exid, s["section_number"], str(s["section_number"]), s["title"],
        )
    secmap = await EX._section_id_map(exid)
    await db.execute(
        "delete from library_objectives where extraction_id=$1 and user_id is null and provenance='seed_grounded'",
        exid,
    )
    for o in kept:
        await db.execute(
            "insert into library_objectives (extraction_id, user_id, section_id, text, citation, provenance, status) "
            "values ($1, null, $2, $3, $4, 'seed_grounded', 'accepted')",
            exid, secmap.get(o.get("section_number")), o["text"], o.get("citation"),
        )
    await db.execute("delete from library_alignments where extraction_id=$1 and source='auto'", exid)
    for a in EX.align_to_spine(book["text"], sections):
        try:
            await db.execute(
                "insert into library_alignments (extraction_id, section_id, spine_level, spine_node_id, status, source) "
                "values ($1,$2,$3,$4,'proposed','auto') on conflict do nothing",
                exid, secmap.get(a.get("section_number")), a["spine_level"], a["spine_node_id"],
            )
        except Exception:  # noqa: BLE001 — spine node not present; skip
            pass
    return str(exid)


# Per-book token profile for the dry-run forecast (excludes thinking tokens): 1 `derive`
# call, plus a `propose` and a `verify` call per USABLE section (>= _MIN_SECTION_CHARS).
_DERIVE_IN, _DERIVE_OUT = 1800, 600
_PER_SECTION_IN, _PER_SECTION_OUT = 3550, 550


def _report_segments(books: list[dict], model: str) -> None:
    """Per-work segment counts + a cost forecast grounded in the ACTUAL counts (not a guess).
    Sorted so single-'Full text' books (segmentation misses worth inspecting) surface first."""
    import statistics

    rows = []
    for b in books:
        n_all = len(b["sections"])
        n_use = sum(1 for s in b["sections"] if _usable(s))
        single = n_all == 1 and b["sections"][0].get("title") == "Full text"
        rows.append((n_use, n_all, single, b["meta"]["title"], b["source"]))
    rows.sort()

    print(f"\n=== segment report · model={model} · {len(books)} books ===")
    for n_use, n_all, single, title, src in rows:
        flag = "  ⚠ Full text (no chapters detected)" if single else ""
        print(f"  {n_use:4} usable / {n_all:4} total   {title[:46]:46} [{src}]{flag}")

    if not rows:
        return
    total_use = sum(r[0] for r in rows)
    singles = sum(1 for r in rows if r[2])
    counts = [r[0] for r in rows]
    tin = len(rows) * _DERIVE_IN + total_use * _PER_SECTION_IN
    tout = len(rows) * _DERIVE_OUT + total_use * _PER_SECTION_OUT
    in_rate, out_rate = _rates(model)
    cost = tin * in_rate / 1_000_000 + tout * out_rate / 1_000_000
    print(f"\n  usable sections: {total_use:,} (total {sum(r[1] for r in rows):,}) · "
          f"per book min {min(counts)} / median {statistics.median(counts):g} / max {max(counts)} · "
          f"single-'Full text' books: {singles}")
    print(f"  forecast (Batch API, excludes thinking): in {tin:,} out {tout:,} tok · "
          f"{model} ≈ ${cost:,.2f}  (${cost / len(rows):.3f}/book)")


def _keep_awake(on: bool) -> None:
    """Stop Windows from sleeping mid-run — the Gemini batch poll can run long and a sleep
    suspends the whole process. No-op on other platforms; releases on exit either way."""
    if sys.platform != "win32":
        return
    import ctypes

    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
    except Exception:  # noqa: BLE001
        pass


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process only the first N PD titles")
    ap.add_argument("--dry-run", action="store_true", help="fetch + segment only; no API calls")
    ap.add_argument("--poll", type=int, default=30, help="batch poll interval (s)")
    ap.add_argument("--model", default="gemini-3.8-flash",
                    help="extraction model (gemini-3.8-flash [default] or claude-sonnet-5)")
    ap.add_argument("--delay", type=float, default=0.3,
                    help="pause after each real (uncached) network fetch (s), to be gentle on free mirrors")
    ap.add_argument("--concurrency", type=int, default=6,
                    help="how many books to fetch in parallel (overlaps throttle-waits)")
    args = ap.parse_args()
    model = args.model

    await db.init_pool()
    wanted = load_pd(args.limit)
    print(f"PD titles to seed: {len(wanted)}")

    # Fetch + segment concurrently (bounded), skipping already-extracted books. The disk cache
    # makes repeats free; concurrency overlaps the gutendex throttle-waits on a cold run.
    books, skipped, missing = [], 0, 0
    sem = asyncio.Semaphore(max(1, args.concurrency))

    async def process(meta: dict):
        nonlocal skipped, missing
        exid = await EX.ensure_extraction_row(meta)
        if (await db.fetchval("select status from library_extractions where id=$1", exid)) == "extracted":
            skipped += 1
            return
        async with sem:
            was_cached = cached(meta)
            got = await fetch_book(meta)
            if not was_cached and args.delay:
                await asyncio.sleep(args.delay)
        if not got:
            missing += 1
            print(f"  --  no source: {meta['title']} — {meta['authors'][0]}", flush=True)
        else:
            books.append(got)
            n_use = sum(1 for s in got["sections"] if _usable(s))
            print(f"  {n_use:4} sec  {meta['title'][:50]:50} [{got['source']}]", flush=True)

    await asyncio.gather(*(process(m) for m in wanted))

    # Dedup works that appear under author-name variants (Dostoevsky/Dostoyevsky, Cervantes /
    # Cervantes Saavedra) or from two sources — keep the best-segmenting copy so we never
    # double-charge or persist the coarse one (e.g. a 1-section CCEL over a 6-section Gutenberg).
    from webapp.sources.matching import normalize as _norm
    best: dict = {}
    for b in books:
        k = _norm(b["meta"]["title"])
        n_use = sum(1 for s in b["sections"] if _usable(s))
        if k not in best or n_use > best[k][0]:
            best[k] = (n_use, b)
    deduped = [b for _, b in best.values()]
    if len(deduped) < len(books):
        print(f"deduped {len(books) - len(deduped)} author/source-variant duplicates")
    books = deduped
    print(f"fetched {len(books)} | already-extracted {skipped} | no source {missing}")

    if args.dry_run or not books:
        _report_segments(books, model)
        await db.close_pool()
        return

    _keep_awake(True)  # released on exit; the batch poll can run long
    print(f"extracting with model: {model}")
    # Round 1: derive + propose
    r1, u1 = await asyncio.to_thread(
        run_batch_provider, model, phase1_requests(books, model), "derive+propose", args.poll)
    derivatives, proposals = {}, {}
    for i, b in enumerate(books):
        derivatives[i] = EX.parse_derivative(r1.get(f"d_{i}"))
        for s in b["sections"]:
            props = EX.parse_proposals(s["section_number"], r1.get(f"p_{i}_{s['section_number']}"))
            if props:
                proposals[(i, s["section_number"])] = props

    # Round 2: verify (one call per section)
    r2, u2 = ({}, {"in": 0, "out": 0})
    if proposals:
        r2, u2 = await asyncio.to_thread(
            run_batch_provider, model, phase2_requests(books, proposals, model), "verify", args.poll)
    kept_by_book: dict = {}
    for (i, sn), objs in proposals.items():
        kept_by_book.setdefault(i, []).extend(EX.keep_verified(objs, r2.get(f"v_{i}_{sn}")))

    # Persist
    persisted = 0
    for i, b in enumerate(books):
        try:
            await persist(b, derivatives.get(i, {}), kept_by_book.get(i, []))
            persisted += 1
        except Exception as e:  # noqa: BLE001
            print(f"  persist failed: {b['meta']['title']}: {e}")

    tin, tout = u1["in"] + u2["in"], u1["out"] + u2["out"]
    in_rate, out_rate = _rates(model)
    cost = tin * in_rate / 1_000_000 + tout * out_rate / 1_000_000
    print(f"\nSeeded {persisted}/{len(books)} books · objectives kept "
          f"{sum(len(v) for v in kept_by_book.values())}")
    print(f"Tokens: in {tin:,} out {tout:,} · {model} batch cost ≈ ${cost:,.2f} "
          f"(${cost / max(persisted,1):.3f}/book)")
    _keep_awake(False)
    await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
