"""Search engines see the front door and the public statements, and nothing a student or
teacher signs in for (ROBOTS_TXT in webapp/app.py). No network."""
import re

import pytest
from starlette.testclient import TestClient

from webapp import app as appmod


def allowed(path: str) -> bool:
    """Google's reading of a robots.txt: the longest matching rule wins, Allow wins a tie,
    "*" matches anything and a trailing "$" anchors the end."""
    best = (-1, True)
    for line in appmod.ROBOTS_TXT.splitlines():
        field, _, rule = line.partition(":")
        rule = rule.strip()
        if field.lower() not in ("allow", "disallow") or not rule:
            continue
        pattern = re.escape(rule.rstrip("$")).replace(r"\*", ".*") + ("$" if rule.endswith("$") else "")
        if re.match(pattern, path):
            rank = (len(rule), field.lower() == "allow")
            best = max(best, rank)
    return best[1]


def test_robots_txt_is_served_as_text():
    r = TestClient(appmod.app).get("/robots.txt")
    assert r.status_code == 200 and r.text == appmod.ROBOTS_TXT
    assert r.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize("path", ["/", "/position", "/quiet-standards", "/privacy", "/corpus"])
def test_the_front_door_and_public_statements_may_be_listed(path):
    assert allowed(path)


@pytest.mark.parametrize("path", ["/course", "/course/doc/GEN_final-1-book-of-signs-TEACHER.md",
                                  "/read/some-book", "/memory", "/library", "/generate", "/studio",
                                  "/ops", "/calendar", "/api/config", "/auth/login"])
def test_everything_behind_sign_in_stays_out(path):
    assert not allowed(path)
