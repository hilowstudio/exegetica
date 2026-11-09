"""Reading type (Group G of the exegetica-design skill): one face per role from tokens.css, Greek and Hebrew
self-hosted and tagged on every page, and reading lines held to a comfortable measure. No network."""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "webapp" / "static"
TEMPLATES = STATIC.parent / "templates"
CSS = STATIC / "css"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_no_page_stylesheet_names_a_typeface():
    # faces come from the tokens (var(--sans), var(--serif), ...); the course pages keep the school's own
    # palette in static/course.css, outside this folder
    for sheet in CSS.glob("*.css"):
        if sheet.name == "tokens.css":
            continue
        named = re.findall(r"font-family:\s*([^;}]+)", _read(sheet))
        direct = [f for f in named if not f.strip().startswith(("var(", "inherit", "initial"))]
        assert not direct, (sheet.name, direct)


def test_the_roles_are_tokens():
    tokens = _read(CSS / "tokens.css")
    for role in ("--sans", "--serif", "--mono", "--display", "--caps", "--greek", "--hebrew"):
        assert re.search(rf"{role}:\s*\"", tokens), role
    for role in ("--sans", "--serif"):   # any Greek or Hebrew character, tagged or not, finds its face
        stack = re.search(rf"{role}:([^;]+);", tokens).group(1)
        assert '"Exegetica Greek"' in stack and '"Exegetica Hebrew"' in stack, role


def test_greek_and_hebrew_are_self_hosted_for_every_page():
    orig = _read(STATIC / "fonts" / "orig.css")
    assert "fonts.gstatic.com" not in orig and "fonts.googleapis.com" not in orig
    faces = re.findall(r"@font-face\s*\{([^}]*)\}", orig)
    greek = [f for f in faces if "'Exegetica Greek'" in f]
    hebrew = [f for f in faces if "'Exegetica Hebrew'" in f]
    assert greek and hebrew
    assert any("U+1F00-1FFF" in f for f in greek), "polytonic Greek (Greek Extended) is missing"
    assert all("U+0590-05FF" in f for f in hebrew), "the Hebrew block (letters, points, accents) is missing"
    for url in re.findall(r"url\((/static/fonts/pages/[^)]+)\)", orig):
        assert (STATIC.parent / url.lstrip("/")).exists(), url
    assert '<link rel="stylesheet" href="/static/fonts/orig.css">' in _read(TEMPLATES / "base.html")


def test_greek_and_hebrew_are_tagged_and_set():
    shell_js = _read(STATIC / "js" / "shell.js")
    assert "function tagLanguages(" in shell_js and "tagLanguages: tagLanguages" in shell_js
    assert "tagLanguages(document.body)" in shell_js and "MutationObserver" in shell_js   # the page, then what arrives
    assert 'span.lang = m[1] ? "grc" : "he"' in shell_js and 'span.dir = "rtl"' in shell_js
    shell_css = _read(CSS / "shell.css")
    assert re.search(r":lang\(grc\)\{font-family:var\(--greek\);font-size:1\.\d+em", shell_css)
    assert re.search(r":lang\(he\)\{font-family:var\(--hebrew\);font-size:1\.1\d?em", shell_css)
    # a book's chapter is tagged before its pages are measured
    assert "Shell.tagLanguages(chapter)" in _read(STATIC / "js" / "reader.js")


def test_reading_lines_stay_near_66_characters():
    # chat replies: max-width in ch of Public Sans; 54ch measured at about 68 characters (Group G, G2)
    width = float(re.search(r"\.prose\{[^}]*max-width:([\d.]+)ch", _read(CSS / "chat.css")).group(1))
    assert 45 <= width <= 58, width
    assert re.search(r"--col:\s*6[0-9]ch", _read(CSS / "prose.css"))   # the built pages' column
