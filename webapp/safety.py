"""
Stateless crisis-safety floor for the chat.

Exegetica has no accounts and stores nothing (a hard product constraint), so this is
deliberately only the *front half* of a safety system: a fast, in-the-moment check of
the user's own latest message that surfaces verified crisis resources in the UI. It
notifies no one, writes nothing, and calls no model.

Ported from the Quill & Compass "Thinkling" safety guard, reduced to the parts that fit
a stateless, account-free app: the regex pre-check and the verified resource list. The
classification tiers, caregiver-notification policy, flag storage, pattern escalation,
and parent alerts do NOT apply here — there is no one to notify and nothing is persisted.
A false positive only shows a gentle "Need help now?" panel, so the check errs toward
offering help rather than staying silent.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Verified crisis resources (pure data; safe to send to the client).
# Verified against official sources 2026-06 (ported from the Quill & Compass list).
# RE-VERIFY PERIODICALLY — numbers and links change.
# ---------------------------------------------------------------------------
CRISIS_RESOURCES: list[dict] = [
    {"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988",
     "url": "https://chat.988lifeline.org/", "note": "Free, private, and open all day, every day (US)."},
    {"name": "Childhelp National Child Abuse Hotline", "contact": "Call or text 1-800-422-4453 (text the word GO)",
     "url": "https://www.childhelphotline.org/", "note": "If someone is hurting you. Free and open all day, every day."},
    {"name": "Crisis Text Line", "contact": "Text HOME to 741741 (text HOLA for Spanish)",
     "url": "https://www.crisistextline.org/", "note": "Free texting support, all day, every day."},
    {"name": "Emergency services", "contact": "Call 911",
     "note": "If you or someone else is in immediate danger (US) — or your local emergency number."},
    {"name": "Find A Helpline", "contact": "Visit findahelpline.com",
     "url": "https://findahelpline.com/", "note": "Find a free, confidential helpline in your country."},
]

# Category -> which resources to lead with (most relevant first). The rest always follow,
# so the full set is offered every time — the category only reorders, never filters help away.
_PRIORITY: dict[str, list[str]] = {
    "SELF_HARM": ["988 Suicide & Crisis Lifeline", "Crisis Text Line"],
    "VIOLENCE": ["988 Suicide & Crisis Lifeline", "Emergency services"],
    "ABUSE": ["Childhelp National Child Abuse Hotline", "988 Suicide & Crisis Lifeline"],
}


def get_crisis_resources(category: str | None = None) -> list[dict]:
    """Resources ordered for the category (most relevant first), else canonical order.
    Always returns the complete list — the category only changes ordering."""
    priority = _PRIORITY.get(category or "", [])
    lead = [r for name in priority for r in CRISIS_RESOURCES if r["name"] == name]
    rest = [r for r in CRISIS_RESOURCES if r["name"] not in priority]
    return lead + rest


# ---------------------------------------------------------------------------
# Regex fast-path. Its ONLY job is deciding whether to surface the help panel;
# it classifies nothing further and stores nothing. Conservative by design.
# ---------------------------------------------------------------------------
# A genuine retraction must not trip the check ("I don't want to kill myself").
_NEGATION = re.compile(r"\b(not|never|don'?t want to)\b.{0,12}\b(kill|hurt|die|suicide)\b", re.I)

# Academic / fictional framing that makes an ambiguous reference benign
# ("an article about suicide", "for my history project"). Does NOT suppress the
# explicit first-person phrases below (those are marked exempt).
_WHITELIST = re.compile(
    r"\b(health class|biology|class|assignment|homework|project|essay|paper|report|"
    r"history|literature|novel|book|article|movie|film|character|story)\b", re.I)

# (pattern, category, exempt_from_whitelist)
_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    # Explicit first-person self-harm — no academic context makes these benign.
    (re.compile(r"\b(kill myself|killing myself|end my life|ending my life|"
                r"take my own life|want to die|wanna die|don'?t want to (live|be alive)|"
                r"hurt myself|hurting myself|cut myself|cutting myself|cut my wrists)\b", re.I),
     "SELF_HARM", True),
    # Bare references — legitimately appear in academic/awareness text, so whitelist-gated.
    (re.compile(r"\b(suicide|suicidal|self[-\s]?harm)\b", re.I), "SELF_HARM", False),
    # Physical abuse disclosure ("my dad hits me", "he beats me").
    (re.compile(r"\b(hit|hits|hitting|punch(?:ed|es)?|beat|beats|beating|kick(?:ed|s)?|"
                r"choke[ds]?|slap(?:ped|s)?|burn(?:ed|s)?)\s+me\b", re.I), "ABUSE", True),
    # Sexual-abuse disclosure — a person as subject + a contact verb aimed at "me".
    (re.compile(r"\b(mom|dad|father|mother|stepdad|stepmom|uncle|aunt|grandpa|grandma|"
                r"brother|sister|cousin|teacher|coach|babysitter|pastor|he|she|they)\b"
                r".{0,30}\b(touched|touches|grabbed|groped|forced|made me touch)\b.{0,20}\bme\b", re.I),
     "ABUSE", True),
    # Threat of violence toward others.
    (re.compile(r"\b(shoot|stab|kill|hurt)\b.{0,40}\b(them|him|her|people|everyone|"
                r"classmates?|the school|my school|my class)\b", re.I), "VIOLENCE", False),
]


def precheck(message: str) -> dict:
    """Return {'concern': bool, 'category': str|None}. Stateless and fail-quiet:
    any error, or blank input, yields no concern and never raises into the chat path."""
    try:
        if not message or not message.strip():
            return {"concern": False, "category": None}
        if _NEGATION.search(message):
            return {"concern": False, "category": None}
        whitelisted = bool(_WHITELIST.search(message))
        for rx, category, exempt in _PATTERNS:
            if whitelisted and not exempt:
                continue
            if rx.search(message):
                return {"concern": True, "category": category}
    except Exception:  # noqa: BLE001 — a screening heuristic must never break the chat
        pass
    return {"concern": False, "category": None}


def safeguarding_note() -> str:
    """Crisis-handling instructions appended to every mode's system prompt."""
    return (
        "\n\n---\n\n"
        "## If someone may be in danger\n"
        "If the person mentions self-harm, suicide, abuse, violence, or being hurt by someone, "
        "care comes before everything else:\n"
        "- Respond gently and take it seriously. Do not brush it off, minimize it, or turn it into "
        "a lesson — and do not offer therapy, a diagnosis, or step-by-step advice.\n"
        "- Acknowledge them simply and without alarm, in the impersonal voice: open with \"This "
        "matters.\" and say that they are not in trouble. Do not thank them, and do not mention "
        "your own concern or feelings.\n"
        "- Do NOT invent or recite phone numbers, hotlines, or websites of your own. This app shows "
        "verified crisis resources separately in a \"Need help now?\" panel — point them there.\n"
        "- Urge them to reach a trusted person right now: a parent, pastor, teacher, counselor, or good "
        "friend, and emergency services if they are in immediate danger. Then hand them to that real help "
        "rather than trying to carry it yourself."
    )
