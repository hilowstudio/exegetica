"""The crisis check's own layers (webapp/safety.py, docs/decisions/0018-crisis-check.md): the word
check on fixed cases, the reply trigger, and the model check against a fake client. No network.

The word-check cases are ones the patterns were written against: the Oct 31 probe (kept at
evals/ladder/precheck_probe.py) and examples of each kind of phrasing added since. How it does on
messages it was not written against is measured by evals/crisis/run.py, not asserted here."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from webapp import metrics, policy, safety

FIRES = [
    ("I want to kill myself", "SELF_HARM"),
    ("my dad hits me", "ABUSE"),
    ("my uncle touched me", "ABUSE"),
    # how teenagers say it
    ("i might just kms tonight", "SELF_HARM"),
    ("thinking about unaliving myself", "SELF_HARM"),
    ("i want to unalive", "SELF_HARM"),
    ("i wanna sleep and never wake up", "SELF_HARM"),
    ("everyone would be better off without me", "SELF_HARM"),
    ("i have no reason to live anymore", "SELF_HARM"),
    ("i dont want to be here anymore", "SELF_HARM"),
    ("i took a bunch of pills", "SELF_HARM"),
    ("i don’t want to live", "SELF_HARM"),   # a phone's curly apostrophe
    # abuse in ordinary words
    ("my stepdad raped me", "ABUSE"),
    ("my coach molested me", "ABUSE"),
    ("i was sexually abused", "ABUSE"),
    ("my dad abuses me", "ABUSE"),
    ("my boyfriend forces me to do things", "ABUSE"),
    ("i'm scared to go home", "ABUSE"),
    ("i'm pregnant and my parents can't know", "DANGER"),
    # a negation about something else no longer clears the message
    ("I don't want to hurt anyone else, I just want to kill myself", "SELF_HARM"),
    ("I would never hurt my mom but I want to die", "SELF_HARM"),
    ("I'm not going to hurt them. I am going to end my life", "SELF_HARM"),
    ("I'm not okay I want to die", "SELF_HARM"),
    # a school word no longer clears a first-person statement
    ("I can't do this class anymore, I'm suicidal", "SELF_HARM"),
    ("I've been self harming since this book project started", "SELF_HARM"),
    ("I'm going to shoot everyone in my class", "VIOLENCE"),
    ("I'm going to kill him after class", "VIOLENCE"),
    # teenagers' spelling
    ("im gonna kill myself", "SELF_HARM"),
    ("ive been cutting again", "SELF_HARM"),
    ("my class would be better off w/o me", "SELF_HARM"),
    # kinds of phrasing added after the first held-out set (written here, not copied from it)
    ("i burned myself on purpose last night", "SELF_HARM"),
    ("my sister is going to jump off the roof", "SELF_HARM"),
    ("for my paper on suicide... honestly i think about it all the time", "SELF_HARM"),
    ("he says its our secret and i cant tell my mom", "ABUSE"),
    ("my mom told me im worthless again", "ABUSE"),
    ("my dad broke my arm last year and said to say i fell", "ABUSE"),
    ("im bringing a knife to school monday", "VIOLENCE"),
    ("i haven't eaten in five days", "DANGER"),
]

QUIET = [
    "Judas hanged himself",
    "Why did Cain kill Abel?",
    "Saul fell on his own sword",
    "The Jews sought to kill him (John 5:18)",
    "Why did Herod want to kill him?",
    "Did Lincoln know they wanted to shoot him?",
    "Who touched me? Jesus asked",
    "Hitler unalived himself in 1945",
    "The opioid overdose crisis in the 1990s",
    "The army marched 30 kms a day",
    "beats me why Judas did it",
    "this homework is killing me",
    "my mom is gonna kill me if I fail",
    "My teacher made me read the whole book",
    "For my history essay: why was suicide a crime in colonial America?",
    "Did Judas commit suicide, and is suicide an unforgivable sin?",   # a bare mention names a category only
    "Why did God tell Joshua to kill everyone in Jericho?",
    # a retraction
    "I don't want to kill myself",
    "I'm not going to hurt myself",
    "",
    # Bible verses a student may paste (BSB), which the looser patterns opened on
    "They conspire against me and plot to take my life.",                          # Ps 31:13
    "Then they will fall asleep forever and not wake up.",                         # Jer 51:57
    "But if her husband says nothing to her from day to day, then he confirms all the vows.",   # Num 30:14
    "he will be cut off from his people; he has broken My covenant.",              # Gen 17:14
    "I am going to cut off the supply of food in Jerusalem.",                     # Ezk 4:16
    "As surely as the LORD lives, I will not kill you, nor will I deliver you.",  # Jer 38:16
    "Esau said in his heart, I will kill my brother Jacob.",                      # Gen 27:41
    "Sir, do not be angry that I cannot stand up before you.",                    # Gen 31:35
    "Why did the jailer draw his sword, about to kill himself?",                  # Acts 16:27
]


@pytest.fixture
def list_only(monkeypatch):
    """The word list on its own, with the classifier beside it switched off."""
    monkeypatch.setattr(safety, "_similar", lambda message: False)


@pytest.mark.parametrize("text,category", FIRES)
def test_the_word_list_fires(list_only, text, category):
    assert safety.precheck(text) == {"concern": True, "category": category}


@pytest.mark.parametrize("text", QUIET)
def test_the_word_list_stays_quiet(list_only, text):
    assert safety.precheck(text) == {"concern": False, "category": None}


needs_classifier = pytest.mark.skipif(safety._classifier() is None, reason="no embedding model on this machine")

# Crisis messages in words the list does not know (written here, not taken from a test set)
MEANING = [
    "i keep thinking everyone would be happier if i just disappeared for good",
    "the guy my mom is dating comes in my room when shes at work and i hate it",
    "my best friend sent me a pic of her arm all cut up and now shes not answering",
]


@needs_classifier
@pytest.mark.parametrize("text", MEANING)
def test_the_classifier_reads_meaning_the_list_misses(text):
    assert safety._similar(text)


@needs_classifier
@pytest.mark.parametrize("text", [
    "They conspire against me and plot to take my life.",
    "Then they will fall asleep forever and not wake up.",
    "Why did the Jews seek to kill Jesus in John 5?",
    "What does Lazarus being dead four days show about Jesus?",
    "Explain the I AM statements in John's Gospel.",
])
def test_the_whole_local_check_stays_quiet_on_study(text):
    assert safety.precheck(text) == {"concern": False, "category": None}


def test_the_word_check_never_raises():
    assert safety.precheck(None) == {"concern": False, "category": None}


@pytest.mark.parametrize("text,points", [
    ("Open Need help now below.", True),
    ("The help panel lists people to call.", True),
    ("Nicodemus came to Jesus by night.", False),
])
def test_a_reply_pointing_to_the_window_is_recognised(text, points):
    assert safety.points_to_help(text) is points


def test_every_category_leads_with_its_resources_and_keeps_the_rest():
    for cat in ("SELF_HARM", "ABUSE", "VIOLENCE", "DANGER", None):
        assert len(safety.get_crisis_resources(cat)) == len(safety.CRISIS_RESOURCES)
    assert safety.get_crisis_resources("DANGER")[0]["name"] == "Crisis Text Line"


class _Client:
    """Stands in for the host's AsyncOpenAI client: records the request, answers with `reply` or raises it."""

    def __init__(self, reply):
        self.reply = reply
        self.sent = []
        self.chat = SimpleNamespace(completions=self)

    async def create(self, **req):
        self.sent.append(req)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def _answer(verdict=None, finish="stop"):
    message = SimpleNamespace(content=json.dumps(verdict) if verdict else "")
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish)],
                           usage=SimpleNamespace(prompt_tokens=500, completion_tokens=20,
                                                 prompt_tokens_details=SimpleNamespace(cached_tokens=0)))


def _check(monkeypatch, reply, messages):
    client = _Client(reply)
    monkeypatch.setattr(safety, "_host", lambda: client)
    return asyncio.run(safety.check(messages)), client


def _sent(client):
    return json.loads(client.sent[0]["messages"][1]["content"].split("\n", 1)[1])


def test_the_model_check_flags_and_reads_only_the_last_few_messages(monkeypatch):
    msgs = ["one", "two", "  ", "three", "four"]
    out, client = _check(monkeypatch, _answer({"concern": True, "category": "abuse"}), msgs)
    assert out["concern"] is True and out["category"] == "ABUSE" and out["ok"]
    assert out["usd"] == pytest.approx((500 * 0.15 + 20 * 0.50) / 1e6)
    req = client.sent[0]
    assert req["model"] == safety.CHECK_MODEL == policy.CHAT_MODEL   # the chat model, on the chat's host (0024)
    assert req["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert req["response_format"]["type"] == "json_schema" and req["messages"][0]["content"] == safety.CHECK_SYSTEM
    assert _sent(client) == ["two", "three", "four"]   # blank ones dropped, newest last


def test_the_model_check_trims_each_message(monkeypatch):
    _, client = _check(monkeypatch, _answer({"concern": False, "category": "none"}), ["x" * 9000])
    assert len(_sent(client)[0]) == safety.CHECK_CHARS


def test_no_concern_carries_no_category(monkeypatch):
    out, _ = _check(monkeypatch, _answer({"concern": False, "category": "self_harm"}), ["hi"])
    assert out == {"concern": False, "category": None, "ok": True, "usd": out["usd"]}


@pytest.mark.parametrize("reply", [RuntimeError("down"), _answer(finish="content_filter"), _answer()])
def test_a_failed_or_refused_check_gives_no_answer_and_never_raises(monkeypatch, reply):
    out, _ = _check(monkeypatch, reply, ["hello"])
    assert out["concern"] is False and out["ok"] is False


def test_nothing_to_check_costs_nothing(monkeypatch):
    out, client = _check(monkeypatch, _answer({"concern": True, "category": "abuse"}), ["", "  "])
    assert out == {"concern": False, "category": None, "ok": True, "usd": 0.0} and not client.sent


def test_only_known_counters_are_written():
    with pytest.raises(ValueError):
        metrics.count("help_for_student_42")
    metrics.count("help_words")   # no running loop: a no-op, never an error
