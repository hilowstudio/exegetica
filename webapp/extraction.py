"""Living Library core extraction (public-domain first, grounding-first).

Given a book's fetched full text, this: segments it into sections, derives a
transformative summary/themes/reading-level + per-section facts **from the text**,
proposes community learning objectives each **cited to a section**, runs a
citation-verify pass that drops unsupported ones, proposes spine alignments (reusing
the owned spine embeddings), and persists everything to Neon.

Grounding-first (docs/living-library-plan.md §10): every factual claim is derived from
the supplied text, never model memory. The verify pass checks each objective's cited
section actually supports it before it enters the shared community set.

The Anthropic calls and the network fetch can't run in a sandbox without egress; the
pure parts (encryption, spine alignment, JSON parsing, persistence) are unit-tested and
the whole pipeline is runnable via scripts/extract_book.py in an environment with a key.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid

from webapp import db
from webapp.sources import matching, text_processing as TP

logger = logging.getLogger("study-bible-web.extraction")

_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-sonnet-5")

# Shared system for the section-grounded steps (propose + verify). Keeping it identical
# across both lets the section text be a cacheable prefix reused between the two calls on
# the interactive path (propose then verify, seconds apart). See _section_user/_call.
_GROUNDING_SYSTEM = (
    "You are a careful curriculum assistant. Work ONLY from the supplied section text — do "
    "not use outside knowledge and do not fabricate. Reply with STRICT JSON only."
)


# --------------------------------------------------------------------------- #
# Anthropic one-shot JSON helper
# --------------------------------------------------------------------------- #
def _parse_json(text: str | None):
    """Best-effort JSON extraction from a model reply (tolerates code fences / prose)."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    text = text.strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        i = text.find(opener)
        if i != -1:
            try:
                return json.loads(text[i:])
            except Exception:  # noqa: BLE001
                j = text.rfind(closer)
                if j > i:
                    try:
                        return json.loads(text[i : j + 1])
                    except Exception:  # noqa: BLE001
                        pass
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return None


def _params(system, user, max_tokens: int = 4000, model: str | None = None) -> dict:
    """A `messages.create` param dict — the single request shape reused by the interactive
    path (_call, below) and the Batch API seeder (scripts/seed_batch.py). `user` is a plain
    string or a list of content blocks (so the section text can carry cache_control)."""
    return {"model": model or _MODEL, "max_tokens": max_tokens,
            "system": system, "messages": [{"role": "user", "content": user}]}


def _text_of(msg) -> str:
    return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")


async def _call(params: dict):
    """Run one param dict now and parse its JSON (the interactive path). None on failure.
    Dispatches by model: gemini-* → the Gemini provider (run in a thread; the SDK call is
    sync), everything else → Anthropic."""
    if str(params.get("model", "")).startswith("gemini"):
        import asyncio

        from webapp import gemini

        return await asyncio.to_thread(gemini.complete_json_sync, params)

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()  # uses ANTHROPIC_API_KEY
    try:
        return _parse_json(_text_of(await client.messages.create(**params)))
    except Exception:  # noqa: BLE001
        logger.exception("extraction model call failed")
        return None
    finally:
        import contextlib

        with contextlib.suppress(Exception):
            await client.close()


async def _complete_json(system: str, user: str, max_tokens: int = 4000, model: str | None = None):
    """One-shot structured (JSON) completion. Returns the parsed object or None."""
    return await _call(_params(system, user, max_tokens, model))


# --------------------------------------------------------------------------- #
# Tier-1 encryption (AES-GCM; key derived from the LIBRARY_ENC_KEY secret)
# --------------------------------------------------------------------------- #
def _enc_key() -> bytes | None:
    raw = os.environ.get("LIBRARY_ENC_KEY")
    if not raw:
        return None
    return hashlib.sha256(raw.encode("utf-8")).digest()  # 32 bytes


def encrypt_text(plaintext: str) -> tuple[bytes, bytes]:
    """AES-GCM encrypt; returns (nonce, ciphertext+tag). Raises if no key is set."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _enc_key()
    if key is None:
        raise RuntimeError("LIBRARY_ENC_KEY is not set — cannot store private source text")
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce, ct


def decrypt_text(nonce: bytes, ciphertext: bytes) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _enc_key()
    if key is None:
        raise RuntimeError("LIBRARY_ENC_KEY is not set")
    return AESGCM(key).decrypt(bytes(nonce), bytes(ciphertext), None).decode("utf-8")


# --------------------------------------------------------------------------- #
# Grounding-first derivation (from the source text, never model memory)
# --------------------------------------------------------------------------- #
def _excerpt(s: str, n: int) -> str:
    s = (s or "").strip()
    return s[:n]


def derive_params(meta: dict, sections: list[dict]) -> dict:
    title = (meta or {}).get("title") or "this work"
    toc = "\n".join(f"{s['section_number']}. {s['title']}" for s in sections[:60])
    sample = "\n\n".join(f"[{s['section_number']}] {_excerpt(s['text'], 800)}" for s in sections[:8])
    user = (
        f"BOOK: {title}\n\nTABLE OF CONTENTS (detected):\n{toc}\n\n"
        f"EXCERPTS (grounding):\n{sample}\n\n"
        "Return JSON: {\"summary\": string|null (2-4 sentences, transformative — your own "
        "words, no verbatim copying), \"themes\": string[] (3-6), \"reading_level\": "
        "string|null (e.g. 'Grade 7-9'), \"confidence\": \"high\"|\"medium\"|\"low\"}."
    )
    return _params(_GROUNDING_SYSTEM, user, max_tokens=1500)


def parse_derivative(out) -> dict:
    if not isinstance(out, dict):
        return {}
    return {
        "summary": out.get("summary"),
        "themes": [t for t in (out.get("themes") or []) if isinstance(t, str)][:6],
        "reading_level": out.get("reading_level"),
        "confidence": out.get("confidence"),
    }


async def derive_book(meta: dict, sections: list[dict]) -> dict:
    """Summary + themes + reading level, grounded in the text. Never fabricates; {} on
    failure. (Interactive path; the seeder builds the same request via derive_params.)"""
    return parse_derivative(await _call(derive_params(meta, sections)))


def _section_user(section: dict, instruction: str, cache: bool) -> list[dict]:
    """User content = the section text (a cacheable prefix, so propose and verify reuse it
    on the interactive path) followed by the task instruction. `cache=False` for the Batch
    API, where propose and verify land in separate batches and the 5-min cache never hits."""
    body = _excerpt(section["text"], 6000)
    block = {"type": "text", "text": f"SECTION {section['section_number']}: {section['title']}\n\nTEXT:\n{body}"}
    if cache:
        block["cache_control"] = {"type": "ephemeral"}
    return [block, {"type": "text", "text": instruction}]


def propose_params(meta: dict, section: dict, per_section: int = 3, cache: bool = True) -> dict:
    title = (meta or {}).get("title") or "this work"
    instruction = (
        f"BOOK: {title}\nFrom the section text above, write up to {per_section} grounded, "
        "teachable learning objectives — each supported by THIS section, no outside knowledge "
        "or invented facts. Return JSON: {\"objectives\": [ {\"text\": string (e.g. 'Explain "
        "how ...'), \"citation\": string (the specific passage/detail it rests on)} ] }. If the "
        "section can't support a solid objective, return an empty list."
    )
    return _params(_GROUNDING_SYSTEM, _section_user(section, instruction, cache), max_tokens=1200)


def verify_params(section: dict, objectives: list[dict], cache: bool = True) -> dict:
    listing = "\n".join(
        f"{i}. {o['text']}  (cited: {o.get('citation') or '(none)'})" for i, o in enumerate(objectives)
    )
    instruction = (
        "You are an adversarial fact-checker. For EACH numbered objective below, decide ONLY "
        "from the section text above whether the text SUPPORTS it (the facts it presupposes are "
        "actually present). Be strict: unsupported or fabricated → false.\n\n"
        f"OBJECTIVES:\n{listing}\n\n"
        "Return JSON: {\"verdicts\": [ {\"index\": int, \"supported\": true|false} ] }."
    )
    return _params(_GROUNDING_SYSTEM, _section_user(section, instruction, cache), max_tokens=600)


def parse_proposals(section_number, out) -> list[dict]:
    return [
        {"section_number": section_number, "text": o["text"], "citation": o.get("citation")}
        for o in ((out or {}).get("objectives", []) if isinstance(out, dict) else [])
        if isinstance(o, dict) and o.get("text")
    ]


async def propose_objectives(meta: dict, sections: list[dict], per_section: int = 3) -> list[dict]:
    """Per-section grounded learning objectives, each CITED to its section. Community
    (shared) candidates — they enter 'proposed' and must pass verify. (Interactive path;
    the Batch API seeder builds the same requests via propose_params.)"""
    proposals: list[dict] = []
    for s in sections:
        if len(_excerpt(s["text"], 6000)) < TP._MIN_SECTION_CHARS:
            continue
        out = await _call(propose_params(meta, s, per_section))
        proposals.extend(parse_proposals(s["section_number"], out))
    return proposals


def keep_verified(objectives: list[dict], out) -> list[dict]:
    """Filter one section's proposed objectives by a verify response's per-index verdicts."""
    ok = {v.get("index") for v in ((out or {}).get("verdicts", []) if isinstance(out, dict) else [])
          if v.get("supported") is True}
    return [o for i, o in enumerate(objectives) if i in ok]


async def verify_objectives(objectives: list[dict], sections_by_num: dict[int, dict]) -> list[dict]:
    """Citation-verify gate: keep an objective only if its section actually supports it. ONE
    call per section verifies all that section's objectives together (was one-per-objective).
    The source text is the reviewer — verification is retrieval, not expertise."""
    from collections import defaultdict

    by_section: dict = defaultdict(list)
    for o in objectives:
        by_section[o.get("section_number")].append(o)
    kept: list[dict] = []
    for sn, objs in by_section.items():
        sec = sections_by_num.get(sn)
        if not sec:
            continue
        out = await _call(verify_params(sec, objs))
        kept.extend(keep_verified(objs, out))
    return kept


# --------------------------------------------------------------------------- #
# Spine alignment (reuse the owned spine embeddings — offline, no external service)
# --------------------------------------------------------------------------- #
_ALIGN_LEVEL = {
    "subject": "subject",
    "strand": "sub_subject",
    "topic": "topic",
    "sub-topic": "sub_topic",
    "objective": "objective",
}


def align_to_spine(book_text: str, sections: list[dict], book_hits: int = 4, section_hits: int = 1) -> list[dict]:
    """Propose spine alignments: book-level (section_number None) + section-level.
    Uses generator.search_standards (local hybrid semantic+fuzzy search). Returns
    [{section_number, spine_level, spine_node_id}] — section_number maps to a section_id
    at persist time. Never raises."""
    try:
        from webapp import generator
    except Exception:  # noqa: BLE001
        return []
    seen: set = set()
    out: list[dict] = []

    def add(hit: dict, section_number):
        lvl = _ALIGN_LEVEL.get(hit.get("level"))
        if not lvl:
            return
        nid = (hit.get("ids") or {}).get(lvl)
        if not nid:
            return
        key = (section_number, lvl, nid)
        if key in seen:
            return
        seen.add(key)
        out.append({"section_number": section_number, "spine_level": lvl, "spine_node_id": nid})

    for h in generator.search_standards(_excerpt(book_text, 2000), 12)[:book_hits]:
        add(h, None)
    for s in sections or []:
        q = (s.get("title", "") + " " + _excerpt(s.get("text", ""), 400)).strip()
        for h in generator.search_standards(q, 6)[:section_hits]:
            add(h, s.get("section_number"))
    return out


# --------------------------------------------------------------------------- #
# Persistence & stepped orchestration
#
# The quillnext batched-steps + transient-holding pattern: the fetched multi-MB text
# lives in library_extractions.full_text_raw BETWEEN steps, so nothing large crosses an
# Inngest step boundary and no single step runs long. A long book just becomes more
# `objectives-{b}` steps. full_text_raw only ever holds PD / us_clear text; NULLed at
# finalize. (In-copyright uploads use the encrypted tier-1 path — layer 3.)
# --------------------------------------------------------------------------- #
# Sources whose works are US public domain (safe to share full_text). Gutenberg only.
_US_CLEAR_SOURCES = {"gutenberg"}
# Sections per objectives step — keeps each step's Claude calls bounded.
OBJECTIVES_BATCH = 2

# Provenance tier for canonical-copy selection: a trusted, clean PD source outranks any
# user upload, so a book we can fetch ourselves is never superseded by someone's PDF.
_TRUSTED_SOURCE_TIER = 3
_UPLOAD_TIER = 2
# A newer same-tier copy must beat the incumbent's quality by at least this margin to be
# auto-promoted to canonical; a smaller gap is "borderline" and held (copy kept private).
_PROMOTE_MARGIN = 0.10


async def verify_identity(meta: dict, text: str) -> dict:
    """Grounding-first identity check for an upload: does the extracted text actually BELONG
    to the work the uploader claims? Judges the WORK, not the edition — a different
    translation/abridgment/printing of the same work is still a match — so it rejects only
    a genuinely different work (or non-prose). Returns
    {match: 'yes'|'no'|'unsure', detected: str, confidence: 'high'|'medium'|'low', reason: str}.
    Fails OPEN (returns 'unsure') on any model/parse error, so the gate never wrongly blocks
    a legitimate upload because of an infrastructure hiccup."""
    title = (meta or {}).get("title") or ""
    author = (((meta or {}).get("authors") or [""]) or [""])[0] or ""
    n = len(text)
    samples = "\n\n".join([
        f"[opening]\n{_excerpt(text, 1500)}",
        f"[middle]\n{_excerpt(text[n // 2:], 1200)}" if n > 4000 else "",
        f"[near end]\n{_excerpt(text[-1500:], 1200)}" if n > 4000 else "",
    ]).strip()
    system = (
        "You verify whether an uploaded text is the work its uploader claims, to catch "
        "mislabeled uploads before they are processed. Judge the WORK, not the edition: a "
        "different translation, abridgment, annotated edition, or printing of the SAME work "
        "is a MATCH ('yes'). Answer 'no' ONLY when the text is clearly a DIFFERENT work than "
        "claimed, or is not coherent readable prose. When the samples are too thin or "
        "genuinely ambiguous, answer 'unsure'. Reply with STRICT JSON only."
    )
    user = (
        f"CLAIMED TITLE: {title}\nCLAIMED AUTHOR: {author}\n\n"
        f"SAMPLES FROM THE UPLOADED TEXT:\n{samples}\n\n"
        "Return JSON: {\"match\": \"yes\"|\"no\"|\"unsure\", \"detected\": string (what work "
        "this actually appears to be, or \"\"), \"confidence\": \"high\"|\"medium\"|\"low\", "
        "\"reason\": string (one sentence)}."
    )
    out = await _complete_json(system, user, max_tokens=300)
    if not isinstance(out, dict) or out.get("match") not in ("yes", "no", "unsure"):
        return {"match": "unsure", "detected": "", "confidence": "low", "reason": "verifier unavailable"}
    return {
        "match": out["match"],
        "detected": out.get("detected") or "",
        "confidence": out.get("confidence") or "low",
        "reason": out.get("reason") or "",
    }


def compute_quality(text: str, sections: list[dict]) -> dict:
    """A cheap, mechanical 0..1 quality score for a copy — used to pick the best copy of a
    book across uploads/sources. No model call. Rewards clean structure and clean text and
    penalizes the single-'Full text' blob and OCR/mojibake garble."""
    text = text or ""
    n_chars = len(text)
    n = len(sections)
    single_blob = n == 1 and (sections[0].get("title") == "Full text")
    structure = 0.35 if (single_blob or n == 0) else (1.0 if 2 <= n <= 60 else 0.6)
    nonspace = sum(1 for c in text if not c.isspace()) or 1
    alpha_ratio = sum(1 for c in text if c.isalpha()) / nonspace
    garble_ratio = (text.count("�") + text.count("�")) / max(n_chars, 1)
    integrity = max(0.0, min(1.0, alpha_ratio / 0.8)) - min(0.5, garble_ratio * 200)
    integrity = max(0.0, integrity)
    length = min(1.0, n_chars / 30000)  # most books clear this; short fragments score lower
    score = round(0.4 * structure + 0.4 * integrity + 0.2 * length, 3)
    return {
        "score": score,
        "signals": {"sections": n, "chars": n_chars, "alpha_ratio": round(alpha_ratio, 3),
                    "garble_ratio": round(garble_ratio, 5), "single_blob": single_blob},
    }


def book_dedup_key(meta: dict) -> str:
    isbn = re.sub(r"[^0-9Xx]", "", (meta or {}).get("isbn") or "")
    if isbn:
        return isbn
    return "t:" + matching.normalize((meta or {}).get("title")) + "|" + matching.author_last_name(
        ((meta or {}).get("authors") or [""])[0]
    )


async def ensure_extraction_row(meta: dict, user_id=None):
    """Find-or-create the shared catalog row (status 'pending'); returns its id."""
    dedup = book_dedup_key(meta)
    row = await db.fetchrow(
        """insert into library_extractions (kind, dedup_key, title, creator, status, seeded_by_user_id)
           values ('book', $1, $2, $3, 'pending', $4)
           on conflict (kind, dedup_key) do update set updated_at = now()
           returning id""",
        dedup, (meta.get("title") or ""), ((meta.get("authors") or [""])[0] or ""), user_id,
    )
    return row["id"]


async def _section_id_map(exid) -> dict:
    rows = await db.fetch("select number, id from library_sections where extraction_id = $1", exid)
    return {int(r["number"]): r["id"] for r in rows if r["number"] and str(r["number"]).isdigit()}


async def _read_source_text(exid, user_id=None) -> str | None:
    """The grounding text for the derive/objectives/finalize steps. For a PD fetch it's
    the transient full_text_raw (public); for an upload it's the uploader's DECRYPTED
    tier-1 copy (private, in-copyright — never shared)."""
    if user_id:
        row = await db.fetchrow(
            "select nonce, ciphertext from library_source_texts where extraction_id=$1 and user_id=$2",
            exid, uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id,
        )
        if row:
            try:
                return decrypt_text(row["nonce"], row["ciphertext"])
            except Exception:  # noqa: BLE001
                logger.exception("tier-1 decrypt failed")
                return None
    return await db.fetchval("select full_text_raw from library_extractions where id=$1", exid)


async def _read_toc(exid) -> list[str] | None:
    """The stored published TOC (EPUB nav / PDF outline / embedded Contents), if any."""
    toc = await db.fetchval("select toc from library_extractions where id=$1", exid)
    return toc if isinstance(toc, list) and toc else None


async def step_fetch(exid, meta: dict) -> dict:
    """Discover + fetch a PD full text and PARK it in full_text_raw (never returned).
    Sets us_clear / public_domain / source. Returns a small summary."""
    hits = await registry.discover_all(meta)
    got = await registry.fetch_first_available(hits)
    if not got:
        await db.execute(
            "update library_extractions set status='failed', error='no public-domain source found', updated_at=now() where id=$1",
            exid,
        )
        return {"ok": False, "reason": "no_source"}
    us_clear = got["source"] in _US_CLEAR_SOURCES
    q = compute_quality(got["text"], TP.segment_into_chapters(got["text"]))
    await db.execute(
        """update library_extractions set
             full_text_raw=$2, source_meta=$3, public_domain=true, us_clear=$4,
             grounding='source_text', status='extracting', error=null,
             canonical_source=$5, canonical_tier=$6, quality_score=$7, updated_at=now()
           where id=$1""",
        exid, got["text"], {"source": got["source"], "source_id": got["source_id"]}, us_clear,
        got["source"], _TRUSTED_SOURCE_TIER, q["score"],
    )
    return {"ok": True, "source": got["source"], "us_clear": us_clear, "chars": len(got["text"])}


async def step_ingest_upload(exid, r2_object_key: str, source_format: str, user_id, acquisition: str, meta: dict | None = None) -> dict:
    """Upload path: fetch the R2 object, extract text, verify it's the claimed work, encrypt
    it into the uploader's PRIVATE tier-1 vault, then delete the R2 object. In-copyright →
    us_clear stays false (full_text never shared). Nothing plaintext touches the shared catalog."""
    from webapp import filetext, r2

    meta = meta or {}
    data = await r2.get_bytes_async(r2_object_key)
    if not data:
        await db.execute(
            "update library_extractions set status='failed', error='upload not found', updated_at=now() where id=$1",
            exid,
        )
        return {"ok": False, "reason": "no_object"}
    text = filetext.extract_text(data, source_format)
    if not filetext.looks_full(text):
        # not full (scanned/empty/DRM'd) — keep nothing; discard the original.
        await db.execute(
            "update library_extractions set status='failed', error='could not extract text (scanned or empty file?)', updated_at=now() where id=$1",
            exid,
        )
        await r2.delete_async(r2_object_key)
        return {"ok": False, "reason": "not_full"}
    toc = filetext.extract_toc(data, source_format) or None  # EPUB nav / PDF outline

    # --- Identity gate (grounding-first): reject a copy that isn't the claimed work ---
    ident = await verify_identity(meta, text)
    if ident["match"] == "no":
        detected = f" (looks like: {ident['detected']})" if ident.get("detected") else ""
        await db.execute(
            "update library_extractions set verify_verdict='rejected', verify_detail=$2, updated_at=now() where id=$1",
            exid, ident,
        )
        # Only fail the shared row if nothing good is already published there.
        await db.execute(
            "update library_extractions set status='failed', "
            "error=$2 where id=$1 and status <> 'extracted'",
            exid, f"upload does not match the stated title/author{detected}",
        )
        await r2.delete_async(r2_object_key)  # never store a mislabeled copy
        return {"ok": False, "reason": "identity_mismatch", "detail": ident}

    # --- Quality score for canonical-copy selection ---
    sections = TP.segment_into_chapters(text, toc)
    q = compute_quality(text, sections)

    # --- Supersession: best verified copy wins (auto-promote clear wins, review borderline) ---
    cur = await db.fetchrow(
        "select status, canonical_tier, coalesce(quality_score, 0) qs from library_extractions where id=$1", exid,
    )
    incumbent_tier = (cur["canonical_tier"] if cur else None) or 0
    incumbent_q = float(cur["qs"]) if cur else 0.0
    already = bool(cur) and cur["status"] == "extracted"

    if not already or incumbent_tier < _UPLOAD_TIER:
        outcome = "promote"                                    # nothing canonical yet, or a weaker incumbent
    elif incumbent_tier > _UPLOAD_TIER:
        outcome = "superseded"                                 # a trusted PD copy is canonical; uploads can't win
    elif q["score"] >= incumbent_q + _PROMOTE_MARGIN:
        outcome = "promote"                                    # same tier, a clear quality win
    elif q["score"] <= incumbent_q - _PROMOTE_MARGIN:
        outcome = "superseded"                                 # same tier, clearly worse → keep private
    else:
        outcome = "review"                                     # same tier, within the margin → human decides

    # Always keep the uploader's own verified copy in their PRIVATE tier-1 vault
    # (accessibility): a copy that doesn't win canonical is still theirs to build from.
    review_status = "pending" if outcome == "review" else ("promoted" if outcome == "promote" else "none")
    nonce, ct = encrypt_text(text)
    await db.execute(
        """insert into library_source_texts
             (user_id, extraction_id, nonce, ciphertext, char_count, source_format, extraction_full,
              acquisition, quality_score, review_status)
           values ($1, $2, $3, $4, $5, $6, true, $7, $8, $9)
           on conflict (user_id, extraction_id) do update set
             nonce=excluded.nonce, ciphertext=excluded.ciphertext, char_count=excluded.char_count,
             source_format=excluded.source_format, acquisition=excluded.acquisition,
             quality_score=excluded.quality_score, review_status=excluded.review_status, updated_at=now()""",
        uuid.UUID(str(user_id)), exid, nonce, ct, len(text), source_format, acquisition,
        q["score"], review_status,
    )
    await r2.delete_async(r2_object_key)  # verified-full extraction done → discard the original

    if outcome == "promote":
        await db.execute(
            """update library_extractions set
                 grounding='source_text', status='extracting', error=null,
                 canonical_source=$2, canonical_tier=$3, quality_score=$4,
                 verify_verdict='accepted', verify_detail=$5, toc=$6, updated_at=now()
               where id=$1""",
            exid, f"upload:{user_id}", _UPLOAD_TIER, q["score"], {"identity": ident, "quality": q}, toc,
        )
        return {"ok": True, "derive": True, "chars": len(text), "quality": q["score"]}
    # Kept private (superseded or awaiting review): don't disturb the canonical derivative.
    return {"ok": True, "derive": False, "reason": outcome, "quality": q["score"]}


async def step_derive(exid, meta: dict, user_id=None) -> dict:
    """Read the source text (PD raw or private tier-1); segment; derive the book summary/
    themes; persist the derivative and the section tree (replacing prior)."""
    raw = await _read_source_text(exid, user_id)
    if not raw:
        return {"sections": 0, "reason": "no_source"}
    sections = TP.segment_into_chapters(raw, await _read_toc(exid))
    derivative = await derive_book(meta, sections)
    derivative["table_of_contents"] = [{"n": s["section_number"], "title": s["title"]} for s in sections]
    await db.execute("update library_extractions set derivative=$2, updated_at=now() where id=$1", exid, derivative)
    await db.execute("delete from library_sections where extraction_id=$1", exid)
    for s in sections:
        await db.execute(
            "insert into library_sections (extraction_id, position, label_type, number, title) values ($1,$2,'chapter',$3,$4)",
            exid, s["section_number"], str(s["section_number"]), s["title"],
        )
    # reset the grounded community objective set for a fresh derivation
    await db.execute(
        "delete from library_objectives where extraction_id=$1 and user_id is null and provenance='seed_grounded'",
        exid,
    )
    return {"sections": len(sections)}


async def step_objectives(exid, meta: dict, batch_index: int, batch_size: int = OBJECTIVES_BATCH, user_id=None) -> dict:
    """Propose + citation-verify grounded community objectives for ONE batch of sections
    (re-reading the source text). Idempotent per batch. Returns {"added": n}."""
    raw = await _read_source_text(exid, user_id)
    if not raw:
        return {"added": 0}
    sections = TP.segment_into_chapters(raw)
    batch = sections[batch_index * batch_size : batch_index * batch_size + batch_size]
    if not batch:
        return {"added": 0}
    proposed = await propose_objectives(meta, batch)
    verified = await verify_objectives(proposed, {s["section_number"]: s for s in sections})
    secmap = await _section_id_map(exid)
    batch_ids = [secmap[s["section_number"]] for s in batch if s["section_number"] in secmap]
    if batch_ids:  # idempotent: clear this batch's objectives before inserting (safe on retry)
        await db.execute(
            "delete from library_objectives where extraction_id=$1 and user_id is null "
            "and provenance='seed_grounded' and section_id = any($2::uuid[])",
            exid, batch_ids,
        )
    for o in verified:
        await db.execute(
            """insert into library_objectives (extraction_id, user_id, section_id, text, citation, provenance, status)
               values ($1, null, $2, $3, $4, 'seed_grounded', 'accepted')""",
            exid, secmap.get(o.get("section_number")), o["text"], o.get("citation"),
        )
    return {"added": len(verified)}


async def step_finalize(exid, user_id=None) -> dict:
    """Spine-align, publish full_text ONLY if us_clear (PD), clear the transient raw, mark
    extracted. For uploads (user_id set, in-copyright) full_text is never published — the
    text stays in the private tier-1 vault; the community gets only the derivative."""
    raw = await _read_source_text(exid, user_id)
    if not raw:
        return {"status": "no_source"}
    sections = TP.segment_into_chapters(raw)
    alignments = align_to_spine(raw, sections)
    secmap = await _section_id_map(exid)
    await db.execute("delete from library_alignments where extraction_id=$1 and source='auto'", exid)
    for a in alignments:
        try:
            await db.execute(
                """insert into library_alignments (extraction_id, section_id, spine_level, spine_node_id, status, source)
                   values ($1, $2, $3, $4, 'proposed', 'auto') on conflict do nothing""",
                exid, secmap.get(a.get("section_number")), a["spine_level"], a["spine_node_id"],
            )
        except Exception:  # noqa: BLE001 — spine node id not present; skip
            pass
    if user_id:  # upload: NEVER publish the private in-copyright text
        await db.execute(
            "update library_extractions set full_text_raw=null, status='extracted', extracted_at=now(), updated_at=now() where id=$1",
            exid,
        )
    else:  # PD fetch: publish full_text only when us_clear (the column), then drop the transient raw
        await db.execute(
            """update library_extractions set
                 full_text = case when us_clear then $2 else null end,
                 full_text_raw = null, status='extracted', extracted_at=now(), updated_at=now()
               where id=$1""",
            exid, raw,
        )
    return {"status": "extracted", "alignments": len(alignments)}


# --------------------------------------------------------------------------- #
# Orchestrator (non-durable; the Inngest function runs the same steps as memoized
# ctx.step.run calls — see webapp/inngest_app.py)
# --------------------------------------------------------------------------- #
async def extraction_summary(exid) -> dict:
    row = await db.fetchrow(
        """select e.status, e.us_clear,
             (select count(*) from library_sections   s where s.extraction_id=e.id) sections,
             (select count(*) from library_objectives o where o.extraction_id=e.id and o.user_id is null) objectives,
             (select count(*) from library_alignments a where a.extraction_id=e.id) alignments
           from library_extractions e where e.id=$1""",
        exid,
    )
    return dict(row) if row else {}


async def run_all(exid, meta: dict, batch_size: int = OBJECTIVES_BATCH) -> dict:
    """Run every step in sequence (for the CLI runner + tests). No durability/memoization —
    the Inngest function is the durable version."""
    f = await step_fetch(exid, meta)
    if not f.get("ok"):
        return {"status": "failed", "reason": f.get("reason"), "extraction_id": str(exid)}
    d = await step_derive(exid, meta)
    n = int(d.get("sections", 0))
    for b in range((n + batch_size - 1) // batch_size):
        await step_objectives(exid, meta, b, batch_size)
    await step_finalize(exid)
    summary = await extraction_summary(exid)
    summary["extraction_id"] = str(exid)
    return summary
