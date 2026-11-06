# The academic spine

A K-12 hierarchy, **Subject → Strand → Topic → Sub-topic → Objective**, that the Prep Room's "From standards" mode drafts toward. It is **what to teach**; `resource-generators.yaml` is **how to deliver it**.

Coverage (2026-11-05): **14 subjects · 105 strands · 435 topics · 1,897 sub-topics · 14,872 objectives**, of which 11,323 are anchored to a published standard or, in Bible & Theology, to Scripture and the confessions.

| File | Purpose |
|---|---|
| `standards-tree.json` | The menu: subjects, strands, topics, and sub-topics, with each sub-topic's objective count and grades. No objectives, so it loads fast. |
| `standards-objectives.json` | Objectives keyed by sub-topic id. Only the objectives a teacher selects reach the model. |
| `standards-embeddings.npy` / `.json` | Precomputed embeddings for the standards search (`scripts/build_standards_embeddings.py`). The app checks a signature and falls back to word matching when they are stale. |
| `format-recommendations.yaml` | The formats each strand suggests first. |

Anyone can browse the spine at `/prep-room/standards` (`standards_page` in `webapp/about.py`): subjects, strands, topics, and sub-topics, each sub-topic's objectives loaded when it is opened, and the Prep Room's search. A signed-in teacher also gets a link from each sub-topic into the Prep Room at that sub-topic.

These JSON files are the working spine. `scripts/seed_spine.py` copied an earlier version into the Postgres table `spine_nodes` on 2026-09-10, but nothing reads that table now and nothing exports it back, so it is out of date.

## How it was built

1. **The Quill template.** The spine began as Quill & Compass's `quill-standards/`: 12 subjects and 26,016 objectives, exactly 16 per sub-topic, spread from kindergarten to grade 12 by an algorithm (Bloom level, subject difficulty, prerequisites). The fixed count produced filler and topics that drifted as the grades climbed. `scripts/build_standards_index.py` first distilled it into the two JSON files. The template files are stale; do not trust their counts. They left the repo on 2026-11-06, and git history and `_backups/quill-standards.pre-fanout.tar.gz` keep them.
2. **Published standards, owned locally.** `scripts/download_standards.py` downloads standards once from the Common Standards Project into `standards/raw/` (Common Core, NGSS, NCSS, the national geography standards, CSTA, the National Core Arts Standards, ITEEA, Family and Consumer Sciences, CASEL, the National Health Education Standards, ACTFL, and since 2026-11-05 the AFNR standards, 2024 edition). `scripts/build_standards_crosswalk.py` normalizes them into `standards/standards-index.json`, each with its verified code and grade span.
3. **The September rebuild.** Twelve subjects were rebuilt by hand under the maker's rule (below), which brought the spine to 14 subjects and 11,642 objectives. How that rebuild was carried out is not recorded.
4. **The November rebuild (2026-11-05).** Bible & Theology had never been rebuilt (220 of its 223 sub-topics still held exactly 16), and Agriculture, Food & Natural Resources, added late because agricultural education and FFA are central at Yorkville, was a uniform first pass (exactly 6 objectives in every sub-topic, no standards). `scripts/rebuild_objectives.py` rebuilt both, one sub-topic at a time, with Claude Opus 5.5, for about $35. Bible & Theology now has 5,062 objectives, 4,811 of them anchored to Scripture verified against the bundled Bible and, where a confession states the doctrine, to that article, verified against the library's documents. Agriculture has 2,407, and 1,293 of them, nearly all of its high-school objectives, cite the AFNR standard they teach. Each sub-topic's result, with its inputs, model, and token use, is kept in `standards/rebuild/`, with the old sets beside them.

## The rule for objectives

The count is not a target. A sub-topic gets as many objectives as its distinct competencies warrant, drawn from the real sub-skills of its grade span, with no padding and no trimming. Each objective is a distinct, student-facing competency a teacher can observe, on the sub-topic's own topic, placed at the grade where a student can first do it, and anchored to the standard it teaches where one exists. In Bible & Theology a student's feelings or profession of faith is never an objective, and doctrinal positions are stated as the tradition's.

The rebuilt subjects differ in grain: Bible & Theology and Agriculture average about 22 objectives per sub-topic, the September subjects about 5. The maker chose the richer grain for the November rebuild.

## Schemas

`standards-tree.json`
```json
{ "subjects": [ { "id": "BIB", "name": "Bible & Theology", "sub_subjects": [
  { "id": "BIB.1", "name": "Apologetics and Worldviews", "topics": [
    { "id": "BIB.1.1", "name": "Arguments for God's Existence", "sub_topics": [
      { "id": "BIB.1.1.1", "name": "Arguments for God's Existence", "objective_count": 21, "grades": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] }
    ]}]}]}]}
```

`standards-objectives.json`, keyed by sub-topic id: `id` (dotted), `t` (text), `g` (grade, 0 = K), `c` (order within the sub-topic, 3 to 26), `u` (UUID), and `a` (anchors: `standards`, or `scripture` and `confessions`).
```json
{ "BIB.10.1.1": [
  { "id": "BIB.10.1.1.1", "t": "Identify the Ten Commandments as the rules God gave his people for how to live", "g": 0, "c": 3, "u": "…",
    "a": { "scripture": ["Exodus 20:1-17"], "confessions": ["Westminster Shorter Catechism Q41"] } }
]}
```

## After any change

1. Edit the objectives (or rerun `scripts/rebuild_objectives.py` for a subject).
2. Rebuild the embeddings: `PYTHONPATH=. .venv/Scripts/python.exe scripts/build_standards_embeddings.py`
3. Run `python -m pytest`.

The grade on an objective is a default a teacher can adjust; the complexity order and the Bloom verb are the better guide to cognitive demand.
