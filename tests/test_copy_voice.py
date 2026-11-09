"""Every word people see follows the voice rules (docs/voice-and-copy.md, exegetica-design rule K5): the page
templates, the page scripts, the words the server renders into pages and messages, and the documents shown
as public pages. Quotations in those documents are someone else's words, so they're left out. The model
prompts are instructions to a model, held by test_student_prompts.py and their decision records. No network."""
import ast
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEBAPP = ROOT / "webapp"

# Modules whose strings become pages or messages in the browser.
PAGE_MODULES = ["about.py", "account.py", "calendar_views.py", "course_views.py", "house_cover.py", "library_store.py",
                "metrics.py", "ops.py", "reader.py", "shell.py", "store.py", "studio.py"]
PUBLIC_DOCS = ["privacy.md", "position-statement-christian-school-theologian.md", "quiet-standards-statement.md"]
DATA = re.compile(r"<script[^>]*type=\"application/json\"[^>]*>.*?</script>", re.S)   # book titles are data
QUOTED = re.compile(r"“[^”]*”|\"[^\"\n]*\"")
LOG_CALLS = {"debug", "info", "warning", "error", "exception"}


def _lint():
    spec = importlib.util.spec_from_file_location("lint_voice", ROOT / "scripts" / "lint_voice.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.lint_text


def _report(where, hits):
    return "\n".join(f"{where}:{n}: {label}: {snippet!r}" for n, label, snippet in hits)


def _page_files():
    return sorted(WEBAPP.glob("templates/**/*.html")) + sorted(WEBAPP.glob("static/js/*.js"))


@pytest.mark.parametrize("path", _page_files(), ids=lambda p: p.relative_to(WEBAPP).as_posix())
def test_templates_and_page_scripts_follow_the_voice_rules(path):
    text = DATA.sub(lambda m: "\n" * m.group(0).count("\n"), path.read_text(encoding="utf-8"))
    hits = _lint()(text)
    assert not hits, _report(path.relative_to(ROOT), hits)


def _server_strings(path):
    """String literals in a module, without its docstrings or log lines, which no reader sees."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                skip.add(id(first.value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in LOG_CALLS:
            skip.update(id(sub) for sub in ast.walk(node))
    return [(node.lineno, node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip]


@pytest.mark.parametrize("name", PAGE_MODULES)
def test_words_the_server_renders_follow_the_voice_rules(name):
    lint = _lint()
    hits = [(line, label, snippet) for line, s in _server_strings(WEBAPP / name) for _, label, snippet in lint(s)]
    assert not hits, _report(f"webapp/{name}", hits)


@pytest.mark.parametrize("name", PUBLIC_DOCS)
def test_public_pages_follow_the_voice_rules_outside_quotations(name):
    text = QUOTED.sub("“”", (ROOT / "docs" / name).read_text(encoding="utf-8"))
    hits = _lint()(text)
    assert not hits, _report(f"docs/{name}", hits)


def test_the_help_window_keeps_the_approved_crisis_wording():
    # Adam approved these exact lines on 2026-11-09. Any change to crisis copy is his call.
    assert "These people can help any time. It's free and " in (WEBAPP / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert "These people can help right now. It's free and private." in (WEBAPP / "static" / "js" / "chat.js").read_text(encoding="utf-8")
