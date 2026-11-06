# Living Library — Generation Redesign

**Status:** proposed (2026-09-17). Revises the generation/processing approach in
`docs/sources/living-library-plan.md`. Grew out of a design conversation; this is the plan of record for
how the Generator should work against Living Library books.

## North star

**Omniscient comprehension, positioned output.** The model understands the *whole* work; the
resource it produces lands exactly where the student is in reading it. Concretely:

- **Read the real text at generation time.** Don't generate from pre-extracted, pre-verified
  objectives — those are a lossy compression of the very content the model will write from.
- **Let the model understand the full work.** A quiz on chapter 7 is stronger when written by
  something that has read the whole book: it knows which details in ch. 7 are load-bearing
  (pay off later) versus incidental, and can develop themes intentionally.
- **Calibrate the artifact to the student's position.** Questions answerable from what's been
  read; answers honoring the reader's current vantage (dramatic irony intact); no spoilers in
  student-facing material. The model is like a teacher who has read the whole novel writing a
  quiz for a class that is only at chapter 7.
- **Stop indexing books to the academic spine.** No pre-alignment, no reverse-lookup index.

This trades a large, LLM-heavy indexing subsystem (derive → propose objectives → verify → align)
for a plain shelf + live reading + a light comprehension aid.

## Decisions locked (from the design conversation)

1. Generation grounds on the **actual text**, read at generation time — not on pre-extracted objectives.
2. The model should **understand the full work** to produce strong resources, even when the assignment targets one section.
3. Output is calibrated to the student's position via an explicit **position marker**.
4. Books are **not** pre-anchored to the academic spine (alignment + reverse index dropped).
5. Per-section **verified objectives are dropped** as a generation source.
6. **Mechanical chapter segmentation is kept** (we already do it for the reader).
7. **Teacher and student editions calibrate differently** (teacher may be arc-aware; student positioned).
8. Reader **persistence features** (highlights, annotations, precise sync) are **out of scope here** — parked.

## The core model

Two inputs govern a generation:

- **Comprehension** — the model's understanding of the whole work.
- **Position** — where the student is.

### Size-adaptive comprehension

Reading live is best when it fits; pre-comprehend only when it can't.

- **Fits-in-context works** (a normal novel): feed the **whole text** at generation time. No
  pre-processing beyond segmentation.
- **Large works** (Summa ≈ 2.5M words, Josephus ≈ 800k): can't be stuffed into context, so
  pre-build a **whole-work comprehension layer** + **section retrieval**; feed the comprehension
  layer + the target section's text (+ prior-context recap).
- **Threshold:** a token budget (see Open Decisions) picks the path per book.

### The position marker (new primitive)

An explicit, structured statement of where the student is, passed at generation time:

```
{
  book: "great-expectations",
  coverage: { through_section: 7 },        // or { range: [5, 7] }
  read_set: [1..7],
  not_yet_set: [8..59],
  vantage: "Treat the student's knowledge and interpretations as of the end of section 7."
}
```

It drives all calibration: what's answerable, how answers read (provisional / dramatic irony),
difficulty, and whether forward-priming (never forward-revealing) prompts are allowed. It's
derived from the teacher's selection, not authored by hand.

### Generation input (assembled prompt)

```
[system]     pedagogical role + the "omniscient comprehension, positioned output" rules
[knowledge]  whole-work comprehension layer  (large works)  OR  the whole text  (fits-in-context)
[target]     the target section's full text  (+ prior-context recap for precise vantage)
[position]   the position marker
[task]       format + grade band + brief + edition (teacher | student) [+ optional standard]
```

## Comprehension layer — what it must contain

Not a blurb. The point is to make the model genuinely well-read on the work. Per book:

- **Whole-work summary** — one tight paragraph.
- **The arc** — how the work develops (opening / turns / climax / resolution), the major hinges.
- **Themes & motifs** — where each is introduced, developed, and paid off.
- **Structure map** — every chapter/section with a 1–2 sentence "role in the whole."
- **Significance map** — which elements are load-bearing (set up or resolve something later)
  versus incidental. *This is what lets the model choose what is worth a question.*
- **Cumulative recap ladder** (optional, for big works + precise vantage) — "the story so far as
  of section N," each entry bounded to its point (inherently spoiler-safe).

**Build method:** map-reduce over the full text — per-section notes → synthesize the whole-work
understanding. One LLM job per book, run once (rebuild trigger in Open Decisions). This *replaces*
the old derive → propose-objectives → verify → align pipeline.

## Generation flow (new)

1. Teacher picks a **book** from the shelf.
2. Picks a **position** — a chapter or a range ("through ch. 7", "chs. 5–7").
3. Picks **format** + grade band + optional **brief** + **edition** (teacher/student) [+ optional standard to align to].
4. The server assembles the prompt above and streams the resource (same SSE path as today).

**Prompt rules baked into `[system]`:**
- Use whole-work understanding to judge significance and develop themes deliberately.
- Produce content answerable from the covered range only.
- Honor the student's vantage — provisional interpretations, dramatic irony ("appears to be…").
- **Student edition:** no spoilers; forward-*priming* prompts allowed ("notice how X is described"),
  forward-*revealing* ones forbidden.
- **Teacher edition:** may be explicitly arc-aware ("this foreshadows X in ch. 20 — steer discussion toward…").

## Data model

Per book, what we keep / add / drop:

| Concern | Store | Change |
|---|---|---|
| Full text (PD) | `books.db` (Reading Room) or `library_extractions.full_text` | **keep** |
| Full text (uploaded, in-copyright) | `library_source_texts` (encrypted, private tier-1) | **keep** |
| Chapter/section structure | `library_sections` and/or `books.db.book_chapters` | **keep** (mechanical) |
| Whole-work comprehension | **new** (`book_comprehension`, see below) | **add** (large works) |
| Grounded per-section objectives | `library_objectives` | **deprecate → remove** |
| Spine alignment | `library_alignments` | **deprecate → remove** |

New comprehension store — proposed `library_comprehension` (Neon): `book_key`, `summary`,
`arc jsonb`, `themes jsonb`, `structure jsonb` (per-section role), `significance jsonb`,
`recap jsonb` (cumulative ladder), `model`, `built_at`. Keyed by a stable book identity so it
serves both PD books and uploads.

**Corpus convergence (decision):** the Reading Room `books.db` now holds 2,427 works with clean
chapters + full text. Strongly consider making it the **PD source the Generator reads**, with
uploads staying private in Neon — one corpus, two consumers (reader + generator), instead of the
separate `library_extractions` full-text path.

## What gets removed

- **`webapp/extraction.py`:** `propose_objectives`, `verify_objectives`, `keep_verified`,
  `align_to_spine`, and the propose/verify params. **Keep** the fetch/ingest paths, mechanical
  segmentation, and add a comprehension-build step.
- **`webapp/inngest_app.py`:** the `objectives-{b}` batch steps and `finalize`'s alignment write;
  replace `derive`/`objectives` with a single `comprehend` step (large works only).
- **`scripts/schema.sql`:** deprecate `library_objectives`, `library_alignments` (+ indexes/FKs)
  after migration; add `library_comprehension`.
- **`webapp/generator.py`:** the objective-driven `build_task`; replace with the
  position + text + comprehension construction. `build_system` gains the vantage rules.
- **`webapp/static/generate.html`:** the spine navigation (subject → … → objective) selection;
  replace with **book → position → format** selection.

## Phased implementation

- **Phase 1 — new generation path for fits-in-context works.** Position marker + read-whole-text
  `build_task`; new generate UI (book + position + format). Old objective path stays behind a flag
  so nothing breaks mid-migration.
- **Phase 2 — comprehension layer + retrieval for large works.** `library_comprehension` +
  map-reduce build; retrieval in **both** modes — section-level fetch *and* a semantic embedding
  index (reuse the existing model2vec / sqlite-vec pattern from the theology layer). Both first-class.
- **Phase 3 — remove the old pipeline.** Delete objectives/alignment code, tables, and the
  spine-selection UI. Execute corpus convergence (books.db as generator source) if chosen.

## Decisions (resolved 2026-09-17)

1. **Corpus — converge on `books.db`.** It is the generator's PD source (2,427 works already there
   with full text + chapters); uploads stay private/encrypted in `library_source_texts`. The
   comprehension layer lives in **Neon**, keyed by `books.db` slug (PD) or extraction id (upload)
   — *not* in `books.db`, so updating comprehension never forces a corpus republish.
   *Load-bearing; do first. Known cost: reconcile the teacher shelf/catalog to `books.db` slugs.*
2. **Context threshold — a word-count switch.** Read the whole text when it fits under ~110k words
   (≈ 150k tokens); above that, comprehension + retrieval. A cheap constant, tuned after measuring.
3. **Retrieval — both section fetch AND embeddings, both first-class.** A teacher-named
   chapter/range → **section fetch** (+ prior-context recap); a topic/theme request → **semantic
   retrieval** over an embedding index (reuse the model2vec / sqlite-vec pattern). A single
   generation may use either or both (e.g. the named section *plus* thematically-relevant passages
   elsewhere in the work).
4. **Standards spine — keep it, as an optional teacher-invoked target at generation time.** The
   spine survives; only the *pre-computed* book↔standard links are dropped. The teacher names a
   standard when they want alignment; the system no longer discovers it for them.
5. **Editions — one generation, both editions.** A position-bounded student artifact plus a
   teacher addendum (answer key + arc-aware notes) in a single pass, so the key and the questions
   can't drift. The UI toggle shows/hides the teacher portion.
6. **Comprehension freshness — lazy build, no schedule.** Built on first generation against a
   *large* book and cached; rebuilt only on canonical-text change or a manual/batch request. (Small
   books are read whole and never need a comprehension layer.)

## Out of scope (parked)

Reader persistence features — highlights, annotations, precise cross-device position, synced
preferences, collections/assigned reading, shared teacher annotation layer. Captured in the
earlier discussion; to be planned separately.
