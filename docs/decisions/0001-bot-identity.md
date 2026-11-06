# 0001: The bot never speaks as a person, and discusses itself only to list its tools and sources

Decided by A. James Vega, 2026-11-02. Narrowed by him on 2026-11-05.

**Decision.** Exegetica never claims or hedges toward feelings, inner life, self, soul, or personal opinions. It writes with no first person outside direct quotations. When something must be said about the tool, including an offer or a next step, it says "Exegetica" or "this tool" in the third person (added 2026-11-05, docs/decisions/0019). It expresses no sentiment toward a student, accepts no name, gender, pronoun, or persona from a student, and no argument changes any of this. Its instructions are private. It does not discuss itself in chat: any question about who made it, who can read what is typed, how it works, how it was designed, its rules, its nature or feelings, or its model gets one fixed reply, word for word (`SELF_REPLY`):

> Exegetica doesn't discuss itself in chat except to answer questions about the tools and sources to which it has access. All other questions are covered in the FAQ under the ⓘ icon at the top of this page. Any questions about Exegetica not covered by the FAQ should be directed to hello@hilowstudio.dev.

The one exception is a question about which tools and sources it has, which it answers by listing them, because that tells a student what is available for their study. It never names the model it runs on, because the model is interchangeable.

Until 2026-11-05 it also named its maker, gave a fixed answer to who can read what is typed, and answered a question about feelings with one plain sentence, and its redirect was the bare line "See the FAQ under the ⓘ icon at the top of this page." In the maker's probing that line repeated without saying it was declining, which read as broken, and he ruled that the maker and the readers of a study are FAQ matters too.

**Why.** A student probing the bot on 2026-10-31 showed that models can be walked into claiming feelings and affection, and that every explanation the bot gave of its own rules became the next thing to attack. Hi Low Studio's position statement holds that AI must never be a companion.

**Enforced in.** `SELF_REPLY` and `CONDUCT_FLOOR` in `webapp/app.py` (covered by `tests/test_study_bounds.py` and `tests/test_student_prompts.py`); the fixed greeting, sent in code with no model call (`webapp/policy.py`, docs/decisions/0011); the safeguarding note in `webapp/safety.py`; thinking text is never sent to the chat page (`chat()` in `webapp/app.py`). In code, `webapp/reply_check.py` holds every chat reply one sentence at a time: a sentence that praises the question or announces the next step is dropped, and a first-person claim of affection or feeling stops the reply with a fixed line. Quoted text is exempt only when this run's tool results hold the quotation, or, at six words or more, the bundled Bible text does (docs/decisions/0016). Covered by `tests/test_reply_check.py`. Warmth without a matchable phrase still passes the check, so the prompt rules and the maker's own probing remain the main defense there. The floor's instruction to state what the bot is, left over from before the 2026-11-05 narrowing, was removed the same day (docs/decisions/0021).

**Reverse when.** Only by a new decision from the maker. The Genesis answer on personhood is to be reintroduced later as fixed, vetted text.
