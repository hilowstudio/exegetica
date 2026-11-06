# Public-domain sources spike (2026-10-05)

Which public-domain sites can add books to the Reading Room. The legal test is **US** public domain, because Exegetica is hosted in the US:

- published before 1931: public domain;
- published 1931–63: public domain only if the copyright was not renewed.

A book that is public domain in Australia or Canada can still be under copyright in the US.

Baseline: 11,689 books (Gutenberg 9,338, Standard Ebooks 1,517, CCEL 830). The "new" counts below are titles that are neither in the library nor on gutenberg.org, worked out by fuzzy title + author matching. Treat them as upper bounds.

## Verdicts

| Source | Verdict | New, US-safe, English (est.) | Route |
|---|---|---|---|
| Standard Ebooks | **Ingest + sync** | 9 now, ~20/month | Diff the GitHub org (1,526 book repos) or the public Atom new-releases feed |
| Fadedpage | **Ingest** (US-PD filter) | 4,473 eligible (3,525 pre-1931 + 948 from 1931–63), before dropping periodicals/non-English | `allbooks.php` catalog (year per book) → session-cookie HTML download, ~1 req/s; strip the Fadedpage name |
| PG Australia | **Ingest selectively** | 2,208 eligible (1,785 pre-1931 + 423 from 1931–63), before dropping short single stories | `gutindex_aus.txt` + author-page years → `NNNNNNNh.html`; 782 are txt-only and need a chapter splitter |
| Wikisource | **Ingest selectively** | ~150–300 | "Ready for export" OPDS + Validated texts, ≤1930 → ws-export EPUB (noisy Parsoid markup to clean) |
| PG Canada | Ingest selectively (low priority) | ~300 | One index page → DP-style HTML; overlap with Fadedpage not yet checked |
| ExClassics | **Ingest selectively** | ~60–80 (drop ~10 unsuitable) | Per-title EPUB/TXT; the site dedicates its own transcriptions to the public domain |
| Lovecraft gaps | Fill gaps | ~30 stories | From Gutenberg (#30637, #76113, #73243, #70606) and Wikisource, **not** hplovecraft.com (all rights reserved) |
| Andersen / Grimm gaps | Fill gaps | Andersen tales we lack | Gutenberg #27200 (Paull translation); re-ingest Crane's Grimm |
| Global Grey | Discovery only | ~150–250 suitable | Cleared under UK rules (fails the US test for some), heavily occult; take texts from archive.org/PG instead |
| DPLA | Discovery only | 0 texts | Metadata only (CC0, S3 bulk); good for finding PD theology, then source clean copies |
| Public Domain Review | Discovery only | 0 books | Modern essays, mostly CC BY-SA; weighted toward occult/folklore |
| Projekt Runeberg | Skip (hand-pick) | ~70 | 119 English titles total, page-per-file OCR, robots blocks download |
| Distributed Proofreaders | Skip | 0 | Everything it finishes already goes to Gutenberg (51k titles) |
| sherlock-holm.es | Skip | 0 | We hold all 60 via Standard Ebooks |
| GrimmStories / AndersenStories | Skip | 0 | Mix PD translations with copyrighted ones (Ashliman ©2000, Hersholt 1949) |
| Literature Network | Skip | 0 | Gutenberg text with ads, all rights reserved, Cloudflare-blocked |
| Loyal Books | Skip | 0 | Texts link to PG/CCEL; useful only for LibriVox audio links |
| By the Fireplace | Skip | 0 | Gutenberg text; robots `Disallow: /` |
| DigiLibraries | Skip | 0 | Gutenberg mirror, terms forbid redistribution |
| E-Book Mecca | **Do not use** | 0 | Hosts pirated copyrighted books (Dahl, Goosebumps, Little House) |
| "Lex" | Skip | 0 | A reader app over PG/IA/SE, not a source |

## Copyright filters for the two big pools

- **Fadedpage** (9,145 books, DP Canada's output site): the US-PD rule is the one the library already uses: published before 1931, or 1931–63 and not renewed. Each book page gives "Published: YYYY", and the header gives the first-publication date and the author's dates. Revised editions carry the revision year (e.g. Nancy Drew 1959–68), so the filter catches them. Breakdown: 4,885 pre-1931, 4,079 from 1931–63 (3,963 not already in the library or on PG), 159 from 1964+ (skip). Also drop its ~613 periodical issues and ~260 non-English titles.
  - **Foreign authors, 1931–63:** for a non-US book, non-renewal doesn't make it US-PD, because the 1996 URAA restored US copyright in foreign works still protected at home on 1996-01-01. Such a book is US-PD only if it was already PD in its home country then: Canadian author died 1945 or earlier (life+50); British author died 1925 or earlier (life+70). Example: C. S. Lewis's *The Problem of Pain* (London 1940, Lewis died 1963) was restored and is not US-PD. The Fadedpage header's author dates make this check mechanical.
  - **Permission (2026-10-05):** Adam asked Fadedpage. Reformatting our own copies is fine, as long as we strip the Fadedpage name (header and DP Canada credits) from them.
- **PG Australia** (4,384, frozen since 31 Dec 2024): it uses Australia's rule (authors who died before 1955), so it carries *1984* and *Gone with the Wind*, and book headers carry **no US flag**. Keep titles with a stated year before 1931 or an author who died before 1931 (2,448). Its 854 titles dated 1931 or later go through the same renewal and foreign-author check as Fadedpage. For an Australian author, the home-country test is death in 1945 or earlier (life+50 in 1996). Skip its 1,082 undated titles. Its licence requires removing the PGA header and the "Project Gutenberg" name from modified texts.

## Eligibility list (built 2026-10-05)

[pd-nonrenewal-candidates.csv](pd-nonrenewal-candidates.csv), from `scripts/build_nonrenewal_eligibility.py`. It has one row per Fadedpage and PG Australia book. Each row gives a status, the renewal or registration evidence, the author's citizenship and death year, and whether the book is already in the library or on PG. Rerun it any time; everything is cached under `.seed_cache/`.

**How a status is decided**
1. **Published before 1931:** public domain.
2. **Published 1964 or later:** protected (renewal was automatic).
3. **Published 1931–63:** checked against NYPL's transcription of every renewal filed 1950–1991 (444k title entries). A renewal counts only when the title matches **and** the author's surname is in the record. A title-only match goes to `check`.
4. **Not renewed:** the book is public domain if it's a US work. It counts as a US work when the Copyright Office registered a US ("A") edition in its first-publication year (NYPL's 820k registrations, 1930–63), or when the author was American (Wikidata). That second test is what admits pulp stories: they ran in US magazines and never had book registrations.
5. **Not renewed, foreign:** the 1996 URAA restored US copyright unless the book was already public domain at home. That means the author died by 1925, or by 1945 for a citizen of a life+50 country (Canada, Australia, New Zealand, South Africa). Example: *The Problem of Pain* (1940, Lewis died 1963, British) is restored.

| Status | Meaning | Fadedpage new | PGA new |
|---|---|---|---|
| `pd-pre1931` | Public domain | 3,525 | 1,785 |
| `pd-not-renewed` | Public domain: US work, not renewed | 847 | 346 |
| `pd-foreign-home-pd` | Public domain: foreign, already PD at home in 1996 | 101 | 77 |
| `renewed` | Protected | 1,284 | 319 |
| `foreign-restored` | Protected (URAA) | 1,127 | 644 |
| `protected-1964+` | Protected | 156 | 21 |
| `check` | Title matches a renewal, author doesn't. Mostly real renewals under pen names (Hardy Boys, Kay Tracey, Patricia Wentworth); a few are another work with the same title | 453 | 160 |
| `foreign-needs-dates` / `-check-nationality` / `unknown-year` | Not enough author data; Fadedpage's book header gives the dates at ingest | 165 | 211 |

**Other sources in the same list** (`scripts/build_source_catalogs.py` builds their catalogs):

| Source | How it's cleared | Eligible, not in library or on PG |
|---|---|---|
| Standard Ebooks | SE clears every book under US law | 9 |
| Wikisource (Validated + Proofread) | Wikisource hosts only US-PD works; post-1963 items are modern US-government documents, marked `skip-modern-document` (404) | 3,391 works, but many are short pieces (articles, encyclopedia entries, periodical issues); expect ~150–300 book-length |
| ExClassics | Every text predates 1900 (Civil War pamphlets, 18th-c. memoirs, Foxe, Gerard); Wikidata lacks most of its authors, so it's cleared by site scope | 115 |
| Projekt Runeberg (English books) | Swedish site, so run through the full check; 3 foreign-restored, 2 post-1963 | 80 |

**Eligible now:** 4,473 Fadedpage and 2,208 PGA books that aren't in the library or on PG. Fadedpage's ~613 periodical issues and ~260 non-English titles, and PGA's single short stories, still need dropping at ingest.

**Known limits**
- A few renewals have no title in NYPL's data, e.g. *To Have and Have Not*, which is mislabeled `pd-not-renewed`.
- An author absent from Wikidata (160) can't use the citizenship test.
- Citizenship stands in for place of first publication.

## Project Gutenberg gap (2026-10-05 catalog)

Gutenberg has 61,794 English texts. We hold about 8,500 by Gutenberg ID, and ~1,440 more sit inside pulp issue collections. That leaves **~50,000 not in the library**. The original harvest (`scripts/harvest_gutenberg.py`) took only books on Gutenberg's editor-curated bookshelves, about 12k. It skipped the ~48k that carry only automatic "Category:" tags.

| Missing | Count | Note |
|---|---|---|
| Periodical issues | 3,992 | Punch, Notes and Queries, Atlantic, Chambers's, Blackwood's, Scientific American, Harper's Young People. Candidates for issue collections, like the pulps |
| Fiction | 18,120 | Many are single short stories |
| Literature (poetry, drama, essays, criticism) | 6,667 | |
| History & travel | 8,078 | |
| Religion & philosophy | 2,789 | |
| Science, medicine, technology | 3,874 | |
| Society, law, education | 2,165 | |
| Geography, arts, music, military | 2,313 | |
| Catalogs, bibliographies, government reports, dictionaries | 1,166 | Mostly not reading material |
| Raw scripture / hymn-text collections | 420 | Excluded by rule |
| Unclassified | 501 | |

Only ~690 non-periodical books on curated shelves are missing; the curated harvest was near-complete. Those 690 were probably dropped at fetch (no usable HTML) or removed in cleanup passes. 77 texts have been issued since our last catalog (2026-09-21).

Scale: books.db is ~5 GB for 11.7k books, so taking the whole tail would be roughly +15–20 GB on the Fly volume and on every R2 publish.

## Fixes found in our own library

- **Lucy Crane's Grimm (book 6893)** splits into only 4 chapters. It's a broken ingest: re-ingest from Gutenberg #19068.
- **Duplicate Holmes stories:** 8 single-story Gutenberg Holmes books (PG 8640, 8642–8647) duplicate the Standard Ebooks canon. Candidates for removal.
- **Missing Standard Ebooks:** Grant's *Personal Memoirs* is missing, probably because the import failed on its size.

## Suggested order

1. **Standard Ebooks:** the 9 missing titles and a weekly sync. Smallest job, best quality.
2. **The gap-fill set:** the Lovecraft gaps, the Andersen gaps, the Crane Grimm re-ingest, and the Holmes dedupe.
3. **Fadedpage:** the largest clean pool: pre-1931, plus 1931–63 books that weren't renewed (with the foreign-author check), with the Fadedpage name stripped.
4. **ExClassics and Wikisource:** small, curated, distinctive.
5. **PG Australia:** worth doing, but its HTML is inconsistent and nearly half the set is txt-only.

The Fadedpage and PG Australia pools are mostly 1900–1930 genre fiction (mystery, western, juvenile, adventure) plus Canadiana and Australiana. They need the same suitability review the existing shelves got.
