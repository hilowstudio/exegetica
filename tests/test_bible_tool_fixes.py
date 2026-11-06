"""Cross-references without a source to pick, ACAI records tied to the right name entry, and
confession proofs that answer in one pass (src/studybible_mcp). The database cases read
db/study_bible.db and skip where it is absent. No network."""
import unicodedata

import pytest

from studybible_mcp import server as bible
from studybible_mcp.database import StudyBibleDB
from studybible_mcp.server import _proof_sections
from studybible_mcp.tools import TOOLS

DB_PATH = bible.get_db_path()
needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="no study_bible.db here")


def test_cross_references_offer_no_source_to_choose():
    schema = next(t for t in TOOLS if t.name == "get_cross_references").inputSchema
    assert "source" not in schema["properties"]


def test_lookup_name_offers_only_types_that_exist():
    schema = next(t for t in TOOLS if t.name == "lookup_name").inputSchema
    assert schema["properties"]["type"]["enum"] == ["person", "place"]


@pytest.mark.parametrize("section,labels,expected", [
    ("Q1", ["Q1", "Q2", "Q10"], ["Q1"]),
    ("q2", ["Q1", "Q2", "Q10"], ["Q2"]),
    ("1", ["Q1", "Q2", "Q10"], ["Q1"]),                  # a bare number in a catechism
    ("1", ["1.1", "1.2", "10.1"], ["1.1", "1.2"]),         # a chapter of a confession
    ("1.2", ["1.1", "1.2", "10.1"], ["1.2"]),
    ("99", ["1.1", "1.2"], []),
])
def test_a_section_may_be_named_several_ways(section, labels, expected):
    assert _proof_sections(section, labels) == expected


@pytest.fixture
async def db():
    d = StudyBibleDB(DB_PATH)
    await d.connect()
    yield d
    await d.close()


@needs_db
async def test_down_voted_cross_references_are_left_out_by_default(db):
    rows = await db.get_cross_references("John 3:16", limit=500, min_strength=0)
    assert rows and all(r["relevance"] >= 0 for r in rows)


@needs_db
async def test_each_acai_record_goes_to_its_own_entry(db):
    entries = await db.lookup_name("Boaz") + await db.lookup_name("John")
    acai = await db.acai_for_names(entries)
    by_ref = {e["refs"]: acai.get(e["id"], {}).get("id") for e in entries if e["name"] in ("Boaz", "John")}
    assert by_ref['["Rut.2.1"]'] == "person:Boaz"
    assert by_ref['["1Ki.7.21"]'] is None                       # the pillar in the temple
    johns = [v for k, v in by_ref.items() if k not in ('["Rut.2.1"]', '["1Ki.7.21"]')]
    assert len(set(filter(None, johns))) == len(list(filter(None, johns)))   # no John shares a record
    records = list(acai.values())
    assert len({r["id"] for r in records}) == len(records)


@needs_db
async def test_the_occurrence_search_reads_one_book_in_the_original(db, monkeypatch):
    """2026-11-06: "how does John use believe" took one verse lookup per example, and answers cited
    examples from memory. One call now shows John's uses, the Greek around each, and what follows."""
    monkeypatch.setattr(bible, "db", db)
    out = (await bible.handle_search_by_strongs({"strongs": "G4100", "book": "John", "limit": 3}))[0].text
    out = unicodedata.normalize("NFC", out)   # the text writes oxia (ύ U+1F7B), the same letter as tonos
    assert "In John: " in out and "**Jhn.1.12**" in out and "Mat." not in out
    assert "**πιστεύουσιν** [V-PAP-DPM] εἰς τὸ ὄνομα" in out
    assert "The word right after it: εἰς (G1519)" in out
    none = (await bible.handle_search_by_strongs({"strongs": "G4102", "book": "John"}))[0].text
    assert "No verses found with this Strong's number in John" in none   # John never uses the noun "faith"
    assert "Unknown book" in (await bible.handle_search_by_strongs({"strongs": "G4100", "book": "Johnny"}))[0].text


def test_the_occurrence_search_takes_a_book():
    schema = next(t for t in TOOLS if t.name == "search_by_strongs").inputSchema
    assert "book" in schema["properties"]


@needs_db
async def test_the_proof_outline_is_in_document_order(db):
    outline = await db.confession_proof_outline("wlc")
    assert [o["section_label"] for o in outline[:3]] == ["Q1", "Q2", "Q3"]
    assert sum(o["n"] for o in outline) == 2568


# ---------------------------------------------------------------- numbered confessions
@pytest.mark.parametrize("section,expected", [
    ("29", (29, None)), ("29.2", (29, 2)), ("29:2", (29, 2)), ("chapter 29", (29, None)),
    ("ch. 29 para 2", (29, 2)), ("Chapter 29, paragraph 2", (29, 2)), ("Q33", None), ("Of Baptism", None),
])
def test_a_confession_section_may_be_numbered_several_ways(section, expected):
    assert bible._section_numbers(section) == expected


def test_proof_sections_take_the_same_numbering():
    assert _proof_sections("chapter 29 paragraph 2", ["29.1", "29.2"]) == ["29.2"]
    assert _proof_sections("ch. 29", ["28.1", "29.1", "29.2"]) == ["29.1", "29.2"]


@pytest.fixture
def numbered(db, monkeypatch):
    monkeypatch.setattr(bible, "db", db)
    monkeypatch.setattr(bible, "_outlines", {})
    return bible


@needs_db
async def test_the_1689_names_a_paragraph_by_its_true_number(numbered):
    # The tool once printed this paragraph with a stray "4" and no chapter, and models cited it as 29.4.
    out = (await numbered.handle_get_confession({"document": "1689 London Baptist Confession", "section": "29.2"}))[0].text
    assert "Chapter 29: Of Baptism" in out and "**29.2** Those who do actually profess" in out
    assert "Proof texts: Mrk 16:16" in out


@needs_db
async def test_a_chapter_title_names_that_chapter_alone(numbered):
    out = (await numbered.handle_get_confession({"document": "London Baptist Confession of Faith",
                                                 "section": "Of Baptism"}))[0].text
    assert "Chapter 29: Of Baptism" in out and "Lord's Supper" not in out
    assert "newness of life. 3" not in out                      # the source's footnote counter is gone


@needs_db
async def test_westminster_takes_a_chapter_and_paragraph_number(numbered):
    # The tool once answered "No section '25.6' found", and the model cited 25.5 from memory.
    out = (await numbered.handle_get_confession({"document": "Westminster Confession", "section": "25.6"}))[0].text
    assert "Chapter 25: Of the Church" in out and "**25.6** The Lord Jesus Christ is the only head" in out


@needs_db
async def test_every_numbered_paragraph_agrees_with_the_proof_index(numbered):
    parted = set()
    for doc, chapters in (("london-baptist-1689", 32), ("westminster-confession", 33)):
        outline = await numbered._confession_outline(doc)
        unnumbered = [ch["title"] for ch in outline if ch["num"] is None]
        assert unnumbered == (["Of the Holy Spirit"] if doc == "westminster-confession" else [])
        assert [ch["num"] for ch in outline if ch["num"]] == list(range(1, chapters + 1))
        parted |= {(doc, ch["num"]) for ch in outline for p in ch["paras"]
                   if p["indexed"] and p["indexed"] != f"{ch['num']}.{p['num']}"}
    assert parted <= {("westminster-confession", 31)}   # this edition's chapter 31 has four paragraphs


@needs_db
async def test_a_topic_search_numbers_its_confession_hits(numbered):
    out = (await numbered.handle_get_confession({"topic": "only proper subjects"}))[0].text
    assert "London Baptist Confession of Faith 29.2 (Of Baptism)" in out


@needs_db
@pytest.mark.parametrize("name,doc_id", [
    ("1689", "london-baptist-1689"), ("1689 London Baptist Confession", "london-baptist-1689"),
    ("Second London Baptist Confession", "london-baptist-1689"), ("WCF", "westminster-confession"),
    ("Westminster Shorter Catechism", "westminster-shorter-catechism"), ("Apostles Creed", "apostles-creed"),
])
async def test_common_names_find_their_document(numbered, name, doc_id):
    assert await numbered._find_document(name) == doc_id
