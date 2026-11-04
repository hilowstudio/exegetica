# 0008: Every model run has step, output, and spend ceilings

Recorded 2026-11-02 from the harness Loop and Governance spikes.

**Decision.** Each surface has a ceiling on model calls per run, output tokens per call, and estimated spend per run: student and teacher chat 8 steps, 16,000 tokens, $1; Generator 12, 64,000, $5; Revise 3, 64,000, $2. The last allowed step, or the first past the spend ceiling, must answer without calling tools. A reply cut off by its length or step limit says so. A chat transcript may hold 48 messages (24 turns), 8,000 characters per student message, and 120,000 characters in all, with only plain text and records of known tools.

**Why.** One anonymous request could previously spend about $15 in output alone (64,000 tokens times 12 steps), and runs that hit a limit ended silently.

**Enforced in.** `webapp/policy.py`; `_run_anthropic` in `webapp/providers.py`; `clean_history` applied in `chat()`. Every run ends in a named state, a tool call is cut off at 30 seconds (`webapp/bridge.py`), and two all-failed tool steps end the run (docs/decisions/0012). A step that fails before any of its text reaches the reader (overload, rate limit, server error, dropped connection) is retried once per run after two seconds. Text already shown stays, and the run ends with a plain notice. Raw errors go to the server log only. A large book's whole-work comprehension for the Generator is built on Inngest (`build-comprehension` in `webapp/inngest_app.py`): one build per book at a time, at most 40 map calls and one reduce, five calls in flight across all builds, each step retried on its own, and a failed build leaves a marker so the Generator works from the covered text for a day. Covered by `tests/test_policy_and_loop.py`, `tests/test_run_endings.py`, `tests/test_bridge.py`, and `tests/test_comprehension_build.py`.

**Reverse when.** Adjust the numbers from production metrics (`/ops`). Per-account daily caps are in docs/decisions/0011.
