"""Public-domain / open full-text sourcing for the Living Library.

Ported (concepts, not code) from Quill & Compass's `src/lib/sources/`. Each source
exposes async `discover(meta) -> location | None` (light catalog lookup) and
`fetch(text_url) -> str | None` (heavy download + de-boilerplate). The registry
probes sources best-first and fetches the first that yields text, under a budget.

Guiding invariant, carried over verbatim: **a WRONG full text is worse than none** —
matching is deliberately conservative and every source fails closed (returns None)
rather than raising.
"""
