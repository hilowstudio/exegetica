"""Who may sign in (decision 0005): school accounts, the teacher and admin allowlists, and the few guests the maker adds
by hand (GUEST_EMAILS). A guest has the student role and rules, takes no classes, and never reads school copies.
Taking someone off a list ends their access on their next request. No network, no database."""
import asyncio
import json

import pytest

from webapp import auth, reader, shelves

GUEST = "a.guest@gmail.com"
SCHOOL = "a.student@yorkvillechristian.com"


@pytest.fixture(autouse=True)
def lists(monkeypatch):
    monkeypatch.setenv("GUEST_EMAILS", f'"{GUEST.upper()}, another@example.org"')
    monkeypatch.setenv("TEACHER_EMAILS", "a.teacher@gmail.com")
    monkeypatch.setenv("LIBRARY_ADMIN_EMAILS", "the.maker@example.com")


class Request:
    def __init__(self, user, body=None):
        self.session = {"user": user} if user else {}
        self._body = body or {}

    async def json(self):
        return self._body


def test_school_accounts_sign_in_only_when_verified():
    assert auth._may_sign_in({"email": SCHOOL, "email_verified": True})
    assert not auth._may_sign_in({"email": SCHOOL, "email_verified": False})


def test_a_listed_guest_signs_in_and_anyone_else_from_outside_does_not():
    assert auth._may_sign_in({"email": GUEST, "email_verified": True})
    assert not auth._may_sign_in({"email": GUEST, "email_verified": False})
    assert not auth._may_sign_in({"email": "someone.else@gmail.com", "email_verified": True})


def test_teachers_and_admins_still_sign_in():
    assert auth._may_sign_in({"email": "a.teacher@gmail.com"})
    assert auth._may_sign_in({"email": "the.maker@example.com"})


def test_a_guest_is_a_student_and_never_a_teacher():
    assert auth._role_for(GUEST) == "student"
    assert not auth.is_teacher({"email": GUEST})
    assert auth.is_guest({"email": GUEST})
    assert not auth.is_guest({"email": SCHOOL})
    assert not auth.is_guest({"email": "a.teacher@gmail.com"})
    assert not auth.is_guest(None)


def test_a_guest_never_reads_school_copies():
    assert not reader.may_read_school({"email": GUEST})
    assert reader.reader_level({"email": GUEST}) == 0


def test_taking_a_guest_off_the_list_ends_their_session(monkeypatch):
    assert auth.current_user(Request({"email": GUEST, "id": "x"})) is not None
    monkeypatch.setenv("GUEST_EMAILS", "")
    assert auth.current_user(Request({"email": GUEST, "id": "x"})) is None
    assert auth.current_user(Request({"email": SCHOOL, "id": "y"})) is not None


def test_a_guest_takes_no_classes():
    guest = {"email": GUEST, "id": "00000000-0000-0000-0000-000000000001"}
    assert shelves.courses_open_to(guest) == []
    assert asyncio.run(shelves.classes_of(guest)) == []
    assert shelves.courses_open_to({"email": SCHOOL})   # a school student still sees the school's list


def test_a_guest_cannot_choose_classes():
    guest = {"email": GUEST, "id": "00000000-0000-0000-0000-000000000001"}
    r = asyncio.run(shelves.choose_classes(Request(guest, {"courses": ["bible-2"]})))
    assert r.status_code == 403
    assert json.loads(r.body)["error"] == shelves.GUEST_CLASSES
