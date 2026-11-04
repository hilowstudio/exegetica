"""The supervised MCP bridge against a real stdio server (tests/fake_mcp_server.py): a server
that dies mid-call is respawned and the next call works, a slow tool is cut off at the timeout,
and nothing raises into the caller (webapp/bridge.py). Local subprocesses only; no network."""
import asyncio
import time

from webapp import bridge as bridgemod


def test_bridge_survives_a_dead_server_and_a_slow_tool(monkeypatch):
    monkeypatch.setattr(bridgemod, "TOOL_TIMEOUT", 2.0)

    async def go():
        b = bridgemod.MCPBridge("tests.fake_mcp_server", with_curriculum=False)
        await b.start()
        try:
            assert {t["name"] for t in b.tools} == {"echo", "slow", "die"}
            assert await b.call("echo", {"text": "logos"}) == ("logos", False)
            assert await b.ping()

            # The server dies mid-call: the caller gets a plain failure, never an exception.
            text, is_error = await b.call("die", {})
            assert is_error and text == bridgemod.LIBRARY_DOWN

            # The supervisor respawns it, and the next call works.
            t0 = time.monotonic()
            assert await b.call("echo", {"text": "again"}) == ("again", False)
            assert time.monotonic() - t0 < 10 and b.restarts >= 1

            # A tool past the timeout is cut off and reported as failed.
            t0 = time.monotonic()
            text, is_error = await b.call("slow", {"seconds": 6})
            assert is_error and text == bridgemod.TOO_SLOW
            assert time.monotonic() - t0 < 5
        finally:
            await b.stop()

    asyncio.run(asyncio.wait_for(go(), 60))
