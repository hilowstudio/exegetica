"""Hebrew Strong's searches, word lookups and Septuagint psalm numbering. The pure helpers run anywhere.
The database cases read db/study_bible.db and skip where it is absent. No network."""
import pytest

from studybible_mcp import server as bible
from studybible_mcp.database import StudyBibleDB, base_strongs, fold_transliteration
from studybible_mcp.parsers.tagged_text import parse_hebrew_word

DB_PATH = bible.get_db_path()
needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="no study_bible.db here")


def test_strongs_numbers_normalize_and_drop_sense_letters():
    assert StudyBibleDB._normalize_strongs("h430") == "H0430"
    assert StudyBibleDB._normalize_strongs("G26") == "G0026"
    assert StudyBibleDB._normalize_strongs("h1254a") == "H1254A"
    assert base_strongs("H3068G") == "H3068"
    assert base_strongs("H3068") == "H3068"
    assert base_strongs("AS_Βελίαλ") == "AS_Βελίαλ"


@pytest.mark.parametrize("spelling,language,folded", [
    ("agapē", "greek", "agape"),
    ("dikaiosyne", "greek", "dikaiosune"),
    ("checed", "hebrew", "hesed"),
    ("chesed", "hebrew", "hesed"),
    ("ḥesed", "hebrew", "hesed"),
    ("kabowd", "hebrew", "kabod"),
    ("tzedek", "hebrew", "tsedek"),
])
def test_transliterations_fold_to_a_common_spelling(spelling, language, folded):
    assert fold_transliteration(spelling, language) == folded


def test_a_prefixed_hebrew_word_keeps_its_root_number():
    # TAHOT marks the root with braces: "in" (H9003) + reshit (H7225G)
    row = ["Gen.1.1#01=L", "בְּ/רֵאשִׁ֖ית", "be./re.Shit", "in/ beginning", "H9003/{H7225G}", "HR/Ncfsa"]
    assert parse_hebrew_word(row)["strongs"] == "H7225G"
    bare = ["Gen.1.1#04=L", "אֵ֥ת", "'et", "<obj.>", "H0853", "HTo"]
    assert parse_hebrew_word(bare)["strongs"] == "H0853"


@pytest.fixture
async def db():
    d = StudyBibleDB(DB_PATH)
    await d.connect()
    yield d
    await d.close()


@needs_db
@pytest.mark.parametrize("strongs,first", [("H3068", "Gen.2.4"), ("H430", "Gen.1.1"), ("H1254", "Gen.1.1"),
                                           ("H1254A", "Gen.1.1"), ("G26", "Mat.24.12"), ("G2424", "Mat.1.1")])
async def test_strongs_search_finds_lettered_forms(db, strongs, first):
    verses = await db.get_verses_with_strongs(strongs, limit=3)
    assert verses and verses[0]["reference"] == first


@needs_db
@pytest.mark.parametrize("word,language,strongs", [
    ("shalom", None, "H7965"), ("shalom", "hebrew", "H7965"), ("agape", None, "G0026"),
    ("logos", None, "G3056"), ("hesed", None, "H2617"), ("chesed", None, "H2617"),
    ("torah", None, "H8451"), ("elohim", None, "H0430"), ("pistis", None, "G4102"),
    ("love", None, "G0026"), ("peace", "hebrew", "H7965"), ("man", None, "G0435"),
])
async def test_an_exact_transliteration_or_gloss_wins(db, word, language, strongs):
    entry = await db.find_word(word, language)
    assert entry and entry["strongs"] == strongs


@needs_db
@pytest.mark.parametrize("english,lxx", [
    ("Psa.1.1", "Psa.1.1"),        # no heading
    ("Psa.3.1", "Psa.3.2"),        # one-verse heading, same psalm number
    ("Psa.18.1", "Psa.17.2"),      # one-verse heading
    ("Psa.23.1", "Psa.22.1"),      # heading inside verse 1
    ("Psa.51.1", "Psa.50.3"),      # two-verse heading
    ("Psa.60.1", "Psa.59.3"),      # two-verse heading
    ("Psa.9.1", "Psa.9.2"), ("Psa.10.1", "Psa.9.22"), ("Psa.10.18", "Psa.9.39"),          # 9 and 10 merged
    ("Psa.114.1", "Psa.113.1"), ("Psa.115.1", "Psa.113.9"), ("Psa.115.18", "Psa.113.26"),  # 114 and 115 merged
    ("Psa.116.9", "Psa.114.9"), ("Psa.116.10", "Psa.115.1"),                              # 116 split
    ("Psa.147.11", "Psa.146.11"), ("Psa.147.12", "Psa.147.1"),                            # 147 split
    ("Psa.150.6", "Psa.150.6"),
    ("Jer.31.31", "Jer.38.31"),    # outside the Psalms the map is used as before
])
async def test_english_psalm_numbers_land_on_the_same_lxx_text(db, english, lxx):
    assert await db.standard_to_lxx(english) == lxx


@needs_db
@pytest.mark.parametrize("lxx,english", [
    ("Psa.50.1", "Psa.51.0"), ("Psa.50.2", "Psa.51.0"),  # the heading
    ("Psa.50.3", "Psa.51.1"), ("Psa.9.22", "Psa.10.1"), ("Psa.12.6", "Psa.13.5-Psa.13.6"),
])
async def test_lxx_psalm_numbers_map_back_to_english(db, lxx, english):
    assert await db.lxx_to_standard(lxx) == english
