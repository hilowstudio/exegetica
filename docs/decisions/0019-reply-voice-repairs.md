# 0019: Narration and em dashes come out of a reply before the reader sees it, and the prompt gives the third-person form

Decided by A. James Vega, 2026-11-05. The first rule amended 2026-11-06.

**Decision.**
- In the OpenAI-compatible loop that open models run on, a step that may still call a tool shows none of its text until it ends. Text written before a lookup never reaches the reader, whether it narrated the lookup ("Let me pull the passage.") or answered the question. When that text had begun a third sentence, it was a whole answer the model went on to check: the lookup runs, and the next step writes the whole answer with tools withheld. A step offered no tools streams from its first word. The chat shows one chip per tool with a count beside it when the tool ran more than once, so a repeated lookup shows.
- The reply check rewrites em dashes outside quotation marks. After a short label (a list item, a heading, or bold text) the first one becomes a colon. One that ends the text or meets punctuation goes. Any other becomes a comma. Quotations and blockquotes keep theirs.
- First person stays a prompt rule (docs/decisions/0001). The student prompt now gives the form to use: the tool is "Exegetica" or "this tool", in the third person, and offers and next steps take that form too ("Exegetica can pull the Greek too.").

A check that dropped any short sentence holding a first-person offer was built and taken out the same day. The maker judged it would break on too many edge cases, since an offer often shares its sentence with an instruction or a refusal.

**Why.** In the 2026-11-05 bake-off, Nemotron 3.5 Super wrote in the first person, showed a student its working notes ("I have strong excerpts. Let me pull the full speech text"), and used about one em dash per answer. Opus rarely does any of these. Narration and dashes can be repaired mechanically for whichever model runs. Wording is better taught than cut.

The first rule held text only until a third sentence, on the view that text before a lookup is a one-line note. In the maker's probe on 2026-11-06, Nemotron wrote a whole answer, which was already on the student's screen, called `lookup_verse` to check its Leviticus quote, and wrote the answer again from the start. It checked and wrote it a third time. A lookup could drop only text still held, and the tool's one chip had no count, so the repeated calls looked like one. Holding the whole step costs streaming: an answer written in a step offered tools appears at once when the step ends. Allowing one check keeps a model that answers first to two paid steps.

**Enforced in.** `_run_openai` in `webapp/providers.py` (`_ANSWER_SENTENCES`, `ANSWER_IN_FULL`); the tool chips in `webapp/static/js/chat.js`; `mend_dashes` in `webapp/reply_check.py`; the first-person rule in `CONDUCT_FLOOR` in `webapp/app.py`. Dropped narration and held answers count toward the metrics row's dropped sentences (`checks_dropped`). Covered by `tests/test_open_model_loop.py` (the 2026-11-06 session is replayed there) and `tests/test_reply_check.py`.

**Reverse when.** A fine-tuned model stops writing these on the bake-off set, or a dropped stretch of narration turns out to have carried study content.
