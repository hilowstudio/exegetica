"""The lookups made in code before an open model starts (webapp/prefetch.py, decision 0020). No network."""
from webapp import curriculum
from webapp.prefetch import MAX_CALLS, plan

BIBLE = {"lookup_verse", "get_passage", "get_confession"} | curriculum.HANDLER_NAMES
HISTORY = {"search_history", "get_document"} | curriculum.HANDLER_NAMES


def test_a_verse_a_range_and_a_chapter_are_looked_up():
    assert plan("What does John 3:16 mean?", BIBLE) == [("lookup_verse", {"reference": "John 3:16"})]
    assert plan("Explain Romans 8:28-39", BIBLE) == [("get_passage", {"reference": "Romans 8:28-39"})]
    assert plan("Quiz me on John 4. Five questions.", BIBLE) == [("get_passage", {"reference": "John 4"})]


def test_words_that_only_look_like_books_are_not():
    assert plan("What is in Unit 6 and Article 36?", {"lookup_verse", "get_passage"}) == []


def test_a_named_confession_is_fetched_with_its_section():
    assert plan("What does the Westminster Shorter Catechism Q33 say?", BIBLE) == [
        ("get_confession", {"document": "Westminster Shorter Catechism", "section": "33"})]
    assert plan("What does the 1689 Confession say about baptism?", BIBLE) == [
        ("get_confession", {"document": "1689"})]
    assert plan("What happened in 1689 in England?", BIBLE) == []   # a year, not the confession


def test_the_course_is_fetched_by_unit_memory_verses_and_date():
    assert plan("What do we read in unit 6 and what's the memory verse?", BIBLE) == [
        ("get_reading_guide", {"unit": 6}), ("get_memory_verses", {"unit": 6})]
    assert plan("What are we reading today?", BIBLE) == [("get_course_schedule", {})]


def test_only_this_chats_tools_are_used_and_the_count_is_capped():
    assert plan("What does John 3:16 mean?", HISTORY) == []
    many = "Compare John 1:1, John 1:5, John 3:16, John 8:58 and John 20:31."
    assert len(plan(many, BIBLE)) == MAX_CALLS
