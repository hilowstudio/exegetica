"""Google Gemini provider for the extraction pipeline (the `google-genai` SDK).

Extraction runs on Anthropic (claude-*) or Gemini (gemini-*), chosen by EXTRACTION_MODEL
(interactive path) or the seeder's --model. Requests are built once, Anthropic-shaped
(a `system` string + a user message whose content is a string or text blocks — see
extraction._params); this module translates that neutral shape to google-genai and runs
it, for BOTH the interactive call and the Batch API seeder.

These are grounded, low-reasoning JSON tasks, so thinking is pinned to 'low' (Gemini bills
thinking tokens at the output rate; 3.8 Flash rejects 'minimal'). JSON is forced with
response_mime_type; we still parse + validate the values ourselves.

Auth: GEMINI_API_KEY or GOOGLE_API_KEY (GOOGLE_API_KEY wins if both are set).
"""
from __future__ import annotations

import json
import os

_THINKING_LEVEL = os.environ.get("GEMINI_THINKING_LEVEL", "low")


def configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def is_gemini(model: str | None) -> bool:
    return bool(model) and str(model).startswith("gemini")


def _user_text(params: dict) -> str:
    """Flatten the neutral user content (a string, or Anthropic-style text blocks) to the
    single string google-genai wants. cache_control on a block is dropped (Gemini's implicit
    cache is automatic, and our per-section calls fall below its 4k-token threshold anyway)."""
    content = params["messages"][0]["content"]
    if isinstance(content, str):
        return content
    return "\n\n".join(
        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
    )


def _gen_config(params: dict) -> dict:
    return {
        "system_instruction": params.get("system"),
        "max_output_tokens": params.get("max_tokens", 1200),
        "response_mime_type": "application/json",
        "thinking_config": {"thinking_level": _THINKING_LEVEL},
    }


_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client()
    return _client


def complete_json_sync(params: dict):
    """One grounded JSON completion (interactive path). Returns the parsed object or None.
    Synchronous — extraction._call runs it in a thread so it fits the async pipeline."""
    from webapp.extraction import _parse_json  # lazy: avoid an import cycle

    try:
        resp = _get_client().models.generate_content(
            model=params["model"], contents=_user_text(params), config=_gen_config(params)
        )
        return _parse_json(getattr(resp, "text", None))
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger("study-bible-web.gemini").exception("gemini call failed")
        return None


# --------------------------------------------------------------------------- #
# Batch API (native google-genai) — the seeder's bulk path (50% cheaper)
# --------------------------------------------------------------------------- #
def _batch_line(custom_id: str, params: dict) -> dict:
    """One JSONL line: {"key": <id>, "request": <GenerateContentRequest>}. The `key` is
    echoed back on the matching response — Gemini's equivalent of a batch custom_id."""
    return {
        "key": custom_id,
        "request": {
            "contents": [{"role": "user", "parts": [{"text": _user_text(params)}]}],
            "system_instruction": {"parts": [{"text": params.get("system", "")}]},
            "generation_config": {
                "max_output_tokens": params.get("max_tokens", 1200),
                "response_mime_type": "application/json",
                "thinking_config": {"thinking_level": _THINKING_LEVEL},
            },
        },
    }


def _parse_result_line(obj: dict):
    """(key, parsed_json | None, {'in','out'}) from one result JSONL object."""
    from webapp.extraction import _parse_json

    resp = obj.get("response") or {}
    text = "".join(
        part.get("text", "")
        for cand in resp.get("candidates", [])
        for part in ((cand.get("content", {}) or {}).get("parts", []) or [])
    )
    um = resp.get("usageMetadata", {}) or {}
    usage = {"in": um.get("promptTokenCount", 0) or 0,
             "out": (um.get("candidatesTokenCount", 0) or 0) + (um.get("thoughtsTokenCount", 0) or 0)}
    return obj.get("key"), (_parse_json(text) if text else None), usage


# Max input tokens to enqueue in a single batch job. The Batch API caps *concurrent*
# enqueued tokens per model (Gemini 3.8 Flash at paid Tier 1 = 3,000,000); exceed it and
# batches.create returns 429 RESOURCE_EXHAUSTED. We chunk under this and submit chunks
# sequentially — each drains (polled to completion) before the next, so there is no ceiling
# on total tokens processed, only on how many wait at once. Override via env for other tiers.
_BATCH_TOKEN_BUDGET = int(os.environ.get("GEMINI_BATCH_TOKEN_BUDGET", "2500000"))


def _est_tokens(params: dict) -> int:
    """Rough input-token estimate for one request (~4 chars/token), used only to size chunks."""
    return (len(params.get("system", "") or "") + len(_user_text(params))) // 4


def _chunk_by_tokens(requests: list[dict], budget: int) -> list[list[dict]]:
    """Greedily pack requests into chunks whose estimated input tokens stay under budget.
    A single request larger than budget gets its own chunk (can't be split further)."""
    chunks: list[list[dict]] = []
    cur: list[dict] = []
    cur_tok = 0
    for r in requests:
        t = _est_tokens(r["params"])
        if cur and cur_tok + t > budget:
            chunks.append(cur)
            cur, cur_tok = [], 0
        cur.append(r)
        cur_tok += t
    if cur:
        chunks.append(cur)
    return chunks


def _submit_and_drain(client, model: str, requests: list[dict], label: str, poll: int) -> tuple[dict, dict]:
    """Upload → create → poll one batch job to completion → download. On a 429 at create
    (still over the enqueue cap despite chunking), split the chunk in half and recurse; a
    lone request over the cap re-raises with a clear message."""
    import tempfile
    import time

    from google.genai import types
    from google.genai import errors as _gerr

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for r in requests:
            f.write(json.dumps(_batch_line(r["custom_id"], r["params"])) + "\n")
        path = f.name
    up = client.files.upload(file=path, config=types.UploadFileConfig(display_name=label, mime_type="jsonl"))
    try:
        job = client.batches.create(model=model, src=up.name, config={"display_name": label})
    except _gerr.ClientError as e:
        if getattr(e, "code", None) == 429 and len(requests) > 1:
            mid = len(requests) // 2
            print(f"  [{label}] 429 on {len(requests)} reqs — splitting into {mid} + {len(requests) - mid}")
            a = _submit_and_drain(client, model, requests[:mid], label + "a", poll)
            b = _submit_and_drain(client, model, requests[mid:], label + "b", poll)
            out = {**a[0], **b[0]}
            return out, {"in": a[1]["in"] + b[1]["in"], "out": a[1]["out"] + b[1]["out"]}
        if getattr(e, "code", None) == 429:
            raise RuntimeError(
                "Gemini 429 RESOURCE_EXHAUSTED on a single-request batch — one work's text alone "
                "exceeds this tier's enqueued-token cap (Gemini 3.8 Flash Tier 1 = 3,000,000). Raise "
                "the account tier, or skip that oversized work."
            ) from e
        raise
    print(f"  [{label}] gemini batch {job.name}: {len(requests)} requests submitted")
    done = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
    while job.state.name not in done:
        time.sleep(poll)
        job = client.batches.get(name=job.name)
    out, usage = {}, {"in": 0, "out": 0}
    if job.state.name == "JOB_STATE_SUCCEEDED" and job.dest and job.dest.file_name:
        data = client.files.download(file=job.dest.file_name).decode("utf-8")
        ok = 0
        for line in data.splitlines():
            if not line.strip():
                continue
            key, parsed, u = _parse_result_line(json.loads(line))
            out[key] = parsed
            usage["in"] += u["in"]
            usage["out"] += u["out"]
            ok += parsed is not None
        print(f"  [{label}] state {job.state.name}; parsed {ok}/{len(out)}; "
              f"tokens in {usage['in']:,} out {usage['out']:,}")
    else:
        print(f"  [{label}] state {job.state.name} (no results): {getattr(job, 'error', None)}")
    return out, usage


def run_batch(requests: list[dict], label: str, poll: int = 30) -> tuple[dict, dict]:
    """Submit requests as one or more Gemini batch jobs, returning {custom_id: parsed_json} +
    summed token usage. Chunks under the per-model enqueued-token cap and submits chunks
    sequentially (each drains before the next). Mirrors the seeder's Anthropic run_batch."""
    if not requests:
        return {}, {"in": 0, "out": 0}
    client = _get_client()
    model = requests[0]["params"]["model"]
    chunks = _chunk_by_tokens(requests, _BATCH_TOKEN_BUDGET)
    if len(chunks) > 1:
        print(f"  [{label}] {len(requests)} requests exceed the enqueue budget "
              f"(~{_BATCH_TOKEN_BUDGET:,} tok) → {len(chunks)} sequential batches")
    out, usage = {}, {"in": 0, "out": 0}
    for i, chunk in enumerate(chunks, 1):
        clabel = label if len(chunks) == 1 else f"{label} {i}/{len(chunks)}"
        o, u = _submit_and_drain(client, model, chunk, clabel, poll)
        out.update(o)
        usage["in"] += u["in"]
        usage["out"] += u["out"]
    return out, usage
