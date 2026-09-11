# Living Library — Teacher Tool Plan

Building out Exegetica's teacher tools, **starting with the Living Library**. This
file records the locked architectural decisions ("the boulders") before schema work.

- **Reference design:** Quill & Compass ("quillnext", `C:\Users\adam\quillnext`) —
  its Living Library, mapped in `docs/codebase-map/14-living-library.md`. **Port the
  concepts, not the code** (their stack: Prisma/Inngest/Gemini/Firebase; ours:
  Starlette + Neon + Anthropic + baked study-bible SQLite).
- **Current Exegetica state:** `webapp/library.py` + `webapp/static/library.html` are
  a **discovery layer only** — stateless search adapters (books via Google
  Books/OpenLibrary, YouTube via Data API + local semantic re-rank, podcasts via
  iTunes). "Add to shelf" is **localStorage-only**; nothing is persisted server-side,
  nothing is extracted. These search adapters stay, as the "add" front door.
- **Access:** already teacher-gated (`role === "teacher"` via `acct.js` +
  `TEACHER_EMAILS`); the `/library` route/page exist.

---

## 1. Copyright framework (the rules that shape the architecture)

Owner's directive, confirmed:

1. **Transformative derived works are fair use — storable AND shareable.** A unique
   product *about* a copyrighted work (summary, TOC, themes, study guide —
   SparkNotes-style) is our own creation. → lives in the **global shared catalog**.
2. **The source copy must be lawfully accessed** — purchased, library-borrowed, or
   obtained under the **accessibility exception** (Chafee Amendment 17 U.S.C. § 121 /
   Marrakesh Treaty — e.g. Internet Archive's *Books for the Print Disabled*, which the
   first uploader, a print-disabled user, is authorized to use). This is the precondition
   to *derive*; it is **not** a license to share the original.
3. **The original expression may never be redistributed** — no scans, no large
   verbatim citations. (Ordinary exception: *short* quotations woven into a
   derivative.)

**Operative line:** derived output = shareable; original text = never redistributed.
**Verbatim cap:** derivatives may keep only short citations; large verbatim excerpts
are excluded. (Exact quantity cap — TBD, see Open Questions.)

**Verbatim exception — publicly broadcast content (owner decision, 2026-09-10):**
Full **video/podcast transcripts** *are* stored and shared in the catalog
(`full_text`). Rationale: a freely, publicly broadcast video is a different
acquisition context than a purchased book copy; matches common practice (and
quillnext). The book/document rule is unchanged — **in-copyright source text stays
private (tier 1); only public-domain full text may go global.**

**Accessibility-acquired sources (owner decision, 2026-09-10).** The first uploader is
a print-disabled user with broader lawful access to in-copyright books via the
accessibility exception (above). These flow through the **normal tier-1 path** — private
encrypted source text → shared transformative derivative — with three guardrails:
- The tier-1 row records `acquisition ∈ {owned, borrowed, accessibility}`; the attestation
  affirms lawful access for that type.
- **Enforced invariant:** in-copyright sources (borrowed/accessibility) never populate
  `library_extractions.full_text` — it is set only when `us_clear` is true. So the
  community gets **only the transformative derivative** (short-citation-capped); the
  protected text stays private to the uploader, forever.
- We **do not touch Internet Archive's DRM'd accessible loans** — the user supplies the
  text through the normal upload from their *authorized* accessible reader. No scraping /
  no integration with the lending system (that would break the DRM and exceed the exception).
- **Payoff:** the print-disabled user's broader lawful access enriches the *community
  derivatives* — a standard account gets study materials for books it couldn't itself
  access, without ever receiving one word of the protected source text. (Not legal advice;
  rests on the same transformative-fair-use chain + the accessibility exception for lawful
  access; the private-text + verbatim-cap guardrails are what keep it defensible.)

---

## 2. Three-tier storage model (LOCKED)

| Tier | Scope | Holds | Access rule |
|---|---|---|---|
| **1. Private source vault** | per-uploader, private | the retained **extracted text** (original file discarded after full extraction); **acquisition** provenance (owned / borrowed / accessibility) + attestation; later: private RAG chunks/embeddings | rows readable only where `user_id = current user`; never joined to or served from any shared path |
| **2. Shared extraction catalog** | global, deduped | the **transformative derivative** (summary, TOC, themes, reading level, discussion questions…) + provenance; **and** shareable verbatim text in `full_text` where redistribution is permissible — public **video/podcast transcripts**, and (later) **public-domain** book/document full text | community-readable; **in-copyright book/document text never here** (stays in tier 1) |
| **3. Per-teacher shelf** | per-teacher | lightweight rows referencing tier-2 entries (+ notes/tags/added_at) | the teacher's own |

**Structural guarantee:** the source text lives only in tier 1 keyed to its uploader;
the derivative lives in tier 2, shared. There is **no code path** from a shelf entry to
a source except tier 1's `user_id = me` filter. So User B (no copy) sees the derivative
but can never retrieve the source — the guarantee holds by shape, not by a runtime check.

---

## 3. Dedup keys (tier-2 identity)

| Type | Dedup key |
|---|---|
| Book | normalized ISBN-13; fallback `title\|author` slug |
| YouTube video | 11-char video id |
| Podcast | feed URL (show); + episode GUID if per-episode |
| Article | canonical / normalized URL |
| Document | SHA-256 of the file bytes |

---

## 4. Add / dedup / extract flow

1. **Add** → find-or-create the tier-2 row by dedup key.
   - `EXTRACTED` → shelf links **instantly, no reprocessing**.
   - `EXTRACTING` → link + poll status.
   - new → create row, run extraction **once** from the provided copy → write
     derivative → `EXTRACTED`; everyone who adds it afterward reuses it.
2. **Grounding split** (design axis, refine later): a derivative can be generated
   **from a provided copy** (richer, quote-capable within the short-citation cap) or
   **from the model's own knowledge** when no copy is provided (allowed for
   in-copyright works). Distinguish via a grounding-source / `has_source_copy` field.

---

## 5. Storage & pipeline decisions (LOCKED)

- **Original file → discard after *verified-full* extraction.** Never on partial/failed
  (keep for retry until confirmed whole). "Full" = all pages/chapters extracted, not
  truncated; a scanned image-only PDF (no text) is **not** full → flag for OCR or
  reject (else we'd delete the source and be left with nothing).
- **Transient original binary → Cloudflare R2.** Presigned **direct browser→bucket**
  upload (keeps big files off the 1 GB Fly app machine — the real "under load" win),
  private bucket, server-side encryption, lifecycle auto-expire (~48 h) as an
  orphan backstop; explicit delete on verified-full extraction. **R2 is not on any
  read path** — an outage only blocks *new uploads*, never reading the library. R2
  over S3: zero egress, S3-compatible API. **Server validates after upload** (object
  exists, type/size, metadata/ISBN) before enqueuing — never trust the client.
- **Retained private text + shared derivative + shelf + job status → Neon (Postgres),
  relational tables** (chosen over jsonb blobs for dedup lookups + querying/integrity).
  Private text is **app-side encrypted** (AES-GCM, key = Fly secret) so a DB dump can't
  leak copyrighted text.
- **Attestation + acquisition:** the tier-1 row records `acquisition` (owned / borrowed /
  accessibility) + a timestamped attestation of lawful access for that type ("I own",
  "I've borrowed", or "I'm authorized to access this as a print-disabled user under the
  accessibility exception"). In-copyright acquisitions (borrowed/accessibility) never set
  the shared `full_text` — enforced by the `us_clear` gate (§1).

---

## 6. Extraction worker → Inngest (serve mode) (LOCKED)

- **Serve mode**: Inngest cloud calls **into** the app over HTTP → the inbound request
  **wakes the scaled-to-zero Fly machine** → the step runs → the machine sleeps.
  (NOT *connect* mode, which needs an always-on outbound worker and defeats
  scale-to-zero.)
- **Buys:** durable steps + automatic retries; **flow control** (concurrency cap /
  throttle) to protect the Anthropic budget when uploads burst; `step.sleep` /
  `waitForEvent` / cron; a real observability dashboard.
- **Fit:** Python SDK supports FastAPI (Starlette-based) → mount a small serve
  endpoint in the Starlette app.
- **Constraint:** Inngest step output-size limits → large text stays in R2/Neon;
  steps pass **ids/references, never payloads** (the reason quillnext's
  `BookExtraction` has a transient `fullTextRaw` holding field).
- **Not on the read path** — an outage delays extraction, loses no data. Self-hostable
  (`inngest start` / Docker) if we ever drop the cloud.

**Extract-first scope:** Books, YouTube videos, Podcasts (podcasts trickier — audio,
per-episode — likely sequenced after books/videos).

**Resulting pipeline:**
`R2 (transient file)` → `Inngest (durable, concurrency-capped job)` →
`Anthropic (derive)` → `Neon (private text + shared derivative + shelf)`.

---

## 7. Relationship to the academic spine (LOCKED)

The **academic spine** is Generate's pedagogical backbone: a K–12 hierarchy
**Subject → Sub-subject(strand) → Topic → Sub-topic → Objective**. Authoritative
source = the **app spine** `webapp/standards/standards-tree.json` +
`standards-objectives.json` (14 / 105 / 435 / 1,897 / 11,642 as of 2026-09-10),
with precomputed embeddings (`standards-embeddings.npy`). The
`quill-standards/academic_standards_master.json` + `academic-spine.md` are STALE
(12/86/365/1,626/26,016) — see [[ref-academic-spine-source]]. Objective counts are
**intentionally variable** (fitted to each sub-topic's complexity), so treat
objectives as variable-grain.

- **Two axes that meet in Generate:** the spine = the pedagogical axis (*what* to
  teach, at *what* level); the Living Library = the content axis (*what to teach
  from*). Generate produces resources that are **objective-aligned AND
  source-grounded** — quillnext's `generatedFrom…Id` provenance.
- **Books map onto the existing spine, coarse→fine:** book-level → subject / strand /
  topic (usually the relevant sub-topics); section-level (chapters/units) → topics /
  sub-topics / objectives. A book almost never introduces new structure.
- **"Can't place it" is a spine signal, not a workaround:** extraction **proposes a
  spine addition for curator review** rather than inventing per-book structure. The
  spine grows deliberately, evidence-driven.
- **Alignment is auto-proposed at extraction, teacher-curated.** Reuse the spine
  embeddings to suggest node matches (owned data, no external service).
- **Canonical store = Postgres `spine_nodes`** (decided 2026-09-10 — done up front on
  the empty slate). Seeded from the JSON via `scripts/seed_spine.py` (14,093 nodes:
  14/105/435/1,897/11,642). `library_alignments.spine_node_id` and
  `library_spine_proposals.parent_node_id` **FK to it** (referential integrity, verified —
  a fake node id is rejected). Carries `status` (`active`/`proposed`/`retired`) + `source`
  (`seed`/`curated`) so curation grows it **in place**, no redeploy.
- **The `webapp/standards/` JSON + `.npy` embeddings are a GENERATED READ-CACHE** the
  in-memory hybrid search loads; `generator.py` is unchanged (perf-sensitive path stays
  fast + DB-independent). **Operating invariant:** spine edits (curation) write to
  `spine_nodes`, then **regenerate the JSON + embeddings** so Generate stays in sync.
  (Later option: point `generator.py`'s structure reads at Postgres and/or move
  embeddings to pgvector — not needed now.)
- **Durability:** node ids are durable; a re-sequence updates rows in place rather than
  renumbering, so stored alignments survive.

## 8. Objectives model — three tiers (LOCKED)

"Spine vs. resource" and "shared vs. private" are **orthogonal** axes, giving three
tiers of objective, most-shared → most-private:

1. **Spine objectives** — universal, reusable (in `webapp/standards`).
2. **Community book objectives** — canonical for a specific widely-taught work,
   attached to the **shared catalog row (tier 2)**; every teacher who adds that book
   inherits them.
3. **Personal book objectives** — a teacher's own goals for a class/student
   ("identify the color red…"), attached to the **shelf (tier 3)**, private.

- **Reusability is the router:** applies to >1 book → spine (or a spine-gap proposal);
  particular to one book → resource objective, attached to the resource with **no spine
  parent**.
- **Promotion gradient:** personal → community → spine (recurrence drives promotion).
- **Generate offers the union** (spine via alignment + community + personal); the
  teacher **selects** — nobody is forced to author.
- **Storage hint:** one objectives table keyed to the extraction with a **nullable
  `user_id`** (null = community, set = that teacher's personal), plus `section` ref,
  `status`, and provenance.

## 9. Community-objective governance — wiki-style (LOCKED, not deferred)

- **Versioned** — each edit is a revision (author + timestamp); reversible, nothing
  destroyed.
- **Provenance flags** — `seed` / `community-added` / `promoted-from-personal`.
- **Per-teacher hide is separate from editing** — a teacher hides a community objective
  on their own shelf without mutating the shared one (the tier-3 override).
- **Moderation is a dial** — start **open** (any teacher edits; history protects);
  flip to *propose → approve* later via the `status` field. No re-architecture to
  turn it on.

## 10. Anti-hallucination: grounding-first seeding (LOCKED — the core principle)

Rationale (owner): frontier models **hallucinate even on the most canonical texts**
(the Bible — the reason the study-bible MCP tools exist); non-expert review can't catch
it and expert reviewers don't scale. So **"generate + approve" is rejected.** The
Living Library inherits the same architecture as the MCP tools: **own the data, ground
the model, cite the source, verify the citation.**

**Grounding is unconditional and model-agnostic — not contingent on a hallucination
pilot.** Rationale (owner, 2026-09-10): design to the property (owned-data grounding),
not to a model's current numbers. Evidence that model choice is a fragile basis: the
Opus 5 system card admits it "hallucinates factual claims more than Opus 4.8… confidently
stated an answer it was unsure about," and Artificial Analysis measured Opus 5 at 54.2%
accuracy / **50.1% hallucination** vs Opus 4.8's 46.6% / **35.9%** — i.e. more capable
yet *less* guarded under uncertainty. (This session runs on Opus 4.8, max effort +
reasoning, for that reason.) Grounding may be overkill for some model/book pairs and
essential for others; we build it once, unconditionally, so the app survives model
swaps. Two consequences:
- **Grounding lives in the retrieval/tool layer, not the model.** Retrieve from owned
  source + cite; the model behind it is swappable (the "durable, not single-model" goal).
- **The citation-verify pass is the continuous hallucination measurement** — every
  rejected claim is a caught hallucination, so the signal comes for free in production
  and flags immediately if a swapped model is less guarded. No separate study needed.

**Rule: a community objective may enter ONLY from a verifiable source — never from
ungrounded model memory.** Two admissible sources:

1. **Ingested human-authored objectives** — trust **by provenance**. Openly-licensed
   OER: **EngageNY** (CC BY-NC-SA), **Louisiana LDOE ELA Guidebooks** (CC BY), CK-12.
   License-audit each source, same discipline as the corpus (`docs/ingestion-roadmap.md`
   + `NOTICE`). NC is fine (non-commercial / education).
2. **Source-text-grounded objectives** — trust **by grounding**. Derived from the
   book's *actual text* (PD full text, or a teacher's tier-1 private copy), where
   **every factual claim cites the passage it rests on** → verification is **retrieval,
   not expertise** (the source text is the reviewer). An **automated citation-verify
   pass** (retrieve cited passage → "does the text support this?", the adversarial-verify
   pattern) gates entry to the community tier and rejects unsupported claims.

**Hard rule: seed NOTHING where neither source exists** — no objective beats a wrong
shared objective. The wiki fills those gaps later from teachers who have grounds.

**Seeding the canon:** public reading lists / textbook-adoption lists (CCSS Appendix B
exemplars, AP lists, state adoption lists) are *facts* → use them to define **which**
books to pre-seed; the **objectives** come from OER (provenance) or source-grounding
(grounding), **never** from proprietary guides (SparkNotes/LitCharts) or model memory.

## 11. Ingestion quality & content integrity (LOCKED 2026-09-11)

Uploads take countless shapes (OCR PDFs, mixed EPUBs, wrong/partial files) and a user
could mislabel one (upload a romance novel as *The Hobbit*). Same principle as the MCP
tools: **never trust unverified input.** Two guards, both grounding-first:

- **Identity gate (per upload, before anything is shared).** After text extraction, a
  grounded model check asks whether the extracted text *is the claimed work* — judging
  the WORK, not the edition (a different translation/abridgment/printing still matches).
  **Decision: hard-reject on a confident mismatch** — the copy is discarded, the R2 object
  deleted, nothing enters the shared catalog (an already-`extracted` row is left intact).
  It **fails open** (`unsure` → pass) so an infrastructure hiccup never blocks a real
  upload. **Safety = identity-only:** a mislabeled/pornographic file fails identity and is
  rejected anyway, so no separate content-safety classifier — a *correctly-labeled* mature
  book (Gatsby, Of Mice and Men) is a teacher's curricular call, not ours to police.
- **Best-copy-wins canonicalization.** `library_extractions` no longer welds the first
  copy to the shared derivative. Each copy carries a mechanical `quality_score` (structure
  health + text integrity + length) and a provenance `canonical_tier` (trusted PD source
  Gutenberg/CCEL = 3 > user upload = 2). **Decision: auto-promote clear wins, hold
  borderline.** A new copy becomes canonical iff nothing is canonical yet, or it outranks
  the incumbent's tier, or (same tier) beats its score by ≥ `_PROMOTE_MARGIN` (0.10);
  otherwise it is kept in the uploader's private vault (accessibility preserved) but does
  NOT rebuild the shared derivative. This also fixes the prior last-writer-wins bug.

Columns added to `library_extractions`: `quality_score`, `verify_verdict`
(accepted/rejected/borderline/superseded), `verify_detail` jsonb, `canonical_source`,
`canonical_tier`. Still TODO: a **borderline-review queue** UI (governance §9) and
per-copy quality history when >2 copies compete.

## 12. Open questions / next steps

**Prioritized build order (2026-09-11):**
1. ~~**Borderline-review queue**~~ — **DONE 2026-09-11.** Same-tier copies within
   `_PROMOTE_MARGIN` (0.10) are held `review_status='pending'`; teacher-only endpoints
   (`GET /api/library/reviews`, `POST .../reviews/{promote,reject}`) + a "Copy reviews"
   pill/modal in library.html let a teacher pick the canonical copy (quality signals only,
   never the private text). Promotion fires the `rederive` Inngest fn to rebuild the shared
   derivative from the chosen vault copy. Columns on `library_source_texts`:
   `quality_score`, `review_status` (none/pending/promoted/rejected).
2. ~~**TOC alignment**~~ — **DONE 2026-09-11.** Two parts:
   - *Duplicate-division fold* (`_dedupe_major`, major tier only — chapter numbers
     legitimately repeat across books): a work's front-matter argument, real body, and
     back-matter index for the same book/part fold to the largest (real) body, fixing the
     Institutes 12→4 duplication. Also fixed a latent bug — the cross-ref guard's bare `v`
     token rejected the roman numeral in "Book V" (verse tokens now require their period).
   - *Descriptive titles* from a **structured** published TOC: `filetext.extract_toc` reads
     the EPUB nav / PDF outline (front/back-matter filtered), persisted to
     `library_extractions.toc`; `_align_titles` upgrades a terse section label ("Chapter 5")
     to its TOC title ("Chapter 5. The Confrontation") — by enumerator, or purely positional
     when TOC and sections line up 1:1 — and NEVER overwrites an already-descriptive body
     title. Verified end-to-end on the upload path. The embedded-plain-text "Contents"
     parser was tried and **dropped as unreliable** (it mis-titled Pilgrim's Progress);
     alignment uses structured TOCs only. Also fixed a latent crash: `step_ingest_upload`
     referenced `meta` without receiving it (would NameError on every upload) — now passed
     through from the worker.
3. Next PD source waves (Sefaria, Perseus) per docs/living-library-sources.md.

**Bulk seeding + extraction cost (2026-09-11).** `scripts/seed_batch.py` seeds the shared
catalog from the public-domain list (`docs/classics-lists-pd-split.md`) via the **Batch API**
(50% off) on **Claude Sonnet 5** (`EXTRACTION_MODEL` default is now `claude-sonnet-5`). Two
batch rounds: derive + propose, then verify. Cost drivers cut four ways (approved): Sonnet
over Opus (~−60%), Batch API (−50%), **verify batched one-call-per-section** (was one call
per objective — core change in `verify_objectives`, benefits every path), and **section-text
prompt caching** on the interactive path only (in batch, propose/verify are separate rounds
so the 5-min cache can't hit — `cache=False` there). Estimated ~$45–50 for all 266 PD titles;
the seeder reports **actual** usage/cost and has `--limit N` for a measured pilot and
`--dry-run` (fetch+segment, no spend). Extraction request-building is now split into
`derive_params`/`propose_params`/`verify_params` reused by both the interactive `_call` path
and the batch seeder.

- **Verification pilot — NOT a gate (decided 2026-09-10).** Grounding is locked
  unconditionally, so no pilot is required before building. The citation-verify pass
  provides continuous, model-agnostic measurement instead. (A pilot is available later
  only as optional threshold-tuning, never as a go/no-go.)
- **Schema extension (NEXT build):** add spine-alignment (extraction → node IDs,
  book- and section-level), the objectives table (nullable `user_id`, `section`,
  `status`, provenance) + a revisions table, and — later — the deferred
  `Resource`/generated-materials table (`generated_from_extraction_id` + objective ids).
- ~~Cloud vs self-hosted Inngest~~ — **RESOLVED: cloud** (2026-09-10). `inngest` Python SDK
  installed; `INNGEST_EVENT_KEY` + `INNGEST_SIGNING_KEY` in `.env` (serve mode). The
  Inngest Cloud MCP (optional, for inspecting runs) needs a separate `INNGEST_API_KEY`
  from app.inngest.com/mcp/setup.
- **Verbatim-citation quantity cap** — how much direct quoting a derivative may keep.
- **Fly cold-start** — each Inngest callback wakes the machine and re-spawns the
  study-bible MCP subprocess in `lifespan` (unused by extraction); minor waste.
- **Later:** private RAG chunks/embeddings for the owner's grounded generation
  (in-copyright chunks stay private; PD full-text may be global); wiring the catalog
  into the Generator / Course Builder as a source (`sourceType`/`sourceId`).
