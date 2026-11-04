"""Inngest (serve mode) — the durable, concurrency-capped extraction worker.

Inngest Cloud calls INTO this app's /api/inngest serve endpoint to run the
`extract-book` function (that's why serve mode fits Fly's scale-to-zero: the inbound
request wakes the machine). The function wraps webapp.extraction.extract_book, capped
at 2 concurrent runs so a burst of books queues rather than melting the Anthropic budget.
`build-comprehension` builds a large book's whole-work comprehension (webapp/comprehension.py)
for the Generator, one memoized step per span.

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
from inngest import Concurrency, Event, Inngest, Singleton, TriggerCron, TriggerEvent

from webapp import comprehension, db, extraction
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


async def comprehension_failed_fn(ctx) -> None:
    """The build used its retries: leave a marker so generation stops waiting on it for a day."""
    original = (ctx.event.data or {}).get("event") or {}
    key = (original.get("data") or {}).get("book_key")
    if key:
        await comprehension.mark_failed(key)


@client.create_function(
    fn_id="build-comprehension",
    trigger=TriggerEvent(event="library/comprehension.build.requested"),
    singleton=Singleton(key="event.data.book_key", mode="skip"),
    concurrency=[Concurrency(limit=comprehension.MAP_CONCURRENCY)],
    retries=3,
    on_failure=comprehension_failed_fn,
)
async def build_comprehension_fn(ctx) -> dict:
    """Whole-work comprehension for a large book: plan → map each span (memoized, at most
    MAP_CONCURRENCY in flight) → reduce and cache. One run per book at a time (a second
    request while one runs is skipped), and the plan step returns early when the build is
    already cached, so repeated requests cost a database read."""
    key = (ctx.event.data or {})["book_key"]
    plan = await ctx.step.run("plan", comprehension.step_plan, key)
    if plan.get("status") != "build":
        return plan
    spans, notes = plan["spans"], []
    for start in range(0, len(spans), comprehension.MAP_CONCURRENCY):
        group = tuple(
            (lambda i=i: ctx.step.run(f"map-{i}", comprehension.step_map, key, spans[i], i, len(spans)))
            for i in range(start, min(start + comprehension.MAP_CONCURRENCY, len(spans))))
        notes.extend(await ctx.group.parallel(group))
    return await ctx.step.run("reduce", comprehension.step_reduce, key, plan["title"], plan["total"], notes)


async def _studio_prices() -> dict:
    from webapp import studio

    book = await studio.refresh_prices()
    entries = book["routes"].values()
    return {"read": sum(e.get("status") == "ok" for e in entries), "kept": sum(e.get("status") == "kept" for e in entries)}


@client.create_function(
    fn_id="studio-prices",
    trigger=TriggerCron(cron="TZ=America/Chicago 0 5 * * *"),
    retries=1,
)
async def studio_prices_fn(ctx) -> dict:
    """Image Studio's daily price check (webapp/studio_prices.py, docs/decisions/0017): each
    morning at 5:00 Central, read every service's price so each model runs on the cheapest."""
    return await ctx.step.run("read-prices", _studio_prices)


functions = [extract_book_fn, extract_upload_fn, rederive_fn, build_comprehension_fn, studio_prices_fn]


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


async def trigger_comprehension(book_key: str) -> list[str]:
    """Request the whole-work comprehension build for a large book (from the generate endpoint)."""
    return await client.send(
        Event(name="library/comprehension.build.requested", data={"book_key": book_key})
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
