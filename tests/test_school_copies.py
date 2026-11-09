"""School-provided copies (2026-11-09): books Yorkville Christian provides for its own accounts are in copyright, so
they are listed and opened only for a signed-in school account, a teacher or an admin; everyone else never sees
them, and their address answers "not found". The files never enter git. No network."""
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def books_db(tmp_path, monkeypatch):
    db = tmp_path / "books.db"
    con = sqlite3.connect(db)
    con.executescript("""
        create table books (id integer primary key, slug text, title text, author text, author_sort text, source text,
          license text, us_clear integer, language text, subjects text, chapter_count integer, word_count integer,
          genres text, section text, cover_url text, front_html text, access text);
        create table book_chapters (book_id integer, section_number integer, title text, html text, words integer);
    """)
    for i, (slug, access) in enumerate((("public-book", None), ("school-book", "school")), 1):
        con.execute("insert into books values (?,?,?,?,?,?,?,0,'en','[]',1,10,'[\"Christianity\"]','[\"Christianity\"]',"
                    "null,null,?)", (i, slug, slug.title(), "An Author", "Author, An", "x", "x", access))
        con.execute("insert into book_chapters values (?,1,'One','<h2>One</h2><p>Text of the chapter.</p>',5)", (i,))
    con.commit(); con.close()
    from webapp import reader
    monkeypatch.setattr(reader, "_db_path", lambda: str(db))
    return reader


def test_only_school_accounts_teachers_and_admins_may_read(books_db):
    r = books_db
    assert r.may_read_school({"email": "a.student@yorkvillechristian.com"})
    assert not r.may_read_school({"email": "someone@gmail.com"})
    assert not r.may_read_school(None)


def test_a_school_copy_is_hidden_from_everyone_else(books_db):
    r = books_db
    slugs = lambda d: [i["slug"] for i in d["items"]]
    assert slugs(r._catalog_sync(False)) == ["public-book"]
    assert set(slugs(r._catalog_sync(True))) == {"public-book", "school-book"}
    assert [i for i in r._catalog_sync(True)["items"] if i["slug"] == "school-book"][0]["school"] is True
    assert slugs(r._list_sync("School", 10, 0, False)) == [] and slugs(r._list_sync("School", 10, 0, True)) == ["school-book"]
    shelves = r._shelves_sync(False)["shelves"]
    assert all(b["slug"] != "school-book" for s in shelves for b in s["books"])
    assert r._book_sync("school-book", False) is None and r._book_sync("school-book", True)
    assert r._chapter_sync("school-book", 1, False) is None and r._chapter_sync("school-book", 1, True)
    assert r._book_sync("public-book", False)                     # everything else is unchanged


def test_the_handlers_ask_who_is_reading():
    src = (ROOT / "webapp" / "reader.py").read_text(encoding="utf-8")
    for fn in ("_list_sync, q, limit, offset, reader_level", "_shelves_sync, reader_level", "_catalog_sync, reader_level",
               "_book_sync, request.path_params[\"slug\"], reader_level", "_chapter_sync, request.path_params[\"slug\"], n,"):
        assert fn in src, fn


def test_the_copies_stay_out_of_git():
    assert "/book-copies/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".seed_cache/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.pdf" in (ROOT / ".dockerignore").read_text(encoding="utf-8")


def _ingest():
    spec = importlib.util.spec_from_file_location("ingest_school_copy", ROOT / "scripts" / "ingest_school_copy.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_work_files_become_plain_chapter_html():
    m = _ingest()
    work = "\n".join([
        "<!-- a book -->", "## Chapter One", "<!-- p16 -->", "",
        "The first paragraph ends here.2", "", "> The kingdom of heaven is like treasure.", "[sig] —Matthew 13:44", "",
        "### A Subhead", "", "Another paragraph.", "", "## Chapter Two", "", "Text."])
    ch = m._chapters_from_work(work)
    assert [c["title"] for c in ch] == ["Chapter One", "Chapter Two"]
    h = ch[0]["html"]
    assert h.startswith('<h2 class="ex-keep">Chapter One</h2>') and "<!--" not in h
    assert "<blockquote><p>The kingdom of heaven is like treasure.</p></blockquote>" in h
    assert '<p class="ex-cite">—Matthew 13:44</p>' in h
    assert "here.<sup>2</sup>" in h and "<h3>A Subhead</h3>" in h


def test_line_end_hyphens_rejoin_words_and_keep_compounds():
    m = _ingest()
    import collections
    vocab = collections.Counter({"responsibility": 2})
    L = lambda *ts: [{"t": t} for t in ts]
    assert m._join_lines(L("great respon-", "sibility here"), vocab) == "great responsibility here"
    m._COMMON = {"all", "powerful"}
    assert m._join_lines(L("the all-", "powerful God"), collections.Counter()) == "the all-powerful God"


def test_running_heads_and_scan_footers_are_furniture():
    m = _ingest()
    head = lambda t, y=0.05: {"t": t, "y0": y, "y1": y + 0.01}
    assert m._is_furniture(head("18 / Be Daring"), "be daring")
    assert m._is_furniture(head("Excitement in Ephesus / 19"), "be daring")
    assert m._is_furniture(head("19", 0.95), "")
    assert m._is_furniture(head("https://archive.org/details/x", 0.5), "")
    assert not m._is_furniture(head("A sentence in the middle of the page.", 0.5), "be daring")


def test_a_chapter_really_titled_chapter_one_keeps_its_heading():
    # the house pass blanks "Chapter One" as an importer's placeholder; a school copy marks its headings as its own
    from webapp import typeset as T
    body = "<p>" + "A sentence of the chapter. " * 8 + "</p>"
    assert T.typeset('<h2 class="ex-keep">Chapter Three</h2>' + body, "Chapter Three")[1:] == ("", "Chapter Three")
    assert T.typeset("<h2>Chapter Three</h2>" + body, "Chapter Three")[1:] == ("", "")    # every other book unchanged


def test_the_reader_styles_a_body_attribution():
    css = (ROOT / "webapp" / "static" / "css" / "reader.css").read_text(encoding="utf-8")
    assert ".chapter p.ex-cite:not(.ex-epi){text-align:right" in css


def test_quotation_marks_pair_up_within_a_paragraph():
    m = _ingest()
    # a conversion from a scan sets marks the wrong way round and spaces them wrongly
    assert m._requote('“Remember that you’re a duke’s son, ”Jessica said. ”Go.“') == \
        '“Remember that you’re a duke’s son,” Jessica said. “Go.”'
    assert m._requote('He said, "Come here"') == 'He said, “Come here”'


def test_a_one_word_first_paragraph_is_text_not_a_label():
    m = _ingest()
    assert not m._epub_label("Hagrid?”", "fallen warrior")
    assert m._epub_label("CHAPTER FIVE", "fallen warrior")
    assert m._epub_label("TWENTY-ONE", "twentyone")
    assert m._epub_label("= = = = = =", "chapter 6")
    assert m._epub_label("THE TRIBUTES", "part i the tributes")


def test_shifted_text_codes_are_not_taken_for_spaces():
    m = _ingest()
    assert m._space(" ") and m._space("\n")
    assert not m._space("\x1c")          # a font that shifts its codes sets 9 here


def test_an_epigraph_reaches_the_front_page(tmp_path):
    m = _ingest()
    db = tmp_path / "books.db"
    con = sqlite3.connect(db)
    con.executescript("""
        create table books (id integer primary key autoincrement, slug text, title text, author text, author_sort text,
          source text, license text, us_clear integer, language text, subjects text, genres text, section text,
          genres_backup text, title_backup text, cover_url text, chapter_count integer, word_count integer,
          access text, front_html text, added_at text);
        create table book_chapters (book_id integer, section_number integer, title text, html text, words integer);
    """)
    con.close()
    d = tmp_path / "a-book"
    d.mkdir()
    (d / "book.json").write_text(json.dumps({
        "slug": "a-book", "title": "A Book", "author": "An Author", "rights": "© 2000 An Author",
        "dedication": "For you", "epigraphs": [{"lines": ["One line,", "and another."], "cite": "A Poet"}]}),
        encoding="utf-8")
    (d / "work.md").write_text("## One\n\nThe text of the chapter.\n", encoding="utf-8")
    m.CACHE = tmp_path
    import types
    m.cmd_load(types.SimpleNamespace(slug="a-book", db=str(db)))
    front = sqlite3.connect(db).execute("select front_html from books").fetchone()[0]
    assert 'class="ex-dedication"' in front and 'class="ex-epigraph"' in front
    assert "<span>One line,</span><span>and another.</span>" in front and "<cite>A Poet</cite>" in front


def test_a_reference_copy_is_for_teachers_and_never_shelved(books_db, monkeypatch):
    r = books_db
    import sqlite3 as _s
    con = _s.connect(r._db_path())
    con.execute("insert into books values (3,'a-textbook','A Textbook','An Author','Author, An','x','x',0,'en','[]',1,"
                "10,'[\"Science & Nature\"]','[\"Science & Nature\"]',null,null,'reference')")
    con.execute("insert into book_chapters values (3,1,'One','<h2>One</h2><p>Text.</p>',1)")
    con.commit(); con.close()
    slugs = lambda d: {b["slug"] for b in d["items"]}
    assert "a-textbook" in slugs(r._list_sync("Textbook", 10, 0, 2))           # the Prep Room's search, a teacher
    assert "a-textbook" not in slugs(r._list_sync("Textbook", 10, 0, 1))       # a student
    assert all(b["slug"] != "a-textbook" for s in r._shelves_sync(2)["shelves"] for b in s["books"])
    assert all(b["slug"] != "a-textbook" for b in r._catalog_sync(2)["items"])
    assert r._book_sync("a-textbook", 2) and r._book_sync("a-textbook", 1) is None
    assert r._gen_book_sync("a-textbook")["chapters"]


def test_a_transcribed_textbook_keeps_its_maths_tables_and_lists():
    m = _ingest()
    work = ("## Polynomials\n\n**Key Concept** Let \\(p(x) = x^4 - 7x\\) and \\(m > n\\).\n\n"
            "\\[\nx^2 - 1 = (x - 1)(x + 1)\n\\]\n\n| Notation | Meaning |\n|---|---|\n| \\(y = \\sin^{-1} x\\) | angle |\n\n"
            "- first point\n- second point\n\n[Figure: a cube with side \\(x - 5\\).]\n")
    html = m._chapters_from_work(work, rich=True)[0]["html"]
    assert "<strong>Key Concept</strong>" in html
    assert "\\(p(x) = x^4 - 7x\\)" in html and "\\(m &gt; n\\)" in html      # TeX untouched (KaTeX reads the text)
    assert "<p>\\[ x^2 - 1 = (x - 1)(x + 1) \\]</p>" in html
    assert "<th>Notation</th>" in html and "<td>\\(y = \\sin^{-1} x\\)</td>" in html
    assert "<ul><li>first point</li><li>second point</li></ul>" in html
    assert 'class="ex-figure"' in html
    plain = m._chapters_from_work("## One\n\n* * *\n\n**not bold** here\n")[0]["html"]   # a novel: none of that
    assert "<ul>" not in plain and "<strong>" not in plain
