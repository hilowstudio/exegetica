"""
A check on every chat reply before it reaches the browser (docs/decisions/0001, proposal Layer 5).

Text is held one sentence at a time, a delay of about one sentence, and each sentence is checked
against the rules a pattern can enforce. A sentence that only praises the question or announces
the next step ("Good question...", "Let me pull...") is dropped. Em dashes outside quotations are
rewritten as colons or commas (docs/decisions/0019). A first-person claim of
affection or feeling stops the reply. Quotations and blockquotes are the source speaking, so
Scripture's own first person ("I am the bread of life") passes; the gate follows an open quotation
across sentences, so the later sentences of a long quotation count as quoted too. Given a source
check (webapp/citations.py), quoted affection passes only when this run's tool results or the
bundled Bible text hold the quotation, so quotation marks alone cannot carry it past the check.
These patterns are narrow on purpose: a false stop costs a student their answer, so only
phrasings the rules forbid outright are matched.
"""
from __future__ import annotations

import re
from typing import Callable

STOP_TEXT = ("Exegetica stopped this reply. Exegetica is software and has no feelings. If something is "
             "weighing on you, talk with a parent, teacher, or pastor you trust, or open Need help now with the lifesaver ring button.")

# A sentence ends at . ! ? (plus any closing quote or bracket) followed by space, or at a newline.
_BOUNDARY = re.compile(r"(?<=[.!?])[\"”’)\]]*[ \t]+|\n")
# List markers, headings, and bold that may open a line before the sentence itself.
_LEAD = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#+\s+)?(?:\*\*|__)?")

_PRAISE = re.compile(
    r"(?:what an?\s+|that'?s an?\s+|that is an?\s+)?(?:good|great|excellent|wonderful|fantastic|"
    r"interesting|fair|thoughtful|insightful|important|lovely)\s+(?:question|point|thought|observation)\b",
    re.I)
_NARRATION = re.compile(
    r"(?:let me|let's|let us|i'll|i will|i'm going to|i am going to|i've|i have|i can|i need to|"
    r"i want to|i'd|i would|i'm pulling|i'm looking|i'm checking)\b", re.I)
_AFFECTION = re.compile(
    r"\b(?:i|we)(?:\s+\w+){0,2}\s+(?:love|loved|loving|care about|cared about|cared for|miss|missed|adore)"
    r"\s+you\b|\blove you too\b|\bi(?:'m| am)\s+(?:so\s+|really\s+)?(?:glad|happy|proud|delighted|sad|"
    r"lonely|hurt)\b|\bi\s+(?:feel|felt)\b", re.I)
_SIGNOFF = re.compile(r"(?:still\s+)?love you\b", re.I)
# A line that opens with a list marker or heading, or with a bold or italic label, before an em dash.
_LIST_LEAD = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#+\s+)")
_LABEL_WORDS = 8


def split_quoted(text: str, open_quote: bool = False) -> tuple[str, str, bool]:
    """(unquoted text, quoted text, whether a quotation is still open at the end). Curly quotes open
    and close; a straight double quote toggles. Separate quotations in one sentence are joined with
    an ellipsis, which the source check splits on, so each is looked up on its own. Run together,
    two correct quotations once made one unfindable string ("believeLazarus has died") and stopped
    a reply."""
    plain, quoted = [], []
    inside = open_quote
    for ch in text:
        if ch == "“":
            inside = True
        elif ch == "”":
            inside = False
        elif ch == '"':
            inside = not inside
        else:
            (quoted if inside else plain).append(ch)
            continue
        if not inside and quoted and not "".join(quoted).endswith(" … "):
            quoted.append(" … ")
    return "".join(plain), "".join(quoted).rstrip(" …") if quoted else "", inside


# A short label before a verse set on its own line: "John 13:34 — ", "**Unit 18** ", "(ESV) ".
_VERSE_LABEL = re.compile(r"^[^.!?]{0,60}?(?:\*\*|—|\)|:\s)\s*")


def _source_speaks(sentence: str, quote_ok: Callable[[str], bool] | None) -> bool:
    """A sentence with no quotation marks that is, whole or after a short label, text this run's sources
    hold word for word, so its first person is the source's (docs/decisions/0016). A memory verse
    listed without quotation marks, "just as I have loved you", is John 13:34 speaking. A sentence that
    mixes the source's words with the bot's own is not held, and is checked as the bot's. Quoted text
    keeps the quotation rule."""
    if quote_ok is None:
        return False
    if quote_ok(sentence):
        return True
    m = _VERSE_LABEL.match(sentence)
    rest = sentence[m.end():] if m else ""
    return bool(rest.strip()) and quote_ok(rest)


def check_sentence(piece: str, quote_ok: Callable[[str], bool] | None = None, open_quote: bool = False) -> str:
    """'pass', 'drop', or 'stop' for one sentence of a reply.

    open_quote says the sentence begins inside a quotation left open by an earlier one. Without
    quote_ok, quoted text is exempt as before. With it, quoted text that matches the affection
    pattern passes only when quote_ok finds the quotation in a source.
    """
    s = piece.strip()
    if not s:
        return "pass"
    if s.startswith(">"):   # a blockquote line is quoted throughout
        body = s.lstrip(">").strip()
        if quote_ok is not None and _AFFECTION.search(body) and not quote_ok(body):
            return "stop"
        return "pass"
    bare = _LEAD.sub("", s, count=1)
    unquoted, quoted, _ = split_quoted(bare, open_quote)
    if bare[:1] in "‘'" and not open_quote:   # a single-quoted opening (‘…’) counts as quoted too
        unquoted, quoted = "", bare
    if (_AFFECTION.search(unquoted) or (not open_quote and _SIGNOFF.match(unquoted.strip()))) \
            and not (not quoted and _source_speaks(bare, quote_ok)):
        return "stop"
    if quoted and quote_ok is not None and _AFFECTION.search(quoted) and not quote_ok(quoted):
        return "stop"
    if not open_quote and bare[:1] not in "\"“‘'" and (_PRAISE.match(bare) or _NARRATION.match(bare)):
        return "drop"
    return "pass"


def mend_dashes(piece: str, open_quote: bool = False) -> str:
    """The sentence with each em dash outside quotation marks rewritten (docs/decisions/0019). The
    first one after a short label (a list item or heading, or bold or italic text) becomes a colon,
    "**Bread of life** — Jesus says" to "**Bread of life**: Jesus says". One that ends the text or
    meets punctuation goes. Any other becomes a comma, so a pair around an aside becomes two commas."""
    if "—" not in piece or piece.lstrip().startswith(">"):
        return piece
    out: list[str] = []
    inside = open_quote
    dashes_on_line = 0
    i = 0
    while i < len(piece):
        ch = piece[i]
        if ch == "“":
            inside = True
        elif ch == "”":
            inside = False
        elif ch == '"':
            inside = not inside
        elif ch == "\n":
            dashes_on_line = 0
        if ch != "—" or inside:
            out.append(ch)
            i += 1
            continue
        while out and out[-1] in " \t":
            out.pop()
        j = i + 1
        while j < len(piece) and piece[j] in " \t—":
            j += 1
        rest = piece[j:]
        line = "".join(out).rsplit("\n", 1)[-1]
        label = _LIST_LEAD.sub("", line, count=1).strip()
        # A numbered item reaches here without its "1." (the period ends a sentence), so bold that
        # opens the text counts as a label too.
        labelled = (_LIST_LEAD.match(line) or label.startswith(("**", "__"))
                    or label.endswith(("**", "__", "*", "_"))) and label.strip("*_ ")
        # A straight quote mark may open or close, so a dash beside one becomes a comma like any other.
        if not rest.strip() or rest[:1] in "\n.,;:!?)]”" or not out or out[-1] in "([“\n":
            pass
        elif labelled and dashes_on_line == 0 and len(label.split()) <= _LABEL_WORDS \
                and not re.search(r"[.!?;,](?:\s|$)", label):
            out.append(": ")
        else:
            out.append(", ")
        dashes_on_line += 1
        i = j
    return "".join(out)


class ReplyGate:
    """Feed streamed text in; get back only the sentences that pass, in order."""

    def __init__(self, quote_ok: Callable[[str], bool] | None = None) -> None:
        self.buf = ""
        self.stopped = False
        self.dropped = 0
        self.quote_ok = quote_ok
        self.in_quote = False   # a quotation opened in an earlier sentence and not yet closed

    def feed(self, text: str) -> list[str]:
        self.buf += text
        out: list[str] = []
        while not self.stopped:
            m = _BOUNDARY.search(self.buf)
            if not m:
                break
            piece, self.buf = self.buf[:m.end()], self.buf[m.end():]
            out.extend(self._check(piece))
        return out

    def flush(self) -> list[str]:
        """Release whatever is held (end of reply, or before a tool call so order is kept)."""
        piece, self.buf = self.buf, ""
        return self._check(piece) if piece and not self.stopped else []

    def _check(self, piece: str) -> list[str]:
        was_open = self.in_quote
        verdict = check_sentence(piece, self.quote_ok, self.in_quote)
        if "\n\n" in piece or piece.endswith("\n") and not piece.strip():
            self.in_quote = False   # a blank line ends any quotation left open
        elif not piece.lstrip().startswith(">"):
            self.in_quote = split_quoted(_LEAD.sub("", piece.strip(), count=1), self.in_quote)[2]
        if verdict == "stop":
            self.stopped = True
            return []
        if verdict == "drop":
            self.dropped += 1
            return []
        return [mend_dashes(piece, was_open)]
