"""The corpus manifest measures sources from the databases and reports where /corpus, NOTICE, or the
committed manifest disagree with them (scripts/corpus_manifest.py). Tiny fixtures only: no large
databases, no network."""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "scripts" / "corpus_manifest.py"
_spec = importlib.util.spec_from_file_location("corpus_manifest", _PATH)
cm = importlib.util.module_from_spec(_spec)
sys.modules["corpus_manifest"] = cm  # dataclasses look the module up while building Source
_spec.loader.exec_module(cm)

GILL = cm.Source("gill", "John Gill's Exposition", "study_bible", "commentaries", "Public domain",
                 "https://example.org", r"Gill", key="source", values=("john-gill",), unit="entries")
HENRY = cm.Source("henry", "Matthew Henry", "study_bible", "commentaries", "Public domain",
                  None, r"Matthew Henry", key="source", values=("matthew-henry",), unit="entries")
SOURCES = [GILL, HENRY]


@pytest.fixture
def con(tmp_path):
    c = sqlite3.connect(tmp_path / "study_bible.db")
    c.execute("create table commentaries (id integer primary key, source text, text text)")
    c.executemany("insert into commentaries (source, text) values (?, ?)",
                  [("john-gill", "a"), ("john-gill", "b"), ("matthew-henry", "c")])
    c.commit()
    yield c
    c.close()


def test_measure_counts_and_fingerprints(con):
    e = cm.measure(con, GILL)
    assert (e["count"], e["rows"], e["unit"]) == (2, 2, "entries")
    assert e["fingerprint"].startswith("sha256:") and e["credit_in_notice"]
    assert cm.measure(con, GILL)["fingerprint"] == e["fingerprint"]
    con.execute("insert into commentaries (source, text) values ('john-gill', 'd')")
    assert cm.measure(con, GILL)["fingerprint"] != e["fingerprint"]
    assert cm.measure(con, HENRY)["count"] == 1


def test_missing_table_is_an_error_entry_not_a_crash(con):
    s = cm.Source("x", "X", "study_bible", "no_such_table", "PD", None)
    e = cm.measure(con, s)
    assert e["count"] == 0 and "error" in e


def test_missing_database_keeps_the_committed_entry(con):
    committed = {"sources": [{"id": "gill", "database": "study_bible", "count": 9, "rows": 9}]}
    assert cm.build_entries({"study_bible": None}, committed, SOURCES) == committed["sources"]
    fresh = cm.build_entries({"study_bible": con}, committed, SOURCES)
    assert [e["count"] for e in fresh] == [2, 1]


def test_unregistered_values_and_tables_are_reported(con):
    con.execute("insert into commentaries (source, text) values ('barnes', 'e')")
    con.execute("create table new_corpus (id integer)")
    con.execute("create virtual table commentaries_fts using fts5(text)")
    out = cm.unregistered({"study_bible": con}, SOURCES)
    assert any("'barnes'" in m for m in out)
    assert any("table new_corpus" in m for m in out)
    assert not any("commentaries_fts" in m for m in out)


PAGE = """
<p class="lead"><b>9 public-domain commentaries</b>, a <b>3-author church-fathers catena</b></p>
<div class="sec-h"><h2>Commentaries</h2><span class="k">9 works &middot; verse-keyed</span></div>
<div class="sec-h"><h2>About the chat system</h2><span class="k">persona &middot; 2 tools</span></div>
<div class="tool">lookup_verse</div><div class="tool">get_passage</div>
<script id="fathers-data" type="application/json">[{"name": "Augustine", "count": 5}, {"name": "Jerome", "count": 2}]</script>
<script>var STATS = [[9, "Commentaries"]];</script>
"""


def test_page_matches():
    actual = {"commentaries": 9, "catena_authors": 2}
    out = cm.page_drift(PAGE.replace("3-author", "2-author"), actual,
                        {"Augustine": 5, "Jerome": 2}, ["lookup_verse", "get_passage"])
    assert out == []


def test_page_drift_is_reported():
    actual = {"commentaries": 10, "catena_authors": 2, "translations": 5}
    out = cm.page_drift(PAGE, actual, {"Augustine": 6, "Bede": 1},
                        ["lookup_verse", "get_passage", "get_course_schedule"])
    text = "\n".join(out)
    assert "public-domain commentaries says 9, the database has 10" in text
    assert "Commentaries heading says 9" in text
    assert "catena authors says 3, the database has 2" in text
    assert "Bible translations heading' was not found" in text
    assert "Bede" in text and "Jerome" in text and "Augustine 5 vs 6" in text
    assert "registers get_course_schedule" in text and "says 2 tools" in text


NOTICE = """Bundled data
- John Gill's Exposition. Public domain. Source: https://example.org
- Patristic catena. ~85,600
  public-domain church-father comment excerpts.

Optional live-proxied translations (NOT bundled; fetched at request time):
- Matthew Henry, listed here by mistake.
"""


def test_notice_drift():
    entries = [{"id": "gill", "count": 2, "unit": "entries", "rows": 2},
               {"id": "henry", "count": 1, "unit": "entries", "rows": 1}]
    out = cm.notice_drift(NOTICE, entries, SOURCES, actual={"catena_hcf": 85654})
    assert len(out) == 1 and "files Matthew Henry under" in out[0]

    out = cm.notice_drift(NOTICE.replace("John Gill's", "Someone's"), entries, SOURCES,
                          actual={"catena_hcf": 90000})
    text = "\n".join(out)
    assert "does not credit John Gill's Exposition" in text
    assert "says ~85,600, the database has 90,000" in text


def test_notice_names_a_source_with_no_rows():
    entries = [{"id": "gill", "count": 0, "unit": "entries", "rows": 0}]
    out = cm.notice_drift(NOTICE, entries, SOURCES)
    assert out == ["NOTICE names John Gill's Exposition, and the database has no rows for it"]


def test_notice_must_name_the_source_the_data_came_from():
    entries = [{"id": "gill", "count": 2, "unit": "entries", "rows": 2}]
    wrong = NOTICE.replace("https://example.org", "https://github.com/someone/other-repo")
    out = cm.notice_drift(wrong, entries, SOURCES)
    assert out == ["NOTICE credits John Gill's Exposition without naming its source (https://example.org)"]


def test_notice_claim_that_disappears_is_reported():
    entries = [{"id": "gill", "count": 2, "unit": "entries", "rows": 2}]
    out = cm.notice_drift(NOTICE.replace("~85,600", "many"), entries, SOURCES, actual={"catena_hcf": 85654})
    assert out == ["NOTICE: the claim 'HistoricalChristianFaith excerpts' was not found (wording changed?)"]


def test_source_token():
    assert cm.source_token("https://github.com/BibleAquifer/ACAI") == "ACAI"
    assert cm.source_token("https://huggingface.co/datasets/jncraton/ccel-paragraphs") == "ccel-paragraphs"
    assert cm.source_token("https://www.openbible.info/labs/cross-references/") == "openbible.info"
    assert cm.source_token("https://ebible.org (eng-Brenton)") == "ebible.org"
    assert cm.source_token(None) is None


LIVE = """<div class="sec-h"><h2>About the chat system</h2><span class="k" id="tkey">persona</span></div>
<div id="tool-groups"></div>
<script>fetch("/api/config").then(function(r){ return r.json(); });</script>"""


def test_live_tool_list_is_left_to_the_catalog():
    assert cm.page_drift(LIVE, {}, None, ["lookup_verse", "get_course_schedule"]) == []
    # With neither a live list nor a typed one, every registered tool is missing from the page.
    out = cm.page_drift(LIVE.replace('id="tool-groups"', ""), {}, None, ["lookup_verse"])
    assert out == ["/corpus: the chat registers lookup_verse, which the page's tool list does not show"]


def test_catalog_drift():
    import types
    fake = types.SimpleNamespace(_groups=lambda subject: [("Group", "sources", [("a", "A."), ("b", "B.")])])
    out = cm.catalog_drift(["a", "c"], None, catalog=fake)
    assert out == ["tool_catalog: c is registered in Bible mode but has no group (it shows under 'Other tools' "
                   "with its raw description)",
                   "tool_catalog: lists b in Bible mode, which the chat does not register there"]
    assert cm.catalog_drift(["a", "b"], ["a", "b"], catalog=fake) == []


def test_page_credit_drift():
    by = cm.Source("xr", "Cross-references", "study_bible", "cross_references", "CC BY 4.0",
                   "https://www.openbible.info/labs/cross-references/", r"OpenBible")
    sa = cm.Source("acai", "ACAI entities", "study_bible", "acai_entities", "CC BY-SA 4.0",
                   "https://github.com/BibleAquifer/ACAI", r"ACAI")
    pd = cm.Source("gill", "Gill", "study_bible", "commentaries", "Public domain", "https://example.org", r"Gill")
    entries = [{"id": s.id, "rows": 1} for s in (by, sa, pd)]
    page = '<section id="credits"><a href="https://www.openbible.info/">OpenBible</a></section>'
    out = cm.page_credit_drift(page, entries, [by, sa, pd])
    assert out == ["/corpus: the credits section does not link ACAI entities (CC BY-SA 4.0; expected 'ACAI')"]
    assert "no credits section" in cm.page_credit_drift("<p></p>", entries, [by, sa, pd])[0]
    assert cm.page_credit_drift("<p></p>", [{"id": "gill", "rows": 1}], [pd]) == []


def test_manifest_drift():
    e = {"id": "gill", "database": "study_bible", "count": 2, "rows": 2, "fingerprint": "sha256:a"}
    assert cm.manifest_drift({"sources": [e]}, [e], {"study_bible"}) == []
    changed = dict(e, rows=3, fingerprint="sha256:b")
    assert "gill changed" in cm.manifest_drift({"sources": [e]}, [changed], {"study_bible"})[0]
    assert cm.manifest_drift({"sources": [e]}, [changed], set()) == []
    assert "does not exist" in cm.manifest_drift(None, [e], {"study_bible"})[0]


def test_no_databases_is_skipped(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cm, "DB_DIR", tmp_path)
    assert cm.main(["--check"]) == 0
    assert "No corpus databases found" in capsys.readouterr().out
