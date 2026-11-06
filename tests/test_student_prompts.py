"""The prompts students actually get carry the conduct floor and none of the persona lines that
contradict it (docs/decisions/0001, 0006), attribute the doctrine and keep the method rules before
the floor (0021). No network; builds the prompts only."""
import importlib.util
import pathlib
import re

import pytest

from webapp import app

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _lint():
    spec = importlib.util.spec_from_file_location("lint_voice", ROOT / "scripts" / "lint_voice.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# Phrases from the pastors' persona and the old History prompt that must never reach students:
# a self that confesses or loves, a shepherd that listens for the heart, student sorting, praise,
# worship-leading, and a crisis number the safeguarding note forbids.
CONFLICTS = [
    "You confess", "in love with Jesus Christ", "Pastoral rather than professorial", "Listen first",
    "read the room", "You are softened by the cross", "Doxological landing", "Every prayer is Trinitarian",
    "remaining entirely yourself", "Stay fully in your established voice", "pastoral mind",
    "Confess that God rules", "## The room", "coasting", "Praise only what is earned", "988",
    "You are the Historian", "thinking as a faithful Christian historian",
]


@pytest.mark.parametrize("subject", ["bible", "history"])
def test_student_prompt_has_no_persona_conflicts(subject):
    prompt = app._system_for("professor", subject)
    found = [p for p in CONFLICTS if p in prompt]
    assert not found, f"{subject} prompt still contains: {found}"


@pytest.mark.parametrize("subject", ["bible", "history"])
def test_student_prompt_carries_the_floor_and_identity(subject):
    prompt = app._system_for("professor", subject)
    assert "## How you relate to the person" in prompt
    assert app.SELF_REPLY in prompt   # the one reply about Exegetica itself (decision 0001)
    assert "## If someone may be in danger" in prompt
    assert "Write with no first person" in prompt


def test_bible_prompt_attributes_doctrine():
    prompt = app._system_for("professor", "bible")
    assert "# The Reformed tradition" in prompt
    assert "never present them as Exegetica's own beliefs" in prompt
    assert 'never to Exegetica or "this library"' in prompt
    for gone in ("tradition this library follows", "This places the library", "rewrite it if the latter"):
        assert gone not in prompt, gone


def test_the_student_doctrine_tracks_the_shared_doctrine():
    """doctrine-student.md is doctrine.md attributed and trimmed (decision 0021). Its sections must
    still exist in the shared file, so an edit to one is noticed in the other."""
    shared = re.findall(r"^## (.+)$", (app.PROMPTS_DIR / "doctrine.md").read_text(encoding="utf-8"), re.M)
    student = (app.PROMPTS_DIR / "doctrine-student.md").read_text(encoding="utf-8")
    for head in re.findall(r"^## (.+)$", student, re.M):
        assert any(s.startswith(head) for s in shared), head
    for gone in ("## Style", "## Using the Study Bible tools", "## Anchors"):
        assert gone not in student


def test_method_study_order_and_plain_teaching_sit_before_the_floor():
    bible = app._system_for("professor", "bible")
    history = app._system_for("professor", "history")
    for section in ("## How Exegetica studies a passage", "## Plain teaching and real disagreement"):
        assert section in bible and section not in history
    order = ["# The Reformed tradition", "## Method", "## How Exegetica studies a passage",
             "## Plain teaching and real disagreement", "## How you relate to the person"]
    assert [bible.index(s) for s in order] == sorted(bible.index(s) for s in order)
    assert history.index("## Method") < history.index("## How you relate to the person")


def test_the_bible_prompt_asks_for_plain_answers_not_surveys():
    """Decision 0022: the 0021 procedure made every disputed-looking answer a survey."""
    bible = app._system_for("professor", "bible")
    assert "## Disputed questions" not in bible
    assert "then where Christians differ" not in bible
    assert "Say in the first sentence that Christians read it differently" not in bible
    assert "Say plainly what Scripture plainly teaches" in bible
    assert "only when the student asks how they compare" in bible


def test_greek_claims_rest_on_verses_the_answer_saw():
    """2026-11-06: every answer on John's "believe" gave verse examples of a Greek construction that it
    never opened, and most were wrong."""
    bible = app._system_for("professor", "bible")
    assert "search its occurrences in that book" in bible
    assert "cites only verses this answer has seen in the original" in bible


def test_bible_prompt_prose_names_no_tools():
    # Both models copied tool names from the prompt into replies in the 2026-11-05 bake-offs.
    prompt = app._system_for("professor", "bible")
    for name in ("lookup_verse", "get_passage", "get_confession", "word_study", "list_john_curriculum",
                 "get_reading_guide", "get_memory_verses", "get_course_schedule"):
        assert name not in prompt, name


@pytest.mark.parametrize("subject", ["bible", "history"])
def test_student_prompts_pass_their_own_voice_rules(subject):
    """The prompt is what the model imitates. The voice rules quote the tics they ban, so they are
    left out of the text checked."""
    text = app._system_for("professor", subject).replace(app._voice(), "")
    assert _lint().lint_text(text) == []
