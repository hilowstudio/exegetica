# 0033: A course can give its students reading supports, and no level is ever named

Decided by A. James Vega, 2026-11-14.

**Decision.**
- A teacher's course can carry **reading supports**. Everything the Prep Room makes for that course, and every revision
  of it, is written for readers who need support:
  - short sentences and plain words
  - hard words kept and explained where they first appear, or in a "Words to know" box
  - short chunks under headings that say what they are about
  - one task per numbered step, with a worked example and a sentence starter or word bank
  - full references for every passage students must find
  The content, the depth of thought and a grown-up tone stay. The course keeps its grade band; the supports replace
  only that band's guidance on vocabulary and text length.
- **No level is named, anywhere.** The supports are described by what a page does, never by a level. Nothing the app
  makes states, labels or hints at a reading level, a grade level or band, or that material was simplified or adapted.
  This holds in the prompt, in the code, in the documents and in this record.
- The Gospel of John course (`bible-2`) carries the supports.

**Why.** Many of the sophomores read poorly and most have never read their Bibles, so they need supports to learn
what the text says. Students who look through the app with their browser's tools must never find that it was
designed around them, and a page that announced its level would shame the readers it serves.

**Enforced in.**
- `webapp/generator.py`:
  - `SUPPORTED_COURSES` lists the courses that get the supports.
  - `READING_SUPPORTS` is added to the system prompt; `REVISION_SUPPORTS` is added to a revision.
  - `scrub_levels` runs on every saved version made for a supported course, removing any line that names a band or
    level and any sentence that talks about one.
- `webapp/prep_draft.py`: the draft and revise routes turn the supports and the scrub on for a supported course.
- `webapp/prep_catalog.py` (`student_copy`) and its mirror in `webapp/static/js/prepdoc.js`: no student copy of any
  resource carries a Grade Band line.
- All of this is server-side. The prompts and the course list never reach a browser.
- `tests/test_reading_supports.py` covers:
  - the supports name no level
  - they reach only supported courses
  - revisions keep them
  - the scrub and the student copy work
  - none of the supports' wording is shipped in a static file or template

**Reverse when.** The maker decides. Adding a course is one entry in `SUPPORTED_COURSES`. A setting a teacher could
change from a page would need this record amended, and that setting would have to stay out of anything sent to
students.
