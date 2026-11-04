# 0011: Some replies are decided in code, and chat has daily caps and rate limits

Recorded 2026-11-03 from the harness proposal (Layers 3, 5 and 6), built while the maker was away. The numbers are starting points for him to adjust.

**Decision.** Before any model call, `chat()` answers these in code, after the crisis pre-check, so the help panel still opens first:

- **A bare greeting** ("hi", "good morning", "hello Exegetica") gets the fixed greeting for its subject. The greeting rule left the system prompt.
- **A drifted study:** when a student's last five replies all ran without a library tool, the next message gets a fixed line pointing back to study. Teachers are exempt.
- **Rate limits:** six turns per account in a rolling minute, and at most twelve model streams at once on the server. Kept in memory, keyed to the account, never the IP address, since the school shares one.
- **Daily caps per school day (Chicago time):** a student has 30 turns or $1.50, a teacher 300 turns, and all students together $8. Teachers stay outside the school-wide total. A capped or limited student gets fixed text and no model call.

**Why.** A greeting needs no model and no improvised welcome. Long tool-free runs are where the probing chats drifted: a narrow conduct pattern fired by turn six in all 24 ladder transcripts, and so did three tool-free replies in a row. The caps bound what one account, or the school, can spend on the maker's key in a day.

**Enforced in.** `webapp/policy.py` (`GREETING`, `is_greeting`, `drifted`, `DRIFT_TEXT`); `webapp/usage.py` (caps and rate limits); `chat()` in `webapp/app.py`. Counters live in `usage_daily`, keyed by a keyed hash of account and date, deleted after two days. Until `scripts/schema.sql` is applied, caps fail open and the Anthropic Console spend limit is the stop. Covered by `tests/test_chat_route.py` and `tests/test_privacy_and_data.py`.

**Reverse when.** Change the numbers after two weeks of `/ops` data. The drift count resets with New Study. Moving it server-side would need a per-account record, which decision 0002 rules against.
