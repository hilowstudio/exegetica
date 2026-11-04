# 0016: Replies and documents say what they drew on

Recorded 2026-11-03 from the harness proposal (Layer 2 step 8, Layer 5 steps 5 and 8), built at the maker's request to do Phase 5.

**Decision.**

- Each run's tool results are held in memory for that run, for the checks below, and never stored.
- A chat reply that used no library tool shows "No library source was consulted." under it. A reply that used tools lists, under it, any quotation of six words or more that neither the study's library results nor the bundled Bible text holds. The note is saved with the study for display, and the server drops it before history reaches the model.
- The reply check exempts quoted text from its affection pattern only when this run's tool results hold the quotation, or, at six words or more, the bundled Bible text does. A short phrase such as "I love you" occurs in Scripture, so the Bible alone cannot vouch for it. The check follows an open quotation across sentences, so the later sentences of a long quotation count as quoted.
- A finished Generator document is followed by a source check: Scripture references checked against the bundled Bible, and quotations that neither the run's prompt material and tool results nor the bundled Bible text holds. It never blocks a download and never calls anything verified. Revise gets no check, since a revision's sources were the first run's.
- Theology search results give the paragraph number for keyword and Scripture-reference hits. Hits found by meaning come from a chunked copy without paragraph numbers and carry none.

**Why.** A student cannot tell an answer drawn from the library from one the model wrote from memory, and the label says which. Quotation marks were an open door in the reply check: any text inside them passed, so a claim of affection could be wrapped in quotes. The checks say only what was found where. A quotation not found may still be accurate (ESV wording is never stored here), and a reference that exists may still be the wrong one.

**Enforced in.** `webapp/citations.py` (`Recorder`, `quote_check`, `chat_note`, `generator_report`); `webapp/reply_check.py` (quote state and `quote_ok`); `chat()` and `_generation()` in `webapp/app.py`; `webapp/static/index.html` and `webapp/static/generate.html`; `handle_search_theology` in `src/studybible_mcp/server.py`. Covered by `tests/test_citations.py`, `tests/test_reply_check.py`, and `tests/test_chat_route.py`.

**Reverse when.** The label and notes can go if the maker finds them noise. The quotation rule in the reply check changes only with a new decision, since it closes a route around decision 0001.
