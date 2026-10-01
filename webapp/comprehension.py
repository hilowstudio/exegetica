"""Whole-work comprehension layer for the Living Library generator (Phase 2).

Large works can't be fed to the model whole, so we pre-build an analytical understanding of the
ENTIRE work — summary, arc, themes, significant (load-bearing) elements, and a cumulative recap
ladder — via a batched map-reduce over the text, cached in Neon (library_comprehension). Built
lazily on first generation against a large book, using the server ANTHROPIC key (a shared, cached
artifact, not per-teacher BYOK). Small books never need this — they're read whole at generation
time. See docs/living-library-generation-plan.md.

Also provides covered-range passage selection (semantic retrieval via webapp.embed) for when the
covered range itself is too large to include verbatim.
"""
from __future__ import annotations

import asyncio
import logging
import math

from webapp import db, embed, extraction

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
_MAP_CONCURRENCY = 5


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


async def build(book: dict) -> dict:
    """Map-reduce the whole work into a comprehension dict (server LLM key; bounded to ~40 map calls)."""
    chapters = book.get("chapters") or []
    total = book.get("word_count") or sum(c.get("words", 0) for c in chapters)
    batches = _batches(chapters, total)
    sem = asyncio.Semaphore(_MAP_CONCURRENCY)

    async def one(i, b):
        async with sem:
            return await _map_batch(book["title"], b, i, len(batches))

    notes = list(await asyncio.gather(*[one(i, b) for i, b in enumerate(batches)]))
    reduced = await _reduce(book["title"], notes)
    reduced["recap"] = _recap_ladder(notes)
    reduced["_word_count"] = total
    return reduced


async def get(book_key: str) -> dict | None:
    if not db.ready():
        return None
    row = await db.fetchrow(
        "select summary, arc, themes, significance, recap, word_count from library_comprehension where book_key=$1",
        book_key)
    if not row:
        return None
    return {"summary": row["summary"], "arc": row["arc"] or [], "themes": row["themes"] or [],
            "significance": row["significance"] or [], "recap": row["recap"] or [],
            "_word_count": row["word_count"]}


async def _store(book_key: str, title: str, comp: dict, word_count: int) -> None:
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
        comp.get("significance", []), comp.get("recap", []), extraction._MODEL, word_count)


async def ensure(book: dict, rebuild: bool = False) -> dict | None:
    """Cached comprehension for this book, building + caching it if missing or stale (word_count
    guard). Returns None if it can't be built (no LLM key / failure) so the caller can degrade."""
    key = book.get("slug") or ""
    total = book.get("word_count") or sum(c.get("words", 0) for c in (book.get("chapters") or []))
    if not rebuild:
        cached = await get(key)
        if cached and cached.get("_word_count") == total:
            return cached
    try:
        comp = await build(book)
    except Exception:  # noqa: BLE001
        logger.exception("comprehension build failed for %s", key)
        return None
    if not comp.get("summary"):
        return None
    try:                                       # caching is best-effort — a store failure (e.g. the
        await _store(key, book.get("title", ""), comp, total)   # table not migrated yet) must not
    except Exception:  # noqa: BLE001          # break generation; we just use the fresh (uncached) comp
        logger.exception("comprehension store failed for %s", key)
    return comp


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
