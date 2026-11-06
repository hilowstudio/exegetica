# Ingestion Roadmap — Research Spike Outcome

Derived from the six-agent research spike (2026-08-24). Full ranked writeup:
the "Sources Worth Owning" artifact. This file is the working checklist for the
resources labeled **Now**, plus the deferred phases.

Architecture unchanged: **own the data** — everything bundled into the portable
SQLite at build time; PD or openly-licensed only; attribution/ShareAlike honored
in `NOTICE`. New data follows the existing `download_*` → `import_*` script
pattern; new tools register in `tools.py` (`TOOLS`) + `server.py`
(`_TOOL_HANDLERS`).

## Cross-cutting infrastructure (build once, reused)

- **OSIS / reference normalizer** — parse `Rom.1.19-Rom.1.20` and friends to the
  internal book/chapter/verse scheme. Needed by confession proof-texts, TSK,
  topical, devotional. (`parsers/refs.py`)
- **SWORD-style verse-keyed importer** — many PD classics (TSK, Barnes, Vincent,
  Robertson, ISBE, Nave's, Easton's, Smith's) ship as verse-keyed modules/JSON;
  one reader amortizes across all of them.
- **Versification map** — already exists for the LXX; reused for the deuterocanon.

## "Now" checklist

Status: [ ] todo · [~] in progress · [x] done

### Phase A — quick unlocks (no or trivial download)
- [x] **Deuterocanon wiring** — book-name map for 14 WEB apocrypha books already
  in `translations`; fix `Judith→Jude` collision; fold Susanna/Bel/Letter of
  Jeremiah/Psalm 151; auto-route deutero refs to WEB. Tools touched:
  `get_passage`, `lookup_verse`, `compare_translations`. **Done + tested.**
- [x] **Reader-mode frequency** — `word_frequency` table materialized from owned
  STEPBible tags (`build_word_frequency.py`, 14,550 Strong's); new
  `vocabulary_list(passage, threshold)` tool; `reader_mode` flag on
  `lookup_verse`/`get_passage`. **Done + tested (Greek + Hebrew).**
- [~] **Dictionaries** — new `dictionaries` table + generic importer
  (`download_dictionaries.py`/`import_dictionaries.py`); **Easton's ingested
  (3,961 articles)** and merged into `get_bible_dictionary`. Smith's/ISBE feed
  the same table once a clean source is pinned (search API was rate-limited).
- [x] **Tyndale Open Study Notes** — **already present**: the DB carries 16,923
  Aquifer `study_notes` + the Tyndale Open Bible Dictionary (6,120), served by
  `get_study_notes` / `get_bible_dictionary`. No re-ingest (would duplicate).

### Phase B — the verse graph (M; builds shared infra)
- [x] **Confession proof-texts** — `reformed-standards/compendium` (Apache-2.0)
  imported: **10,152 proof-texts** across WCF/WLC/WSC/WSC-PCA/Heidelberg/Savoy.
  New `confession_proof_texts` table + OSIS normalizer (`parsers/refs.py`, reused
  infra); tools **`find_confessions_by_verse` + `get_confession_proofs`** (both
  tested); +4 net-new docs → `get_confession`. **Follow-ups:** `Creeds.json`
  breadth (~19 early-Reformation confessions), and 5 compendium docs whose YAML
  shape (top-level `articles`/`markdown`) the section parser doesn't yet read
  (Second Helvetic, Scots, Sum of Saving Knowledge, 1858 Abstract, 95 Theses).
- [~] **Treasury of Scripture Knowledge** — **deferred as largely redundant.**
  Our 344,799 OpenBible.info cross-refs are themselves TSK-derived; scrollmapper
  and OpenBible both trace to TSK. Low marginal value vs. effort; revisit only if
  the *classic curated chain ordering* is specifically wanted.
- [ ] **Nave's Topical Bible** (PD) → new `topical_index` + `get_topical`.
- [x] **Spurgeon devotionals** — *Morning & Evening* imported: **732 readings
  (697 verse-keyed)** → `devotionals` table + **`get_devotional`** (by verse or
  by calendar date; tested). *Faith's Checkbook* is a follow-up (no clean JSON;
  needs CCEL/Gutenberg parsing).

### Phase C — depth & voices (M; reuses B infra)
- [ ] **ISBE 1915** (PD) → `get_bible_dictionary`.
- [ ] **Barnes' Notes** (PD) → `get_commentary`.
- [ ] **Ellicott's Commentary** (PD) → `get_commentary`.
- [ ] **Vincent's Word Studies** (PD) → `word_study` enrichment.
- [ ] **Robertson's Word Pictures** (PD as distributed; vol. 5 footnote) →
  `word_study` enrichment.
- [ ] **Patristic full works** — `HistoricalChristianFaith/Writings-Database` +
  `gregorycrane/nicenefathers` (TEI backbone) → `patristic_writings` +
  `get_writing`/`search_writings`. Filter the permission-only tail.

## Deferred (Later)
KJVA second deuterocanon witness · Clementine Vulgate · MACULA Greek (Louw-Nida) ·
Book of Concord · Method for Prayer · Pulpit / Hastings / McClintock & Strong /
Lange / Meyer / Alford (L-effort OCR).

## Excluded (license)
puritan-prayer (Valley of Vision ©) · Monergism (by-permission) · gnt-reader data
(SBLGNT EULA + Mounce ©) · Vine's/Wuest (©) · CCEL/New Advent editions ·
scrollmapper deuterocanonical fork (no license) · unfoldingWord UGNT (SA+™) ·
Archive.org items without a PD flag.
