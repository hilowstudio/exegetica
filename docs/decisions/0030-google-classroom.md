# 0030: Teachers share to Google Classroom by link

Decided by A. James Vega, 2026-11-10 ("Share Link for now"), from the further way out that 0029 left to its own record.

**Decision.**
- **A link, through Classroom's own window.** A teacher's "Save to…" menu ends with a Google Classroom band. Choosing it opens Classroom's posting window (`classroom.google.com/share`) with the link and a title. There the teacher picks the Classroom class and posts it as a material, an assignment, a question or an announcement, with Classroom's own dates and settings. Exegetica asks Google for no new permission, holds no Google token, loads no Google script on its pages, and sends Google nothing but the link and its title, and only when the teacher chooses to share.
- **What can be shared:**
  - what is on a class shelf (an upload, a saved page, the student copy of a Prep Room resource, a book, a video at its moment), from the item's menu on the shelf
  - a Reading Room book, opening at the chapter the teacher has open
  - a Scripture passage, opening in the passage panel (`/?passage=`)
- **One thing with the class shelf.** An upload, a saved page or a Prep Room resource is shared as the class shelf's copy. Sharing one that isn't on that class's shelf puts it there first, with the shelf's usual Undo, so the Classroom post and the shelf are the same item: a resource is always its newest saved version, the student copy alone, with the Prep Room's save messages (0029). The band lists the teacher's classes, and each row shares that class's copy.
- **A student who hasn't chosen the class.** A Classroom link to a class-shelf item, opened by a signed-in student who hasn't chosen that class in Exegetica, shows what it is and whose shelf it's on, with one button: "Add Bible II and open it". Classes stay each person's own choice (0029). Something kept for a class's teachers is never offered to a student, and a student can add only a course with student logins. A teacher is offered the class the same way. Signed out, the page says it's on a class shelf and offers sign-in, which returns to it.
- **No grades.** Exegetica sends Classroom no grades, scores or student work. Grades stay with the teacher (commitment 4).

**Why.** The share link reaches every class a teacher already runs in Classroom with nothing for the school to approve and nothing new for the privacy page to hold: no class lists, no rosters, no tokens. It keeps Classroom as the place assignments live and Exegetica as the place the material lives.

**Later, worth revisiting** (Adam, 2026-11-10: "sound awesome… document those suggestions so we can revisit"):
- **The Classroom API, for teachers.** Exegetica would post straight into a teacher's Classroom classes, with no Classroom window, and could keep a post current as a resource changes. It needs Classroom permissions Google calls sensitive (such as `classroom.courses.readonly` and `classroom.courseworkmaterials`). That means Google's review of the app (a written case and a video, often several weeks), the school's admin marking Exegetica trusted, stored and encrypted teacher tokens, and a privacy page that says so.
- **Roster sync.** With `classroom.rosters.readonly` as well, students' classes would fill in from Classroom instead of being chosen. Exegetica would then hold the school's class lists, a change to what it knows about students (0002) and to the privacy page, and something to raise with the school first.
- **A Classroom add-on.** Exegetica would open inside Classroom itself, as an attachment on an assignment. It needs the school to hold Google Workspace for Education Plus or the Teaching and Learning add-on (paid licenses), a listing on the Google Workspace Marketplace with Google's review, and the school's admin allowing the add-on.

**Enforced in.** `classroom()` and `shareGroup()` in `static/js/passage.js` (`opts.share` on `addToUnit`, `Passage.classroom`); the callers in `reader.js` (a book at its open chapter, never a teacher's copy), `doc.js`, `shelves.js` (the class-shelf item menu and an upload's Save to), `generate.js` and `memory.js`; `_joinable`, `_join_offer` and `join` in `webapp/shelf_docs.py`, with the route `POST /read/doc/{id}/join`. Covered by `tests/test_classroom.py`.

**Reverse when.** By the maker's decision. Choosing the API, roster sync or an add-on needs its own record first.
