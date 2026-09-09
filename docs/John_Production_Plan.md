# John — Production Plan
## Driving the resource generator to build the course

The John course is exactly what the generator app was built to produce. Rather than hand-write 150 lessons' worth of materials, we drive the tool from the calendar map and this inventory (Approach B). The six teacher guides already hand-built become the **style exemplars** the tool matches. Machine-readable inventory: `john-production-inventory.json`.

## What the tool can make (John artifact → generator format)

The generator has 75 formats; these are the ones the course uses.

| John artifact | Generator format | Audience |
|---|---|---|
| Teacher lesson plan | `lesson_plan` | teacher |
| Per-unit reading guide | `inductive_passage_study` (or `close_reading_guide`) | student |
| Checkpoint quiz + key | `quiz` + `answer_key` | student/teacher |
| Memory master + verse cards | `scripture_memory_plan` + `flashcards` | student |
| Project assignment + rubric | `project_guide` + `rubric` | student |
| Student-led devotional template | `devotional_guide` | student |
| Character-study project | `character_study` | student |
| Dramatized-reading project | `script` | student |
| "Why trust John" project | `apologetics_argument_map` | student |
| Semester final + key + study guide | `quiz` + `answer_key` + `study_guide` | student |
| "How to Read John" (Unit 0) | `book_survey` / `how_to_guide` | student |
| Journal guides | `reflection_journal` | student |
| Passion harmony (teacher prep) | `harmony_chart` | teacher |
| Exegesis prep | `exegesis_report` | teacher |
| Slides (optional) | `slide_deck` | teacher |

## The one integration point

The generator was built to produce from **standards objectives** (choose spine objectives, generate a format). The John course is **passage-driven**. So each generation job is fed:

1. the **passage** and the lesson's **big idea** and **objectives** (from the calendar map and the teacher guide),
2. the relevant **Bible-spine strands** (Biblical Literacy, New Testament Studies, Hermeneutics) so it stays standards-aligned,
3. the **style exemplar** (our lesson template and the six built guides) so output matches our voice, the three-tier design, and the teacher-governing structure.

This is the small adapter that turns the objective-driven tool into a source-driven one, which is the ingestion phase the app was already heading toward.

## New formats to author (the course's own molds)

The 75 formats are a starting palette, not a ceiling. A format is authored data: an ordered `structure` list the generator renders into its system prompt, plus a definition, a when-to-use, and formatting rules, the same kind of extension as the Agriculture subject added to the spine. Because the tool predates this course, three of its shapes deserve a bespoke format rather than the nearest generic fit:

1. **`bible_lesson_guide` — the 5-move governed lesson guide (high priority).** Encodes our template exactly: the header with Reach / Hold / Stretch, the talk budget, the five moves (Quiet time / Hear the Word / Work the text as a question sequence with no lecture / Land and minister / Respond), the after-the-bell block, and teacher notes, with 50 / 36 / 26-minute variants. This is the mold that lets the tool generate the remaining 145 teacher guides in our structure, matched to the six hand-built exemplars.
2. **`bible_reading_guide` — the per-unit student guide** shaped to our lesson arc and the two-journal system, tiered for the three-tier room, rather than the generic inductive study.
3. **`student_devotional` — the participation-graded devotional template** mirroring the miniature lesson arc students lead.

Everything else reuses the generic formats well: `quiz`, `answer_key`, `flashcards`, `scripture_memory_plan`, `study_guide`, `rubric`, `project_guide`, `harmony_chart`, `exegesis_report`, `book_survey`, `apologetics_argument_map`, `character_study`, `script`.

## Course-level artifacts (build once, week one first)

| Artifact | Format | Status |
|---|---|---|
| Lesson template (style exemplar) | `lesson_plan` | built |
| "How to Read John" orientation handout | `book_survey` | to generate |
| Reading Journal guide + template | `reflection_journal` | to generate |
| Quiet-Time Journal guide | `reflection_journal` | to generate |
| Memory Verse master sheet (25 + schedule) | `scripture_memory_plan` | to generate |
| Memory Verse card set (25) | `flashcards` | to generate |
| Rolling memory quiz bank + keys | `quiz` + `answer_key` | to generate |
| Participation rubric | `rubric` | built (menu) |
| Student-led devotional rubric | `rubric` | built (menu) |
| Project & Oral rubric | `performance_rubric` | built (menu) |
| Student-led devotional template | `devotional_guide` | to generate |
| Semester 1 & 2 finals (+ keys + study guides) | `quiz`+`answer_key`+`study_guide` | to generate |

## Per-lesson artifacts (the tool walks the calendar map)

Rules applied in `john-production-inventory.json`:

- **Every lesson** gets a `lesson_plan` teacher guide (151 total; 6 built, 145 to generate).
- **Each teaching unit's first lesson** gets one student **reading guide** (`inductive_passage_study`, 22 total).
- **Each unit's memory verse** gets a card at its first lesson (`flashcards`, 26).
- **Checkpoint lessons** get a `quiz` + `answer_key` (4 each).
- **Project intro lessons** get a `project_guide` + `rubric`.
- **Half-day recap lessons** get a memory `quiz`.

Aggregate per-lesson: **215 artifacts**, of which 6 are built and ~209 are to generate.

## Decisions to confirm

1. **Author the three bespoke formats** (`bible_lesson_guide`, `bible_reading_guide`, `student_devotional`) so the tool produces our structures natively, starting with the lesson guide. I lean yes; the lesson guide is the unlock.
2. **Teacher plans:** once the `bible_lesson_guide` format exists, generate the remaining 145 with the tool and review, hand-finishing the starred fresh-build units (Nicodemus, Samaritan woman, foot-washing, the cross). The six built guides are the exemplars the format is written from.
3. **Slides:** add a `slide_deck` per lesson, or skip (the design teaches from the board and the journals). I lean skip for now.
4. **Project placement:** the inventory currently detects 2 project intros; the four marquee projects (The Signs, a Q2 content piece, Teaching the Farewell Discourse, Passion & Response) need their intro and due lessons marked explicitly in the map. A quick refinement.

## Recommended generation order

1. **Course-level, week one:** "How to Read John," the two journal guides, the memory master sheet and cards. These go out with the syllabus in the first days.
2. **A proof run:** generate one reading guide (Unit 1) and one quiz with the tool, review against the hand-built teacher guides, and tune the adapter until the output matches our voice.
3. **Unit by unit:** as we build each unit's teacher guides, generate that unit's reading guide, memory cards, and any checkpoint or project pieces alongside.
