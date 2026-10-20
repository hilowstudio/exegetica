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
  {"type": "error", "message": ...}

The API key is supplied per request and used to build a throwaway client; it is
never stored or logged server-side.
"""

import json
import logging

logger = logging.getLogger("study-bible-web.providers")

MAX_TOOL_TURNS = 12

# Tool results feed the model in full within a turn, and each later step of the tool loop
# re-reads them. Most results run 1-8k chars and the big useful ones (a verse's commentary,
# a long psalm, a theology search) 12-17k, so this cap only trims outliers such as
# multi-chapter passages, and tells the model to ask for less.
_LIVE_TOOL_CAP = 20000


async def _call_tool(mcp, name: str, args: dict) -> tuple[str, bool]:
    out, is_error = await mcp.call(name, args)
    out = out or ""
    if len(out) > _LIVE_TOOL_CAP:
        out = (out[:_LIVE_TOOL_CAP] + f"\n\n[Result truncated: {len(out):,} characters, first "
               f"{_LIVE_TOOL_CAP:,} shown. Request a narrower range if you need the rest.]")
    return out, is_error


# Per-turn token usage, logged so cost and cache health are visible in the Fly logs.
# $ per million tokens: (input, output, cache-read multiplier); cache writes are 1.25x input.
_PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.05), "claude-sonnet-4-6": (3.0, 15.0, 0.10)}


def _log_usage(model: str, u: dict) -> None:
    if not u["requests"]:
        return
    cost = ""
    if model in _PRICES:
        inp, outp, read = _PRICES[model]
        usd = (u["input"] * inp + u["cache_write"] * inp * 1.25 + u["cache_read"] * inp * read
               + u["output"] * outp) / 1e6
        cost = f" est=${usd:.4f}"
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
}


def public_providers() -> list[dict]:
    """Provider metadata safe to expose to the front-end."""
    return [
        {"id": pid, "label": p["label"], "default_model": p["default_model"],
         "fallback_model": p.get("fallback_model"), "key_url": p["key_url"]}
        for pid, p in PROVIDERS.items()
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


def _attempt(cfg, api_key, model, system_text, history, mcp):
    """One streaming attempt on a single model (returns an async generator)."""
    kind = cfg["kind"]
    if kind == "anthropic":
        return _run_anthropic(api_key, model, system_text, history, mcp)
    if kind == "responses":                       # OpenAI: reasoning + tools
        return _run_openai_responses(cfg, api_key, model, system_text, history, mcp)
    return _run_openai(cfg, api_key, model, system_text, history, mcp)  # Grok / Gemini


async def run(provider: str, api_key: str | None, model: str,
              system_text: str, history: list[dict], mcp) -> "AsyncIterator[dict]":
    """Dispatch a streaming, tool-using conversation, with a stable-model fallback.

    Tries the requested model first. If it fails with a model-availability error
    *before* anything has streamed to the user, it retries once on the provider's
    stable fallback model and emits a notice. A failure after content has begun,
    or an auth / rate-limit / server error, is passed through unchanged.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        yield {"type": "error", "message": f"Unknown provider: {provider}"}
        return
    if cfg["kind"] != "anthropic" and not api_key:
        yield {"type": "error", "message": f"An API key is required for {cfg['label']}."}
        return

    requested = (model or "").strip() or cfg["default_model"]
    fallback = cfg.get("fallback_model")
    candidates = [requested] + ([fallback] if fallback and fallback != requested else [])

    for i, current in enumerate(candidates):
        last = i == len(candidates) - 1
        emitted = False
        fell_back = False
        async for ev in _attempt(cfg, api_key, current, system_text, history, mcp):
            if ev["type"] in ("text", "tool_call", "tool_done", "thinking"):
                emitted = True
            if ev["type"] == "error" and not emitted and not last and _is_model_error(ev.get("message", "")):
                yield {"type": "notice",
                       "message": f"Model “{current}” is unavailable — falling back to “{candidates[i + 1]}”."}
                fell_back = True
                break
            yield ev
        if not fell_back:
            return


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


async def _run_anthropic(api_key, model, system_text, history, mcp):
    import anthropic
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    messages = _anthropic_messages(history)

    # Thinking is always on for current models and counts toward max_tokens, so leave
    # room for it plus a long generated document (streaming, so no HTTP timeout risk).
    # The explicit marker on the system prompt caches tools + system (shared by every chat);
    # top-level automatic caching moves a second breakpoint to the end of the conversation
    # on each request, so every step of the tool loop, and the next turn, re-reads the
    # history from cache instead of at full price.
    params = dict(model=model, max_tokens=64000, system=system, tools=mcp.tools,
                  thinking={"type": "adaptive", "display": "summarized"},
                  cache_control={"type": "ephemeral"})
    usage = {"requests": 0, "input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    if model in _EFFORT:
        params["output_config"] = {"effort": _EFFORT[model]}
    fallback = model.startswith(_REFUSAL_FALLBACK_PREFIXES)
    if fallback:
        params.update(betas=[_FALLBACK_BETA], fallbacks="default")
    stream_fn = client.beta.messages.stream if fallback else client.messages.stream

    try:
        for _turn in range(MAX_TOOL_TURNS):
            async with stream_fn(messages=messages, **params) as stream:
                async for event in stream:
                    if event.type == "content_block_start" and \
                            getattr(event.content_block, "type", None) == "tool_use":
                        yield {"type": "tool_call", "name": event.content_block.name}
                    elif event.type == "content_block_delta":
                        d = event.delta
                        if d.type == "text_delta":
                            yield {"type": "text", "text": d.text}
                        elif d.type == "thinking_delta":
                            yield {"type": "thinking", "text": d.thinking}
                final = await stream.get_final_message()
            u = final.usage
            usage["requests"] += 1
            usage["input"] += u.input_tokens or 0
            usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
            usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
            usage["output"] += u.output_tokens or 0

            if final.stop_reason == "refusal":   # declined, and any fallback declined too
                yield {"type": "error",
                       "message": "Claude declined to answer this request. Try rephrasing it, or ask it a different way."}
                return
            content = _after_fallback(final.content)
            messages.append({"role": "assistant", "content": content})
            if final.stop_reason != "tool_use":
                return
            tool_results = []
            for block in content:
                if block.type != "tool_use":
                    continue
                out, is_error = await _call_tool(mcp, block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": out, "is_error": is_error})
                yield {"type": "tool_done", "name": block.name, "input": block.input,
                       "output": _cap(out), "error": is_error}
            messages.append({"role": "user", "content": tool_results})
    except anthropic.APIStatusError as e:
        yield {"type": "error", "message": f"Anthropic API error {e.status_code}: {getattr(e, 'message', str(e))}"}
    except Exception as e:  # noqa: BLE001
        logger.exception("anthropic stream failed")
        yield {"type": "error", "message": str(e)}
    finally:
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
async def _run_openai(cfg, api_key, model, system_text, history, mcp):
    import openai
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=cfg["base_url"])
    tools = _openai_tools(mcp.tools)
    messages = [{"role": "system", "content": system_text}]
    messages += _chat_messages(history)

    extra = cfg.get("extra_params", {})
    try:
        for _turn in range(MAX_TOOL_TURNS):
            stream = await client.chat.completions.create(
                model=model, messages=messages, tools=tools, stream=True, **extra,
            )
            text_parts: list[str] = []
            calls: dict[int, dict] = {}
            announced: set[int] = set()
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    text_parts.append(delta.content)
                    yield {"type": "text", "text": delta.content}
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

            if not calls:
                return  # model finished with text

            # Append the assistant turn (with its tool calls), then each result.
            messages.append({
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                    for c in calls.values()
                ],
            })
            for c in calls.values():
                try:
                    args = json.loads(c["args"]) if c["args"].strip() else {}
                except json.JSONDecodeError:
                    args = {}
                out, is_error = await _call_tool(mcp, c["name"], args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                yield {"type": "tool_done", "name": c["name"], "input": args,
                       "output": _cap(out), "error": is_error}
    except openai.APIStatusError as e:
        yield {"type": "error", "message": f"{cfg['label']} API error {e.status_code}: {getattr(e, 'message', str(e))}"}
    except openai.APIConnectionError:
        yield {"type": "error", "message": f"Could not reach {cfg['label']}. Check the key and network."}
    except Exception as e:  # noqa: BLE001
        logger.exception("openai-compatible stream failed")
        yield {"type": "error", "message": str(e)}
    finally:
        import contextlib
        with contextlib.suppress(Exception):
            await client.close()
