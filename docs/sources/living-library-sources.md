# Living Library — Full-Text Source Catalog & Adapter Plan

Research spike (2026-09-10) for the extraction pipeline's public-domain / open source
adapters. Ported design from Quill & Compass's `src/lib/sources/`; extended by a
3-front web research spike (verified against live docs). Companion to
`docs/sources/living-library-plan.md` (§5–§6 pipeline, §10 grounding-first seeding).

## 1. How sources plug into the pipeline (ported from quillnext)

- **Two-phase adapter** per source: `discover(meta) -> {source_id, text_url} | None`
  (light catalog lookup) and `fetch(text_url) -> str | None` (heavy download +
  de-boilerplate). Keeping them separate makes each a bounded unit of work.
- **Best-first registry**: `discover_all(meta)` probes every source in priority order
  and collects all hits; `fetch_first_available(hits, budget≈40s)` tries fetches in
  order until one yields text, and does **not** start a new fetch once the budget is spent.
- **Conservative, never-throw matching** (`score_title_author`): normalized title
  containment either direction + 3-char floor; if an author is supplied, its surname
  must appear among the candidate's authors, else **reject**. *A wrong full text is
  worse than none.* Every source fails closed (returns None) rather than raising.
- **Reusable format adapters** (build once, reuse widely): a **Pressbooks REST** adapter
  (`/wp-json/pressbooks/v2/...`) unlocks BCcampus, Milne, and much of the Pressbooks
  Directory; a **MediaWiki** adapter (`api.php?action=parse`) unlocks Wikisource,
  Wikibooks, Wikiversity, Wikimedia Commons; a **TEI/CTS** adapter unlocks Perseus +
  First1KGreek + (partly) Corpus Corporum/DTA; an **OAI-PMH** adapter unlocks DOAB/OAPEN,
  Europeana, DTA.

## 2. Licensing & legal gates (these decide what we may store/share)

- **US-copyright gate (we serve a US school).** Source-country PD ≠ US-clear. A work PD
  abroad (Canada/Australia life+50; EU/Nordics life+70) can still be under US copyright
  (US: most pre-1978 published works protected 95 yrs from publication). Every extraction
  carries **two flags**: `source_pd` and `us_clear`. We only store/share `full_text` when
  **US-clear** (published pre-1930, as of 2026). Source PD is necessary-not-sufficient.
- **License tiers → what may be shared** (ties to plan §1, §5, §10):
  - **PD / CC0 / CC-BY / CC-BY-SA** → full text shareable (SA obliges share-alike on
    derivatives; isolate it). Verbatim quotes OK for PD literature.
  - **Open textbooks (CC-BY) → "ground, don't echo"** (quillnext `TEXTBOOK_SOURCES`): use
    excerpts for factual grounding, teach in our own words, no verbatim.
  - **CC-BY-NC / NC-SA / ND** → **gated on the commercial question below.** If commercial:
    derive-only/reference-only (objectives as *alignment signals*, no text redistribution)
    — legal-review-required. If non-commercial: usable with attribution/SA hygiene.
  - **All-rights-reserved / by-permission / anti-scrape ToS** → excluded.
- **RESOLVED (2026-09-10): Exegetica is NON-COMMERCIAL (ministry / education)** — matches
  the study-bible corpus scope (`docs/sources/ingestion-roadmap.md`). The **NC tier is usable**
  (EngageNY / EL Education, Core Knowledge, CK-12, IM 2nd ed, NC OER) with attribution +
  ShareAlike hygiene. Still excluded regardless of commercial status: **by-permission**
  sites (Monergism, Grace Gems — permission ≠ license), **anti-scrape/anti-AI ToS**
  (CommonLit), **not-openly-licensed** (Fishtank), and **© / restricted** (Loeb, PHI Latin).
- **Hard exclusions found:** **CommonLit** (ToS explicitly bars scraping + AI training),
  **Fishtank** (not openly licensed), Feedbooks & ebooks@Adelaide (defunct), ManyBooks
  (ambiguous), Monergism/Grace Gems (by-permission), Loeb (©).

## 3. Full-text source catalog (build waves)

Already in quillnext (keep): **Gutenberg, Standard Ebooks, Wikisource, Internet Archive,
OpenStax, Siyavula, LibreTexts.**

### Wave 1 — on-domain + cleanest access (build first)
| Source | Access | License | Worth |
|---|---|---|---|
| **Project Gutenberg** | Gutendex API; **RDF bulk catalog** (`/cache/epub/feeds/rdf-files.tar.bz2`) for completeness; plain-text bodies | PD | HIGH (foundation; plain text = zero new deps) |
| **CCEL** | per-section HTML `?html=true` + AJAX scripture endpoint; ThML source; crawl slug index | PD (pre-1929 authors) | **HIGH — most on-mission** (Fathers→Reformers→Puritans→creeds) |
| **Sefaria** | v3 REST `/api/v3/texts/{tref}` (no key) + ~26GB GCS bulk + GitHub export; per-version license field | PD/CC0/BY/BY-SA/some NC | **HIGH** (biblical/Jewish primary; best API+bulk) |
| **Perseus / First1KGreek** | Git-native **TEI-XML** (`PerseusDL`, `OpenGreekAndLatin/First1KGreek`), CTS-URN addressing; Scaife CTS/DTS API | CC-BY(-SA) | **HIGH** (Greek/Latin classics + Greek patristics; clone repos) |

### Wave 2 — resolvers + broad literature
| Source | Access | Role |
|---|---|---|
| **Google Books API** | REST; `q=intitle:+inauthor:` / `q=isbn:`; `accessInfo.publicDomain` + epub/pdf downloadLink | Best title/author/**ISBN** resolver + PD EPUB/PDF (region-gated; PDF+OCR fallback). Needs API key |
| **Open Library** | keyless Read API (`/api/volumes/brief/isbn/{isbn}.json`) + Search + bulk dumps | ISBN→readable **resolver** → routes to Internet Archive |
| **HathiTrust** | keyless Bibliographic API (`catalog.hathitrust.org/api/volumes/...`) | ISBN/OCLC **resolver** (full text gated; metadata only) |
| **Europeana** | Search API `reusability=open` + OAI-PMH/FTP bulk + IIIF/Fulltext | Multilingual/regional long-tail (mostly IIIF/OCR + newspapers) |

### Wave 3 — OER textbooks (gated on the commercial decision; "ground-don't-echo")
| Source | Access | License | Worth |
|---|---|---|---|
| **Open Textbook Library** | public JSON API (`.json` on catalog URLs) + CSV/MARC bulk | mixed (filter BY/BY-SA) | HIGH — master **index** of open higher-ed textbooks (link-out to hosts) |
| **Oak National Academy** | first-class open API/SDK/ontology/MCP + bulk | OGL ≈ CC-BY (**commercial OK**) | HIGH — structured full text **and** per-lesson objectives |
| **BCcampus / Milne / Pressbooks Directory** | **Pressbooks REST** (one adapter) + EPUB/XHTML exports | mostly CC-BY | HIGH via the reusable Pressbooks adapter |
| **Saylor Academy** | GitHub **Common Cartridge**/Moodle bulk (`saylordotorg/course_backups`) | CC-BY (Saylor-original) | HIGH — CC-BY content **and** learning outcomes |
| **Wikibooks / Wikiversity** | **MediaWiki** API + full dumps | CC-BY-SA (copyleft) | MEDIUM — trivial ingest, uneven quality |
| OER Commons / MERLOT | token/gated metadata APIs, link-out | mixed | LOW-MED — discovery seeds only |

### Wave 4 — regional PD long-tail (US-copyright-gated)
| Source | Access | License basis | Worth |
|---|---|---|---|
| **Faded Page** | scrape (stable `allbooks.php` + `showbook.php?pid=` + `csearch.php`); TXT/EPUB/HTML | Canada life+50 | HIGH (of the no-API group; ~9,100 books, 13 langs) |
| **Project Runeberg** | bulk `download.pl?mode=work` (ZIP OCR+HTML) + IA mirror + datasets | Sweden/EU life+70 | HIGH for Nordic (raw OCR cleanup) |
| **Gallica / BnF** | **SRU** search + **IIIF** + OCR (`RequestDigitalElement`, ALTO) | French life+70, **per-item rights** | HIGH access, French-centric; must parse per-item rights + OCR presence |
| **PG Australia / PG Canada** | scrape only (index files + predictable paths); real full text | AU/CA life+50 | MEDIUM — unique life+50 titles; brittle scrape |

### Wave 5 — domain deep cuts (classical Christian school)
| Source | Access | License | Notes |
|---|---|---|---|
| **Dickinson College Commentaries** | scrape + Open Book Publishers EPUB/PDF/XML editions | **CC-BY-SA** | Classroom-ready Latin/Greek (Caesar/Vergil/Ovid…) with vocab + notes — small but perfectly on-target. HIGH |
| **ToposText** | REST API + **bulk RDF/Turtle** (`/TT-downloads`) | mostly open; **some translations by-permission** (filter) | ~1,000 ancient texts geo-linked — history/geography of the classical & biblical world. MED-HIGH |
| **CrossWire / SWORD PD modules** | public module repos (OSIS/ThML zips) | per-module (PD subset) | **PD commentary modules** (Matthew Henry, JFB, Gill, Calvin) pre-versioned — skip Bible text (we own it). MED |
| **Corpus Corporum** (UZH) | TEI-backed, site search; contact-for-bulk | per-subcorpus | **Patrologia Latina + Vulgate + patristic Latin** — HIGH content, access is the limiter |
| **DOAB / OAPEN** | OAI-PMH + REST + PDF/EPUB download; **ISBN/DOI present** | per-title CC (some NC/ND) | modern **CC-licensed** theology/biblical **monographs** |
| **The Latin Library** | scrape (flat HTML, `/{author}.html`) | PD/uncertain (no provenance) | fast bulk Latin plain text where citation rigor isn't needed. MED |
| **Documenta Catholica Omnia** | scrape (PDF/HTML) | PD Migne editions (gray aggregator) | deep Latin patristics; prefer Corpus Corporum/First1KGreek first. MED |
| **Deutsches Textarchiv** | TEI + OAI-PMH bulk | CC-BY-SA/NC | German Reformation-era |
| **sacred-texts.com** | bulk `.txt.gz` + scrape | **mixed — © John Bruno Hare on parts** | comparative religion; CCEL covers the Christian subset better |

**⛔ Flag / do NOT ingest:** **Monergism**, **Grace Gems** (by-permission / non-commercial / ©), **PHI Latin** (viewing-only, no redistribution), **Loeb** (© subscription — get PD-expired original volumes from IA/Gutenberg instead), and the **© portions of sacred-texts**. Re-source any PD authors from CCEL / Gutenberg / Wikisource where status is unambiguous.

## 4. Objectives sources (for the community-objective seeding, plan §10)

Seed community objectives **only** from verifiable, appropriately-licensed sources:

- **Commercial-safe (CC-BY / OGL):** **Oak National Academy** (best — explicit per-lesson
  outcomes in an open API/ontology), **Illustrative Mathematics 1st ed.** (per-lesson
  Learning Targets + standards; ⚠️ 2nd ed "v.360"/TK is NC), **Saylor** (per-unit outcomes),
  **Louisiana LDOE ELA Guidebooks** (per-lesson "look-fors" tied to anchor texts; verify
  exact CC), **PhET** (CC-BY "Learning Goals" per sim).
- **NC (EngageNY DNA) — USABLE (we are non-commercial), with attribution/SA hygiene:**
  EngageNY / EL Education / UnboundEd, Core Knowledge (CKLA + Sequence), CK-12. The
  richest, most granular objectives + essential questions tied to specific texts. Isolate
  ShareAlike-derived data so obligations don't bleed.
- **Off-limits regardless:** CommonLit (anti-scrape/anti-AI ToS), Fishtank (not open).

## 5. Canon / reading-list sources (which books to pre-seed)

Titles + authors are **facts** (not copyrightable); the curated *sequence/annotations*
often carry site copyright — extract the book identities, don't clone their prose. None
offer an API → scrape the HTML/PDF booklists to `{title, author, stage, source}`, dedupe,
then resolve each to a full-text adapter (Gutendex / Perseus URN / CCEL index / Standard
Ebooks). This is where the canon meets acquisition.

| Source | Access | Fit | Worth |
|---|---|---|---|
| **AmblesideOnline** | structured HTML, per-year pages (`/ao-y{N}-bks`) | Charlotte Mason K-12, PD "living books", Christian | **TOP** — best structured, extractable, PD-aligned classical-Christian canon |
| **St. John's College reading list** | free structured HTML | gold-standard 4-yr great-books (antiquity→modern, incl. Bible/Augustine/Aquinas/Calvin) | HIGH |
| **Veritas "Omnibus" / ACCS lists** | published booklists (HTML/PDF) | **exact Reformed-classical alignment** | HIGH |
| **Memoria Press scope & sequence** | catalog + S&S (HTML/PDF) | classical-Christian, Latin-forward | HIGH |
| **Thomas Aquinas College** | published 4-yr list (HTML) | canonical, theology-heavy | HIGH |
| **Great Books of the Western World / Syntopicon** | widely reproduced author/work list | canonical backbone | HIGH |
| **The Well-Trained Mind / Well-Educated Mind** | free pages (HTML); fullest lists in © books | trivium-staged great books | HIGH |
| **PRDL** | scrape author/title pages | **Reformation-era primary-source discovery** | HIGH (as canon layer) |
| Circe Institute · Classical Academic Press · Bloom's *Western Canon* | scrape | supplementary framing/titles | MEDIUM |

Also standard, fact-based: **CCSS Appendix B** text exemplars (book→grade band) and **AP
English** reading lists (for grade-level placement / breadth).

## 6. Build order (roadmap — does NOT front-load all adapters)

1. **Prove the core extraction on Gutenberg alone** (plain text, zero new deps): fetch →
   sections → derivative + `full_text` → grounded objectives w/ citations → verify → spine
   alignment → DB. This is the current next build.
2. Add **CCEL, Sefaria, Perseus** (Wave 1 on-domain) behind the same registry once the
   core works — each is a discover/fetch adapter.
3. Add the **resolvers** (Google Books/Open Library/HathiTrust) + Internet Archive/Wikisource.
4. Build the **reusable format adapters** (Pressbooks, MediaWiki, TEI/CTS, OAI-PMH) → OER
   waves, gated on the commercial decision.
5. Regional (Wave 4) + domain deep cuts (Wave 5) as coverage demands.

## 7. Open decisions
- ~~Commercial vs non-commercial~~ — **RESOLVED: non-commercial** (NC tier usable; see §2).
- Confirm the **US-copyright gate** approach (store/share `full_text` only when US-clear).
- Wave-1 build scope after Gutenberg (all three on-domain, or sequence them).
- New dependencies to add when we reach non-plain-text sources: an HTML parser
  (selectolax/bs4), TEI/XML (lxml), EPUB (ebooklib), PDF (pypdf) — none needed for Gutenberg.
