"""
How long account data is kept (docs/decisions/0013-privacy-and-retention.md).

One place states each period, and /privacy reads it, so the page never claims a purge that isn't
running. The purge of account data is OFF until the maker turns it on with RETENTION_PURGE=on in
the server's secrets, since the periods are his decision. Operational tables (metrics, cap
counters) are purged by webapp/metrics.py whether or not this is on.

When on, it runs at most once a day, from the keep-warm ping (webapp/ops.flag), because Fly stops
idle machines and an in-process timer would never fire.
"""
from __future__ import annotations

import datetime as dt
import logging
import os

import asyncpg

from webapp import account, auth, db, r2

logger = logging.getLogger("study-bible-web.retention")

INACTIVE_MONTHS = 12   # an account with no sign-in for this long is deleted, with everything in it
JOB_DAYS = 30          # finished or failed library jobs (teachers' uploads)
METRICS_DAYS = 90      # webapp/metrics.RETENTION_DAYS, stated here for the privacy page
CAP_DAYS = 2           # daily cap counters (webapp/usage.py)

_last_day: dt.date | None = None


def enabled() -> bool:
    return (os.environ.get("RETENTION_PURGE") or "").strip().lower() in ("1", "on", "true", "yes")


async def run_if_due() -> dict | None:
    """Run the account-data purge once per UTC day, if it is turned on."""
    global _last_day
    today = dt.datetime.now(dt.timezone.utc).date()
    if not enabled() or not db.ready() or _last_day == today:
        return None
    _last_day = today
    return await purge()


async def purge() -> dict:
    """Delete accounts past INACTIVE_MONTHS and library jobs past JOB_DAYS. Current teachers and
    admins are kept: their library shelves are the school's working material."""
    out = {"accounts": 0, "jobs": 0}
    rows = await db.fetch(
        f"""select id, email from users
            where coalesce(last_login_at, created_at) < now() - interval '{INACTIVE_MONTHS} months'""")
    for r in rows:
        user = {"email": r["email"]}
        if auth.is_teacher(user) or auth.is_admin(user):
            continue
        try:
            await account.remove(r["id"], r["email"])
            out["accounts"] += 1
        except Exception:  # noqa: BLE001
            logger.warning("retention: an account could not be deleted", exc_info=True)
    jobs = await db.fetch(
        f"""select id, r2_object_key from library_ingest_jobs
            where status in ('done', 'failed') and updated_at < now() - interval '{JOB_DAYS} days'""")
    for j in jobs:
        if j["r2_object_key"] and r2.configured():
            await r2.delete_async(j["r2_object_key"])   # a failed job can leave its original behind
        await db.execute("delete from library_ingest_jobs where id = $1", j["id"])
        out["jobs"] += 1
    try:
        await db.execute(
            """insert into ops_daily (day, name, value) values (current_date, 'retention_purge', $1)
               on conflict (day, name) do update set value = ops_daily.value + excluded.value""",
            float(out["accounts"] + out["jobs"]))
    except asyncpg.UndefinedTableError:
        pass
    logger.info("retention purge: accounts=%d jobs=%d", out["accounts"], out["jobs"])
    return out
