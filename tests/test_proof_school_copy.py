"""The proofing tools for school copies (scripts/proof_school_copy.py): a hand correction is recorded only when it
matches the built book once and stays short, stray marks are found, and the measure gates trip. No network."""
import importlib.util
import json
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def tool(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("proof_school_copy", ROOT / "scripts" / "proof_school_copy.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    monkeypatch.setattr(m, "CACHE", tmp_path)
    monkeypatch.setattr(m, "_vocab", lambda: {"the", "light", "did", "not", "go", "out", "lord", "is", "in", "control"})
    d = tmp_path / "a-book"
    d.mkdir()
    (d / "work.md").write_text(
        "## Chapter One\n<!-- p5 -->\n\nbut the fight did not go out.\n\nThe Lord is | in control.\n\n"
        "The fight was over.\n\nthen it went on.\n", encoding="utf-8")
    (d / "book.json").write_text(json.dumps({"chapters": [], "fixes": []}), encoding="utf-8")
    (d / "pages.jsonl").write_text(json.dumps({"n": 5, "src": "text", "lines": []}) + "\n", encoding="utf-8")
    return m, d


def _fix(m, *args, near=None, all_=False):
    a = types.SimpleNamespace(slug="a-book", to_or_from=args[0], to=args[1] if len(args) > 1 else None,
                              near=near, all=all_)
    m.cmd_fix(a)


def test_a_fix_is_recorded_only_when_it_matches_once(tool):
    m, d = tool
    _fix(m, "the fight did not", "the light did not")
    assert json.loads((d / "book.json").read_text(encoding="utf-8"))["fixes"] == [["the fight did not", "the light did not"]]
    with pytest.raises(SystemExit):
        _fix(m, "fight", "light")                 # twice in the book: needs its own words around it
    with pytest.raises(SystemExit):
        _fix(m, "not in the book", "x")


def test_a_near_fix_stays_short_and_starts_once(tool):
    m, d = tool
    _fix(m, "Lord is in control.", near=("The Lord is", "control."))
    assert json.loads((d / "book.json").read_text(encoding="utf-8"))["fixes"][-1] == ["The Lord is | in control.", "Lord is in control."]
    (d / "work.md").write_text("The start " + "x " * 400 + "end", encoding="utf-8")
    with pytest.raises(SystemExit):
        _fix(m, "y", near=("The start", "end"))   # a span over 600 characters could swallow a chapter


def test_stray_marks_are_found(tool):
    m, d = tool
    m.cmd_marks(types.SimpleNamespace(slug="a-book"))
    assert "odd character" in (d / "marks.txt").read_text(encoding="utf-8")


def test_the_gates_trip_on_lowercase_paragraph_starts(tool, capsys):
    m, d = tool
    m.cmd_measure(types.SimpleNamespace(slug="a-book"))
    out = capsys.readouterr().out
    assert "start in lowercase" in out and "opening mid-sentence" in out


def test_the_skill_names_the_tools_and_the_rules():
    skill = (ROOT / ".claude" / "skills" / "school-copies" / "SKILL.md").read_text(encoding="utf-8")
    for s in ("proof_school_copy.py", "ingest_school_copy.py", "Never guess", "Restore what the book printed",
              "Sonnet at medium", "Opus at high", "only when Adam says"):
        assert s in skill, s
