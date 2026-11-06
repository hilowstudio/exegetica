"""History mode can be withheld from a site that has its database (docs/decisions/0023). With
HISTORY_MODE=off the Social Sciences server never starts, so /api/config lists no History tools and
the chat page shows no Bible/History toggle. No network."""
from types import SimpleNamespace

from webapp import app as appmod


async def _start(monkeypatch, tmp_path, mode):
    db = tmp_path / "social_sciences.db"
    db.write_bytes(b"")
    monkeypatch.setenv("SOCIAL_SCIENCES_DB", str(db))
    if mode is None:
        monkeypatch.delenv("HISTORY_MODE", raising=False)
    else:
        monkeypatch.setenv("HISTORY_MODE", mode)
    started = []

    class Bridge:
        def __init__(self, *args, **kwargs):
            started.append(args)

        async def start(self):
            pass

    monkeypatch.setattr(appmod, "MCPBridge", Bridge)
    app = SimpleNamespace(state=SimpleNamespace(mcp_history=None))
    await appmod._start_history(app)
    return started, app.state.mcp_history


async def test_history_mode_off_starts_no_server(monkeypatch, tmp_path):
    started, bridge = await _start(monkeypatch, tmp_path, "off")
    assert started == [] and bridge is None


async def test_history_mode_is_on_unless_turned_off(monkeypatch, tmp_path):
    for mode in (None, "on"):
        started, bridge = await _start(monkeypatch, tmp_path, mode)
        assert started == [("socialsci_mcp.server",)] and bridge is not None
