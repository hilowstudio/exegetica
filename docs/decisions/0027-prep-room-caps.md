# 0027: The Prep Room has daily caps, per teacher and for all teachers together

Drafted 2026-11-09 at the maker's request ("draft a Prep Room daily cap decision record like 0011"). The numbers are starting points for him to set; nothing is deployed until he does.

**Decision.** Before any model call, every Prep Room run (a draft, a change by instruction, and the older Generator and Revise routes) checks two counters for the school day, in Chicago time:

- **Each teacher:** 25 runs or $10 of estimated spend.
- **All teachers together:** $40 of estimated spend.

A capped teacher sees one fixed line where the document would be, and no model is called: "You've reached today's Prep Room limit. It opens again tomorrow, and everything you've made is saved." When the school total is reached, the line names the school instead. Every run is counted when it ends, finished or not, with its estimated cost. The Prep Room's counters are kept apart from the same teacher's chat turns, so planning never uses up a teacher's chat, or the reverse.

**Why the numbers.** `/ops` held one Prep Room run on 2026-11-09: a book draft at $0.73 that took two minutes. One run may spend up to $5 under decision 0008 (Revise $2). Twenty-five runs covers a heavy planning day of about ten drafts and fifteen changes, and $10 a teacher is roughly a dozen typical drafts. Twenty-four teachers each at their cap would be $240 in a day, so the shared $40 bounds what the maker pays if many plan at once; at October's rate (about $37 for the month across all of Exegetica) it is far above a normal day.

**Enforced in.** `usage.prep_check` and `usage.prep_add` (`PREP_RUNS`, `PREP_USD`, `PREP_ALL_USD`); `prep_capped` and `prep_counter` in `webapp/app.py`, called by `prep_draft.draft`, `prep_draft.revise`, `generate_endpoint`, `generate_book_endpoint` and `revise_endpoint`; `_generation(on_end=)` counts the run after it ends. Counters live in `usage_daily` beside chat's (keyed by a keyed hash of account and date, deleted after two days, decision 0011). Like chat's caps, they fail open when the database is unreachable, and the Anthropic Console spend limit is then the stop. Covered by `tests/test_prep_draft.py`.

**Reverse when.** Change the numbers after two weeks of `/ops` data with the Prep Room in use, by the maker's decision.
