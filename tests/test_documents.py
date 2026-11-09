"""Documents, PDFs and books (Group H of the exegetica-design skill): the Prep Room's printed document follows
the locked print rules, the offline PDF builders use Exegetica's own fonts with Greek and Hebrew, and the
credit line is a choice at download. No network, no browser."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "webapp" / "static"
sys.path.insert(0, str(ROOT / "scripts"))

import print_fonts  # noqa: E402  (scripts/print_fonts.py)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_the_builders_tag_greek_and_hebrew_like_the_pages():
    html = ('<p>The Word <em>λόγος</em> and Genesis 1:1, '
            'בְּרֵאשִׁית בָּרָא, '
            '<code>λ</code> <a title="αρχή">x</a></p><style>.a{content:"λ"}</style>')
    out = print_fonts.tag_languages(html)
    assert '<span lang="grc" class="orig">λόγος</span>' in out
    assert '<span lang="he" dir="rtl" class="orig">בְּ' in out and "א</span>," in out
    assert "<code>λ</code>" in out and 'title="αρχή"' in out and 'content:"λ"' in out
    assert print_fonts.tag_languages(out) == out   # tagging twice changes nothing


def test_the_builders_embed_our_own_fonts():
    css = print_fonts.embedded(("reader", "orig"), ("EB Garamond", "Exegetica Hebrew"))
    assert "data:font/woff2;base64," in css and not re.search(r"url\(\s*['\"]?https?://", css)
    faces = set(re.findall(r"font-family: '([^']+)'", css))
    assert faces == {"EB Garamond", "Exegetica Hebrew"}, faces
    for builder in ("course_pdf.py", "book_pdf.py"):
        src = _read(ROOT / "scripts" / builder)
        assert "from print_fonts import" in src and "tag_languages(" in src and "embedded(" in src, builder
        assert "fonts.googleapis.com" not in src, builder   # a render fetches nothing (rule H11)


def test_the_prep_room_prints_by_the_locked_rules():
    css = _read(STATIC / "css" / "generate.css")
    printed = re.search(r"@media print\{.*?\n\}", css, re.S).group(0)
    assert "font-family:var(--doc)" in printed and "font-size:12pt" in printed   # EB Garamond, a book face
    assert re.search(r"@page\{size:letter;margin:[\d.]+in 2in", printed)        # near 70 characters a line
    assert "orphans:2;widows:2" in printed
    assert 'data-band="middle"' in printed                                      # grades 6 to 8 print larger
    assert "h2::after" in printed and "margin-bottom:-4.5em" in printed          # headings stay with their text
    assert "border-bottom:.5pt solid" in printed                                 # hairline tables
    assert re.search(r'--doc:"EB Garamond"', _read(STATIC / "css" / "tokens.css"))
    page = _read(STATIC.parent / "templates" / "generate.html")
    assert '<link rel="stylesheet" href="/static/fonts/doc.css">' in page and 'id="credit"' in page
    js = _read(STATIC / "js" / "generate.js")
    assert "function setPrintHead()" in js and "counter(page)" in js and "Teacher copy" in js and "Student copy" in js
    assert "printReady().then(()=>window.print())" in js   # the print waits for its faces


def test_the_credit_line_is_a_choice_at_download():
    js = _read(STATIC / "js" / "generate.js")
    assert "new Blob([withCredit(shown())]" in js          # the .md download
    assert 'p.className="credit"' in js                     # the document, and so the PDF
    assert "exeg-credit" in js                               # the teacher's choice is remembered
    copy = re.search(r'\$\("copy"\)\.addEventListener\([^\n]*', js).group(0)
    assert "withCredit" not in copy                          # Copy stays the document alone


def test_tables_come_from_the_shell():
    # rule J2: one table for chat and the Prep Room, numbers right-aligned, scrolling in a reachable region
    shell_js = _read(STATIC / "js" / "shell.js")
    assert "function table(head, rows, inline)" in shell_js and "table: table" in shell_js
    assert "role='region' tabindex='0' aria-label=" in shell_js and "scope='col'" in shell_js
    for page in ("chat.js", "generate.js"):
        js = _read(STATIC / "js" / page)
        assert "Shell.table(" in js and "<div class='tablewrap'>" not in js, page
    assert "td.num{text-align:right;font-variant-numeric:tabular-nums}" in _read(STATIC / "css" / "chat.css")
    # on a phone: references never break, five columns or more become labelled cards, and a shade shows hidden columns
    assert "head.length >= 5" in shell_js and "data-label=" in shell_js and 'role("cell")' in shell_js
    assert "function fitTables(root)" in shell_js and "more-right" in shell_js
    shell_css = _read(STATIC / "css" / "shell.css")
    assert ".tablewrap .nobr{white-space:nowrap}" in shell_css
    phone = re.search(r"@media screen and \(max-width:560px\)\{.*?\n\}", shell_css, re.S).group(0)
    assert "table.stack" in phone and "attr(data-label)" in phone
    assert ".tablebox.more-left::before,.tablebox.more-right::after{opacity:1}" in shell_css
    # the Prep Room's paper and column may shrink below a wide table, so the table scrolls and the page never does
    gen_css = _read(STATIC / "css" / "generate.css")
    assert re.search(r"\.paper\{[^}]*min-width:0", gen_css)
    assert "1fr;" not in re.sub(r"minmax\(0,1fr\)", "", re.search(r"\n\.app\{[^}]*\}", gen_css).group(0))
    narrow = re.search(r"@media\(max-width:900px\)\{.*?\n\}", gen_css, re.S).group(0)
    assert ".app{grid-template-columns:minmax(0,1fr)" in narrow
