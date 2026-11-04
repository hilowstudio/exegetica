# 0006: The mode toggle is hidden and replies are labeled Exegetica

Decided by A. James Vega, 2026-11-02.

**Decision.** The chat page no longer shows the mode toggle. Bible chat uses the Theologian persona and History chat the Historian. Every reply is labeled "Exegetica". The Aide and Researcher modes stay in code, unused by the page, so reintegrating them can be discussed later.

**Why.** Replies labeled "Professor" contradicted the position statement's "AI must never be the teacher."

**Enforced in.** `webapp/static/index.html` (toggle hidden, saved studies no longer restore a persona, the reply label). The server still accepts any allowlisted persona (`webapp/policy.py`).

**Consequence, resolved 2026-11-02.** Students no longer get `theologian.md`. Bible chat uses `BIBLE_STUDENT` in `webapp/app.py` (a reference-work brief: attribute doctrine to the tradition, no prayers or devotions written for students, the first draft of graded work is the student's) plus `src/studybible_mcp/prompts/doctrine.md`, the tradition's doctrine in the third person. The maker signed off on `doctrine.md` the same day, so there is one copy of the doctrine: `theologian.md` now holds only the pastors' persona (voice, pastoral framework, teacher integration), and its loaders (`_load_persona` in `src/studybible_mcp/server.py`, `_THEOLOGIAN` in `webapp/generator.py`) append `doctrine.md`. `historian.md` was corrected in place (no self-description, no confessing, no sorting students by spiritual state, no praise, no crisis number). `tests/test_student_prompts.py` and `tests/test_generator_conduct.py` fail if any of this regresses. The Claude Code skill at `.claude/skills/theologian/SKILL.md` is a separate, older copy and was not changed.

**Reverse when.** By the maker's decision.
