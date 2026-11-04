"""Whole-work comprehension layer for the Living Library generator (Phase 2).

Large works can't be fed to the model whole, so we pre-build an analytical understanding of the
ENTIRE work — summary, arc, themes, significant (load-bearing) elements, and a cumulative recap
ladder — via a batched map-reduce over the text, cached in Neon (library_comprehension). The build
runs on Inngest (webapp/inngest_app.py, `build-comprehension`): one memoized step per batch, one
build per book at a time, so a closed browser or a crash loses no paid work and a retry re-runs only
the failed batch. The first generation against a large book requests it and tells the teacher the
book is being prepared. Uses the server ANTHROPIC key (a shared, cached artifact, not per-teacher
BYOK). Small books never need this — they're read whole at generation time. See
docs/living-library-generation-plan.md.

Also provides covered-range passage selection (semantic retrieval via webapp.embed) for when the
covered range itself is too large to include verbatim.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import math

from webapp import db, embed, extraction, reader

logger = logging.getLogger("study-bible-web.comprehension")

_MAP_SYSTEM = ("You are a careful analytical reader. Read the given span of a literary or scholarly "
               "work and report structured notes on it. Reply with STRICT JSON only.")
_REDUCE_SYSTEM = ("You synthesize a whole-work understanding from ordered span-notes. Be concrete and "
                  "specific to THIS work, not generic. Reply with STRICT JSON only.")

def _as_obj(out) -> dict:
    """Coerce an LLM JSON reply to a dict (models sometimes wrap it in a one-element array)."""
    if isinstance(out, dict):
        return out
    if isinstance(out, list) and out and isinstance(out[0], dict):
        return out[0]
    return {}


_MAX_BATCHES = 40          # cap total map calls even for enormous works
_MIN_BATCH_WORDS = 40000   # ~a comfortable chunk per map call
_MAX_WORDS = 1_500_000     # above this (e.g. Spurgeon's 24M-word sermon corpus) a whole-work pass is
                           # neither affordable nor meaningful — callers fall back to the covered text
MAP_CONCURRENCY = 5       # map steps in flight per build (Inngest also caps the function at this)
FAILED_MODEL = "build-failed"   # model column of a failed build's marker row
RETRY_AFTER = dt.timedelta(hours=24)   # a failed build is tried again after this


def _batches(chapters: list[dict], total_words: int) -> list[list[dict]]:
    per = max(_MIN_BATCH_WORDS, math.ceil((total_words or 1) / _MAX_BATCHES))
    out, cur, cw = [], [], 0
    for c in chapters:
        cur.append(c)
        cw += c.get("words", 0)
        if cw >= per:
            out.append(cur); cur, cw = [], 0
    if cur:
        out.append(cur)
    return out


async def _map_batch(title: str, batch: list[dict], i: int, n: int) -> dict:
    first, last = batch[0]["n"], batch[-1]["n"]
    text = "\n\n".join(
        f"[section {c['n']}{(' — ' + c['title']) if c.get('title') else ''}]\n{c['text']}" for c in batch)
    user = (f'Work: "{title}"\nThis is span {i + 1} of {n} (sections {first}–{last}).\n\n{text}\n\n'
            'Return JSON only: {"summary": "3–5 concise sentences on what happens in this span", '
            '"themes": ["up to 8 SHORT theme/motif phrases"], '
            '"significant": ["up to 10 SHORT phrases — elements introduced/developed here that '
            'matter later: characters, objects, revelations, turns, motifs"]}')
    out = _as_obj(await extraction._complete_json(_MAP_SYSTEM, user, max_tokens=2500))
    return {"first": first, "last": last, "summary": out.get("summary", ""),
            "themes": out.get("themes") or [], "significant": out.get("significant") or []}


async def _reduce(title: str, notes: list[dict]) -> dict:
    joined = "\n\n".join(f"Span {i + 1} (sections {b['first']}–{b['last']}): {b['summary']}"
                         for i, b in enumerate(notes))
    themes = sorted({t for b in notes for t in b["themes"]})
    user = (f'Work: "{title}"\nOrdered span summaries:\n{joined}\n\nThemes seen across spans: '
            f'{", ".join(themes)}\n\nSynthesize a whole-work understanding. Return JSON: '
            '{"summary": "one tight paragraph on the whole work", '
            '"arc": [{"title": "movement name", "span": "sections a–b", "what_happens": "…"}], '
            '"themes": [{"name": "…", "arc": "how it is introduced, developed, and paid off"}], '
            '"significance": [{"element": "…", "why_matters": "what it sets up or resolves later"}]}')
    return _as_obj(await extraction._complete_json(_REDUCE_SYSTEM, user, max_tokens=3500))


def _recap_ladder(notes: list[dict]) -> list[dict]:
    """Cumulative 'story so far through section N' — bounded to each point (no later spoilers)."""
    ladder, acc = [], []
    for b in notes:
        if b["summary"]:
            acc.append(b["summary"])
        ladder.append({"through_section": b["last"], "so_far": " ".join(acc)})
    return ladder


def _total(book: dict) -> int:
    return book.get("word_count") or sum(c.get("words", 0) for c in (book.get("chapters") or []))


async def get(book_key: str) -> dict | None:
    if not db.ready():
        return None
    row = await db.fetchrow(
        "select summary, arc, themes, significance, recap, model, word_count, built_at "
        "from library_comprehension where book_key=$1",
        book_key)
    if not row:
        return None
    return {"summary": row["summary"], "arc": row["arc"] or [], "themes": row["themes"] or [],
            "significance": row["significance"] or [], "recap": row["recap"] or [],
            "_model": row["model"], "_word_count": row["word_count"], "_built_at": row["built_at"]}


async def _store(book_key: str, title: str, comp: dict, word_count: int, model: str | None = None) -> None:
    if not db.ready():
        return
    await db.execute(
        """insert into library_comprehension
             (book_key, title, summary, arc, themes, significance, recap, model, word_count, built_at)
           values ($1,$2,$3,$4,$5,$6,$7,$8,$9, now())
           on conflict (book_key) do update set title=excluded.title, summary=excluded.summary,
             arc=excluded.arc, themes=excluded.themes, significance=excluded.significance,
             recap=excluded.recap, model=excluded.model, word_count=excluded.word_count, built_at=now()""",
        book_key, title, comp.get("summary", ""), comp.get("arc", []), comp.get("themes", []),
        comp.get("significance", []), comp.get("recap", []), model or extraction._MODEL, word_count)


async def status(book: dict) -> tuple[str, dict | None]:
    """Where this book's comprehension stands, for the generate endpoint:
    ("ready", comp) when a build for the current text is cached; ("failed", None) when the last
    build failed within RETRY_AFTER; ("too_large", None) above _MAX_WORDS; else ("missing", None).
    A missing table or database reads as missing."""
    total = _total(book)
    if total > _MAX_WORDS:
        return "too_large", None
    try:
        cached = await get(book.get("slug") or "")
    except Exception:  # noqa: BLE001
        logger.exception("comprehension lookup failed")
        return "missing", None
    if not cached or cached.get("_word_count") != total:
        return "missing", None
    if cached.get("_model") == FAILED_MODEL:
        built = cached.get("_built_at")
        fresh = built and dt.datetime.now(dt.timezone.utc) - built < RETRY_AFTER
        return ("failed", None) if fresh else ("missing", None)
    return ("ready", cached) if cached.get("summary") else ("missing", None)


# --------------------------------------------------------------------------- #
# Inngest steps (webapp/inngest_app.py). Each loads the book itself from books.db, so only
# small JSON (span ranges, span notes) crosses a step boundary.
# --------------------------------------------------------------------------- #
async def _load(book_key: str) -> dict | None:
    return await asyncio.to_thread(reader._gen_book_sync, book_key)


async def step_plan(book_key: str) -> dict:
    """Decide whether a build is needed and split the work into spans of section numbers."""
    book = await _load(book_key)
    if not book or not book.get("chapters"):
        return {"status": "no_book"}
    state, _ = await status(book)
    if state != "missing":
        return {"status": state}
    total = _total(book)
    spans = [[b[0]["n"], b[-1]["n"]] for b in _batches(book["chapters"], total)]
    return {"status": "build", "title": book["title"], "total": total, "spans": spans}


async def step_map(book_key: str, span: list, i: int, n: int) -> dict:
    """One map call over sections span[0]..span[1]."""
    book = await _load(book_key)
    batch = [c for c in (book or {}).get("chapters") or [] if span[0] <= c["n"] <= span[1]]
    if not batch:
        raise RuntimeError(f"span {span} of {book_key} has no sections")
    return await _map_batch(book["title"], batch, i, n)


async def step_reduce(book_key: str, title: str, total: int, notes: list[dict]) -> dict:
    """Synthesize the span notes and cache the result. An empty synthesis raises so Inngest retries it."""
    reduced = await _reduce(title, notes)
    if not reduced.get("summary"):
        raise RuntimeError(f"comprehension reduce for {book_key} returned no summary")
    reduced["recap"] = _recap_ladder(notes)
    await _store(book_key, title, reduced, total)
    return {"status": "built", "spans": len(notes)}


async def mark_failed(book_key: str) -> None:
    """After the build has used its retries: a marker row, so generation degrades to the
    covered text for RETRY_AFTER instead of telling the teacher to wait for a build that failed."""
    book = await _load(book_key)
    if book:
        await _store(book_key, book.get("title", ""), {}, _total(book), model=FAILED_MODEL)


# --------------------------------------------------------------------------- #
# Covered-range retrieval (semantic passage selection when the range won't fit)
# --------------------------------------------------------------------------- #
def _passages(text: str, target_words: int = 350) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    out, cur, cw = [], [], 0
    for p in paras:
        cur.append(p); cw += len(p.split())
        if cw >= target_words:
            out.append("\n\n".join(cur)); cur, cw = [], 0
    if cur:
        out.append("\n\n".join(cur))
    return out


def select_covered_text(book: dict, covered_set: set, query: str, budget_words: int):
    """Covered chapters as (n, title, text) in reading order — whole text if it fits the budget,
    else the passages most relevant to `query` (semantic), still in reading order. Returns
    (passages, retrieved_bool). CPU embeddings — call in a threadpool."""
    covered = [c for c in (book.get("chapters") or []) if c["n"] in covered_set]
    if sum(c.get("words", 0) for c in covered) <= budget_words:
        return [(c["n"], c.get("title", ""), c["text"]) for c in covered], False
    chunks = [(c["n"], c.get("title", ""), p, len(p.split()))
              for c in covered for p in _passages(c["text"])]
    used, picked = 0, []
    for idx, _score in embed.topk(query, [x[2] for x in chunks], k=len(chunks)):
        if used + chunks[idx][3] > budget_words:
            continue
        picked.append(idx); used += chunks[idx][3]
        if used >= budget_words:
            break
    picked.sort(key=lambda i: (chunks[i][0], i))
    return [(chunks[i][0], chunks[i][1], chunks[i][2]) for i in picked], True


def recap_before(comp: dict | None, first_covered_n: int) -> str:
    """Cumulative 'story so far' up to just before the covered range starts (empty when the range
    begins at section 1)."""
    if not comp or first_covered_n <= 1:
        return ""
    best = ""
    for e in comp.get("recap", []):
        if e.get("through_section", 0) < first_covered_n:
            best = e.get("so_far", "")
    return best
