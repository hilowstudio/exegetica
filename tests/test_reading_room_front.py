"""The Reading Room as redesigned on 2026-11-09 (exegetica-design skill): a front table above the whole library
(the reader's books in hand, then two shelves worth starting with), a laptop that gets the two-page spread, a
book that never opens on a blank page, and a top bar that names the book open. No network, no browser."""
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "webapp" / "static" / "js" / "reader.js").read_text(encoding="utf-8")
CSS = (ROOT / "webapp" / "static" / "css" / "reader.css").read_text(encoding="utf-8")
HTML = (ROOT / "webapp" / "templates" / "reader.html").read_text(encoding="utf-8")
PY = (ROOT / "webapp" / "reader.py").read_text(encoding="utf-8")


def _front_slugs():
    block = JS[JS.index("var FRONT = ["):JS.index("function frontRow(")]
    return re.findall(r'"([a-z0-9][a-z0-9_-]+_[a-z0-9_-]+|ccel-[a-z0-9_-]+)"', block)


def test_the_front_table_sits_above_the_whole_library_and_steps_aside_for_a_search():
    results = HTML[HTML.index('<div class="results">'):]
    assert results.index('id="front"') < results.index('id="grid"')
    assert "box.hidden = !!(state.q || state.section || state.length || state.reading);" in JS
    assert "buildFacets(); renderFront();" in JS                      # redrawn on every search or filter
    assert '"The whole library"' in JS


def test_continue_reading_leads_with_the_book_read_last():
    assert '"updated": {r["book_slug"]: r["at"] for r in rows}' in PY
    assert "updated = (res[1] && res[1].updated) || {};" in JS
    assert "(updated[b.slug] || 0) - (updated[a.slug] || 0)" in JS
    assert '"Chapter " + n + " of " + of' in JS


def test_the_curated_shelves_name_real_books():
    slugs = _front_slugs()
    assert len(slugs) == 24
    db = ROOT / "db" / "books.db"
    if not db.exists():
        pytest.skip("books.db is not in this checkout")
    con = sqlite3.connect(db)
    try:
        missing = [s for s in slugs if not con.execute("select 1 from books where slug=?", (s,)).fetchone()]
    finally:
        con.close()
    assert not missing, missing


def test_every_cover_in_the_browse_view_flips_and_restyles():
    assert '$("grid").addEventListener(' not in JS                    # handlers serve the front table's tiles too
    assert JS.count('$("browse").addEventListener(') >= 5
    assert 'querySelectorAll("#grid .cover")' not in JS


def test_the_rows_scroll_by_mouse_touch_and_keyboard():
    assert 'class="fr-prev" aria-label="Earlier books in' in JS and 'class="fr-next" aria-label="More books in' in JS
    assert 'row.setAttribute("role", "list")' in JS and 'cell.setAttribute("role", "listitem")' in JS
    assert ".fr-books{display:grid;grid-auto-flow:column" in CSS and "overflow-x:auto" in CSS


def test_a_book_never_opens_on_a_blank_page():
    assert 'class="fm-page fm-blank" aria-hidden="true"' in JS
    assert 'chapter.classList.toggle("one-up", cols === 1);' in JS
    assert "#chapter.one-up .fm-blank{display:none}" in CSS
    # the class is set before the pages are measured
    p = JS[JS.index("function paginate(){"):]
    assert p.index('classList.toggle("one-up"') < p.index("stride = chapter.clientWidth")


def test_a_laptop_gets_the_two_page_spread():
    assert "@media (min-width:821px){ .tb-toc{display:none} }" not in CSS   # the contents toggle shows on every screen
    assert 'aria-controls="toc" aria-expanded="false"' in HTML
    assert 'lsGet("exeg-toc")' in JS and 'lsSet("exeg-toc"' in JS
    assert '$("stage").clientWidth - 2 * 66 - 76 < 2 * 420' in JS
    assert ".toc.hidden{visibility:hidden;" in CSS                     # a closed panel takes no focus
    assert 'e.propertyName === "margin-left"' in JS                    # measured after the panel slides


def test_the_top_bar_names_the_book_and_chapter():
    assert '<span class="tb-book">' in JS and '<span class="tb-ch">' in JS
    assert ".tb-title .tb-ch::before" in CSS
