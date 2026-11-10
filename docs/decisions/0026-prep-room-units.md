# 0026: The Prep Room keeps a teacher's work in units, with every version

Decided by A. James Vega, 2026-11-09, from the Prep Room concept (direction A, the workbench, with B's gallery as its Make panel; the container is called a unit).

**Decision.**
- A teacher works inside a **unit**, such as "John 7 and 8". A unit holds its sources, its objectives, a note every draft should know, and every resource made in it. A **quick resource** made outside a unit is kept too.
- **Every draft, revision, hand edit and restore is saved** as a numbered version on the server, so a reload or a bad revision loses nothing. The newest 40 versions of a resource are kept.
- A unit's **sources** are a Reading Room book (with how far the class has read), a work with an outline only, a Bible passage, a Living Library item, an uploaded document, or a link. The text of an upload or a link is the teacher's own copy of someone's work. It is kept encrypted with the Living Library's private-copy key, never shared, and decrypted only to draft from it.
- Units and resources are **private to the teacher** who made them. The maker can read them, as the privacy page says. They are in the teacher's data download and go with the account.
- Which Yorkville courses a teacher teaches is kept by account address in `teacher_courses`, so the Living Library opens on those courses' books. The school's book list is read on the maker's machine to seed it. No teacher's name is stored in the app, the repository or memory.

**Why.** Drafts lived only in the open tab and vanished on reload, and nothing tied a resource to the material it came from. Teachers plan by unit, and a unit lets the class, grade band and sources be set once.

**Enforced in.** `webapp/prep.py` (every query scoped to the account; `clean_ref` keeps only what each kind of source needs; `clean_objectives` keeps each objective's anchors); the tables `prep_units`, `prep_sources`, `prep_resources`, `prep_versions` and `teacher_courses` in `scripts/schema.sql`; `account.collect` and `account.remove` (decision 0013). Routes are teacher-only (decision 0007). Covered by `tests/test_prep.py`; the SQL is checked by `scripts/check_prep_sql.py` against a throwaway schema.

**Reverse when.** A teacher's saved work is never dropped without notice. Changing the version limit or what a source may hold needs only a code change here; storing anything about students in a unit needs a new decision (0002).
