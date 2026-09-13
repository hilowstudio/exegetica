"""
Tool definitions for the Study Bible MCP server.

Each tool is defined as an MCP Tool object with name, description, and input schema.

The server exposes read-only research data about the Bible: verse text in English
and the original Greek/Hebrew, Strong's lexicon entries, morphological parsing,
cross-reference datasets, a biblical people/places/events graph, published study
notes and dictionary articles, Ancient Near East background, theological
scholarship extracts, Torah literary-structure data, and MT/LXX/DSS textual
variants.

The datasets relate to one another through several shared keys, which is what
makes multi-tool research possible:

- **People and places** — entries carry family relationships (parents, siblings,
  spouse, children) and event/location links, so narratives can be traced across
  books.
- **Strong's numbers** — lexicon entries, verse word data, and concordance search
  share the same identifiers, so a term can be followed through its occurrences.
- **Verse references** — cross-references, study notes, ANE context, scholarship,
  Torah weave cells, and textual variants are all keyed by canonical reference.

Results are returned as Markdown text. Where a tool produces a diagram it is
emitted as a Mermaid code block within that text.
"""

import html
import json
import re

from mcp.types import Tool, ToolAnnotations

# Directionality/zero-width control characters that pollute BDB/LSJ definitions.
_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")


def _clean_lexicon_text(text: str | None) -> str:
    """Decode HTML entities (e.g. '&#x200E;') and strip invisible bidi/zero-width
    control marks that the BDB/LSJ source embeds."""
    if not text:
        return text or ""
    return _INVISIBLE.sub("", html.unescape(text))


def _parse_json_field(value, default=None):
    """Parse a JSON string field, returning default if parsing fails or value is already the right type."""
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _truncate(text: str, limit: int, suffix: str = "\n\n*[Truncated]*") -> str:
    """Truncate text to limit characters, appending suffix if truncated."""
    if len(text) <= limit:
        return text
    return text[:limit] + suffix

TOOLS = [
    Tool(
        name="word_study",
        annotations=ToolAnnotations(title="Word Study", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up the lexicon entry for a Strong's number, or for a Greek, Hebrew, or English word.

Given a Strong's number (G26, H430) the entry is returned directly; given an
English word, the most relevant Greek or Hebrew term is resolved first.

Returns:
- The word in its original script (e.g. ἀγάπη, אֱלֹהִים)
- Transliteration and pronunciation
- Strong's number
- Brief and full definitions (LSJ for Greek, BDB for Hebrew, plus Abbott-Smith
  for NT Greek where available)
- Etymology, semantic range, and related words
- Occurrence counts and representative passages

Relevant for questions about a specific original-language term, a theological
term's underlying vocabulary, or the semantic range behind an English rendering.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {
                    "type": "string",
                    "description": "Strong's number (e.g., 'G26' for agapē, 'H3068' for YHWH)"
                },
                "word": {
                    "type": "string",
                    "description": "English word to study (e.g., 'love', 'faith'). Will find the most relevant Greek/Hebrew term."
                },
                "language": {
                    "type": "string",
                    "enum": ["greek", "hebrew"],
                    "description": "Language to search if using 'word' parameter. Default: greek"
                }
            }
        }
    ),
    Tool(
        name="lookup_verse",
        annotations=ToolAnnotations(title="Lookup Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up a Bible verse in a readable modern translation, with the original language available.

Returns:
- The verse in a readable translation (default: BSB — Berean Standard Bible;
  also WEB, KJV, ASV, YLT via the `translation` argument)
- The original Greek/Hebrew text (optional, on by default)
- An optional word-by-word interlinear (Strong's + gloss + parsing) via include_morphology
- Genre-specific interpretive background for the passage's literary type
- An alternate-versification note where the verse is numbered differently in the Hebrew tradition

Accepts references such as 'John 3:16', 'Gen 1:1', or 'Jude 3'. For a multi-verse
passage or a whole chapter use `get_passage`; to see several translations at once
use `compare_translations`.

Relevant whenever the wording of a passage, or its original-language form, is needed.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference (e.g., 'John 3:16', 'Genesis 1:1', 'Jude 3')"
                },
                "translation": {
                    "type": "string",
                    "description": "Translation for the readable text: BSB (default), WEB, KJV, ASV, YLT (bundled), or ESV / NET (fetched live; ESV needs an ESV_API_KEY, NET is keyless)."
                },
                "include_original": {
                    "type": "boolean",
                    "description": "Include original Greek/Hebrew text. Default: true"
                },
                "include_morphology": {
                    "type": "boolean",
                    "description": "Include the word-by-word interlinear (Strong's, gloss, parsing). Default: false"
                },
                "reader_mode": {
                    "type": "boolean",
                    "description": "Append a reader-mode vocabulary list of the rarest original-language words in the verse (from corpus frequency). Default: false"
                },
                "vocab_threshold": {
                    "type": "integer",
                    "description": "With reader_mode, include words occurring at most this many times in the corpus. Default: 30"
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_passage",
        annotations=ToolAnnotations(title="Get Passage", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Return a readable passage — a verse range or a whole chapter — in one translation.

Gives the running text of a passage (each verse numbered) in a readable
translation. Use this for reading a pericope or chapter rather than a single
verse; use `lookup_verse` for one verse with original-language detail.

Accepts 'Romans 3:21-26', 'Psalm 23' (whole chapter), 'John 3:16', or 'Jude 3-5'.
Also serves the deuterocanon / apocrypha (Tobit, Judith, Wisdom, Sirach, Baruch,
1-4 Maccabees, 1-2 Esdras, Prayer of Manasseh, Greek Esther, Psalm 151, and the
additions Susanna / Bel and the Dragon / Letter of Jeremiah) from the WEB text,
which it selects automatically for those books.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Passage reference (e.g., 'Romans 3:21-26', 'Psalm 23')"
                },
                "translation": {
                    "type": "string",
                    "description": "Translation: BSB (default), WEB, KJV, ASV, YLT, or ESV / NET (fetched live)."
                },
                "reader_mode": {
                    "type": "boolean",
                    "description": "Append a reader-mode vocabulary list of the rarest original-language words across the passage. Default: false"
                },
                "vocab_threshold": {
                    "type": "integer",
                    "description": "With reader_mode, include words occurring at most this many times in the corpus. Default: 30"
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="compare_translations",
        annotations=ToolAnnotations(title="Compare Translations", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Show a single verse across several English translations side by side.

Displays the verse in each requested translation (or all bundled translations if
none are named), for comparing renderings. Bundled translations: BSB, WEB, KJV,
ASV, YLT (all public domain).

Relevant for comparing how translations render a verse, or checking a literal
(YLT/ASV) against a readable (BSB/WEB) rendering.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference (e.g., 'John 3:16')"
                },
                "translations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of translations to compare (e.g., ['BSB','KJV','YLT']). Omit for all."
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="vocabulary_list",
        annotations=ToolAnnotations(title="Vocabulary List", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""List the rarest original-language words in a passage (reader-mode vocabulary).

For a passage, returns the Hebrew/Greek words whose corpus frequency is at or
below a threshold — the words a reader is least likely to know — each with its
gloss, Strong's number, and how many times it occurs in the whole tagged Bible,
rarest first. Frequency is computed from the owned STEPBible tags.

Relevant for preparing to read a passage in the original language, building a
vocabulary list for study, or gauging which words in a text are uncommon.
Covers the Hebrew Old Testament and Greek New Testament (the tagged corpus).""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Passage reference (e.g., 'Romans 3:21-26', 'Jonah 1', 'John 1:1-5')"
                },
                "threshold": {
                    "type": "integer",
                    "description": "Include words occurring at most this many times across the corpus. Default: 30 (lower = rarer words only)."
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="search_lexicon",
        annotations=ToolAnnotations(title="Search Lexicon", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Search the Greek and Hebrew lexicons by English word, transliteration, or concept.

Returns the matching lexicon entries ranked by relevance — typically several
distinct original-language words that an English term covers (e.g. "love" →
agapē, phileō, erōs), each with its Strong's number, definition, and semantic
range.

Relevant for identifying which original-language terms lie behind an English
word or a biblical concept, and for distinguishing between near-synonyms.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (English word, transliteration, or concept)"
                },
                "language": {
                    "type": "string",
                    "enum": ["greek", "hebrew"],
                    "description": "Limit search to one language. Omit to search both."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return. Default: 10"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_cross_references",
        annotations=ToolAnnotations(title="Cross References", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve the cross-references for a Bible reference — the passages traditionally read alongside it — or a curated chain of passages for a doctrinal theme.

Two modes:

**By verse reference** (most common). Pass `reference="John 3:16"` (or any
canonical verse) to get the passages historically read alongside it. The
database draws from four scholarly sources, returned in a three-tier ranking:

  **Tier 3 (top, "consensus and curated"):**
    - **CH** — Harrison & Romhild's curated dataset (~58k links, OT-only as
      source). Hand-vetted; high-relevance pairs flagged canonical-direction.
    - **Gage parallel** — the tighter pairings from Warren Gage's John ↔
      Revelation typological reading (Bradley/Gage, John/Rev only).
    - **TSK ≥100 votes** — TSK pairs with crowd-source consensus that strong
      are near-universal cross-references (top ~0.4% of TSK) and break
      through to compete with curated.

  **Tier 2 ("argued and acknowledged"):**
    - **Burnett** — David A. Burnett's argued chain for the Gen 15:5 / Rom
      4:18 "star-like seed" deification reading (JSPL 5.2, 2015). ~30 pairs.
    - **Gage chiastic** — the looser-typology sheet of Bradley/Gage (the
      source spreadsheet labels these "looser connections, just noting").
    - **TSK 20–99 votes** — solid topical links acknowledged across
      commentaries (top ~5%).

  **Tier 1 (long-tail):** TSK <20 votes — surface only when explicitly raising
  `limit` for exhaustive study.

Results typically include the texts the verse quotes, its fulfilment passages,
contested parallel readings, and the later authors who picked the verse up.

**By theme**. Pass `theme="atonement"` (or `salvation_by_grace`, `deity_of_christ`,
`resurrection`, `holy_spirit`, `justification`) to get a hand-curated chain
of foundational passages for that doctrine — relevant for broad theological
questions not anchored to a specific verse.

**Coverage caveat.** TSK is built on R.A. Torrey's 19th-century
index, which catalogues **topical/thematic** connections — not necessarily
direct quotations or verbal allusions. Consequence: a verse with few cross-refs
here is NOT necessarily a verse with few biblical echoes. Famously,
Revelation shows surprisingly few links to OT prophetic books even though
it is saturated with OT symbolism, because Torrey indexed by subject and
Revelation's subject is "apocalyptic". The CH dataset partly compensates
(it leans toward NT-quotes-OT linking), so `source="ch"` may surface a
quotation or allusion the topical index misses, as may `find_similar_passages`
for verbal parallels.

**Adaptive default — `limit` is a cap, not a target.** Default `limit=8`. Rows
are returned in tier-then-strength order, and tier-1 noise (low-vote TSK) is
suppressed by default whenever the verse has at least 3 rows from tier 2+. So:

  - Signal-rich anchors return 6–8 strong refs spanning curated, scholarly,
    and consensus-TSK sources.
  - Signal-poor anchors return only what passes the bar; a short result set
    means the verse has few well-attested links, not that the query failed.

For the long tail, `source="tsk"` returns all TSK rows including tier 1, and
`min_strength=0` sets an explicit floor of zero. Either disables tier-1
suppression; both pair with a higher `limit` (20–30).

**Interpreting the scores.** Each row carries `type` (the dataset),
`relevance` (its native strength signal), and where applicable a `tsk_votes`
side-channel showing the TSK count for that pair. The scales differ by
dataset:

  TSK vote scale (full corpus distribution):
    ≥ 500 votes  — extraordinary; near-universal cross-reference (top 0.01%, only 35 pairs)
    100-499      — very strong; the link tradition reflexively makes (top 0.4%)
     50-99       — strong; well-established parallel (top 1.3%)
     20-49       — solid; real connection acknowledged across commentaries (top 5%)
     10-19       — moderate; one of many recognised links (top 12%)
      5-9        — weak; thematic stretch, use with caution (top 33%)
      2-4        — very weak; mostly noise floor (62% of TSK)
      0-1        — noise

  CH (curated — all CH refs carry signal; the tag indicates weight):
    "canonical direction" (rel=3 or 2) — Harrison's flag for the canonical
        direction of the pair, often part of a thematic circle (top 78% of CH)
    no tag (rel=0) — present in CH but unflagged (still hand-curated)

  Gage (John ↔ Revelation typology):
    relevance=3 ("parallel" tier) — tighter pairings from the parallel-reading
        of John 1 ↔ Revelation 1
    relevance=1 ("chiastic" tier) — looser thematic echoes across the full
        John-Revelation chiasm; the source spreadsheet flags these as
        "looser connections, just noting"
    The `note` field carries the thematic tags + commentary + per-row
    attribution (Bradley vs Gage). Treat as canonical-typology, not topical.

  Burnett (single-paper argued chain):
    All Burnett rows are at relevance=5 by convention — they're explicit
    claims from one scholar's published argument, not graded by strength.
    The `note` field carries the JSPL citation and which step of the argument
    the pair belongs to. They represent a single scholarly proposal rather
    than consensus.

A result whose strongest row has only 5–15 votes indicates a verse the topical
index does not treat as a major thematic anchor — a materially weaker signal
than a 200-vote parallel. For such verses `source="ch"` (Harrison's curated
set, which leans toward NT-quotes-OT links) and `find_similar_passages`
(verbal/semantic parallels Torrey did not index) cover different ground.

The `source` parameter restricts results to a single dataset — useful when CH
alone gives too little coverage for an obscure verse, or when the dense TSK
long-tail is wanted.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference to find cross-references for (e.g. 'John 3:16', 'Rom 3:23')."
                },
                "theme": {
                    "type": "string",
                    "description": "Theological theme. One of: salvation_by_grace, deity_of_christ, atonement, resurrection, holy_spirit, justification."
                },
                "source": {
                    "type": "string",
                    "enum": ["ch", "tsk", "gage", "burnett"],
                    "description": "Optional dataset filter when using `reference`. 'ch' = Harrison/Romhild curated; 'tsk' = Treasury of Scripture Knowledge; 'gage' = Gage/Bradley John↔Revelation typology; 'burnett' = Burnett's Gen 15:5 / Rom 4:18 deification chain (JSPL 5.2). Default: all four, ranked CH/Gage > Burnett > TSK."
                },
                "limit": {
                    "type": "integer",
                    "description": "Cap on rows returned (not a target). Default 8. The returned count may be smaller when the verse has fewer rows above the noise floor. Values of 20–30 combined with `source='tsk'` or `min_strength=0` return the long tail."
                },
                "min_strength": {
                    "type": "integer",
                    "description": "Strength floor for TSK refs (vote count). TSK pairs below this are excluded; CH/Gage/Burnett refs are exempt from this floor, being hand-curated or scholarly-argued. Setting this also disables the default tier-1 suppression, since it specifies an explicit floor. Sensible thresholds: 0 (include long-tail), 5 (drops bottom ~75%% of TSK), 20 (top ~5%% only). Default: tier-1 suppressed when verse is signal-rich."
                }
            }
        }
    ),
    Tool(
        name="lookup_name",
        annotations=ToolAnnotations(title="Lookup Name", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up general information about a biblical person, place, or thing by name — Abraham, David, Bethlehem, and so on.

Covers 4,000+ biblical persons and 1,000+ places. Returns the entry's original-language
name, description, key verse references, ACAI annotations where available (variant
names, roles, reference and speech counts), and its immediate relationships:

- **Parents** — one generation back (e.g. David → Jesse)
- **Children** — one generation forward (e.g. Abraham → Isaac)
- **Siblings** (e.g. Moses ↔ Aaron ↔ Miriam)
- **Spouse** (e.g. Ruth ↔ Boaz)

Relevant for identifying a named figure or location and for the immediate
family and reference context around it. Multi-generation lineages are covered by
`explore_genealogy`, a person's life events by `explore_person_events`, and a
location's full history by `explore_place`.""",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name to look up (e.g., 'David', 'Jerusalem', 'Abraham')"
                },
                "type": {
                    "type": "string",
                    "enum": ["person", "place", "thing"],
                    "description": "Filter by type. Omit to search all types."
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="parse_morphology",
        annotations=ToolAnnotations(title="Parse Morphology", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Explain a morphological/grammatical parsing code.

For Greek: Robinson codes (e.g., 'V-AAI-3S' = Verb, Aorist, Active, Indicative, 3rd person, Singular)
For Hebrew: Westminster/OpenScriptures codes

Returns full grammatical explanation including part of speech, 
person, number, tense, voice, mood, case, and gender where applicable.""",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Morphology code to parse (e.g., 'V-AAI-3S', 'N-GSF')"
                },
                "language": {
                    "type": "string",
                    "enum": ["greek", "hebrew"],
                    "description": "Language of the code. Default: greek"
                }
            },
            "required": ["code"]
        }
    ),
    Tool(
        name="search_by_strongs",
        annotations=ToolAnnotations(title="Search by Strong's Number", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Search by Strong's number for every verse where that word appears.

Takes a Strong's number (typically obtained from `word_study` or
`search_lexicon`) and returns the passages containing that Greek or Hebrew word,
showing how biblical authors used it in context and the range of senses it
carries across occurrences.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {
                    "type": "string",
                    "description": "Strong's number (e.g., 'G26', 'H430')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum verses to return. Default: 20"
                }
            },
            "required": ["strongs"]
        }
    ),
    Tool(
        name="explore_genealogy",
        annotations=ToolAnnotations(title="Explore Genealogy", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Trace a genealogy: a biblical person's ancestors and/or descendants across multiple generations of lineage.

Traverses genealogical data covering 1,100+ biblical persons. Returns a family
tree with generation numbers and relationship types, plus a Mermaid diagram of
the tree.

Covers questions such as tracing the line from Abraham to David, a person's
tribal ancestry, the Messianic lineage, or how a figure connects into a known
line. For a single generation (e.g. one person's father), `lookup_name` returns
immediate family without the traversal.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "Name of the person (e.g., 'David', 'Abraham', 'Jesus')"
                },
                "direction": {
                    "type": "string",
                    "enum": ["ancestors", "descendants", "both"],
                    "description": "Direction to trace. Default: both"
                },
                "generations": {
                    "type": "integer",
                    "description": "Maximum generations to trace. Default: 5"
                }
            },
            "required": ["person"]
        }
    ),
    Tool(
        name="people_in_passage",
        annotations=ToolAnnotations(title="People in Passage", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""List the people, places, and events mentioned in a Bible passage.

Returns the entities recorded for a chapter or verse in the Theographic Bible
Metadata — for example, Genesis 22 returns Abraham, Isaac, the angel of the LORD,
and Moriah; Acts 15 returns Paul, Barnabas, James, Jerusalem, and Antioch.

Relevant for establishing the cast and setting of a narrative passage. Related
tools: `graph_enriched_search` is verse-level only but adds the verse text and
family relationships for each person found.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference - chapter (e.g., 'Romans 8') or verse (e.g., 'Genesis 22:1')"
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="explore_person_events",
        annotations=ToolAnnotations(title="Explore Person Events", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve the recorded events of a biblical person's life in chronological order.

Returns each event with its location and date where known, plus a Mermaid
timeline diagram. Moses returns birth, burning bush, exodus, Sinai, and death on
Nebo; Paul returns conversion, missionary journeys, imprisonment, and Rome.

This is the only tool covering event sequence and dating for a person. Related
tools: `lookup_name` for identity and relationships, `explore_genealogy` for
lineage.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "Name of the person (e.g., 'Moses', 'Paul', 'David')"
                }
            },
            "required": ["person"]
        }
    ),
    Tool(
        name="explore_place",
        annotations=ToolAnnotations(title="Explore Place", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve the full biblical history of a place.

Returns the events recorded there, the people born or who died there, and
geographic data, spanning all biblical periods — plus a Mermaid network diagram.
Jerusalem returns events from Salem/Melchizedek through David, Solomon, the
exile, and Jesus; Mount Sinai returns the burning bush, the giving of the law,
the golden calf, and Elijah.

Relevant for questions about biblical geography or a location's significance
across salvation history. Related tool: `lookup_name` with type="place" returns
basic place info and immediate connections only.""",
        inputSchema={
            "type": "object",
            "properties": {
                "place": {
                    "type": "string",
                    "description": "Name of the place (e.g., 'Jerusalem', 'Bethlehem', 'Egypt')"
                }
            },
            "required": ["place"]
        }
    ),
    Tool(
        name="find_connection",
        annotations=ToolAnnotations(title="Find Connection", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Trace the shortest family relationship path between two biblical people.

Walks parent, child, sibling, and spouse relationships in the biblical
genealogies to find a connecting path, and returns it as a Mermaid flowchart.
Ruth and David return Ruth → Obed → Jesse → David; Abraham and Moses trace
through Levi. Where no family connection exists, that is reported.

Relevant for questions about how two named figures relate. Related tool:
`explore_genealogy` returns one person's ancestors or descendants rather than a
path between two people.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person1": {
                    "type": "string",
                    "description": "First person's name (e.g., 'Abraham')"
                },
                "person2": {
                    "type": "string",
                    "description": "Second person's name (e.g., 'David')"
                }
            },
            "required": ["person1", "person2"]
        }
    ),
    Tool(
        name="graph_enriched_search",
        annotations=ToolAnnotations(title="Graph Enriched Search", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve a comprehensive enriched view of a single verse: its text plus all people, places, events, and family relationships.

Returns the verse text, the people, places, and events mentioned in it, and the
family relationships of each person found. For 'Matthew 1:1' that is the verse
text, Jesus, David, and Abraham with their relationships, and the associated
places and events.

Combines what `lookup_verse` and `people_in_passage` return separately. Verse
level only; `people_in_passage` also accepts chapters but returns entity lists
without verse text or relationships.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible verse reference (e.g., 'Genesis 22:1', 'Matthew 1:1')"
                }
            },
            "required": ["reference"]
        }
    ),
    # =========================================================================
    # Aquifer content tools
    # =========================================================================
    Tool(
        name="get_study_notes",
        annotations=ToolAnnotations(title="Study Notes", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get scholarly study notes and translation notes for a Bible verse or chapter.

Returns combined commentary from:
- **Tyndale Study Notes**: Concise, verse-level scholarly commentary (66 books)
- **UW Translation Notes**: Translator-focused commentary with linguistic insights
- **SIL Translator Notes**: Additional translation and cultural context

Relevant for published commentary on a specific verse, difficult passages,
translation and cultural background, and chapter-level overviews of themes and
context. The content is published scholarship, quoted as-is with source
attribution.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference (e.g., 'John 3:16', 'Genesis 1', 'Romans 8:28')"
                },
                "chapter_only": {
                    "type": "boolean",
                    "description": "If true, return all notes for the chapter. Default: false (verse-specific)"
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_bible_dictionary",
        annotations=ToolAnnotations(title="Bible Dictionary", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up a topic in the Tyndale Bible Dictionary.

Contains 500+ topical articles covering:
- Biblical people and places
- Theological concepts and doctrines
- Cultural practices and customs
- Historical background
- Archaeological findings

Relevant for background on a biblical topic, historical or cultural context, a
detailed article on a person, place, or concept, or a published definition of a
theological term.

Returns the full dictionary article with cross-references.""",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to look up (e.g., 'Abraham', 'covenant', 'baptism', 'Pharisees')"
                }
            },
            "required": ["topic"]
        }
    ),
    Tool(
        name="get_key_terms",
        annotations=ToolAnnotations(title="Key Terms", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up a key theological term in the FIA Key Terms database.

Contains 200+ carefully defined theological and biblical terms with:
- Clear definitions accessible to translators
- Biblical usage and context
- Cross-references to related terms
- Translation guidance

Relevant for a precise definition of a theological term (agape, atonement,
justification, and similar), how a concept is used across Scripture, a
translation-oriented explanation, or cross-references to related concepts.""",
        inputSchema={
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "Theological term to look up (e.g., 'agape', 'atonement', 'covenant', 'grace')"
                }
            },
            "required": ["term"]
        }
    ),
    Tool(
        name="get_commentary",
        annotations=ToolAnnotations(title="Get Commentary", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get public-domain commentary on a specific verse.

Returns classic verse-level or section-level commentary from bundled
public-domain works. Available sources: Matthew Henry, John Gill (verse-by-verse),
Jamieson-Fausset-Brown, Adam Clarke, John Calvin, and Keil & Delitzsch (Old
Testament). Name one or more in `sources` (e.g. ['Matthew Henry','Gill']), or omit
to get every source that covers the verse.

Section-level commentaries (e.g. Matthew Henry) note the verse range the comment
covers. Distinct from `get_study_notes`, which returns the Tyndale/SIL/unfoldingWord
translation-oriented notes.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "A specific verse (e.g., 'Romans 3:23', 'John 3:16')"
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional commentary names/ids (e.g., ['Matthew Henry','Gill','Calvin']). Omit for all."
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_church_fathers",
        annotations=ToolAnnotations(title="Church Fathers", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Return a catena of public-domain church-father comments on a verse.

Gathers how the church fathers and later pre-1900 writers commented on a verse —
excerpts from Ante-Nicene, Nicene/Post-Nicene, Eastern/Byzantine, Syriac, and
medieval writers, each with author, approximate date, and source. Popular verses
have many; the earliest are shown first. Restrict to one writer with `father`
(e.g. 'Chrysostom', 'Augustine', 'Irenaeus').

Distinct from `get_commentary` (continuous, mostly Reformation-era commentaries)
and `get_study_notes` (modern translation-oriented notes).""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "A specific verse (e.g., 'John 1:1', 'Genesis 1:1')"
                },
                "father": {
                    "type": "string",
                    "description": "Optional: restrict to one writer (e.g., 'Chrysostom', 'Augustine')."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max excerpts to return (default 8)."
                }
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="search_theology",
        annotations=ToolAnnotations(title="Theology Library (grounding)", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Full-text search the church's public-domain theological treasury for grounding.

A local corpus of ~965 complete public-domain works — the Ante-Nicene and
Nicene/Post-Nicene Fathers, Reformers and Puritans (Owen, Edwards, Manton, Flavel,
Watson, Shepard), Reformed systematics (Hodge, Boyce), Aquinas' Summa, Schaff's
church history, Edersheim, Josephus, and Philo — indexed for keyword/BM25 retrieval.

Use it to GROUND a claim in what the tradition actually wrote: search a term or
phrase ('propitiation', 'federal headship', 'union with Christ', 'effectual
calling') and get the most relevant passages, each with author and work to cite.
Restrict to one writer with `author` (e.g. 'owen', 'edwards', 'schaff').

Distinct from `get_commentary` (verse-keyed commentary) and `get_church_fathers`
(verse-keyed patristic catena): this searches the full continuous texts by topic.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A theological term, phrase, or question (e.g., 'mortification of sin')."},
                "author": {"type": "string", "description": "Optional: restrict to one author's works (e.g., 'owen', 'aquinas', 'schaff')."},
                "limit": {"type": "integer", "description": "Max passages to return (default 8, max 25)."}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_confession",
        annotations=ToolAnnotations(title="Creeds & Confessions", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve or search the historical creeds, confessions, and catechisms.

Bundled documents span the Christian traditions (all public domain): ecumenical
creeds (Apostles', Nicene, Athanasian, Chalcedon); Reformed/Protestant confessions
(Westminster Confession + Larger/Shorter Catechisms, Belgic, Canons of Dort,
Heidelberg, 1689 London Baptist, 39 Articles, Augsburg); Catholic (Council of
Trent, Baltimore Catechism); and Orthodox (Confession of Dositheus, Philaret's
Catechism).

Usage: no arguments lists the documents; `document` retrieves one (or its section
index if long); `document` + `section` returns a specific chapter/article/question;
`topic` searches every document for a keyword or theme.""",
        inputSchema={
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document name (e.g., 'Nicene Creed', 'Westminster Confession', 'Heidelberg Catechism')"},
                "section": {"type": "string", "description": "A section/article/question within the document (e.g., 'Q1', 'God the Father')"},
                "topic": {"type": "string", "description": "Search all documents for a keyword or theme (e.g., 'justification', 'baptism')"}
            }
        }
    ),
    Tool(
        name="find_confessions_by_verse",
        annotations=ToolAnnotations(title="Confessions Citing a Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Find which confession or catechism articles cite a verse as a proof text.

Given a verse, returns every Reformed confession/catechism article that lists it
among its Scripture proofs (Westminster Confession, Larger & Shorter Catechisms,
Heidelberg, 1689, Savoy, Scots, Keach, ...), with the article's text. The
inverse of get_confession_proofs.

Relevant for tracing how the confessional tradition grounds a doctrine in a
given text, or building a verse-to-confession map for study.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "A single verse (e.g., 'Romans 1:20', 'John 1:1')"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_confession_proofs",
        annotations=ToolAnnotations(title="Confession Proof Texts", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Show the Scripture proof texts behind a confession or catechism article.

For a document (and optionally one article/question), returns each article with
its cited proof texts resolved to the actual verse text. E.g. the proofs behind
Westminster Confession 1.1, or Shorter Catechism Q1. The inverse of
find_confessions_by_verse.

Documents include the Westminster Standards (wcf, wlc, wsc), Heidelberg, 1689,
Savoy, Second Helvetic, Scots, Keach, and more.""",
        inputSchema={
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document name or id (e.g., 'Westminster Confession', 'wcf', 'Shorter Catechism', 'wsc')"},
                "section": {"type": "string", "description": "Optional article/question label: 'Q1' (catechism) or '1.2' = chapter.article (confession)"}
            },
            "required": ["document"]
        }
    ),
    Tool(
        name="get_devotional",
        annotations=ToolAnnotations(title="Get Devotional", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve a verse-keyed public-domain devotional reading.

Returns a daily devotional meditation anchored to a Bible verse, by verse
reference or by calendar date. Currently Spurgeon's "Morning and Evening"
(public domain). This is devotional/homiletical reflection, distinct from the
exegesis, commentary, and study-note tools.

Relevant for a devotional reflection on a passage, or the reading for a given
day. Not a substitute for exegesis.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "A verse the devotional is keyed to (e.g., 'Isaiah 40:31')"},
                "date": {"type": "string", "description": "A calendar date instead (e.g., 'January 1', 'Jan 1', '1/1')"}
            }
        }
    ),
    Tool(
        name="get_parallel_passages",
        annotations=ToolAnnotations(title="Parallel Passages", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Find the passages that run parallel to a verse (UBS Parallel Passage Database).

Given a verse, returns the editorially-grouped parallel references — Synoptic
Gospel parallels, Old Testament quotations in the New Testament, and repeated
narratives (e.g. Genesis 2:24 = Matthew 19:5 = Mark 10:7-8 = 1 Corinthians 6:16 =
Ephesians 5:31). Complements `get_cross_references` (thematically related verses)
with curated, genuinely parallel passages.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "A specific verse (e.g., 'Matthew 19:5', 'Genesis 2:24')"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_septuagint",
        annotations=ToolAnnotations(title="Septuagint (LXX)", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up the Greek Septuagint (LXX) text of a verse, with automatic versification mapping.

Returns the Greek text of H.B. Swete's edition (the whole Greek Old Testament in
LXX numbering, including the deuterocanon and Psalm 151), and reconciles the
LXX's divergent numbering with the standard Hebrew/English numbering.

By default the reference is read in standard (English) numbering and the
matching LXX verse is returned — e.g. 'Psalm 51:1' returns LXX Psalm 50:1, and
'Jeremiah 46:1' returns LXX Jeremiah 26:1. Set numbering='lxx' to give the
reference in the Septuagint's own numbering instead.

Relevant for the Greek wording of an Old Testament verse, the LXX Psalm or
Jeremiah renumbering, or comparing the Septuagint with the Hebrew/English text.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference (e.g., 'Psalm 51:1', 'Jeremiah 46:1', 'Genesis 1:1')"
                },
                "numbering": {
                    "type": "string",
                    "enum": ["english", "lxx"],
                    "description": "Numbering of the input reference: 'english' (default) or 'lxx' (the Septuagint's own)."
                }
            },
            "required": ["reference"]
        }
    ),
]


# =========================================================================
# Format functions — Theological scholarship
# =========================================================================

# Stated on every theology result so the nature of the content is explicit in the
# output itself: these cells are original summary prose, not reproduced text.
def format_lexicon_entry(entry: dict) -> str:
    """Format a lexicon entry for display.

    Shows separate sections for brief and full definitions when both exist.
    Greek entries with TFLSJ data show "Full LSJ Definition".
    Hebrew entries with BDB data show "Full BDB Definition".
    """
    lines = []

    # Header
    lines.append(f"## {entry['strongs']} - {entry['word']}")
    lines.append(f"**Transliteration**: {entry['transliteration']}")
    if entry.get('pronunciation'):
        lines.append(f"**Pronunciation**: {entry['pronunciation']}")
    lines.append(f"**Language**: {entry['language'].title()}")
    lines.append("")

    short_def = _clean_lexicon_text(entry.get('short_definition', ''))
    full_def = _clean_lexicon_text(entry.get('full_definition', ''))

    if short_def and full_def and short_def != full_def:
        # Show both brief and full definitions
        lines.append("### Brief Definition")
        lines.append(short_def)
        lines.append("")

        # Label based on language
        if entry.get('language') == 'greek':
            label = "Full LSJ Definition"
        elif entry.get('language') == 'hebrew':
            label = "Full BDB Definition"
        else:
            label = "Full Definition"

        lines.append(f"### {label}")
        lines.append(_truncate(full_def, 3000, "\n\n*[Definition truncated — full entry available in the lexicon]*"))
        lines.append("")
    elif full_def:
        lines.append("### Definition")
        lines.append(_truncate(full_def, 3000, "\n\n*[Definition truncated]*"))
        lines.append("")
    elif short_def:
        lines.append("### Definition")
        lines.append(short_def)
        lines.append("")
    else:
        lines.append("### Definition")
        lines.append("No definition available.")
        lines.append("")

    # Etymology
    if entry.get('etymology'):
        lines.append("### Etymology")
        lines.append(_clean_lexicon_text(entry['etymology']))
        lines.append("")

    # Semantic range
    domains = _parse_json_field(entry.get('semantic_domain'))
    if domains:
        lines.append("### Semantic Range")
        lines.append(", ".join(domains))
        lines.append("")

    # Usage count
    if entry.get('usage_count'):
        lines.append(f"**Usage**: Occurs {entry['usage_count']} times in the Bible")
        lines.append("")

    # Related words
    related = _parse_json_field(entry.get('related_words'))
    if related:
        lines.append("### Related Words")
        for r in related:
            if isinstance(r, dict):
                lines.append(f"- {r.get('strongs', '')} {r.get('word', '')} - {r.get('gloss', '')}")
            else:
                lines.append(f"- {r}")
        lines.append("")

    # Abbott-Smith definition (NT-focused)
    abbott_def = _clean_lexicon_text(entry.get('abbott_smith_def'))
    if abbott_def:
        lines.append("### Abbott-Smith Definition (NT-Focused)")
        lines.append(_truncate(abbott_def, 3000, "\n\n*[Definition truncated — full entry available in Abbott-Smith]*"))
        lines.append("")

    # LXX / Hebrew equivalents
    lxx = _parse_json_field(entry.get('lxx_hebrew'))
    if lxx:
        lines.append("### LXX / Hebrew Equivalents")
        for item in lxx:
            if isinstance(item, dict):
                lines.append(f"- {item.get('strongs', '')} {item.get('hebrew', '')}")
        lines.append("")

    # Synonyms
    syn_text = entry.get('synonyms')
    if syn_text:
        lines.append("### Synonyms")
        lines.append(syn_text)
        lines.append("")

    # NT occurrences
    nt_count = entry.get('nt_occurrences')
    if nt_count:
        lines.append(f"**NT Usage**: Occurs {nt_count} times in the New Testament")
        lines.append("")

    return "\n".join(lines)


def format_verse(verse: dict, include_original: bool = True, include_morphology: bool = False,
                 readable_text: str | None = None, translation_label: str | None = None) -> str:
    """Format a verse for display.

    When `readable_text` is given it is shown as the primary text (labelled with
    `translation_label`); otherwise the STEPBible word-gloss is used. The
    word-by-word interlinear is shown only when `include_morphology` is set.
    """
    lines = []

    _p = verse['reference'].split(".")
    ref_disp = f"{_p[0]} {_p[1]}:{_p[2]}" if len(_p) == 3 else verse['reference']
    lines.append(f"## {ref_disp}")
    alt = verse.get('ref_alt')
    if alt:
        p = alt.split(".")
        alt_disp = f"{p[0]} {p[1]}:{p[2]}" if len(p) == 3 else alt
        lines.append(f"*Also numbered {alt_disp} (alternate versification).*")
    lines.append("")
    if readable_text:
        lines.append(f"**{translation_label}:** {readable_text}")
    else:
        lines.append(verse.get('text_english', 'No English text available.'))
    lines.append("")

    if include_original and verse.get('text_original'):
        lines.append("### Original Text")
        lines.append(verse['text_original'])
        lines.append("")

    words = _parse_json_field(verse.get('word_data'))
    if words and include_morphology:
        lines.append("### Word-by-Word (Interlinear)")
        for w in words:
            if isinstance(w, dict):
                word_line = f"- **{w.get('word', '')}** ({w.get('strongs', '')}): {w.get('gloss', '')}"
                if w.get('morph'):
                    word_line += f" [{w['morph']}]"
                lines.append(word_line)
        lines.append("")

    return "\n".join(lines)


def format_name_entry(entry: dict, acai_data: dict | None = None) -> str:
    """Format a name entry for display, optionally enriched with ACAI data."""
    lines = []

    lines.append(f"### {entry['name']}")
    if entry.get('name_original'):
        lines.append(f"**Original**: {entry['name_original']}")
    lines.append(f"**Type**: {entry.get('type', 'Unknown').title()}")
    lines.append("")

    if entry.get('description'):
        lines.append(entry['description'])
        lines.append("")

    # ACAI enrichment
    if acai_data:
        acai_parts = []

        if acai_data.get('description'):
            acai_parts.append(f"**Description**: {acai_data['description']}")

        # Variant names
        variants = _parse_json_field(acai_data.get('referred_to_as'))
        if variants:
            acai_parts.append(f"**Also known as**: {', '.join(str(v) for v in variants[:5])}")

        # Roles
        roles = _parse_json_field(acai_data.get('roles'))
        if roles:
            acai_parts.append(f"**Roles**: {', '.join(str(r) for r in roles)}")

        if acai_data.get('reference_count'):
            acai_parts.append(f"**Referenced in**: {acai_data['reference_count']} verses")

        if acai_data.get('speeches_count'):
            acai_parts.append(f"**Attributed speeches**: {acai_data['speeches_count']}")

        if acai_parts:
            lines.append("**ACAI Annotations**:")
            lines.extend(acai_parts)
            lines.append("")

    rels = _parse_json_field(entry.get('relationships'))
    if rels:
        lines.append("**Relationships**:")
        for key, value in rels.items():
            if value:
                lines.append(f"- {key.title()}: {value}")
        lines.append("")

    refs = _parse_json_field(entry.get('references'))
    if refs:
        lines.append("**Key References**: " + ", ".join(refs[:10]))
        if len(refs) > 10:
            lines.append(f"(and {len(refs) - 10} more)")
        lines.append("")

    return "\n".join(lines)


# =========================================================================
# Aquifer content formatters
# =========================================================================

def format_study_notes(notes: list[dict]) -> str:
    """Format study notes grouped by source type."""
    if not notes:
        return "No study notes available for this reference.\n"

    lines = []

    # Group by resource_type
    groups: dict[str, list[dict]] = {}
    for note in notes:
        rt = note.get('resource_type', 'unknown')
        groups.setdefault(rt, []).append(note)

    type_labels = {
        'study_notes': 'Tyndale Study Notes',
        'translation_notes_uw': 'Translation Notes (unfoldingWord)',
        'translation_notes_sil': 'Translation Notes (SIL)',
    }

    for resource_type, group_notes in groups.items():
        label = type_labels.get(resource_type, resource_type)
        lines.append(f"### {label}")
        lines.append("")

        for note in group_notes:
            title = note.get('title', '')
            content = note.get('content_plain', '')

            if title:
                lines.append(f"**{title}**")
            if content:
                lines.append(_truncate(content, 2000, "\n\n*[Note truncated]*"))
            lines.append("")

    return "\n".join(lines)


def _format_content_items(items: list[dict], limit: int, truncation_note: str, empty_msg: str) -> str:
    """Format a list of content items (articles, terms) with title + truncated body."""
    if not items:
        return empty_msg

    lines = []
    for item in items:
        title = item.get('title', 'Untitled')
        content = item.get('content_plain', '')
        lines.append(f"## {title}")
        lines.append("")
        if content:
            lines.append(_truncate(content, limit, truncation_note))
        lines.append("")
    return "\n".join(lines)


def format_dictionary_article(articles: list[dict]) -> str:
    """Format Bible dictionary articles."""
    return _format_content_items(
        articles, 4000,
        "\n\n*[Article truncated — full text available in the Tyndale Bible Dictionary]*",
        "No dictionary article found for this topic.\n",
    )


def format_key_terms(terms: list[dict]) -> str:
    """Format FIA Key Terms results."""
    return _format_content_items(
        terms, 3000,
        "\n\n*[Term entry truncated]*",
        "No key term found matching this query.\n",
    )


# =========================================================================
# ANE context formatting
# =========================================================================

def format_year(year: int | None) -> str:
    """Format a year as BC/AD."""
    if year is None:
        return "unknown"
    if year < 0:
        return f"{abs(year)} BC"
    return f"AD {year}"


def _render_family_list(people: list[dict], heading: str, lines: list[str]) -> None:
    """Render a list of ancestors or descendants into lines."""
    if people and len(people) > 1:
        lines.append(f"### {heading}")
        for p in people:
            if p["generation"] == 0:
                continue
            indent = "  " * p["generation"]
            rel = p["relationship"].replace("_of", "").title()
            year_str = f" ({format_year(p.get('birth_year'))})" if p.get("birth_year") else ""
            lines.append(f"{indent}- **{p['name']}** ({rel}){year_str}")
        lines.append("")


def format_genealogy(person_name: str, ancestors: list[dict], descendants: list[dict]) -> str:
    """Format a genealogy tree for display."""
    lines = [f"## Genealogy of {person_name}\n"]

    _render_family_list(ancestors, "Ancestors", lines)
    _render_family_list(descendants, "Descendants", lines)

    if len(ancestors) <= 1 and len(descendants) <= 1:
        lines.append("No genealogical data found in the Theographic database.\n")

    return "\n".join(lines)


def format_person_events(person_name: str, events: list[dict], event_places: dict[str, list[dict]]) -> str:
    """Format a person's event timeline."""
    lines = [f"## Timeline of {person_name}\n"]

    if not events:
        lines.append("No events found in the Theographic database.\n")
        return "\n".join(lines)

    for evt in events:
        year_str = f" ({format_year(evt.get('start_year'))})" if evt.get("start_year") else ""
        lines.append(f"- **{evt['title']}**{year_str}")
        places = event_places.get(evt["id"], [])
        if places:
            place_names = ", ".join(p["name"] for p in places)
            lines.append(f"  Location: {place_names}")
    lines.append("")

    return "\n".join(lines)


def format_place_history(place: dict, events: list[dict], people: dict) -> str:
    """Format a place's biblical history."""
    lines = [f"## {place['name']}\n"]

    if place.get("feature_type"):
        lines.append(f"**Type**: {place['feature_type']}")
    if place.get("latitude") and place.get("longitude"):
        lines.append(f"**Coordinates**: {place['latitude']:.4f}, {place['longitude']:.4f}")
    lines.append("")

    if events:
        lines.append("### Events at this location")
        for evt in events:
            year_str = f" ({format_year(evt.get('start_year'))})" if evt.get("start_year") else ""
            lines.append(f"- **{evt['title']}**{year_str}")
        lines.append("")

    born = people.get("born_here", [])
    died = people.get("died_here", [])

    if born:
        lines.append("### Born here")
        for p in born:
            lines.append(f"- {p['name']}")
        lines.append("")

    if died:
        lines.append("### Died here")
        for p in died:
            lines.append(f"- {p['name']}")
        lines.append("")

    if not events and not born and not died:
        lines.append("No detailed history found in the Theographic database.\n")

    return "\n".join(lines)


def format_passage_entities(reference: str, entities: dict) -> str:
    """Format entities found in a passage."""
    lines = [f"## Entities in {reference}\n"]

    people = entities.get("people", [])
    places = entities.get("places", [])
    events = entities.get("events", [])

    if people:
        lines.append("### People")
        for p in people:
            lines.append(f"- **{p.get('entity_name', p.get('entity_id', 'unknown'))}**")
        lines.append("")

    if places:
        lines.append("### Places")
        for p in places:
            lines.append(f"- **{p.get('entity_name', p.get('entity_id', 'unknown'))}**")
        lines.append("")

    if events:
        lines.append("### Events")
        for e in events:
            lines.append(f"- **{e.get('entity_name', e.get('entity_id', 'unknown'))}**")
        lines.append("")

    if not people and not places and not events:
        lines.append("No entities found for this passage in the Theographic database.\n")

    return "\n".join(lines)


def format_connection_path(person1: str, person2: str, path: list[dict]) -> str:
    """Format a relationship path between two people."""
    lines = [f"## Connection: {person1} → {person2}\n"]

    if not path:
        lines.append("No family connection found in the Theographic database.\n")
        return "\n".join(lines)

    for step in path:
        rel = step["relationship_type"].replace("_", " ").title()
        lines.append(f"- {step['from_name']} → *{rel}* → {step['to_name']}")
    lines.append("")

    return "\n".join(lines)


def format_enriched_verse(reference: str, verse: dict | None, entities: dict, family_data: dict[str, dict]) -> str:
    """Format a verse with its entity context and family relationships.

    Args:
        reference: The verse reference string
        verse: The verse dict (or None)
        entities: Dict with 'people', 'places', 'events' lists
        family_data: Map of person name -> family dict from graph_get_family
    """
    lines = [f"## {reference}\n"]

    if verse:
        lines.append(verse.get("text_english", ""))
        lines.append("")
        if verse.get("text_original"):
            lines.append(f"**Original**: {verse['text_original']}")
            lines.append("")

    people = entities.get("people", [])
    places = entities.get("places", [])
    events = entities.get("events", [])

    if people:
        lines.append("### People Mentioned")
        for p in people:
            name = p.get("entity_name", p.get("entity_id"))
            lines.append(f"\n**{name}**")
            family = family_data.get(name)
            if family:
                parts = []
                if family["parents"]:
                    parent_names = ", ".join(pr["name"] for pr in family["parents"])
                    parts.append(f"Parents: {parent_names}")
                if family["partners"]:
                    partner_names = ", ".join(pr["name"] for pr in family["partners"])
                    parts.append(f"Spouse: {partner_names}")
                if family["children"]:
                    child_names = ", ".join(c["name"] for c in family["children"][:5])
                    suffix = f" (+{len(family['children'])-5} more)" if len(family["children"]) > 5 else ""
                    parts.append(f"Children: {child_names}{suffix}")
                if parts:
                    lines.append("  " + " | ".join(parts))
        lines.append("")

    if places:
        lines.append("### Places Mentioned")
        for p in places:
            lines.append(f"- **{p.get('entity_name', p.get('entity_id'))}**")
        lines.append("")

    if events:
        lines.append("### Events")
        for e in events:
            lines.append(f"- **{e.get('entity_name', e.get('entity_id'))}**")
        lines.append("")

    if not people and not places and not events:
        lines.append("*No entity data available for this verse in the Theographic database.*\n")

    return "\n".join(lines)


# =========================================================================
# Mermaid diagram formatters
# =========================================================================

def _mermaid_id(name: str) -> str:
    """Create a safe Mermaid node ID from a name."""
    return name.replace(" ", "_").replace("'", "").replace("(", "").replace(")", "")


def mermaid_genealogy(
    person_name: str,
    ancestors: list[dict],
    descendants: list[dict],
    family: dict | None = None,
) -> str:
    """Generate a Mermaid flowchart for a family tree.

    Uses family edges (parents/children/partners) for accurate connections.
    Falls back to generation-based layout if family data not provided.
    """
    lines = ["```mermaid", "graph TD"]
    seen_edges = set()
    seen_nodes = set()
    person_mid = _mermaid_id(person_name)

    # Style the focal person
    lines.append(f'    {person_mid}["{person_name}"]')
    lines.append(f"    style {person_mid} fill:#4a90d9,color:#fff,stroke:#2a5a8a")
    seen_nodes.add(person_mid)

    # Ancestors: show direct lineage chain only (gen 1 = parents, gen 2 = grandparents, etc.)
    # Build a map of unique people per generation to avoid cartesian products
    if ancestors and len(ancestors) > 1:
        by_gen: dict[int, list[dict]] = {}
        for a in ancestors:
            by_gen.setdefault(a["generation"], []).append(a)

        max_gen = max(by_gen.keys())
        # Connect each generation to the one below, but limit edges
        for gen in range(max_gen, 0, -1):
            people_at_gen = by_gen.get(gen, [])
            people_below = by_gen.get(gen - 1, [])
            for person in people_at_gen:
                pid = _mermaid_id(person["name"])
                rel = person["relationship"].replace("_of", "")
                if not seen_nodes.__contains__(pid):
                    seen_nodes.add(pid)
                # Connect to the person one generation below
                # For gen 1, connect to the focal person
                if gen == 1:
                    edge_key = (pid, person_mid)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        lines.append(f'    {pid}["{person["name"]}"] -->|{rel}| {person_mid}')
                else:
                    # Connect to people at gen-1 (limit to 2 to avoid explosion)
                    for child in people_below[:2]:
                        child_id = _mermaid_id(child["name"])
                        edge_key = (pid, child_id)
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            lines.append(f'    {pid}["{person["name"]}"] -->|{rel}| {child_id}["{child["name"]}"]')

    # Descendants: only show generation 1 (direct children) to keep diagram clean
    if descendants and len(descendants) > 1:
        direct_children = [d for d in descendants if d["generation"] == 1]
        for d in direct_children:
            did = _mermaid_id(d["name"])
            rel = d["relationship"].replace("_of", "")
            edge_key = (person_mid, did)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                lines.append(f'    {person_mid} -->|{rel}| {did}["{d["name"]}"]')

    # Partners from family data
    if family and family.get("partners"):
        for p in family["partners"]:
            pid = _mermaid_id(p["name"])
            edge_key = (person_mid, pid)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                lines.append(f'    {person_mid} -.-|spouse| {pid}["{p["name"]}"]')
                lines.append(f"    style {pid} fill:#d9a04a,color:#fff")

    lines.append("```")
    return "\n".join(lines)


def mermaid_connection_path(person1: str, person2: str, path: list[dict]) -> str:
    """Generate a Mermaid flowchart showing the relationship path between two people."""
    if not path:
        return ""

    lines = ["```mermaid", "graph LR"]

    # Style start and end
    start_id = _mermaid_id(person1)
    end_id = _mermaid_id(person2)
    lines.append(f"    style {start_id} fill:#4a90d9,color:#fff,stroke:#2a5a8a")
    lines.append(f"    style {end_id} fill:#d94a4a,color:#fff,stroke:#8a2a2a")

    seen = set()
    for step in path:
        fid = _mermaid_id(step["from_name"])
        tid = _mermaid_id(step["to_name"])
        rel = step["relationship_type"].replace("_", " ")
        edge_key = (fid, tid)
        if edge_key not in seen:
            seen.add(edge_key)
            lines.append(f'    {fid}["{step["from_name"]}"] -->|{rel}| {tid}["{step["to_name"]}"]')

    lines.append("```")
    return "\n".join(lines)


def mermaid_person_timeline(
    person_name: str,
    events: list[dict],
    event_places: dict[str, list[dict]],
) -> str:
    """Generate a Mermaid timeline diagram for a person's life events."""
    if not events:
        return ""

    lines = ["```mermaid", "timeline", f"    title {person_name}"]

    for evt in events:
        year = evt.get("start_year")
        year_str = format_year(year) if year else ""
        title = evt["title"].replace('"', "'")
        places = event_places.get(evt["id"], [])

        section_label = year_str if year_str else title[:20]
        lines.append(f"    {section_label} : {title}")
        if places:
            place_names = ", ".join(p["name"] for p in places[:3])
            lines.append(f"        : {place_names}")

    lines.append("```")
    return "\n".join(lines)


def mermaid_place_network(
    place: dict,
    events: list[dict],
    people: dict,
) -> str:
    """Generate a Mermaid graph showing a place's connections to events and people."""
    born = people.get("born_here", [])
    died = people.get("died_here", [])
    if not events and not born and not died:
        return ""

    lines = ["```mermaid", "graph TD"]

    place_id = _mermaid_id(place["name"])
    lines.append(f'    {place_id}["{place["name"]}"]')
    lines.append(f"    style {place_id} fill:#2a8a4a,color:#fff,stroke:#1a5a2a")

    # Events
    if events:
        for evt in events[:12]:  # limit to avoid huge diagrams
            eid = _mermaid_id(evt["title"][:30])
            year_str = f" ({format_year(evt.get('start_year'))})" if evt.get("start_year") else ""
            label = evt["title"][:40] + year_str
            lines.append(f'    {place_id} --- {eid}["{label}"]')

    # People born/died
    for p in born[:8]:
        pid = _mermaid_id(p["name"]) + "_b"
        lines.append(f'    {pid}["{p["name"]}"] -->|born| {place_id}')
        lines.append(f"    style {pid} fill:#4a90d9,color:#fff")

    for p in died[:8]:
        pid = _mermaid_id(p["name"]) + "_d"
        lines.append(f'    {place_id} -->|died| {pid}["{p["name"]}"]')
        lines.append(f"    style {pid} fill:#d94a4a,color:#fff")

    lines.append("```")
    return "\n".join(lines)


# =========================================================================
# Format functions — Torah Weave
# =========================================================================

# Template explaining the structural meaning of each direction.
