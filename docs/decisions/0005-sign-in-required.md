# 0005: Chat requires a school Google account

Decided by A. James Vega, 2026-11-02.

**Decision.** `/api/chat` refuses anyone not signed in. Google sign-in accepts only verified accounts in the school's Workspace domain (`SCHOOL_DOMAIN`, default `yorkvillechristian.com`), plus anyone on the `TEACHER_EMAILS` or `LIBRARY_ADMIN_EMAILS` allowlists. Teacher status is checked live against `TEACHER_EMAILS` on every request, never trusted from the session cookie.

**Why.** Anonymous, unlimited chat on the maker's own API key could not be limited per person, and gave no way to bind a student to the rules of the school.

**Enforced in.** `chat()` in `webapp/app.py`; `_may_sign_in` and `is_teacher` in `webapp/auth.py`; the sign-in prompt in `webapp/templates/chat.html` and `webapp/static/js/chat.js`.

**Consequences still open.**
- Signed-in chats sync to Neon (`chat_state`), so every student's chats are now stored where the maker can read them. Decided in [0009](0009-student-chats-readable.md).
- Counsel has not yet answered SOPPA (which covers nonpublic schools) or COPPA for grade 6.
- A student's school-provisioned account signed in successfully on 2026-09-11, so the school's Google Workspace allows sign-in to Exegetica. If the school later restricts third-party apps for under-18 accounts, an admin would need to trust the app.
- Rotate `SESSION_SECRET` in production when this ships, to end sessions created before the domain rule.

**Reverse when.** By the maker's decision; anonymous chat would also need the shared daily pool from the proposal (Layer 6).
