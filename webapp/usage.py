"""
Daily caps and rate limits on chat (docs/decisions/0011-fixed-replies-and-caps.md).

Caps count turns and estimated dollars per account per school day (America/Chicago) in
`usage_daily`. A row's key is a keyed hash of the account id and the date, so a row cannot be
joined to an account, to another day, or to `turn_metrics`, and rows are deleted after two days
(webapp/metrics.purge). Students' spend also adds to one shared row, the school-wide cap.
Teachers have a turn cap and stay outside the school-wide total.

Rate limits are per account and held in memory only: identity, never IP, since the whole school
shares one address. Until the table exists, or if the database is down, caps fail open and the
Anthropic Console spend limit remains the stop.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import hmac
import logging
import os
import secrets
import time

import asyncpg

from webapp import curriculum, db, metrics

logger = logging.getLogger("study-bible-web.usage")

STUDENT_TURNS = 30
STUDENT_USD = 1.50
TEACHER_TURNS = 300
SCHOOL_USD = 8.00          # all students together, per school day
PER_MINUTE = 6             # turns per account per rolling minute
MAX_STREAMS = 12           # model streams at once, whole server

CAPPED = "This account has reached today's chat limit. Chat opens again tomorrow."
SCHOOL_CAPPED = "Exegetica has reached today's chat limit for the school. Chat opens again tomorrow."
TOO_FAST = "That's too many messages in one minute. Wait a moment and send it again."
BUSY = "Exegetica is busy. Try again in a minute."

# The Prep Room (decision 0027): drafts and changes, per teacher and for all teachers together, per school day.
PREP_RUNS = 25
PREP_USD = 10.00
PREP_ALL_USD = 40.00
PREP_CAPPED = "You've reached today's Prep Room limit. It opens again tomorrow, and everything you've made is saved."
PREP_ALL_CAPPED = ("The Prep Room has reached today's limit for the school. It opens again tomorrow, and everything "
                   "you've made is saved.")
PREP_ALL = "prep"
# Transcripts Gemini writes for the Living Library (decision 0028), per teacher and for everyone, per school day.
TRANSCRIBE_RUNS = 10
TRANSCRIBE_ALL_USD = 5.00
TRANSCRIBE_CAPPED = "You've made today's limit of transcripts. You can make more tomorrow."
TRANSCRIBE_ALL_CAPPED = "Exegetica has made today's limit of transcripts for the school. More can be made tomorrow."
TRANSCRIBE_ALL = "transcribe"

SCHOOL = "school"
_KEY = (os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)).encode()

_recent: dict[str, collections.deque] = {}
_streams = 0


def today() -> dt.date:
    """The school day, in Chicago time (works without a tz database, as on Windows)."""
    return curriculum._chicago_today()


def who(user_id: str, day: dt.date) -> str:
    """The counter key for one account on one day. Unlinkable without the server's secret."""
    return hmac.new(_KEY, f"{day.isoformat()}:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


# ---------------------------------------------------------------- rate limits (memory)
def admit(user_id: str) -> str | None:
    """None if this account may start a turn now, else the fixed text to show."""
    now = time.monotonic()
    q = _recent.setdefault(user_id, collections.deque())
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= PER_MINUTE:
        return TOO_FAST
    if _streams >= MAX_STREAMS:
        return BUSY
    q.append(now)
    if len(_recent) > 2000:   # drop idle accounts so the map stays small
        for k in [k for k, v in _recent.items() if not v or now - v[-1] > 60]:
            _recent.pop(k, None)
    return None


def stream_opened() -> None:
    global _streams
    _streams += 1


def stream_closed() -> None:
    global _streams
    _streams = max(0, _streams - 1)


# ---------------------------------------------------------------- daily caps (Neon)
async def check(user_id: str, teacher: bool) -> str | None:
    """None if under every cap, else the fixed text to show. Fails open."""
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return None
    day = today()
    mine = who(user_id, day)
    try:
        rows = await db.fetch("select who, turns, est_usd from usage_daily where day = $1 and who = any($2)",
                              day, [mine, SCHOOL])
    except asyncpg.UndefinedTableError:
        metrics.missing_tables.add("usage_daily")
        logger.warning("usage_daily table missing; daily caps are off until scripts/schema.sql is applied")
        return None
    except Exception:  # noqa: BLE001
        logger.warning("cap check failed; allowing the turn", exc_info=True)
        return None
    seen = {r["who"]: r for r in rows}
    me, school = seen.get(mine), seen.get(SCHOOL)
    if teacher:
        return CAPPED if me and me["turns"] >= TEACHER_TURNS else None
    if school and float(school["est_usd"]) >= SCHOOL_USD:
        return SCHOOL_CAPPED
    if me and (me["turns"] >= STUDENT_TURNS or float(me["est_usd"]) >= STUDENT_USD):
        return CAPPED
    return None


async def add(user_id: str, teacher: bool, usd: float) -> None:
    """Count one model turn and its estimated cost."""
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return
    day = today()
    keys = [who(user_id, day)] + ([] if teacher else [SCHOOL])
    try:
        for key in keys:
            await db.execute(
                """insert into usage_daily (day, who, turns, est_usd) values ($1, $2, 1, $3)
                   on conflict (day, who) do update
                     set turns = usage_daily.turns + 1, est_usd = usage_daily.est_usd + excluded.est_usd""",
                day, key, usd)
    except asyncpg.UndefinedTableError:
        metrics.missing_tables.add("usage_daily")
    except Exception:  # noqa: BLE001
        logger.warning("cap counter write failed", exc_info=True)


# ---------------------------------------------------------------- Prep Room caps (Neon, decision 0027)
def _prep_key(user_id: str, day: dt.date) -> str:
    return who(f"prep:{user_id}", day)   # apart from the same teacher's chat turns


async def prep_check(user_id: str) -> str | None:
    """None if this teacher may start a Prep Room run, else the fixed text to show. Fails open, like chat's."""
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return None
    day = today()
    mine = _prep_key(user_id, day)
    try:
        rows = await db.fetch("select who, turns, est_usd from usage_daily where day = $1 and who = any($2)",
                              day, [mine, PREP_ALL])
    except asyncpg.UndefinedTableError:
        metrics.missing_tables.add("usage_daily")
        return None
    except Exception:  # noqa: BLE001
        logger.warning("Prep Room cap check failed; allowing the run", exc_info=True)
        return None
    seen = {r["who"]: r for r in rows}
    me, everyone = seen.get(mine), seen.get(PREP_ALL)
    if everyone and float(everyone["est_usd"]) >= PREP_ALL_USD:
        return PREP_ALL_CAPPED
    if me and (me["turns"] >= PREP_RUNS or float(me["est_usd"]) >= PREP_USD):
        return PREP_CAPPED
    return None


async def prep_add(user_id: str, usd: float) -> None:
    """Count one Prep Room run, finished or not, and its estimated cost."""
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return
    day = today()
    try:
        for key in (_prep_key(user_id, day), PREP_ALL):
            await db.execute(
                """insert into usage_daily (day, who, turns, est_usd) values ($1, $2, 1, $3)
                   on conflict (day, who) do update
                     set turns = usage_daily.turns + 1, est_usd = usage_daily.est_usd + excluded.est_usd""",
                day, key, usd)
    except asyncpg.UndefinedTableError:
        metrics.missing_tables.add("usage_daily")
    except Exception:  # noqa: BLE001
        logger.warning("Prep Room counter write failed", exc_info=True)


# ---------------------------------------------------------------- transcription caps (Neon, decision 0028)
def _tx_key(user_id: str, day: dt.date) -> str:
    return who(f"tx:{user_id}", day)


async def transcribe_check(user_id: str) -> str | None:
    """None if this teacher may ask for a transcript now, else the fixed text to show. Fails open."""
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return None
    day = today()
    mine = _tx_key(user_id, day)
    try:
        rows = await db.fetch("select who, turns, est_usd from usage_daily where day = $1 and who = any($2)",
                              day, [mine, TRANSCRIBE_ALL])
    except Exception:  # noqa: BLE001
        logger.warning("transcription cap check failed; allowing it", exc_info=True)
        return None
    seen = {r["who"]: r for r in rows}
    if seen.get(TRANSCRIBE_ALL) and float(seen[TRANSCRIBE_ALL]["est_usd"]) >= TRANSCRIBE_ALL_USD:
        return TRANSCRIBE_ALL_CAPPED
    if seen.get(mine) and seen[mine]["turns"] >= TRANSCRIBE_RUNS:
        return TRANSCRIBE_CAPPED
    return None


async def transcribe_add(user_id: str, usd: float) -> None:
    if not db.ready() or "usage_daily" in metrics.missing_tables:
        return
    day = today()
    try:
        for key in (_tx_key(user_id, day), TRANSCRIBE_ALL):
            await db.execute(
                """insert into usage_daily (day, who, turns, est_usd) values ($1, $2, 1, $3)
                   on conflict (day, who) do update
                     set turns = usage_daily.turns + 1, est_usd = usage_daily.est_usd + excluded.est_usd""",
                day, key, usd)
    except Exception:  # noqa: BLE001
        logger.warning("transcription counter write failed", exc_info=True)
