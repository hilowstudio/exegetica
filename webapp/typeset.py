"""Exegetica interior typesetting: a stored chapter's HTML -> the house markup the reader styles.

Every book reaches the reader through this pass, so the inside of every book shares one design:

* provenance is gone: transcriber's notes, digitizer and proofreader credits, distributor
  boilerplate, scan-source notes and printed page markers ("[Pg 6]", "{12}");
* the chapter heading becomes an opener: a small-capitals label ("Chapter Twelve") over a title
  set in proper case (sources shout theirs in capitals), with the book's ornament beneath;
* the first prose paragraph carries the drop cap and a small-capitals lead-in;
* scene breaks (rules, rows of asterisks) become ornament breaks;
* verse (a paragraph of short lines joined by <br>) becomes stanzas of lines, so it sets as verse;
* prose gets soft hyphens, so justified lines stay even in every browser.

The pass is pure and cached per chapter; stored HTML is never modified here.
"""
from __future__ import annotations

import functools
import re

from lxml import html as LH
from lxml.etree import ParserError

try:
    import pyphen
    _HY = pyphen.Pyphen(lang="en_US")
except Exception:  # noqa: BLE001 — hyphenation is a nicety, never a failure
    _HY = None

SHY = "­"

# ---------------------------------------------------------------- provenance
# Provenance that is unmistakable anywhere in a short block …
_PROVENANCE = re.compile(
    r"Project Gutenberg|gutenberg\.(?:org|net)|Distributed Proofread|\bpgdp\b|fadedpage|Faded Page|"
    r"Transcriber[’']?s?\s+[Nn]ote|Transcriber[’']?s?\s+[Cc]omment|Note from the transcriber|"
    r"\b(?:e-?text|ebook|e-book|HTML version)\b.{0,60}\b(?:produced|prepared|created)\b|"
    r"archive\.org|Digitized by Google|Online Distributed|HathiTrust|"
    r"Christian Classics Ethereal|ccel\.org|standardebooks\.org|Images? (?:generously )?made available by",
    re.I,
)
# … and credit lines that only count as the start of a short block ('Produced by Jane Doe and the Online …').
# Prose like 'the record prepared by the Harkers' must never match.
_CREDIT = re.compile(
    r"^\s*(?:this (?:e-?text|e-?book|book|file|edition) (?:was|has been) )?"
    r"(?:produced|prepared|transcribed|digiti[sz]ed|scanned|proofread|proofed|converted|html version)\s+(?:by|from)\b",
    re.I,
)
_PAGE_MARK = re.compile(r"\[\s*(?:Pg|Page|p)\.?\s*[\dIVXLCivxlc]+\s*\]|\{\s*\d{1,4}\s*\}(?=[\s <.,;:]|$)")
_IMPRINT = re.compile(                                       # title-page / imprint matter, safe on prose
    r"(?:Copyright|COPYRIGHT),?\s*(?:©|\(c\)|\(C\))?\s*(?:by\s+)?\d{4}|©\s*\d{4}|All rights reserved|ALL RIGHTS RESERVED|Library of Congress|"
    r"Printed in (?:the )?(?:United States|U\.\s?S\.\s?A|Great Britain|England)|PRINTED IN|Catalog(?:ue)? Card|Manufactured in the|"
    r"\bPUBLISHERS?\b|\bPublishers?\s*(?:$|[,.:]\s*(?:\d|[A-Z]{2}))|\b(?:Author|AUTHOR) of\b|"
    r"\b(?:FIRST|SECOND|THIRD|NEW) (?:EDITION|PRINTING|IMPRESSION)\b|"
    r"\b(?:LONDON|NEW YORK|BOSTON|PHILADELPHIA|EDINBURGH|CHICAGO|TORONTO|OXFORD|CAMBRIDGE)\b|"
    r"\b(?:London|New York|Boston|Philadelphia|Edinburgh|Chicago|Toronto|Oxford|Cambridge)\s*[:,]\s*(?:[A-Z][A-Za-z.&]+\s*){0,6},?\s*(?:M\s?D|\d{4})|"
    r"\bC\s?O\s?N\s?T\s?E\s?N\s?T\s?S\b|^Contents\b|"
    r"\b(?:WITH|With) (?:ILLUSTRATIONS|Illustrations|FRONTISPIECE|a Frontispiece)(?:\s+(?:by|in)\b|\s*$|\s*\.)|\bIllustrated by\b|ILLUSTRATED BY|"
    r"\bISBN\b|\bp\. cm\.|\bCIP\b|Cataloging-in|Originally published|Reprinted from the|Bison Book|Most recent printing|"
    r"^\s*PAGE\s*$|^\s*PAGE\s|\bPRICE\b|\[Pg [\dxivlc]+\]|^\s*[ivxlc]+\s*$")
_SECTION_START = re.compile(
    r"^(?:preface|the preface|introduction|introductory|foreword|prologue|prelude|proem|dedication|to the reader|argument|"
    r"chapter\s+(?:i|1|one|the first)\b|book\s+(?:i|1|one|the first)\b|part\s+(?:i|1|one|the first)\b|stave\s+(?:i|one)\b|"
    r"(?:author|editor|translator|publisher)[’']?s?[’']? (?:note|preface|introduction)|a note|note|preliminary|i\.?$|1\.?$)\b", re.I)
_BLOCKS = {"p", "div", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "li", "small", "pre"}

# ---------------------------------------------------------------- headings
_LABEL_WORDS = ("chapter", "book", "part", "stave", "canto", "letter", "section", "act", "scene", "lecture",
                "sermon", "volume", "fit", "song", "lesson", "discourse", "essay", "homily", "epistle", "psalm",
                "tale", "story", "day", "night", "chap", "serm", "lect", "bk", "ch")
_LABEL_FULL = {"chap": "Chapter", "ch": "Chapter", "serm": "Sermon", "lect": "Lecture", "bk": "Book"}
_NUM = r"(?:[IVXLCDM]+|\d+|[A-Za-z]+(?:-[A-Za-z]+)?)"
_LABEL = re.compile(rf"^\s*(?P<w>{'|'.join(re.escape(w) for w in _LABEL_WORDS)})\.?\s+(?P<n>{_NUM})\b\.?\s*(?:[:.—–-]\s*)?(?P<rest>.*)$", re.I | re.S)
_ROMAN = re.compile(r"^(?=[MDCLXVI])M*(?:C[MD]|D?C{0,3})(?:X[CL]|L?X{0,3})(?:I[XV]|V?I{0,3})\.?$")
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_SMALL = set("a an the and or nor but of in on at to by for with from as into upon via vs o'er".split())


def _roman_value(s: str) -> int | None:
    s = s.rstrip(".").upper()
    if not s or not _ROMAN.match(s):
        return None
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total


def _words(n: int) -> str:
    if n < 20:
        return _ONES[n].capitalize()
    if n < 100:
        t, o = divmod(n, 10)
        return _TENS[t].capitalize() + ("-" + _ONES[o].capitalize() if o else "")
    return str(n)


def _number_word(tok: str) -> str:
    """'XII' / '12' -> 'Twelve' (labels read as words, the way a printed book sets them)."""
    v = _roman_value(tok) if not tok.isdigit() else int(tok)
    if v is None:
        return tok[:1].upper() + tok[1:].lower()
    return _words(v) if v < 100 else tok.upper()


def proper_case(s: str) -> str:
    """Capitals -> title case; mixed-case text is trusted and left alone."""
    letters = [c for c in s if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) < 0.8 * len(letters):
        return s
    out, first = [], True
    for tok in re.split(r"(\s+|—|–)", s):
        if not tok.strip() or tok in ("—", "–"):
            out.append(tok)
            continue
        core = re.sub(r"[^\w'’]", "", tok)
        if _ROMAN.match(core.upper()) and len(core) > 1 or core in ("I",):
            out.append(tok)
        elif not first and core.lower() in _SMALL:
            out.append(tok.lower())
        else:
            low = tok.lower()
            out.append(re.sub(r"[a-zà-ÿ]", lambda m: m.group(0).upper(), low, count=1))
            out[-1] = re.sub(r"(?<=\bmc)([a-z])", lambda m: m.group(1).upper(), out[-1], flags=re.I)
        first = tok.rstrip().endswith((":", ".", "?", "!"))
    return "".join(out)


def split_heading(text: str) -> tuple[str, str]:
    """A source heading -> (label, title). 'CHAPTER I: THE FUGITIVES' -> ('Chapter One', 'The Fugitives');
    'XII.' -> ('', 'XII'); 'Marley’s Ghost' -> ('', 'Marley’s Ghost')."""
    t = re.sub(r"\s+", " ", text or "").strip().rstrip(".") if text else ""
    vol = ""
    while " · " in t:                                         # merge / de-duplication prefixes: 'Vol. 2 · ', 'XXI · '
        head, rest = t.split(" · ", 1)
        mv = re.fullmatch(r"(?i)(vol(?:ume)?|book|part|series)\.?\s+(\w+)", head.strip())
        if mv:
            vol = f"{_LABEL_FULL.get(mv.group(1).lower(), 'Volume' if mv.group(1).lower().startswith('vol') else mv.group(1).capitalize())} {_number_word(mv.group(2))}"
            t = rest
        elif len(head) <= 40 and (_roman_value(head) or head.isdigit() or _LABEL.match(rest) or _roman_value(rest.rstrip("."))
                                  or len(rest) <= 60):
            t = rest
        else:
            break
    t = t[:1].upper() + t[1:]
    if vol:
        label, title = split_heading(t)
        return (f"{vol} · {label}" if label else vol), title
    m = _LABEL.match(t)
    if m and (m.group("n")[:1].isdigit() or _roman_value(m.group("n")) or m.group("n").lower() in
              {w.lower() for w in _ONES + _TENS[2:]} or re.fullmatch(r"(?i)first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last|the\s+\w+", m.group("n"))):
        word = m.group("w").rstrip(".")
        word = _LABEL_FULL.get(word.lower(), word[:1].upper() + word[1:].lower())
        label = f"{word} {_number_word(m.group('n'))}"
        return label, proper_case(m.group("rest").strip(" .:—–-"))
    if _roman_value(t) or t.isdigit():
        return "", t.upper()
    return "", proper_case(t)


# ---------------------------------------------------------------- the pass
def _text(el) -> str:
    if not isinstance(el.tag, str):                          # comments, processing instructions
        return ""
    return re.sub(r"\s+", " ", el.text_content() or "").strip()


def _drop(el) -> None:
    """Remove an element but keep its tail text."""
    parent = el.getparent()
    if parent is None:
        return
    tail = el.tail
    if tail and tail.strip():
        prev = el.getprevious()
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail
    parent.remove(el)


def _is_break(el) -> bool:
    if el.tag == "hr":
        return True
    if el.tag in ("p", "div") and len(el) == 0:
        t = (el.text or "").replace(" ", " ").strip()
        return bool(t) and re.fullmatch(r"(?:[*·•.⁂✻❦§~_—-]\s*){2,}|[⁂❦§]", t) is not None
    return False


def _verse_lines(el) -> list[str] | None:
    """A <p> that is really verse: 2+ <br> and short lines -> each line's inner HTML."""
    brs = el.findall(".//br")
    if el.tag != "p" or len(brs) < 1:
        return None
    raw = LH.tostring(el, encoding="unicode", with_tail=False)
    inner = raw[raw.index(">") + 1: raw.rindex("<")]
    lines = [l.strip() for l in re.split(r"<br\s*/?>", inner)]
    lines = [l for l in lines if re.sub(r"<[^>]+>|&nbsp;|\s", "", l)]
    if len(lines) < 2:
        return None
    plain = [re.sub(r"<[^>]+>", "", l) for l in lines]
    long_ = sum(1 for l in plain if len(l) > 72)
    if long_ > len(lines) * 0.2:
        return None
    return lines


def _indent_of(line: str) -> int:
    m = re.match(r"^(?:\s|&nbsp;| )+", line)
    if not m:
        return 0
    n = m.group(0).count("&nbsp;") + m.group(0).count(" ") + m.group(0).count(" ")
    return 2 if n >= 6 else 1 if n >= 2 else 0


_TEX = re.compile(r"(\\\(.*?\\\)|\\\[.*?\\\])", re.S)   # a formula the reader typesets with KaTeX


def _outside_tex(s: str, fn) -> str:
    """Apply a text clean-up only outside TeX: in a formula "{54}" is a fraction's denominator, not a page marker."""
    parts = _TEX.split(s)
    for k in range(0, len(parts), 2):
        parts[k] = fn(parts[k])
    return "".join(parts)


def _hyphenate(el) -> None:
    if _HY is None:
        return

    def hy(s: str | None) -> str | None:
        if not s:
            return s
        # TeX between \( \) or \[ \] is left alone: a soft hyphen inside \triangle or bmatrix breaks the formula
        parts = _TEX.split(s)
        for k in range(0, len(parts), 2):
            parts[k] = re.sub(r"[A-Za-z]{7,}", lambda m: _HY.inserted(m.group(0), hyphen=SHY), parts[k])
        return "".join(parts)

    for node in el.iter():
        if node.tag in ("code", "pre", "abbr") or not isinstance(node.tag, str):
            continue
        node.text = hy(node.text)
        if node is not el:
            node.tail = hy(node.tail)


_LEAD_STOP = re.compile(r"^(.{6,34}?[,;:.!?—])(?=\s)|^((?:\S+\s+){2,4}?\S+)(?=\s)")


def _lead_in(p) -> bool:
    """Wrap the opening words of the first paragraph in small capitals; the drop cap is CSS."""
    if p.text is None or not p.text.strip():
        return False
    t = p.text.lstrip()
    m = _LEAD_STOP.match(t)
    if not m:
        return False
    lead = m.group(1) or m.group(2)
    if "\\(" in lead or "\\[" in lead:      # never cut a formula in two: end the lead-in before it
        lead = lead[:min(i for i in (lead.find("\\("), lead.find("\\[")) if i >= 0)].rstrip()
    if len(lead) < 6:
        return False
    span = LH.Element("span")
    span.set("class", "ex-lead")
    span.text = lead
    span.tail = t[len(lead):]
    p.text = ""
    p.insert(0, span)
    return True


def _make(tag: str, cls: str, text: str | None = None):
    e = LH.Element(tag)
    e.set("class", cls)
    if text:
        e.text = text
    return e


def _prose(t: str) -> bool:
    letters = [c for c in t if c.isalpha()]
    words = t.split()
    nums = sum(1 for w in words if re.fullmatch(r"\(?[\dxivlc]+[.,;)]?", w) and re.search(r"\d", w))
    return (len(t) >= 180 and bool(letters) and sum(c.islower() for c in letters) > 0.7 * len(letters)
            and nums < 0.04 * len(words) and not _IMPRINT.search(t[:300]))


def _trim_front(root) -> None:
    """A book's first chapter often opens on the source's title page, imprint and contents list; our
    own title page and contents replace them. Cut everything before the real opening (a section heading
    followed by prose, or the first prose paragraph), keeping dedications and epigraphs."""
    blocks = [k for k in root if isinstance(k.tag, str)]
    texts = [_text(b) for b in blocks]
    nonempty = [i for i, t in enumerate(texts) if t]
    nxt_of = {i: (texts[nonempty[k + 1]] if k + 1 < len(nonempty) else "") for k, i in enumerate(nonempty)}

    def opens(i: int) -> bool:                                # a section heading over prose, or prose
        return heading_over_prose(i) or _prose(texts[i])

    def heading_over_prose(i: int) -> bool:                  # any heading (not imprint) followed by prose
        t = texts[i]
        return (len(t) < 200 and _prose(nxt_of[i]) and not _IMPRINT.search(t)
                and (blocks[i].tag in ("h1", "h2", "h3", "h4", "h5", "h6") or bool(_SECTION_START.match(t))))

    anchor = next((i for i in nonempty if heading_over_prose(i) or (_prose(texts[i]) and _prose(nxt_of[i]))), None)
    if anchor is None:
        return
    signals = [i for i in nonempty if i < anchor and len(texts[i]) < 600 and (_IMPRINT.search(texts[i]) or re.fullmatch(
        r"(?i)(?:table of |list of )?(?:contents|illustrations)\.?|by", texts[i]))]
    if not signals:
        return
    start = next((i for i in nonempty if signals[-1] < i <= anchor and opens(i)), anchor)
    cut = " ".join(texts[:start])
    if len(cut.split()) > 2500:
        return
    pending_to = None                                         # a bare 'To' takes the dedicatee that follows
    for b, t in zip(blocks[:start], texts[:start]):
        if pending_to is not None and t and len(t) < 160 and not _IMPRINT.search(t):
            pending_to.text = f"To {proper_case(t.rstrip('.'))}"
            for ch in list(pending_to):
                pending_to.remove(ch)
            pending_to = None
            _drop(b)
            continue
        all_italic = bool(t) and len(t) < 500 and _text(b) == " ".join(_text(x) for x in b.iter("i", "em") if x.getparent() is not None
                                                                   and x.getparent().tag not in ("i", "em")).strip()
        verse = len(b.findall(".//br")) >= 1 or bool(re.search(r"[“\"‘']", t))
        if all_italic and verse and not _IMPRINT.search(t):   # an epigraph ('Son cœur est un luth suspendu…')
            if b.tag == "table":                              # set in a table cell for centring: lift it out
                bq = LH.Element("blockquote")
                for td in b.iter("td"):
                    p = LH.Element("p")
                    p.text = td.text
                    for ch in list(td):
                        p.append(ch)
                    bq.append(p)
                bq.tail = b.tail
                b.getparent().replace(b, bq)
                b = bq
            b.set("class", (b.get("class", "") + " ex-epi").strip())
            nb = b.getnext()
            while nb is not None and not _text(nb):
                nb = nb.getnext()
            if nb is not None and len(_text(nb)) <= 60 and not _IMPRINT.search(_text(nb)):
                nb.set("class", (nb.get("class", "") + " ex-epi ex-epi-by").strip())
            continue
        if "ex-epi" in (b.get("class") or ""):
            continue
        keep = b.tag == "blockquote" or (re.match(r"^(?:to|dedicated to|in memory of|these (?:stories|tales|pages|poems) are dedicated)\b",
                                                  t, re.I) and len(t) < 300 and not _IMPRINT.search(t))
        if keep:
            if b.tag != "blockquote":
                b.tag = "p"
            b.set("class", (b.get("class", "") + " ex-ded").strip())
            pending_to = b if t.strip(" .").lower() == "to" else None
        else:
            if t:
                pending_to = None
            _drop(b)
    if pending_to is not None:                                # a 'To' with no name is no dedication
        _drop(pending_to)


_AD = re.compile(
    r"\$\s?\d|\b(?:4to|8vo|12mo|16mo|18mo|24mo)\b|\bcloth\b|\bnet\b\.?|\bPublishers?\b|PUBLISHERS|Uniform with|UNIFORM WITH|"
    r"Each (?:volume|vol\.)|Now ready|NOW READY|By the same author|BY THE SAME AUTHOR|Send for (?:our )?catalogue|"
    r"\bCatalogue\b|CATALOGUE|\bPrice\b|\bPRICE\b|postpaid|post-paid|Popular Copyright|Ask your dealer|A\. ?L\. ?Burt|"
    r"Grosset|at all booksellers|Booksellers?\b|\d+s\. \d+d\.|\b\d+s\. net\b|Gilt top|gilt top|Half (?:Calf|Morocco|Leather)")


_TNOTE = re.compile(r"(?i)(?:obvious|minor|apparent) (?:print(?:er'?s)?|typographical|punctuation|spelling) errors|"
                    r"(?:full ?stop|comma|period|hyphen|quotation mark)s? (?:has|have) been (?:added|removed|corrected)|"
                    r"has been corrected to|were (?:silently )?corrected|retained as (?:printed|in the original)|"
                    r"cover image was created|illustrations have been (?:moved|repositioned)|this (?:e-?text|e-?book)")


def _trim_back(root) -> None:
    """A book's last chapter often ends in the source's advertisements ('12mo, cloth, $1.50 … Publishers')
    and a long transcriber's note. Cut that trailing run; keep 'THE END' as a closing mark."""
    blocks = [k for k in root if isinstance(k.tag, str)]
    texts = [_text(b) for b in blocks]
    total = sum(len(t.split()) for t in texts) or 1
    end = next((i for i, t in enumerate(texts) if re.fullmatch(r"(?i)the end\.?|finis\.?|the end of [\w ,'’]+\.?", t)), None)
    cut_from = None
    for i in range(len(blocks) - 1, -1, -1):                 # the trailing run of advertising
        t = texts[i]
        if not t:
            continue
        ad = (bool(_AD.search(t)) and (len(t) < 700 or len(_AD.findall(t)) >= 3)) or (len(t) < 300 and bool(_IMPRINT.search(t)))             or bool(_TNOTE.search(t))
        listing = len(t) < 140 and (t.isupper() or re.search(r"\b(?:By|BY)\s+[A-Z]", t)) and cut_from is not None
        if ad or listing or re.match(r"(?i)transcriber", t):
            cut_from = i
            continue
        break
    # 'THE END' itself licenses nothing: an author's closing note may follow it (Machen's 'Note.—Helen Vaughan
    # was born…'). Only the trailing run of advertising and transcriber matter found above is cut.
    if cut_from is None:
        return
    cut_words = sum(len(t.split()) for t in texts[cut_from:])
    ad_blocks = sum(1 for t in texts[cut_from:] if t and _AD.search(t))
    if cut_words > (0.9 if ad_blocks >= 5 else 0.4) * total:    # a long catalogue may outweigh the last pages
        return
    for b in blocks[cut_from:]:
        _drop(b)
    if end is not None and end < cut_from:
        blocks[end].tag = "p"
        blocks[end].set("class", "ex-fin")


_FRAGMENTS = {"the", "by", "a", "an", "of", "and", "in", "to", "with", "from"}
_PLACEHOLDER = re.compile(r"(?i)^\s*(?:section|part|chapter|untitled|text)\s+(?:\d+|one|two|three)\s*$|^\s*(?:section|untitled)\s*$")
_BR = object()
_BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul", "ol", "dl", "table", "hr", "header",
               "hgroup", "section", "figure", "pre", "article", "aside", "nav", "footer", "center"}


def _wrap_loose(root) -> None:
    """Loose text and inline runs at the top level (text trailing <br>s, bare <i>…</i>) become paragraphs;
    a double <br> starts a new one, a single <br> stays a line break inside it."""
    def flush(run: list, at: int) -> int:
        while run and run[-1] is _BR:
            run.pop()
        if not any(x is not _BR and ((isinstance(x, str) and x.strip()) or (not isinstance(x, str) and (x.text_content() or "").strip()))
                   for x in run):
            return at
        p = LH.Element("p")
        for x in run:
            if x is _BR:
                p.append(LH.Element("br"))
            elif isinstance(x, str):
                if len(p):
                    p[-1].tail = (p[-1].tail or "") + x
                else:
                    p.text = (p.text or "") + x
            else:
                p.append(x)
        root.insert(at, p)
        return at + 1

    items, out = [], []
    if root.text and root.text.strip():
        items.append(root.text)
    root.text = None
    for k in list(root):
        root.remove(k)
        tail, k.tail = k.tail, None
        if isinstance(k.tag, str):                            # comments and processing instructions go
            items.append(k)
        if tail and tail.strip():
            items.append(tail)
    run, brs, idx = [], 0, 0
    for x in items:
        if not isinstance(x, str) and isinstance(x.tag, str) and x.tag.lower() in _BLOCK_TAGS:
            idx = flush(run, idx)
            run, brs = [], 0
            root.insert(idx, x)
            idx += 1
        elif not isinstance(x, str) and x.tag == "br":
            brs += 1
            if brs >= 2:
                idx = flush(run, idx)
                run = []
            elif run:
                run.append(_BR)
        else:
            brs = 0
            run.append(x if isinstance(x, str) else x)
    flush(run, idx)


def incipit(html: str, words: int = 7) -> str:
    """A chapter named by its opening words, the old convention for untitled sections."""
    for m in re.finditer(r"(?is)<p\b[^>]*>(.*?)</p>", html or ""):
        t = _html_text(m.group(1))
        if len(t) > 40:
            ws = t.split()
            return " ".join(ws[:words]).rstrip(",;:—") + "…"
    return ""


def _html_text(h: str) -> str:
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", h))).replace(SHY, "").strip()


@functools.lru_cache(maxsize=512)
def typeset(html: str, toc_title: str = "", first: bool = False, last: bool = False) -> tuple[str, str, str]:
    """-> (house HTML, label, title)."""
    try:
        root = LH.fragment_fromstring(html or "<p></p>", create_parent="div")
    except (ParserError, ValueError):
        return html, "", toc_title

    # 1 · provenance + page markers
    for el in list(root.iter()):
        if not isinstance(el.tag, str) or el.getparent() is None:
            continue
        bt = _text(el)
        if el.tag in _BLOCKS and ((len(bt) < 900 and _PROVENANCE.search(bt)) or (len(bt) < 400 and _CREDIT.match(bt))):
            _drop(el)
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.text and _PAGE_MARK.search(el.text):
            el.text = _outside_tex(el.text, lambda s: _PAGE_MARK.sub("", s))
        if el.tail and _PAGE_MARK.search(el.tail):
            el.tail = _outside_tex(el.tail, lambda s: _PAGE_MARK.sub("", s))
    fragment = (toc_title or "").strip(" .:").lower() in _FRAGMENTS
    _wrap_loose(root)
    if first or fragment:                                     # a title page can sit inside any 'By' chapter
        _trim_front(root)
    if last:                                                  # the source's advertisements after the story
        _trim_back(root)

    # 2 · the opening heading
    label, title, head_sub = "", "", ""
    kids = [k for k in root if isinstance(k.tag, str)]
    while kids and kids[0].tag in ("br", "hr"):
        _drop(kids.pop(0))
    lead = [k for k in kids if re.search(r"\bex-(?:ded|epi)\b", k.get("class") or "")]
    kids = [k for k in kids if k not in lead]                 # dedications stay put beneath the opener
    if kids and kids[0].tag == "p" and len(_text(kids[0])) < 40 and re.fullmatch(
            r"(?i)(?:the )?(?:preface|introduction|introductory|foreword|prologue|advertisement|to the reader|dedication)\.?",
            _text(kids[0])):
        kids[0].tag = "h2"                                    # 'PREFACE.' set as its own paragraph is a heading
    head = kids[0] if kids and kids[0].tag in ("h1", "h2", "h3", "h4", "hgroup", "header") else None
    # a heading marked as the book's own (a school copy whose chapters really are 'Chapter One') is never taken
    # for an importer's placeholder
    keep = head is not None and "ex-keep" in (head.get("class") or "")
    if head is not None:
        if head.tag in ("hgroup", "header"):
            for bq in reversed(head.xpath(".//blockquote")):  # an epigraph inside the header follows the opener
                bq.getparent().remove(bq)
                bq.tail = None
                bq.set("class", (bq.get("class", "") + " ex-epi").strip())
                head.addnext(bq)
            hs = head.xpath(".//h1|.//h2|.//h3|.//h4")
            main = " ".join(_text(s) for s in hs[0].xpath("./span")) if hs and hs[0].xpath("./span") else (_text(hs[0]) if hs else "")
            subs = [_text(p) for p in head.xpath(".//p")]
            label, title = split_heading(main)
            if subs:
                label, title = (label or title), subs[0]
                head_sub = " ".join(subs[1:]).strip()            # '(Kept in shorthand.)' stays with the title
        else:
            ht = _text(head)
            nxt = head.getnext()
            while nxt is not None and not isinstance(nxt.tag, str):
                nxt = nxt.getnext()
            if ht.strip(" .:").lower() in ("the", "a", "an") and nxt is not None and len(_text(nxt)) < 120 and (
                    nxt.tag in ("h1", "h2", "h3", "h4", "h5") or (nxt.tag == "p" and _text(nxt).isupper())):
                # 'THE' + 'EMBROIDERESS OF TREVISO.' is one title
                ht = f"{ht} {_text(nxt)}"
                _drop(nxt)
            label, title = split_heading(ht)
        _drop(head)
        # a second heading straight after a bare label ('CHAPTER I' then 'THE FUGITIVES') is the title
        kids = [k for k in root if isinstance(k.tag, str)]
        if label and not title and kids and kids[0].tag in ("h2", "h3", "h4", "h5") and len(_text(kids[0])) < 120:
            title = proper_case(_text(kids[0]))
            _drop(kids[0])
    elif kids and kids[0].tag == "p" and kids[0].text and re.match(
            r"(?i)\s*(preface|introduction|introductory|foreword|prologue|advertisement|to the reader)[.:]\s+(?=\S)", kids[0].text):
        m = re.match(r"(?i)\s*(preface|introduction|introductory|foreword|prologue|advertisement|to the reader)[.:]\s+", kids[0].text)
        title = proper_case(m.group(1).upper()) if m.group(1).isupper() else m.group(1)[:1].upper() + m.group(1)[1:]
        kids[0].text = kids[0].text[m.end():]                 # 'PREFACE. The material…' -> heading + paragraph
    elif toc_title and not (first and (re.match(r"(?i)^by\b", toc_title) or _IMPRINT.search(toc_title) or len(toc_title) <= 3)):
        label, title = split_heading(toc_title)
    if label and not title:                                   # 'Chapter Twelve' alone reads as the title
        title, label = label, ""
    title = re.sub(r"\s*\[(?:\d{1,3}|[A-Z*†])\]", "", title).strip()   # a note marker never belongs in a title
    if title.strip(" .:").lower() in _FRAGMENTS or (_PLACEHOLDER.match(title) and not keep):   # torn-off words, importer placeholders
        title = ""
    title = re.sub(r"(?<![A-Z][a-z])(?<!\b[A-Z])(?<!\bSt)(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bCo)\.$", "", title).strip()  # a title ends without a period

    # 3 · inner headings, breaks, verse
    for h in root.xpath(".//h1|.//h2|.//h3|.//h4|.//h5|.//h6"):
        t = _text(h)
        if t:
            for ch in list(h):
                _drop(ch) if not _text(ch) else None
            h.text = proper_case(_text(h))
            for ch in list(h):
                h.remove(ch)
        h.set("class", "ex-sub")
    for el in list(root.iter()):
        if not isinstance(el.tag, str) or el.getparent() is None:
            continue
        if _is_break(el):
            brk = _make("div", "ex-brk")
            brk.set("role", "separator")
            for _ in range(3):
                brk.append(_make("i", "ex-o"))
            brk.tail = el.tail
            el.getparent().replace(el, brk)
    poem = None
    for el in list(root):
        if not isinstance(el.tag, str):
            continue
        lines = _verse_lines(el)
        if lines is None:
            poem = None
            continue
        st = _make("div", "ex-st")
        for line in lines:
            ind = _indent_of(line)
            frag = LH.fragment_fromstring(re.sub(r"^(?:\s|&nbsp;| )+", "", line) or " ", create_parent="span")
            frag.set("class", "ex-l" + (f" ex-i{ind}" if ind else ""))
            st.append(frag)
        if poem is None or poem.getnext() is not el:
            poem = _make("div", "ex-poem")
            el.addprevious(poem)
        poem.append(st)
        root.remove(el)
    # trailing / leading breaks never stand alone
    kids = [k for k in root if isinstance(k.tag, str)]
    while kids and "ex-brk" in (kids[0].get("class") or ""):
        _drop(kids.pop(0))
    while kids and "ex-brk" in (kids[-1].get("class") or ""):
        _drop(kids.pop())

    # 3b · a story byline straight after the heading ('by H. P. Lovecraft')
    for el in root:
        if not isinstance(el.tag, str):
            continue
        if el.tag == "p" and re.match(r"^by\s+\S", _text(el), re.I) and len(_text(el)) <= 70:
            el.set("class", "ex-by")
        break

    # 2a · headers inside the chapter ('Letter, Lucy Westenra to Mina Murray', 'Dr. Seward's Diary') are signposts
    for hd in root.iter("header", "hgroup"):
        if "ex-open" not in (hd.get("class") or ""):
            hd.set("class", (hd.get("class", "") + " ex-dochead").strip())
            for p in hd.iter("p"):
                p.text = proper_case(p.text) if p.text and not len(p) else p.text

    # 2b · a whole document quoted in the chapter (a journal, a letter) reads as the chapter's own text
    total_words = len(_text(root).split()) or 1
    for bq in [k for k in root if k.tag == "blockquote"]:
        if len(_text(bq).split()) > 0.4 * total_words:
            bq.set("class", (bq.get("class", "") + " ex-doc").strip())

    # 3a · footnotes first, so a note set under the heading is never taken for the opening paragraph
    _footnotes(root)

    # 3b2 · a chapter argument: 'The Mussulmaun religion.—Sectarians.—Their difference of faith.—…'
    for el in root:
        if not isinstance(el.tag, str) or not _text(el):
            continue
        if re.search(r"\bex-(?:ded|epi|by)\b", el.get("class") or "") or el.tag == "blockquote":
            continue
        t = _text(el)
        if el.tag == "p" and len(t) < 900 and len(re.findall(r"[.;]\s*[—–]\s*[A-Z]", t)) >= 2:
            el.set("class", (el.get("class", "") + " ex-arg").strip())
        break

    # 3c · an epigraph under the heading: a short quotation with its attribution
    tops = [k for k in root if isinstance(k.tag, str) and _text(k)][:4]
    for i, el in enumerate(tops):
        if re.search(r"\bex-(?:ded|by)\b", el.get("class") or ""):
            continue
        t = _text(el)
        nxt = _text(tops[i + 1]) if i + 1 < len(tops) else ""
        attributed = re.search(r"[—–]\s*[A-Z][^.!?]{1,60}\.?$", t) and len(t) < 500
        quote_then_by = (re.match(r"^[“\"‘']", t) or el.tag == "blockquote") and len(t) < 500 and re.match(r"^[—–-]\s*\S", nxt)
        if el.tag in ("p", "blockquote") and (attributed or quote_then_by):
            el.set("class", (el.get("class", "") + " ex-epi").strip())
            if quote_then_by:
                tops[i + 1].set("class", (tops[i + 1].get("class", "") + " ex-epi ex-epi-by").strip())
            break
        if len(t) > 500:
            break
    # 3d · a letter: dateline and salutation above the first paragraph
    for el in [k for k in root if isinstance(k.tag, str) and _text(k)][:3]:
        t = _text(el)
        if el.get("class"):
            continue
        if el.tag == "p" and len(t) <= 70 and re.match(
                r"^(?:my\s+)?(?:dear(?:est)?|honou?red|respected|beloved)\b.*[,:;!]$|^(?:sir|madam|gentlemen|ladies)[,:;!]$", t, re.I):
            el.set("class", "ex-salute")
            break
        if el.tag == "p" and len(t) <= 80 and re.search(r"\b1[5-9]\d\d\.?$|\b(?:January|February|March|April|May|June|July|August|"
                                                        r"September|October|November|December)\b.*\d", t) and not t.endswith((".”", "?")):
            el.set("class", "ex-dateline")
            continue
        break

    # 4 · the first prose paragraph: drop cap + lead-in
    flow = []
    for el in root:                                           # a whole-chapter document opens like the chapter itself
        flow += list(el) if "ex-doc" in (el.get("class") or "") else [el]
    for el in flow:
        if not isinstance(el.tag, str):
            continue
        if re.search(r"\bex-(?:ded|epi|by|salute|dateline|arg)\b", el.get("class") or "") or el.tag == "blockquote":
            continue                                          # dedications, epigraphs, bylines, letter heads sit above
        if el.tag == "p" and len(_text(el)) > 120:
            starts_inline = (el.text is None or not el.text.strip()) and len(el) and el[0].tag in ("i", "em", "b", "span")
            if _text(el)[:1].isdigit() or starts_inline:      # '3 May. Bistritz.—' : a dateline takes no drop cap
                el.set("class", (el.get("class", "") + " ex-first ex-nodrop").strip())
            else:
                el.set("class", (el.get("class", "") + " ex-first").strip())
                _lead_in(el)
            break
        if el.tag in ("p", "div") and _text(el):
            break

    # 4b · a closing signature / dateline: the last few short paragraphs after prose set flush right
    tail = []
    for el in reversed([k for k in root if isinstance(k.tag, str)]):
        t = _text(el)
        if el.tag == "p" and 0 < len(t) <= 60 and not el.get("class"):
            tail.append(el)
            continue
        break
    body_ps = [k for k in root if k.tag == "p" and len(_text(k)) > 120]
    if 0 < len(tail) <= 4 and body_ps:
        for el in tail:
            el.set("class", "ex-close")

    # 5 · hyphenation for prose
    for el in root.iter("p", "li", "blockquote"):
        if el.xpath("ancestor::*[contains(@class,'ex-poem')]"):
            continue
        _hyphenate(el)

    head_html = ""
    words = len(_html_text(LH.tostring(root, encoding="unicode")).split())
    part = bool(re.match(r"(?i)(?:part|book|volume|division|period|epoch|series)\b", label or title or "")) and words < 90
    if title or label:
        main, syn = synopsis(title)
        syn = " · ".join(x for x in (syn, head_sub) if x)
        head_html = (f'<header class="ex-open{" ex-part" if part else ""}">' + (f'<p class="ex-lab">{_esc(label)}</p>' if label else "")
                     + f'<h2 class="ex-t{" ex-num" if _roman_value(main) or main.isdigit() else ""}{" ex-long" if len(main) > 48 else ""}">{_esc(main)}</h2>'
                     + (f'<p class="ex-syn">{_esc(syn)}</p>' if syn else "")
                     + '<i class="ex-orn" aria-hidden="true"></i></header>')
    body = "".join(LH.tostring(k, encoding="unicode") for k in root)
    return head_html + body, label, title


_NOTE_START = re.compile(r"^\s*\[(\d{1,3}|[A-Z]|[*†‡§])\]\s*")
_REF = re.compile(r"(?<=[^\s\[])\[(\d{1,3}|[A-Z]|[*†‡§])\]")


def _footnotes(root) -> None:
    """'…the battlements[30]' with a '[30] Note text' paragraph -> a tappable reference and a gathered note.
    Also the linked form: <sup><a href="#n1">1</a></sup> with <p id="n1">… in a footnotes block."""
    notes: dict[str, object] = {}
    bare = [p for p in root.iter("p") if re.fullmatch(r"\s*\[\d{1,4}\]\s*", _text(p) or "x")]
    if len(bare) >= 1:                                        # "[172]" alone on a line: printed page numbers
        for p in bare:
            _drop(p)
        for el in root.iter():
            if isinstance(el.tag, str):
                if el.text:
                    el.text = re.sub(r"\s?\[\d{1,4}\](?=[\s,.;:]|$)", "", el.text)
                if el.tail:
                    el.tail = re.sub(r"\s?\[\d{1,4}\](?=[\s,.;:]|$)", "", el.tail)
        return
    for p in list(root.iter("p")):
        m = _NOTE_START.match(_text(p)) if p.text is not None or len(p) else None
        if m and p.text and _NOTE_START.match(p.text):
            key = m.group(1)
            if key in notes:
                continue
            p.text = _NOTE_START.sub("", p.text, count=1)
            notes[key] = p
    for div in root.xpath(".//div[contains(@class,'footnotes')]"):
        for p in div.iter("p"):
            pid = p.get("id")
            if pid:
                for a in p.xpath(".//sup[a]|.//a[@href]"):
                    (a.getparent() if a.tag == "a" and a.getparent() is not None and a.getparent().tag == "sup" else a).drop_tree()
                    break
                notes[f"#{pid}"] = p
    if not notes:
        return
    order: list[str] = []

    def ref_html(key: str) -> str:
        n = order.index(key) + 1 if key in order else (order.append(key) or len(order))
        return f'<a class="ex-ref" href="#fn{n}" data-fn="{n}" role="doc-noteref">{n}</a>'

    note_els = set(notes.values())

    def in_note(el) -> bool:
        return el in note_els or any(a in note_els for a in el.iterancestors())

    for el in list(root.iter()):                              # bracketed markers in running text
        if not isinstance(el.tag, str) or in_note(el):
            continue
        for attr in ("text", "tail"):
            s = getattr(el, attr)
            if not s or not _REF.search(s):
                continue
            if attr == "tail" and el.getparent() is not None and in_note(el.getparent()):
                continue
            parts = _REF.split(s)
            if not any(parts[i] in notes for i in range(1, len(parts), 2)):
                continue
            holder = LH.fragment_fromstring(_esc(parts[0]) + "".join(
                (ref_html(parts[i]) if parts[i] in notes else _esc(f"[{parts[i]}]")) + _esc(parts[i + 1])
                for i in range(1, len(parts), 2)), create_parent="span")
            if attr == "text":
                el.text = holder.text
                for j, ch in enumerate(list(holder)):
                    el.insert(j, ch)
            else:
                parent = el.getparent()
                el.tail = holder.text
                at = parent.index(el) + 1
                for j, ch in enumerate(list(holder)):
                    parent.insert(at + j, ch)
    for sup in root.xpath(".//sup[not(*)]"):                  # '<sup>[2]</sup>' / '<sup>2</sup>' with a note
        key = (sup.text or "").strip().strip("[]")
        if key in notes and not in_note(sup):
            a = LH.fragment_fromstring(ref_html(key))
            a.tail = sup.tail
            sup.getparent().replace(sup, a)
    for sup in root.xpath(".//sup[a[starts-with(@href,'#')]]"):  # linked superscript markers
        key = sup[0].get("href")
        if key in notes:
            a = LH.fragment_fromstring(ref_html(key))
            a.tail = sup.tail
            sup.getparent().replace(sup, a)
    for key in notes:                                         # notes whose marker sat in a heading still gather
        if key not in order:
            order.append(key)
    sec = LH.Element("section")
    sec.set("class", "ex-notes")
    sec.set("role", "doc-endnotes")
    for n, key in enumerate(order, 1):
        p = notes[key]
        if p.getparent() is not None:
            p.getparent().remove(p)
        p.tail = None
        p.set("class", "ex-note")
        p.set("id", f"fn{n}")
        num = LH.Element("span")
        num.set("class", "ex-note-n")
        num.text = str(n)
        num.tail = (" " + p.text) if p.text else " "
        p.text = None
        p.insert(0, num)
        sec.append(p)
    for div in root.xpath(".//div[contains(@class,'footnotes')]"):
        if not _text(div):
            div.getparent().remove(div)
    root.append(sec)


def synopsis(title: str) -> tuple[str, str]:
    """'Webster on his Way.—Wrecked Trains.—A Rescue' -> ('Webster on his Way', 'Wrecked Trains · A Rescue')."""
    parts = [p.strip(" .⁠") for p in re.split(r"\.?[\s⁠]*—[\s⁠]*(?=[A-Z\"“'‘])", title or "") if p.strip(" .⁠")]
    if len(parts) < 2 or len(title) < 50:
        return title, ""
    return parts[0], " · ".join(parts[1:])


def toc_entry(title: str, head_html: str = "", first: bool = False) -> tuple[str, str]:
    """Contents-page (label, name) for a chapter: read from the opening of its HTML when given (the
    stored title often lacks the chapter's name: 'Stave I' for 'Stave One · Marley's Ghost')."""
    body = ""
    if head_html:
        body, label, name = typeset.__wrapped__(head_html, title or "", first)
        if name and not (label and name == title):
            return label, name
    if (title or "").strip(" .:").lower() in _FRAGMENTS or _PLACEHOLDER.match(title or "") or \
            (first and (re.match(r"(?i)^by\b", title or "") or _IMPRINT.search(title or ""))):
        return "", incipit(body or head_html) or "Beginning"
    label, name = split_heading(title or "")
    return ("", label) if label and not name else (label, name)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
