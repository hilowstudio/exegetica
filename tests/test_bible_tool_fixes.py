"""Cross-references without a source to pick, ACAI records tied to the right name entry, and
confession proofs that answer in one pass (src/studybible_mcp). The database cases read
db/study_bible.db and skip where it is absent. No network."""
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
async def test_the_proof_outline_is_in_document_order(db):
    outline = await db.confession_proof_outline("wlc")
    assert [o["section_label"] for o in outline[:3]] == ["Q1", "Q2", "Q3"]
    assert sum(o["n"] for o in outline) == 2568
