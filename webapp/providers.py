"""
Multi-provider chat backends (BYOK).

Three code paths cover four providers:
  - Anthropic  -> native Anthropic SDK (Messages API, adaptive thinking).
  - OpenAI     -> OpenAI SDK, Responses API (reasoning + function tools together).
  - xAI Grok / Google Gemini -> OpenAI SDK, chat completions (both expose an
    OpenAI-compatible chat/tools API via a base_url).

Both paths drive the SAME Study Bible MCP tools and yield the SAME event dicts:
  {"type": "text", "text": ...}
  {"type": "thinking", "text": ...}          (Anthropic only)
  {"type": "tool_call", "name": ...}
  {"type": "tool_done", "name": ..., "error": bool}
  {"type": "status", "stage": ..., "words": n}   (what the run is doing while nothing shows yet)
  {"type": "error", "message": ...}

A status stage is "studying" (the first step), "reading" (a step after lookups), "looking" (lookups
running), "writing" (an answer held until its step ends, with its words so far, or the answer after
a check), or "checking" (lookups checking an answer the model wrote). The page names each one.

The API key is supplied per request and used to build a throwaway client; it is
never stored or logged server-side.
"""

import asyncio
import json
import logging
import os
import re

from webapp import policy

logger = logging.getLogger("study-bible-web.providers")

MAX_TOOL_TURNS = 12

# Tool results feed the model in full within a turn, and each later step of the tool loop
# re-reads them. Most results run 1-8k chars and the big useful ones (a verse's commentary,
# a long psalm, a theology search) 12-17k, so this cap only trims outliers such as
# multi-chapter passages, and tells the model to ask for less.
_LIVE_TOOL_CAP = 20000

# The last allowed step must answer (docs/decisions/0008), and the last tool results carry this line
# so the model knows it. Opus 5.5 once spent its last step, tools withheld, writing nothing at all.
# Open models can also ignore tool_choice "none", so their loop sends that step with no tools.
ANSWER_NOW = ("[The library step limit is reached. Write the answer now from the results above, "
              "with no further lookups.]")
# After an answer that was checked with a lookup (docs/decisions/0019). The student never saw that answer.
ANSWER_IN_FULL = ("[The student has not seen the answer above. Write the whole answer now, correcting it by "
                  "what the library returned, with no further lookups. The student sees only the answer that follows.]")
STEP_LIMIT = "This answer reached its step limit. Ask a narrower question to go further."


async def _call_tool(mcp, name: str, args: dict) -> tuple[str, bool]:
    out, is_error = await mcp.call(name, args)
    out = out or ""
    if len(out) > _LIVE_TOOL_CAP:
        out = (out[:_LIVE_TOOL_CAP] + f"\n\n[Result truncated: {len(out):,} characters, first "
               f"{_LIVE_TOOL_CAP:,} shown. Request a narrower range if you need the rest.]")
    return out, is_error


# Per-turn token usage, logged so cost and cache health are visible in the Fly logs.
# $ per million tokens: (input, output, cache-read multiplier); cache writes are 1.25x input.
_PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.05), "claude-sonnet-5-5": (2.0, 10.0, 0.05),
           "claude-sonnet-5": (2.0, 10.0, 0.10), "claude-haiku-5-5": (0.10, 0.50, 0.10),
           "claude-sonnet-4-6": (3.0, 15.0, 0.10),
           # DeepInfra's Nemotron 3.5 Super, checked 2026-11-05: cached input is $0.02 of $0.15.
           "nvidia/NVIDIA-Nemotron-3.5-Super-VL": (0.15, 0.50, 0.02 / 0.15),
           # DeepInfra's GLM-5.3-Flash, the chat fallback, checked 2026-11-06: cached input $0.03.
           "zai-org/GLM-5.3-Flash": (0.15, 0.50, 0.20)}


def _usd(model: str, u: dict) -> float:
    """Estimated dollars for the usage so far; 0 for a model without a price here."""
    if model not in _PRICES:
        return 0.0
    inp, outp, read = _PRICES[model]
    return (u["input"] * inp + u["cache_write"] * inp * 1.25 + u["cache_read"] * inp * read
            + u["output"] * outp) / 1e6


def _log_usage(model: str, u: dict) -> None:
    if not u["requests"]:
        return
    cost = f" est=${_usd(model, u):.4f}" if model in _PRICES else ""
    total_in = u["input"] + u["cache_write"] + u["cache_read"]
    hit = f" cache_hit={u['cache_read'] / total_in:.0%}" if total_in else ""
    logger.info("usage model=%s requests=%d input=%d cache_read=%d cache_write=%d output=%d%s%s",
                model, u["requests"], u["input"], u["cache_read"], u["cache_write"], u["output"], hit, cost)

# Registry. `kind` selects the code path; `base_url` overrides the OpenAI host.
# default_model is a starting point the user can override in the UI (current
# model IDs for non-Anthropic providers change; the field is editable).
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)", "kind": "anthropic",
        "default_model": "claude-opus-5-5",
        "fallback_model": "claude-sonnet-4-6",   # stable, broadly available
        "base_url": None,
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "label": "OpenAI", "kind": "responses",   # Responses API: reasoning + tools
        "default_model": "gpt-5.6",
        "fallback_model": "gpt-5.6-terra",        # same-gen stable, lower cost
        "base_url": None,
        "key_url": "https://platform.openai.com/api-keys",
        "reasoning_effort": "medium",
    },
    "gemini": {
        "label": "Google Gemini", "kind": "openai",
        "default_model": "gemini-3.1-pro-preview",   # Pro tier (preview)
        "fallback_model": "gemini-3.7-flash",        # stable, confirmed via compat + tools
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "grok": {
        "label": "xAI Grok", "kind": "openai",
        "default_model": "grok-4.6",
        "fallback_model": "grok-4.5",             # stable prior flagship
        "base_url": "https://api.x.ai/v1",
        "key_url": "https://console.x.ai",
    },
    # Chat for everyone (docs/decisions/0024): open models on DeepInfra, which keeps no prompts or
    # replies under its terms, paid with the server's key. Settings doesn't offer it.
    "deepinfra": {
        "label": "DeepInfra", "kind": "openai",
        "default_model": "nvidia/NVIDIA-Nemotron-3.5-Super-VL",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "key_url": "https://deepinfra.com/dash/api_keys",
        "key_env": "DEEPINFRA_API_KEY",
        "extra_params": {"reasoning_effort": "medium"},
        # A stalled host gives way to the fallback model within about a minute, with no SDK retries
        # stacked under the loop's own one retry.
        "timeout": 60, "max_retries": 0,
        "server_only": True,
    },
}


def public_providers() -> list[dict]:
    """Provider metadata safe to expose to the front-end."""
    return [
        {"id": pid, "label": p["label"], "default_model": p["default_model"],
         "fallback_model": p.get("fallback_model"), "key_url": p["key_url"]}
        for pid, p in PROVIDERS.items() if not p.get("server_only")
    ]


# Substrings that mark a model-availability failure (worth a fallback), as
# opposed to auth / rate-limit / server errors (not worth switching models).
_MODEL_ERROR_HINTS = (
    "not found", "does not exist", "no such model", "unknown model",
    "invalid model", "unsupported model", "model_not_found", "404",
    "not available", "unavailable", "decommission", "deprecat",
)


def _is_model_error(message: str) -> bool:
    m = (message or "").lower()
    return any(h in m for h in _MODEL_ERROR_HINTS)


def _openai_tools(mcp_tools: list[dict]) -> list[dict]:
    """Anthropic tool dicts -> OpenAI function-tool dicts."""
    return [
        {"type": "function", "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }}
        for t in mcp_tools
    ]


# ---------------------------------------------------------------------------
# Cross-turn tool memory
#
# The browser stores each assistant turn as {role, content, tools?} where `tools`
# is a provider-NEUTRAL list of the tools that ran during that turn:
#   [{"name", "input": {...}, "output": "...", "is_error": bool}, ...]
# On the next request we rehydrate those into each provider's native tool turns,
# so the model actually sees its own earlier tool calls + results (and can build
# on them) instead of a transcript with the tool activity amputated.
#
# We cap each stored output so the persisted chat blob can't grow without bound;
# the LIVE turn always feeds the model the FULL tool output — only the copy we
# stream back for persistence is capped.
# ---------------------------------------------------------------------------
_TOOL_OUTPUT_CAP = 4000


def _cap(text: str, n: int = _TOOL_OUTPUT_CAP) -> str:
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n…[truncated]"


def _hist_tools(m: dict) -> list[dict]:
    return m.get("tools") or [] if m.get("role") == "assistant" else []


def _anthropic_messages(history: list[dict]) -> list[dict]:
    """Neutral history -> Anthropic message list, reconstructing tool_use/tool_result."""
    out: list[dict] = []
    for idx, m in enumerate(history):
        if m.get("role") == "user":
            out.append({"role": "user", "content": m["content"]})
            continue
        content = m.get("content")
        if not isinstance(content, str):  # already native (defensive) — pass through
            out.append({"role": "assistant", "content": content})
            continue
        tools = _hist_tools(m)
        blocks: list[dict] = []
        if content:
            blocks.append({"type": "text", "text": content})
        for i, t in enumerate(tools):
            blocks.append({"type": "tool_use", "id": f"h{idx}_{i}",
                           "name": t.get("name") or "tool", "input": t.get("input") or {}})
        if not blocks:
            continue
        out.append({"role": "assistant", "content": blocks})
        if tools:
            out.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": f"h{idx}_{i}",
                 "content": t.get("output") or "", "is_error": bool(t.get("is_error"))}
                for i, t in enumerate(tools)
            ]})
    return _merge_user_runs(out)


def _merge_user_runs(msgs: list[dict]) -> list[dict]:
    """Fold consecutive user turns into one (a reconstructed tool_result turn is
    followed by the next real user turn) so message roles stay well-formed."""
    def as_blocks(c):
        if isinstance(c, str):
            return [{"type": "text", "text": c}] if c else []
        return list(c)

    merged: list[dict] = []
    for m in msgs:
        if merged and m["role"] == "user" and merged[-1]["role"] == "user":
            merged[-1] = {"role": "user",
                          "content": as_blocks(merged[-1]["content"]) + as_blocks(m["content"])}
        else:
            merged.append(dict(m))
    return merged


def _responses_input(history: list[dict]) -> list[dict]:
    """Neutral history -> OpenAI Responses input items (function_call + output)."""
    items: list[dict] = []
    for idx, m in enumerate(history):
        if m.get("role") == "user":
            items.append({"role": "user", "content": m["content"]})
            continue
        content = m.get("content")
        if isinstance(content, str) and content:
            items.append({"role": "assistant", "content": content})
        for i, t in enumerate(_hist_tools(m)):
            cid = f"h{idx}_{i}"
            items.append({"type": "function_call", "call_id": cid,
                          "name": t.get("name") or "tool",
                          "arguments": json.dumps(t.get("input") or {})})
            items.append({"type": "function_call_output", "call_id": cid,
                          "output": t.get("output") or ""})
    return items


def _chat_messages(history: list[dict]) -> list[dict]:
    """Neutral history -> OpenAI-compatible chat messages (tool_calls + role:tool)."""
    msgs: list[dict] = []
    for idx, m in enumerate(history):
        if m.get("role") == "user":
            msgs.append({"role": "user", "content": m["content"]})
            continue
        content = m.get("content")
        tools = _hist_tools(m)
        if not tools:
            msgs.append({"role": "assistant", "content": content})
            continue
        msgs.append({"role": "assistant",
                     "content": content if isinstance(content, str) and content else None,
                     "tool_calls": [
                         {"id": f"h{idx}_{i}", "type": "function",
                          "function": {"name": t.get("name") or "tool",
                                       "arguments": json.dumps(t.get("input") or {})}}
                         for i, t in enumerate(tools)]})
        for i, t in enumerate(tools):
            msgs.append({"role": "tool", "tool_call_id": f"h{idx}_{i}",
                         "content": t.get("output") or ""})
    return msgs


def _attempt(cfg, api_key, model, system_text, history, mcp, limits=None, stats=None):
    """One streaming attempt on a single model (returns an async generator)."""
    kind = cfg["kind"]
    if kind == "anthropic":
        return _run_anthropic(api_key, model, system_text, history, mcp, limits, stats)
    if kind == "responses":                       # OpenAI: reasoning + tools
        return _run_openai_responses(cfg, api_key, model, system_text, history, mcp)
    return _run_openai(cfg, api_key, model, system_text, history, mcp, limits, stats)  # Grok / Gemini / open models


OUTCOMES = ("complete", "cut_off", "step_limit", "budget", "tools_failed", "refused",
            "provider_error", "cancelled")


async def run(provider: str, api_key: str | None, model: str,
              system_text: str, history: list[dict], mcp, limits=None, stats=None) -> "AsyncIterator[dict]":
    """Dispatch a streaming, tool-using conversation, with a stable-model fallback.

    Tries the requested model first. If it fails with a model-availability error
    *before* anything has streamed to the user, it retries once on the provider's
    stable fallback model and emits a notice. A failure after content has begun,
    or an auth / rate-limit / server error, is passed through unchanged.

    `limits` (webapp/policy.RunLimits) bounds steps, output, and spend. A locked run (chat) never
    uses the provider's fallback. It turns, without a notice, to its own `fallback_model` when
    the first model ends in an error before any text was shown (docs/decisions/0024).

    Every run ends with one {"type": "end", "outcome": ...} event naming how it ended (OUTCOMES).
    `stats`, if given, is filled as the run goes with numbers for webapp/metrics.py, so a caller
    still has them when the browser closes mid-run. The Anthropic path fills all of it; the
    bring-your-own-key paths report the outcome only.
    """
    stats = {} if stats is None else stats
    stats.setdefault("model_req", (model or "").strip() or None)
    cfg = PROVIDERS.get(provider)
    if not cfg:
        stats["outcome"] = "provider_error"
        yield {"type": "error", "message": f"Unknown provider: {provider}"}
        yield {"type": "end", "outcome": "provider_error"}
        return
    locked = bool(limits and limits.locked)
    if not api_key and cfg.get("key_env"):   # a provider the server pays for (chat)
        api_key = os.environ.get(cfg["key_env"])
    if cfg["kind"] != "anthropic" and not api_key:
        stats["outcome"] = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR if locked else
               f"An API key is required for {cfg['label']}."}
        yield {"type": "end", "outcome": "provider_error"}
        return

    requested = (model or "").strip() or cfg["default_model"]
    # A locked run's fallback model lives on the chat provider, so it applies only there.
    fallback = (limits.fallback_model if provider == policy.CHAT_PROVIDER else None) if locked \
        else cfg.get("fallback_model")
    candidates = [requested] + ([fallback] if fallback and fallback != requested else [])

    errored = False
    carried = 0.0   # spend on a model that gave way to the fallback
    for i, current in enumerate(candidates):
        last = i == len(candidates) - 1
        emitted = wrote = False
        fell_back = False
        attempt = _attempt(cfg, api_key, current, system_text, history, mcp, limits, stats)
        async for ev in attempt:
            if ev["type"] in ("text", "tool_call", "tool_done", "thinking"):
                emitted = True
            wrote = wrote or ev["type"] == "text"
            if ev["type"] == "error" and not last and (   # a refusal ends a locked run (0004)
                    not wrote and ev.get("message") != policy.REFUSAL_TEXT if locked
                    else not emitted and _is_model_error(ev.get("message", ""))):
                if locked:   # the reader sees one reply, from whichever model wrote it
                    logger.warning("%s could not answer; falling back to %s", current, candidates[i + 1])
                else:
                    yield {"type": "notice",
                           "message": f"Model “{current}” is unavailable — falling back to “{candidates[i + 1]}”."}
                fell_back = True
                break
            errored = errored or ev["type"] == "error"
            yield ev
        if not fell_back:
            break
        await attempt.aclose()   # its cleanup fills stats now, before the next model's run starts
        carried += stats.get("est_usd") or 0.0
    if carried:
        stats["est_usd"] = round((stats.get("est_usd") or 0.0) + carried, 6)
    if stats.get("outcome") in (None, "cancelled"):   # the BYOK paths don't set one
        stats["outcome"] = "provider_error" if errored else "complete"
    yield {"type": "end", "outcome": stats["outcome"]}


# ---------------------------------------------------------------------------
# Anthropic (native SDK)
# ---------------------------------------------------------------------------
# Models whose safety classifiers can decline a request (stop_reason "refusal").
# For these we opt into the server-side fallback: a declined request is re-run on
# Anthropic's recommended model for that refusal category, inside the same call.
_REFUSAL_FALLBACK_PREFIXES = ("claude-opus-5", "claude-fable-5")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"   # the header for fallbacks="default"

# Explicit effort per model. Opus 5.5 defaults to "medium" (Opus 4.8 defaulted to
# "high"); stating it keeps the setting visible here as the thing to tune.
_EFFORT = {"claude-opus-5-5": "medium"}


def _after_fallback(content: list) -> list:
    """Apply the echo rule for a mid-output server-side fallback: before the last
    `fallback` marker, keep only text blocks (the declined model's thinking and
    tool calls don't carry over); keep everything after it."""
    last = max((i for i, b in enumerate(content) if getattr(b, "type", None) == "fallback"), default=None)
    if last is None:
        return list(content)
    kept = [b for b in content[:last] if getattr(b, "type", None) == "text"]
    return kept + list(content[last + 1:])


def _step_usage(u) -> dict:
    return {"input": getattr(u, "input_tokens", 0) or 0,
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "output": getattr(u, "output_tokens", 0) or 0}


_CATEGORY = re.compile(r"^[a-z_]{1,40}$")


def _refusal_category(final) -> str | None:
    """The refusal's category label, if the API gave one in a recognisable shape."""
    cat = getattr(getattr(final, "stop_details", None), "category", None)
    return cat if isinstance(cat, str) and _CATEGORY.match(cat) else None


RETRY_WAIT = 2.0   # seconds before the one retry of a failed step
_RETRY_ERROR_TYPES = {"overloaded_error", "api_error", "rate_limit_error", "timeout_error"}


def _retryable(e: Exception) -> bool:
    """A failure that a second try can fix: overload, rate limit, a server error, or a dropped
    connection. An error sent mid-stream arrives with the stream's 200 status, so its body decides."""
    import anthropic
    if isinstance(e, getattr(anthropic, "APIConnectionError", ())):
        return True
    if isinstance(e, getattr(anthropic, "APIStatusError", ())):
        if e.status_code in (408, 409, 429) or e.status_code >= 500:
            return True
        err = e.body.get("error") if isinstance(e.body, dict) else None
        return isinstance(err, dict) and err.get("type") in _RETRY_ERROR_TYPES
    return type(e).__module__.split(".")[0] in ("httpx", "httpx2", "httpcore")


async def _run_anthropic(api_key, model, system_text, history, mcp, limits=None, stats=None):
    import anthropic
    from anthropic import AsyncAnthropic

    stats = {} if stats is None else stats
    client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    messages = _anthropic_messages(history)

    # Thinking is always on for current models and counts toward max_tokens, so leave
    # room for it plus a long generated document (streaming, so no HTTP timeout risk).
    # The explicit marker on the system prompt caches tools + system (shared by every chat);
    # top-level automatic caching moves a second breakpoint to the end of the conversation
    # on each request, so every step of the tool loop, and the next turn, re-reads the
    # history from cache instead of at full price.
    params = dict(model=model, max_tokens=limits.max_tokens if limits else 64000, system=system,
                  tools=mcp.tools, thinking={"type": "adaptive", "display": "summarized"},
                  cache_control={"type": "ephemeral"})
    usage = {"requests": 0, "input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    if model in _EFFORT:
        params["output_config"] = {"effort": _EFFORT[model]}
    # A locked run (student chat) ends on a refusal; no other model answers in its place.
    fallback = model.startswith(_REFUSAL_FALLBACK_PREFIXES) and not (limits and limits.locked)
    if fallback:
        params.update(betas=[_FALLBACK_BETA], fallbacks="default")
    stream_fn = client.beta.messages.stream if fallback else client.messages.stream

    max_steps = limits.max_steps if limits else MAX_TOOL_TURNS
    locked = bool(limits and limits.locked)
    spent = 0.0          # estimated dollars, priced per step at the model that served it
    cur = None           # usage of the step in flight, tallied from stream events
    failed_steps = 0     # consecutive steps whose every tool call failed
    retried = False      # one retry per run, for a step that failed before any text reached the reader
    outcome = None
    wrote = False        # some text of this run has reached the reader
    stats.update(model_req=model, steps=0, tool_errors=0)

    def tally_partial():
        nonlocal cur, spent
        if cur is not None:   # a step cut short: count what it used
            usage["requests"] += 1
            for k, v in cur.items():
                usage[k] += v
            spent += _usd(model, cur)
            cur = None

    try:
        for step in range(max_steps):
            # The last allowed step, or the first one past the spend ceiling, must answer with what
            # it has rather than call more tools, so a run never ends without a reply.
            over_budget = limits is not None and spent >= limits.max_usd
            final_step = step == max_steps - 1 or over_budget
            call = dict(params, tool_choice={"type": "none"}) if final_step and step else params
            if final_step and step and messages[-1]["role"] == "user" and isinstance(messages[-1]["content"], list):
                messages[-1] = {"role": "user", "content": messages[-1]["content"] + [{"type": "text", "text": ANSWER_NOW}]}
            yield {"type": "status", "stage": "reading" if step else "studying"}
            while True:
                shown = False   # text from this step has reached the reader
                try:
                    async with stream_fn(messages=messages, **call) as stream:
                        async for event in stream:
                            if event.type == "message_start":
                                cur = _step_usage(event.message.usage)
                            elif event.type == "message_delta" and cur is not None and getattr(event, "usage", None):
                                cur["output"] = getattr(event.usage, "output_tokens", 0) or cur["output"]
                            elif event.type == "content_block_start" and \
                                    getattr(event.content_block, "type", None) == "tool_use":
                                yield {"type": "tool_call", "name": event.content_block.name}
                            elif event.type == "content_block_delta":
                                d = event.delta
                                if d.type == "text_delta":
                                    shown = wrote = True
                                    yield {"type": "text", "text": d.text}
                                elif d.type == "thinking_delta":
                                    yield {"type": "thinking", "text": d.thinking}
                        final = await stream.get_final_message()
                    break
                except Exception as e:  # noqa: BLE001
                    # Once text has reached the reader it stays, and the run ends with a notice below.
                    if shown or retried or not _retryable(e):
                        raise
                    retried = True
                    logger.warning("anthropic step %d failed (%s), retrying once", step, type(e).__name__)
                    tally_partial()
                    await asyncio.sleep(RETRY_WAIT)
            cur = None
            served = getattr(final, "model", None) or model
            su = _step_usage(final.usage)
            if not usage["requests"]:
                stats.update(first_read=su["cache_read"], first_write=su["cache_write"])
            usage["requests"] += 1
            for k, v in su.items():
                usage[k] += v
            spent += _usd(served if served in _PRICES else model, su)
            stats.update(steps=usage["requests"], model_served=served)

            if final.stop_reason == "refusal":   # declined, and any fallback declined too
                stats["refusal_category"] = _refusal_category(final)
                yield {"type": "error", "message": policy.REFUSAL_TEXT if locked else
                       "Claude declined to answer this request. Try rephrasing it, or ask it a different way."}
                outcome = "refused"
                break
            content = _after_fallback(final.content)
            messages.append({"role": "assistant", "content": content})
            if final.stop_reason == "max_tokens":
                yield {"type": "notice", "incomplete": True,
                       "message": "This answer was cut off at its length limit. Ask for a shorter piece."}
                outcome = "cut_off"
                break
            if final.stop_reason != "tool_use":
                outcome = "budget" if over_budget else "step_limit" if final_step and step else "complete"
                if final_step and step and not wrote:   # the reader would otherwise see nothing at all
                    yield {"type": "notice", "incomplete": True, "message": STEP_LIMIT}
                break
            if final_step:   # tool_choice "none" should prevent this; never run tools past the limit
                yield {"type": "notice", "incomplete": True, "message": STEP_LIMIT}
                outcome = "step_limit"
                break
            yield {"type": "status", "stage": "looking"}
            tool_results = []
            for block in content:
                if block.type != "tool_use":
                    continue
                out, is_error = await _call_tool(mcp, block.name, block.input)
                stats["tool_errors"] += bool(is_error)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": out, "is_error": is_error})
                yield {"type": "tool_done", "name": block.name, "input": block.input,
                       "output": _cap(out), "error": is_error}
            messages.append({"role": "user", "content": tool_results})
            failed_steps = failed_steps + 1 if tool_results and all(r["is_error"] for r in tool_results) else 0
            if failed_steps >= 2:   # the library is down; stop paying for steps that can't ground an answer
                yield {"type": "notice", "incomplete": True, "message": policy.TOOLS_DOWN}
                outcome = "tools_failed"
                break
    except anthropic.APIStatusError as e:
        # The raw error can echo the request, so it stays out of the reply and the metrics.
        logger.warning("anthropic API error status=%s type=%s", e.status_code, type(e).__name__)
        stats["http_status"] = e.status_code
        outcome = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR if locked else
               f"{policy.PROVIDER_ERROR} (Anthropic API error {e.status_code})"}
    except Exception:  # noqa: BLE001
        logger.exception("anthropic stream failed")
        outcome = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR}
    finally:
        tally_partial()       # a step cut short (closed browser, failure): count what it used
        stats.update({k: usage[k] for k in ("input", "cache_read", "cache_write", "output")},
                     est_usd=round(spent, 6), outcome=outcome or "cancelled")
        _log_usage(model, usage)
        import contextlib
        with contextlib.suppress(Exception):
            await client.close()


# ---------------------------------------------------------------------------
# OpenAI via the Responses API (reasoning + function tools together)
# ---------------------------------------------------------------------------
async def _run_openai_responses(cfg, api_key, model, system_text, history, mcp):
    import contextlib

    import openai
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=cfg.get("base_url"))
    # Responses tools are flat (no nested "function"); no strict (our schemas
    # allow optional properties).
    tools = [{"type": "function", "name": t["name"], "description": t["description"],
              "parameters": t["input_schema"]} for t in mcp.tools]
    reasoning = {"effort": cfg.get("reasoning_effort", "medium")}
    # Stateless multi-turn: resend the growing input list each turn. Rehydrate any
    # tool activity from earlier turns so the model sees its own prior calls.
    input_list: list = _responses_input(history)

    try:
        for _turn in range(MAX_TOOL_TURNS):
            stream = await client.responses.create(
                model=model, instructions=system_text, tools=tools,
                input=input_list, reasoning=reasoning, stream=True,
            )
            final = None
            async for event in stream:
                et = getattr(event, "type", "")
                if et == "response.output_text.delta":
                    yield {"type": "text", "text": event.delta}
                elif et == "response.reasoning_summary_text.delta":
                    yield {"type": "thinking", "text": event.delta}
                elif et == "response.output_item.added":
                    item = getattr(event, "item", None)
                    if item is not None and getattr(item, "type", None) == "function_call":
                        yield {"type": "tool_call", "name": item.name}
                elif et == "response.completed":
                    final = event.response
            if final is None:
                return
            # Preserve the model's output items (incl. reasoning) for the next turn.
            input_list += final.output
            calls = [it for it in final.output if getattr(it, "type", None) == "function_call"]
            if not calls:
                return
            for it in calls:
                try:
                    args = json.loads(it.arguments) if (it.arguments or "").strip() else {}
                except json.JSONDecodeError:
                    args = {}
                out, is_error = await _call_tool(mcp, it.name, args)
                input_list.append({"type": "function_call_output",
                                   "call_id": it.call_id, "output": out})
                yield {"type": "tool_done", "name": it.name, "input": args,
                       "output": _cap(out), "error": is_error}
    except openai.APIStatusError as e:
        yield {"type": "error", "message": f"{cfg['label']} API error {e.status_code}: {getattr(e, 'message', str(e))}"}
    except openai.APIConnectionError:
        yield {"type": "error", "message": f"Could not reach {cfg['label']}. Check the key and network."}
    except Exception as e:  # noqa: BLE001
        logger.exception("openai responses stream failed")
        yield {"type": "error", "message": str(e)}
    finally:
        with contextlib.suppress(Exception):
            await client.close()


# ---------------------------------------------------------------------------
# OpenAI-compatible chat completions (xAI Grok / Google Gemini)
# ---------------------------------------------------------------------------
# While a step may still call a tool, all its text is held, and it reaches the reader only if the step
# ends without one (docs/decisions/0019). Text before a lookup never shows. Held text that had begun a
# third sentence was a whole answer the model went on to check, so the step after the check answers
# with tools withheld: one check, never a loop of answer, lookup, answer.
_ANSWER_SENTENCES = 3
# While text is held, the status line counts its words: first once a step has written more than a
# one-line note, then every few words, so a student sees the answer growing (the word count is
# rechecked every hundred or so characters).
_STATUS_FIRST_WORDS = 12
_STATUS_EVERY_WORDS = 25
# With nothing fetched in advance, a first answer that used no library is set aside unseen and the
# model is asked once to look first (docs/decisions/0020). Open model hosts reject a forced tool
# call (tool_choice "required"), so this is the portable form of one.
LOOK_FIRST = ("[Before answering, look this up with the library tools and answer from what they "
              "return. The student sees only the answer that follows.]")


def _from_prompt(text: str, system_text: str) -> bool:
    """A reply the system prompt dictates word for word, such as the fixed reply about Exegetica."""
    t = " ".join(text.split())
    return len(t) >= 40 and t in " ".join(system_text.split())


def _sentences_begun(text: str) -> int:
    from webapp.reply_check import _BOUNDARY
    return sum(1 for piece in _BOUNDARY.split(text) if piece.strip())


def _openai_retryable(e: Exception) -> bool:
    import openai
    if isinstance(e, openai.APIConnectionError):
        return True
    return isinstance(e, openai.APIStatusError) and (e.status_code in (408, 409, 429) or e.status_code >= 500)


async def _run_openai(cfg, api_key, model, system_text, history, mcp, limits=None, stats=None):
    """The chat-completions tool loop for Grok, Gemini and open models, under the same ceilings as the
    Anthropic loop (docs/decisions/0008): steps, output per call, estimated spend for models with a
    price, a last step that must answer, one retry, and two all-failed tool steps end the run."""
    import openai
    from openai import AsyncOpenAI

    from webapp import prefetch

    stats = {} if stats is None else stats
    client = AsyncOpenAI(api_key=api_key, base_url=cfg["base_url"],
                         **{k: cfg[k] for k in ("timeout", "max_retries") if k in cfg})
    tools = _openai_tools(mcp.tools)
    messages = [{"role": "system", "content": system_text}]
    messages += _chat_messages(history)
    extra = cfg.get("extra_params", {})
    max_steps = limits.max_steps if limits else MAX_TOOL_TURNS
    locked = bool(limits and limits.locked)
    priced = model in _PRICES   # usage is asked for only where it can be priced
    usage = {"requests": 0, "input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    spent = 0.0
    failed_steps = 0
    retried = False
    outcome = None
    wrote = False   # some text of this run has reached the reader
    checked = ""    # an answer the last step wrote and then looked something up to check (never shown)
    looked = False  # some lookup has run, so a step starts by reading its results
    stats.update(model_req=model, steps=0, tool_errors=0, narration_dropped=0, answers_held=0)

    try:
        # The library first (docs/decisions/0020): sources the student's message names are looked up
        # before the model starts, and with none found the first step must use the library.
        must_call = False
        if limits and limits.tool_first:
            asked = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
            planned = prefetch.plan(asked, {t["name"] for t in mcp.tools})
            must_call = not planned
            stats["prefetched"] = len(planned)
            if planned:
                yield {"type": "status", "stage": "looking"}
                looked = True
                ids = [f"pre{i}" for i in range(len(planned))]
                messages.append({"role": "assistant", "content": None, "tool_calls": [
                    {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
                    for cid, (name, args) in zip(ids, planned)]})
                for cid, (name, args) in zip(ids, planned):
                    yield {"type": "tool_call", "name": name}
                    out, is_error = await _call_tool(mcp, name, args)
                    stats["tool_errors"] += bool(is_error)
                    messages.append({"role": "tool", "tool_call_id": cid, "content": out})
                    yield {"type": "tool_done", "name": name, "input": args, "output": _cap(out), "error": is_error}

        for step in range(max_steps):
            over_budget = limits is not None and spent >= limits.max_usd
            at_limit = step == max_steps - 1
            final_step = bool(step) and (at_limit or over_budget or bool(checked))
            params = dict(model=model, messages=messages, stream=True, **extra)
            if limits:
                params["max_tokens"] = limits.max_tokens
            if priced:
                params["stream_options"] = {"include_usage": True}
            if final_step:
                if messages[-1]["role"] == "tool":
                    note = ANSWER_IN_FULL if checked else ANSWER_NOW
                    messages[-1] = dict(messages[-1], content=f"{messages[-1]['content']}\n\n{note}")
            else:
                params["tools"] = tools
            hold_all = step == 0 and must_call   # this answer shows only if it used the library
            yield {"type": "status", "stage": "writing" if checked else "reading" if looked else "studying"}
            while True:
                text_parts: list[str] = []
                held: list[str] = []   # a step offered tools shows nothing until it ends without a call
                held_chars = recount_at = said = 0   # the status line's word count of the held text
                shown = False
                calls: dict[int, dict] = {}
                announced: set[int] = set()
                finish = None
                served = None
                su = None
                try:
                    stream = await client.chat.completions.create(**params)
                    async for chunk in stream:
                        served = getattr(chunk, "model", None) or served
                        if getattr(chunk, "usage", None):
                            u = chunk.usage
                            cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
                            su = {"input": (u.prompt_tokens or 0) - cached, "cache_read": cached,
                                  "cache_write": 0, "output": u.completion_tokens or 0}
                        if not chunk.choices:
                            continue
                        choice = chunk.choices[0]
                        finish = getattr(choice, "finish_reason", None) or finish
                        delta = choice.delta
                        if getattr(delta, "content", None):
                            text_parts.append(delta.content)
                            if final_step:   # a step with no tools is the answer from its first word
                                shown = True
                                yield {"type": "text", "text": delta.content}
                            else:
                                held.append(delta.content)
                                held_chars += len(delta.content)
                                if held_chars >= recount_at:
                                    recount_at = held_chars + 100
                                    words = len("".join(held).split())
                                    if words >= (said + _STATUS_EVERY_WORDS if said else _STATUS_FIRST_WORDS):
                                        said = words
                                        yield {"type": "status", "stage": "writing", "words": words}
                        for tc in (getattr(delta, "tool_calls", None) or []):
                            slot = calls.setdefault(tc.index, {"id": None, "name": "", "args": ""})
                            if tc.id:
                                slot["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    slot["name"] += tc.function.name
                                if tc.function.arguments:
                                    slot["args"] += tc.function.arguments
                            if slot["name"] and tc.index not in announced:
                                announced.add(tc.index)
                                yield {"type": "tool_call", "name": slot["name"]}
                    if not text_parts and not calls and finish != "length" and not retried:
                        retried = True   # an empty completion is a host glitch, like a dropped connection
                        logger.warning("%s step %d came back empty, retrying once", cfg["label"], step)
                        await asyncio.sleep(RETRY_WAIT)
                        continue
                    break
                except Exception as e:  # noqa: BLE001
                    if shown or retried or not _openai_retryable(e):
                        raise
                    retried = True
                    logger.warning("%s step %d failed (%s), retrying once", cfg["label"], step, type(e).__name__)
                    await asyncio.sleep(RETRY_WAIT)
            usage["requests"] += 1
            if su:
                for k, v in su.items():
                    usage[k] += v
                spent += _usd(model, su)
            stats.update(steps=usage["requests"], model_served=served or model)
            answer = "".join(held)
            if answer.strip() and calls:   # text before a lookup never reaches the reader
                if _sentences_begun(answer) >= _ANSWER_SENTENCES:
                    stats["answers_held"] += 1
                    checked = answer   # it answered, then looked something up to check: next, the whole answer
                else:
                    stats["narration_dropped"] += 1   # "Let me pull the passage."
            elif answer and not calls:
                if hold_all and finish != "length" and not _from_prompt(answer, system_text):
                    stats["lookup_nudges"] = 1   # answered from memory: set it aside and ask once to look
                    messages.append({"role": "user", "content": LOOK_FIRST})
                    continue
                yield {"type": "text", "text": answer}   # the step ended without a lookup: this is the answer
                shown = True
            wrote = wrote or shown

            if finish == "length":
                yield {"type": "notice", "incomplete": True,
                       "message": "This answer was cut off at its length limit. Ask for a shorter piece."}
                outcome = "cut_off"
                break
            if not calls:
                if not wrote and not final_step:   # empty again after the retry: say so, never a blank reply
                    yield {"type": "error", "message": policy.PROVIDER_ERROR}
                    outcome = "provider_error"
                    break
                outcome = "budget" if over_budget else "step_limit" if at_limit else "complete"
                if final_step and not wrote:   # the reader would otherwise see nothing at all
                    if checked:   # the step after the check wrote nothing: show the answer it was checking
                        yield {"type": "text", "text": checked}
                    else:
                        yield {"type": "notice", "incomplete": True, "message": STEP_LIMIT}
                break
            if final_step:   # tools were withheld; never run a call past the limit
                yield {"type": "notice", "incomplete": True, "message": STEP_LIMIT}
                outcome = "step_limit"
                break
            for c in calls.values():   # a call with arguments that aren't JSON runs with none, like the app
                try:
                    json.loads(c["args"] or "{}")
                except json.JSONDecodeError:
                    c["args"] = "{}"
            messages.append({
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                    for c in calls.values()
                ],
            })
            yield {"type": "status", "stage": "checking" if checked else "looking"}
            errors = []
            for c in calls.values():
                args = json.loads(c["args"]) if c["args"].strip() else {}
                out, is_error = await _call_tool(mcp, c["name"], args)
                stats["tool_errors"] += bool(is_error)
                errors.append(is_error)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                yield {"type": "tool_done", "name": c["name"], "input": args,
                       "output": _cap(out), "error": is_error}
            looked = True
            failed_steps = failed_steps + 1 if errors and all(errors) else 0
            if failed_steps >= 2:   # the library is down; stop paying for steps that can't ground an answer
                yield {"type": "notice", "incomplete": True, "message": policy.TOOLS_DOWN}
                outcome = "tools_failed"
                break
        else:
            outcome = "step_limit"
    except openai.APIStatusError as e:
        # The raw error can echo the request, so a locked run shows fixed text only.
        logger.warning("%s API error status=%s", cfg["label"], e.status_code)
        stats["http_status"] = e.status_code
        outcome = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR if locked else
               f"{cfg['label']} API error {e.status_code}: {getattr(e, 'message', str(e))}"}
    except openai.APIConnectionError:
        outcome = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR if locked else
               f"Could not reach {cfg['label']}. Check the key and network."}
    except Exception as e:  # noqa: BLE001
        logger.exception("openai-compatible stream failed")
        outcome = "provider_error"
        yield {"type": "error", "message": policy.PROVIDER_ERROR if locked else str(e)}
    finally:
        stats.update({k: usage[k] for k in ("input", "cache_read", "cache_write", "output")},
                     est_usd=round(spent, 6), outcome=outcome or "cancelled")
        if stats["narration_dropped"] or stats["answers_held"]:
            logger.info("held back before a lookup: narration steps=%d, checked answers=%d",
                        stats["narration_dropped"], stats["answers_held"])
        _log_usage(model, usage)
        import contextlib
        with contextlib.suppress(Exception):
            await client.close()
