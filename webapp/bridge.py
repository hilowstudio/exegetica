"""
The co-located MCP servers (Study Bible, Social Sciences), spawned over stdio and supervised
(docs/harness-maturity-proposal.md, Layer 2).

Each bridge owns its client session inside a task of its own. The SDK's stdio client runs task
groups that cancel the task that opened them when the connection breaks; opened in the app's
lifespan, that cancelled the lifespan itself and closed the Neon pool while the server kept
serving. Here a broken connection ends only the supervisor's attempt, and the supervisor
respawns the server with backoff. A tool call that outlasts TOOL_TIMEOUT is reported as failed.
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
import os
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import CONNECTION_CLOSED

from webapp import curriculum

logger = logging.getLogger("study-bible-web")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOL_TIMEOUT = 30.0       # seconds; the servers give up at 25 and return their own error first
START_TIMEOUT = 180.0     # first connection, which may include the server opening large databases
RECONNECT_WAIT = 10.0     # how long a call waits for a respawned server before giving up

LIBRARY_DOWN = "The library did not answer. It may be restarting. Try again shortly."
TOO_SLOW = "This library tool took too long and was stopped. Ask for something narrower."


class MCPBridge:
    """Owns a long-lived, supervised MCP client session and exposes its tools."""

    def __init__(self, module: str = "studybible_mcp.server", with_curriculum: bool = True) -> None:
        self.module = module
        self.with_curriculum = with_curriculum
        self.session: ClientSession | None = None
        self.tools: list[dict] = []
        self.restarts = 0
        self.timeouts = 0
        self.last_error: str | None = None   # an exception class name, for /ops
        self._task: asyncio.Task | None = None
        self._live = asyncio.Event()      # set while a session is connected
        self._settled = asyncio.Event()   # set once the first attempt has connected or failed
        self._broken = asyncio.Event()    # set to end the current session (dead connection, stop)
        self._stopping = asyncio.Event()
        self._closing = False

    async def start(self) -> None:
        """Start supervising, and wait for the first connection so a broken server fails boot loudly."""
        self._task = asyncio.create_task(self._supervise(), name=f"mcp:{self.module}")
        try:
            await asyncio.wait_for(self._settled.wait(), START_TIMEOUT)
        except asyncio.TimeoutError:
            pass
        if not self._live.is_set():
            await self.stop()
            raise RuntimeError(f"MCP server {self.module} did not start ({self.last_error or 'timeout'})")

    async def stop(self) -> None:
        self._closing = True
        self._stopping.set()
        self._broken.set()
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(asyncio.shield(self._task), 10)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):  # noqa: BLE001
                self._task.cancel()

    async def _supervise(self) -> None:
        delay = 1.0
        while not self._closing:
            began = time.monotonic()
            try:
                await self._serve_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001  (includes the SDK's exception groups)
                self.last_error = type(e).__name__
                logger.warning("MCP %s session ended: %s", self.module, self.last_error)
            self.session = None
            self._live.clear()
            self._settled.set()
            if self._closing:
                return
            if time.monotonic() - began > 60:   # it ran a while before failing: start over quickly
                delay = 1.0
            self.restarts += 1
            logger.info("MCP %s restarting in %.0f s", self.module, delay)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), delay)
            delay = min(delay * 2, 30.0)

    async def _serve_once(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.module, "--transport", "stdio"],
            env={**os.environ},
            cwd=str(PROJECT_ROOT),
        )
        async with stdio_client(params) as (read, write):
            # No session-wide read timeout: the first handshake can take longer than a tool call
            # while the server opens its databases. Tool calls carry their own (see call()).
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), START_TIMEOUT)
                result = await asyncio.wait_for(session.list_tools(), START_TIMEOUT)
                tools = [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                         for t in result.tools]
                # Aggregate the local, student-facing John curriculum tools alongside the
                # study-bible MCP tools. All providers read from self.tools and dispatch
                # through self.call, so this is the only wiring needed.
                extra = curriculum.TOOLS if self.with_curriculum else []
                self.tools = tools + extra
                self._broken.clear()
                self.session = session
                self._live.set()
                self._settled.set()
                logger.info("MCP %s connected: %d tools (+%d curriculum)", self.module, len(tools), len(extra))
                await self._broken.wait()

    def _mark_broken(self, session) -> None:
        """End `session` so the supervisor respawns the server (ignored if it was already replaced)."""
        if session is not None and session is self.session:
            self.session = None
            self._live.clear()
            self._broken.set()

    async def _wait_live(self, timeout: float) -> ClientSession | None:
        try:
            await asyncio.wait_for(self._live.wait(), timeout)
        except asyncio.TimeoutError:
            return None
        return self.session

    async def ping(self, timeout: float = 10.0) -> bool:
        """True if the server answers a ping. A server that doesn't is restarted."""
        session = self.session
        if session is None:
            return False
        try:
            await asyncio.wait_for(session.send_ping(), timeout)
            return True
        except Exception:  # noqa: BLE001
            logger.warning("MCP %s missed a ping; restarting it", self.module)
            self._mark_broken(session)
            return False

    async def call(self, name: str, arguments: dict) -> tuple[str, bool]:
        """Call a tool; return (text, is_error). Never raises and never outlasts TOOL_TIMEOUT by much."""
        t0 = time.perf_counter()
        # Local curriculum tools are served in-process (no MCP round-trip).
        if self.with_curriculum and name in curriculum.HANDLER_NAMES:
            try:
                text = curriculum.handle(name, arguments or {})
            except Exception as e:  # noqa: BLE001
                logger.info("tool %s (curriculum) FAILED in %.0f ms", name, (time.perf_counter() - t0) * 1000)
                return f"Tool call failed: {e}", True
            logger.info("tool %s (curriculum) took %.0f ms", name, (time.perf_counter() - t0) * 1000)
            return text, False
        for attempt in (1, 2):
            session = self.session or await self._wait_live(RECONNECT_WAIT)
            if session is None:
                logger.info("tool %s: library unavailable", name)
                return LIBRARY_DOWN, True
            try:
                result = await asyncio.wait_for(
                    session.call_tool(name, arguments or {}, read_timeout_seconds=dt.timedelta(seconds=TOOL_TIMEOUT)),
                    TOOL_TIMEOUT + 2)
            except asyncio.TimeoutError:
                return self._timed_out(name, t0, session)
            except McpError as e:
                if e.error.code == 408:   # the SDK's own read timeout
                    return self._timed_out(name, t0, session)
                if e.error.code == CONNECTION_CLOSED:   # the server died: respawn, then retry once
                    self._mark_broken(session)
                    if attempt == 1:
                        continue
                    return LIBRARY_DOWN, True
                logger.info("tool %s FAILED in %.0f ms", name, (time.perf_counter() - t0) * 1000)
                return f"Tool call failed: {e.error.message}", True
            except Exception as e:  # noqa: BLE001  (a closed stream, a dead process)
                logger.info("tool %s: connection broke (%s)", name, type(e).__name__)
                self._mark_broken(session)
                if attempt == 1:
                    continue
                return LIBRARY_DOWN, True
            logger.info("tool %s took %.0f ms", name, (time.perf_counter() - t0) * 1000)
            parts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
            text = "\n".join(parts) if parts else "(no textual content returned)"
            return text, bool(getattr(result, "isError", False))
        return LIBRARY_DOWN, True

    def _timed_out(self, name: str, t0: float, session) -> tuple[str, bool]:
        self.timeouts += 1
        logger.info("tool %s TIMED OUT after %.0f ms", name, (time.perf_counter() - t0) * 1000)
        # A server past its own deadline may be wedged: check it in the background.
        asyncio.get_running_loop().create_task(self.ping())
        return TOO_SLOW, True


class CombinedTools:
    """Several MCP bridges presented as one tool set, each call routed to the bridge that owns the
    tool. The History mode uses it: its own Social Sciences tools plus the Study Bible's tools (Scripture,
    the church fathers, the creeds and confessions, and the theology library's church history), because
    church history is history. The John-course curriculum tools stay with the Bible mode."""

    def __init__(self, *parts: tuple[MCPBridge, set[str]]) -> None:
        self.tools: list[dict] = []
        self._route: dict[str, MCPBridge] = {}
        for bridge, exclude in parts:
            for t in bridge.tools:
                if t["name"] in exclude or t["name"] in self._route:
                    continue
                self.tools.append(t)
                self._route[t["name"]] = bridge

    async def call(self, name: str, arguments: dict) -> tuple[str, bool]:
        bridge = self._route.get(name)
        if bridge is None:
            return f"Unknown tool: {name}", True
        return await bridge.call(name, arguments)
