# Social Sciences Mode: sources and build plan

**Status:** Phase 1 built locally, 2026-10-19 (not deployed). Code: `src/socialsci_mcp/` (server, database, `prompts/historian.md`), `scripts/socialsci/harvest_avalon.py`, `scripts/socialsci/build_social_sciences_db.py` -> `db/social_sciences.db`; chat wiring in `webapp/app.py` (subject = bible | history) and the Bible | History switch in `webapp/static/index.html`. Publish with `scripts/publish_db.py social-sciences`; Fly reads `SOCIAL_SCIENCES_DB`.
**Courses served:** the seven Yorkville Social Sciences courses, in priority order below.
**Rule:** self-hosted, the same as the Bible MCP. Every source is downloaded or harvested once into our own SQLite database, published to R2, and served from the Fly volume. No tool calls an outside service when a student asks a question. An API is acceptable only as a one-time harvest channel, and only within its terms.

## The short answer

Social Sciences can be built almost entirely on owned data. Nearly every core source is public domain (U.S. government works, pre-1931 texts) or openly licensed (CC0, CC BY, CC BY-SA). Three well-known sources fail the rule and are left out: FRED, the American Presidency Project, and the full text of Founders Online. Each has a public-domain substitute.

## How it maps onto the Bible build

| Bible MCP | Social Sciences counterpart | Source (verdict) |
|---|---|---|
| Scripture text | Primary documents: founding documents, the founders' writings, speeches, statutes | Avalon Project (Yes), Library of Congress digitized books (Yes), Miller Center speeches (Yes), govinfo and U.S. Code (Yes), Wikisource subset (Yes), Reading Room (ours) |
| Confessions and creeds | Founding charters | Declaration, Constitution, Bill of Rights, Federalist (Reading Room / PD originals) |
| Commentaries (PD) | Classic historians and political writers | Reading Room: about 870 History and 305 Society/Politics/Economics books (ours) |
| `search_theology` (CCEL grounding) | `search_history`: hybrid full-text and semantic search over a history corpus | Reading Room shelves + LOC digitized books subset + Wikisource subset |
| Lexicon and word study | Period dictionaries | Webster's 1828 (Yes, CC BY-SA CSV), Black's Law Dictionary 1910 (Yes, raw OCR needs cleanup) |
| Cross-references | Clause-by-clause commentary and legal links | Constitution Annotated (Partly: PD but PDF only) |
| People / places graph (Theographic) | People, events, places, dates | Wikidata subset (Yes, CC0), congress-legislators (Yes, CC0), Pleiades (Yes, CC BY) |
| Church Fathers catena | Supreme Court opinions | Harvard Caselaw Access Project, U.S. Reports vols 1-572 (Yes) |
| (new) | Historical newspapers | Chronicling America bulk OCR (Yes, take a slice) |
| (new) | Historical maps | Newberry county boundaries, CShapes, historical-basemaps, Natural Earth (Yes) |
| (new) | Statistics | BLS, Census, Historical Statistics 1975, Maddison, World Bank WDI (Yes) |
| Theologian persona | A Christian historian's voice | To be written with the U.S. History teacher |

## Verified sources

### Primary documents and corpora

| Source | What we'd take | Bulk method | License | Verdict |
|---|---|---|---|---|
| LOC Selected Digitized Books | Subset of 90,414 PD books (U.S. history, government, speeches, older editions of the founders' writings) | data.labs.loc.gov/digitized-books/ (OCR text + 324 MB metadata) | "in the public domain and are free to use and reuse" | **Yes** |
| Chronicling America | Newspaper OCR for chosen eras or titles (e.g., Illinois papers, key events) | loc.gov/collections/chronicling-america/datasets/ (per-batch tar.bz2, 10 MB to 2.6 GB each; whole set est. 1.5-2 TB) | LOC: PD or "no known copyright restrictions"; titles over 95 years old fully PD | **Yes, slice only** |
| Miller Center speeches | About 1,000 presidential speeches | data.millercenter.org/miller_center_speeches.tgz | "The speeches are in the public domain." | **Yes** |
| Wikisource (English) | History and government category subset | dumps.wikimedia.org/enwikisource (3.4 GB) | CC BY-SA 4.0 on contributions; works mostly PD | **Yes** (rebuild text from `Page:` namespace) |
| Perseus (canonical-greekLit / latinLit) | English translations for ancient World History (about 788 Greek, 156 Latin) | GitHub / Zenodo | CC BY-SA 4.0 | **Yes** |
| NARA Catalog | Descriptions for discovery and citations | AWS Open Data (261 GB, take a subset) | CC0 for NARA-produced metadata | **Partly** (metadata, not full text) |
| Founders Online | Metadata index only | founders.archives.gov/Metadata (54 MB JSON) | CC BY-NC; editorial notes are press-copyrighted; no API; bot-blocked | **Partly.** Index only. Take the founders' texts from PD editions instead |
| Yale Avalon Project | Constitutional, diplomatic, and legal documents, ancient to modern | One-time polite crawl of the static pages (no bulk export) | "© 2008 Lillian Goldman Law Library," no stated reuse terms; open reuse confirmed informally by a Yale contact of Adam's (2026-10-19); the underlying texts are mostly PD | **Yes** |

### Law and government

| Source | What we'd take | Bulk method | License | Verdict |
|---|---|---|---|---|
| Harvard Caselaw Access Project | U.S. Reports vols 1-572 (Supreme Court through about 2018) | static.case.law/us/ (per-volume JSON/HTML) | Released "without restriction on access or use" | **Yes** |
| CourtListener | Supreme Court opinions after 2018 | Quarterly bulk CSVs (opinions file is 55 GB compressed; filter to `scotus`) | Public Domain Mark | **Yes, later** (heavy download for a small slice) |
| U.S. Code | All titles | uscode.house.gov/download.html (USLM XML) | U.S. government work | **Yes** |
| govinfo bulk data | Statutes at Large, Public Laws, bill status, Federal Register | govinfo.gov/bulkdata (XML) | U.S. government work | **Yes** (Congressional Record not in bulk) |
| Constitution Annotated | Clause-by-clause essays | govinfo PDFs (no XML) | U.S. government work | **Partly** (extract from PDF once) |
| congress-legislators | Every member of Congress 1789-present, presidents, VPs, committees | GitHub (YAML/JSON/CSV) | CC0 | **Yes** |
| Illinois Compiled Statutes + Illinois Constitution | Street Law, Illinois-specific | ilga.gov FTP (HTML), constitution HTML/PDF | ILCS declared public domain by statute | **Yes** |
| Black's Law Dictionary 1910 | Legal glossary | archive.org OCR (6.8 MB) | Public domain | **Yes, needs cleanup** (two-column OCR) |
| Oyez | Case summaries, oral arguments | Undocumented API, scrape only | CC BY-NC 4.0 (page not directly verified) | **Partly** |
| Supreme Court Database | Coded variables for every case 1791-2025 (issue area, vote split, majority author, how each justice voted) | scdb.la.psu.edu (CSV) | No license on the site; secondary sources describe it as Creative Commons-licensed; treated as open for school use by Adam's decision (2026-10-19), credited to The Pennsylvania State University | **Yes** |

### Reference, maps, and economics

| Source | What we'd take | Bulk method | License | Verdict |
|---|---|---|---|---|
| Wikidata | People with dates, wars, battles, treaties, polities, places | Paged SPARQL harvest (60 s query limit, 5 parallel), or WDumper; avoid the 156 GB full dump | CC0 | **Yes** |
| Wikipedia (English) | Background excerpts, with link and CC BY-SA notice | Article dump (25 GB compressed) | CC BY-SA 4.0 | **Yes, with attribution** (optional for v1) |
| Webster's 1828 | Founding-era definitions | github.com/akaitsurugi/webster1828 (CSV) | CC BY-SA 4.0 (1828 text PD) | **Yes** (don't scrape webstersdictionary1828.com) |
| Pleiades | Ancient places | Daily JSON / GitHub releases | CC BY 3.0 | **Yes** |
| Newberry Atlas of Historical County Boundaries | U.S. state and county boundaries 1783-2000, dated changes | Shapefiles + change database | Lawful reuse; CC BY-NC-SA copy included | **Yes** (best U.S. source) |
| CShapes 2.0 | World state borders 1886-2019, dated | CSV / GeoJSON | CC BY-NC-SA 4.0 | **Yes, non-commercial** |
| historical-basemaps | World borders at snapshot years, 2000 BCE on | GitHub | GPL-3.0 | **Yes** (rough in places) |
| Natural Earth | Base map | naturalearthdata.com | Public domain | **Yes** |
| BLS | CPI, wages, employment | download.bls.gov flat files (send a contact User-Agent) | Public domain | **Yes** |
| Census + Historical Statistics (1975) | Population and economic tables, colonial times to 1970 | Census FTP; Historical Statistics as PDF | U.S. government work | **Yes** (Historical Statistics needs table extraction) |
| Maddison Project 2023 | GDP and population, 169 countries | rug.nl (Excel) | CC BY 4.0 | **Yes** |
| World Bank WDI | Development indicators since 1960 | Bulk ZIP (270 MB CSV) | CC BY 4.0 | **Yes** |

### Excluded

| Source | Why | Substitute |
|---|---|---|
| FRED | Terms forbid storing, caching, or putting its content in a database | The same series from BLS, BEA, Census, Federal Reserve Board |
| FRASER | Terms bar scraping and database use | govinfo, HathiTrust public pages |
| American Presidency Project | No copying or redistribution | Miller Center speeches, govinfo / Federal Register |
| Founders Online full text | No API, bot-blocked, editorial content copyrighted | PD editions via LOC digitized books and the Reading Room |
| HathiTrust datasets | Research use only, no redistribution | LOC digitized books |
| Fordham Sourcebooks | Asks that texts not be stored locally | Use as a finding aid; take PD originals |
| NHGIS | No redistribution without permission | Newberry |

## Proposed v1 tools

Modeled on the Bible MCP's tool shapes. One `social_sciences.db` built at build time, plus the existing books.db for the Reading Room.

1. **`search_history`**: hybrid full-text and semantic search over the history corpus (Reading Room history and politics shelves, LOC digitized-books subset, Wikisource subset, Miller Center speeches). The counterpart to `search_theology`.
2. **`get_document`**: a founding or government document by name or section (Declaration, Constitution by article and clause, Bill of Rights, Federalist by number, major speeches and acts).
3. **`get_constitution_annotation`**: Constitution Annotated commentary for a clause.
4. **`search_cases` / `get_case`**: Supreme Court opinions by name, citation, or topic, with the Supreme Court Database's coding (issue, vote, majority author, each justice's vote) on every case, starting with a curated set of landmark cases for Government and Street Law, then the full U.S. Reports.
5. **`get_statute`**: U.S. Code, Statutes at Large, and Illinois statutes and constitution by citation.
6. **`lookup_person` / `explore_event` / `explore_place`**: the Wikidata subset plus congress-legislators. The counterpart to the Theographic people and places tools.
7. **`define_term`**: Webster's 1828 and Black's 1910, so students read the founders and old court opinions in their own vocabulary. The counterpart to the lexicon tools.
8. **`search_newspapers`**: Chronicling America slice ("what did papers say the week of Fort Sumter").
9. **`get_map`**: borders and boundaries in a given year (Newberry for U.S. counties and states, CShapes for 1886-2019, historical-basemaps earlier, Pleiades for the ancient world).
10. **`get_statistic`**: historical and current series (BLS, Census, Historical Statistics, Maddison, WDI).
11. **The persona**: a Christian historian's voice, written with the U.S. History teacher, with rulings on contested questions (e.g., the founders' faith, slavery and the Constitution, how to read a primary source).

## Courses served and priority

From the 2026-27 catalog. Graduation requires 3.0 credits of Social Sciences (3.5 for College Prep), and they "must include World History, US History, and Government/Economics." So four of the eight courses are taken by every student.

| # | Course | Grades / credit | Required? | What it needs from the tools | Ships in |
|---|---|---|---|---|---|
| 1 | **U.S. History** and **Honors U.S. History** | 11-12, 1.0 each | Yes (one of the two) | Founding documents, speeches, the founders' writings, slave narratives, newspapers, people and events, period vocabulary. **The Constitution Test** (students must pass it; it covers the U.S. Constitution, the Illinois Constitution, and the flag, plus the Declaration) | Phases 1, 3, 4, 6 |
| 2 | **U.S. Government** | 11-12, 0.5 | Yes (Government/Economics) | Constitution clause by clause, Supreme Court cases with their coding, statutes, Congress members, the Illinois Constitution, state and local government | Phase 2 |
| 3 | **Street Law** | 11-12, 0.5 | Elective | Constitutional law, landmark cases, U.S. and Illinois statutes, legal vocabulary (Black's), civil rights | Phase 2 (comes almost free with Government) |
| 4 | **World History** | 10-11, 1.0 | Yes | Renaissance and Enlightenment onward (the course starts there, not in the ancient world): Wikisource and LOC primary sources, the Reading Room (Machiavelli, Hobbes, Burke, Smith, Paine), Wikidata events, world borders by year | Phase 5 |
| 5 | **Economics** | 12, 0.5 | Yes (Government/Economics) | Classical and Keynesian texts (Smith in the Reading Room), U.S. data (BLS, Census, Historical Statistics), world data (Maddison, WDI). The course's investing unit needs current stock data, which can't be self-hosted; historical market data is a later question | Phase 6 |
| 6 | **Geography** | 9, 0.5 | No (standard elective) | Countries and capitals, climates and landforms, maps, resources and trade, and each country's religions compared with Christianity (the World Religions shelf and the theology tools help here) | Phase 6 |
| 7 | **Psychology and Sociology** | 11-12, 0.5 | No | Census and ACS data for the student research project; PD classics (William James). The weakest fit for this toolset; it may later want its own Mode | Phase 7 |

**Why this order:** U.S. History comes first because every student takes it, it carries the Constitution Test, and its sources are the most ready (Avalon, Miller Center, DocSouth, LOC books, the Reading Room). Government is second because it's required and adds the law layer, and Street Law rides along on that same layer at almost no extra cost. World History is required, but its post-Renaissance sources are more scattered (translations, European documents), so it follows. Economics and Geography share the maps and statistics layer. Psychology and Sociology fits least.

**Other departments that benefit:** Junior Literature and Composition (American literature read alongside its history), Speech (the Miller Center speeches), Yearbook/Journalism and Newsprint (historic newspapers), and Bible IV: Culture & Theology (founding-era faith, church and state).

**A note on World History:** because the course starts with the Renaissance, Perseus and Pleiades (ancient Greece and Rome) drop from v1. They stay in the source list for a later ancient-history need.

## Build order

1. **U.S. History core:** founding documents (Avalon Project), Miller Center speeches, DocSouth slave narratives, LOC digitized-books subset, and `search_history` over those plus the Reading Room. A Constitution Test study tool (U.S. Constitution, Illinois Constitution, Declaration, flag). Persona draft with the teacher.
2. **Government and Street Law:** CAP U.S. Reports with the Supreme Court Database coding, U.S. Code, Constitution Annotated, congress-legislators, Illinois statutes and constitution, Black's 1910 (cleanup).
3. **People and events:** Wikidata harvest (U.S. and world history subset).
4. **Reference:** Webster's 1828, Wikipedia excerpts if wanted.
5. **World History:** Wikisource and LOC post-1400 primary sources, world borders by year (CShapes, historical-basemaps).
6. **Economics and Geography:** BLS, Census, Historical Statistics, Maddison, WDI; Newberry county boundaries, Natural Earth; NBER Macrohistory if permission comes through.
7. **Depth:** a curated Chronicling America slice, post-2018 Supreme Court terms from CourtListener, Psychology and Sociology data.

## Licensing notes

- Most of the corpus is public domain. Attribution and share-alike apply to Wikipedia, Wikisource, Perseus, and the Webster's 1828 CSV: show the source and license with any excerpt.
- Several map and metadata sources are non-commercial (CShapes, Newberry's NC-SA copy, Oyez, Founders Online metadata). That fits Yorkville's school use, but it would block any commercial version of this Mode.
- Storage: the v1 subsets are small next to books.db (8.4 GB). The large datasets (Chronicling America, NARA, CourtListener, Wikidata) are only ever used as slices. The 40 GB Fly volume has room.

## Open items

- **Permissions:** DocSouth is cleared: its data page says UNC "has made the texts, encoding, and metadata in DocSouth Data available for use without restriction" and asks for credit (collections: The Church in the Southern Black Community, First-Person Narratives of the American South, Library of Southern Literature, North American Slave Narratives). NBER Macrohistory needs written permission: the database page states no license, and NBER's site terms allow only personal, non-commercial use and bar copying, data extraction, and automated access, with waivers valid only in writing. Adam requested permission (2026-10-19); NBER replied that it is not aware of any such restrictions and to go ahead (2026-10-20). Cleared for use. Fallback if declined: the 1975 Historical Statistics, which covers much of the U.S. side of those series (NBER also has British, French and German data).
- **Not yet verified:** Oyez license page wording, Founders Online transcription rights (vs. annotations), CAP license wording on case.law itself, Chronicling America total size, whether Wikidata's WDumper is currently working, Pleiades and CAP file sizes.
- **Decisions for Adam and the teacher:** confirm U.S. History as the lead course (recommended in the priority list above); which eras of newspapers to slice, whether to include Wikipedia excerpts, and the persona's voice and rulings.
