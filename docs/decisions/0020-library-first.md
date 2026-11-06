# 0020: For open models, the library comes before the answer

Decided by A. James Vega, 2026-11-05.

**Decision.** A run with `tool_first` set, which student chat has, puts the library first in the OpenAI-compatible loop.
- Before the model starts, code looks up what the student's message names plainly: a verse, a range, or a whole chapter; a creed, confession or catechism, with any section number written after its name; a course unit, the memory verses, or today's lesson. It makes at most four lookups and uses only the chat's own tools.
- When nothing was looked up, the first answer is held unseen. If it used no library tool, it is set aside and the model is asked once to look first. A reply the system prompt dictates word for word, such as the fixed reply about Exegetica, is shown as written.

The Anthropic loop leaves this off. Opus streams as it writes, and it already looks things up.

**Why.** In the 2026-11-05 bake-off, Nemotron 3.5 Super on DeepInfra answered the prayer request, the graded-reflection request and "How are Christians treated in China today?" with no library at all. A forced tool call would be the direct fix, but DeepInfra's Nemotron endpoint accepts neither tool_choice "required" nor a named function (OpenRouter's routing check, 2026-11-05). Holding the first answer works with any host. On the same day the confession tool began numbering every Westminster and 1689 paragraph, after both Nemotron runs cited sections the tool had misnumbered or failed to find.

**Enforced in.** `RunLimits.tool_first` in `webapp/policy.py`, on for `STUDENT_CHAT`; `plan` in `webapp/prefetch.py`; `_run_openai`, `LOOK_FIRST` and `_from_prompt` in `webapp/providers.py`. Covered by `tests/test_prefetch.py` and `tests/test_open_model_loop.py`.

**Reverse when.** A fine-tuned model reaches for the library on its own as often as Opus on the bake-off set. A held first answer adds a few seconds before the first word appears, so revisit this if students find the wait long.
