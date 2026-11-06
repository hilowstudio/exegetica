# 0023: History chat is withheld from the site until a broader release

Decided by A. James Vega, 2026-11-06.

**Decision.** The production site offers Bible chat only for now. `HISTORY_MODE = 'off'` in `fly.toml` keeps the Social Sciences server from starting, so `/api/config` lists no History tools, the chat page shows no Bible/History toggle, and a student who last used History starts in Bible chat. A new message in a saved History study gets the "not available" answer. The History database still downloads to the volume, and the Bible chat is unaffected. The maker will release History as part of a broader release.

**Enforced in.** `_start_history` in `webapp/app.py` and `fly.toml`. `scripts/predeploy.py` expects no live History tools while the mode is off. Covered by `tests/test_history_mode.py`.

**Reverse when.** The maker releases History: remove `HISTORY_MODE` from `fly.toml`, or set it to `on`, and deploy.
