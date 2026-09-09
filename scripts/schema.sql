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

-- Scripture Memory: mirrors the current localStorage shape, keyed to a user.
create table if not exists memory_folders (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references users(id) on delete cascade,
    name       text not null,
    created_at timestamptz not null default now()
);

create table if not exists memory_verses (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references users(id) on delete cascade,
    folder_id         uuid references memory_folders(id) on delete set null,
    reference         text not null,
    text              text,
    current_step      int not null default 0,
    mastered_at       timestamptz,
    last_practiced_at timestamptz,
    last_refreshed_at timestamptz,
    created_at        timestamptz not null default now()
);
create index if not exists idx_memory_verses_user  on memory_verses(user_id);
create index if not exists idx_memory_folders_user on memory_folders(user_id);

-- Saved chats. The whole transcript lives in `messages` (jsonb); resending it is
-- how the model keeps context, so this is all that continuation needs.
create table if not exists chats (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references users(id) on delete cascade,
    title      text,
    persona    text,
    messages   jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_chats_user on chats(user_id);
