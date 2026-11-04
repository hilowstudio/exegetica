"""
Operational metrics (docs/harness-maturity-proposal.md, Layer 7; docs/decisions/0012-metrics.md).

One row per model run in `turn_metrics`, holding numbers and fixed labels only. Never recorded:
message text or its hash, tool inputs or outputs, provider error strings, persona, IP, browser,
session, email, account id, or key. The time is cut to the hour, and there is no column that could
join a row to a person. Rows older than RETENTION_DAYS are deleted on the write path, so the purge
runs whenever the app is in use.

Writes never block or fail a reply: each one runs as its own task, and a failure is counted in
memory for /ops. Until the tables exist (scripts/schema.sql) every write and read is a no-op.
"""
from __future__ import annotations

import asyncio
import logging
import time

import asyncpg

from webapp import db

logger = logging.getLogger("study-bible-web.metrics")

RETENTION_DAYS = 90

ROUTES = {"chat:bible", "chat:history", "generate", "generate:book", "revise", "studio", "studio:video"}
KEY_SOURCES = {"server", "byok"}
OUTCOMES = {
    # how a model run ended (providers.OUTCOMES)
    "complete", "cut_off", "step_limit", "budget", "tools_failed", "refused", "provider_error", "cancelled",
    # endings decided in the app
    "check_stop",     # the reply check stopped the reply (webapp/reply_check.py)
    "greeting",       # a bare greeting got the fixed reply, no model call
    "drift",          # a long tool-free study got the fixed reply, no model call
    "capped",         # a daily cap was reached, no model call
    "limited",        # too many turns in a minute, or the server was full, no model call
}
LABELS = {"route": ROUTES, "key_source": KEY_SOURCES, "outcome": OUTCOMES}
MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-sonnet-5", "claude-haiku-5-5", "claude-sonnet-4-6"}
NUMBERS = ("http_status", "steps", "tool_errors", "input", "cache_read", "cache_write", "output",
           "first_read", "first_write", "duration_ms", "checks_dropped", "checks_stopped")
FIELDS = ("route", "key_source", "model_req", "model_served", "prefix_hash", "outcome",
          "refusal_category", "est_usd") + NUMBERS

# In-memory health for /ops: since this process started.
failed_writes = 0
missing_tables: set[str] = set()
_tasks: set[asyncio.Task] = set()
_last_purge = 0.0


def row(**fields) -> dict:
    """Validate one metrics row against the allowlist. Unknown fields raise; labels must be from
    their fixed sets; models outside the known list become 'other'; numbers are coerced."""
    unknown = set(fields) - set(FIELDS)
    if unknown:
        raise ValueError(f"not a metrics field: {sorted(unknown)}")
    out: dict = {}
    for name, allowed in LABELS.items():
        value = fields.get(name)
        if value not in allowed:
            raise ValueError(f"{name} must be one of the fixed labels")
        out[name] = value
    for name in ("model_req", "model_served"):
        value = fields.get(name)
        out[name] = None if value is None else value if value in MODELS else "other"
    prefix = fields.get("prefix_hash")
    out["prefix_hash"] = prefix if isinstance(prefix, str) and len(prefix) == 12 and prefix.isalnum() else None
    cat = fields.get("refusal_category")
    out["refusal_category"] = cat if isinstance(cat, str) and cat.replace("_", "").isalpha() and len(cat) <= 40 else None
    for name in NUMBERS:
        value = fields.get(name)
        out[name] = None if value is None else int(value)
    out["est_usd"] = round(float(fields.get("est_usd") or 0.0), 6)
    return out


def from_stats(route: str, key_source: str, stats: dict, **extra) -> dict:
    """A row from the stats dict providers.run fills, plus app-side fields."""
    picked = {k: stats.get(k) for k in FIELDS if k in stats}
    picked.update(extra)
    return row(route=route, key_source=key_source, **picked)


def record(r: dict) -> None:
    """Write a validated row in the background. Safe to call from a `finally` after cancellation."""
    try:
        task = asyncio.get_running_loop().create_task(_write(r))
    except RuntimeError:   # no running loop (tests, shutdown)
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _write(r: dict) -> None:
    global failed_writes
    if not db.ready() or "turn_metrics" in missing_tables:
        return
    cols = list(r)
    sql = (f"insert into turn_metrics (hour, {', '.join(cols)}) values (date_trunc('hour', now()), "
           + ", ".join(f"${i + 1}" for i in range(len(cols))) + ")")
    try:
        await db.execute(sql, *r.values())
    except asyncpg.UndefinedTableError:
        missing_tables.add("turn_metrics")
        logger.warning("turn_metrics table missing; apply scripts/schema.sql to record metrics")
        return
    except Exception:  # noqa: BLE001
        failed_writes += 1
        logger.warning("metrics write failed", exc_info=True)
        return
    await purge_if_due()


async def purge_if_due() -> None:
    """Delete expired operational rows, at most once an hour per process."""
    global _last_purge
    now = time.monotonic()
    if _last_purge and now - _last_purge < 3600:
        return
    _last_purge = now
    await purge()


async def purge() -> dict:
    """Delete metrics past RETENTION_DAYS and spent cap counters. Returns rows deleted per table."""
    deleted = {}
    if not db.ready():
        return deleted
    for table, sql in (
        ("turn_metrics", f"delete from turn_metrics where hour < now() - interval '{RETENTION_DAYS} days'"),
        ("ops_daily", f"delete from ops_daily where day < current_date - {RETENTION_DAYS}"),
        ("usage_daily", "delete from usage_daily where day < current_date - 2"),
    ):
        if table in missing_tables:
            continue
        try:
            status = await db.execute(sql)
            deleted[table] = int(status.split()[-1]) if status.startswith("DELETE") else 0
        except asyncpg.UndefinedTableError:
            missing_tables.add(table)
        except Exception:  # noqa: BLE001
            logger.warning("purge of %s failed", table, exc_info=True)
    return deleted


async def daily_summary(days: int = 14) -> list[dict] | None:
    """Per UTC day: runs, estimated spend, and counts by ending. None if the table is missing."""
    if not db.ready() or "turn_metrics" in missing_tables:
        return None
    try:
        rows = await db.fetch(
            """select (hour at time zone 'UTC')::date as day,
                      count(*) as runs,
                      coalesce(sum(est_usd), 0) as usd,
                      count(*) filter (where outcome = 'complete') as complete,
                      count(*) filter (where outcome = 'refused') as refused,
                      count(*) filter (where outcome in ('provider_error', 'tools_failed')) as failed,
                      count(*) filter (where outcome in ('cut_off', 'step_limit', 'budget')) as truncated,
                      count(*) filter (where outcome = 'cancelled') as cancelled,
                      count(*) filter (where outcome in ('capped', 'limited')) as capped,
                      count(*) filter (where outcome in ('greeting', 'drift')) as fixed,
                      coalesce(sum(checks_dropped), 0) as dropped,
                      count(*) filter (where outcome = 'check_stop') as stopped,
                      coalesce(sum(tool_errors), 0) as tool_errors
               from turn_metrics
               where hour >= date_trunc('day', now() at time zone 'UTC') at time zone 'UTC' - make_interval(days => $1)
               group by 1 order by 1 desc""", days - 1)
    except asyncpg.UndefinedTableError:
        missing_tables.add("turn_metrics")
        return None
    return [dict(r) for r in rows]


async def last_row_at():
    if not db.ready() or "turn_metrics" in missing_tables:
        return None
    try:
        return await db.fetchval("select max(hour) from turn_metrics")
    except asyncpg.UndefinedTableError:
        missing_tables.add("turn_metrics")
        return None


async def spend_on(day) -> float | None:
    """Estimated dollars for one UTC day, or None if unknown."""
    if not db.ready() or "turn_metrics" in missing_tables:
        return None
    try:
        return float(await db.fetchval(
            "select coalesce(sum(est_usd), 0) from turn_metrics where (hour at time zone 'UTC')::date = $1", day))
    except asyncpg.UndefinedTableError:
        missing_tables.add("turn_metrics")
        return None
