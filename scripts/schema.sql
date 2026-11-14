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

-- Reading Room cover styles: a reader's light/dark theme, font and motif for the whole library,
-- each shelf and single books. One JSON blob per user; the browser owns its shape.
create table if not exists cover_prefs (
    user_id    uuid primary key references users(id) on delete cascade,
    prefs      jsonb not null default '{"library":{},"shelves":{},"books":{}}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists chat_state (
    user_id    uuid primary key references users(id) on delete cascade,
    state      jsonb not null default '{"chats":[]}'::jsonb,
    updated_at timestamptz not null default now()
);

-- E-reader position: where each signed-in reader left off in each book. book_slug keys into
-- the static reader corpus (books.db on the volume — no Neon FK). One row per (user, book).
create table if not exists reading_state (
    user_id        uuid not null references users(id) on delete cascade,
    book_slug      text not null,
    section_number integer not null default 1,
    pages          integer not null default 1,   -- furthest overall page (folio) reached; gates "Continue Reading" (>= 7)
    updated_at     timestamptz not null default now(),
    primary key (user_id, book_slug)
);
alter table reading_state add column if not exists pages integer not null default 1;

-- Library-admin cover-art overrides for the shared Reading-Room catalog. books.db is
-- read-only (R2 -> volume), so an admin's replacement cover URL lives here and is merged
-- on top of the baked-in cover_url when the catalog is served. Deleting a row reverts a
-- book to its original cover. See webapp/reader.py (catalog / cover_put), auth.is_admin.
create table if not exists cover_overrides (
    book_slug   text primary key,
    cover_url   text not null,      -- source URL the admin supplied (for reference / re-fetch)
    webp        bytea,              -- the downloaded, resized WebP bytes we self-host and serve
    updated_by  text,
    updated_at  timestamptz not null default now()
);
alter table cover_overrides add column if not exists webp bytea;
-- Where the chosen art came from, for attribution and any later rights question:
-- e.g. source = "Galaxy Science Fiction, July 1958 (Galactic Central)", source_page = its page.
alter table cover_overrides add column if not exists source text;
alter table cover_overrides add column if not exists source_page text;

-- ===========================================================================
-- Academic spine (canonical store). Source of truth for the Generator's K–12
-- scope-and-sequence (Subject → Sub-subject → Topic → Sub-topic → Objective),
-- housed in Postgres so Living Library alignments get referential integrity and
-- the spine can be curated/grown in place (proposals → active). The JSON in
-- webapp/standards/ + the .npy embeddings are a GENERATED READ-CACHE, regenerated
-- from this table (the perf-sensitive in-memory search still loads them). See
-- docs/sources/living-library-plan.md §7. Seeded by scripts/seed_spine.py from the JSON.
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
-- docs/sources/living-library-plan.md):
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
    -- This copy's mechanical quality score + its standing in canonical selection.
    -- review_status: none | pending (same-tier borderline, awaiting a human) |
    -- promoted (won canonical) | rejected (reviewer declined; stays private).
    quality_score   double precision,
    review_status   text not null default 'none',
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
    cover_url     text,   -- per-shelf cover override; falls back to the catalog cover when null
    added_at      timestamptz not null default now(),
    unique (user_id, extraction_id)
);
alter table library_items add column if not exists cover_url text;
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
-- Living Library — spine alignment & objectives layer (docs/sources/living-library-plan.md
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

-- Living Library generation redesign (Phase 3, 2026-09-17): the per-book OBJECTIVES and
-- SPINE-ALIGNMENT layer is retired — generation now reads book text live plus a whole-work
-- comprehension layer (library_comprehension). No live code writes or reads these tables, so
-- they are dropped. (The academic spine itself — spine_nodes / webapp/standards — stays.)
drop table if exists library_objective_revisions cascade;
drop table if exists library_hidden_objectives   cascade;
drop table if exists library_objectives           cascade;
drop table if exists library_alignments           cascade;
drop table if exists library_spine_proposals      cascade;

-- Additive columns for already-migrated databases (idempotent; fresh DBs get them
-- from the CREATE statements above).
alter table library_extractions  add column if not exists us_clear      boolean not null default false;
alter table library_extractions  add column if not exists full_text_raw text;
-- Ingestion quality gate + best-copy-wins canonicalization (docs/sources/living-library-plan.md).
-- verify_verdict: null (unchecked) | accepted | rejected | borderline | superseded.
-- canonical_source: which copy produced the live derivative ('gutenberg'/'ccel'/'upload:<uid>').
-- canonical_tier: provenance rank of that copy (trusted PD source 3 > user upload 2).
alter table library_extractions  add column if not exists quality_score   double precision;
alter table library_extractions  add column if not exists verify_verdict  text;
alter table library_extractions  add column if not exists verify_detail   jsonb;
alter table library_extractions  add column if not exists canonical_source text;
alter table library_extractions  add column if not exists canonical_tier  integer;
-- Published table of contents (ordered entry titles) from an EPUB nav / PDF outline /
-- embedded 'Contents' — used to upgrade terse section labels to descriptive titles.
alter table library_extractions  add column if not exists toc            jsonb;
alter table library_source_texts add column if not exists acquisition   text not null default 'owned';
alter table library_source_texts add column if not exists quality_score double precision;
alter table library_source_texts add column if not exists review_status text not null default 'none';
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'library_source_texts_acquisition_chk') then
    alter table library_source_texts add constraint library_source_texts_acquisition_chk
      check (acquisition in ('owned','borrowed','accessibility'));
  end if;
end $$;


-- ===========================================================================
-- Living Library — generation redesign (docs/sources/living-library-generation-plan.md).
-- Whole-work COMPREHENSION layer for LARGE works only (small books are read whole at
-- generation time). Built lazily on first generation against a big book and cached here;
-- rebuilt only when the source text changes (word_count guard) or on manual request.
-- Keyed by book identity: a books.db slug (PD) or 'upload:<extraction_id>'.
-- ===========================================================================
create table if not exists library_comprehension (
    book_key     text primary key,          -- books.db slug, or 'upload:<extraction_id>'
    title        text,
    summary      text,                       -- one-paragraph whole-work summary
    arc          jsonb,                       -- [{title, span, what_happens}] major movements
    themes       jsonb,                       -- [{name, arc}] introduced → developed → paid off
    significance jsonb,                       -- [{element, why_matters}] load-bearing elements
    recap        jsonb,                       -- [{through_section, so_far}] cumulative, bounded per point
    model        text,
    word_count   integer,                     -- invalidation guard (rebuild if the text changed)
    built_at     timestamptz not null default now()
);


-- ===========================================================================
-- Harness Phase 3-4 (docs/harness-maturity-proposal.md, docs/decisions/0011-0013).
-- The app runs without these tables (metrics and caps stay off until they exist).
-- ===========================================================================

-- One row per model run: numbers and fixed labels only (webapp/metrics.py). No text, no
-- account, no session, no IP. The time is cut to the hour. Deleted after 90 days.
create table if not exists turn_metrics (
    hour             timestamptz not null,
    route            text not null,
    key_source       text not null,
    model_req        text,
    model_served     text,
    prefix_hash      text,
    outcome          text not null,
    http_status      integer,
    refusal_category text,
    steps            integer,
    tool_errors      integer,
    input            integer,
    cache_read       integer,
    cache_write      integer,
    output           integer,
    first_read       integer,
    first_write      integer,
    est_usd          double precision not null default 0,
    duration_ms      integer,
    checks_dropped   integer,
    checks_stopped   integer
);
create index if not exists turn_metrics_hour_idx on turn_metrics(hour);

-- Daily operational counters and flags (the spend alert's once-a-day mark). Deleted after 90 days.
create table if not exists ops_daily (
    day   date not null,
    name  text not null,
    value double precision not null default 0,
    primary key (day, name)
);

-- Daily chat caps (webapp/usage.py). `who` is a keyed hash of account id and date, or 'school'
-- for all students together, so rows join to nothing. Deleted after two days.
create table if not exists usage_daily (
    day     date not null,
    who     text not null,
    turns   integer not null default 0,
    est_usd double precision not null default 0,
    primary key (day, who)
);

-- QSF DAT-07: the Google profile photo is no longer stored. Nulling (instead of dropping the
-- column) keeps sign-in working if this runs before the code that stops writing it is deployed.
update users set picture = null where picture is not null;


-- ===========================================================================
-- The Prep Room (docs/decisions/0026-prep-room-units.md, webapp/prep.py). A teacher's units, the
-- sources each draws on, and every resource made in one with its versions. Private to the teacher
-- who made them; the maker can read them, as /privacy says. They go with the account.
-- ===========================================================================
create table if not exists prep_units (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    title       text not null,
    course_key  text,                                   -- a Yorkville course (webapp/data/yorkville.json)
    grade_band  text not null default 'secondary',
    notes       text not null default '',               -- what every draft in the unit should know
    objectives  jsonb not null default '[]'::jsonb,     -- picked spine objectives, anchors included
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index if not exists prep_units_user_idx on prep_units(user_id, updated_at desc);

-- A teacher's course (decision 0032) is a tree of these rows: the course, its units, their lessons.
-- A Prep Room unit made outside a course keeps kind 'unit' with no parent, exactly as before.
alter table prep_units add column if not exists parent_id uuid references prep_units(id) on delete cascade;
alter table prep_units add column if not exists kind      text not null default 'unit';   -- course | unit | lesson | group
alter table prep_units add column if not exists position  integer not null default 0;     -- order among siblings
alter table prep_units add column if not exists passage   text;                           -- 'John 6:25-29'
alter table prep_units add column if not exists calendar  text;                           -- a course's school calendar
alter table prep_units add column if not exists meetings  integer;                        -- a unit's class meetings
alter table prep_units add column if not exists day_type  text;                           -- a lesson's: regular | thursday | half_day
alter table prep_units add column if not exists plan      jsonb not null default '{}'::jsonb;  -- a lesson's moves, questions, materials
alter table prep_units add column if not exists taught_on date;                           -- the day a lesson was marked taught
alter table prep_units add column if not exists hidden    jsonb not null default '[]'::jsonb;  -- shelf items removed from here
create index if not exists prep_units_parent_idx on prep_units(parent_id, position);

-- What a unit draws on. `ref` holds only what its kind needs (webapp/prep.clean_ref). An upload's or
-- a link's text is the teacher's own copy, kept encrypted (AES-GCM, LIBRARY_ENC_KEY).
create table if not exists prep_sources (
    id          uuid primary key default gen_random_uuid(),
    unit_id     uuid not null references prep_units(id) on delete cascade,
    kind        text not null check (kind in ('book','outline','passage','library','upload','link')),
    ref         jsonb not null,
    label       text not null,
    words       integer,
    position    integer not null default 0,
    text_nonce  bytea,
    text_ct     bytea,
    added_at    timestamptz not null default now()
);
create index if not exists prep_sources_unit_idx on prep_sources(unit_id, position);

-- A resource made in the Prep Room. unit_id is null for a quick resource made outside a unit.
create table if not exists prep_resources (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    unit_id     uuid references prep_units(id) on delete cascade,
    format_id   text not null,
    title       text not null,
    settings    jsonb not null default '{}'::jsonb,     -- variant, item types, length, grade band, brief
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index if not exists prep_resources_user_idx on prep_resources(user_id, updated_at desc);
create index if not exists prep_resources_unit_idx on prep_resources(unit_id);

-- Every draft, revision, hand edit and restore, newest kept to 40 per resource.
create table if not exists prep_versions (
    resource_id uuid not null references prep_resources(id) on delete cascade,
    n           integer not null,
    origin      text not null check (origin in ('draft','revise','edit','restore')),
    instruction text,
    document    text not null,
    drew_on     jsonb not null default '[]'::jsonb,     -- the sources this run was given
    report      jsonb,                                  -- the source check (webapp/citations.py)
    created_at  timestamptz not null default now(),
    primary key (resource_id, n)
);

-- Which Yorkville courses a teacher teaches, so their Living Library opens on those courses' books.
-- Keyed by the account's address (a teacher may not have signed in yet). 'school' rows come from the
-- school's book list (scripts/seed_teacher_courses.py reads it on the maker's machine; no name is
-- stored anywhere); 'teacher' rows are the teacher's own picks; 'removed' marks a school row the
-- teacher took off, so a later seed doesn't put it back. Deleted with the account.
create table if not exists teacher_courses (
    email       text not null,
    course_key  text not null,
    source      text not null default 'school' check (source in ('school','teacher','removed')),
    added_at    timestamptz not null default now(),
    primary key (email, course_key)
);

-- Transcripts of public videos and podcast episodes (webapp/transcripts.py), shared by everyone who adds
-- the item: published broadcast text only, never a private copy. key: 'yt:<video id>' or 'ep:<extraction id>:<guid>'.
create table if not exists library_transcripts (
    key         text primary key,
    title       text,
    segments    jsonb not null,               -- [{start, end, text, speaker}] in seconds
    source      text not null,                -- 'application/json', 'text/vtt', 'youtube captions', ...
    fetched_at  timestamptz not null default now()
);

-- A teacher's saved moments in a video or episode (decision 0026): a time range, the words spoken there when
-- a transcript exists (or the teacher's own), and a note. Private to the teacher; deleted with the account.
create table if not exists library_excerpts (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references users(id) on delete cascade,
    extraction_id uuid not null references library_extractions(id) on delete cascade,
    episode_key   text,                       -- a podcast episode's guid; null for a video
    episode_title text,
    start_s       real not null,
    end_s         real not null,
    quote         text,
    note          text,
    created_at    timestamptz not null default now()
);
create index if not exists library_excerpts_user_idx on library_excerpts(user_id, extraction_id);

-- A transcription Gemini is writing, or the reason the last one failed (decision 0028). One row per transcript
-- key while it runs; removed when the transcript is stored. No account is kept here.
create table if not exists library_transcribe_jobs (
    key         text primary key,
    status      text not null check (status in ('running','failed')),
    error       text,
    updated_at  timestamptz not null default now()
);

-- What is on a shelf in the Living Library (decision 0029). A row belongs to one person (user_id) or to one
-- course's class shelf (course_key), never both. Phase 1 holds the Reading Room books a person shelves; uploads,
-- links, videos, podcasts and Prep Room resources, and class shelves with their audience, come in later phases.
create table if not exists shelf_items (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid references users(id) on delete cascade,
    course_key  text,
    audience    text check (audience in ('students','teachers')),
    kind        text not null check (kind in ('book','upload','link','video','podcast','resource')),
    ref         jsonb not null,
    label       text,
    added_by    uuid references users(id) on delete set null,
    added_at    timestamptz not null default now(),
    check ((user_id is null) <> (course_key is null))
);
create unique index if not exists shelf_items_user_book on shelf_items (user_id, (ref->>'slug'))
    where kind = 'book' and user_id is not null;
create index if not exists shelf_items_course_idx on shelf_items(course_key) where course_key is not null;

-- The classes a student says they take (decision 0029), so their class shelves come first. The student's own
-- setting: chosen and changed by them, never put in a prompt (0002), deleted with the account.
create table if not exists student_courses (
    user_id     uuid not null references users(id) on delete cascade,
    course_key  text not null,
    added_at    timestamptz not null default now(),
    primary key (user_id, course_key)
);

-- The text of an upload or a saved link on a shelf (decision 0029, phase 3), kept encrypted like a Prep Room upload.
-- One row per shelf item: a class shelf's copy has its own, so a handout outlives the teacher's own copy.
create table if not exists shelf_texts (
    item_id     uuid primary key references shelf_items(id) on delete cascade,
    nonce       bytea not null,
    ct          bytea not null,
    words       integer not null default 0
);

-- A teacher's suggestion that a public-domain or openly licensed book they uploaded join the Reading Room
-- (decision 0029). The maker approves or declines it at /ops, then adds an approved book to the catalog by hand.
create table if not exists catalog_suggestions (
    id          uuid primary key default gen_random_uuid(),
    item_id     uuid references shelf_items(id) on delete set null,
    user_id     uuid references users(id) on delete set null,
    title       text not null,
    author      text,
    basis       text not null,
    status      text not null default 'pending' check (status in ('pending','approved','declined')),
    created_at  timestamptz not null default now(),
    decided_at  timestamptz
);
