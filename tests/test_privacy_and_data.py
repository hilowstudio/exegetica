"""What the server keeps about people, and how it lets them leave: the metrics allowlist, the cap
counters' keys, account export and delete, and the privacy page's retention lines. A fake
database; nothing touches Neon or R2."""
import asyncio
import datetime as dt
import uuid

import pytest

from webapp import about, account, db, metrics, r2, retention, usage

UID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


# ---------------------------------------------------------------- metrics
@pytest.mark.parametrize("field", ["email", "user_id", "text", "message", "persona", "ip", "session", "error"])
def test_metrics_rows_refuse_personal_fields(field):
    with pytest.raises(ValueError):
        metrics.row(route="chat:bible", key_source="server", outcome="complete", **{field: "x"})


def test_metrics_labels_come_from_fixed_sets():
    with pytest.raises(ValueError):
        metrics.row(route="chat:bible", key_source="server", outcome="the student said hello")
    r = metrics.row(route="chat:bible", key_source="server", outcome="complete",
                    model_req="claude-opus-5-5", model_served="some-new-model",
                    prefix_hash="not a hash at all", refusal_category="Please help me", steps="3")
    assert r["model_served"] == "other" and r["prefix_hash"] is None and r["refusal_category"] is None
    assert r["steps"] == 3


def test_cap_counter_keys_change_every_day_and_hide_the_account():
    d1, d2 = dt.date(2026, 11, 2), dt.date(2026, 11, 3)
    a, b = usage.who(str(UID), d1), usage.who(str(UID), d2)
    assert a != b and str(UID) not in a and len(a) == 32


def test_caps_fail_open_without_a_database(monkeypatch):
    monkeypatch.setattr(db, "ready", lambda: False)
    assert asyncio.run(usage.check(str(UID), False)) is None


# ---------------------------------------------------------------- export and delete
class _Conn:
    def __init__(self, log):
        self.log = log

    async def execute(self, sql, *args):
        self.log.append(("sql", " ".join(sql.split()), args))
        return "DELETE 1" if sql.strip().startswith("delete") else "UPDATE 0"

    def transaction(self):
        log = self.log

        class _Tx:
            async def __aenter__(self):
                log.append(("begin",))

            async def __aexit__(self, *a):
                log.append(("commit",) if a[0] is None else ("rollback",))
        return _Tx()


class _Pool:
    def __init__(self, log):
        self.log = log

    def acquire(self):
        conn = _Conn(self.log)

        class _Acq:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False
        return _Acq()


def test_delete_removes_files_first_then_scrubs_and_deletes_in_one_transaction(monkeypatch):
    log = []
    monkeypatch.setattr(db, "pool", lambda: _Pool(log))
    monkeypatch.setattr(r2, "configured", lambda: True)

    async def fake_prefix(prefix):
        log.append(("r2", prefix))
        return 2
    monkeypatch.setattr(r2, "delete_prefix_async", fake_prefix)
    out = asyncio.run(account.remove(UID, "t@school.test"))
    assert log[:2] == [("r2", f"uploads/{UID}/"), ("r2", f"studio/{UID}/")]   # uploads, then Image Studio
    assert log[2] == ("begin",) and log[-1] == ("commit",)
    sql = [entry[1] for entry in log if entry[0] == "sql"]
    assert sql[0].startswith("update library_extractions set canonical_source = 'upload:removed'")
    assert any(s.startswith("update cover_overrides set updated_by = null") for s in sql)
    assert sql[-1].startswith("delete from users where id = $1")
    assert out == {"files": 4, "account": True}


def test_delete_stops_before_the_database_if_the_files_cannot_be_removed(monkeypatch):
    log = []
    monkeypatch.setattr(db, "pool", lambda: _Pool(log))
    monkeypatch.setattr(r2, "configured", lambda: True)

    async def broken(prefix):
        raise RuntimeError("R2 down")
    monkeypatch.setattr(r2, "delete_prefix_async", broken)
    with pytest.raises(RuntimeError):
        asyncio.run(account.remove(UID, None))
    assert log == []


def test_export_covers_every_account_store(monkeypatch):
    async def fetchrow(sql, *a):
        return None

    async def fetch(sql, *a):
        return []
    monkeypatch.setattr(db, "fetchrow", fetchrow)
    monkeypatch.setattr(db, "fetch", fetch)
    data = asyncio.run(account.collect(UID))
    for key in ("account", "scripture_memory", "studies", "reading_places", "cover_preferences",
                "library_shelf", "library_uploads"):
        assert key in data


def test_prefix_delete_refuses_anything_but_a_folder():
    with pytest.raises(ValueError):
        asyncio.run(r2.delete_prefix_async(""))
    with pytest.raises(ValueError):
        asyncio.run(r2.delete_prefix_async("uploads"))


# ---------------------------------------------------------------- privacy page
def _privacy() -> str:
    return asyncio.run(about.privacy_page(None)).body.decode()


def test_privacy_page_claims_no_purge_that_is_off(monkeypatch):
    monkeypatch.delenv("RETENTION_PURGE", raising=False)
    page = _privacy()
    assert "{{" not in page and "until you delete it" in page and "12 months" not in page


def test_privacy_page_states_the_purge_when_it_is_on(monkeypatch):
    monkeypatch.setenv("RETENTION_PURGE", "on")
    page = _privacy()
    assert f"{retention.INACTIVE_MONTHS} months" in page


def test_privacy_page_states_the_facts_the_faq_promises():
    page = _privacy()
    for fact in ("mandated reporter", "Anthropic", "internet connection", "pays the running costs",
                 "Download my data", "Delete my account", "Clear this browser", "Google Fonts"):
        assert fact in page, fact
