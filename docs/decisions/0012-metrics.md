# 0012: Every model run leaves one row of numbers, and the maker reads them at /ops

Recorded 2026-11-03 from the harness proposal, Layer 7.

**Decision.** Each chat, Generator, and Revise run writes one row to `turn_metrics`: route, key source, requested and served model, a 12-character hash of the prompt and tools, how the run ended, steps, tool errors, token counts, estimated cost, duration, and how many sentences the reply check dropped or stopped. The time is cut to the hour. Fixed replies (greeting, drift, cap, rate limit) write a row with no tokens. Rows are deleted after 90 days.

Never recorded: message text or its hash, tool inputs or outputs, provider error strings, persona, IP, browser, session, email, account id, or key. A test pins each row to this allowlist.

`/ops` is admin-only. It shows 14 UTC days of runs and spend by ending, the libraries' health, the tables' state, and failed metric writes. `/ops/flag` sends the one alert: the first time in a UTC day that estimated spend passes $5, it answers 500, so the keep-warm run fails and GitHub emails the maker. It needs `OPS_FLAG_TOKEN`, set both as a Fly secret and as a GitHub Actions secret.

**Every run ends in one named state:** complete, cut_off, step_limit, budget, tools_failed, refused, provider_error, or cancelled, plus check_stop, greeting, drift, capped, and limited from the app. The chat page treats a stream without an end event as interrupted. Two steps in a row where every tool failed end the run with a plain notice. Students never see a raw provider error.

**Why.** Before this, usage was a log line no one stored, errors logged nothing, and a run cut short looked finished. A user column would turn a cost log into a behaviour log of identifiable minors (QSF DAT-07, DAT-10), so there is none.

**Enforced in.** `webapp/metrics.py`, `webapp/ops.py`, `webapp/providers.py` (`stats`, the end event, and usage tallied from stream events so a closed browser is still costed), and `chat()` and `_generation()` in `webapp/app.py`. Covered by `tests/test_run_endings.py`, `tests/test_chat_route.py`, `tests/test_privacy_and_data.py`.

**Reverse when.** Drop a column that proves useless after two weeks. Do not add a person or text column under any decision.
