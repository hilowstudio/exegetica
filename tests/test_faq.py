"""The chat page's FAQ is built from docs/faq.md (scripts/build_faq.py) into a partial the chat page
includes: the partial matches the source, every link in it leads to a page the app serves, and
nothing from the working notes after the end marker reaches the page. No network."""
import importlib.util
import re

from webapp import app as appmod

spec = importlib.util.spec_from_file_location("build_faq", appmod.PROJECT_ROOT / "scripts" / "build_faq.py")
build_faq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_faq)


def _block() -> str:
    return build_faq.PAGE.read_text(encoding="utf-8")


def test_the_page_matches_docs_faq():
    assert build_faq.render(build_faq.SOURCE.read_text(encoding="utf-8")) == _block()
    chat = (appmod.PROJECT_ROOT / "webapp" / "templates" / "chat.html").read_text(encoding="utf-8")
    assert '{% include "partials/faq.html" %}' in chat


def test_every_audience_has_questions():
    found = build_faq.sections(build_faq.SOURCE.read_text(encoding="utf-8"))
    assert [a for a, _q in found] == ["Students", "Teachers", "Parents"]
    assert all(q for _a, q in found)


def test_every_link_in_the_faq_leads_somewhere():
    paths = {getattr(r, "path", None) for r in appmod.app.routes}
    for href in re.findall(r'href="([^"]+)"', _block()):
        assert href.startswith("https://") or href.split("#")[0] in paths, href


def test_the_working_notes_stay_out_of_the_page():
    block = _block()
    for note in ("Follow-ups", "maker's direction", "Set aside"):
        assert note not in block
