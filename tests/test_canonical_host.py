"""One origin per place, so Google sign-in's callback matches the registered address
(CanonicalHostMiddleware in webapp/app.py). No network."""
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from webapp import app as appmod


def client(monkeypatch, on_fly=False):
    monkeypatch.setattr(appmod, "_ON_FLY", on_fly)
    app = Starlette(routes=[Route("/{path:path}", lambda r: PlainTextResponse("ok"), methods=["GET", "POST"])],
                    middleware=[Middleware(appmod.CanonicalHostMiddleware)])
    return TestClient(app, follow_redirects=False)


@pytest.mark.parametrize("host,location", [
    ("127.0.0.1:8100", "http://localhost:8100/auth/login?next=%2F"),   # Google registers localhost only
    ("www.exegetica.app", "https://exegetica.app/auth/login?next=%2F"),
])
def test_other_names_for_a_host_redirect_to_the_registered_one(monkeypatch, host, location):
    r = client(monkeypatch).get("/auth/login?next=%2F", headers={"host": host})
    assert r.status_code == 308 and r.headers["location"] == location


@pytest.mark.parametrize("host", ["localhost:8100", "exegetica.app"])
def test_the_registered_hosts_pass_through(monkeypatch, host):
    assert client(monkeypatch).get("/auth/login", headers={"host": host}).text == "ok"


def test_a_check_on_the_server_itself_never_bounces(monkeypatch):
    r = client(monkeypatch, on_fly=True).get("/api/config", headers={"host": "127.0.0.1:8080"})
    assert r.status_code == 200
