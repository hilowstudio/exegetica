# 0009: Signed-in student chats are stored, and the maker can read them

Decided by A. James Vega, 2026-11-02, "for now."

**Decision.** Student chats sync to Neon (`chat_state`) under the student's school account, as they do for every signed-in user. A. James Vega, the sole maker and the only person with Neon access, can read them. Students are told so in the FAQ ("Who can read what I type?"), which also says he is a mandated reporter, on `/privacy`, and by the bot itself, which answers "who can read this?" with the same facts in fixed words (`ABOUT_EXEGETICA` in `webapp/app.py`).

**Why.** It keeps a way to look into misuse, such as the inappropriate use seen in October and November 2026, and lets students keep their studies across devices.

**Enforced in.** `webapp/store.py` (storage), and for disclosure the FAQ in `webapp/static/index.html`, `docs/privacy.md`, and `ABOUT_EXEGETICA`. No code restricts or logs reads; access is the maker's own Neon credentials.

**Still open.**
- A written procedure: when he reads student chats (routinely, or only when something is reported), and what he does when he reads something reportable. Illinois lists school personnel as mandated reporters. The school should know the procedure exists.
- How long chats are kept. Students can delete a study or their whole account, and the retention purge is built but off until the maker sets its periods (docs/decisions/0013).
- The saved copy is written by the student's browser, so it can be edited and is not proof of what was said. A server-written log would be needed for that (proposal, Layer 4, under "an adult reads").

**Reverse when.** Choosing the other option means keeping student chats in the browser only, so that no one can read them, and changing the FAQ to say so.
