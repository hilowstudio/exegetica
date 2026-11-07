"""After a deploy, a browser must check pages and scripts before reusing them, so a new rail link or
script shows on the next load without a hard refresh (RevalidateMiddleware in webapp/app.py, and
shell.page for the pages). No network."""
import pytest
from starlette.testclient import TestClient

from webapp import app as appmod


@pytest.fixture(scope="module")
def client():
    return TestClient(appmod.app)


@pytest.mark.parametrize("path", ["/static/js/settings.js", "/static/js/shell.js", "/static/css/shell.css",
                                  "/static/fonts/app.css"])
def test_scripts_and_styles_are_checked_before_reuse(client, path):
    r = client.get(path)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert r.headers.get("etag")   # so an unchanged file answers 304


@pytest.mark.parametrize("path", ["/", "/library", "/read", "/privacy"])
def test_pages_differ_by_person_so_no_shared_cache_keeps_them(client, path):
    # the rail shows a teacher's and an admin's places, so a page is built for its reader
    r = client.get(path)
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-cache"


def test_an_unchanged_script_answers_not_modified(client):
    etag = client.get("/static/js/settings.js").headers["etag"]
    assert client.get("/static/js/settings.js", headers={"If-None-Match": etag}).status_code == 304


def test_who_is_signed_in_is_never_stored(client):
    # JSON with its own rule: the middleware leaves it alone
    assert client.get("/api/me").headers["cache-control"] == "no-store"
