"""One text, many views (the cohesion work of 2026-11-09): every surface hands a Scripture reference to the shared
passage panel, and a teacher can send what they find into a Prep Room unit from wherever they find it."""
import pathlib
import re

from webapp import prep

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = ROOT / "webapp" / "static" / "js"


def read(name):
    return (JS / name).read_text(encoding="utf-8")


def test_the_reading_room_links_references_before_it_measures_pages():
    js = read("reader.js")
    link, measure = js.index("Passage.linkRefs(chapter)"), js.index("typesetMath(chapter, c.html).then")
    assert js.index("Shell.tagLanguages(chapter)") < link < measure
    assert 'e.target.closest(".passage,dialog")' in js        # page-turn keys leave the panel's scrolling alone
    css = (ROOT / "webapp" / "static" / "css" / "reader.css").read_text(encoding="utf-8")
    assert ".chapter a.ref{color:inherit;" in css             # a book's references are marked quietly (rule B10)
    # tabbing to a reference on another page turns the book there, and undoes the browser's scroll of the frame
    focus = js[js.index('chapter.addEventListener("focusin"'):]
    assert "pageport.scrollLeft = 0" in focus[:600] and "goToPage(p, false)" in focus[:600]


def test_a_title_stays_a_title_and_course_pages_keep_their_link_colour():
    assert ",h1," in re.search(r'var SKIP = "([^"]+)"', read("passage.js")).group(0)
    course = (ROOT / "webapp" / "static" / "course.css").read_text(encoding="utf-8")
    assert ".doc a.ref { color: var(--navy-700);" in course   # always light, whatever the device's theme


def test_the_prep_room_links_its_documents_and_knows_the_open_unit():
    js = read("generate.js")
    render = js[js.index("function render(){"):js.index("function printReady(){")]
    assert "Passage.linkRefs(paper)" in render
    assert "Passage.currentUnit=" in js and 'addEventListener("prep:sources-changed"' in js
    assert 'e.key==="Escape"&&!e.defaultPrevented' in js     # Escape closes the panel before the Make panel
    label = js[js.index("function sourceLabel(s){"):js.index("function renderUnit(){")]
    assert 'class="s-label s-open ref"' in label and "href=\"/read/'+encodeURIComponent(r.slug)" in label


def test_scripture_memory_asks_and_opens_by_address_without_adding_on_its_own():
    js = read("memory.js")
    assert '$("t-ask").onclick=function(){ Passage.ask(v.reference); }' in js
    addr = js[js.index("function openFromAddress(){"):js.index("function newVerse(ref, folderId){")]
    assert 'q.get("verse")' in addr and "ui.offer=ref" in addr and "db.verses.push" not in addr
    assert "history.replaceState(null" in addr
    assert "if(phone && phone.matches) setDrawerOpen(false);" in addr      # the list doesn't cover the verse asked for


def test_the_living_library_sends_items_moments_and_class_texts_to_a_unit():
    lib, moments, shelves, reader = read("library.js"), read("library_moments.js"), read("shelves.js"), read("reader.js")
    assert "function _unitBtn(it)" in lib and lib.count("_unitBtn(it)+_rmBtn(it)") == 2 and "_unitBtn(it)+'<div id=\"extract-out\"" in lib
    assert 'e.key==="Escape"&&!e.defaultPrevented' in lib
    assert 'Passage.addToUnit({kind:"library",ref:{item_id:M.item.id,excerpts:[id]}' in moments
    assert 'place:{kind:"video",ref:{item_id:M.item.id,start:x.start' in moments   # a video's moment can go on a class shelf
    # a class's book from its top bar, and a book known only by its outline from the outline (decision 0029)
    assert 'kind: "book", ref: {slug: book.slug, coverage: {}}' in reader
    assert 'kind: "outline", ref: {key: w.outline, parts: []}' in shelves


def test_saving_a_moment_reads_its_own_fields():
    # a local named q once hid the q() helper, so "Save moment" threw before it sent anything
    moments = read("library_moments.js")
    save = moments[moments.index("function save(ev){"):moments.index("function remove(id){")]
    assert not re.search(r"\bq\s*=\s*q\(", save)


def test_course_documents_are_marked_as_holding_scripture():
    views = (ROOT / "webapp" / "course_views.py").read_text(encoding="utf-8")
    assert views.count('<article class="doc" data-scripture>') == 2
    assert "querySelectorAll(\"[data-scripture]\")" in read("passage.js")


def test_a_second_add_of_a_moment_joins_the_item_already_in_the_unit():
    item = "0b6c5c1e-8f4a-4d7e-9d1a-3c2b1a0f9e8d"
    a, b = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
    assert prep.merged_excerpts({"item_id": item, "excerpts": [a]}, {"item_id": item, "excerpts": [b]}) == \
        {"item_id": item, "excerpts": [a, b]}
    assert prep.merged_excerpts({"item_id": item, "excerpts": [a]}, {"item_id": item, "excerpts": [a]}) is None
    assert prep.merged_excerpts({"item_id": item}, {"item_id": item, "excerpts": [a]}) is None     # the whole item is there
    assert prep.merged_excerpts({"item_id": item, "excerpts": [a]}, {"item_id": item}) == {"item_id": item}
    assert set(prep.SAME_SOURCE) == {"book", "outline", "passage", "library", "link", "upload"}
    assert prep.SAME_SOURCE["upload"] == "shelf"     # an upload from a shelf is held once; a file uploaded to the unit may repeat
    assert "shelf" not in prep.clean_ref("upload", {"filename": "a.docx", "format": "docx"})


def test_add_to_a_unit_is_a_save_to_list_in_the_house_menu():
    js = read("passage.js")
    assert "role='menuitemcheckbox'" in js and '"?kind=" + encodeURIComponent(hk.kind)' in js
    assert 'menu.className = "shell-menu"' in js and "icons: {memory: TO_MEMORY, chat: TO_CHAT, prep: TO_PREP, save: SAVE}" in js
    assert "<div class='shell-menu-lab'>Class shelves</div>" in js and "menu: smallMenu" in js   # one menu card for every menu
    shell = (ROOT / "webapp" / "static" / "css" / "shell.css").read_text(encoding="utf-8")
    # the same card the Prep Room and Scripture Memory draw for their menus (rule F10)
    assert ".shell-menu{position:fixed" in shell and "box-shadow:0 8px 26px rgba(0,0,0,.14)" in shell
    assert ".pg-menu" not in shell and ".sm-box{border:1.5px solid var(--ink-faint)" in shell   # a box people can see (1.4.11)
