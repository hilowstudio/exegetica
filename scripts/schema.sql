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
