"""The browser check (scripts/design_check.py, exegetica-design rule K3) stays safe and complete: it blanks
production data and every model key before the app loads, it never takes Adam's port, its copy of axe-core
is the vendored one, and it visits every page the app serves. No network, no browser."""
import importlib.util
from pathlib import Path

from starlette.routing import Route

ROOT = Path(__file__).resolve().parent.parent


def _check():
    spec = importlib.util.spec_from_file_location("design_check", ROOT / "scripts" / "design_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_it_blanks_production_data_and_model_keys():
    blank = set(_check().BLANK)
    assert {"DATABASE_URL", "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"} <= blank
    assert {"ANTHROPIC_API_KEY", "DEEPINFRA_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"} <= blank
    src = (ROOT / "scripts" / "design_check.py").read_text(encoding="utf-8")
    assert src.index("os.environ[name] = \"\"") < src.index("from webapp import auth")   # before the app reads .env
    assert "a.port == 8100" in src                                                         # Adam's own server


def test_it_uses_the_vendored_axe_core():
    axe = _check().AXE
    assert axe == ROOT / "scripts" / "vendor" / "axe-core" / "axe.min.js"
    assert axe.read_text(encoding="utf-8")[:40].startswith("/*! axe v4.")
    assert (axe.parent / "LICENSE").exists() and "Mozilla Public License" in (axe.parent / "LICENSE").read_text(encoding="utf-8")


def test_it_visits_every_page_the_app_serves():
    from webapp.app import app
    not_pages = {"/robots.txt", "/favicon.ico", "/apple-touch-icon.png", "/ops/flag"}
    pages = {r.path for r in app.routes if isinstance(r, Route) and "GET" in (r.methods or set())
             and "{" not in r.path and not r.path.startswith(("/api", "/auth", "/static", "/mcp")) and r.path not in not_pages}
    missing = pages - set(_check().PAGES)
    assert not missing, f"add these to PAGES in scripts/design_check.py: {sorted(missing)}"
