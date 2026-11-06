# Pushing the course into Google Classroom

This is how to get the finished, student-facing Gospel of John course into a Google
Classroom class you teach: units as topics, reading guides and handouts as materials,
and the four projects and two finals as graded assignments with due dates.

It is done by a standalone script, `scripts/push_to_classroom.py`, that you run from
your own machine. It is **not** part of the web app. It signs in as you, uploads the
student PDFs to your Google Drive, builds the class, and exits. Nothing about it lives
in the app, and it stores no student data.

## What gets pushed

Student-facing documents only. Teacher lesson guides and answer keys are never
uploaded (the two "TEACHER copy" finals are hard-excluded by name).

| In the course | In Classroom | How |
| --- | --- | --- |
| Units 1-28 | Topics named "Unit N · <date range>" | date range from the calendar |
| Unit reading guides, the Unit 1 terms card | Materials under their unit | PDF, view-only |
| Unit 1 daily pages | **Assignments** under Unit 1 | **Google Doc, one editable copy per student** |
| Reading Journal | **Assignment** under "Journals" | **Doc, per-student copy** (you can read it) |
| Quiet-Time Journal | Material under "Journals" | **Doc, view-only**; students copy it to their own Drive so it stays private |
| Syllabus, How to Read John, journal *guides*, memory sheets | Materials under "Course resources" | PDF, view-only |
| The 4 quarter projects | Assignments under "Projects", with due dates | PDF attached |
| The 2 semester exams | Assignments under "Exams and review", with due dates | PDF attached |
| The 2 review study guides | Materials under "Exams and review" | PDF, view-only |

Fill-in items (daily pages and the journals) are delivered as native **Google Docs**,
not PDFs, so students type into them. "Per-student copy" means Classroom hands each
student their own editable copy. The Quiet-Time (prayer) journal is intentionally
view-only: students keep their own copy in their own Drive, and you never see it, which
preserves its private, uncollected design. The daily-page and Reading-Journal
assignments are **ungraded** (no points) — they are for writing, not scoring.

Due dates come straight from the course calendar (`docs/john/john-course-calendar.json`):
Q1 Nov 5 2026, Q3 Mar 18 2027, Q4 May 19 2027, Sem 1 final Jan 11 2027, Sem 2 final
May 25 2027. (Q2 Character Study has no date in the calendar, so it is pushed without
one — set it in Classroom, or add the date to the calendar and re-run.)

Everything is created as a **draft** by default. Nothing is visible to students until
you review it in Classroom and publish, or re-run with `--publish`.

## Before you start: the one thing that can block this

Yorkville almost certainly runs **Google Workspace for Education**. On those domains a
Workspace administrator controls whether outside apps may use the Classroom API, and
the assignment/coursework permissions are treated as "sensitive." **You will probably
need your school's Workspace admin to allow API access for the OAuth app you create
below** (or to add you as an allowed user / mark the app "internal" and trusted).

If the admin will not allow it, the automated path is closed and your option is the
manual one: the script still renders the plan (`--dry-run`), and you upload the PDFs
to Drive and attach them in Classroom by hand, using the table above as the map.

Confirm this is possible before spending time on the setup.

## One-time setup

You need a Google Cloud project with the two APIs enabled and a Desktop OAuth client.
This takes about ten minutes and you only do it once.

1. **Create a project.** Go to <https://console.cloud.google.com>, sign in with your
   school Google account, and create a new project (name it e.g. "John Classroom push").

2. **Enable the APIs.** In "APIs & Services → Library", enable both:
   - **Google Classroom API**
   - **Google Drive API**

3. **Configure the consent screen.** "APIs & Services → OAuth consent screen".
   - User type: **Internal** if your school account offers it (simplest — no review).
     If only **External** is available, choose it and add your own email as a **Test
     user**; test mode is fine for a single teacher.
   - Fill in the app name and your email where required; you can skip the rest.

4. **Add the scopes** (only needed if the consent screen asks you to list them). The
   script requests exactly these:
   - `.../auth/classroom.courses.readonly`
   - `.../auth/classroom.topics`
   - `.../auth/classroom.coursework.students`
   - `.../auth/classroom.courseworkmaterials`
   - `.../auth/drive.file`

5. **Create the OAuth client.** "APIs & Services → Credentials → Create credentials →
   OAuth client ID → Application type: Desktop app".

6. **Give the script the client**, either way:
   - **Env vars (what we use):** set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (in
     your environment or the repo's `.env`). No file needed.
   - **or JSON file:** download the client JSON and save it at `.secrets/client_secret.json`.

   Either is fine; env vars take priority. The `.secrets/` folder and `.env` are
   gitignored, so neither is ever committed.

7. **Install the client libraries** (once):
   ```
   .venv/Scripts/python.exe -m pip install -e ".[classroom]"
   ```

### First run acts as you, in a browser

With the OAuth client, the first command opens a browser and asks *you* to consent.
That is deliberate: Classroom actions are performed as a real teacher of the course, so
the push runs as you. The consent produces a token cached in `.secrets/`; later runs
reuse it silently.

### Headless alternative: service account + delegation

If you want the push to run with no browser (a server, a scheduled job), use a service
account **with domain-wide delegation**. A bare service account does not work: it is not
a teacher of any course, so Classroom rejects it. Your Workspace **admin** must, in the
Admin Console (Security → API controls → Domain-wide delegation), authorize the service
account's client ID for exactly the five scopes listed above. Then the script
impersonates you:

```
python scripts/push_to_classroom.py \
  --service-account .secrets/sa-key.json --impersonate you@yorkvillechristian.org \
  --course-id <ID>
```

(Or set `GOOGLE_SERVICE_ACCOUNT_FILE` and `CLASSROOM_IMPERSONATE` instead of the flags.)
Until the admin delegates, stick with the OAuth path above.

## Running it

All commands use the project's interpreter from the repo root.

```bash
# 0. (if the PDFs are stale) re-render the student set
.venv/Scripts/python.exe scripts/course_pdf.py --all

# 1. see the full plan and confirm every PDF exists — contacts no Google service
.venv/Scripts/python.exe scripts/push_to_classroom.py --dry-run

# 2. sign in and find the class to push into
#    (opens a browser the first time; the token is cached in .secrets/)
.venv/Scripts/python.exe scripts/push_to_classroom.py --list-courses

# 3. push everything as drafts into that class
.venv/Scripts/python.exe scripts/push_to_classroom.py --course-id <COURSE_ID>

# 4. when you have reviewed it in Classroom, make it live
.venv/Scripts/python.exe scripts/push_to_classroom.py --course-id <COURSE_ID> --publish
```

Push a subset while you iterate:

```bash
# one unit
.venv/Scripts/python.exe scripts/push_to_classroom.py --course-id <ID> --only U5
# one document or group (matches file/title/topic)
.venv/Scripts/python.exe scripts/push_to_classroom.py --course-id <ID> --only syllabus
.venv/Scripts/python.exe scripts/push_to_classroom.py --course-id <ID> --only project
```

## Re-running is safe

The script records what it created per course in `.secrets/classroom-push-state.json`.
Run it again after you edit and re-render a document and it **updates the existing**
Drive file, topic, and Classroom item in place instead of making duplicates. So the
normal workflow is: edit the Markdown → `course_pdf.py --all` → `push_to_classroom.py`
again.

## Notes and limits

- **Two sections (P2 and P5).** Each Classroom class has its own id. Run the push once
  per section with that section's `--course-id`; the state file tracks them separately.
- **Due times** are set to 23:59 on the due date (Classroom stores due times in UTC, so
  the wall-clock time may look slightly off; the date is what matters — adjust in
  Classroom if you like).
- **The finals** are pushed as assignments dated to the exam window so they show on the
  calendar; if you give the exam only on paper in class, keep them as drafts or delete
  them after — they are a scheduling placeholder, not a submission box.
- **Points** default to 100 on every assignment; reweight in Classroom to match the
  syllabus (Projects 25%, exams 15%, etc.).
- **The script never touches teacher material.** Only `docs/john/john-pdf/student/` PDFs are
  uploaded, and the teacher answer-key finals are excluded by name.
