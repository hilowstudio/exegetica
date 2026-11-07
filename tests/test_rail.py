"""The shared layout (webapp/shell.py, templates/base.html): one rail, drawn once, on every page, whose
places differ only by who is signed in; the theme button and Settings as a profile icon at its foot;
Settings offers no provider, model or key (policy.BYOK is off). No network."""
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp import app as appmod
from webapp import auth, policy, shell

WEBAPP = Path(appmod.__file__).parent
TEMPLATES = WEBAPP / "templates"
STATIC = WEBAPP / "static"
PAGES = sorted(p for p in TEMPLATES.glob("*.html") if p.name != "base.html")


def _places(teacher, admin):
    return [i["href"] for i in shell.rail_items("/", teacher, admin)]


def test_the_rail_shows_each_role_its_places():
    assert _places(False, False) == ["/", "/memory", "/read"]
    assert _places(True, False) == ["/", "/memory", "/read", "/generate", "/library"]
    assert _places(True, True) == ["/", "/memory", "/read", "/generate", "/library", "/studio"]
    assert _places(False, True) == _places(True, True)   # an admin sees the teacher places too


def test_the_rail_marks_the_page_you_are_on():
    def active(path):
        return [i["href"] for i in shell.rail_items(path, True, True) if i["active"]]
    assert active("/") == ["/"] and active("/read/some-book") == ["/read"] and active("/memory") == ["/memory"]
    assert active("/privacy") == []


@pytest.mark.parametrize("user,shown,hidden", [
    (None, ["/memory", "/read"], ["/generate", "/library", "/studio"]),
    ({"email": "t@school.test", "role": "teacher"}, ["/generate", "/library"], ["/studio"]),
])
def test_a_page_draws_only_the_places_the_reader_may_open(monkeypatch, user, shown, hidden):
    monkeypatch.setattr(auth, "current_user", lambda request: user)
    monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u))
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    rail = re.search(r'<nav class="rail".*?</nav>', TestClient(appmod.app).get("/privacy").text, re.S).group(0)
    for href in shown:
        assert f'href="{href}"' in rail, href
    for href in hidden:
        assert f'href="{href}"' not in rail, href


def test_every_page_extends_the_base_and_none_draws_its_own_rail():
    assert PAGES and not list(STATIC.glob("*.html"))   # every page is a template now
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        assert text.lstrip().startswith(('{% extends "base.html" %}', "{#")) and '{% extends "base.html" %}' in text, page.name
        assert 'class="rail"' not in text and 'id="help-bg"' not in text and "<!doctype" not in text.lower(), page.name
    assert (TEMPLATES / "base.html").read_text(encoding="utf-8").count('{% include "partials/rail.html" %}') == 1
    for py in WEBAPP.glob("*.py"):
        assert "<!doctype" not in py.read_text(encoding="utf-8").lower(), py.name   # built pages use shell.Built


def test_no_page_stylesheet_restyles_the_rail_or_redefines_the_colours():
    shared = set(re.findall(r"(--[\w-]+)\s*:", (STATIC / "css" / "tokens.css").read_text(encoding="utf-8")))
    sheets = [p for p in (STATIC / "css").glob("*.css") if p.name not in ("tokens.css", "shell.css")]
    sheets.append(STATIC / "course.css")
    for sheet in sheets:
        css = sheet.read_text(encoding="utf-8")
        assert not re.search(r"(^|[\s,}])\.rail\b", css), sheet.name
        assert not shared & set(re.findall(r"(--[\w-]+)\s*:", css)), (sheet.name, shared & set(re.findall(r"(--[\w-]+)\s*:", css)))


def test_the_rail_ends_with_help_then_the_theme_button_then_settings():
    rail = (TEMPLATES / "partials" / "rail.html").read_text(encoding="utf-8")
    assert re.search(r'id="help-link".*?id="theme-toggle"[^>]*>\s*</button>\s*<button[^>]*id="open-settings"', rail, re.S)
    settings = re.search(r'id="open-settings".*?</button>', rail, re.S).group(0)
    assert '<circle cx="12" cy="12" r="9"/>' in settings   # the profile icon, in its circle
    assert 'getElementById("theme-toggle")' not in (STATIC / "js" / "settings.js").read_text(encoding="utf-8")
    assert '$("theme-toggle")' in (STATIC / "js" / "shell.js").read_text(encoding="utf-8")


def test_tool_chips_are_drawn_by_the_shell_alone():
    # one chip per tool with a count (Shell.chips in shell.js, .tool-chip in shell.css), on every page that has them
    for js in (STATIC / "js").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        if js.name == "shell.js":
            assert "function chips(box)" in text
        else:
            assert "tool-chip running" not in text and "class='ic'" not in text, js.name
    for page in ("chat.js", "generate.js"):
        assert "Shell.chips(" in (STATIC / "js" / page).read_text(encoding="utf-8"), page
    for css in (STATIC / "css").glob("*.css"):
        assert (".tool-chip" in css.read_text(encoding="utf-8")) == (css.name == "shell.css"), css.name


def test_settings_offers_no_model_or_key():
    js = (STATIC / "js" / "settings.js").read_text(encoding="utf-8")
    assert "Model &amp; Key" not in js and 'id="set-key"' not in js and "Appearance" not in js


def test_the_prep_room_ignores_a_provider_model_or_key_from_the_browser():
    assert policy.BYOK is False
    assert policy.byok({"provider": "openai", "model": "gpt-5.6", "api_key": "sk-x"}) == ("anthropic", "", None)
