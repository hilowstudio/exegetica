# Study Bible Web App

A streaming chat front-end that drives the Claude API over the Study Bible MCP
tools. The backend co-locates the MCP server (spawned over stdio, in-process),
runs the Anthropic streaming tool-use loop, and pushes tokens + tool activity to
the browser over Server-Sent Events. The API key and the MCP server stay on the
backend; the browser only talks to this app.

## Architecture

```
browser (SSE)  ──►  webapp/app.py  ──►  Anthropic API (claude-opus-5-5, streaming)
                         │
                         └──►  studybible_mcp.server (stdio, in-process)  ──►  SQLite
```

- The Claude tool-use loop lives in the backend; on each `tool_use` it calls the
  co-located MCP server and feeds the result back. No public MCP URL and no
  MCP-side OAuth are needed — the app owns the loop.
- The Theologian persona (from `src/studybible_mcp/prompts/theologian.md`) or a
  neutral study-assistant prompt is the system prompt, chosen by the UI toggle
  and cached across requests.

## Resource Generator (`/generate`)

A standards-aligned resource generator. Two layers fuse:

- **quill-standards** (what to teach) → distilled into `webapp/standards/`
  (`standards-tree.json` menu + `standards-objectives.json`, 26,016 objectives).
- **resource-generators.yaml** (how to deliver it) → 74 format archetypes with
  schemas, plus `webapp/standards/format-recommendations.yaml` bridging each of
  the 86 sub-subjects to fitting formats.

Flow: navigate Subject → Sub-subject → Topic → Sub-topic → pick objective(s) →
pick a format (recommended ones surfaced first) → grade band + optional brief →
**Generate**. The backend (`webapp/generator.py`) assembles `global_conventions`
+ the format's schema + the objective text/grade/complexity into a system+task
prompt, runs it through the same provider layer (streaming + tools — so BIB/CFL
resources are grounded in the Study Bible tools), and streams a downloadable
Markdown document stamped with the `standardId`s it targets.

Endpoints: `/api/formats`, `/api/standards/tree`, `/api/standards/objectives`,
`/api/recommend`, `POST /api/generate` (SSE), `POST /api/revise` (SSE). Rebuild
the index after editing the spine: `python scripts/build_standards_index.py`.

The generated document (Markdown is the source of truth) supports:
- **Teacher ↔ Student** — the answer key is always generated as a final
  `## Answer Key` section (after the `Standards:` line); Student view/PDF/export
  hides it, Teacher shows it.
- **PDF in browser** — a paper-styled view + a print stylesheet; the PDF button
  opens the browser's print/save-as-PDF on just the document.
- **Edit & Modify without regenerating** — an Edit mode (raw-Markdown textarea)
  for hand tweaks, and a Modify box that sends the current document + an
  instruction to `/api/revise`, which returns the whole updated document with
  only the requested change applied (structure, header, key, and Standards line
  preserved).

## Providers (bring your own key)

The ⚙ panel lets a viewer choose a model provider, paste their own API key, and
set the model name. Two backend code paths cover four providers
(`webapp/providers.py`):

Model defaults confirmed against each provider's docs (Aug 2026); all editable in
the panel.

| Provider | Path | Default model | Notes |
|---|---|---|---|
| Anthropic (Claude) | native Anthropic SDK | `claude-opus-5-5` | best experience; persona + tools are Claude-tuned. Works with the server key too. |
| OpenAI | OpenAI SDK, **Responses API** | `gpt-5.6` | flagship `gpt-5.6-sol`. Uses the Responses API so **reasoning + function tools** run together (`reasoning.effort="medium"`). |
| xAI Grok | OpenAI SDK, chat completions, `base_url=https://api.x.ai/v1` | `grok-4.6` | flagship |
| Google Gemini | OpenAI SDK, chat completions, `base_url=.../v1beta/openai/` | `gemini-3.1-pro-preview` | Pro tier (Flash alt: `gemini-3.7-flash`); compat endpoint + tools confirmed |

**Stable fallback per provider.** Each provider has a stable `fallback_model`
(Anthropic `claude-sonnet-4-6`, OpenAI `gpt-5.6-terra`, Gemini `gemini-3.7-flash`,
Grok `grok-4.5`). If the chosen model fails with a model-availability error
*before* any text has streamed, the backend retries once on the fallback and
emits a `notice` the UI shows inline. This protects the preview Gemini default in
particular. Failures after streaming has begun, and auth/rate-limit/server
errors, pass through unchanged.

Keys are stored **only in the viewer's browser** (localStorage) and sent to the
backend per request to build a throwaway client — never logged or stored
server-side. The server's own `ANTHROPIC_API_KEY` remains the default for
Anthropic, so it works with no key entered. Model IDs for the non-Anthropic
providers are editable in the panel, since they change over time.

## Run locally

```sh
# from the repo root, with the DB already built (db/study_bible.db)
./.venv/Scripts/python -m pip install -e ".[webapp]"     # POSIX: .venv/bin/python
export ANTHROPIC_API_KEY=sk-ant-...                       # Windows: setx ANTHROPIC_API_KEY ...
python -m uvicorn webapp.app:app --port 8100
# open http://localhost:8100 (Google sign-in is registered for localhost)
```

Optional: `export ESV_API_KEY=...` so the tools can serve live ESV.

## Deploy (hosted path)

Build the container (bakes in the read-only DB) and run it on a container host:

```sh
docker build -t study-bible-web .
docker run -p 8100:8100 -e ANTHROPIC_API_KEY=sk-ant-... study-bible-web
```

The container is stateless (read-only DB), so it scales by replica. Two things
to add for a shared deployment:

1. **User auth** — put an auth proxy in front (Cloudflare Access, or an OAuth
   gate). The app has no auth of its own yet.
2. **Secrets** — provide `ANTHROPIC_API_KEY` (and optionally `ESV_API_KEY`) as
   host secrets, never baked into the image.
