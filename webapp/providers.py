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

# Registry. `kind` selects the code path; `base_url` overrides the OpenAI host.
# default_model is a starting point the user can override in the UI (current
# model IDs for non-Anthropic providers change; the field is editable).
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)", "kind": "anthropic",
        "default_model": "claude-opus-4-8",
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
async def _run_anthropic(api_key, model, system_text, history, mcp):
    import anthropic
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key) if api_key else AsyncAnthropic()
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    try:
        for _turn in range(MAX_TOOL_TURNS):
            async with client.messages.stream(
                model=model, max_tokens=16000, system=system,
                tools=mcp.tools, messages=messages,
                thinking={"type": "adaptive", "display": "summarized"},
            ) as stream:
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

            messages.append({"role": "assistant", "content": final.content})
            if final.stop_reason != "tool_use":
                return
            tool_results = []
            for block in final.content:
                if block.type != "tool_use":
                    continue
                out, is_error = await mcp.call(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": out, "is_error": is_error})
                yield {"type": "tool_done", "name": block.name, "error": is_error}
            messages.append({"role": "user", "content": tool_results})
    except anthropic.APIStatusError as e:
        yield {"type": "error", "message": f"Anthropic API error {e.status_code}: {getattr(e, 'message', str(e))}"}
    except Exception as e:  # noqa: BLE001
        logger.exception("anthropic stream failed")
        yield {"type": "error", "message": str(e)}
    finally:
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
    # Stateless multi-turn: resend the growing input list each turn.
    input_list: list = [{"role": m["role"], "content": m["content"]} for m in history]

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
                out, is_error = await mcp.call(it.name, args)
                input_list.append({"type": "function_call_output",
                                   "call_id": it.call_id, "output": out})
                yield {"type": "tool_done", "name": it.name, "error": is_error}
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
    messages += [{"role": m["role"], "content": m["content"]} for m in history]

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
                out, is_error = await mcp.call(c["name"], args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
                yield {"type": "tool_done", "name": c["name"], "error": is_error}
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
