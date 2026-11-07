# 0015: A student's study takes new messages for one day, then opens for reading only

Decided by A. James Vega, 2026-11-03 (decision F in the harness proposal).

**Decision.** A student's study accepts new messages for 24 hours after it began. After that it opens for reading only, with a line saying why and a button to start a new study. Every study, a teacher's included, also stops at the server's message limit of 48 messages (24 turns) and then opens for reading only. Teachers' studies have no one-day limit.

**Why.** Reopening a study sends its whole transcript back to the model, so one conversation can carry the model across many days. That is the slow-burn route the October 31 probing used to walk a model off its rules. A fresh study starts from the rules alone.

**Enforced in.** `studyClosed()` and `syncComposer()` in `webapp/static/js/chat.js`. A new study records `created`, and an older study without it falls back to `updated`. The message limit is enforced on the server by `policy.clean_history` (`MAX_MESSAGES`), and the page mirrors it so the box closes before the server refuses. `tests/test_study_bounds.py` keeps the page's numbers in step with `webapp/policy.py`.

**Limits.** The one-day rule is enforced only in the browser. The server never holds a study's start time, because the browser sends the transcript with each message, so a student who crafts requests by hand can send an old transcript. The server's message limit and daily caps (0011) still bound what that costs.

**Reverse when.** Change `OPEN_HOURS` in `index.html`, or remove the one-day check from `studyClosed()`, by a new decision from the maker.
