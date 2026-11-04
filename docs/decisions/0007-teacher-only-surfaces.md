# 0007: Generator, Revise, library jobs, and exam materials are teacher-only

Recorded 2026-11-02 from the harness Governance spike.

**Decision.** `/api/generate`, `/api/generate/book`, `/api/revise`, `/api/library/extract`, and the upload routes require a signed-in teacher. The course site shows students only files matching known student patterns; everything else in `docs/john-materials/` (both finals, every answer key, anything added later) is teacher-only, and the teacher view itself requires a signed-in teacher.

**Why.** The Generator writes answer keys and runs on the server key with no conduct floor. The final-exam keys were public on the live site on 2026-11-02, linked from `/course`.

**Enforced in.** `_teacher_only` and `_view` in `webapp/app.py`; `_is_teacher` in `webapp/library_store.py`; `_STUDENT_FILE` in `webapp/course.py`. Checked by the route checks run on 2026-11-02 (23 of 23).

**Reverse when.** A file type becomes student-visible only by adding its pattern to `_STUDENT_FILE`.
