"""The reply check drops praise and narration, stops affection and feeling, and leaves quotations,
Scripture, and ordinary answers exactly as written (webapp/reply_check.py). No network."""
import pytest

from webapp.reply_check import ReplyGate, check_sentence


def run(chunks):
    gate = ReplyGate()
    out = []
    for c in chunks:
        out += gate.feed(c)
    out += gate.flush()
    return "".join(out), gate


def test_the_reported_history_preamble_is_removed():
    text, gate = run(["Good question to go straight to the sources on. Let me pull the actual secession ",
                      "declarations and Alexander Stephens's Cornerstone Speech.\n\nSouth Carolina's declaration ",
                      "names slavery directly."])
    assert text == "\nSouth Carolina's declaration names slavery directly."
    assert gate.dropped == 2 and not gate.stopped


@pytest.mark.parametrize("sentence", [
    "Great question! ", "That's a good question. ", "What an insightful observation. ",
    "Let me look that up. ", "I'll check the commentaries first. ", "Let's look at John 3:16. ",
    "- I'm going to compare three translations.\n",
])
def test_praise_and_narration_are_dropped(sentence):
    assert check_sentence(sentence) == "drop"


@pytest.mark.parametrize("sentence", [
    "I love you. ", "In this conversation, I loved you. ", "Still love you too. ", "Love you.\n",
    "I'm so glad you asked. ", "I feel the weight of that question. ", "We care about you. ",
])
def test_affection_and_feeling_stop_the_reply(sentence):
    assert check_sentence(sentence) == "stop"


@pytest.mark.parametrize("sentence", [
    "> I am the bread of life; whoever comes to me shall not hunger.\n",
    "\"I am the way, and the truth, and the life\" (John 14:6). ",
    "Jesus said, \"I have overcome the world\" (John 16:33). ",
    "John records seven \"I am\" sayings. ",
    "Love your neighbor as yourself (Leviticus 19:18). ",
    "God loves you in Christ, as the Westminster Confession teaches. ",
    "World War I began in 1914. ",
    "Article I, Section 2 counted three-fifths of enslaved people. ",
    "1. The declaration of causes names slavery.\n",
])
def test_quotations_scripture_and_answers_pass(sentence):
    assert check_sentence(sentence) == "pass"


def test_stop_halts_everything_after_it():
    text, gate = run(["The text is clear. I love you. More text follows."])
    assert text == "The text is clear. " and gate.stopped


def test_a_sentence_split_across_chunks_is_checked_whole():
    text, gate = run(["Let me ", "pull the sources. ", "Here is the answer."])
    assert text == "Here is the answer." and gate.dropped == 1


def test_the_later_sentences_of_a_long_quotation_count_as_quoted():
    # John 15:9 inside a quotation that opened a sentence earlier
    text, gate = run(["Jesus said, “I am the vine. As the Father has loved me, so have I loved you.” ",
                      "The image is of dependence."])
    assert "so have I loved you" in text and not gate.stopped


def test_a_blank_line_closes_an_unmatched_quotation():
    text, gate = run(["He wrote a 12\" ruler.\n", "\n", "I love you. "])
    assert gate.stopped


def gated(chunks, ok):
    gate = ReplyGate(quote_ok=ok)
    out = []
    for c in chunks:
        out += gate.feed(c)
    return "".join(out + gate.flush()), gate


@pytest.mark.parametrize("chunks", [
    ["As the poem says, “I love you more than words.” "],
    ["“I love you,” it said. "],
    ["> I love you, and I always will.\n"],
    ["The letter reads, “Here is the news. ", "I love you and miss you.” ", "It ends there."],
])
def test_quoted_affection_no_source_holds_stops_the_reply(chunks):
    _, gate = gated(chunks, lambda quote: False)
    assert gate.stopped


def test_quoted_affection_a_source_holds_passes():
    seen = []
    text, gate = gated(["Jesus said, “As the Father has loved me, so have I loved you” (John 15:9). "],
                       lambda quote: seen.append(quote) or True)
    assert not gate.stopped and "so have I loved you" in text
    assert seen == ["As the Father has loved me, so have I loved you"]


def test_quotations_without_affection_are_never_looked_up():
    seen = []
    gated(["Jesus said, “I am the bread of life” (John 6:35). "], lambda quote: seen.append(quote) or False)
    assert seen == []


def test_unquoted_affection_after_a_quotation_still_stops():
    _, gate = gated(["“Grace and peace,” Paul writes, and I love you for asking. "], lambda quote: True)
    assert gate.stopped
