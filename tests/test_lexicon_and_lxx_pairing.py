"""Hebrew short definitions from TBESH, and Brenton's English paired with Swete's Greek by content.
The pure helpers run anywhere; the database cases read db/study_bible.db and skip where it is absent.
No network."""
import unicodedata
import zipfile

import pytest

from studybible_mcp import server as bible
from studybible_mcp.database import StudyBibleDB
from studybible_mcp.parsers.lexicon import hebrew_short_definition
from studybible_mcp.parsers.lxx import align_verses, content_routes, parse_brenton, swete_ref

DB_PATH = bible.get_db_path()
needs_db = pytest.mark.skipif(not DB_PATH.exists(), reason="no study_bible.db here")


def info(*rows):
    """A TBESH entry: rows of (extended number, kind, part of speech, gloss, definition)."""
    return {"word": "", "transliteration": "", "rows": list(rows)}


@pytest.mark.parametrize("bdb,entry,counts,expected", [
    # a grammar label gives way to the gloss; a compound use ('a Part of') is left out
    ("noun masculine plural",
     info(("H0430G", "a Name of", "H:N-M", "God", "This name means gods"),
          ("H0430H", "a Part of", "H:N-M", "(LORD)-Elohe", "Combined with LORD")),
     None, "God"),
    # BDB's senses stay when TBESH's definition confirms them, after the gloss
    ("completeness, soundness, welfare, peace",
     info(("H7965G", "", "H:N-M", "peace", "1) completeness, soundness, welfare, peace"),
          ("H7965I", "a Meaning of", "H:N-M", "peace: well-being", "well-being")),
     None, "peace, completeness, soundness, welfare"),
    # a stray BDB phrase is dropped
    ("constantly, as more precise designation",
     info(("H1121G", "", "H:N-M", "son", "1) son, grandson, child, member of a group")),
     None, "son"),
    # a proper name keeps BDB's label
    ("proper name, masculine", info(("H1732G", "", "N:N-M-P", "David", "David = beloved")), None,
     "David, proper name, masculine"),
    # a rare homograph drops out beside the common one
    ("noun [masculine]",
     info(("H5892A", "", "H:N-M", "excitement", "anguish"), ("H5892B", "", "H:N-M", "city", "city, town")),
     {"H5892A": 2, "H5892B": 1085}, "city"),
    # without a TBESH entry the BDB gloss stands
    ("upright", None, None, "upright"),
])
def test_hebrew_short_definitions_lead_with_a_gloss(bdb, entry, counts, expected):
    assert hebrew_short_definition(bdb, entry, counts) == expected


def test_running_the_gloss_rule_twice_changes_nothing():
    entry = info(("H1732G", "", "N:N-M-P", "David", "David = beloved"))
    once = hebrew_short_definition("proper name, masculine", entry)
    assert hebrew_short_definition(once, entry) == once


def g(ch, v, text):
    return {"chapter": ch, "verse": v, "text_greek": text}


def e(ch, v, text, letter=""):
    return {"chapter": ch, "verse": v, "letter": letter, "text_english": text}


def test_a_chapter_numbered_differently_pairs_by_content():
    # Brenton ends chapter 1 a verse later than Swete, as in Isaiah 8-9: its 1:4 is Swete's 2:1
    greek = [g(1, 1, "Ἀβραὰμ ἐγέννησεν τὸν Ἰσαάκ"), g(1, 2, "λόγος " * 20), g(1, 3, "ῥῆμα " * 5),
             g(2, 1, "καὶ Δαυεὶδ ὁ βασιλεὺς " + "λαλεῖ " * 10), g(2, 2, "ἔργον " * 9), g(2, 3, "ὁδὸς " * 18)]
    english = [e(1, 1, "Abraam begot Isaac"), e(1, 2, "word " * 22), e(1, 3, "saying " * 4),
               e(1, 4, "And David the king " + "speaks " * 9), e(2, 1, "work " * 10), e(2, 2, "way " * 22)]
    assert align_verses(greek, english) == {0: [0], 1: [1], 2: [2], 3: [3], 4: [4], 5: [5]}


def test_lettered_parts_join_the_verse_that_holds_them():
    # Swete prints Proverbs 9:12a-c inside 9:12
    greek = [g(9, 11, "ζωή " * 15), g(9, 12, "σοφός " * 60), g(9, 13, "γυνή " * 12)]
    english = [e(9, 11, "life " * 16), e(9, 12, "wise " * 18), e(9, 12, "winds " * 18, "a"),
               e(9, 12, "vineyard " * 12, "b"), e(9, 12, "desert " * 14, "c"), e(9, 13, "woman " * 11)]
    assert align_verses(greek, english) == {0: [0], 1: [1, 2, 3, 4], 2: [5]}


def test_a_verse_with_no_greek_takes_english_only_at_its_own_number():
    greek = [g(43, 7, "τόξον " * 10), g(43, 8, ""), g(43, 9, "θεός " * 14)]
    english = [e(43, 7, "bow " * 11), e(43, 8, "saved " * 12), e(43, 9, "God " * 15)]
    assert align_verses(greek, english) == {0: [0], 1: [1], 2: [2]}


def test_brenton_keeps_lettered_verses_and_drops_notes(tmp_path):
    usfm = ("\\id PSA\n\\c 144\n\\v 13 Thy kingdom \\f + \\fr 144:13 \\ft Gr. of all ages.\\f*is everlasting.\n"
            "\\v 13a The Lord is faithful in his words.\n\\v 14 The Lord supports all.\n")
    path = tmp_path / "brenton.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("20-PSAeng-Brenton.usfm", usfm)
    rows = list(parse_brenton(path))
    assert [(r["reference"], r["letter"]) for r in rows] == [("Psa.144.13", ""), ("Psa.144.13a", "a"),
                                                               ("Psa.144.14", "")]
    assert rows[0]["text_english"] == "Thy kingdom is everlasting."


@pytest.mark.parametrize("ref,swete", [
    ("Esg.2.1", "Est.2.1"),      # Copenhagen's Greek Esther
    ("Ezr.11.1", "Neh.1.1"),     # 2 Esdras runs on into Nehemiah
    ("Ezr.10.44", "Ezr.10.44"),
    ("Dan.13.5", "Sus.1.5"),     # Susanna, folded into Daniel in English
    ("Dan.14.3", "Bel.1.3"),
    ("Bar.6.3", "Epj.1.3"),      # the Letter of Jeremiah
    ("Ps2.1.1", "Psa.151.1"),
    ("Gen.1.1", "Gen.1.1"),
])
def test_references_take_swetes_book_names(ref, swete):
    assert swete_ref(ref) == swete


KJV = {  # Malachi 4:4-6, which Swete orders 4:5, 4:6, 4:4 and numbers 4:4-6
    "Mal.4.3": "And ye shall tread down the wicked; for they shall be ashes under the soles of your feet",
    "Mal.4.4": "Remember ye the law of Moses my servant, which I commanded unto him in Horeb for all Israel, "
               "with the statutes and judgments.",
    "Mal.4.5": "Behold, I will send you Elijah the prophet before the coming of the great and dreadful day of the LORD:",
    "Mal.4.6": "And he shall turn the heart of the fathers to the children, and the heart of the children to "
               "their fathers, lest I come and smite the earth with a curse.",
}
BRENTON = {
    "Mal.4.3": "And ye shall trample the wicked; for they shall be ashes underneath your feet",
    "Mal.4.4": "And, behold, I will send to you Elias the Thesbite, before the great and glorious day of the Lord comes;",
    "Mal.4.5": "who shall turn again the heart of the father to the son, and the heart of a man to his neighbour, "
               "lest I come and smite the earth grievously.",
    "Mal.4.6": "Remember the law of my servant Moses, accordingly as I charged him with it in Choreb for all Israel, "
               "even the commandments and ordinances.",
}


def test_content_finds_a_reordered_verse():
    routes = content_routes(KJV, {}, BRENTON, set(BRENTON))
    assert {e: r for e, (r, _) in routes.items()} == {"Mal.4.4": "Mal.4.6", "Mal.4.5": "Mal.4.4", "Mal.4.6": "Mal.4.5"}


def test_a_single_look_alike_stays_put():
    # one tribe in a list reads like the next one; the routed verse is the right one
    english = {"Num.10.20": "And over the host of the tribe of the children of Gad was Eliasaph the son of Deuel.",
               "Num.10.26": "And over the host of the tribe of the children of Asher was Pagiel the son of Ocran."}
    brenton = {"Num.10.20": "And over the host of the tribe of the children of Gad, was Elisaph the son of Raguel.",
               "Num.10.26": "And over the forces of the tribe of the sons of Aser, was Phageel the son of Echran."}
    assert content_routes(english, {}, brenton, set(brenton)) == {}


def test_a_renumbered_block_moves_together():
    # Swete numbers these three verses two higher, as in Daniel 4 (English 4:4 is Swete's 4:1)
    english = {"Dan.4.4": "I Nebuchadnezzar was at rest in mine house, and flourishing in my palace",
               "Dan.4.5": "I saw a dream which made me afraid, and the thoughts upon my bed troubled me",
               "Dan.4.6": "Therefore made I a decree to bring in all the wise men of Babylon before me"}
    brenton = {"Dan.4.4": "I Nabuchodonosor was flourishing in my house, and prospering",
               "Dan.4.5": "I saw a vision, and it terrified me, and I was troubled on my bed",
               "Dan.4.6": "And by me was made a decree to bring in all the wise men of Babylon before me",
               "Dan.4.7": "Then came in the enchanters",
               "Dan.4.1": "x", "Dan.4.2": "y", "Dan.4.3": "z"}
    shifted = {"Dan.4.6": brenton["Dan.4.4"], "Dan.4.7": brenton["Dan.4.5"], "Dan.4.8": brenton["Dan.4.6"],
               "Dan.4.4": "the king answered", "Dan.4.5": "a fourth beast"}
    routes = content_routes(english, {}, shifted, set(shifted))
    assert {e: r for e, (r, _) in routes.items()} == {"Dan.4.4": "Dan.4.6", "Dan.4.5": "Dan.4.7", "Dan.4.6": "Dan.4.8"}


@pytest.mark.parametrize("reference,normalized", [
    ("Song of Solomon 2:1", "Sng.2.1"), ("Song of Songs 1:1", "Sng.1.1"), ("Wisdom of Solomon 7:26", "Wis.7.26"),
    ("1 John 3:16", "1Jn.3.16"), ("John 3:16", "Jhn.3.16"), ("Jude 3", "Jud.1.3"),
])
def test_book_names_of_several_words_parse(reference, normalized):
    assert StudyBibleDB._normalize_reference(None, reference) == normalized


@pytest.fixture
async def db():
    d = StudyBibleDB(DB_PATH)
    await d.connect()
    yield d
    await d.close()


@needs_db
async def test_lexicon_search_puts_the_glossed_words_first(db):
    first = [r["strongs"] for r in await db.search_lexicon("love", limit=6)]
    assert {"G0025", "G0026", "H0157"} <= set(first)
    atonement = [r["strongs"] for r in await db.search_lexicon("atonement", limit=3)]
    assert "H3725" in atonement and "H7676" not in atonement


@needs_db
@pytest.mark.parametrize("strongs,short", [("H0430", "God"), ("H1121", "son"), ("H0136", "Lord"),
                                           ("H0085", "Abraham"), ("H5921", "upon")])
async def test_hebrew_entries_have_glosses(db, strongs, short):
    entry = await db.get_lexicon_entry(strongs)
    assert entry and entry["short_definition"].split(",")[0] == short


@needs_db
@pytest.mark.parametrize("ref,greek,english", [
    ("Isa.9.6", "παιδ", "a child is born"),          # Brenton numbers this 9:5
    ("Jer.9.1", "Τίς δώσει", "water to my head"),       # Brenton numbers this 8:23
    ("Psa.144.14", "πιστὸς", "faithful in his words"),  # Brenton's 13a sits in Swete's 14
    ("Dat.1.1", "τρίτῳ", "third year"),                 # Theodotion's Daniel, which Brenton translated
])
async def test_brenton_sits_beside_its_greek(db, ref, greek, english):
    row = await db.get_lxx_verse(ref)
    assert plain(greek) in plain(row["text_greek"]) and english in row["text_english"]


def plain(text: str) -> str:
    """Greek without accents, since Swete's accents are not always the code points typed here."""
    return "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))


@needs_db
@pytest.mark.parametrize("english,lxx", [
    ("Mal.4.4", "Mal.4.6"), ("Mal.4.5", "Mal.4.4"), ("Mal.4.6", "Mal.4.5"),  # Swete's Malachi order
    ("Dan.3.24", "Dan.3.91"),                                                # after the Prayer of Azariah
    ("Job.41.27", "Job.41.19"),
    ("Neh.1.1", "Neh.1.1"), ("Est.1.1", "Est.1.1"),                          # Copenhagen's Ezr 11 and Esg
])
async def test_english_verses_route_to_the_swete_verse_that_holds_them(db, english, lxx):
    assert swete_ref(await db.standard_to_lxx(english) or english) == lxx
    assert await db.get_lxx_verse(lxx)


@needs_db
async def test_a_reordered_verse_maps_back(db):
    assert await db.lxx_to_standard("Mal.4.6") == "Mal.4.4"


@needs_db
async def test_greekless_verses_keep_brentons_english_and_the_old_greek_has_none(db):
    row = await db.get_lxx_verse("Psa.43.8")
    assert row["text_greek"] is None and "saved us" in row["text_english"]
    assert (await db.get_lxx_verse("Dan.1.1"))["text_english"] is None
