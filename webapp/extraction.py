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

_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-opus-4-8")


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


async def _complete_json(system: str, user: str, max_tokens: int = 4000, model: str | None = None):
    """One-shot structured (JSON) completion. Returns the parsed object or None."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()  # uses ANTHROPIC_API_KEY
    try:
        msg = await client.messages.create(
            model=model or _MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
        return _parse_json(text)
    except Exception:  # noqa: BLE001
        logger.exception("extraction model call failed")
        return None
    finally:
        import contextlib

        with contextlib.suppress(Exception):
            await client.close()


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


async def derive_book(meta: dict, sections: list[dict]) -> dict:
    """Summary + themes + reading level, grounded in the text (section titles + a
    sample per section). Never fabricates; returns {} on failure."""
    title = (meta or {}).get("title") or "this work"
    toc = "\n".join(f"{s['section_number']}. {s['title']}" for s in sections[:60])
    sample = "\n\n".join(f"[{s['section_number']}] {_excerpt(s['text'], 800)}" for s in sections[:8])
    system = (
        "You are a careful curriculum assistant. Work ONLY from the supplied text of a "
        "book — do not use outside knowledge and do not fabricate. If the text is "
        "insufficient, say so with null. Reply with STRICT JSON only."
    )
    user = (
        f"BOOK: {title}\n\nTABLE OF CONTENTS (detected):\n{toc}\n\n"
        f"EXCERPTS (grounding):\n{sample}\n\n"
        "Return JSON: {\"summary\": string|null (2-4 sentences, transformative — your own "
        "words, no verbatim copying), \"themes\": string[] (3-6), \"reading_level\": "
        "string|null (e.g. 'Grade 7-9'), \"confidence\": \"high\"|\"medium\"|\"low\"}."
    )
    out = await _complete_json(system, user, max_tokens=1500)
    if not isinstance(out, dict):
        return {}
    return {
        "summary": out.get("summary"),
        "themes": [t for t in (out.get("themes") or []) if isinstance(t, str)][:6],
        "reading_level": out.get("reading_level"),
        "confidence": out.get("confidence"),
    }


async def propose_objectives(meta: dict, sections: list[dict], per_section: int = 3) -> list[dict]:
    """Per-section grounded learning objectives, each CITED to its section. Community
    (shared) candidates — they enter 'proposed' and must pass verify."""
    title = (meta or {}).get("title") or "this work"
    proposals: list[dict] = []
    for s in sections:
        body = _excerpt(s["text"], 6000)
        if len(body) < TP._MIN_SECTION_CHARS:
            continue
        system = (
            "You write learning objectives for a section of a book, grounded ONLY in the "
            "supplied section text. Do NOT use outside knowledge; do NOT invent characters, "
            "plot points, or facts not present in the text. Each objective must be a real, "
            "teachable outcome supported by THIS section. STRICT JSON only."
        )
        user = (
            f"BOOK: {title}\nSECTION {s['section_number']}: {s['title']}\n\nTEXT:\n{body}\n\n"
            f"Return JSON: {{\"objectives\": [ up to {per_section} × "
            "{\"text\": string (a learning objective, e.g. 'Explain how ...'), "
            "\"citation\": string (the specific passage/detail in THIS section it rests on) } ] }. "
            "If the section can't support a solid objective, return an empty list."
        )
        out = await _complete_json(system, user, max_tokens=1200)
        for o in (out or {}).get("objectives", []) if isinstance(out, dict) else []:
            if isinstance(o, dict) and o.get("text"):
                proposals.append(
                    {"section_number": s["section_number"], "text": o["text"], "citation": o.get("citation")}
                )
    return proposals


async def verify_objectives(objectives: list[dict], sections_by_num: dict[int, dict]) -> list[dict]:
    """Citation-verify gate: keep an objective only if its cited section actually
    supports it. The source text is the reviewer — verification is retrieval, not
    expertise. Anything unverifiable is dropped."""
    kept: list[dict] = []
    for o in objectives:
        sec = sections_by_num.get(o.get("section_number"))
        if not sec:
            continue
        system = (
            "You are an adversarial fact-checker. Decide ONLY from the supplied section text "
            "whether it SUPPORTS the claim in the objective (the facts it presupposes are "
            "actually in the text). Be strict: unsupported or fabricated → false. STRICT JSON only."
        )
        user = (
            f"SECTION TEXT:\n{_excerpt(sec['text'], 6000)}\n\n"
            f"OBJECTIVE: {o['text']}\nCITED: {o.get('citation') or '(none)'}\n\n"
            "Return JSON: {\"supported\": true|false, \"reason\": string}."
        )
        out = await _complete_json(system, user, max_tokens=400)
        if isinstance(out, dict) and out.get("supported") is True:
            kept.append(o)
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
    await db.execute(
        """update library_extractions set
             full_text_raw=$2, source_meta=$3, public_domain=true, us_clear=$4,
             grounding='source_text', status='extracting', error=null, updated_at=now()
           where id=$1""",
        exid, got["text"], {"source": got["source"], "source_id": got["source_id"]}, us_clear,
    )
    return {"ok": True, "source": got["source"], "us_clear": us_clear, "chars": len(got["text"])}


async def step_ingest_upload(exid, r2_object_key: str, source_format: str, user_id, acquisition: str) -> dict:
    """Upload path: fetch the R2 object, extract text, verify it's full, encrypt it into
    the uploader's PRIVATE tier-1 vault, then delete the R2 object. In-copyright → us_clear
    stays false (full_text never shared). Nothing plaintext ever touches the shared catalog."""
    from webapp import filetext, r2

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
    nonce, ct = encrypt_text(text)
    await db.execute(
        """insert into library_source_texts
             (user_id, extraction_id, nonce, ciphertext, char_count, source_format, extraction_full, acquisition)
           values ($1, $2, $3, $4, $5, $6, true, $7)
           on conflict (user_id, extraction_id) do update set
             nonce=excluded.nonce, ciphertext=excluded.ciphertext, char_count=excluded.char_count,
             source_format=excluded.source_format, acquisition=excluded.acquisition, updated_at=now()""",
        uuid.UUID(str(user_id)), exid, nonce, ct, len(text), source_format, acquisition,
    )
    # Leave us_clear alone (a fresh upload row defaults false; don't downgrade a PD row);
    # finalize guarantees an upload never publishes full_text regardless.
    await db.execute(
        "update library_extractions set grounding='source_text', status='extracting', error=null, updated_at=now() where id=$1",
        exid,
    )
    await r2.delete_async(r2_object_key)  # verified-full extraction done → discard the original
    return {"ok": True, "chars": len(text)}


async def step_derive(exid, meta: dict, user_id=None) -> dict:
    """Read the source text (PD raw or private tier-1); segment; derive the book summary/
    themes; persist the derivative and the section tree (replacing prior)."""
    raw = await _read_source_text(exid, user_id)
    if not raw:
        return {"sections": 0, "reason": "no_source"}
    sections = TP.segment_into_chapters(raw)
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
