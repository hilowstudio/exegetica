# 0019: Narration and em dashes come out of a reply before the reader sees it, and the prompt gives the third-person form

Decided by A. James Vega, 2026-11-05.

**Decision.**
- In the OpenAI-compatible loop that open models run on, the text a step writes is held until it has begun a third sentence. A step that calls a tool before then was narrating its next lookup ("Let me pull the passage."), and that text is dropped.
- The reply check rewrites em dashes outside quotation marks. After a short label (a list item, a heading, or bold text) the first one becomes a colon. One that ends the text or meets punctuation goes. Any other becomes a comma. Quotations and blockquotes keep theirs.
- First person stays a prompt rule (docs/decisions/0001). The student prompt now gives the form to use: the tool is "Exegetica" or "this tool", in the third person, and offers and next steps take that form too ("Exegetica can pull the Greek too.").

A check that dropped any short sentence holding a first-person offer was built and taken out the same day. The maker judged it would break on too many edge cases, since an offer often shares its sentence with an instruction or a refusal.

**Why.** In the 2026-11-05 bake-off, Nemotron 3.5 Super wrote in the first person, showed a student its working notes ("I have strong excerpts. Let me pull the full speech text"), and used about one em dash per answer. Opus rarely does any of these. Narration and dashes can be repaired mechanically for whichever model runs. Wording is better taught than cut.

**Enforced in.** `_run_openai` in `webapp/providers.py` (`_HOLD_SENTENCES`); `mend_dashes` in `webapp/reply_check.py`; the first-person rule in `CONDUCT_FLOOR` in `webapp/app.py`. Dropped narration counts toward the metrics row's dropped sentences (`checks_dropped`). Covered by `tests/test_open_model_loop.py` and `tests/test_reply_check.py`.

**Reverse when.** A fine-tuned model stops writing these on the bake-off set, or a dropped stretch of narration turns out to have carried study content.
