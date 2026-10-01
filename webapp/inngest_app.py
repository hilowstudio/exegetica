"""Inngest (serve mode) — the durable, concurrency-capped extraction worker.

Inngest Cloud calls INTO this app's /api/inngest serve endpoint to run the
`extract-book` function (that's why serve mode fits Fly's scale-to-zero: the inbound
request wakes the machine). The function wraps webapp.extraction.extract_book, capped
at 2 concurrent runs so a burst of books queues rather than melting the Anthropic budget.

Env: INNGEST_EVENT_KEY (send events), INNGEST_SIGNING_KEY (serve/verify). In production
(FLY_APP_NAME set) the client runs in production mode; locally it targets the Inngest
Dev Server. Optional INNGEST_SERVE_ORIGIN overrides the public callback origin.

Building this module (client + serve app) needs no network; the live cloud round-trip is
validated after a deploy (Inngest must reach the deployed serve URL).
"""
from __future__ import annotations

import logging
import os

import inngest
import inngest.fast_api
from inngest import Concurrency, Event, Inngest, TriggerEvent

from webapp import db, extraction
from webapp.sources import registry

logger = logging.getLogger("study-bible-web.inngest")

client = Inngest(
    app_id="exegetica",
    is_production=bool(os.environ.get("FLY_APP_NAME")),
    logger=logger,
)


@client.create_function(
    fn_id="extract-book",
    trigger=TriggerEvent(event="library/book.extract.requested"),
    concurrency=[Concurrency(limit=2)],
    retries=3,
)
async def extract_book_fn(ctx) -> dict:
    """Grounding-first extraction as bounded, memoized steps (the quillnext pattern):
    fetch (park text) → derive → finalize. The multi-MB text lives in
    library_extractions.full_text_raw between steps, so nothing large crosses a step
    boundary. Each step is idempotent, so a retry re-runs only the failing step."""
    import uuid

    d = ctx.event.data or {}
    meta = {"title": d.get("title") or "", "authors": ([d["author"]] if d.get("author") else [])}
    exid = uuid.UUID(d["extraction_id"]) if d.get("extraction_id") else await extraction.ensure_extraction_row(meta)

    fetched = await ctx.step.run("fetch", extraction.step_fetch, exid, meta)
    if not fetched.get("ok"):
        return {"status": "failed", "reason": fetched.get("reason"), "extraction_id": str(exid)}

    await ctx.step.run("derive", extraction.step_derive, exid, meta)
    await ctx.step.run("finalize", extraction.step_finalize, exid)
    return await ctx.step.run("summary", extraction.extraction_summary, exid)


@client.create_function(
    fn_id="extract-upload",
    trigger=TriggerEvent(event="library/upload.extract.requested"),
    concurrency=[Concurrency(limit=2)],
    retries=3,
)
async def extract_upload_fn(ctx) -> dict:
    """Upload path (in-copyright / accessibility): the same batched steps, but the source
    text is the teacher's uploaded copy — ingested from R2 into the private tier-1 vault,
    never published as full_text. `ingest` replaces `fetch`; user_id threads through so the
    derive/finalize steps read the DECRYPTED tier-1 copy."""
    import uuid

    d = ctx.event.data or {}
    exid = uuid.UUID(d["extraction_id"])
    user_id = d["user_id"]
    meta = {"title": d.get("title") or "", "authors": ([d["author"]] if d.get("author") else [])}

    ingested = await ctx.step.run(
        "ingest", extraction.step_ingest_upload,
        exid, d["r2_object_key"], d.get("source_format", "epub"), user_id, d.get("acquisition", "owned"), meta,
    )
    if not ingested.get("ok"):
        return {"status": "failed", "reason": ingested.get("reason"), "extraction_id": str(exid)}
    if not ingested.get("derive"):
        # Verified and stored in the uploader's private vault, but a better/PD copy is
        # already canonical — don't rebuild the shared derivative from this one.
        return {"status": "kept_private", "reason": ingested.get("reason"), "extraction_id": str(exid)}

    await ctx.step.run("derive", extraction.step_derive, exid, meta, user_id)
    await ctx.step.run("finalize", extraction.step_finalize, exid, user_id)
    return await ctx.step.run("summary", extraction.extraction_summary, exid)


@client.create_function(
    fn_id="rederive",
    trigger=TriggerEvent(event="library/rederive.requested"),
    concurrency=[Concurrency(limit=2)],
    retries=3,
)
async def rederive_fn(ctx) -> dict:
    """Rebuild the shared derivative from an already-stored copy — no ingest, no R2. Fired
    when a reviewer promotes a borderline upload to canonical: the canonical_source/tier/
    quality are set by the promote endpoint first; here we just re-run derive → finalize
    against that copy's text (user_id set → the private tier-1 vault; null → the PD raw)."""
    import uuid

    d = ctx.event.data or {}
    exid = uuid.UUID(d["extraction_id"])
    user_id = d.get("user_id")  # may be None for a PD copy
    meta = {"title": d.get("title") or "", "authors": ([d["author"]] if d.get("author") else [])}

    await ctx.step.run("derive", extraction.step_derive, exid, meta, user_id)
    await ctx.step.run("finalize", extraction.step_finalize, exid, user_id)
    return await ctx.step.run("summary", extraction.extraction_summary, exid)


functions = [extract_book_fn, extract_upload_fn, rederive_fn]


async def trigger_extract(title: str, author: str | None = None, extraction_id=None) -> list[str]:
    """Send the PD extraction event (from the trigger endpoint). Returns the event ids."""
    return await client.send(
        Event(
            name="library/book.extract.requested",
            data={"title": title, "author": author, "extraction_id": str(extraction_id) if extraction_id else None},
        )
    )


async def trigger_upload_extract(*, title, author, extraction_id, r2_object_key, source_format, user_id, acquisition) -> list[str]:
    """Send the upload extraction event (from the upload-complete endpoint)."""
    return await client.send(
        Event(
            name="library/upload.extract.requested",
            data={
                "title": title, "author": author, "extraction_id": str(extraction_id),
                "r2_object_key": r2_object_key, "source_format": source_format,
                "user_id": str(user_id), "acquisition": acquisition,
            },
        )
    )


async def trigger_rederive(*, title, author, extraction_id, user_id=None) -> list[str]:
    """Rebuild the shared derivative from an already-stored copy (reviewer promotion)."""
    return await client.send(
        Event(
            name="library/rederive.requested",
            data={
                "title": title, "author": author, "extraction_id": str(extraction_id),
                "user_id": str(user_id) if user_id else None,
            },
        )
    )


def build_serve_app():
    """A FastAPI sub-app that serves the Inngest endpoint at its root (mounted under
    /api/inngest in the main Starlette app; public_path tells Inngest the real path)."""
    from fastapi import FastAPI

    sub = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    # Mounted at /api/inngest with the sub-app serving at "/", so /api/inngest/ (with
    # slash) is the non-redirecting endpoint; register THAT with Inngest so its function
    # invocations hit it directly instead of relying on the 307 from the no-slash form.
    kw = {"serve_path": "/", "public_path": "/api/inngest/"}
    origin = os.environ.get("INNGEST_SERVE_ORIGIN")
    if origin:
        kw["serve_origin"] = origin
    inngest.fast_api.serve(sub, client, functions, **kw)
    return sub
