"""What the chat can reach, in words a student can read.

The info bubble on the chat screen shows this. Tool names are filtered to the tools that are
actually registered for the mode, so a tool that is not running is never listed. A registered
tool that is missing from the groups below still shows, under "Other tools" with its own first
sentence, so the list cannot fall behind the code. Source names are curated from NOTICE and the
tools' own descriptions. Counts are left to /corpus, where they are kept in one place.
"""
from __future__ import annotations

_COURSE = (
    "Gospel of John course",
    "The built-in Gospel of John course materials.",
    [
        ("list_john_curriculum", "The course outline: every unit reading guide, the four quarter projects, and the memory verses."),
        ("get_reading_guide", "The reading guide for one unit: its passage, big question, and prompts."),
        ("get_project", "The student guide for one of the four quarter projects."),
        ("get_memory_verses", "The memory-verse sheet: the verses, the unit that introduces each, and the review schedule."),
        ("get_course_schedule", "Today's date and what the course calendar has on for a day or a week: unit, lesson, and passage."),
    ],
)

# (group title, sources line, [(tool name, one-line description), ...])
BIBLE = [
    (
        "Scripture text",
        "Berean Standard Bible, World English Bible, King James Version, American Standard Version, "
        "Young's Literal Translation; the Septuagint in Greek (Swete) and English (Brenton). "
        "ESV and NET appear only when enabled.",
        [
            ("lookup_verse", "A verse in a readable modern translation, with the original language available."),
            ("get_passage", "A verse range or a whole chapter in one translation."),
            ("compare_translations", "One verse across several English translations, side by side."),
            ("get_septuagint", "The Greek Septuagint text of a verse, with versification mapping."),
        ],
    ),
    (
        "Original languages and words",
        "Tagged Hebrew Old Testament and Greek New Testament (STEPBible, Tyndale House). Lexicons: "
        "Extended Strong's, Liddell-Scott-Jones, Brown-Driver-Briggs, Abbott-Smith.",
        [
            ("word_study", "The lexicon entry for a Strong's number or a Greek, Hebrew, or English word."),
            ("search_lexicon", "Search the Greek and Hebrew lexicons by English word, transliteration, or concept."),
            ("search_by_strongs", "Every verse where a given Strong's-numbered word appears."),
            ("parse_morphology", "Explain a grammatical parsing code."),
            ("vocabulary_list", "The rarest original-language words in a passage."),
        ],
    ),
    (
        "Cross-references and parallels",
        "OpenBible.info cross-references; the UBS Parallel Passage Database.",
        [
            ("get_cross_references", "Passages traditionally read alongside a reference, or a doctrinal chain."),
            ("get_parallel_passages", "Passages that run parallel to a verse."),
        ],
    ),
    (
        "Biblical people, places and events",
        "Theographic Bible Metadata.",
        [
            ("lookup_name", "Information about a biblical person, place, or thing by name."),
            ("people_in_passage", "The people, places, and events mentioned in a passage."),
            ("explore_person_events", "A person's recorded life events in order."),
            ("explore_place", "The biblical history of a place."),
            ("explore_genealogy", "A person's ancestors and descendants across generations."),
            ("find_connection", "The shortest family-relationship path between two biblical people."),
            ("graph_enriched_search", "A verse together with its people, places, events, and relationships."),
        ],
    ),
    (
        "Study notes and reference",
        "Tyndale study notes and Bible Dictionary; unfoldingWord and SIL translation notes; "
        "FIA Key Terms; Easton's Bible Dictionary; Spurgeon's Morning and Evening.",
        [
            ("get_study_notes", "Scholarly study and translation notes for a verse or chapter."),
            ("get_bible_dictionary", "A topic in the Tyndale Bible Dictionary."),
            ("get_key_terms", "A key theological term, defined."),
            ("get_devotional", "A verse-keyed public-domain devotional reading."),
        ],
    ),
    (
        "Commentary and the historic church",
        "Public-domain commentaries (Matthew Henry, John Gill, Jamieson-Fausset-Brown, Adam Clarke, "
        "Calvin, Keil and Delitzsch, and others on the full list); a catena of church-father comments "
        "(HistoricalChristianFaith); a library of public-domain theology; creeds, confessions, and "
        "catechisms from the Ecumenical, Reformed, Lutheran, Anglican, Catholic, and Orthodox traditions.",
        [
            ("get_commentary", "Public-domain verse commentary from classic authors."),
            ("get_church_fathers", "Church-father comments on a verse."),
            ("search_theology", "Search a library of public-domain theology: the fathers, Reformers and Puritans, Reformed systematics, Aquinas, Schaff."),
            ("get_confession", "Retrieve or search the creeds, confessions, and catechisms."),
            ("find_confessions_by_verse", "Which confession or catechism articles cite a verse as a proof text."),
            ("get_confession_proofs", "The Scripture proof texts behind a confession or catechism article."),
        ],
    ),
    _COURSE,
]

HISTORY = [
    (
        "Documents and speeches",
        "Avalon Project documents, Miller Center presidential speeches, DocSouth slave narratives and "
        "first-person Southern accounts, and public-domain history books from the Reading Room.",
        [
            ("search_history", "Search founding documents, treaties, speeches, narratives, and history books by keyword or meaning."),
            ("find_documents", "Find a document by title, author, or source."),
            ("get_document", "Read a document's full text."),
            ("people_in_document", "The people and events named in a document or Supreme Court case."),
        ],
    ),
    (
        "Constitutions, statutes, and the flag",
        "The U.S. Constitution and the Illinois Constitution (1970); the Constitution Annotated "
        "(Congressional Research Service, 2022); the U.S. Code and Illinois Compiled Statutes; the U.S. Flag Code.",
        [
            ("get_constitution", "The exact text of the U.S. Constitution or the Illinois Constitution."),
            ("get_constitution_annotation", "Clause-by-clause essays on how the Constitution has been understood, with leading cases."),
            ("get_statute", "A section of the U.S. Code or selected Illinois Compiled Statutes."),
            ("get_flag_code", "The U.S. Flag Code."),
            ("constitution_test_guide", "What the Illinois Constitution Test covers, and where each part lives in these tools."),
        ],
    ),
    (
        "Supreme Court",
        "U.S. Reports through the Caselaw Access Project, with Supreme Court Database coding.",
        [
            ("search_cases", "Search Supreme Court opinions through June 2014 by name, topic, or words in the opinion."),
            ("get_case", "Read a Supreme Court case, with its vote, justices, and issue area."),
        ],
    ),
    (
        "Historical people, events, and places",
        "The app's history graph of people, events, and places (built from a Wikidata slice), linked to "
        "its documents and cases; members of Congress and presidents since 1789.",
        [
            ("lookup_person", "Who someone in history was: dates, offices, speeches, writings, and where they appear."),
            ("explore_life", "A person's life in order."),
            ("explore_family", "A historical person's family tree."),
            ("explore_event", "Wars, treaties, laws, elections, speeches, expeditions, and movements."),
            ("explore_historic_place", "A place in history: what happened there and who was born or died there."),
            ("find_historical_connection", "How two people, or a person and an event, are connected."),
            ("succession", "Who held an office in order, or each office a person held."),
            ("timeline", "What was happening in a span of years."),
            ("lookup_legislator", "Members of Congress, presidents, and vice presidents since 1789."),
        ],
    ),
    (
        "Words in their time",
        "Black's Law Dictionary (2nd ed., 1910); Webster's American Dictionary (1828).",
        [
            ("define_term", "A word as it was used in its own time."),
        ],
    ),
]


def _first_sentence(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    end = text.find(". ")
    text = text if end == -1 else text[: end + 1]
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _groups(subject: str) -> list:
    # History mode also reaches the Study Bible tools (church history is history), minus the
    # John-course tools, which stay with the Bible mode.
    return HISTORY + [g for g in BIBLE if g is not _COURSE] if subject == "history" else BIBLE


def sources_note(subject: str) -> str:
    """The sources of each group, for the system prompt: the bot may list these when asked."""
    lines = [f"- {title}: {sources}" for title, sources, _ in _groups(subject)]
    return "\n\nSources available in this mode:\n" + "\n".join(lines)


def build(subject: str, tools: list[dict]) -> list[dict]:
    """Groups for one subject, limited to the tools registered for it.

    `tools` are the tool dicts the chat actually passes to the model (each has "name" and
    "description"). Returns [{"group", "sources", "tools": [{"name", "desc"}]}, ...].
    """
    groups = _groups(subject)
    by_name = {t["name"]: t for t in tools}
    out: list[dict] = []
    used: set[str] = set()
    for title, sources, items in groups:
        rows = [{"name": n, "desc": d} for n, d in items if n in by_name]
        used.update(r["name"] for r in rows)
        if rows:
            out.append({"group": title, "sources": sources, "tools": rows})
    rest = sorted(n for n in by_name if n not in used)
    if rest:
        out.append({"group": "Other tools", "sources": None,
                    "tools": [{"name": n, "desc": _first_sentence(by_name[n].get("description", ""))} for n in rest]})
    return out
