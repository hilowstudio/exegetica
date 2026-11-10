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
    # the Reading Room is a room inside the Living Library, which everyone has (decision 0029)
    assert _places(False, False) == ["/", "/memory", "/library"]
    assert _places(True, False) == ["/", "/memory", "/library", "/generate"]
    assert _places(True, True) == ["/", "/memory", "/library", "/generate", "/studio"]
    assert _places(False, True) == _places(True, True)   # an admin sees the teacher places too


def test_the_rail_marks_the_page_you_are_on():
    def active(path):
        return [i["href"] for i in shell.rail_items(path, True, True) if i["active"]]
    assert active("/") == ["/"] and active("/memory") == ["/memory"] and active("/library") == ["/library"]
    assert active("/read") == ["/library"] and active("/read/some-book") == ["/library"]   # a room of the Living Library
    assert active("/privacy") == []


@pytest.mark.parametrize("user,shown,hidden", [
    (None, ["/memory", "/library"], ["/generate", "/studio", "/read"]),
    ({"email": "t@school.test", "role": "teacher"}, ["/library", "/generate"], ["/studio"]),
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


def test_the_status_line_is_the_shells_and_names_every_stage_the_server_sends():
    # the wording lives once, in shell.js, and covers each stage webapp/providers.py can send
    from webapp import providers
    shell_js = (STATIC / "js" / "shell.js").read_text(encoding="utf-8")
    sent = re.findall(r'"stage": ([^,}]+)', Path(providers.__file__).read_text(encoding="utf-8"))
    stages = {s for expr in sent for s in re.findall(r'"(\w+)"', expr)}
    assert stages == {"studying", "reading", "looking", "writing", "checking"}
    for stage in stages:
        assert re.search(rf"\b{stage}: \"", shell_js), stage
    for page in ("chat.js", "generate.js"):
        text = (STATIC / "js" / page).read_text(encoding="utf-8")
        assert "Shell.status(" in text and "Studying the question" not in text, page


def test_pages_ask_and_confirm_through_the_shell():
    # rule F3/F4 of the exegetica-design skill: the page's own dialog (Shell.ask) and one toast with Undo
    # (Shell.toast), never the browser's confirm(), alert() or prompt(), and no toast of a page's own
    shell_js = (STATIC / "js" / "shell.js").read_text(encoding="utf-8")
    assert "function ask(" in shell_js and "function toast(" in shell_js and "ask: ask, toast: toast" in shell_js
    native = re.compile(r"(?<![\w$.])(?:window\.)?(?:confirm|alert|prompt)\s*\(")
    for js in (STATIC / "js").glob("*.js"):
        code = re.sub(r"/\*.*?\*/", "", js.read_text(encoding="utf-8"), flags=re.S)
        code = "\n".join(line.split("//")[0] if "://" not in line else line for line in code.splitlines())
        assert not native.search(code), (js.name, native.search(code).group(0))
    for page in PAGES:
        assert 'id="toast"' not in page.read_text(encoding="utf-8"), page.name
    for css in (STATIC / "css").glob("*.css"):
        if css.name != "shell.css":
            assert not re.search(r"(^|[\s,}])\.toast[{.:\s]", css.read_text(encoding="utf-8")), css.name


def test_settings_offers_no_model_or_key():
    js = (STATIC / "js" / "settings.js").read_text(encoding="utf-8")
    assert "Model &amp; Key" not in js and 'id="set-key"' not in js and "Appearance" not in js


def test_the_prep_room_ignores_a_provider_model_or_key_from_the_browser():
    assert policy.BYOK is False
    assert policy.byok({"provider": "openai", "model": "gpt-5.6", "api_key": "sk-x"}) == ("anthropic", "", None)


def test_every_page_sits_on_the_garden_with_the_wordmark_in_its_own_column():
    css = {f.name: f.read_text(encoding="utf-8") for f in (STATIC / "css").glob("*.css")}
    assert "var(--garden)" in re.search(r"^body\{[^}]*\}", css["shell.css"], re.M).group(0)
    gardens = re.findall(r'--garden:url\("/static/([\w.-]+)"\)', css["tokens.css"])   # light, system dark, chosen dark
    assert gardens == ["garden-light.webp", "garden.webp", "garden.webp"], gardens
    assert all((STATIC / g).exists() for g in gardens)
    for page in ("generate", "studio", "reader", "covers"):   # their sticky bars stay clear until stuck
        assert "shell-stick" in (TEMPLATES / f"{page}.html").read_text(encoding="utf-8"), page
    for name, sheet in css.items():   # no page paints the paper colour over the whole page (on screen: paper prints white)
        if name != "shell.css":
            sheet = re.sub(r"@media print\{.*?\n\}", "", sheet, flags=re.S)
            body = re.search(r"^\s*body\{[^}]*\}", sheet, re.M)
            assert not body or "background" not in body.group(0), name
    assert "masthead" not in (TEMPLATES / "base.html").read_text(encoding="utf-8")   # no banner above the page
    for page in PAGES:   # each page puts the wordmark in its own column, once
        text = page.read_text(encoding="utf-8")
        stacks = page.name in ("generate.html", "studio.html")   # their panels stack on a phone: one shows at a time
        # doc.html is an upload's reading view: like a book's pages in the Reading Room, it has no wordmark
        assert text.count('{% include "partials/masthead.html" %}') == (0 if page.name in ("built.html", "doc.html") else 2 if stacks else 1), page.name
        if stacks:
            assert 'mast="narrow"' in text and 'mast="wide"' in text, page.name
        assert "/static/wordmark" not in text, page.name   # the wordmark lives in the partial alone
    client = TestClient(appmod.app)
    for path in ("/", "/memory", "/read", "/corpus", "/privacy", "/position"):
        assert client.get(path).text.count('class="masthead"') == 1, path
    browse = re.search(r'<main id="browse" hidden>.*?</main>', client.get("/read/some-book").text, re.S).group(0)
    assert 'class="masthead"' in browse   # on the shelves only: a book's pages fill the window
    assert 'href="/"' not in re.search(r'<header class="masthead">.*?</header>', client.get("/").text, re.S).group(0)
    assert shell.MASTHEAD not in client.get("/privacy").text
    printed = re.search(r"@media print\{.*?^\}", css["shell.css"], re.S | re.M).group(0)
    assert ".masthead{display:none" in printed.replace(",.masthead{", ".masthead{")   # nor on paper


STUDENT = {"email": "s@school.test", "role": "student"}
TEACHER = {"email": "t@school.test", "role": "teacher"}
ADMIN = {"email": "a@school.test", "role": "teacher"}


@pytest.mark.parametrize("path,opens,says", [
    ("/generate", ("teacher", "admin"), "The Prep Room is for teachers."),
    ("/read/admin/covers", ("admin",), "The magazine covers review is for library admins."),
])
def test_teacher_places_turn_others_away_with_a_page(monkeypatch, path, opens, says):
    # decision 0007: the actions already refuse, and the page says so instead of showing a tool that can't work
    people = {"guest": None, "student": STUDENT, "teacher": TEACHER, "admin": ADMIN}
    for role, user in people.items():
        monkeypatch.setattr(auth, "current_user", lambda request, u=user: u)
        monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u["role"] == "teacher")
        monkeypatch.setattr(auth, "is_admin", lambda u: bool(u) and u["email"] == "a@school.test")
        r = TestClient(appmod.app).get(path)
        if role in opens:
            assert r.status_code == 200 and says not in r.text, (path, role)
        else:
            assert r.status_code == 403 and says in r.text and 'href="/">Back to chat' in r.text, (path, role)
            assert ("/auth/login?next=" in r.text) == (user is None), (path, role)   # sign-in only when signed out


def test_the_verse_list_sits_beside_the_page_wider_than_a_phone():
    # Adam, 2026-11-09: on a laptop or tablet the open list moves the page over, so nothing hides under it.
    # On a phone it covers the page, which waits out of reach (inert) until the list closes.
    css = (STATIC / "css" / "memory.css").read_text(encoding="utf-8")
    wide = re.search(r"@media \(min-width:641px\)\{.*?\n\}", css, re.S).group(0)
    assert ".side.open ~ .col{padding-left:294px}" in wide and ".side.open{box-shadow:none}" in wide
    js = (STATIC / "js" / "memory.js").read_text(encoding="utf-8")
    assert "col.inert = !!o && !!(phone && phone.matches)" in js
    assert "if(phone && phone.matches) setDrawerOpen(false);" in js   # a docked list stays put when a verse is chosen
    assert '"Hide verses":"Show verses"' in js                         # the toggle says what it will do


def test_the_rail_is_always_there():
    # Adam, 2026-11-09: the rail is never collapsible. No hide button, no edge handle, no remembered closed state.
    root = Path(__file__).resolve().parent.parent / "webapp"
    rail = (root / "templates" / "partials" / "rail.html").read_text(encoding="utf-8")
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")
    css = (root / "static" / "css" / "shell.css").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert "rail-collapse" not in rail and "rail-handle" not in rail
    assert 'data-rail' not in base and 'data-rail' not in css
    assert "setRail" not in js and 'localStorage.removeItem("exeg-rail")' in js


def test_the_living_library_opens_for_everyone(monkeypatch):
    # decision 0029: the Living Library is everyone's, with the Reading Room inside it; the page draws by role
    for user in (None, STUDENT, TEACHER):
        monkeypatch.setattr(auth, "current_user", lambda request, u=user: u)
        monkeypatch.setattr(auth, "is_teacher", lambda u: bool(u) and u["role"] == "teacher")
        r = TestClient(appmod.app).get("/library")
        assert r.status_code == 200 and "is for teachers" not in r.text
