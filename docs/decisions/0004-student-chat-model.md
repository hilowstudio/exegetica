# 0004: Student chat runs on one model, and a refusal ends the reply

Decided by A. James Vega, 2026-11-02.

**Decision.** Every student chat request runs on `claude-opus-5-5`. The provider, model, and API key a browser sends are ignored for students. Student chat has no model fallback of any kind: no retry on another model after an error, and no server-side refusal fallback. When the model declines a student's message, the reply ends with a fixed line pointing the student to a trusted adult and the Need help now panel. Teachers keep the provider choice, their own keys, and the fallbacks.

**Why.** On 2026-10-31, Sonnet 4.6, then the automatic fallback, failed the slow-burn safety ladder that Opus 5.5 passed. A fallback that runs an unladdered model on a probing student defeats the ladder. Anyone could also type another model into Settings and use it with no key.

**Enforced in.** `webapp/policy.py` (`STUDENT_MODEL`, `STUDENT_CHAT`, `REFUSAL_TEXT`), `chat()` in `webapp/app.py`, and `run` / `_run_anthropic` in `webapp/providers.py`. Covered by `tests/test_policy_and_loop.py`.

**Reverse when.** Another model may serve students only after the maker has probed it himself and approved it. Safety probing is done by hand by A. James Vega; no automated ladder runs are made on his key (decided 2026-11-02).
