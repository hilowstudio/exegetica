"""Write the corpus manifest, and check the /corpus page and NOTICE against the databases.

    .venv/Scripts/python.exe scripts/corpus_manifest.py           # write docs/corpus-manifest.json
    .venv/Scripts/python.exe scripts/corpus_manifest.py --check   # exit 1 if anything disagrees

The manifest lists every source the app serves from its SQLite corpora (db/study_bible.db,
db/theology.db, db/social_sciences.db, db/books.db): name, count, rows, license, source URL, and
a fingerprint. Sources are registered by hand in SOURCES below, because license and URL live in
no table. A value that turns up in a database with no registered source is reported, so a new
import cannot slip in without an entry.

Fingerprint. Each source's fingerprint is a SHA-256 (first 16 hex digits) of a small identity
query: its row count and rowid range, grouped by source key where the table holds several
sources. The file is never hashed. Hashing 6-8 GB on every run takes minutes, and the file's
bytes change on a VACUUM or page reshuffle that changes no content. The identity query takes a
few seconds for all four databases, changes when rows are added, removed, or regrouped, and
holds steady across a rebuild that changes nothing. It does not see an in-place edit of a row's
text; publish_db.py already content-hashes the whole file when it ships.

The check compares:
  - the numbers on /corpus (webapp/static/corpus.html) with the databases, including the
    embedded church-father list and the grounding-work list (the Lexicons heading's "5 works"
    is not checked: lexicon rows are not labeled by work);
  - the page's tool list with the tools the chat registers. The page renders that list at load
    from /api/config, which builds it with webapp/tool_catalog.py from the registered tools, so
    the check is that every registered tool has a group in tool_catalog (Bible mode and History
    mode) and tool_catalog names no tool the chat lacks. A tool list or count typed into the
    page is still compared with the registered tools;
  - the page's credits section: every source under a CC BY or CC BY-SA license links its source
    there, because chat users read the page and never see NOTICE;
  - NOTICE with the databases: every source that should be credited there is named with its
    source (the repository or dataset name, or the host), every bundled source NOTICE names has
    rows, NOTICE's counts are present and match, and nothing bundled is filed under its "NOT
    bundled" heading. Every study_bible.db and theology.db source should be named (NOTICE's own
    convention for the Study Bible data); social_sciences.db and books.db sources only where
    the license asks for credit;
  - the committed manifest with the databases (--check only).

It never edits NOTICE or corpus.html. It prints what disagrees, and those files are corrected
by hand. A database that is missing locally is skipped with a note: its committed manifest
entries are kept as they are, and the checks that need it are not run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "db"
MANIFEST = ROOT / "docs" / "corpus-manifest.json"
NOTICE = ROOT / "NOTICE"
PAGE = ROOT / "webapp" / "static" / "corpus.html"

DATABASES = {
    "study_bible": "db/study_bible.db",
    "theology": "db/theology.db",
    "social_sciences": "db/social_sciences.db",
    "books": "db/books.db",
}
# Databases whose every source NOTICE should name (it is the Study Bible MCP's NOTICE).
MCP_DATABASES = {"study_bible", "theology"}

_CC_BY_SA = "CC BY-SA 4.0"
_AQUIFER = "https://github.com/BibleAquifer/"
_CCEL_PARAGRAPHS = "https://huggingface.co/datasets/jncraton/ccel-paragraphs"
_CCEL_LICENSE = "Public-domain texts; CCEL Paragraphs dataset (Jon Craton) CC BY-SA 4.0"


@dataclass
class Source:
    id: str
    name: str
    db: str
    table: str
    license: str
    url: str | None
    notice: str | None = None        # regex NOTICE must match; None = not required there
    key: str | None = None           # column that tells this table's sources apart
    values: tuple = ()               # this source's values of `key`
    exclude: tuple = ()              # or: every value of `key` except these
    filter: str = ""                 # extra SQL condition for a source that is part of its rows
    unit: str = "rows"
    count_sql: str | None = None     # the count in `unit`; default = count(*) over where()
    rows_sql: str | None = None      # all rows it fills; default = count(*) over where()
    fp_sql: str | None = None        # default = count, rowid range (per key)
    tables: tuple = ()               # other tables this source fills
    note: str = ""

    def where(self) -> str:
        parts = [self.filter] if self.filter else []
        if self.values:
            parts.append(f"{self.key} in ({','.join(_lit(v) for v in self.values)})")
        elif self.exclude:
            parts.append(f"{self.key} not in ({','.join(_lit(v) for v in self.exclude)})")
        return " and ".join(parts) or "1"


def _lit(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


_THEOLOGAI_DOCS = (
    "apostles-creed", "nicene-creed", "athanasian-creed", "chalcedonian-definition",
    "westminster-confession", "westminster-larger-catechism", "westminster-shorter-catechism",
    "belgic-confession", "canons-of-dort", "heidelberg-catechism", "london-baptist-1689",
    "augsburg-confession", "39-articles", "council-of-trent", "baltimore-catechism",
    "confession-of-dositheus", "philaret-catechism",
)
_COMPENDIUM_DOCS = ("wsc-pca", "keach", "savoy", "catechism-young-children")
_HELLOAO = ("adam-clarke", "jamieson-fausset-brown", "john-calvin", "john-gill",
            "keil-delitzsch", "matthew-henry")

SOURCES: list[Source] = [
    # ---------------------------------------------------------------- study_bible.db
    Source("stepbible-text", "STEPBible tagged Hebrew OT and Greek NT (TAHOT, TAGNT)", "study_bible",
           "verses", "CC BY 4.0", "https://github.com/STEPBible/STEPBible-Data", r"STEPBible",
           unit="verses", tables=("passages", "thematic_references")),
    Source("stepbible-lexicons", "Extended Strong's lexicons (TBESH, TBESG) and LSJ (TFLSJ)", "study_bible",
           "lexicon", "CC BY 4.0", "https://github.com/STEPBible/STEPBible-Data", r"TBESH",
           unit="entries"),
    Source("bdb", "Brown-Driver-Briggs Hebrew Lexicon", "study_bible", "lexicon",
           "Public domain (1906)", "https://github.com/eliranwong/unabridged-BDB-Hebrew-lexicon",
           r"Brown-Driver-Briggs", unit="Hebrew entries",
           filter="language='hebrew' and coalesce(full_definition,'')!=''"),
    Source("abbott-smith", "Abbott-Smith, Manual Greek Lexicon of the New Testament", "study_bible", "lexicon",
           "Public domain", "https://github.com/translatable-exegetical-tools/Abbott-Smith",
           r"Abbott-Smith", unit="Greek entries", filter="coalesce(abbott_smith_def,'')!=''"),
    Source("tipnr", "STEPBible proper names (TIPNR)", "study_bible", "names", "CC BY 4.0",
           "https://github.com/STEPBible/STEPBible-Data", r"TIPNR", unit="names"),
    Source("morphology", "STEPBible morphology codes (TEHMC, TEGMC)", "study_bible", "morphology",
           "CC BY 4.0", "https://github.com/STEPBible/STEPBible-Data", r"morphology code", unit="codes"),
    Source("word-frequency", "Word-frequency index (derived from the STEPBible tags)", "study_bible",
           "word_frequency", "Derived from CC BY 4.0 data", None, r"Word-frequency index",
           unit="Strong's numbers"),
    Source("translations", "Readable English translations (BSB, WEB, KJV, ASV, YLT)", "study_bible",
           "translations", "Public domain (\"World English Bible\" is an eBible.org trademark)",
           "https://ebible.org", r"Berean Standard Bible", key="translation",
           values=("ASV", "BSB", "KJV", "WEB", "YLT"), unit="translations",
           count_sql="select count(distinct translation) from translations where {where}"),
    Source("lxx-swete", "Greek Septuagint (H.B. Swete, 1909-1930)", "study_bible", "lxx_verses",
           "Public domain (digitization GPL-3.0)", "https://github.com/eliranwong/LXX-Swete-1930",
           r"Swete", unit="verses", filter="coalesce(text_greek,'')!=''"),
    Source("lxx-brenton", "English Septuagint (L.C.L. Brenton, 1851)", "study_bible", "lxx_verses",
           "Public domain", "https://ebible.org (eng-Brenton)", r"Brenton", unit="verses",
           filter="coalesce(text_english,'')!=''"),
    Source("versification", "Copenhagen Alliance versification mappings", "study_bible",
           "versification_map", "CC BY-SA 4.0 (data; the repository's code is Apache-2.0)",
           "https://github.com/Copenhagen-Alliance/versification-specification", r"Copenhagen",
           unit="mappings", tables=("lxx_routes",),
           note="lxx_routes holds our corrections where Swete's numbering is not the map's, found by "
                "comparing Brenton's English with the KJV."),
    Source("theographic", "Theographic Bible Metadata (people, places, events)", "study_bible",
           "graph_people", _CC_BY_SA, "https://github.com/robertrouse/theographic-bible-metadata",
           r"Theographic", unit="people", count_sql="select count(*) from graph_people",
           rows_sql="select (select count(*) from graph_people)+(select count(*) from graph_places)"
                    "+(select count(*) from graph_events)",
           fp_sql="select (select count(*) from graph_people),(select count(*) from graph_places),"
                  "(select count(*) from graph_events),(select count(*) from graph_family_edges),"
                  "(select count(*) from graph_verse_mentions)",
           tables=("graph_places", "graph_events", "graph_family_edges", "graph_verse_mentions",
                   "graph_event_place_edges", "graph_person_event_edges", "graph_person_group_edges",
                   "graph_people_groups")),
    Source("acai", "ACAI entities (BibleAquifer)", "study_bible", "acai_entities", _CC_BY_SA,
           "https://github.com/BibleAquifer/ACAI", r"ACAI", unit="entities"),
    Source("openbible-xrefs", "OpenBible.info cross-references", "study_bible", "cross_references",
           "CC BY 4.0", "https://www.openbible.info/labs/cross-references/", r"OpenBible",
           unit="cross-references"),
    Source("ubs-parallels", "UBS Parallel Passage Database", "study_bible", "parallel_passages",
           _CC_BY_SA, "https://github.com/ubsicap/ubs-open-license", r"UBS Parallel Passage",
           unit="groups", count_sql="select count(distinct group_id) from parallel_passages"),
    Source("helloao-commentaries", "Public-domain commentaries via HelloAO (Henry, Gill, JFB, Clarke, "
           "Calvin, Keil & Delitzsch)", "study_bible", "commentaries", "Public domain",
           "https://bible.helloao.org", r"HelloAO", key="source", values=_HELLOAO, unit="commentaries",
           count_sql="select count(distinct source) from commentaries where {where}"),
    Source("spurgeon-treasury", "Spurgeon, The Treasury of David", "study_bible", "commentaries",
           "CC0 (public-domain text)", "https://github.com/lyteword/chspurgeon-tod", r"Treasury of David",
           key="source", values=("spurgeon-treasury",), unit="entries"),
    Source("hodge-romans", "Charles Hodge, Commentary on Romans", "study_bible", "commentaries",
           "Public domain (Hodge d. 1878)", None, r"Hodge", key="source", values=("hodge-romans",),
           unit="entries", note="Imported from an EPUB of the public-domain text."),
    Source("ryle-gospels", "J.C. Ryle, Expository Thoughts on the Gospels", "study_bible", "commentaries",
           "Public domain (Ryle d. 1900)", None, r"Ryle", key="source", values=("ryle-expository",),
           unit="entries", note="Imported from an EPUB of the public-domain text."),
    Source("catena-hcf", "Patristic catena (HistoricalChristianFaith Commentaries-Database)", "study_bible",
           "patristic_catena", "Public domain (pre-1900 authors only)",
           "https://github.com/HistoricalChristianFaith/Commentaries-Database", r"HistoricalChristianFaith",
           key="source", values=("historical-christian-faith",), unit="excerpts"),
    Source("catena-sermonindex", "Patristic quotations (SermonIndex early-church-fathers)", "study_bible",
           "patristic_catena", "CC BY 4.0", "https://huggingface.co/datasets/sermonindex/early-church-fathers",
           r"SermonIndex", key="source", values=("sermonindex",), unit="excerpts"),
    Source("creeds-theologai", "Creeds, confessions, and catechisms (TheologAI compilation)", "study_bible",
           "historical_documents", "Public-domain texts (ISC-licensed compilation)",
           "https://github.com/TJ-Frederick/TheologAI", r"TheologAI", key="doc_id", values=_THEOLOGAI_DOCS,
           unit="documents", count_sql="select count(distinct doc_id) from historical_documents where {where}"),
    Source("creeds-compendium", "Reformed Standards Compendium (proof-texts and four documents)", "study_bible",
           "confession_proof_texts", "Apache-2.0", "https://github.com/reformed-standards/compendium",
           r"Reformed Standards Compendium", unit="proof-texts",
           fp_sql="select count(*), min(rowid), max(rowid), (select count(distinct doc_id) from "
                  "historical_documents where doc_id in ('wsc-pca','keach','savoy','catechism-young-children')) "
                  "from confession_proof_texts"),
    Source("creeds-json", "Creeds, confessions, and catechisms (Creeds.json)", "study_bible",
           "historical_documents", "Public-domain texts; compilation under the Unlicense",
           "https://github.com/NonlinearFruit/Creeds.json", r"Creeds\.json|NonlinearFruit", key="doc_id",
           exclude=_THEOLOGAI_DOCS + _COMPENDIUM_DOCS, unit="documents",
           count_sql="select count(distinct doc_id) from historical_documents where {where}"),
    Source("eastons", "Easton's Bible Dictionary (1897)", "study_bible", "dictionaries", "Public domain",
           "https://github.com/garydavenport73/eastons-bible-dictionary-json", r"Easton", key="source",
           values=("eastons",), unit="articles"),
    Source("morning-evening", "Spurgeon, Morning and Evening", "study_bible", "devotionals", "Public domain",
           "https://github.com/dwahrens/morning-and-evening", r"Morning and Evening", key="source",
           values=("morning-evening",), unit="readings"),
    Source("tyndale-study-notes", "Aquifer Open Study Notes (Mission Mutual, adapted from Tyndale Open "
           "Study Notes)", "study_bible", "aquifer_content", _CC_BY_SA, _AQUIFER + "AquiferOpenStudyNotes",
           r"Tyndale Open Study Notes", key="resource_type", values=("study_notes",), unit="notes"),
    Source("tyndale-dictionary", "Aquifer Open Bible Dictionary (Mission Mutual, adapted from Tyndale Open "
           "Bible Dictionary)", "study_bible", "aquifer_content", _CC_BY_SA,
           _AQUIFER + "AquiferOpenBibleDictionary", r"Tyndale Open Bible Dictionary",
           key="resource_type", values=("dictionary",), unit="articles"),
    Source("fia-key-terms", "FIA Key Terms (Word Collective, via BibleAquifer)", "study_bible", "aquifer_content",
           _CC_BY_SA, _AQUIFER + "FIAKeyTerms", r"\bFIA\b", key="resource_type", values=("key_terms",),
           unit="terms"),
    Source("uw-translation-notes", "unfoldingWord Translation Notes (via BibleAquifer)", "study_bible",
           "aquifer_content", _CC_BY_SA, _AQUIFER + "UWTranslationNotes", r"unfoldingWord", key="resource_type",
           values=("translation_notes_uw",), unit="notes"),
    Source("sil-translation-notes", "Open Translator's Notes (SIL International, via BibleAquifer)",
           "study_bible", "aquifer_content", _CC_BY_SA, _AQUIFER + "SILOpenTranslatorsNotes", r"\bSIL\b",
           key="resource_type", values=("translation_notes_sil",), unit="notes"),
    # ---------------------------------------------------------------- theology.db
    Source("theology-grounding", "Theology grounding corpus (public-domain CCEL works, via CCEL Paragraphs)",
           "theology", "theology_works", _CCEL_LICENSE + " (each work's rights are in theology_works.rights)",
           _CCEL_PARAGRAPHS, r"Theology grounding corpus", unit="works",
           count_sql="select count(*) from theology_works", rows_sql="select count(*) from theology_texts",
           fp_sql="select work_id, n_paragraphs from theology_works order by work_id",
           tables=("theology_texts", "theology_passages"),
           note="Rows are paragraphs. CCEL's copyright policy allows personal, educational, or non-profit use "
                "and asks to be contacted before republishing or commercial use."),
    # ---------------------------------------------------------------- social_sciences.db
    Source("avalon", "Avalon Project documents (Yale Law School)", "social_sciences", "documents",
           "Public domain (historical and government documents)", "https://avalon.law.yale.edu",
           key="source", values=("avalon",), unit="documents", tables=("passages",)),
    Source("miller-center", "Presidential speeches (Miller Center, University of Virginia)", "social_sciences",
           "documents", "Public domain (speech texts)", "https://data.millercenter.org",
           r"Miller Center of Public Affairs", key="source", values=("miller-center",), unit="speeches",
           note="The Miller Center offers the data \"for the use of the research and academic communities\" "
                "and asks to be cited. We keep the transcripts, not its introductions."),
    Source("docsouth", "Documenting the American South (UNC-Chapel Hill)", "social_sciences", "documents",
           "CC BY 4.0 (credit the University Library, UNC-Chapel Hill)", "https://docsouth.unc.edu",
           r"DocSouth|Documenting the American South", key="source", values=("docsouth",), unit="documents",
           note="DocSouth Data's readme excepts \"Fields's Observations: The Slave Narrative of a "
                "Nineteenth-Century Virginian\" (ed. Mary J. Bratton, 1980) from its CC BY grant: it has no "
                "known rights."),
    Source("nara", "National Archives founding and milestone documents", "social_sciences", "documents",
           "U.S. government work (public domain)", "https://www.archives.gov/milestone-documents",
           key="source", values=("nara",), unit="documents"),
    Source("wikisource-docs", "Wikisource texts", "social_sciences", "documents",
           "Public-domain texts; Wikisource contributions CC BY-SA 4.0", "https://en.wikisource.org",
           r"Wikisource", key="source", values=("wikisource",), unit="documents"),
    Source("single-documents", "Single documents (U.S. Code title 4, Illinois Constitution, Worcester v. "
           "Georgia, one Project Gutenberg text)", "social_sciences", "documents", "Public domain", None,
           key="source", values=("govinfo", "ilga", "cap", "gutenberg"), unit="documents"),
    Source("reading-room-history", "Reading Room history books (from books.db)", "social_sciences", "documents",
           "Public domain", None, key="source", values=("reading-room",), unit="books",
           note="Credited with the Reading Room sources in books.db."),
    Source("cap-cases", "Supreme Court opinions (Caselaw Access Project, Harvard Law School)", "social_sciences",
           "cases", "Released without restriction on access or use; court opinions are public domain",
           "https://case.law", unit="cases", tables=("case_opinions", "case_passages")),
    Source("scdb", "Supreme Court Database coding (vote, issue area, justices)", "social_sciences", "cases",
           "No license stated; cited as its makers ask, with the release number", "https://scdb.la.psu.edu",
           r"Supreme Court Database", unit="cases", filter="coalesce(scdb_id,'')!=''"),
    Source("conan", "Constitution Annotated (Congressional Research Service, 2022)", "social_sciences", "conan",
           "U.S. government work (public domain)", "https://constitution.congress.gov", unit="entries"),
    Source("us-code", "United States Code", "social_sciences", "statutes", "U.S. government work (public domain)",
           "https://www.govinfo.gov/app/collection/uscode", key="code", values=("usc",), unit="sections"),
    Source("ilcs", "Illinois Compiled Statutes (selected chapters)", "social_sciences", "statutes",
           "Public domain by statute", "https://www.ilga.gov/legislation/ilcs/ilcs.asp", key="code",
           values=("ilcs",), unit="sections"),
    Source("constitutions", "U.S. and Illinois Constitutions and the U.S. Flag Code", "social_sciences",
           "sections", "Public domain", "https://www.archives.gov/founding-docs", key="code",
           values=("us-constitution", "il-constitution", "flag-code"), unit="sections"),
    Source("blacks-law", "Black's Law Dictionary (2nd ed., 1910)", "social_sciences", "glossary", "Public domain",
           None, key="source", values=("Black's Law Dictionary (2nd ed., 1910)",), unit="terms"),
    Source("webster-1828", "Webster's American Dictionary of the English Language (1828)", "social_sciences",
           "glossary", "Public domain", None, key="source",
           values=("Webster's American Dictionary of the English Language (1828)",), unit="terms"),
    Source("wikidata-graph", "History graph of people, events, and places (Wikidata slice)", "social_sciences",
           "h_people", "CC0", "https://www.wikidata.org", unit="people",
           count_sql="select count(*) from h_people", rows_sql="select (select count(*) from h_people)+(select count(*) from h_events)"
                    "+(select count(*) from h_places)",
           fp_sql="select (select count(*) from h_people),(select count(*) from h_events),"
                  "(select count(*) from h_places),(select count(*) from h_entities),(select count(*) from h_edges)",
           tables=("h_events", "h_places", "h_entities", "h_edges", "h_mentions")),
    Source("congress-legislators", "Members of Congress, presidents, and vice presidents", "social_sciences",
           "legislators", "CC0", "https://github.com/unitedstates/congress-legislators", unit="people",
           tables=("legislator_terms", "executives")),
    # ---------------------------------------------------------------- books.db (Reading Room)
    Source("gutenberg", "Project Gutenberg", "books", "books", "Public domain in the U.S.",
           "https://www.gutenberg.org", key="source", values=("gutenberg",), unit="books",
           tables=("book_chapters", "edition_chapters")),
    Source("standard-ebooks", "Standard Ebooks", "books", "books", "CC0 1.0 (public-domain texts)",
           "https://standardebooks.org", key="source", values=("standardebooks",), unit="books"),
    Source("ccel-books", "Christian Classics Ethereal Library (via CCEL Paragraphs)", "books", "books",
           _CCEL_LICENSE, _CCEL_PARAGRAPHS, r"Reading Room theology books", key="source", values=("ccel",),
           unit="books"),
    Source("internet-archive", "Internet Archive scans", "books", "books", "Public domain",
           "https://archive.org", key="source", values=("archive.org",), unit="books"),
    Source("gutenberg-au", "Project Gutenberg Australia", "books", "books", "Public domain (checked U.S.-clear)",
           "https://gutenberg.net.au", key="source", values=("gutenberg-au",), unit="books"),
    Source("wikisource-books", "Wikisource books", "books", "books",
           "Public-domain texts; Wikisource contributions CC BY-SA 4.0", "https://en.wikisource.org",
           r"Wikisource", key="source", values=("wikisource",), unit="books"),
    Source("exegetica-originals", "Exegetica originals", "books", "books", "(c) 2026 Adam Vega", None,
           key="source", values=("exegetica",), unit="books", note="The maker's own writing."),
]

# Columns that tell sources apart within one table. A value here with no registered source is drift.
DISCOVER = [
    ("study_bible", "translations", "translation"),
    ("study_bible", "commentaries", "source"),
    ("study_bible", "dictionaries", "source"),
    ("study_bible", "devotionals", "source"),
    ("study_bible", "aquifer_content", "resource_type"),
    ("study_bible", "patristic_catena", "source"),
    ("social_sciences", "documents", "source"),
    ("social_sciences", "statutes", "code"),
    ("social_sciences", "sections", "code"),
    ("social_sciences", "glossary", "source"),
    ("books", "books", "source"),
]
# Tables that hold no source of their own: search indexes, vectors, and build metadata.
_INDEX_TABLE = re.compile(r"(_fts|_vec)(_|$)|^(meta|theology_vecmeta)$")

# Scalars the /corpus page and NOTICE make claims about: key -> (database, SQL).
ACTUALS = {
    "translations": ("study_bible", "select count(distinct translation) from translations"),
    "commentaries": ("study_bible", "select count(distinct source) from commentaries"),
    "creeds": ("study_bible", "select count(distinct doc_id) from historical_documents"),
    "catena_authors": ("study_bible", "select count(distinct father_name) from patristic_catena"),
    "catena_hcf": ("study_bible", "select count(*) from patristic_catena where source='historical-christian-faith'"),
    "xrefs": ("study_bible", "select count(*) from cross_references"),
    "eastons": ("study_bible", "select count(*) from dictionaries where source='eastons'"),
    "morning_evening_days": ("study_bible", "select count(distinct month||'-'||day) from devotionals "
                                            "where source='morning-evening'"),
    "theologai_docs": ("study_bible", "select count(distinct doc_id) from historical_documents where doc_id in ("
                                      + ",".join(_lit(d) for d in _THEOLOGAI_DOCS) + ")"),
    "creeds_json_docs": ("study_bible", "select count(distinct doc_id) from historical_documents where doc_id "
                                        "not in (" + ",".join(_lit(d) for d in _THEOLOGAI_DOCS + _COMPENDIUM_DOCS)
                                        + ")"),
    "theology_works": ("theology", "select count(*) from theology_works"),
    "theology_paragraphs": ("theology", "select count(*) from theology_texts"),
}

# (what, regex on corpus.html capturing the claimed number, ACTUALS key, how to compare)
PAGE_CLAIMS = [
    ("lead: public-domain commentaries", r"<b>(\d+) public-domain commentaries</b>", "commentaries", "int"),
    ("lead: church-fathers catena authors", r"<b>(\d+)-author church-fathers catena</b>", "catena_authors", "int"),
    ("lead: grounding works", r"<b>([\d,]+)-work full-text grounding corpus</b>", "theology_works", "int"),
    ("Bible translations heading", r"<h2>Bible translations</h2><span class=\"k\">(\d+) texts", "translations", "int"),
    ("Commentaries heading", r"<h2>Commentaries</h2><span class=\"k\">(\d+) works", "commentaries", "int"),
    ("Theology heading", r"id=\"gkey\">([\d,]+) works", "theology_works", "int"),
    ("Theology note: works", r"<b>([\d,]+) works</b>, [\d.]+M paragraphs", "theology_works", "int"),
    ("Theology note: paragraphs", r"<b>[\d,]+ works</b>, ([\d.]+)M paragraphs", "theology_paragraphs", "millions"),
    ("Creeds heading", r"<h2>Creeds, confessions &amp; catechisms</h2><span class=\"k\">(\d+) documents",
     "creeds", "int"),
    ("stat: Grounding works", r"\[\(([\d,]+)\)\.toLocaleString\(\), \"Grounding works\"\]", "theology_works", "int"),
    ("stat: Commentaries", r"\[(\d+), \"Commentaries\"\]", "commentaries", "int"),
    ("stat: Creeds & confessions", r"\[(\d+), \"Creeds & confessions\"\]", "creeds", "int"),
    ("stat: Translations", r"\[(\d+), \"Translations\"\]", "translations", "int"),
]

# (what, regex on NOTICE capturing the claimed number, ACTUALS key, multiplier). A claim that
# starts with "~" may be off by 2%; any other claim must match exactly.
NOTICE_CLAIMS = [
    ("OpenBible cross-references", r"(~?[\d.]+)k community-voted cross-references", "xrefs", 1000),
    ("HistoricalChristianFaith excerpts", r"(~?[\d,]+)\s+public-domain church-father", "catena_hcf", 1),
    ("TheologAI documents", r"(~?\d+) documents\s+across the Ecumenical", "theologai_docs", 1),
    ("Easton's articles", r"(~?[\d,]+) headword articles", "eastons", 1),
    ("Morning and Evening days", r"(~?\d+) verse-keyed daily devotional readings", "morning_evening_days", 1),
    ("Creeds.json documents", r"(~?\d+) confessions,\s+catechisms, and rules of faith", "creeds_json_docs", 1),
]
_NOT_BUNDLED_HEADING = re.compile(r"^Optional live-proxied translations \(NOT bundled", re.M)

# The page builds its tool list at load from /api/config (webapp/tool_catalog.py over the registered tools).
_LIVE_TOOL_LIST = (re.compile(r'fetch\("/api/config"'), re.compile(r'id="tool-groups"'))
_CREDITS_SECTION = re.compile(r'<section id="credits">(.*?)</section>', re.S)


# ------------------------------------------------------------------------------- measuring
def open_databases(db_dir: Path = DB_DIR) -> dict[str, sqlite3.Connection | None]:
    """Read-only connections by name; None for a database that isn't on this machine."""
    out: dict[str, sqlite3.Connection | None] = {}
    for name, rel in DATABASES.items():
        path = db_dir / Path(rel).name
        out[name] = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) if path.exists() else None
    return out


def _scalar(con: sqlite3.Connection, sql: str):
    row = con.execute(sql).fetchone()
    return row[0] if row else None


def measure(con: sqlite3.Connection, s: Source) -> dict:
    """One manifest entry, measured from its database."""
    where = s.where()
    entry = {"id": s.id, "name": s.name, "database": s.db, "table": s.table}
    try:
        base = f"select count(*) from {s.table} where {where}"
        rows = _scalar(con, s.rows_sql or base)
        if s.count_sql:
            count = _scalar(con, s.count_sql.format(where=where))
        else:
            count = _scalar(con, base) if s.rows_sql else rows
        fp_sql = s.fp_sql or (
            f"select {s.key}, count(*), min(rowid), max(rowid) from {s.table} where {where} "
            f"group by {s.key} order by {s.key}" if s.key else
            f"select count(*), min(rowid), max(rowid) from {s.table} where {where}")
        h = hashlib.sha256()
        for row in con.execute(fp_sql):
            h.update(repr(tuple(row)).encode("utf-8"))
        fingerprint = "sha256:" + h.hexdigest()[:16]
    except sqlite3.Error as e:
        count, rows, fingerprint = 0, 0, None
        entry["error"] = f"{type(e).__name__}: {e}"
    entry.update(count=count or 0, unit=s.unit, rows=rows or 0, license=s.license, url=s.url,
                 credit_in_notice=s.notice is not None, fingerprint=fingerprint)
    if s.note:
        entry["note"] = s.note
    return entry


def build_entries(cons: dict, committed: dict | None, sources: list[Source] = SOURCES) -> list[dict]:
    """Measure every source; keep the committed entry for a source whose database is missing."""
    kept = {e["id"]: e for e in (committed or {}).get("sources", [])}
    out = []
    for s in sources:
        con = cons.get(s.db)
        if con is not None:
            out.append(measure(con, s))
        elif s.id in kept:
            out.append(kept[s.id])
    return out


def measure_actuals(cons: dict) -> dict:
    out = {}
    for k, (db, sql) in ACTUALS.items():
        con = cons.get(db)
        if con is None:
            continue
        try:
            out[k] = _scalar(con, sql)
        except sqlite3.Error:
            out[k] = None
    return out


def father_counts(cons: dict) -> dict | None:
    con = cons.get("study_bible")
    if con is None:
        return None
    return dict(con.execute("select father_name, count(*) from patristic_catena group by 1"))


def _import_paths() -> None:
    for p in (ROOT, ROOT / "src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def registered_tools() -> list[str] | None:
    """The tools the chat registers in Bible mode: the Study Bible MCP's TOOLS plus the in-process
    curriculum tools (webapp/app.py MCPBridge.start)."""
    _import_paths()
    try:
        from studybible_mcp.tools import TOOLS as mcp_tools
        from webapp.curriculum import TOOLS as course_tools
    except Exception:  # noqa: BLE001 (report it as skipped, never crash the check)
        return None
    return [t.name for t in mcp_tools] + [t["name"] for t in course_tools]


def registered_history_tools() -> list[str] | None:
    """The tools the chat registers in History mode: the Social Sciences MCP's TOOLS plus every Study
    Bible tool except the John-course tools (webapp/app.py chat(), CombinedTools)."""
    _import_paths()
    try:
        from socialsci_mcp.server import TOOLS as hist_tools
        from studybible_mcp.tools import TOOLS as mcp_tools
    except Exception:  # noqa: BLE001
        return None
    names = [t.name for t in hist_tools]
    return names + [t.name for t in mcp_tools if t.name not in names]


def source_token(url: str | None) -> str | None:
    """The part of a source URL that NOTICE and the /corpus credits must show: the repository or
    dataset name on GitHub or Hugging Face, otherwise the host."""
    if not url:
        return None
    u = urlparse(url.split()[0])
    host = u.netloc.lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]
    if host in ("github.com", "huggingface.co") and parts:
        return parts[-1]
    return host or None


# ------------------------------------------------------------------------------- comparing
def _num(s: str) -> float:
    return float(s.lstrip("~").replace(",", ""))


def page_drift(html: str, actual: dict, fathers: dict | None = None,
               tools: list[str] | None = None) -> list[str]:
    """Where /corpus disagrees with the databases (and with the registered tools)."""
    out = []
    for what, pat, key, how in PAGE_CLAIMS:
        if actual.get(key) is None:
            continue
        m = re.search(pat, html)
        if not m:
            out.append(f"/corpus: the claim '{what}' was not found on the page (layout changed?)")
            continue
        claimed, real = _num(m.group(1)), actual[key]
        if how == "millions":
            ok = round(real / 1e6, 1) == claimed
            real_s = f"{real / 1e6:.2f}M ({real:,})"
        else:
            ok = claimed == real
            real_s = f"{real:,}"
        if not ok:
            out.append(f"/corpus: {what} says {m.group(1)}, the database has {real_s}")

    pills = re.search(r"<h2>Creeds, confessions &amp; catechisms</h2>(.*?)</section>", html, re.S)
    if pills and actual.get("creeds") is not None:
        n = len(re.findall(r'<span class="pill">', pills.group(1)))
        if n != actual["creeds"]:
            out.append(f"/corpus: the creeds section shows {n} documents, the database has {actual['creeds']}")

    works = re.search(r'<script id="corpus-data" type="application/json">(.*?)</script>', html, re.S)
    if works and actual.get("theology_works") is not None:
        n = len(json.loads(works.group(1)))
        if n != actual["theology_works"]:
            out.append(f"/corpus: the full grounding list has {n} works, the database has "
                       f"{actual['theology_works']:,}")

    fj = re.search(r'<script id="fathers-data" type="application/json">(.*?)</script>', html, re.S)
    if fj and fathers is not None:
        page = {f["name"]: f["count"] for f in json.loads(fj.group(1))}
        missing = sorted(set(fathers) - set(page))
        extra = sorted(set(page) - set(fathers))
        changed = sorted(k for k in set(page) & set(fathers) if page[k] != fathers[k])
        if missing:
            out.append(f"/corpus: {len(missing)} catena authors are in the database but not on the page: "
                       + ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else ""))
        if extra:
            out.append(f"/corpus: {len(extra)} catena authors are on the page but not in the database: "
                       + ", ".join(extra[:8]) + (" ..." if len(extra) > 8 else ""))
        if changed:
            out.append(f"/corpus: {len(changed)} catena authors show a different entry count: "
                       + ", ".join(f"{k} {page[k]} vs {fathers[k]}" for k in changed[:5])
                       + (" ..." if len(changed) > 5 else ""))

    if tools is not None:
        # A list built at load from /api/config is checked through tool_catalog (catalog_drift). Anything
        # typed into the page, or a page with no live list, is compared with the registered tools here.
        shown = re.findall(r'<div class="tool">(\w+)</div>', html)
        m = re.search(r"persona &middot; (\d+) tools", html)
        live = all(p.search(html) for p in _LIVE_TOOL_LIST)
        if shown or not live:
            for name in sorted(set(tools) - set(shown)):
                out.append(f"/corpus: the chat registers {name}, which the page's tool list does not show")
            for name in sorted(set(shown) - set(tools)):
                out.append(f"/corpus: the page lists {name}, which the chat does not register")
        if m and int(m.group(1)) != len(tools):
            out.append(f"/corpus: the tools heading says {m.group(1)} tools, the chat registers {len(tools)} "
                       "in Bible mode")
    return out


def catalog_drift(bible_tools: list[str] | None, history_tools: list[str] | None, catalog=None) -> list[str]:
    """Where webapp/tool_catalog.py, which builds the tool list on /corpus and in the chat's info
    bubble, disagrees with the tools each mode registers."""
    if catalog is None:
        _import_paths()
        try:
            from webapp import tool_catalog as catalog
        except Exception:  # noqa: BLE001
            return []
    out = []
    for subject, label, tools in (("bible", "Bible", bible_tools), ("history", "History", history_tools)):
        if tools is None:
            continue
        grouped = {n for _, _, items in catalog._groups(subject) for n, _ in items}
        for name in sorted(set(tools) - grouped):
            out.append(f"tool_catalog: {name} is registered in {label} mode but has no group (it shows under "
                       "'Other tools' with its raw description)")
        for name in sorted(grouped - set(tools)):
            out.append(f"tool_catalog: lists {name} in {label} mode, which the chat does not register there")
    return out


def page_credit_drift(html: str, entries: list[dict], sources: list[Source] = SOURCES) -> list[str]:
    """Sources under CC BY or CC BY-SA that the page's credits section does not link. Chat users read
    excerpts of these sources and can reach /corpus from the chat; they never see NOTICE."""
    by_id = {s.id: s for s in sources}
    owed = [(by_id[e["id"]], source_token(by_id[e["id"]].url)) for e in entries
            if e["id"] in by_id and e.get("rows") and "CC BY" in by_id[e["id"]].license]
    owed = [(s, tok) for s, tok in owed if tok]
    if not owed:
        return []
    sec = _CREDITS_SECTION.search(html)
    if not sec:
        return ['/corpus: the page has no credits section (<section id="credits">) for its CC BY and '
                "CC BY-SA sources"]
    body = sec.group(1).lower()
    return [f"/corpus: the credits section does not link {s.name} ({s.license}; expected '{tok}')"
            for s, tok in owed if tok.lower() not in body]


def notice_drift(notice: str, entries: list[dict], sources: list[Source] = SOURCES,
                 actual: dict | None = None) -> list[str]:
    """Where NOTICE disagrees with the databases."""
    out = []
    by_id = {s.id: s for s in sources}
    head = _NOT_BUNDLED_HEADING.search(notice)
    bundled_part = notice[: head.start()] if head else notice
    for e in entries:
        s = by_id.get(e["id"])
        if s is None:
            continue
        has_rows = bool(e.get("rows"))
        named = bool(s.notice and re.search(s.notice, notice, re.I))
        if named and not has_rows:
            why = f" ({e['error']})" if "error" in e else ""
            out.append(f"NOTICE names {s.name}, and the database has no rows for it{why}")
        elif has_rows and s.notice and not named:
            out.append(f"NOTICE does not credit {s.name} ({e['count']:,} {e['unit']}, {s.license})")
        elif has_rows and not s.notice and s.db in MCP_DATABASES:
            out.append(f"NOTICE has no entry pattern for {s.name}; add one to SOURCES")
        elif named and head and not re.search(s.notice, bundled_part, re.I):
            out.append(f"NOTICE files {s.name} under 'Optional live-proxied translations (NOT bundled)', "
                       "and it is bundled")
        if named and has_rows:
            tok = source_token(s.url)
            if tok and tok.lower() not in notice.lower():
                out.append(f"NOTICE credits {s.name} without naming its source ({s.url})")
    for what, pat, key, mult in NOTICE_CLAIMS:
        real = (actual or {}).get(key)
        if real is None:
            continue
        m = re.search(pat, notice)
        if not m:
            out.append(f"NOTICE: the claim '{what}' was not found (wording changed?)")
            continue
        raw = m.group(1)
        claimed = _num(raw) * mult
        ok = abs(claimed - real) <= 0.02 * real if raw.startswith("~") else claimed == real
        if not ok:
            out.append(f"NOTICE: {what} says {raw}{'k' if mult == 1000 else ''}, the database has {real:,}")
    return out


def unregistered(cons: dict, sources: list[Source] = SOURCES) -> list[str]:
    """Database values and tables that no registered source accounts for."""
    out = []
    for db, table, key in DISCOVER:
        con = cons.get(db)
        if con is None:
            continue
        try:
            found = {r[0] for r in con.execute(f"select distinct {key} from {table}")}
        except sqlite3.Error:
            continue
        mine = [s for s in sources if s.db == db and s.table == table and s.key == key]
        covered = set()
        for s in mine:
            covered |= set(s.values) if s.values else {v for v in found if v not in s.exclude}
        for v in sorted(found - covered, key=str):
            out.append(f"{db}.{table}: {key} = {v!r} has no manifest entry")
    for db, con in cons.items():
        if con is None:
            continue
        claimed = {t for s in sources if s.db == db for t in (s.table, *s.tables)}
        for (name,) in con.execute("select name from sqlite_master where type='table'"):
            if name.startswith("sqlite_") or _INDEX_TABLE.search(name) or name in claimed:
                continue
            out.append(f"{db}: table {name} has no manifest entry")
    return out


def manifest_drift(committed: dict | None, entries: list[dict], present: set[str]) -> list[str]:
    """Where the committed manifest no longer matches the databases on this machine."""
    if committed is None:
        return ["docs/corpus-manifest.json does not exist; run scripts/corpus_manifest.py to write it"]
    old = {e["id"]: e for e in committed.get("sources", [])}
    out = []
    for e in entries:
        if e["database"] not in present:
            continue
        o = old.get(e["id"])
        if o is None:
            out.append(f"manifest: {e['id']} is not in the committed manifest")
        elif (o.get("count"), o.get("rows"), o.get("fingerprint")) != (e["count"], e["rows"], e["fingerprint"]):
            out.append(f"manifest: {e['id']} changed (count {o.get('count')} -> {e['count']}, rows "
                       f"{o.get('rows')} -> {e['rows']}); rerun scripts/corpus_manifest.py")
    for k, o in old.items():
        if o.get("database") in present and k not in {e["id"] for e in entries}:
            out.append(f"manifest: {k} is in the committed manifest but no longer registered")
    return out


# ------------------------------------------------------------------------------- main
def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def _load_manifest(p: Path) -> dict | None:
    text = _read(p)
    return json.loads(text) if text else None


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare only; exit 1 on any disagreement")
    args = ap.parse_args(argv)

    cons = open_databases(DB_DIR)
    present = {k for k, c in cons.items() if c is not None}
    for name in DATABASES:
        if name not in present:
            print(f"skipped: {DATABASES[name]} is not on this machine (its checks are not run; "
                  "committed manifest entries for it are kept)")
    if not present:
        print("No corpus databases found under db/. Nothing measured.")
        return 0

    committed = _load_manifest(MANIFEST)
    entries = build_entries(cons, committed)
    actual = measure_actuals(cons)

    drift: list[tuple[str, str]] = []
    page = _read(PAGE)
    if page is None:
        print(f"skipped: {PAGE.relative_to(ROOT)} not found")
    else:
        tools = registered_tools()
        if tools is None:
            print("skipped: the tool-list check (could not import the registered tools)")
        hist_tools = registered_history_tools()
        if hist_tools is None:
            print("skipped: the History-mode tool check (could not import the Social Sciences tools)")
        drift += [("/corpus", m) for m in page_drift(page, actual, father_counts(cons), tools)]
        drift += [("/corpus", m) for m in catalog_drift(tools, hist_tools)]
        drift += [("/corpus", m) for m in page_credit_drift(page, entries)]
    notice = _read(NOTICE)
    if notice is None:
        print("skipped: NOTICE not found")
    else:
        drift += [("NOTICE", m) for m in notice_drift(notice, entries, actual=actual)]
    drift += [("databases", m) for m in unregistered(cons)]
    drift += [("databases", f"{e['id']}: {e['error']}") for e in entries if "error" in e]

    if args.check:
        drift += [("manifest", m) for m in manifest_drift(committed, entries, present)]
    else:
        doc = {
            "about": "Every source the app serves from its SQLite corpora, with counts, licenses, and "
                     "fingerprints. Written by scripts/corpus_manifest.py; compare with --check.",
            "generated": dt.date.today().isoformat(),
            "fingerprint": "First 16 hex digits of a SHA-256 over each source's identity query (row count "
                           "and rowid range, per source key). It changes when rows are added, removed, or "
                           "regrouped, and does not see an in-place edit of a row's text.",
            "databases": DATABASES,
            "sources": entries,
        }
        if committed and committed.get("sources") == entries and committed.get("databases") == DATABASES:
            print(f"{MANIFEST.relative_to(ROOT)} is up to date ({len(entries)} sources); not rewritten")
        else:
            MANIFEST.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"wrote {MANIFEST.relative_to(ROOT)} ({len(entries)} sources)")
        for e in entries:
            print(f"  {e['database']:<16} {e['id']:<24} {e['count']:>10,} {e['unit']:<18} "
                  f"{e['rows']:>12,} rows  {e['license'][:44]}")

    if drift:
        print(f"\n{len(drift)} disagreement(s). NOTICE and corpus.html are corrected by hand:")
        for area in dict.fromkeys(a for a, _ in drift):
            print(f"\n[{area}]")
            for a, m in drift:
                if a == area:
                    print(f"  - {m}")
    else:
        print("\nNo disagreements: /corpus and NOTICE match the databases.")
    return 1 if (args.check and drift) else 0


if __name__ == "__main__":
    sys.exit(main())
