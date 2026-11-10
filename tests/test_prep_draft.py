"""Drafting in the Prep Room (webapp/prep_draft.py, prep_catalog.py, generator.build_unit_task): what a
draft is told, how sources are gathered, the student copy, and reading uploads and links. No network,
no model."""
import asyncio
import io
import zipfile

from webapp import filetext, generator, prep_catalog, prep_draft, yorkville

DOC = """# Quiz: John 7

Name: ________

1. Where did Jesus teach during the feast?

**Standards:** BIB.10.2.1

---

## Teaching Notes

Point students back to Deuteronomy 16.

### Pacing (Teacher)

Ten minutes.

## Answer Key

1. In the temple courts.
"""


def test_the_student_copy_drops_every_teacher_section_and_the_standards_line():
    out = prep_catalog.student_copy(DOC)
    assert "Where did Jesus teach" in out
    for gone in ("Teaching Notes", "Deuteronomy", "Pacing", "Ten minutes", "Answer Key", "temple courts",
                 "Standards"):
        assert gone not in out, gone
    assert not out.rstrip().endswith("---")


def test_a_teacher_section_above_the_key_no_longer_reaches_students():
    doc = "# Guide\n\n## Notes for the teacher\n\nSpoiler.\n\n## Questions\n\n1. Why?\n"
    out = prep_catalog.student_copy(doc)
    assert "Spoiler" not in out and "1. Why?" in out
    assert prep_catalog.has_teacher_part(doc) and not prep_catalog.has_teacher_part(out)


def test_devotional_variants_are_withheld():
    """Decision 0010: no AI-written prayers or devotions for anyone to follow."""
    ids = {v["id"] for kinds in prep_catalog.gallery()["groups"] for k in kinds["kinds"] for v in k["variants"]}
    assert not ids & prep_catalog.WITHHELD_VARIANTS
    assert prep_catalog.variant_instruction("reflection_journal", "prayer_journal") == ""
    assert prep_catalog.variant_instruction("quiz", "pop_quiz") == "Variant: Pop quiz."


def test_every_kind_is_in_exactly_one_group_of_the_gallery():
    ids = [k["id"] for g in prep_catalog.gallery()["groups"] for k in g["kinds"]]
    assert sorted(ids) == sorted(generator.FORMATS)


def _unit():
    return {"title": "John 7 and 8", "grade_band": "secondary", "course_name": "Bible II",
            "notes": "Period 3 reads aloud.",
            "objectives": [{"id": "BIB.10.2.1", "t": "Explain the Feast of Booths", "g": 10, "c": 2,
                            "a": {"scripture": ["Leviticus 23:33-43"], "standards": ["ACSI 4.1"]}}]}


def test_a_unit_draft_carries_its_note_objectives_anchors_and_teacher_sections():
    task = generator.build_unit_task("quiz", settings={"variant": "pop_quiz", "item_types": ["short_answer"],
                                                       "length": "short", "brief": "Ten items."},
                                     unit=_unit(), materials=[{"type": "passage", "ref": "John 7:14-24"}])
    for want in ('for the unit "John 7 and 8"', "Variant: Pop quiz", "short answer", "about one page",
                 "Course: Bible II", "Period 3 reads aloud", "Leviticus 23:33-43", "ACSI 4.1",
                 "Ten items.", "PASSAGE: John 7:14-24", "## Answer Key", "(Teacher)",
                 "Standards: BIB.10.2.1"):
        assert want in task, want


def test_an_outline_is_given_as_an_outline_and_never_as_the_book():
    m = {"type": "outline", "work": {"title": "Reveal Math, Course 2", "authors": [], "publisher": "McGraw Hill",
                                     "edition": "2020", "summary": "Grade 7 math."},
         "entries": [{"label": "Module 3", "title": "Solve Problems Involving Percents",
                      "covers": "percent change and markups", "children": [{"label": "3-1", "title": "Percent of Change"}]}]}
    task = generator.build_unit_task("worksheet", settings={}, unit=None, materials=[m])
    assert "OUTLINE ONLY" in task and "Do not quote the book" in task and "[From the textbook:" in task
    assert "- Module 3 Solve Problems Involving Percents: percent change and markups" in task
    assert "  - 3-1 Percent of Change" in task


def test_gathering_keeps_the_teachers_order_and_says_what_was_skipped(monkeypatch):
    monkeypatch.setattr(yorkville, "outline_material",
                        lambda key, parts=None: {"type": "outline", "work": {"title": "T"}, "entries": []}
                        if key == "known" else None)
    sources = [
        {"kind": "upload", "label": "Booths handout.docx", "ref": {}, "text": "The feast of booths " * 10},
        {"kind": "outline", "label": "Missing outline", "ref": {"key": "gone"}},
        {"kind": "passage", "label": "John 7:37-39", "ref": {"ref": "John 7:37-39"}},
        {"kind": "outline", "label": "Known outline", "ref": {"key": "known"}},
    ]
    materials, drew_on, notices = asyncio.run(prep_draft.gather(None, sources, "quiz"))
    assert [m["type"] for m in materials] == ["document", "passage", "outline"]
    assert drew_on == ["Booths handout.docx", "John 7:37-39", "Known outline"]
    assert notices and "Missing outline" in notices[0]


def test_a_word_document_is_read():
    body = ('<w:document xmlns:w="w"><w:body><w:p><w:r><w:t>The Feast</w:t></w:r><w:r><w:tab/>'
            '<w:t xml:space="preserve"> of Booths &amp; John 7</w:t></w:r></w:p><w:p><w:r><w:t>Second</w:t>'
            '</w:r></w:p></w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", body)
    assert filetext.extract_text(buf.getvalue(), "docx") == "The Feast\t of Booths & John 7\n\nSecond"


def test_a_web_page_keeps_its_article_and_drops_the_chrome():
    page = ("<html><head><title>Site</title><meta property='og:title' content='Booths in John'></head><body>"
            "<nav>Home About</nav><header>Logo</header><article><h1>Booths</h1><p>Jesus went up "
            "secretly.</p><script>x()</script><aside>Ad</aside></article><footer>(c)</footer></body></html>")
    title, text = prep_draft.readable(page)
    assert title == "Booths in John"
    assert "Jesus went up secretly." in text and "Home" not in text and "Ad" not in text and "x()" not in text


def test_a_draft_streams_records_its_metrics_row_and_says_when_it_wasnt_saved(monkeypatch):
    """A quick resource with no database: the document streams, the metrics row carries a fixed route label
    (an unknown label once broke the stream before the save), and the page hears it wasn't saved."""
    import json

    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from webapp import auth, citations, db, metrics, providers

    rows = []
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "00000000-0000-0000-0000-000000000002",
                                                               "email": "t@school.test", "role": "teacher"})
    monkeypatch.setattr(auth, "is_teacher", lambda u: True)
    monkeypatch.setattr(db, "ready", lambda: False)
    monkeypatch.setattr(metrics, "record", lambda row: rows.append(row))
    monkeypatch.setattr(citations, "generator_report", lambda *a: {"type": "report", "references": 0, "quotations": 0})

    async def fake_run(provider, api_key, model, system_text, history, mcp, limits=None, stats=None):
        assert "PASSAGE: John 7:37-39" in history[-1]["content"]
        yield {"type": "text", "text": "# Quiz\n\n1. What did Jesus cry out?\n\n## Answer Key\n\n1. Come to me."}
        stats.update(outcome="complete", steps=1, est_usd=0.0)
        yield {"type": "end", "outcome": "complete"}
    monkeypatch.setattr(providers, "run", fake_run)

    app = Starlette(routes=[Route("/api/prep/draft", prep_draft.draft, methods=["POST"])])
    app.state.mcp = None
    body = {"format_id": "quiz", "settings": {"variant": "pop_quiz"},
            "sources": [{"kind": "passage", "ref": {"ref": "John 7:37-39"}, "label": "John 7:37-39"}]}
    r = TestClient(app).post("/api/prep/draft", json=body)
    events = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]
    kinds = [e["type"] for e in events]
    assert kinds[0] == "start" and events[0]["drew_on"] == ["John 7:37-39"]
    assert "text" in kinds and "report" in kinds and kinds[-1] == "done"
    assert any(e["type"] == "notice" and "wasn't saved" in e["message"] for e in events)
    assert rows and rows[0]["route"] == "prep:draft"


def test_a_capped_teacher_gets_the_fixed_line_and_no_model_call(monkeypatch):
    """Decision 0027: past today's Prep Room cap, a draft is the fixed text alone."""
    import json

    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from webapp import auth, db, providers, usage

    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "00000000-0000-0000-0000-000000000002",
                                                               "email": "t@school.test", "role": "teacher"})
    monkeypatch.setattr(auth, "is_teacher", lambda u: True)
    monkeypatch.setattr(db, "ready", lambda: False)

    async def capped(user_id):
        return usage.PREP_CAPPED
    monkeypatch.setattr(usage, "prep_check", capped)

    def no_model(*a, **k):
        raise AssertionError("the model was called")
    monkeypatch.setattr(providers, "run", no_model)
    app = Starlette(routes=[Route("/api/prep/draft", prep_draft.draft, methods=["POST"])])
    app.state.mcp = None
    r = TestClient(app).post("/api/prep/draft", json={"format_id": "quiz", "settings": {}})
    events = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:")]
    assert [e["type"] for e in events] == ["start", "notice", "done"]
    assert events[1]["message"] == usage.PREP_CAPPED and events[1]["incomplete"]


def test_prep_caps_count_apart_from_chat_and_the_school_total_comes_first(monkeypatch):
    import asyncio

    from webapp import db, metrics, usage

    monkeypatch.setattr(db, "ready", lambda: True)
    monkeypatch.setattr(metrics, "missing_tables", set())
    day = usage.today()
    assert usage._prep_key("u1", day) != usage.who("u1", day)
    rows = {}

    async def fetch(sql, d, keys):
        return [{"who": k, "turns": rows[k][0], "est_usd": rows[k][1]} for k in keys if k in rows]
    monkeypatch.setattr(db, "fetch", fetch)
    assert asyncio.run(usage.prep_check("u1")) is None
    rows[usage._prep_key("u1", day)] = (usage.PREP_RUNS, 1.0)
    assert asyncio.run(usage.prep_check("u1")) == usage.PREP_CAPPED
    rows[usage.PREP_ALL] = (40, usage.PREP_ALL_USD)
    assert asyncio.run(usage.prep_check("u1")) == usage.PREP_ALL_CAPPED
