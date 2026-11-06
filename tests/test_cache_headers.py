"""After a deploy, a browser must check pages and scripts before reusing them, so a new rail link or
script shows on the next load without a hard refresh (RevalidateMiddleware in webapp/app.py). No
network."""
import pytest
from starlette.testclient import TestClient

from webapp import app as appmod


@pytest.fixture(scope="module")
def client():
    return TestClient(appmod.app)


@pytest.mark.parametrize("path", ["/", "/library", "/static/settings.js", "/static/fonts/app.css"])
def test_pages_scripts_and_styles_are_checked_before_reuse(client, path):
    r = client.get(path)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    assert r.headers.get("etag")   # so an unchanged file answers 304


def test_an_unchanged_script_answers_not_modified(client):
    etag = client.get("/static/settings.js").headers["etag"]
    assert client.get("/static/settings.js", headers={"If-None-Match": etag}).status_code == 304


def test_who_is_signed_in_is_never_stored(client):
    # JSON with its own rule: the middleware leaves it alone
    assert client.get("/api/me").headers["cache-control"] == "no-store"
