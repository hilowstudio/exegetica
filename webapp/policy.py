"""
Server-side policy for every route that spends the server's API key: which model a request may
use, how far one run may go, and what a chat request may carry. These rules are enforced here in
code, so a browser cannot opt out of them by editing a field. See docs/decisions/.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Student chat always runs on this model. Another model reaches students only after it passes the
# safety ladder (docs/decisions/0004-student-chat-model.md).
STUDENT_MODEL = "claude-opus-5-5"

# Shown when the model declines a student's message. Student chat never falls back to another
# model, so a refusal ends the reply here.
REFUSAL_TEXT = ("Exegetica can't help with that. If something is weighing on you, talk with a "
                "parent, teacher, or pastor you trust, or open Need help now below.")


@dataclass(frozen=True)
class RunLimits:
    max_steps: int         # model calls in one run, tool rounds included
    max_tokens: int        # output cap per call
    max_usd: float         # estimated spend for the whole run
    locked: bool = False   # no model fallback of any kind (student chat)


STUDENT_CHAT = RunLimits(max_steps=8, max_tokens=16000, max_usd=1.0, locked=True)
TEACHER_CHAT = RunLimits(max_steps=8, max_tokens=16000, max_usd=1.0)
GENERATE = RunLimits(max_steps=12, max_tokens=64000, max_usd=5.0)
REVISE = RunLimits(max_steps=3, max_tokens=64000, max_usd=2.0)

# One study: 24 turns, a bounded transcript, and no single oversized message.
MAX_MESSAGES = 48
MAX_USER_CHARS = 8000
MAX_TRANSCRIPT_CHARS = 120000
MAX_TOOL_OUTPUT_CHARS = 4100   # the browser keeps tool outputs capped at 4,000 (providers._cap)
END_OF_STUDY = "This study has reached its length limit. Start a new study to keep going."
TOO_LONG = "That message is too long. Shorten it and send it again."

PERSONAS = {"professor", "aide", "researcher", "theologian", "study", "neutral"}

# Fixed replies, sent with no model call (docs/decisions/0011-fixed-replies-and-caps.md).
GREETING = {
    "bible": "Exegetica is a Bible-study tool. Ask about a passage, a Hebrew or Greek word, "
             "a person or place, or a unit in the Gospel of John.",
    "history": "Exegetica History is a research tool. Ask about a person, an event, a document, "
               "a court case, or a law.",
}
_GREETING = re.compile(
    r"^\s*(?:hi+|hello+|hey+|howdy|hiya|yo|greetings|good\s+(?:morning|afternoon|evening|day)|"
    r"what'?s\s+up|sup)(?:\s+(?:there|exegetica|everyone|all))?[\s!.,?~]*$", re.I)

# A student's study that goes this many replies in a row without a library tool gets a fixed
# reply instead of another model call. Long tool-free runs are where probing chats drift.
DRIFT_TURNS = 5
DRIFT_TEXT = ("Exegetica answers study questions from its library. Ask about a passage, a word, "
              "a person, or an event, or start a new study.")

# Fixed text for the provider path: raw SDK errors stay in the server log.
PROVIDER_ERROR = "Exegetica could not finish this reply. Try again in a minute."
TOOLS_DOWN = "The library is not responding right now. Try again in a minute."


def is_greeting(text: str) -> bool:
    """A bare greeting with no question in it."""
    return bool(_GREETING.match(text or ""))


def drifted(messages: list[dict]) -> bool:
    """True when the last DRIFT_TURNS assistant replies all ran without a library tool."""
    count = 0
    for m in reversed(messages):
        if m["role"] != "assistant":
            continue
        if m.get("tools"):
            return False
        count += 1
        if count >= DRIFT_TURNS:
            return True
    return False


def persona(value) -> str:
    return value if value in PERSONAS else "professor"


def clean_history(raw, tool_names: set[str]) -> tuple[list[dict] | None, str | None]:
    """Validate a browser-supplied transcript. Returns (messages, None) or (None, reason).

    Only plain-text turns and well-formed records of known tools pass, so native API blocks and
    invented tool names never reach the model. The record's contents are still the browser's word.
    """
    if not isinstance(raw, list) or not raw:
        return None, "no messages"
    if len(raw) > MAX_MESSAGES:
        return None, END_OF_STUDY
    out: list[dict] = []
    total = 0
    for m in raw:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            return None, "malformed message"
        content = m.get("content")
        if not isinstance(content, str):
            return None, "malformed message"
        if not content:
            continue
        if m["role"] == "user" and len(content) > MAX_USER_CHARS:
            return None, TOO_LONG
        msg = {"role": m["role"], "content": content}
        tools = m.get("tools")
        if m["role"] == "assistant" and tools:
            if not isinstance(tools, list):
                return None, "malformed message"
            records = []
            for t in tools:
                if not (isinstance(t, dict) and t.get("name") in tool_names
                        and isinstance(t.get("input") or {}, dict)
                        and isinstance(t.get("output") or "", str)
                        and len(t.get("output") or "") <= MAX_TOOL_OUTPUT_CHARS):
                    return None, "malformed message"
                records.append({"name": t["name"], "input": t.get("input") or {},
                                "output": t.get("output") or "", "is_error": bool(t.get("is_error"))})
                total += len(records[-1]["output"])
            msg["tools"] = records
        total += len(content)
        out.append(msg)
    if total > MAX_TRANSCRIPT_CHARS:
        return None, END_OF_STUDY
    if not out or out[-1]["role"] != "user":
        return None, "malformed message"
    return out, None
