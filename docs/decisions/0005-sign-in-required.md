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

**Amended 2026-11-25: guests.** The maker may let an account from outside the school sign in by adding it to `GUEST_EMAILS`, a server secret (never in git). The account must be verified by Google.
- A guest has the student role, rules and caps: chat, Scripture Memory and the public Reading Room.
- A guest takes no classes. Class shelves, class videos, class podcasts and Classroom join links stay closed.
- A guest never reads school copies or reference copies. `reader.may_read_school` admits only the school domain, teachers and admins.
- A guest's studies are kept and readable like a student's (0009, 0013).
- An account from outside the school counts only while it is on an allowlist. `current_user` checks the lists on every request, so taking an address off ends that session on its next request. This applies to outside teachers and admins too.

*Why:* the maker wanted one outside account to use Exegetica without opening what the school licensed for its own accounts. *Enforced in:* `_may_sign_in`, `is_guest` and `current_user` in `webapp/auth.py`; `courses_open_to`, `classes_of` and `choose_classes` in `webapp/shelves.py`; `_joinable` and `readable_by` in `webapp/shelf_docs.py`; the Library's class shelves in `webapp/static/js/shelves.js`; `tests/test_sign_in.py`.
