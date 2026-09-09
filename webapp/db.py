"""
Postgres (Neon) access layer.

A thin async wrapper over an asyncpg connection pool. The pool is OPTIONAL: if
DATABASE_URL is unset (or the database is unreachable), init_pool() leaves the
pool as None and the app runs exactly as before — DB-backed features simply stay
off. This lets us land the data layer without breaking the running app while the
rest of the storage migration is built out in stages.

The connection string comes from DATABASE_URL (a Neon *pooled* URL). Neon's URL
carries libpq params asyncpg does not understand (sslmode, channel_binding), so
we strip them and pass a real TLS context instead — Neon presents a valid public
CA cert, so default verification works.
"""
from __future__ import annotations

import json
import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Round-trip json/jsonb columns as Python objects, not raw strings."""
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


def dsn() -> str | None:
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url else None


def _clean_dsn(url: str) -> str:
    """Drop query params asyncpg can't parse (sslmode/channel_binding); TLS is
    supplied separately via the ssl context."""
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("sslmode", "channel_binding")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


async def init_pool() -> asyncpg.Pool | None:
    """Create the pool from DATABASE_URL. Returns None if no URL is set. Raises on
    a real connection failure — callers (the lifespan) decide whether to degrade."""
    global _pool
    url = dsn()
    if not url:
        return None
    ctx = ssl.create_default_context()
    _pool = await asyncpg.create_pool(
        _clean_dsn(url), ssl=ctx, min_size=1, max_size=5, command_timeout=30, init=_init_conn,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool | None:
    return _pool


def ready() -> bool:
    return _pool is not None


# ---- convenience query helpers (raise if the pool is not initialized) ----
async def fetch(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args) -> str:
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)


async def apply_schema(sql: str) -> None:
    """Run a (multi-statement) schema script inside one transaction."""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(sql)
