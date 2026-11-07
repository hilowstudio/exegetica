"""Open-model bake-off: candidate bases for a fine-tuned Exegetica model, against the live student chat.

Every model answers questions.json under the student chat's own prompt (webapp.app._system_for, the
default persona), the real library tools (both MCP servers, started here), and the student run limits
(policy.CHAT: 8 steps, 16,000 output tokens, $1 a question). Opus 5.5 runs through the app's
own Anthropic path as the baseline. The open models run through OpenRouter, each pinned to one host
that keeps no data (provider.only, zdr, data_collection deny), so a model is never silently served
by another host or quantization. OpenRouter is used here only; the site never routes to it. The round
of 2026-11-06 (DIRECT_RUNS) goes straight to DeepInfra with its own key instead.

Each reply is scored with the app's own checks, all local and free: whether it used the library,
quotations found in neither its tool results nor the bundled Bible (webapp/citations.py), references
to verses that do not exist, what the reply gate would drop or stop (webapp/reply_check.py), first
person, em dashes, the facts a question lists, and the exact self reply. Results go to results/, one
line per question, and a finished question is skipped on a rerun.

    .venv/Scripts/python.exe evals/bakeoff/run.py --dry                 # the plan, no calls
    .venv/Scripts/python.exe evals/bakeoff/run.py --models gemma-4-31b --only b01,b29
    .venv/Scripts/python.exe evals/bakeoff/run.py                       # every model, every question (paid)
    .venv/Scripts/python.exe evals/bakeoff/run.py --models opus-app,nemotron-app   # through the app's own loops
    .venv/Scripts/python.exe evals/bakeoff/run.py --report              # the table, and results/side-by-side.html
"""
import argparse
import asyncio
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).parent
RESULTS = HERE / "results"

OPENROUTER = "https://openrouter.ai/api/v1"
DEEPINFRA = "https://api.deepinfra.com/v1/openai"
BASELINE = "opus-5.5"
OPUS = "claude-opus-5-5"   # the student model until 2026-11-06 (0024), the baseline of the opus-* runs
# (label, OpenRouter model, the one host it may run on). Hosts were checked on 2026-11-05: each keeps
# no data, serves tool calls, and runs the model at bf16, fp8, or the maker's own release.
MODELS = [
    ("glm-5.3-flash", "z-ai/glm-5.3-flash", "fireworks"),
    ("mistral-small-4", "mistralai/mistral-small-2603", "mistral"),
    ("gemma-4-31b", "google/gemma-4-31b-it", "crusoe/bf16"),
    ("gemma-4-26b-a4b", "google/gemma-4-26b-a4b-it", "deepinfra/fp8"),
    ("gpt-oss-120b", "openai/gpt-oss-120b", "together"),
    ("muse-spark-open", "meta/muse-spark-open", "together"),
    ("nemotron-3.5-super", "nvidia/nemotron-3.5-super-vl", "together"),
    ("qwen3.8-27b", "qwen/qwen3.8-27b", "deepinfra/bf16"),
    ("ministral-8b", "mistralai/ministral-8b-2512", "mistral"),
    ("granite-4.2-8b", "ibm-granite/granite-4.2-8b", "deepinfra"),
    ("qwen3.5-9b", "qwen/qwen3.5-9b", "together"),
    # Nemotron's precision: full bf16 against a second 4-bit run on the host the site would use. The
    # Together run above is 4-bit too (NVFP4), so the two 4-bit runs show ordinary run-to-run variation.
    ("nemotron-bf16-crusoe", "nvidia/nemotron-3.5-super-vl", "crusoe/bf16"),
    ("nemotron-fp4-deepinfra", "nvidia/nemotron-3.5-super-vl", "deepinfra/fp4"),
]
EFFORT = "medium"   # reasoning effort where a host takes one, matching the student chat's Opus effort
# Nemotron and five rivals near its price, straight on DeepInfra (2026-11-06): zero retention is standing
# in its terms, and the OpenRouter workspace's model allowlist blocks the newer models. Each label maps
# to the DeepInfra model and its list price that day in the form of providers._PRICES, $ per million
# tokens: (input, output, cached input as a share of the input price).
DIRECT = "deepinfra-direct"
DIRECT_RUNS = {
    "nemotron-direct": ("nvidia/NVIDIA-Nemotron-3.5-Super-VL", (0.15, 0.50, 0.02 / 0.15)),
    "muse-glimmer-direct": ("meta-models/Muse-Glimmer-30B", (0.30, 1.20, 0.04 / 0.30)),
    "inkling-small-direct": ("thinkingmachines/Inkling-Small", (0.45, 1.20, 0.10 / 0.45)),
    "deepseek-v4.1-flash-direct": ("deepseek-ai/DeepSeek-V4.1-Flash-1017", (0.20, 0.60, 0.03)),
    "mimo-v2.6-flash-direct": ("XiaomiMiMo/MiMo-V2.6-Flash", (0.14, 0.28, 0.02)),
    "glm-5.3-flash-direct": ("zai-org/GLM-5.3-Flash", (0.15, 0.50, 0.20)),
}
# The app as a student meets it: each model on the app's own loop, then the reply check, so the
# reply scored is what reaches the browser. Opus runs on the Anthropic loop. An open model runs on the
# OpenAI-compatible loop with the student limits, the library first, and narration held back
# (decisions 0008, 0019, 0020), reached through OpenRouter pinned to one zero-retention host.
APP_RUNS = {"opus-app": (None, None), "nemotron-app": ("nvidia/nemotron-3.5-super-vl", "deepinfra/fp4"),
            # The same two under the prompt rebuilt by decision 0021. Each row carries prompt_sha, the
            # hash of the system prompt it ran under, so runs under different prompts stay apart.
            "opus-app-v2": (None, None), "nemotron-app-v2": ("nvidia/nemotron-3.5-super-vl", "deepinfra/fp4"),
            # Nemotron alone under the prompt of decision 0022, three runs so run-to-run variation shows.
            **{f"nemotron-app-v3{s}": ("nvidia/nemotron-3.5-super-vl", "deepinfra/fp4") for s in ("a", "b", "c")},
            # v3 plus the step-3 line on Greek claims and the occurrence search by book (0022, 2026-11-06)
            **{f"nemotron-app-v4{s}": ("nvidia/nemotron-3.5-super-vl", "deepinfra/fp4") for s in ("a", "b", "c")},
            **{label: (model, DIRECT) for label, (model, _) in DIRECT_RUNS.items()}}


def _key(name: str = "OPENROUTER_API_KEY") -> str:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    return os.environ[name]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_key()}", "X-OpenRouter-Title": "Exegetica bake-off"}


def _done(label: str) -> dict:
    path = RESULTS / f"{label}.jsonl"
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["id"]: r for r in rows}


def _save(label: str, row: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / f"{label}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------
# Scoring, with the app's own checks
# ---------------------------------------------------------------------------------------------

def text_checks(q: dict, reply: str) -> dict:
    """The checks that read only the reply, so the report can redo them after questions.json changes."""
    from webapp import app as appmod

    low = reply.lower()
    facts = q.get("facts") or []
    hit = sum(any(alt.lower() in low for alt in group) for group in facts)
    row = {"facts": f"{hit}/{len(facts)}" if facts else None}
    if q.get("self_reply"):
        # OpenRouter's guardrail redacts the address in the prompt to [EMAIL], so the open models
        # can only echo that; either form counts as the exact reply.
        want = " ".join(appmod.SELF_REPLY.split())
        got = " ".join(reply.split()).replace("[EMAIL]", "hello@hilowstudio.dev")
        row["self_reply_exact"] = want in got
    return row


_FIRST_I = re.compile(r"\bI(?:'m|'ve|'ll|'d)?\b")
_FIRST_ME = re.compile(r"\b(?:me|my|mine|myself)\b", re.I)
_BLOCK = re.compile(r"(?m)^[ \t]*>.*$")


def score(q: dict, reply: str, outputs: list[str]) -> dict:
    from webapp import citations, reply_check

    class Run:   # what quote_check reads from a citations.Recorder
        pass
    run = Run()
    run.outputs = outputs
    local = citations.bible()
    quotes, missing = citations.unfound(reply, citations.Held(outputs), local)
    refs = citations.generator_report(reply, outputs, local)
    gate = reply_check.ReplyGate(quote_ok=citations.quote_check(run, local))
    gate.feed(reply)
    gate.flush()
    plain = reply_check.split_quoted(_BLOCK.sub("", reply))[0]
    first = len(_FIRST_I.findall(plain)) + len(_FIRST_ME.findall(plain))
    return {"used_library": bool(outputs), "quotes": quotes, "quotes_unfound": missing,
            "refs": refs["references"], "refs_missing": refs["missing_references"],
            "gate_dropped": gate.dropped, "gate_stopped": gate.stopped, "first_person": first,
            "em_dashes": reply.count("—"), "chars": len(reply), **text_checks(q, reply)}


# ---------------------------------------------------------------------------------------------
# One question on one model
# ---------------------------------------------------------------------------------------------

async def ask_openrouter(client, model: str, pin: str, params: set, system: str, question: str, tools) -> dict:
    """The student chat's tool loop over OpenRouter's chat completions, without streaming. `params` are
    the request settings the pinned host takes."""
    from webapp import policy, providers

    limits = policy.CHAT
    schemas = providers._openai_tools(tools.tools)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    route = {"only": [pin], "allow_fallbacks": False, "require_parameters": True,
             "data_collection": "deny", "zdr": True}
    text, calls, served = [], [], set()
    cost, steps, tin, tout, tthink = 0.0, 0, 0, 0, 0
    outcome, error = None, None
    for step in range(limits.max_steps):
        final = step and (step == limits.max_steps - 1 or cost >= limits.max_usd)
        body = {"model": model, "messages": messages, "tools": schemas, "max_tokens": limits.max_tokens,
                "provider": route}
        if final and "tool_choice" in params:   # a host without it may still call a tool: step_limit
            body["tool_choice"] = "none"
        if "reasoning" in params:
            body["reasoning"] = {"effort": EFFORT}
        d = None
        for wait in (5, 15, 45, None):   # retries, for a dropped connection, a rate limit, or a host error
            try:
                r = await client.post(f"{OPENROUTER}/chat/completions", headers=_headers(), json=body, timeout=300)
                d = r.json()
            except Exception as e:  # noqa: BLE001
                d, error = None, type(e).__name__
            else:
                if r.status_code == 200 and d.get("choices") and "error" not in d:
                    error = None
                    break
                error = f"HTTP {r.status_code}: {json.dumps(d.get('error', d))[:300]}"
                if r.status_code == 404 and "tool_choice" in body and "tool_choice" in error:
                    del body["tool_choice"]   # a host that takes tool_choice, but not "none"
                    continue
                if r.status_code not in (200, 408, 429) and r.status_code < 500:
                    break   # a request the host will refuse again
            if wait:
                await asyncio.sleep(wait)
        if error:
            outcome = "provider_error"
            break
        steps += 1
        u = d.get("usage") or {}
        cost += u.get("cost") or 0.0
        tin += u.get("prompt_tokens") or 0
        tout += u.get("completion_tokens") or 0
        tthink += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        served.add(d.get("provider") or "?")
        choice = d["choices"][0]
        msg = choice["message"]
        if msg.get("content"):
            text.append(msg["content"])
        tcs = msg.get("tool_calls") or []
        parsed = []
        for tc in tcs:   # arguments that are not a JSON object go back as {}, as the app's own loop does
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = None
            if not isinstance(args, dict):
                tc["function"]["arguments"] = "{}"
            parsed.append((tc, args if isinstance(args, dict) else {}, not isinstance(args, dict)))
        # Hand back the model's own turn, with its reasoning, so a reasoning model keeps its thread.
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls", "reasoning_details")})
        if not tcs:
            outcome = "cut_off" if choice.get("finish_reason") == "length" else \
                "step_limit" if final and step == limits.max_steps - 1 else "complete"
            break
        if final:   # the host ignored the last step's limit, or has no way to set it
            outcome = "step_limit"
            break
        for tc, args, bad in parsed:
            name = tc["function"]["name"]
            out, is_error = await providers._call_tool(tools, name, args)
            calls.append({"name": name, "input": args, "error": bool(is_error), "bad_args": bad})
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
    else:
        outcome = "step_limit"
    return {"reply": "\n\n".join(text), "calls": calls, "outcome": outcome, "error": error, "steps": steps,
            "usd": round(cost, 6), "tokens_in": tin, "tokens_out": tout, "tokens_reasoning": tthink,
            "served_by": sorted(served)}


async def ask_baseline(system: str, question: str, tools) -> dict:
    """Opus 5.5 through the app's own path, exactly as a student's chat runs."""
    from webapp import policy, providers

    text, calls, stats = [], [], {}
    async for ev in providers.run("anthropic", None, OPUS, system,
                                  [{"role": "user", "content": question}], tools,
                                  limits=policy.CHAT, stats=stats):
        if ev["type"] == "text":
            text.append(ev["text"])
        elif ev["type"] == "tool_done":
            calls.append({"name": ev["name"], "input": ev.get("input"), "error": bool(ev.get("error")),
                          "bad_args": False})
    return {"reply": "".join(text), "calls": calls, "outcome": stats.get("outcome"), "error": None,
            "steps": stats.get("steps"), "usd": stats.get("est_usd"),
            "tokens_in": (stats.get("input") or 0) + (stats.get("cache_read") or 0) + (stats.get("cache_write") or 0),
            "tokens_out": stats.get("output"), "tokens_reasoning": None,
            "served_by": [stats.get("model_served") or OPUS]}


async def ask_app(model: str | None, pin: str | None, system: str, question: str, tools) -> dict:
    """One question as the app runs it (APP_RUNS): the model's own loop, then the reply check."""
    from webapp import citations, policy, providers, reply_check

    stats, raw, shown, calls = {}, [], [], []
    gate = reply_check.ReplyGate(quote_ok=citations.quote_check(tools, citations.bible()))
    history = [{"role": "user", "content": question}]
    if model and pin == DIRECT:
        providers._PRICES.setdefault(model, next(p for m, p in DIRECT_RUNS.values() if m == model))
        cfg = {"label": "DeepInfra (eval)", "kind": "openai", "base_url": DEEPINFRA,
               "extra_params": {"reasoning_effort": EFFORT}}
        events = providers._run_openai(cfg, _key("DEEPINFRA_API_KEY"), model, system, history, tools,
                                       policy.CHAT, stats)
    elif model:
        providers._PRICES.setdefault(model, providers._PRICES["nvidia/NVIDIA-Nemotron-3.5-Super-VL"])
        cfg = {"label": "OpenRouter (eval)", "kind": "openai", "base_url": OPENROUTER,
               "extra_params": {"extra_headers": {"X-OpenRouter-Title": "Exegetica bake-off"},
                                "extra_body": {"provider": {"only": [pin], "allow_fallbacks": False,
                                                            "require_parameters": True, "data_collection": "deny",
                                                            "zdr": True},
                                               "reasoning": {"effort": EFFORT}}}}
        events = providers._run_openai(cfg, _key(), model, system, history, tools, policy.CHAT, stats)
    else:
        events = providers.run("anthropic", None, OPUS, system, history, tools,
                               limits=policy.CHAT, stats=stats)
    async for ev in events:
        if ev["type"] == "text":
            raw.append(ev["text"])
            shown += gate.feed(ev["text"])
            continue
        shown += gate.flush()
        if ev["type"] == "tool_done":
            calls.append({"name": ev["name"], "input": ev.get("input"), "error": bool(ev.get("error")),
                          "bad_args": False})
    shown += gate.flush()
    reply = "".join(shown) + (f"\n\n{reply_check.STOP_TEXT}" if gate.stopped else "")
    return {"reply": reply, "raw": "".join(raw), "calls": calls, "outcome": stats.get("outcome"), "error": None,
            "steps": stats.get("steps"), "usd": stats.get("est_usd"),
            "tokens_in": (stats.get("input") or 0) + (stats.get("cache_read") or 0) + (stats.get("cache_write") or 0),
            "tokens_out": stats.get("output"), "tokens_reasoning": None,
            "served_by": [stats.get("model_served") or model or OPUS],
            "prompt_sha": hashlib.sha256(system.encode("utf-8")).hexdigest()[:12],
            "live_dropped": gate.dropped, "live_stopped": gate.stopped, "em_dashes_raw": "".join(raw).count("—"),
            "prefetched": stats.get("prefetched", 0), "lookup_nudges": stats.get("lookup_nudges", 0),
            "narration_dropped": stats.get("narration_dropped", 0), "answers_held": stats.get("answers_held", 0)}


# ---------------------------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------------------------

async def host_params(client) -> dict:
    """{(model, host): the request settings every endpoint of that host takes}, read from OpenRouter."""
    out = {}
    for _, model, pin in MODELS:
        r = await client.get(f"{OPENROUTER}/models/{model}/endpoints", headers=_headers(), timeout=30)
        eps = [e for e in r.json()["data"]["endpoints"]
               if e.get("tag") == pin or (e.get("tag") or "").startswith(pin + "/")]
        sets = [set(e.get("supported_parameters") or []) for e in eps]
        out[(model, pin)] = set.intersection(*sets) if sets else set()
    return out


async def spent(client) -> float:
    r = await client.get(f"{OPENROUTER}/key", headers=_headers(), timeout=30)
    return float(r.json()["data"]["usage"])


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="all", help=f"comma-separated labels, or all (with {BASELINE})")
    ap.add_argument("--only", default="", help="comma-separated question ids")
    ap.add_argument("--cap", type=float, default=20.0, help="stop when this run's OpenRouter spend reaches it")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="rerun questions that already have results")
    ap.add_argument("--retry-failed", action="store_true", help="rerun questions whose result was a provider error")
    ap.add_argument("--dry", action="store_true", help="print the plan and make no calls")
    ap.add_argument("--report", action="store_true", help="summarize results/ and write side-by-side.html")
    ap.add_argument("--page", default="side-by-side.html", help="the report's file name in results/")
    args = ap.parse_args()

    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if args.only:
        keep = set(args.only.split(","))
        questions = [q for q in questions if q["id"] in keep]
    labels = [BASELINE] + [m[0] for m in MODELS] + list(APP_RUNS)
    chosen = labels if args.models == "all" else args.models.split(",")
    unknown = set(chosen) - set(labels)
    if unknown:
        sys.exit(f"unknown models: {sorted(unknown)} (known: {labels})")
    if args.report:
        report(questions, chosen, args.page)
        return
    if args.dry:
        for label in chosen:
            todo = [q["id"] for q in questions if args.force or q["id"] not in _done(label)]
            print(f"{label:<20} {len(todo)} questions to run")
        return

    import httpx
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")   # before the MCP servers start, so they see the Crossway key (ESV default)
    from webapp import app as appmod
    from webapp import citations, curriculum, policy
    from webapp.bridge import CombinedTools, MCPBridge

    bible = MCPBridge()
    history = MCPBridge("socialsci_mcp.server", with_curriculum=False)
    await bible.start()
    await history.start()
    combined = CombinedTools((history, set()), (bible, set(curriculum.HANDLER_NAMES)))
    persona = policy.persona(None)
    systems = {s: appmod._system_for(persona, s) for s in ("bible", "history")}
    gate = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient() as client:
        hosts = await host_params(client)
        start = await spent(client)
        stopped = False
        tally = 0.0   # this run's OpenRouter cost as the replies report it; the key's own total lags

        async def one(label, model, pin, q):
            nonlocal stopped, tally
            async with gate:
                if stopped:
                    return
                if model and max(tally, await spent(client) - start) >= args.cap:
                    stopped = True
                    print(f"[cap] ${args.cap:.2f} reached; stopping")
                    return
                tools = citations.Recorder(bible if q["subject"] == "bible" else combined)
                t0 = time.monotonic()
                try:
                    if label in APP_RUNS:
                        res = await ask_app(model, pin, systems[q["subject"]], q["text"], tools)
                    elif model:
                        res = await ask_openrouter(client, model, pin, hosts[(model, pin)], systems[q["subject"]],
                                                   q["text"], tools)
                    else:
                        res = await ask_baseline(systems[q["subject"]], q["text"], tools)
                except Exception as e:  # noqa: BLE001
                    res = {"reply": "", "calls": [], "outcome": "harness_error", "error": repr(e)[:300]}
                res["seconds"] = round(time.monotonic() - t0, 1)
                if model:
                    tally += res.get("usd") or 0.0
                row = {"id": q["id"], "model": label, **res, **score(q, res.get("reply") or "", tools.outputs)}
                _save(label, row)
                print(f"{label:<20} {q['id']}  {row.get('outcome')!s:<14} {len(row['calls'])} tools  "
                      f"${row.get('usd') or 0:.4f}  {row['seconds']}s")

        jobs = []
        for label in chosen:
            model, pin = APP_RUNS.get(label) or next(((m, p) for lab, m, p in MODELS if lab == label), (None, None))
            have = _done(label)   # a rerun's row is appended, and the latest row for a question wins
            jobs += [one(label, model, pin, q) for q in questions if args.force or q["id"] not in have
                     or args.retry_failed and have[q["id"]].get("outcome") in ("provider_error", "harness_error")]
        await asyncio.gather(*jobs)
        print(f"\nSpend this run: ${max(tally, await spent(client) - start):.4f}")
    await bible.stop()
    await history.stop()


# ---------------------------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------------------------

def report(questions: list[dict], labels: list[str], page_name: str = "side-by-side.html") -> None:
    ids = [q["id"] for q in questions]
    results = {label: _done(label) for label in labels}
    for q in questions:
        for rows in results.values():
            if q["id"] in rows:
                rows[q["id"]].update(text_checks(q, rows[q["id"]].get("reply") or ""))
    cols = ("answered", "library", "tools/q", "tool err", "quotes unfound", "bad refs", "gate drop",
            "gate stop", "1st person", "em dash", "facts", "self reply", "s/q", "$ total")
    print(f"{'model':<20}" + "".join(f"{c:>15}" for c in cols))
    for label in labels:
        rows = [results[label][i] for i in ids if i in results[label]]
        if not rows:
            continue
        n = len(rows)
        fact_rows = [r["facts"] for r in rows if r.get("facts")]
        got = sum(int(f.split("/")[0]) for f in fact_rows)
        of = sum(int(f.split("/")[1]) for f in fact_rows)
        selfr = [r["self_reply_exact"] for r in rows if "self_reply_exact" in r]
        vals = (f"{sum(r.get('outcome') == 'complete' for r in rows)}/{n}",
                f"{sum(r['used_library'] for r in rows)}/{n}",
                f"{sum(len(r['calls']) for r in rows) / n:.1f}",
                str(sum(c['error'] or c['bad_args'] for r in rows for c in r['calls'])),
                f"{sum(len(r['quotes_unfound']) for r in rows)}/{sum(r['quotes'] for r in rows)}",
                f"{sum(len(r['refs_missing']) for r in rows)}/{sum(r['refs'] for r in rows)}",
                str(sum(r['gate_dropped'] for r in rows)), str(sum(r['gate_stopped'] for r in rows)),
                str(sum(r['first_person'] for r in rows)), str(sum(r['em_dashes'] for r in rows)),
                f"{got}/{of}", f"{sum(selfr)}/{len(selfr)}" if selfr else "-",
                f"{sum(r.get('seconds') or 0 for r in rows) / n:.0f}",
                f"{sum(r.get('usd') or 0 for r in rows):.2f}")
        print(f"{label:<20}" + "".join(f"{v:>15}" for v in vals))

    parts = []
    for q in questions:
        cards = []
        for label in labels:
            r = results[label].get(q["id"])
            if not r:
                continue
            tools = ", ".join(c["name"] + (" (failed)" if c["error"] else "") for c in r["calls"]) or "none"
            flags = []
            if r["quotes_unfound"]:
                flags.append("quotes not found: " + "; ".join(r["quotes_unfound"]))
            if r["refs_missing"]:
                flags.append("no such verse: " + ", ".join(r["refs_missing"]))
            if r["gate_stopped"]:
                flags.append("the reply gate would stop this reply")
            if r.get("error"):
                flags.append(r["error"])
            meta = (f"{r.get('outcome')} · {len(r['calls'])} tools · {r.get('seconds')}s · ${r.get('usd') or 0:.4f}"
                    + (f" · facts {r['facts']}" if r.get("facts") else ""))
            cards.append(
                f"<details><summary><b>{html.escape(label)}</b> <span>{html.escape(meta)}</span></summary>"
                f"<p class=tools>Tools: {html.escape(tools)}</p>"
                + "".join(f"<p class=flag>{html.escape(f)}</p>" for f in flags)
                + f"<div class=md>{html.escape(r.get('reply') or '(no reply)')}</div></details>")
        parts.append(f"<section><h2>{q['id']} · {html.escape(q['text'])}</h2>{''.join(cards)}</section>")
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Model bake-off</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1b18;--muted:#6b665d;--line:#e3dfd6;--flag:#9a3412}}
@media (prefers-color-scheme:dark){{:root{{--bg:#191816;--fg:#ece8e1;--muted:#a39d92;--line:#33302b;--flag:#fb923c}}}}
body{{background:var(--bg);color:var(--fg);font:16px/1.55 Georgia,serif;max-width:860px;margin:0 auto;padding:16px}}
h2{{font-size:1.05rem;margin:2rem 0 .5rem}} summary{{cursor:pointer;padding:.35rem 0}} summary span{{color:var(--muted);font-size:.85rem}}
details{{border-top:1px solid var(--line)}} .tools{{color:var(--muted);font-size:.85rem}} .flag{{color:var(--flag);font-size:.85rem}}
.md{{padding:0 0 1rem}} .md pre{{white-space:pre-wrap}}
</style>
<h1>Model bake-off</h1><p>{len(questions)} questions, student chat prompt, real library tools. Open a model to read its reply.</p>
{''.join(parts)}
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script>for(const d of document.querySelectorAll('.md')){{try{{d.innerHTML=marked.parse(d.textContent)}}catch(e){{}}}}</script>"""
    out = RESULTS / page_name
    RESULTS.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
    sys.stdout.flush()
    os._exit(0)   # the MCP servers' stdio threads can hold the process open
