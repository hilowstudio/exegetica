"""Sign-in links for guests (decision 0005, amended 2026-11-25): the maker makes a link on /ops for an address on the
guest list; opening it signs no one in; pressing its button signs the guest in once; a used, expired, altered or
off-list link is refused. No network, no database: the users table is a dict here."""
import asyncio
import datetime as dt

import pytest
from starlette.datastructures import URL

from webapp import auth, db, guest_link

GUEST = "a.guest@gmail.com"


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-links")
    monkeypatch.setenv("GUEST_EMAILS", GUEST)
    monkeypatch.setenv("TEACHER_EMAILS", "a.teacher@gmail.com")
    monkeypatch.setenv("LIBRARY_ADMIN_EMAILS", "the.maker@example.com")
    # pages come back as (status, body) instead of being rendered through the shell
    monkeypatch.setattr(guest_link, "_page", lambda request, title, body, status=200, scripts=(): (status, body))


@pytest.fixture()
def users(monkeypatch):
    table: dict[str, dict] = {}

    async def fetchrow(sql, *args):
        if sql.lstrip().startswith("select"):
            return table.get(args[0])
        if sql.lstrip().startswith("update"):
            row = next(r for r in table.values() if r["id"] == args[0])
            row["last_login_at"] = dt.datetime.now(dt.timezone.utc)
            return row
        sub, email, name = args
        row = {"id": f"id-{len(table) + 1}", "name": name, "role": "student", "google_sub": sub,
               "last_login_at": dt.datetime.now(dt.timezone.utc)}
        table[email] = row
        return row

    monkeypatch.setattr(db, "ready", lambda: True)
    monkeypatch.setattr(db, "fetchrow", fetchrow)
    return table


class Request:
    def __init__(self, query=None, form=None, user=None):
        self.query_params = query or {}
        self._form = form or {}
        self.session = {"user": user} if user else {}
        self.base_url = URL("http://localhost:8000/")

    async def form(self):
        return self._form


def run(coro):
    return asyncio.run(coro)


def test_a_link_names_its_guest_and_nothing_else_reads():
    token = guest_link.make_token(GUEST)
    got = guest_link.read_token(token)
    assert got["email"] == GUEST and got["issued"].tzinfo is not None
    assert guest_link.read_token(token[:-2] + "xx") is None          # altered
    assert guest_link.read_token("") is None
    assert guest_link.read_token(guest_link.make_token("someone@gmail.com")) is None   # not on the list


def test_only_guests_get_links():
    assert auth.is_guest_email(GUEST)
    for email in ("a.teacher@gmail.com", "the.maker@example.com", "x@yorkvillechristian.com", "nobody@gmail.com", ""):
        assert not auth.is_guest_email(email)


def test_a_link_expires(monkeypatch):
    token = guest_link.make_token(GUEST)
    monkeypatch.setattr(guest_link, "LINK_DAYS", -1)
    assert guest_link.read_token(token) is None


def test_taking_the_guest_off_the_list_kills_the_link(monkeypatch):
    token = guest_link.make_token(GUEST)
    monkeypatch.setenv("GUEST_EMAILS", "")
    assert guest_link.read_token(token) is None


def test_no_secret_no_links(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET")
    assert guest_link.make_token(GUEST) is None


def test_a_link_is_spent_once_its_account_signs_in_after_it_was_made():
    issued = dt.datetime(2026, 11, 25, 12, tzinfo=dt.timezone.utc)
    assert not guest_link.spent(None, issued)
    assert not guest_link.spent(issued - dt.timedelta(days=1), issued)
    assert guest_link.spent(issued + dt.timedelta(minutes=5), issued)


def test_opening_the_link_signs_no_one_in(users):
    token = guest_link.make_token(GUEST)
    req = Request(query={"t": token})
    status, body = run(guest_link.page(req))
    assert status == 200 and GUEST in body and 'method="post" action="/auth/link"' in body
    assert req.session == {} and users == {}


def test_pressing_the_button_signs_the_guest_in_once(users):
    token = guest_link.make_token(GUEST)
    req = Request(form={"t": token})
    r = run(guest_link.redeem(req))
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert req.session["user"]["email"] == GUEST and req.session["user"]["role"] == "student"
    assert users[GUEST]["google_sub"] == "link:" + GUEST
    again = Request(form={"t": token})                               # the same link on another device
    status, body = run(guest_link.redeem(again))
    assert status == 410 and guest_link.SPENT in body and again.session == {}


def test_a_second_press_on_the_same_device_just_goes_home(users):
    token = guest_link.make_token(GUEST)
    r = run(guest_link.redeem(Request(form={"t": token}, user={"email": GUEST, "id": "id-1"})))
    assert r.status_code == 303 and users == {}


def test_a_bad_link_signs_no_one_in(users):
    req = Request(form={"t": "not-a-link"})
    status, body = run(guest_link.redeem(req))
    assert status == 410 and req.session == {} and users == {}


def test_only_the_maker_makes_links_and_only_for_guests():
    r = run(guest_link.make(Request(form={"email": GUEST}, user={"email": "a.teacher@gmail.com"})))
    assert r.status_code == 404
    status, _ = run(guest_link.make(Request(form={"email": "nobody@gmail.com"}, user={"email": "the.maker@example.com"})))
    assert status == 400
    status, body = run(guest_link.make(Request(form={"email": GUEST}, user={"email": "the.maker@example.com"})))
    assert status == 200 and "http://localhost:8000/auth/link?t=" in body and 'id="copy-link"' in body


def test_ops_lists_the_guests_with_a_button_each():
    out = guest_link.ops_section()
    assert GUEST in out and 'action="/ops/guest-link"' in out and "Make a sign-in link" in out
