"""The prompts students actually get carry the conduct floor and none of the persona lines that
contradict it (docs/decisions/0001, 0006). No network; builds the prompts only."""
import pytest

from webapp import app

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
    assert "## About Exegetica" in prompt
    assert "## If someone may be in danger" in prompt
    assert "Write with no first person" in prompt


def test_bible_prompt_attributes_doctrine():
    prompt = app._system_for("professor", "bible")
    assert "# The tradition this library follows" in prompt
    assert "never present them as Exegetica's own beliefs" in prompt
