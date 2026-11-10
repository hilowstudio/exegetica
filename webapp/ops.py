"""
/ops, the maker's operations page, and /ops/flag, the once-a-day spend alert
(docs/harness-maturity-proposal.md, Layer 7; docs/decisions/0012-metrics.md).

/ops is admin-only and reads webapp/metrics.py: 14 UTC days of runs, estimated spend, how runs
ended, and how often the help window opened, plus the libraries' health. It shows counts only,
never a person or a message.

/ops/flag is for the keep-warm workflow. It answers 500 the first time in a UTC day that the
estimated spend for that day (or the day before) passes ALERT_USD, so the scheduled GitHub run
fails and GitHub emails the maker. Every other call answers 200. It needs the OPS_FLAG_TOKEN
secret in an X-Ops-Token header, and is a 404 when the secret isn't set. The same ping runs the
hourly metrics purge and, if turned on, the daily retention purge.
"""
from __future__ import annotations

import datetime as dt
import hmac
import html
import logging
import os

import asyncpg
from starlette.responses import PlainTextResponse

from webapp import about, auth, db, metrics, retention, shell, usage

logger = logging.getLogger("study-bible-web.ops")

ALERT_USD = 5.0
_alerted: set[dt.date] = set()   # used only while ops_daily is missing


async def _first_alert(day: dt.date, spent: float) -> bool:
    """Record the alert for `day`; True only the first time."""
    try:
        row = await db.fetchrow(
            """insert into ops_daily (day, name, value) values ($1, 'spend_alert', $2)
               on conflict (day, name) do nothing returning day""", day, spent)
        return row is not None
    except asyncpg.UndefinedTableError:
        if day in _alerted:
            return False
        _alerted.add(day)
        return True


async def flag(request):
    token = os.environ.get("OPS_FLAG_TOKEN") or ""
    if not token:
        return PlainTextResponse("Not Found", status_code=404)
    if not hmac.compare_digest(request.headers.get("x-ops-token", ""), token):
        return PlainTextResponse("Not Found", status_code=404)
    await metrics.purge_if_due()
    try:
        await retention.run_if_due()
    except Exception:  # noqa: BLE001
        logger.warning("retention purge failed", exc_info=True)
    today = dt.datetime.now(dt.timezone.utc).date()
    for day in (today - dt.timedelta(days=1), today):
        spent = await metrics.spend_on(day)
        if spent is not None and spent > ALERT_USD and await _first_alert(day, spent):
            logger.warning("spend alert: %s estimated $%.2f", day, spent)
            return PlainTextResponse(f"Estimated spend on {day} is ${spent:.2f}, over ${ALERT_USD:.0f}. "
                                     "See /ops.", status_code=500)
    return PlainTextResponse("ok", headers={"Cache-Control": "no-store"})


async def _table_state() -> dict[str, str]:
    out = {}
    for table in ("turn_metrics", "usage_daily", "ops_daily"):
        if not db.ready():
            out[table] = "no database"
            continue
        try:
            await db.fetchval(f"select 1 from {table} limit 1")
            out[table] = "ok"
            metrics.missing_tables.discard(table)
        except asyncpg.UndefinedTableError:
            out[table] = "missing: apply scripts/schema.sql"
            metrics.missing_tables.add(table)
        except Exception as e:  # noqa: BLE001
            out[table] = f"error ({type(e).__name__})"
    return out


def _bridge_row(name: str, bridge) -> str:
    if bridge is None:
        return f"<tr><th>{name}</th><td colspan=4>off</td></tr>"
    live = "connected" if bridge.session is not None else "down"
    return (f"<tr><th>{name}</th><td>{live}</td><td>{len(bridge.tools)} tools</td>"
            f"<td>{bridge.restarts} restarts, {bridge.timeouts} timeouts</td>"
            f"<td>{html.escape(bridge.last_error or '')}</td></tr>")


_SUGG_WORD = {"pending": "Waiting", "approved": "Approved", "declined": "Declined"}


async def page(request):
    user = auth.current_user(request)
    if not auth.is_admin(user):
        return PlainTextResponse("Not Found", status_code=404)
    tables = await _table_state()
    days = await metrics.daily_summary(14) or []
    last = await metrics.last_row_at()
    state = request.app.state
    cols = ("day", "runs", "usd", "complete", "refused", "failed", "truncated", "cancelled", "capped",
            "fixed", "dropped", "stopped", "tool_errors")
    heads = ("UTC day", "Runs", "Est. $", "Complete", "Refused", "Failed", "Cut short", "Closed early",
             "Limited", "Fixed replies", "Sentences dropped", "Replies stopped", "Tool errors")
    body = "".join(
        "<tr>" + "".join(f"<td>{d[c]:.2f}</td>" if c == "usd" else f"<td>{d[c]}</td>" for c in cols) + "</tr>"
        for d in days) or f"<tr><td colspan={len(cols)}>No runs recorded.</td></tr>"
    total = sum(float(d["usd"]) for d in days)
    week = sum(float(d["usd"]) for d in days[:7])
    helps = await metrics.daily_counts(14) or []
    help_rows = "".join(
        f"<tr><td>{h['day']}</td><td>{h['help_words'] + h['help_reply'] + h['help_check']}</td>"
        f"<td>{h['help_words']}</td><td>{h['help_reply']}</td><td>{h['help_check']}</td>"
        f"<td>{h['check_failed']}</td></tr>" for h in helps) or "<tr><td colspan=6>None recorded.</td></tr>"
    from webapp import shelf_docs
    sugg = await shelf_docs.pending() if db.ready() else []
    sugg_rows = "".join(
        f"<tr><td>{html.escape(r['title'] or '')}</td><td>{html.escape(r['author'] or '')}</td>"
        f"<td>{html.escape(r['basis'] or '')}</td><td>{(r['words'] or 0):,}</td><td>{_SUGG_WORD.get(r['status'], r['status'])}</td><td class=acts>"
        + (f"<a href=\"/ops/suggestions/{r['id']}/text\">Download the text</a>" if r["item_id"] else "Text gone")
        + ("".join(f"<form method=post action=\"/ops/suggestions/{r['id']}\"><input type=hidden name=decision value={d}>"
                   f"<button type=submit>{w}</button></form>" for d, w in (("approved", "Approve"), ("declined", "Decline")))
           if r["status"] == "pending" else "")
        + "</td></tr>" for r in sugg) or "<tr><td colspan=6>None waiting.</td></tr>"
    out = (
        "<h1>Operations</h1>"
        f"<p>Estimated spend: ${week:.2f} in the last 7 UTC days, ${total:.2f} in 14. Alert above "
        f"${ALERT_USD:.0f} a day. The Anthropic Console is the bill of record.</p>"
        "<h2>Libraries</h2><div class=wide tabindex=0 role=region aria-label=\"Libraries\"><table>"
        + _bridge_row("Bible", getattr(state, "mcp", None))
        + _bridge_row("History", getattr(state, "mcp_history", None)) + "</table></div>"
        "<h2>Runs by day</h2><div class=wide tabindex=0 role=region aria-label=\"Runs by day\"><table><tr>" + "".join(f"<th>{h}</th>" for h in heads)
        + "</tr>" + body + "</table></div>"
        "<h2>Help window</h2><p>How many times a day the Need help now window opened, and what opened "
        "it. A total only: no account, message, category, or time.</p><div class=wide tabindex=0 role=region aria-label=\"Help window by day\"><table><tr>"
        "<th>UTC day</th><th>Opened</th><th>Local check</th><th>Reply</th><th>Model check</th>"
        "<th>Model check failed</th></tr>" + help_rows + "</table></div>"
        "<h2 id=suggestions>Reading Room suggestions</h2><p>Books teachers uploaded and believe everyone may read, with "
        "their reason (decision 0029). Approving records your yes; adding the book to the Reading Room is still done "
        "with its text, outside the app.</p><div class=wide tabindex=0 role=region aria-label=\"Reading Room suggestions\"><table>"
        "<tr><th>Title</th><th>Author</th><th>Why everyone may read it</th><th>Words</th><th>Status</th><th>Act</th></tr>"
        + sugg_rows + "</table></div>"
        "<h2>Records</h2><div class=wide tabindex=0 role=region aria-label=\"Records\"><table>"
        + "".join(f"<tr><th>{t}</th><td>{html.escape(s)}</td></tr>" for t, s in tables.items())
        + f"<tr><th>Last metrics row</th><td>{last or 'none'}</td></tr>"
        f"<tr><th>Failed metric writes since start</th><td>{metrics.failed_writes}</td></tr>"
        f"<tr><th>Daily caps</th><td>students {usage.STUDENT_TURNS} turns or ${usage.STUDENT_USD:.2f}; "
        f"teachers {usage.TEACHER_TURNS} turns; all students ${usage.SCHOOL_USD:.2f}</td></tr>"
        f"<tr><th>Account-data purge</th><td>{'on' if retention.enabled() else 'off'}</td></tr>"
        "</table></div>"
    )
    return shell.render(request, about.prose("Operations", out, css=("/static/css/ops.css",), noindex=True),
                        cache="no-store")
