# Standards Index (distilled from quill-standards)

A compact, bundled index of the K-12 academic spine that powers **standards-
aligned resource generation**. Distilled from `quill-standards/` (2,092 files,
~20 MB) by `scripts/build_standards_index.py` into two lean files:

| File | Size | Purpose |
|---|---|---|
| `standards-tree.json` | ~220 KB | Navigable menu skeleton: Subject → SubSubject → Topic → SubTopic (ids, names, objective counts, grade span). No objectives — small and fast. |
| `standards-objectives.json` | ~3.3 MB | Objectives keyed by sub-topic id. Only the *selected* objectives get injected into the model at generation time. |

Coverage: **12 subjects · 86 sub-subjects · 365 topics · 1,626 sub-topics ·
26,016 objectives** (matches the spine exactly). The 12 subjects align 1:1 with
the resource-generator subject areas.

Regenerate after any change to `quill-standards/`:
```sh
python scripts/build_standards_index.py
```

## Schemas

`standards-tree.json`
```json
{ "subjects": [ { "id": "BIB", "name": "Bible & Theology", "sub_subjects": [
  { "id": "BIB.1", "name": "Apologetics and Worldviews", "topics": [
    { "id": "BIB.1.1", "name": "Arguments for God's Existence", "sub_topics": [
      { "id": "BIB.1.1.1", "name": "...", "objective_count": 16, "grades": [8,9,10,11,12] }
    ]}]}]}]}
```

`standards-objectives.json` — keyed by sub-topic id; fields abbreviated to keep
it small: `id` (dotted standardId), `t` (objective text), `g` (grade 0-12,
0=K), `c` (complexity), `u` (UUID).
```json
{ "BIB.1.1.1": [
  { "id": "BIB.1.1.1.1", "t": "Identify that God made the world…", "g": 8, "c": 15, "u": "…" }
]}
```

## How it powers generation

The spine is **what to teach**; `resource-generators.yaml` is **how to deliver
it**. Together:

1. Instructor navigates `standards-tree.json`: Subject → SubSubject → Topic →
   SubTopic (optionally filtered by grade band).
2. At a sub-topic, its objectives (from `standards-objectives.json`) are shown —
   each with its grade, Bloom verb, and complexity. The instructor selects one
   or more objective(s).
3. The instructor picks a **format** (resource-generators.yaml). The app can
   suggest formats that fit the subject.
4. The backend assembles the prompt: `global_conventions` + the format's
   definition/structure/grade-band adaptation + the selected objective text(s)
   + subject/topic context + the objective's grade & cognitive level — and asks
   for a resource that teaches/assesses *those objectives at that level*.
5. The output (Markdown) is **stamped with the standardId(s)/UUID(s)** so every
   generated resource is traceable to the standards it targets (and cross-
   referable to the Course Builder later).

Notes:
- Grade *placement* in the spine is algorithmic and uneven in spots; prefer the
  **complexity + Bloom verb** to calibrate cognitive demand, and treat the grade
  number as an adjustable default (the spine's own methodology says the same).
- BIB (Bible & Theology) and CFL (Biblical languages) objectives additionally
  trigger the Study Bible tool-grounding + citation rules from
  `global_conventions.sourcing`.
