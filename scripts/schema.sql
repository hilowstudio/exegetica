-- Exegetica schema (Neon Postgres). Idempotent: safe to run repeatedly.
-- Applied by scripts/db_migrate.py. gen_random_uuid() is built in on PG13+.

-- People. Identity comes from Google OAuth (google_sub is Google's stable id).
-- No passwords are stored: sign-in is Google SSO for everyone. Role is assigned
-- at first login (teacher via an allowlist, else student).
create table if not exists users (
    id            uuid primary key default gen_random_uuid(),
    google_sub    text unique not null,
    email         text,
    name          text,
    picture       text,
    role          text not null default 'student' check (role in ('teacher','student')),
    created_at    timestamptz not null default now(),
    last_login_at timestamptz
);

-- A teacher's class, joined by students via a code.
create table if not exists classes (
    id         uuid primary key default gen_random_uuid(),
    teacher_id uuid not null references users(id) on delete cascade,
    name       text not null,
    join_code  text unique not null,
    created_at timestamptz not null default now()
);

create table if not exists enrollments (
    class_id   uuid not null references classes(id) on delete cascade,
    student_id uuid not null references users(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (class_id, student_id)
);

-- Superseded by the per-user JSON blobs below (Stage 3). These were created
-- empty in Stage 1 and never populated, so the drops are safe.
drop table if exists memory_verses;
drop table if exists memory_folders;
drop table if exists chats;

-- Per-user state as a JSON blob. The client owns the data shape and its ids; the
-- server just stores and returns each user's whole blob. A low-risk swap for
-- localStorage that migrates to relational later if teacher analytics ever need it.
create table if not exists memory_state (
    user_id    uuid primary key references users(id) on delete cascade,
    state      jsonb not null default '{"verses":[],"folders":[]}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists chat_state (
    user_id    uuid primary key references users(id) on delete cascade,
    state      jsonb not null default '{"chats":[]}'::jsonb,
    updated_at timestamptz not null default now()
);

-- ===========================================================================
-- Academic spine (canonical store). Source of truth for the Generator's K–12
-- scope-and-sequence (Subject → Sub-subject → Topic → Sub-topic → Objective),
-- housed in Postgres so Living Library alignments get referential integrity and
-- the spine can be curated/grown in place (proposals → active). The JSON in
-- webapp/standards/ + the .npy embeddings are a GENERATED READ-CACHE, regenerated
-- from this table (the perf-sensitive in-memory search still loads them). See
-- docs/living-library-plan.md §7. Seeded by scripts/seed_spine.py from the JSON.
-- ===========================================================================
create table if not exists spine_nodes (
    id         text primary key,           -- durable spine code (e.g. 'ELA.5.5.2'); objectives use their oid
    level      text not null check (level in ('subject','sub_subject','topic','sub_topic','objective')),
    parent_id  text references spine_nodes(id) on delete cascade,  -- NULL for subjects
    position   integer not null default 0, -- order among siblings
    name       text,                       -- label (structure) or objective text
    grade      integer,                    -- objective grade band (g); NULL for structure
    status     text not null default 'active' check (status in ('active','proposed','retired')),
    source     text not null default 'seed' check (source in ('seed','curated')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists spine_nodes_parent_idx on spine_nodes(parent_id);
create index if not exists spine_nodes_level_idx on spine_nodes(level);

-- ===========================================================================
-- Living Library (teacher tool). Three tiers, by design (see
-- docs/living-library-plan.md):
--   * library_extractions  — TIER 2: the global, cross-teacher, deduped catalog.
--       Holds the transformative derivative (summary/TOC/themes/...) + intrinsic
--       metadata, and — only where redistribution is permissible — shareable
--       verbatim text in full_text (public video/podcast transcripts now;
--       public-domain book/document full text later). In-copyright book/document
--       text is NEVER here; it stays private in library_source_texts (tier 1).
--   * library_source_texts — TIER 1: a teacher's PRIVATE copy of the source
--       TEXT (the original file is discarded after a verified-full extraction),
--       app-side encrypted. Readable only by its owner; never joined to a shared
--       path. Only kinds that involve a user-provided copy (book/document) get a
--       row here. This is the "original expression" that may not be redistributed.
--   * library_items        — TIER 3: each teacher's shelf; thin references to the
--       catalog (+ their own notes/tags).
-- Plus library_ingest_jobs to track async extraction (Inngest, serve mode).
-- ===========================================================================

-- TIER 2 — global shared catalog, one row per real-world resource (deduped).
create table if not exists library_extractions (
    id                uuid primary key default gen_random_uuid(),
    kind              text not null check (kind in ('book','video','podcast','article','document')),
    -- Real-world identity: ISBN-13 / 11-char YouTube id / feed URL / canonical
    -- article URL / file SHA-256. Unique per kind → the dedup guarantee.
    dedup_key         text not null,
    -- Intrinsic, factual metadata (safe to share globally).
    title             text,
    creator           text,                                   -- author / channel / show
    cover_url         text,
    source_url        text,
    source_meta       jsonb not null default '{}'::jsonb,     -- publisher/year/isbn/duration/feed/... from search
    -- The transformative derivative (the community resource). Shape varies by
    -- kind and will evolve, so jsonb: e.g. book → {summary, toc, themes,
    -- reading_level, questions}; video → {summary, key_points, chapters, topics}.
    -- Short citations only — never wholesale verbatim source text.
    derivative        jsonb,
    -- Shareable verbatim text, populated ONLY when us_clear is true (US public
    -- domain) or for public video/podcast transcripts. In-copyright book/document
    -- text — including anything acquired by borrowing or the accessibility exception
    -- — is NEVER stored here; it stays private in tier 1 (library_source_texts).
    full_text         text,
    -- transient holding for the fetched source text BETWEEN the fetch step and finalize,
    -- so the multi-MB body never crosses an Inngest step boundary (the quillnext
    -- fullTextRaw pattern). Only ever holds PD / us_clear text; NULLed once extracted.
    full_text_raw     text,
    us_clear          boolean not null default false,   -- clear to redistribute under US copyright (pre-1930)
    grounding         text not null default 'none'
                        check (grounding in ('none','knowledge','source_text')),
    public_domain     boolean not null default false,
    status            text not null default 'pending'
                        check (status in ('pending','extracting','extracted','failed')),
    error             text,
    seeded_by_user_id uuid references users(id) on delete set null,  -- provenance only
    extracted_at      timestamptz,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    unique (kind, dedup_key)
);
create index if not exists library_extractions_status_idx on library_extractions(status);

-- TIER 1 — a teacher's PRIVATE source text (encrypted). Only kinds with a
-- user-provided copy (book/document) populate this. App-side AES-GCM: the key
-- lives in a Fly secret, never in the DB, so a DB dump cannot leak the text.
create table if not exists library_source_texts (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references users(id) on delete cascade,
    extraction_id   uuid not null references library_extractions(id) on delete cascade,
    nonce           bytea not null,                 -- AES-GCM nonce/IV
    ciphertext      bytea not null,                 -- AES-GCM ciphertext (+tag)
    char_count      integer,                        -- plaintext length (cleartext): "full" checks + display
    source_format   text,                           -- epub | pdf | txt | md
    extraction_full boolean not null default false, -- verified complete (else keep original for retry)
    -- How the uploader lawfully obtained the source: a purchased copy, a library
    -- borrow, or an accessibility loan (Chafee Amendment / Marrakesh Treaty — e.g.
    -- Internet Archive's Books for the Print Disabled). 'borrowed'/'accessibility'
    -- are in-copyright by nature → the work's full_text is never shared (see the
    -- us_clear gate on library_extractions); only the transformative derivative is.
    acquisition     text not null default 'owned',   -- owned | borrowed | accessibility (CHECK added below)
    attested        boolean not null default true,   -- attests lawful access for the acquisition type
    attested_at     timestamptz not null default now(),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    unique (user_id, extraction_id)
);

-- TIER 3 — a teacher's shelf: thin references to the shared catalog.
create table if not exists library_items (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references users(id) on delete cascade,
    extraction_id uuid not null references library_extractions(id) on delete cascade,
    notes         text,
    tags          text[] not null default '{}',
    added_at      timestamptz not null default now(),
    unique (user_id, extraction_id)
);
create index if not exists library_items_user_idx on library_items(user_id);

-- Async ingest/extraction jobs (executed by Inngest in serve mode; status kept
-- here for the client poll + retry bookkeeping). One row per upload/trigger.
-- For book/document: r2_object_key points at the transient R2 upload, and the
-- job extracts private text → tier 1, then derives → tier 2 if not already done,
-- then deletes the R2 object. For video/podcast: r2_object_key is null; the job
-- fetches the public transcript/audio, derives → tier 2, and stores the full
-- transcript in library_extractions.full_text (publicly broadcast content).
create table if not exists library_ingest_jobs (
    id             uuid primary key default gen_random_uuid(),
    user_id        uuid not null references users(id) on delete cascade,
    extraction_id  uuid not null references library_extractions(id) on delete cascade,
    r2_object_key  text,
    source_format  text,
    status         text not null default 'uploaded'
                     check (status in ('uploaded','processing','done','failed')),
    attempts       integer not null default 0,
    error          text,
    inngest_run_id text,                             -- correlation for debugging
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists library_ingest_jobs_status_idx on library_ingest_jobs(status);
create index if not exists library_ingest_jobs_user_idx on library_ingest_jobs(user_id);

-- ===========================================================================
-- Living Library — spine alignment & objectives layer (docs/living-library-plan.md
-- §7–§10). Adds book structure (a generic typed tree), alignment of resources/
-- sections to the academic spine, three-tier objectives (community + personal)
-- with wiki-style revision history, a per-teacher hide, and spine-gap proposals.
-- ===========================================================================

-- Book structure as a GENERIC TYPED TREE — no hardcoded division names or depth.
-- A play populates act→scene; a textbook unit→chapter→section; a novel flat
-- chapters or part→chapter. label_type carries the division name as DATA and
-- parent_id gives arbitrary nesting. Populated from the extraction's TOC.
create table if not exists library_sections (
    id            uuid primary key default gen_random_uuid(),
    extraction_id uuid not null references library_extractions(id) on delete cascade,
    parent_id     uuid references library_sections(id) on delete cascade,  -- NULL = top level
    position      integer not null default 0,        -- order among siblings
    label_type    text,                              -- 'act','scene','part','unit','chapter','section',…
    number        text,                              -- 'II', '2', '3.1'
    title         text,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);
create index if not exists library_sections_extraction_idx on library_sections(extraction_id);
create index if not exists library_sections_parent_idx on library_sections(parent_id);

-- Alignment of a resource (optionally one section) to a spine node. Shared /
-- catalog-level (intrinsic to the work); auto-proposed at extraction, teacher-
-- curated via status. section_id NULL = book-level; set = section-level.
create table if not exists library_alignments (
    id            uuid primary key default gen_random_uuid(),
    extraction_id uuid not null references library_extractions(id) on delete cascade,
    section_id    uuid references library_sections(id) on delete cascade,   -- NULL = book-level
    spine_level   text not null check (spine_level in ('subject','sub_subject','topic','sub_topic','objective')),
    spine_node_id text not null,                     -- durable id/code from webapp/standards
    status        text not null default 'proposed' check (status in ('proposed','accepted','rejected')),
    source        text not null default 'auto' check (source in ('auto','teacher')),
    created_by    uuid references users(id) on delete set null,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);
create index if not exists library_alignments_extraction_idx on library_alignments(extraction_id);
create index if not exists library_alignments_node_idx on library_alignments(spine_node_id);  -- reverse: sources for an objective
-- one alignment per (resource[/section], spine node); NULL section needs partial indexes
create unique index if not exists library_alignments_book_uk
    on library_alignments(extraction_id, spine_level, spine_node_id) where section_id is null;
create unique index if not exists library_alignments_section_uk
    on library_alignments(extraction_id, section_id, spine_level, spine_node_id) where section_id is not null;

-- Resource-specific objectives (NOT spine objectives — those live in
-- webapp/standards, reached via library_alignments). Three tiers via nullable
-- user_id: NULL = community (shared, tier 2); set = that teacher's personal
-- (tier 3). GROUNDING-FIRST: a community objective may only enter from a
-- verifiable source — provenance 'seed_oer' (human-authored OER) or
-- 'seed_grounded' (source-text-derived, with `citation`) — never ungrounded
-- model memory; it enters 'proposed' and is promoted to 'accepted' only after the
-- citation-verify pass. Personal objectives (user_id set) are 'personal'/'accepted'
-- on create. The community set is wiki-editable (library_objective_revisions).
create table if not exists library_objectives (
    id            uuid primary key default gen_random_uuid(),
    extraction_id uuid not null references library_extractions(id) on delete cascade,
    user_id       uuid references users(id) on delete cascade,   -- NULL = community; set = personal
    section_id    uuid references library_sections(id) on delete set null,  -- optional grain
    text          text not null,
    citation      text,                              -- the passage the objective rests on (grounded)
    provenance    text not null default 'personal'
                    check (provenance in ('seed_oer','seed_grounded','community_added','promoted_personal','personal')),
    status        text not null default 'accepted'
                    check (status in ('proposed','accepted','rejected')),
    created_by    uuid references users(id) on delete set null,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);
create index if not exists library_objectives_extraction_idx on library_objectives(extraction_id);
create index if not exists library_objectives_scope_idx on library_objectives(extraction_id, user_id);

-- Wiki-style revision history for community objectives. Each edit is a row;
-- library_objectives holds the latest text. Editor kept for attribution.
create table if not exists library_objective_revisions (
    id             uuid primary key default gen_random_uuid(),
    objective_id   uuid not null references library_objectives(id) on delete cascade,
    editor_user_id uuid references users(id) on delete set null,
    text           text not null,
    note           text,
    created_at     timestamptz not null default now()
);
create index if not exists library_objective_revisions_obj_idx on library_objective_revisions(objective_id);

-- A teacher hides a COMMUNITY objective on their own shelf without mutating the
-- shared one (the tier-3 override; separate from wiki editing).
create table if not exists library_hidden_objectives (
    user_id      uuid not null references users(id) on delete cascade,
    objective_id uuid not null references library_objectives(id) on delete cascade,
    created_at   timestamptz not null default now(),
    primary key (user_id, objective_id)
);

-- Spine-gap proposals: when a book won't place cleanly, extraction (or a teacher)
-- proposes a NEW spine node for curator review — the spine grows deliberately,
-- never per-book ad hoc.
create table if not exists library_spine_proposals (
    id             uuid primary key default gen_random_uuid(),
    extraction_id  uuid references library_extractions(id) on delete cascade,  -- which book surfaced it
    proposed_level text not null check (proposed_level in ('subject','sub_subject','topic','sub_topic','objective')),
    parent_node_id text,                             -- spine node it would attach under
    label          text not null,                   -- proposed name/text
    rationale      text,
    status         text not null default 'proposed' check (status in ('proposed','accepted','rejected')),
    created_by     uuid references users(id) on delete set null,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists library_spine_proposals_status_idx on library_spine_proposals(status);

-- Additive columns for already-migrated databases (idempotent; fresh DBs get them
-- from the CREATE statements above).
alter table library_extractions  add column if not exists us_clear      boolean not null default false;
alter table library_extractions  add column if not exists full_text_raw text;
-- Ingestion quality gate + best-copy-wins canonicalization (docs/living-library-plan.md).
-- verify_verdict: null (unchecked) | accepted | rejected | borderline | superseded.
-- canonical_source: which copy produced the live derivative ('gutenberg'/'ccel'/'upload:<uid>').
-- canonical_tier: provenance rank of that copy (trusted PD source 3 > user upload 2).
alter table library_extractions  add column if not exists quality_score   double precision;
alter table library_extractions  add column if not exists verify_verdict  text;
alter table library_extractions  add column if not exists verify_detail   jsonb;
alter table library_extractions  add column if not exists canonical_source text;
alter table library_extractions  add column if not exists canonical_tier  integer;
alter table library_source_texts add column if not exists acquisition   text not null default 'owned';
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'library_source_texts_acquisition_chk') then
    alter table library_source_texts add constraint library_source_texts_acquisition_chk
      check (acquisition in ('owned','borrowed','accessibility'));
  end if;
end $$;

-- Referential integrity from Living Library rows to the spine. Added via ALTER
-- (idempotent) because these tables are defined above spine_nodes; safe on empty
-- tables and validated on future inserts.
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'library_alignments_spine_fk') then
    alter table library_alignments
      add constraint library_alignments_spine_fk
      foreign key (spine_node_id) references spine_nodes(id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname = 'library_spine_proposals_parent_fk') then
    alter table library_spine_proposals
      add constraint library_spine_proposals_parent_fk
      foreign key (parent_node_id) references spine_nodes(id) on delete set null;
  end if;
end $$;
