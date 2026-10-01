#!/usr/bin/env python3
"""
Study Bible web front-end.

A streaming chat app that drives the Claude API over the Study Bible MCP tools.
The backend co-locates the MCP server (spawned over stdio, in-process) and runs
the Anthropic streaming tool-use loop, pushing tokens and tool activity to the
browser over Server-Sent Events. The MCP server and API key never leave the
backend.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...        # required
    python -m uvicorn webapp.app:app --port 8100
    # then open http://127.0.0.1:8100
"""

import contextlib
import json
import logging
import os
import secrets
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from webapp import auth, calendar_views, comprehension, course, course_views, curriculum, db, generator, library, library_store, memory, providers, r2, reader, safety, store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("study-bible-web")

MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
PROJECT_ROOT = Path(__file__).parent.parent

# Load ANTHROPIC_API_KEY (and any other secrets) from a repo-root .env, if present.
# The .env is gitignored; the key never leaves the backend.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass
STATIC_DIR = Path(__file__).parent / "static"
PROMPTS_DIR = PROJECT_ROOT / "src" / "studybible_mcp" / "prompts"

NEUTRAL_SYSTEM = (
    "You are the Researcher, a careful and honest Bible-study assistant for pastors, "
    "theologians, and seminary students. Work exegesis-first: establish a passage in its "
    "grammatical, historical, and literary context before drawing theology. "
    "Ground every claim in the Study Bible tools rather than memory, and cite "
    "what you draw on (translation, lexicon, commentary, father, confession). "
    "When you do not know, say so."
)

# Aide mode: a Socratic tutor. It builds the person's own skill in reading Scripture
# rather than handing over finished answers. "Balanced" — facts are fair game (with a
# nudge to verify), but interpretation and application are guided, not given.
STUDY_SYSTEM = (
    "You are the Aide, a patient study guide for a Bible-study app. Your goal is the "
    "learner's own growth "
    "in reading Scripture well, not giving them finished answers to copy. Work like a "
    "patient tutor who wants them to be able to do this without you.\n\n"
    "- FACTS you may give directly: where a passage is, what a word means, a date, a "
    "definition, what a tool returns. But turn each one into learning — name the tool or "
    "source it came from and ask how they would confirm it. Teach them to check, not just "
    "receive.\n"
    "- INTERPRETATION and APPLICATION you do NOT hand over. When they ask what a passage "
    "means, what the author is doing, how it points to Christ, or how it applies to their "
    "life, do not state the conclusion. Guide them to it: have them observe the text, notice "
    "repeated words and connections, read the surrounding context, consult cross-references "
    "and the unit reading guide, and reason it out. Give the next step, not the destination.\n"
    "- If they press for the answer, stay kind but hold the line — your job is their "
    "long-term skill, not a quick answer. Offer a better question or a smaller step.\n"
    "- Ground everything in the Study Bible tools and the course reading guides rather than "
    "memory, and name what you draw on.\n"
    "- Keep it exegesis-first: the text in its grammatical, historical, and literary context, "
    "read as one story culminating in Christ."
)

# Shared conduct floor — applied to EVERY mode, above the persona. The chat has a
# pastoral mind but is not the person's pastor; it is a tool, not a companion.
CONDUCT_FLOOR = (
    "\n\n---\n\n"
    "## How you relate to the person (every mode)\n"
    "- You are a study tool, not a friend, companion, or spiritual authority. Do not build a "
    "personal relationship or invite ongoing emotional dependence on you. Do not use language "
    "that implies you have feelings, an inner life, or a soul. Speak warmly and gently, but "
    "never pretend to feel — you are software.\n"
    "- A pastoral mind is not the same as shepherding. You may explain Scripture with pastoral "
    "care and wisdom, but you are not this person's pastor, counselor, or discipler, and you do "
    "not take up the ongoing care of their soul.\n"
    "- When someone needs shepherding — personal spiritual counsel, a besetting sin, a crisis of "
    "faith or of life, grief, or a decision that needs a wise human who knows them — say so "
    "plainly and point them to a real person: a parent, a pastor, a trusted teacher, or a good "
    "friend. Offer the truth of Scripture, then hand them to their people; do not become the "
    "substitute.\n"
    "- Never flatter. Be honest, kind, and concise."
)


def _theologian_system() -> str:
    try:
        return (PROMPTS_DIR / "theologian.md").read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("theologian.md not found; using neutral system prompt")
        return NEUTRAL_SYSTEM


def _voice() -> str:
    try:
        return (PROMPTS_DIR / "voice.md").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _base_for(persona: str) -> str:
    # Legacy ids (theologian/study/neutral) accepted alongside the new mode names so a
    # cached client or a saved chat keeps working.
    if persona in ("professor", "theologian"):
        return _theologian_system()
    if persona in ("aide", "study"):
        return STUDY_SYSTEM
    return NEUTRAL_SYSTEM


def _system_for(persona: str) -> str:
    base = _base_for(persona)
    v = _voice()
    system = f"{base}\n\n---\n\n{v}" if v else base
    # Curriculum awareness, then the shared conduct floor and the crisis-safeguarding
    # note last, so the guardrails carry recency weight over the persona.
    return system + curriculum.system_note() + CONDUCT_FLOOR + safety.safeguarding_note()


# ---------------------------------------------------------------------------
# MCP session (the co-located Study Bible server, spawned over stdio)
# ---------------------------------------------------------------------------
class MCPBridge:
    """Owns a long-lived MCP client session and exposes its tools."""

    def __init__(self) -> None:
        self.session: ClientSession | None = None
        self.tools: list[dict] = []
        self._stdio_cm = None
        self._session_cm = None

    async def start(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "studybible_mcp.server", "--transport", "stdio"],
            env={**os.environ},
            cwd=str(PROJECT_ROOT),
        )
        self._stdio_cm = stdio_client(params)
        read, write = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read, write)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()
        result = await self.session.list_tools()
        self.tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in result.tools
        ]
        # Aggregate the local, student-facing John curriculum tools alongside the
        # study-bible MCP tools. All providers read from self.tools and dispatch
        # through self.call, so this is the only wiring needed.
        self.tools += curriculum.TOOLS
        logger.info(
            "MCP connected: %d tools (+%d curriculum)",
            len(self.tools) - len(curriculum.TOOLS), len(curriculum.TOOLS),
        )

    async def stop(self) -> None:
        with contextlib.suppress(Exception):
            if self._session_cm:
                await self._session_cm.__aexit__(None, None, None)
        with contextlib.suppress(Exception):
            if self._stdio_cm:
                await self._stdio_cm.__aexit__(None, None, None)

    async def call(self, name: str, arguments: dict) -> tuple[str, bool]:
        """Call a tool; return (text, is_error)."""
        t0 = time.perf_counter()
        # Local curriculum tools are served in-process (no MCP round-trip).
        if name in curriculum.HANDLER_NAMES:
            try:
                text = curriculum.handle(name, arguments or {})
            except Exception as e:  # noqa: BLE001
                logger.info("tool %s (curriculum) FAILED in %.0f ms", name, (time.perf_counter() - t0) * 1000)
                return f"Tool call failed: {e}", True
            logger.info("tool %s (curriculum) took %.0f ms", name, (time.perf_counter() - t0) * 1000)
            return text, False
        try:
            result = await self.session.call_tool(name, arguments or {})
        except Exception as e:  # noqa: BLE001
            logger.info("tool %s FAILED in %.0f ms", name, (time.perf_counter() - t0) * 1000)
            return f"Tool call failed: {e}", True
        logger.info("tool %s took %.0f ms", name, (time.perf_counter() - t0) * 1000)
        parts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
        text = "\n".join(parts) if parts else "(no textual content returned)"
        return text, bool(getattr(result, "isError", False))


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def chat(request):
    """Stream a response (with tool use) to the browser over SSE, via the chosen provider."""
    body = await request.json()
    persona = body.get("persona", "professor")
    provider = body.get("provider", "anthropic")
    model = body.get("model", "")
    api_key = (body.get("api_key") or "").strip() or None
    incoming = body.get("messages", [])
    messages = []
    for m in incoming:
        if not (m.get("content") and m.get("role") in ("user", "assistant")):
            continue
        msg = {"role": m["role"], "content": m["content"]}
        # Carry the provider-neutral tool exchange so providers.run can rehydrate
        # the model's own earlier tool calls + results (see providers._hist_tools).
        if m["role"] == "assistant" and isinstance(m.get("tools"), list) and m["tools"]:
            msg["tools"] = m["tools"]
        messages.append(msg)
    if not messages:
        return JSONResponse({"error": "no messages"}, status_code=400)

    mcp: MCPBridge = request.app.state.mcp
    system_text = _system_for(persona)

    # Stateless crisis pre-check on the person's own latest message. If it looks like a
    # cry for help, surface the verified "Need help now?" resources before the reply
    # streams. Notifies no one, stores nothing (see safety.py).
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    pre = safety.precheck(last_user)

    async def gen():
        yield _sse({"type": "start", "persona": persona, "provider": provider})
        if pre["concern"]:
            yield _sse({"type": "safety", "category": pre["category"],
                        "resources": safety.get_crisis_resources(pre["category"])})
        try:
            async for ev in providers.run(provider, api_key, model, system_text, messages, mcp):
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            logger.exception("chat dispatch failed")
            yield _sse({"type": "error", "message": str(e)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def config(request):
    """Tell the front-end what the backend has: tools, providers, default model."""
    mcp: MCPBridge = request.app.state.mcp
    return JSONResponse({
        "tools": len(mcp.tools),
        "tool_names": [t["name"] for t in mcp.tools],
        "default_model": MODEL,
        "providers": providers.public_providers(),
        # The server ships an Anthropic key, so Anthropic works with no BYOK.
        "server_anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        # Verified crisis resources for the always-available "Need help now?" panel.
        "crisis_resources": safety.get_crisis_resources(),
    })


async def index(request):
    return FileResponse(STATIC_DIR / "index.html")


# ---------------------------------------------------------------------------
# Resource generator (standards-aligned)
# ---------------------------------------------------------------------------
async def generate_page(request):
    return FileResponse(STATIC_DIR / "generate.html")


async def library_page(request):
    return FileResponse(STATIC_DIR / "library.html")


async def corpus_page(request):
    """The source-corpus inventory ('everything the connector can cite'), linked from the chat info icon."""
    return FileResponse(STATIC_DIR / "corpus.html")


# ---------------------------------------------------------------------------
# Course view (browsable Gospel of John materials: day / week / month / unit)
# ---------------------------------------------------------------------------
def _view(request) -> str:
    return "teacher" if request.query_params.get("view") == "teacher" else "student"


async def course_overview(request):
    m = course.build_manifest()
    return HTMLResponse(course_views.overview(m, view=_view(request), here=request.url.path))


async def course_unit(request):
    m, view, here = course.build_manifest(), _view(request), request.url.path
    body = course_views.unit(m, request.path_params["key"], view=view, here=here)
    if body is None:
        return HTMLResponse(course_views.not_found("No such unit.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def course_day(request):
    m, view, here = course.build_manifest(), _view(request), request.url.path
    body = course_views.day(m, request.path_params["date"], view=view, here=here)
    if body is None:
        return HTMLResponse(course_views.not_found("No lesson on that date.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def course_week(request):
    m, view, here = course.build_manifest(), _view(request), request.url.path
    body = course_views.week(m, request.path_params["week"], view=view, here=here)
    if body is None:
        return HTMLResponse(course_views.not_found("No such week.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def course_month(request):
    m, view, here = course.build_manifest(), _view(request), request.url.path
    body = course_views.month(m, request.path_params["month"], view=view, here=here)
    if body is None:
        return HTMLResponse(course_views.not_found("No such month.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def course_doc(request):
    m, view, here = course.build_manifest(), _view(request), request.url.path
    art = course_views.find_artifact(m, request.path_params["file"])
    if not art:
        return HTMLResponse(course_views.not_found("No such document.", view=view, here=here), status_code=404)
    if art["audience"] == "teacher" and view != "teacher":
        return HTMLResponse(course_views.forbidden(view=view, here=here), status_code=403)
    return HTMLResponse(course_views.doc(m, art, view=view, here=here))


# ---------------------------------------------------------------------------
# Course calendar (daily + weekly views over the authoritative course calendar)
# ---------------------------------------------------------------------------
async def calendar_home(request):
    view, here = _view(request), request.url.path
    return HTMLResponse(calendar_views.week(calendar_views.default_week(), view=view, here=here))


async def calendar_week_route(request):
    view, here = _view(request), request.url.path
    try:
        body = calendar_views.week(request.path_params["date"], view=view, here=here)
    except ValueError:
        return HTMLResponse(course_views.not_found("Not a valid week.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def calendar_day_route(request):
    view, here = _view(request), request.url.path
    body = calendar_views.day(request.path_params["date"], view=view, here=here)
    if body is None:
        return HTMLResponse(course_views.not_found("No lesson or event on that date.", view=view, here=here), status_code=404)
    return HTMLResponse(body)


async def library_books(request):
    q = request.query_params.get("q", "")
    return JSONResponse({"results": await library.search_books(q, 10)})


async def library_podcasts(request):
    q = request.query_params.get("q", "")
    return JSONResponse({"results": await library.search_podcasts(q, 10)})


async def library_video(request):
    data = await library.preview_video(request.query_params.get("url", ""))
    if not data:
        return JSONResponse({"ok": False})
    return JSONResponse({"ok": True, "preview": data})


async def library_youtube(request):
    q = request.query_params.get("q", "")
    return JSONResponse({"results": await library.search_youtube(q, 12),
                         "configured": bool(os.environ.get("YOUTUBE_API_KEY"))})


async def standards_tree(request):
    return JSONResponse(generator.TREE)


async def standards_objectives(request):
    stid = request.query_params.get("sub_topic", "")
    return JSONResponse({"objectives": generator.objectives_for(stid)})


async def standards_search(request):
    q = request.query_params.get("q", "")
    return JSONResponse({"results": generator.search_standards(q, 25)})


async def formats_endpoint(request):
    return JSONResponse({"formats": generator.format_list(),
                         "grade_bands": generator.grade_bands()})


async def recommend_endpoint(request):
    ss = request.query_params.get("sub_subject", "")
    return JSONResponse({"recommended": generator.recommend(ss)})


async def generate_book_endpoint(request):
    """Living Library redesign: generate a resource FROM a book (read live from books.db), calibrated
    to the student's position in it. Feeds the whole work when it fits (omniscient comprehension) plus
    a position marker for the covered range. See docs/living-library-generation-plan.md."""
    body = await request.json()
    format_id = body.get("format_id")
    if format_id not in generator.FORMATS:
        return JSONResponse({"error": "unknown format"}, status_code=400)
    slug = (body.get("book_slug") or "").strip()
    if not slug:
        return JSONResponse({"error": "book_slug required"}, status_code=400)
    coverage = body.get("coverage") or {}
    grade_band = body.get("grade_band", "secondary")
    brief = body.get("brief", "")
    provider = body.get("provider", "anthropic")
    model = body.get("model", "")
    api_key = (body.get("api_key") or "").strip() or None

    book = await run_in_threadpool(reader._gen_book_sync, slug)
    if not book or not book.get("chapters"):
        return JSONResponse({"error": "book not found"}, status_code=404)

    system_text = generator.build_system(format_id, grade_band)
    total = book.get("word_count") or sum(c.get("words", 0) for c in book["chapters"])
    if total <= generator._GEN_WORD_BUDGET:                       # fits: feed the whole work
        task = generator.build_book_task(format_id, book, coverage, grade_band, brief)
    else:                                                          # large: whole-work comprehension + covered text
        comp = await comprehension.ensure(book)
        if not comp:                                              # can't build (no key/failure) → Phase-1 degradation
            task = generator.build_book_task(format_id, book, coverage, grade_band, brief)
        else:
            covered, cov_desc, _ = generator._coverage(coverage, book["chapters"])
            query = f'{generator.FORMATS[format_id]["name"]}. {brief} {book["title"]} {cov_desc}'.strip()
            covered_text, retrieved = await run_in_threadpool(
                comprehension.select_covered_text, book, covered, query, generator._GEN_WORD_BUDGET)
            recap = comprehension.recap_before(comp, min(covered) if covered else 1)
            task = generator.build_book_task_large(format_id, book, coverage, grade_band, brief,
                                                   comp, covered_text, recap, retrieved)
    mcp: MCPBridge = request.app.state.mcp

    async def gen():
        yield _sse({"type": "start", "format": format_id, "provider": provider, "book": book["slug"]})
        try:
            async for ev in providers.run(provider, api_key, model, system_text,
                                          [{"role": "user", "content": task}], mcp):
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            logger.exception("book generate dispatch failed")
            yield _sse({"type": "error", "message": str(e)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def generate_endpoint(request):
    """Standards-mode generation: assemble the prompt from selected academic-spine
    objectives and stream the resource (with tool use). Book-mode uses
    /api/generate/book instead."""
    body = await request.json()
    format_id = body.get("format_id")
    if format_id not in generator.FORMATS:
        return JSONResponse({"error": "unknown format"}, status_code=400)
    objectives = body.get("objectives") or []
    if not objectives:
        return JSONResponse({"error": "select at least one objective"}, status_code=400)

    grade_band = body.get("grade_band", "secondary")
    context = body.get("context") or {}
    brief = body.get("brief", "")
    provider = body.get("provider", "anthropic")
    model = body.get("model", "")
    api_key = (body.get("api_key") or "").strip() or None

    system_text = generator.build_system(format_id, grade_band)
    task = generator.build_task(format_id, objectives, grade_band, context, brief)
    mcp: MCPBridge = request.app.state.mcp

    async def gen():
        yield _sse({"type": "start", "format": format_id, "provider": provider})
        try:
            async for ev in providers.run(provider, api_key, model, system_text,
                                          [{"role": "user", "content": task}], mcp):
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            logger.exception("generate dispatch failed")
            yield _sse({"type": "error", "message": str(e)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


async def revise_endpoint(request):
    """Apply a targeted change to an existing resource and stream the updated doc."""
    body = await request.json()
    document = (body.get("document") or "").strip()
    instruction = (body.get("instruction") or "").strip()
    if not document or not instruction:
        return JSONResponse({"error": "document and instruction are required"}, status_code=400)
    provider = body.get("provider", "anthropic")
    model = body.get("model", "")
    api_key = (body.get("api_key") or "").strip() or None
    system_text, task = generator.build_revision(document, instruction)
    mcp: MCPBridge = request.app.state.mcp

    async def gen():
        yield _sse({"type": "start", "provider": provider})
        try:
            async for ev in providers.run(provider, api_key, model, system_text,
                                          [{"role": "user", "content": task}], mcp):
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            logger.exception("revise dispatch failed")
            yield _sse({"type": "error", "message": str(e)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# SQLite DBs distributed via R2 → the Fly volume: (env var holding the local path, R2 object key).
# A DB is fetched only when R2 holds a version marker for it, so listing one here is a no-op until
# it's actually published — safe to keep both.
_R2_DBS = [
    ("STUDY_BIBLE_DB", "study-bible/study_bible.db"),
    ("THEOLOGY_DB", "theology/theology.db"),
    ("BOOKS_DB", "books/books.db"),
    ("COVERS_DB", "covers/covers.db"),
]


async def _fetch_db_if_stale(name: str, path: str, key: str):
    """Download one R2-distributed DB to `path` if missing or a newer version exists. Version-gated
    against a small marker object; non-fatal on failure (the feature degrades, the app still boots)."""
    try:
        remote_ver = ((await r2.get_bytes_async(key + ".version")) or b"").decode().strip()
    except Exception:  # noqa: BLE001
        remote_ver = ""
    if not remote_ver:
        return  # not published to R2 → leave whatever is on disk / in the image
    ver_path = path + ".version"
    local_ver = ""
    with contextlib.suppress(Exception):
        if os.path.exists(path) and os.path.exists(ver_path):
            with open(ver_path) as f:
                local_ver = f.read().strip()
    if local_ver == remote_ver and os.path.exists(path):
        logger.info("%s up to date (v%s)", name, remote_ver)
        return
    logger.info("%s: fetching v%s from R2…", name, remote_ver)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        await r2.download_file_async(key, tmp)
        os.replace(tmp, path)
        with open(ver_path, "w") as f:
            f.write(remote_ver)
        logger.info("%s ready (v%s)", name, remote_ver)
    except Exception as e:  # noqa: BLE001
        logger.warning("%s fetch failed: %s", name, e)


async def _ensure_r2_dbs():
    """Boot-fetch the R2-distributed SQLite DBs onto the volume before the MCP starts."""
    if not r2.configured():
        return
    for env_var, key in _R2_DBS:
        path = os.environ.get(env_var)
        if path:
            await _fetch_db_if_stale(env_var, path, key)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    await _ensure_r2_dbs()   # before the MCP starts, so it can open/attach the DBs
    app.state.mcp = MCPBridge()
    await app.state.mcp.start()
    # Optional DB pool. A missing DATABASE_URL, or a connection failure, must never
    # take the app down — DB-backed features simply stay off until it's reachable.
    if db.dsn():
        try:
            await db.init_pool()
            logger.info("Database pool ready")
        except Exception as e:  # noqa: BLE001
            logger.warning("Database unavailable, continuing without it: %s", e)
    else:
        logger.info("DATABASE_URL not set; database features disabled")
    logger.info("Google sign-in: %s", "configured" if auth.configured() else "not configured")
    try:
        yield
    finally:
        await db.close_pool()
        await app.state.mcp.stop()


SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
if not os.environ.get("SESSION_SECRET"):
    logger.warning("SESSION_SECRET not set; using an ephemeral dev secret (sessions reset on restart)")

# Inngest serve endpoint (durable extraction worker). Built here so a missing/broken
# Inngest config disables the worker rather than taking the whole app down.
try:
    from webapp import inngest_app
    _inngest_serve_app = inngest_app.build_serve_app()
except Exception:  # noqa: BLE001
    logger.warning("Inngest serve endpoint disabled (not configured)", exc_info=True)
    _inngest_serve_app = None

class CanonicalHostMiddleware:
    """Redirect the ``www.`` host to the bare apex so the app has one canonical origin.

    Without this, ``www.exegetica.app`` and ``exegetica.app`` are *separate origins*:
    the session cookie is host-only (SessionMiddleware sets no ``domain``) and the Google
    OAuth ``redirect_uri`` is built from the request host (see auth._redirect_uri). So a
    sign-in begun on ``www`` gets a ``www`` state cookie and a ``www`` callback that the
    apex-registered Google client can't complete — leaving ``www`` visitors stuck while the
    apex works fine. Collapsing to a single origin removes that whole class of bug.

    Runs before SessionMiddleware, so a ``www`` request is redirected before it touches any
    session, cookie, or auth state. Inert off ``www`` (localhost/apex fall straight through)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            host = ""
            for k, v in scope.get("headers") or ():
                if k == b"host":
                    host = v.decode("latin-1")
                    break
            name = host.split(":", 1)[0].lower()
            if name.startswith("www.") and len(name) > 4:
                path = scope.get("raw_path") or scope.get("path", "").encode()
                if isinstance(path, str):
                    path = path.encode("latin-1")
                target = "https://" + name[4:] + path.decode("latin-1")
                qs = scope.get("query_string") or b""
                if qs:
                    target += "?" + qs.decode("latin-1")
                # 308: permanent + preserves method/body, so every verb (GET pages, POST APIs)
                # lands correctly on the apex.
                await RedirectResponse(target, status_code=308)(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = Starlette(
    lifespan=lifespan,
    middleware=[
        Middleware(CanonicalHostMiddleware),
        Middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax",
                   https_only=bool(os.environ.get("FLY_APP_NAME"))),
    ],
    routes=[
        Route("/", index),
        Route("/generate", generate_page),
        Route("/library", library_page),
        Route("/corpus", corpus_page),
        Route("/memory", memory.memory_page),
        Route("/api/memory/text", memory.memory_text),
        Route("/api/memory/audio", memory.memory_audio),
        Route("/api/memory", store.memory_get, methods=["GET"]),
        Route("/api/memory", store.memory_put, methods=["PUT"]),
        Route("/api/chats", store.chat_get, methods=["GET"]),
        Route("/api/chats", store.chat_put, methods=["PUT"]),
        Route("/course", course_overview),
        Route("/course/unit/{key}", course_unit),
        Route("/course/day/{date}", course_day),
        Route("/course/week/{week}", course_week),
        Route("/course/month/{month}", course_month),
        Route("/course/doc/{file}", course_doc),
        Route("/calendar", calendar_home),
        Route("/calendar/week/{date}", calendar_week_route),
        Route("/calendar/day/{date}", calendar_day_route),
        Route("/api/library/books", library_books),
        Route("/api/library/podcasts", library_podcasts),
        Route("/api/library/video", library_video),
        Route("/api/library/youtube", library_youtube),
        Route("/api/library/shelf", library_store.shelf_get, methods=["GET"]),
        Route("/api/library/shelf", library_store.shelf_add, methods=["POST"]),
        Route("/api/library/catalog", library_store.catalog_search, methods=["GET"]),
        Route("/api/library/shelf/{id}", library_store.shelf_remove, methods=["DELETE"]),
        Route("/api/library/shelf/{id}/cover", library_store.shelf_set_cover, methods=["POST"]),
        Route("/api/library/cover/{id}", library_store.cover_serve, methods=["GET"]),
        Route("/api/library/extract", library_store.extract_request, methods=["POST"]),
        Route("/api/library/extract/{id}", library_store.extract_status, methods=["GET"]),
        Route("/api/library/extraction/{id}", library_store.extraction_detail, methods=["GET"]),
        Route("/api/library/upload/presign", library_store.upload_presign, methods=["POST"]),
        Route("/api/library/upload/complete", library_store.upload_complete, methods=["POST"]),
        Route("/api/library/reviews", library_store.reviews_list, methods=["GET"]),
        Route("/api/library/reviews/promote", library_store.review_promote, methods=["POST"]),
        Route("/api/library/reviews/reject", library_store.review_reject, methods=["POST"]),
        Route("/read", reader.reader_page),
        Route("/read/{slug}", reader.reader_page),
        Route("/api/books", reader.books_list),
        Route("/api/shelves", reader.shelves),
        Route("/api/catalog", reader.catalog),
        Route("/api/cover/{slug}", reader.cover_image),
        Route("/api/books/{slug}", reader.book_detail),
        Route("/api/books/{slug}/chapter/{n}", reader.book_chapter),
        Route("/api/reading/position", reader.position_get, methods=["GET"]),
        Route("/api/reading/position", reader.position_put, methods=["PUT"]),
        Route("/api/reading/cover", reader.cover_put, methods=["PUT"]),
        Route("/api/reading/cover/search", reader.cover_search, methods=["GET"]),
        Route("/api/config", config),
        Route("/auth/login", auth.login, name="auth_login"),
        Route("/auth/google/callback", auth.auth_callback, name="auth_callback"),
        Route("/auth/logout", auth.logout, name="auth_logout"),
        Route("/api/me", auth.me),
        Route("/api/chat", chat, methods=["POST"]),
        Route("/api/standards/tree", standards_tree),
        Route("/api/standards/objectives", standards_objectives),
        Route("/api/standards/search", standards_search),
        Route("/api/formats", formats_endpoint),
        Route("/api/recommend", recommend_endpoint),
        Route("/api/generate", generate_endpoint, methods=["POST"]),
        Route("/api/generate/book", generate_book_endpoint, methods=["POST"]),
        Route("/api/revise", revise_endpoint, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ],
)

# Mount the Inngest serve endpoint at /api/inngest (its FastAPI sub-app serves at "/",
# with public_path telling Inngest the real path). Appended so it's optional.
if _inngest_serve_app is not None:
    app.router.routes.append(Mount("/api/inngest", app=_inngest_serve_app))
