# In-App E-Reader — Source & Architecture Spike

Research spike (2026-09-14) for an in-app e-reader that lets users read full public-domain
works directly in Exegetica. Builds on `docs/living-library-sources.md` (the on-demand
adapter catalog) and reuses the extraction pipeline's text plumbing. Three parallel web
streams (Standard Ebooks, Gutenberg bulk datasets, net-new Christian PD) + a codebase audit.

## 0. The finding that reshapes the feature

**The 985 Christian classics in `theology.db` cannot be shown verbatim in a reader.** Our
own pipeline is deliberate: `extraction._US_CLEAR_SOURCES = {"gutenberg"}`, and `full_text`
is published **only when `us_clear`** (US-clear = published pre-1930). CCEL is explicitly
*grounding-only, never republished* — its terms are non-commercial and its editions may
carry copyrighted apparatus (see `webapp/sources/ccel.py` docstring). `theology.db` is a
**grounding corpus, not a reading corpus.**

Consequence: a reader that *displays* text needs **clean-provenance, US-clear PD** — and if
we want Christian classics *readable* in-app (Calvin, Augustine, Bunyan, Spurgeon), they must
be **re-sourced from us_clear provenance** (Gutenberg has many), not pulled from the CCEL
grounding text.

## 1. What's already built (reuse, don't rebuild)

- **Chapter segmentation** — `webapp/sources/text_processing.py::segment_into_chapters(text, toc)`
  returns `[{section_number, title, text}]`: tiered heading detection (major/minor/named/
  roman/arabic), coarsest-plausible-tier selection (2–120 sections), duplicate-division
  folding, TOC-title alignment. Also `strip_gutenberg_boilerplate` / `strip_ccel_boilerplate`.
  This is a reader's navigation backbone, done and tested.
- **Pluggable source registry** — `webapp/sources/registry.py` (`discover_all` + budgeted
  `fetch_first_available`); adapters `gutenberg` (Gutendex; us_clear; leads) and `ccel`
  (grounding-only). The Gutenberg adapter is already hardened for bulk seeding (retry/backoff).
- **License tiers codified** — `us_clear` / `public_domain` flags; encrypted tier-1 vault for
  in-copyright uploads (never shared).
- **Publish/boot-fetch pattern** — `scripts/publish_db.py <study-bible|theology>` → R2 →
  Fly volume `/data`, version-gated by content-hash markers. `study_bible.db` (853 MB) and
  `theology.db` (2.4 GB) already ride this. A third DB slots in cleanly.

## 2. Corpus recommendation — three tiers by provenance & role

### Tier A — General literature (the real gap; ship first)

| Source | Access (free path) | License | Format | Size | Ingest |
|---|---|---|---|---|---|
| **Standard Ebooks** ← showcase | **GitHub org** `github.com/standardebooks` (~1,500 repos, one per book); `git clone --depth 1` or tarball per repo. *Not* OPDS/bulk-zip — those are paywalled behind paid Patrons membership (401). | **CC0 1.0** (typesetting + metadata + covers); texts PD-in-US | Pre-unzipped semantic XHTML + `content.opf` spine + `toc.xhtml` nav + CSS | ~1,500 books, est. ~4–8 GB w/ images | **2** — spine + nav give exact chapter order/TOC for free; strip SE front/back matter (imprint/colophon/uncopyright) |
| **Project Gutenberg** ← breadth | **`sedthh/gutenberg_english`** (HF, parquet, headers pre-stripped, MIT) filtered by LoCC; top up from official `rsync` mirror + `pg_catalog.csv` | PD-in-US | Parquet rows w/ inline `locc`/`subjects`/`bookshelves` | 48,284 EN books / ~18 GB uncompressed | **2** — filter to literature LoCC `PR`/`PS`/`PN`/`PA`/`PQ`/`PT`; segment with our heuristic |

Standard Ebooks is the **hero reading experience** (~1.5k hand-typeset titles with real
structure); Gutenberg is **breadth behind it**. Both are us_clear/publishable and are exactly
the assignable classic canon (Austen, Dickens, Brontës, Twain, Melville, Shakespeare, Homer/
Dante in PD translation) the app lacks. SE "Spirituality" is only ~37 titles — negligible
overlap with our divinity corpus.

### Tier B — Christian classics, made *readable* (mission bridge)

Re-source from **Gutenberg LoC classes `BR` (Christianity), `BS` (Bible), `BT` (doctrinal),
`BV` (practical), `BX` (denominations)** — a few thousand titles, us_clear, publishable.
This is how Calvin/Augustine/Bunyan/Spurgeon become *readable in-app* rather than only a
grounding source. Overlaps our CCEL 985 in *identity* but not in *usable license*, so it's
net-new **capability** even where the work is the same. Dedup on normalized author+title only
to avoid shelving the same edition twice.

### Tier C — Deep Christian breadth (later, gated)

**Internet Archive — Princeton Theological Seminary collection** (`collection:Princeton`,
part of the 150k+ "Theological Commons"): thousands of net-new English PD Reformed/Puritan/
19th-c. dogmatics CCEL never digitized. Bulk-fetch is trivial (`ia download --search "…" --glob
"*_djvu.txt"`); the cost is **raw-OCR cleanup + curation**, so defer this behind Tiers A/B.

**Rejected / deprioritized:** SE OPDS feed (paywalled); HF `Nelathan/standardebooks` (430 MB
Markdown blobs — structurally lossy, ~270 books stale — fine for search, wrong for reading);
`manu/project_gutenberg` (unstripped, no filter columns); SPGC frozen set (tokens only, no full
text); sacred-texts.com Christianity + `gregorycrane/nicenefathers` (≈ CCEL duplicates);
CatholicCorpus/Orthodox/PRDL (Latin/Greek/Russian, not English-render-ready, license risk);
**Monergism / Grace Gems (by-permission — legally excluded)**.

## 3. Storage decision — a dedicated `books.db` on the Fly volume (not Neon)

Full-text books are large, static, and read-only → the same shape as `study_bible.db` /
`theology.db`. Keep them **out of Neon** (Neon is the live per-user mutable layer — chats,
memory, shelves, reading position; don't bloat it with GBs of static prose).

```
books        (id, slug, title, author, source, source_id, license, us_clear,
              locc, subjects, language, word_count, cover_key, added_at)
book_chapters(book_id, section_number, title, text)          -- pre-segmented at ingest
book_fts     (title, author, body)                            -- FTS5, optional in-book search
```

- Built by a seed script, published via an extended `scripts/publish_db.py books`, boot-fetched
  to `/data/books.db`, version-gated like the others.
- **Reading position stays in Neon** (per-user, mutable), mirroring `chat_state`/`memory_state`.
- The reader API can *union* books.db (curated corpus) with a user's own extracted
  `library_extractions.full_text` (us_clear rows) so both surface in one reading UI.

## 4. Ingestion mode — a bulk seed, distinct from the extraction pipeline

The extraction pipeline is on-demand and runs expensive LLM derive/objectives steps a reader
doesn't need. Add a **lighter bulk path** (`scripts/seed_books.py`):

1. **Standard Ebooks:** list org repos → clone/tarball → read `content.opf` spine + `toc.xhtml`
   → emit `book_chapters` directly from the per-file XHTML (chapters already delimited; no
   heuristic needed). New adapter `webapp/sources/standardebooks.py`.
2. **Gutenberg:** load `sedthh` parquet → filter by LoCC → `strip_gutenberg_boilerplate` →
   `segment_into_chapters` → `book_chapters`. Reuses existing text plumbing wholesale.
3. Dedup across sources on normalized author+title (prefer SE's typesetting when both exist).
4. `publish_db.py books` → R2.

## 5. Reader architecture

- **Routes:** `/read` (browse the shelf) and `/read/{slug}` (the reader). Server-rendered
  page shell like `/corpus` and `/course/*`.
- **API:** `GET /api/books` (catalog + filters), `GET /api/books/{id}` (metadata + TOC),
  `GET /api/books/{id}/chapter/{n}` (one chapter's HTML), `GET/PUT /api/books/{id}/position`
  (Neon reading position).
- **UI:** TOC sidebar from `book_chapters`, chapter-at-a-time scroll/paginate, restore last
  position, book-quality typography (reuse the type/measure discipline from `pdf-design.md`
  and the corpus page). SE chapters can render their semantic XHTML nearly directly.
- **Tie-ins:** Living Library catalog "Read" opens the reader; a chat citation can deep-link
  to `/read/{slug}#section-N`.

## 6. Phased build plan

- **Phase 1 — showcase + reader shell.** `books.db` schema + publish/boot-fetch;
  `standardebooks.py` adapter; seed ~1,500 SE titles; `/read` + `/read/{slug}` + chapter API;
  reading position in Neon. Smallest end-to-end slice that proves the reader.
- **Phase 2 — breadth.** Seed Gutenberg literature (LoCC `P*`) + Christian classics (LoCC
  `B*`) from `sedthh`; dedup; catalog browse/search + in-book FTS.
- **Phase 3 — deep Christian PD (later).** Curated IA/Princeton pull with OCR cleanup;
  highlights/annotations.

## 7. Open decisions (for the user)

1. **Corpus priority for Phase 1** — SE general-literature showcase first (recommended), or
   lead with Christian classics (Gutenberg `B*`), or both.
2. **Initial scale** — the full ~1,500 SE showcase, or a curated subset to start.
3. Confirm `books.db`-on-volume over extending Neon (recommended).
4. US-clear gate holds for the reader corpus (pre-1930); SE's PD is asserted **US-only** and
   "thought to be" — acceptable for a US, non-commercial ministry use, but note it.
