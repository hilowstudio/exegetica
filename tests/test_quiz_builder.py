"""The chapter quizzes' Forms builder and print script read the same Markdown (scripts/build_forms_quiz.py).
Every quiz must parse, validate, and turn into Forms requests without a network call; matching lines and blanks
must become their own graded questions; and the points must add up to what the quiz says."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_forms_quiz as bfq  # noqa: E402

QUIZZES = sorted((ROOT / "docs" / "john" / "john-quizzes").glob("ch*-quiz.md"))


@pytest.mark.parametrize("path", QUIZZES, ids=lambda p: p.stem)
def test_every_quiz_builds(path):
    q = bfq.parse_quiz(path)
    assert bfq.validate(q) == []
    said = re.search(r"\*\*Total:\*\*\s*(\d+) points", path.read_text(encoding="utf-8"))
    assert said and q["total"] == int(said.group(1))
    reqs = bfq.form_requests(q)
    items = [r["createItem"]["item"] for r in reqs if "createItem" in r]
    assert [r["createItem"]["location"]["index"] for r in reqs if "createItem" in r] == list(range(len(items)))
    graded = sum(i["questionItem"]["question"]["grading"]["pointValue"] for i in items if "questionItem" in i)
    assert graded == q["total"]


def test_matching_and_blanks(tmp_path):
    md = tmp_path / "chXX-quiz.md"
    md.write_text("""# Test quiz: a title

> **Points:** multiple choice 3 each, matching 3 each, fill in the blank 3 each
> **Total:** 16 points

## Instructions (students see this)

Keep your Bible open.

## Part 1: questions

**1. A question?**
- A. One. ✓
- B. Two.

*Feedback: Because.*

**2. Who said it?**
Choices: Philip; Peter; Judas
- a. "Not enough." (6:7) → Philip
- b. "To whom shall we go?" (6:68) → Peter

*Feedback: John 6.*

**3. Fill in the blank: "I am the ______ of life" (6:35). (4 points)**
Answer: bread

*Feedback: John 6:35.*

## Teacher notes

Not on the form.
""", encoding="utf-8")
    q = bfq.parse_quiz(md)
    assert bfq.validate(q) == []
    assert [it["kind"] for it in q["items"]] == ["header", "mc", "match", "blank"]
    assert q["total"] == 3 + 3 * 2 + 4
    items = [r["createItem"]["item"] for r in bfq.form_requests(q) if "createItem" in r]
    drops = [i for i in items if i.get("questionItem", {}).get("question", {}).get("choiceQuestion", {}).get("type") == "DROP_DOWN"]
    assert [d["title"] for d in drops] == ['2a. "Not enough." (6:7)', '2b. "To whom shall we go?" (6:68)']
    assert drops[1]["questionItem"]["question"]["grading"]["correctAnswers"]["answers"] == [{"value": "Peter"}]
    blank = items[-1]["questionItem"]["question"]
    assert blank["textQuestion"] == {"paragraph": False} and blank["grading"]["pointValue"] == 4
    assert {"value": "Bread"} in blank["grading"]["correctAnswers"]["answers"]


def test_a_matching_answer_must_be_a_choice(tmp_path):
    md = tmp_path / "chYY-quiz.md"
    md.write_text("# T: t\n\n## Instructions\n\nx\n\n## Part 1: p\n\n**1. Who?**\nChoices: Philip; Peter\n"
                  "- a. A line. → Andrew\n\n*Feedback: f.*\n", encoding="utf-8")
    assert any("isn't one of the choices" in p for p in bfq.validate(bfq.parse_quiz(md)))
