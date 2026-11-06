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
        description="""Call when a question turns on one Greek or Hebrew word: its meaning, its range of senses, or the term behind an English rendering. Give a Strong's number, or an English word or transliteration to get its best match.

Returns the full lexicon entry (original script, transliteration, definitions from LSJ or BDB and Abbott-Smith where held, etymology, related words) and up to five example verses. To see every word behind an English term, use search_lexicon. For more verses that use the word, use search_by_strongs.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {
                    "type": "string",
                    "description": "Strong's number (e.g., 'G26' for agapē, 'H3068' for YHWH)"
                },
                "word": {
                    "type": "string",
                    "description": "An English word ('love', 'faith') or a transliteration ('agape', 'shalom', 'hesed'). An exact transliteration or gloss match wins."
                },
                "language": {
                    "type": "string",
                    "enum": ["greek", "hebrew"],
                    "description": "Language to search if using 'word'. Leave it out to search both, Greek first."
                }
            }
        }
    ),
    Tool(
        name="lookup_verse",
        annotations=ToolAnnotations(title="Lookup Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to quote or examine one verse ('John 3:16', 'Jude 3').

Returns the verse in a readable translation (the ESV by default where this server has a Crossway key, else the BSB), its Greek or Hebrew text, a note on reading its genre where one applies, and on request a word-by-word interlinear with Strong's numbers and parsing codes. For a verse range or a chapter, use get_passage. For several translations side by side, use compare_translations. For the Septuagint's Greek of an Old Testament verse, use get_septuagint.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Bible reference (e.g., 'John 3:16', 'Genesis 1:1', 'Jude 3')"
                },
                "translation": {
                    "type": "string",
                    "description": "Leave it out for the default: the ESV where this server has a Crossway key, else the BSB. BSB, WEB, KJV, ASV and YLT are held here. ESV and NET are fetched live, and the BSB stands in, with a note, when they can't be reached."
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
        description="""Call to read more than one verse: a verse range or a whole chapter.

Returns the numbered verses in one translation (the ESV by default where this server has a Crossway key, else the BSB). The deuterocanon (Tobit, Judith, Wisdom, Sirach, Baruch, 1-4 Maccabees, 1-2 Esdras, Prayer of Manasseh, Greek Esther, Psalm 151, Susanna, Bel and the Dragon, Letter of Jeremiah) comes from the WEB automatically. For one verse with its Greek or Hebrew, use lookup_verse.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "A chapter ('Psalm 23') or a verse range inside one chapter ('Romans 3:21-26')."
                },
                "translation": {
                    "type": "string",
                    "description": "Translation: leave it out for the default (the ESV where this server has a Crossway key, else the BSB), or BSB, WEB, KJV, ASV, YLT, or ESV / NET (fetched live)."
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
        description="""Call to compare how translations render a verse, or to check a literal rendering (YLT, ASV) against a readable one.

Returns one verse in each translation named, or in all the bundled ones (BSB, WEB, KJV, ASV, YLT) when none are named. ESV and NET can be named too. For a passage longer than one verse, use get_passage.""",
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
        description="""Call to prepare a passage for reading in Hebrew or Greek, or to build a vocabulary list.

Returns the passage's rarest original-language words, rarest first, each with its gloss, Strong's number, and how often it occurs in the tagged Hebrew Old Testament and Greek New Testament.""",
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
        description="""Call to find which Greek or Hebrew words lie behind an English word or concept, or to tell near-synonyms apart ('love' gives agapaō, agapē, phileō and more).

Returns the matching lexicon entries, best match first, each with its Strong's number, transliteration, and short definition. Open one in full with word_study.""",
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
        description="""Call to find the verses usually read alongside a verse, or a short chain of key passages for a doctrine.

With reference, returns OpenBible.info cross-references ranked by reader votes, each with its vote count. More votes mean a closer link. With theme, returns a curated chain of passages for one of six doctrines. For true parallels (the Synoptic accounts of one event, an Old Testament text quoted in the New), use get_parallel_passages.""",
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
                "limit": {
                    "type": "integer",
                    "description": "Most rows to return, highest votes first. Default 8. Use 20-30 for the long tail."
                },
                "min_strength": {
                    "type": "integer",
                    "description": "Fewest votes a row needs. Default 0, which leaves out links readers voted down. Votes run to over 1,000, and rows under about 5 votes are weak links."
                }
            }
        }
    ),
    Tool(
        name="lookup_name",
        annotations=ToolAnnotations(title="Lookup Name", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to identify a person or place named in the Bible (Abraham, Bethlehem). Covers biblical names only.

Returns every entry whose name contains the text given, each with its original-language name, a description, key references, and parents, children, siblings and spouse, plus ACAI's roles and other names where an ACAI record matches that entry. For a lineage over several generations, use explore_genealogy. For a life in order, use explore_person_events. For a place's history, use explore_place.""",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name to look up (e.g., 'David', 'Jerusalem', 'Abraham')"
                },
                "type": {
                    "type": "string",
                    "enum": ["person", "place"],
                    "description": "'person' or 'place'. Omit for both."
                }
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="parse_morphology",
        annotations=ToolAnnotations(title="Parse Morphology", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to explain a parsing code, such as one in lookup_verse's interlinear. Greek codes are Robinson style ('V-AAI-3S'), Hebrew codes STEPBible style ('HVqp3ms').

Returns the part of speech and, as they apply, tense or stem, voice, mood, person, number, case and gender.""",
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
                    "description": "Language of the code. Default greek, so pass 'hebrew' for a Hebrew code."
                }
            },
            "required": ["code"]
        }
    ),
    Tool(
        name="search_by_strongs",
        annotations=ToolAnnotations(title="Search by Strong's Number", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to see how a word is used across Scripture, or by one book, once you have its Strong's number (from word_study or search_lexicon). Name a book for questions such as how John uses "believe" or whether a book uses a word at all.

Returns the word's short definition; how many times it occurs; the words that most often come right after it, which show its constructions (a preposition such as εἰς or a conjunction such as ὅτι); and the first verses in Bible order, each in a literal word-for-word English gloss with the original words around the term and its parsing.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {
                    "type": "string",
                    "description": "Strong's number (e.g., 'G26', 'H430')"
                },
                "book": {
                    "type": "string",
                    "description": "A book to search within (e.g., 'John', '1 John', 'Romans'). Default: the whole Bible"
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
        description="""Call to trace a biblical lineage over several generations: a person's ancestors, descendants, or both (the line from Abraham to David, a tribal ancestry). Covers people in the Bible only.

Returns the tree with generation numbers, the person's spouses and siblings, and a Mermaid diagram. When the name fits several people, it answers for the closest, most-mentioned match and lists the others with ids to call again with. For one generation, lookup_name is enough. For how two people are related, use find_connection.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "Name of the person (e.g., 'David', 'Abraham', 'Mary Magdalene'), or a graph id such as 'mary_1943' from a list of other matches"
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
        description="""Call to establish the cast and setting of a passage: who and what appears in a chapter ('Genesis 22') or a verse.

Returns the people, places and events recorded for it, by name. For one verse with its text and each person's family, use graph_enriched_search.""",
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
        description="""Call for the course of a biblical person's life: what happened, in order, and when.

Returns the recorded events in order, each with its place and date where known, and a Mermaid timeline. When the name fits several people, it lists the others with ids to call again with. For identity and family, use lookup_name. For lineage, use explore_genealogy.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person": {
                    "type": "string",
                    "description": "Name of the person (e.g., 'Moses', 'Paul', 'John Mark'), or a graph id such as 'john_1679' from a list of other matches"
                }
            },
            "required": ["person"]
        }
    ),
    Tool(
        name="explore_place",
        annotations=ToolAnnotations(title="Explore Place", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call for a biblical place's history and significance across the Bible (Jerusalem, Mount Sinai). Covers places in the Bible only.

Returns its type and coordinates where known, the events recorded there, the people born or who died there, and a Mermaid diagram. For a short identification, lookup_name with type 'place' is enough.""",
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
        description="""Call to find how two people in the Bible are related by family (Ruth and David).

Returns the shortest path through parent, child, sibling and spouse links, with a Mermaid flowchart, or says that no family link was found. For one person's whole line, use explore_genealogy.""",
        inputSchema={
            "type": "object",
            "properties": {
                "person1": {
                    "type": "string",
                    "description": "First person's name (e.g., 'Abraham') or graph id"
                },
                "person2": {
                    "type": "string",
                    "description": "Second person's name (e.g., 'David') or graph id"
                }
            },
            "required": ["person1", "person2"]
        }
    ),
    Tool(
        name="graph_enriched_search",
        annotations=ToolAnnotations(title="Graph Enriched Search", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call for one verse together with the people in it and their families ('Matthew 1:1'). Takes a single verse.

Returns the verse in a literal English gloss and in the original language, the people, places and events it mentions, and each person's parents, spouse and children. For a chapter's cast, use people_in_passage. For a readable translation, use lookup_verse.""",
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
        description="""Call for modern study notes on a verse or a chapter: a hard phrase, translation questions, or cultural background.

Returns Tyndale Study Notes, unfoldingWord translation notes and SIL translator notes, grouped by source. A chapter reference ('Genesis 1') or chapter_only gives the whole chapter's notes. For classic commentaries, use get_commentary.""",
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
        description="""Call for a background article on a biblical topic: a person, place, custom, institution or idea (Pharisees, baptism, covenant).

Returns the matching articles from the Tyndale Bible Dictionary and Easton's Bible Dictionary. For a short definition of a theological term, use get_key_terms. To identify a name quickly, use lookup_name.""",
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
        description="""Call for a precise definition of a biblical or theological term (atonement, justification, grace) and how Scripture uses it.

Returns the matching FIA Key Terms entries, written for Bible translators. For a longer background article, use get_bible_dictionary. For the Greek or Hebrew word itself, use word_study.""",
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
        description="""Call for what the classic commentators said about one verse.

Returns the comment from each public-domain commentary that covers the verse, with the verse range it spans: Matthew Henry, John Gill, Jamieson-Fausset-Brown, Adam Clarke, John Calvin, Keil & Delitzsch (Old Testament), Charles Hodge (Romans), J.C. Ryle (Gospels) and Spurgeon's Treasury of David (Psalms). For the church fathers, use get_church_fathers. For modern study notes, use get_study_notes.""",
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
        description="""Call for how the church fathers and other writers before 1900 read one verse.

Returns excerpts, earliest first, each with author, approximate date and source, and the count on file. Name one writer with father. For Reformation and later commentaries, use get_commentary. To search the fathers' full works by topic, use search_theology.""",
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
        description="""Call to ground a doctrinal or church-history claim in what the tradition wrote ('propitiation', 'union with Christ', 'mortification of sin').

Searches nearly 1,000 public-domain works (the Ante-Nicene and Nicene Fathers, Aquinas, Luther, Owen and the Puritans, Edwards, Hodge, Spurgeon, Schaff's church history, Edersheim, Josephus, Philo) by keyword and by meaning. A Bible book or verse named in the query also brings up the works written on it. Returns passages with the author and work to cite, and the paragraph for keyword and verse matches. For comments keyed to one verse, use get_commentary or get_church_fathers.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A theological term, phrase, or question (e.g., 'mortification of sin')."},
                "author": {"type": "string", "description": "Optional: one author's works, by surname (e.g., 'owen', 'aquinas', 'schaff')."},
                "limit": {"type": "integer", "description": "Max passages to return (default 8, max 25)."}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_confession",
        annotations=ToolAnnotations(title="Creeds & Confessions", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to read or search the creeds, confessions and catechisms: the ecumenical creeds, the Reformed and Baptist standards (Westminster, Heidelberg, Belgic, Dort, 1689), and Lutheran, Anglican, Catholic and Orthodox documents.

With no arguments, lists the documents. document returns one, or its list of sections when it is long. document with section returns one part. topic searches every document. The Westminster Confession and the 1689 come back with every paragraph numbered (29.2) and its proof texts; cite those numbers as shown. For the proof texts behind a catechism answer or another standard, use get_confession_proofs. For the articles that cite a verse, use find_confessions_by_verse.""",
        inputSchema={
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document name (e.g., 'Nicene Creed', 'Westminster Confession', '1689', 'Heidelberg Catechism')"},
                "section": {"type": "string", "description": "A chapter ('29'), a paragraph ('29.2'), a catechism question ('Q1'), or words from a chapter or article title ('Of Creation', 'God the Father')."},
                "topic": {"type": "string", "description": "A word or short phrase, matched as written (e.g., 'justification'). Returns up to 12 sections."}
            }
        }
    ),
    Tool(
        name="find_confessions_by_verse",
        annotations=ToolAnnotations(title="Confessions Citing a Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call to see how the confessions use a verse: which articles cite it as a proof text.

Returns each citing article's label and opening text from the Westminster Confession and Catechisms, Heidelberg, the 1689 London Baptist Confession, Savoy, and Keach's Catechism. To go from an article to its proofs, use get_confession_proofs.""",
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
        description="""Call to see the Scripture behind a confession or catechism article (Westminster Confession 1.1, Shorter Catechism Q1).

Returns the article with its proof texts and the BSB text of each verse. Without a section, returns the list of articles with their proof counts, to choose from. Covers the Westminster Confession and Catechisms (wcf, wlc, wsc, wsc-pca), Heidelberg, the 1689 London Baptist Confession, Savoy, and Keach's Catechism. For other documents, or an article's full text, use get_confession.""",
        inputSchema={
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Document name or id (e.g., 'Westminster Confession', 'wcf', 'Shorter Catechism', 'wsc')"},
                "section": {"type": "string", "description": "A question ('Q1' or '1'), an article ('1.2', chapter 1, article 2), or a whole chapter of a confession ('1'). Leave it out to list the articles."}
            },
            "required": ["document"]
        }
    ),
    Tool(
        name="get_devotional",
        annotations=ToolAnnotations(title="Get Devotional", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Call when a devotional reflection on a verse is wanted, or the reading for a calendar day.

Returns readings from Spurgeon's Morning and Evening keyed to that verse or its chapter, or to that date. Read it alongside the exegesis tools.""",
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
        description="""Call to find true parallels to a verse: the Synoptic accounts of one event, an Old Testament text quoted in the New, or a repeated narrative.

Returns the UBS Parallel Passage groups the verse belongs to (Genesis 2:24 = Matthew 19:5 = Mark 10:7-8 = 1 Corinthians 6:16 = Ephesians 5:31). For verses on a related theme, use get_cross_references.""",
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
        description="""Call for the Septuagint's Greek wording of an Old Testament or deuterocanonical verse, or to compare it with the Hebrew.

Returns Swete's Greek text with Brenton's English, and both Greek texts (Old Greek and Theodotion) for Daniel, Susanna and Bel. The reference is read in English numbering and mapped to the LXX verse ('Psalm 51:1' gives LXX Psalm 50:3), and the answer names both numbers. Set numbering 'lxx' to give Swete's numbering instead. For the Hebrew text, use lookup_verse.""",
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

    refs = _parse_json_field(entry.get('refs') or entry.get('references'))
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
        family_data: Map of person id (graph_verse_mentions.entity_id) -> family dict from graph_get_family
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
            names = [a.strip() for a in (p.get("also_called") or "").split(",") if a.strip()]
            alias = f" ({', '.join(names[:3])}{', ...' if len(names) > 3 else ''})" if names else ""
            lines.append(f"\n**{name}**{alias} `{p.get('entity_id')}`")
            family = family_data.get(p.get("entity_id")) or family_data.get(name)
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
