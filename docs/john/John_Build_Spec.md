# The Gospel of John — Sophomore Bible Course: Build Spec
### Single source of truth for the whole build. Read this first.

**What this is.** A full-year, verse-by-verse Sophomore Bible course on the Gospel of John (2026-27), for Yorkville Christian School. Instructor: Adam Vega, teaching two sections (Periods 2 and 5, same curriculum). We (Adam + Claude) are building it together, and building it to be **produced by the resource-generator app** (this repo), which makes the course the app's flagship use case.

**Status at last update (2026-09-04):** design locked; calendar map + per-lesson passages locked; three bespoke generator formats authored; the generation pipeline built, sturdy, and proven ESV/tool-grounded end to end. Six teacher guides hand-built as exemplars. Ready to generate the week-one course documents, then roll unit by unit. Class starts **Tue 2026-09-08**.

---

## 1. The school (context that shapes everything)

Yorkville Christian School (YCS), Yorkville IL. **Evangelical private school.** Grades 6-12. Teaches primarily **ESV**. Handbook grading rules bind the course (see §5). Full school profile: `docs/school/yorkville-catalog.json`, `docs/school/yorkville-handbook.md`. Voice: plain, warm, evangelical; avoid classical-education idiom (no trivium/Latin/recitation-culture framing).

## 2. Design — the non-negotiables

- **The three-tier room is the master constraint.** Every artifact must reach, in one room: **(S)** a student new to the Bible who cannot yet find the passage, **(B)** a churched but passive student, **(D)** a maturing disciple. Low floor, high ceiling, zero assumed knowledge.
- **Govern the teacher.** Adam's stated weakness: he can lecture the whole period with no student participation. Lessons run on student output; his sustained voice is capped (~40% of the period, no block past 8-10 min) and placed in one protected pastoral moment (the Land).
- **The living Word, not a textbook.** Ministry over academia. Ensure students know the CONTENT (that is the teacher's job) and trust the Spirit for the heart. Lessons minister the truth over the students.
- **Christotelic, exegesis-first, ESV, tool-grounded.** Every Scripture quotation checked through the Study Bible MCP tools; teach in the theologian voice.
- **Peer discipleship + oral.** Stable mixed "John groups"; think-pair-share; rotating roles; student-led devotionals; seminars; encouragement pairs. In the mixed-faith room, **faith content is always invitational, participation is assignable**; no student is required to pray aloud or profess.
- **7-minute quiet time opens every class** (student host on rotation, prayer opt-in). Two journals: a personal **Quiet-Time Journal** (ungraded) and a **Reading Journal** (graded in participation).

## 3. The lesson template (5 moves) — `docs/john/John_Lesson_Template.md`

Every lesson: **Quiet time with the Lord (7 min)** → **Hear the Word (read aloud)** → **Work the text (~25 min, GOVERNED question sequence — Entry/Core/Deeper, no lecture, John groups, cold-call checks)** → **Land and minister (5-7 min, the teacher's protected pulpit; correct theology with grace, off the grade)** → **Respond (in-room existential writing, graded participation)**. Then After-the-bell (near-zero homework = the reading; gradebook feed; sets up next) and Teacher notes. Day-type variants: Regular 50 / Thursday 36 (one key question) / Half-day 26 (single verse or memory/recap).

## 4. Container & sequence — `docs/john/John_Calendar_Map.md` + `docs/john/john-calendar-map.json` (AUTHORITATIVE)

- **150 content lessons** (Semester 1 = 71, John 1-12, the Book of Signs; Semester 2 = 79, John 13-21, the Book of Glory) + 2 pre-finals review days (Jan 8, May 24) + finals (Jan 11-14, May 25-28). Tentative 151st flex day **May 21** (graduation) = **pray for the graduating class** if sophomores meet.
- **Day types:** 50-min regular, 36-min Thursday, 26-min half-day. The 4 half-days (Oct 9, Dec 18, Mar 19, May 7) are memory-quiz + recap beats, never dense exposition.
- **Resolutions baked in:** Unit 1 reshaped so 1:1-5 gets a full period (whole-Prologue orientation takes the Sep 10 Thursday). Thursdays run single-focus. 4 checkpoints, 2 reviews, finals placed. Holy Week alignment NOT a priority (cross ~Apr 9-23, resurrection Apr 27-May 6). Discourse-chapter splits are recut per unit at build time.
- **Per-lesson sub-passages:** `docs/john/john-lesson-passages.json` (from `scripts/plan_passages.py`; even-split snapped to sermon seams; discourse chapters 14-17 need per-unit recut).

### The 29 units

| Unit | Passage | Lessons | Unit | Passage | Lessons |
|---|---|---:|---|---|---:|
| U0 Entering John | orientation | 2 | U15 Sign 7 (Lazarus) | 11:1-57 | 5 |
| U1 The Word | 1:1-18 | 4 | U16 The hour has come | 12:1-50 | 5 |
| U2 Witness & first disciples | 1:19-51 | 4 | U17 Re-entering (bridge) | — | 1 |
| U3 Sign 1 & temple | 2:1-25 | 4 | U18 Towel and basin | 13:1-38 | 7 |
| U4 The new birth ★ | 3:1-21 | 4 | U19 Way to the Father | 14:1-31 | 8 |
| CHK-1 (chs 1-3) | quiz+Signs intro | 1 | U20 Abide | 15:1-27 | 8 |
| U5 He must increase | 3:22-36 | 2 | U21 Spirit & coming joy | 16:1-33 | 7 |
| U6 Living water ★ | 4:1-42 | 5 | U22 Holy Spirit, gathered | synthesis | 1 |
| U7 Sign 2 | 4:43-54 | 2 | U23 Prayer of the Son | 17:1-26 | 8 |
| U8 Sign 3 & authority | 5:1-47 | 5 | CHK-3 (chs 13-17) | quiz+Farewell due | 1 |
| U9 Bread of Life | 6:1-71 | 7 | U24 Arrest and trial | 18:1-40 | 8 |
| CHK-2 (chs 4-6) | quiz+Signs due | 1 | U25 The cross ★ | 19:1-42 | 11 |
| U10 Rivers of living water | 7:1-52 | 5 | CHK-4 (chs 18-19) | quiz | 1 |
| U11 A note on the text | 7:53-8:11 | 1 | U26 The empty tomb | 20:1-31 | 8 |
| U12 Light of the world | 8:12-59 | 5 | U27 Do you love me | 21:1-25 | 6 |
| U13 Sign 6 | 9:1-41 | 4 | U28 Whole Christ (synthesis) | — | 4 |
| U14 The Good Shepherd | 10:1-42 | 5 | | | |

★ = starred fresh-build (no sermon in the set; Adam frames before drafting): Nicodemus/new birth 3:1-21, Samaritan woman 4:1-42, foot-washing 13:1-38, crucifixion 19:17-37.

## 5. Assessment model — `docs/john/John_Assessment_Menu.md`

**Two graded worlds, kept separate.** Content graded on correctness (memory verses, quizzes, finals). Formation graded on effort/service, **theology coached live, never scored** (quiet time, participation, Respond, student-led devotionals).

**Gradebook (handbook-compliant):** Participation & Discipleship 30 / Memory & Quizzes 30 / Projects 25 / Semester Final 15. Handbook rules: homework-alone <20% (here ~0), homework+participation combined may exceed 20%, final fixed at 15% via `(coursework×.85)+(final×.15)`.

**Rubrics:** participation (holistic 0-4); student-led devotional (effort/service, no theology line); project & oral (grasp/Christ/insight/communication/live-Q&A).

**Projects — four, one per quarter** (full designs in the assessment menu): Q1 **The Signs**, Q2 **Character Study**, Q3 **Teaching the Farewell Discourse** (group), Q4 **The Passion & a Personal Response**. Built to the sophomore-project bar: voice-and-choice (fixed skills, free format), authentic audience, scaffolded graded milestones (pitch → plan → draft → present) with in-class check-ins, interdependent roles + confidential peer eval for the group project, and a required metacognitive **Maker's Note**. Project grade = milestones (process) + the final rubric + the Maker's Note + (group) individual contribution. Q4's personal response is credited for honesty, never graded for belief.

**Memory verses — 16-verse anchor core** (evangelical school; short, load-bearing; rolling + cumulative; tested on finals): **20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35, 14:6, 15:5, 16:33, 17:3, 19:30, 21:17.** Planted one per unit (U0,U1,U2,U4,U6,U9,U12,U14,U15,U18,U19,U20,U21,U23,U25,U27); other units review. Longer/secondary verses (20:30-31, 2:11, 3:36, 4:50, 5:24, 7:37-38, 9:25, 12:24, 14:16-17, 18:37) are taught but not memorized (optional stretch).

## 6. Source assets

- **40 sermons** (`docs/john/john-sermons/`), Adam's own John series. Auto-matched to a lesson by passage overlap (the pipeline parses filenames). Map + seams + emphases + gaps: `docs/john/Sermon_Library_to_Curriculum_Map.md`. Pacing rules from the transcripts: one interaction/one sitting; verse-count bows to the text; recap generously; land in worship.
- **External resources** (`docs/john/John_External_Resource_Map.md`): 14 vetted TGC / Ligonier / Third Millennium / BibleProject resources, tier-tagged (S/B/D), with a course-phase crosswalk. **Derive and cite; never copy.** Standouts: Thirdmill Gospels Lesson 5 (free full John survey), BibleProject videos (best (S) on-ramp), Doriani's John lectures (teacher depth), the "Final Days of Jesus" Passion harmony.

## 7. Production via the app (the pipeline)

**The generator** (`webapp/generator.py`): builds a system prompt from a format's `structure` spec + injects the voice rules + grounds Scripture in the co-located **Study Bible MCP** (28 tools; ESV fetched live via the **Crossway `BIBLE_API_KEY`**). Standards spine in `resource-generators.yaml` (`formats`) + `webapp/standards/` (BIB subject = Bible & Theology, the course's home).

**Formats for this course** (`resource-generators.yaml`):
- **Bespoke (authored for this course):** `bible_lesson_guide` (the 5-move governed teacher guide), `bible_reading_guide` (per-unit student guide), `student_devotional`.
- **Reused generics:** `quiz`, `answer_key`, `study_guide`, `flashcards`, `scripture_memory_plan`, `reflection_journal`, `book_survey`, `rubric`, `performance_rubric`, `project_guide`, `character_study`, `script`, `apologetics_argument_map`, `harmony_chart`, `exegesis_report`. (`slide_deck` cut.)
- Note: the app's global system identity still says "Christian classical-education curriculum designer" — **left unchanged by decision**; the John pipeline overrides register to evangelical via its PREAMBLE.

**The pipeline** — `scripts/john_gen.py` (single generation path):
- Subcommands: `lesson --index N [--passage]` · `reading-guide --unit U2` · `devotional --passage 1:35-51` · `course --doc <slug> | --all`. Flags: `--dry-run` (assemble, no API), `--force`, `--no-sermon`.
- Drives the REAL app loop (`providers.run` over `MCPBridge`, model `claude-opus-5-5`) so citations are genuinely tool-grounded ESV. Pins facts from the calendar map; carries ESV + three-tier + evangelical design invariants on every job; auto-matches the paired sermon.
- **Sturdiness:** reuses one MCP bridge per batch; idempotent (skips existing unless `--force`); one-shot retry; never writes a broken/too-short file; JSONL run log at `docs/john/_john-gen-log.jsonl`.
- Outputs: teacher guides → `docs/john/john-lessons/GEN_*.md`; student + course docs → `docs/john/john-materials/GEN_*.md`. **GEN_ files are drafts to review**, not final.
- Course `--all` week-one set (5 docs): `how-to-read-john` (book_survey), `reading-journal-guide` + `quiet-time-journal-guide` (reflection_journal), `memory-master` (scripture_memory_plan, 16 verses), `memory-cards` (flashcards, 16).
- Companion: `scripts/plan_passages.py` writes `docs/john/john-lesson-passages.json`.
- Per-lesson production inventory: `docs/john/john-production-inventory.json` + `docs/john/John_Production_Plan.md`.

## 8. Built so far

- **6 hand-built teacher guides** (the exemplars the generator matches), in `docs/john/john-lessons/`: U0-L1 (aim of the course), U0-L2 (author/how to read a Gospel), U1-L1 (whole Prologue), U1-L2 (1:1-5 deity), U1-L3 (1:6-13 received/rejected), U1-L4 (1:14-18 Word made flesh).
- **2 GEN proof lessons** (U2 1:35-51) proving the tool path (bare-API then tool-grounded).
- All planning docs in `docs/` (see §9).

## 9. File map

| File | Role |
|---|---|
| `docs/john/John_Build_Spec.md` | **this doc — start here** |
| `docs/john/John_Calendar_Map.md` + `docs/john/john-calendar-map.json` | authoritative dated sequence |
| `docs/john/john-lesson-passages.json` | per-lesson sub-passages |
| `docs/john/John_Lesson_Template.md` | the 5-move lesson template |
| `docs/john/John_Assessment_Menu.md` | grading, rubrics, assessment set |
| `docs/john/John_External_Resource_Map.md` | vetted outside resources (cite, don't copy) |
| `docs/john/Sermon_Library_to_Curriculum_Map.md` | 40 sermons → units, seams, gaps |
| `docs/john/John_Production_Plan.md` + `docs/john/john-production-inventory.json` | what to generate, per lesson |
| `scripts/john_gen.py` | the generation pipeline |
| `scripts/plan_passages.py` | sub-passage planner |
| `docs/john/john-lessons/` , `docs/john/john-materials/` | generated + hand-built outputs |
| `docs/john/john-sermons/` | the 40 sermon transcripts |
| `resource-generators.yaml` | generator formats (incl. the 3 bespoke) |

## 10. Decisions log

Approach B (produce the course via the app) · ESV (via Crossway key) · evangelical register, not classical · 16 memory verses (anchor core) · grading 30/30/25/15 · homework near-zero · two journals · three-tier + teacher-governed + living-Word design · student devotionals graded as participation, theology coached not scored · slide_deck cut · app global identity left unchanged · Holy Week alignment not a priority · May 21 flex = pray for graduates.

## 11. Next steps (build order)

1. **Generate the week-one course documents** (`course --all`), review, put in Adam's hands before Tue 9/8.
2. **Roll unit by unit** from the calendar map: for each unit, recut its sub-passage split as needed, generate the reading guide + the lesson guides (reading each unit's paired sermon), review each draft.
3. **Framing huddle before each starred fresh-build** (Nicodemus, Samaritan woman, foot-washing, crucifixion) before drafting.
4. Generate assessments (checkpoints, projects, finals) just ahead of when each is due.
