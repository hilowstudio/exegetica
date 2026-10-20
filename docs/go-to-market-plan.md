# Exegetica Editions: Go-to-Market Plan

*Drafted 2026-10-13. Claude executes this plan. Adam approves each release wave and every public listing.*

## Goal

Every book in the Reading Room becomes an Exegetica edition that is:

- verified against a trustworthy reference text,
- beautifully set, and
- available where people already look for free ebooks: search engines, Kindle (by Send to Kindle), e-reader apps and free-ebook stores.

Nothing goes to a marketplace until it has passed a careful review of that single title. Titles are worked in order of popularity, with seasonal waves first. Halloween is the first wave.

## Why a review of every title

Most of the 15,000 books were formatted by deterministic scripts:

- chapter splitting
- multi-volume merges
- front and back matter removal
- title normalization
- OCR clean-up
- the serve-time typesetting pass

Each script is right in aggregate and wrong somewhere in particular, and the audit on 2026-10-13 confirmed it. A book can lose a paragraph at a chapter seam, gain a stray running header, or have a heading misread. Before an edition carries our name into a store, it has to be checked against what the book is supposed to contain.

## The review protocol (per title)

### 1. Ground the title

Gather the best available reference, by tier:

| Tier | Reference available | Examples | Effort |
|---|---|---|---|
| A | A clean, independently produced edition: the Standard Ebooks source on GitHub, a careful Wikisource transcription, or Perseus TEI for classics | Dracula, Frankenstein, Dorian Gray | Low |
| B | Only our own source as distributed (raw Gutenberg HTML or text, CCEL ThML), plus a second edition or an archive.org scan where one exists | Carmilla, Sleepy Hollow, Poe | Medium |
| C | A clunky source: OCR from scans, pulp magazines, poorly marked-up Gutenberg | Pulp issues, small-press 19th-century titles | High: page images are the reference |

Also record the bibliographic facts the edition will state: first publication year, the authoritative chapter or part structure, and the original subtitle.

### 2. Run the automated fidelity check

Align the text we serve (after typesetting) with the reference, word by word and chapter by chapter. Flag:

- **Missing and extra text:** missing passages (over 15 words), inserted stray text (running heads, page numbers, notes in the wrong place), and duplicated or reordered passages.
- **Structure:** chapter count, order and headings that differ from the reference's structure.
- **Lost markup:** lost italics, verse whose line breaks were lost, footnote markers without notes (or notes without markers), and letters, diaries or datelines that were flattened. This matters for epistolary books like *Dracula* and *Frankenstein*.

The check produces a report per title and a pass/fail score.

### 3. Read it closely (Claude)

- **Structure:** the contents page against the reference structure, the opening and closing of every chapter, and the front and back matter.
- **Flags:** every flagged span from step 2, resolved one by one.
- **Special structures:** verse, letters, epigraphs, footnotes and part titles, each checked in place.
- **Spot reading:** passages from the beginning, middle and end.
- **Fixes:** recorded as logged per-book corrections against the stored text, with the database backed up first. Fixes are never improvised in the reader.

### 4. Check it visually

Render the title page, colophon, contents, a chapter opener, a running page, and any verse, notes or letter pages, each in light mode, dark mode and at phone width. Review the screenshots.

### 5. Write the edition metadata

- A description of 80–150 words, written by us under the house voice rules.
- Subjects (BISAC codes for stores), keywords and the first publication year.
- The final cover render.

### 6. Package and test

- Build the EPUB and pass epubcheck with no errors.
- Test on a real Kindle by Send to Kindle, and in at least one EPUB reader.

### 7. Sign off

The title's status moves to **ready**, and it is listed for Adam's approval in that wave's release batch.

### Tracking

Each title's status lives in a tracking table:

- grounding tier
- reference sources
- fidelity score
- issues found and fixed
- reviewer notes
- EPUB check result
- release status

A dashboard page shows the pipeline.

## Distribution channels, in order

1. **Exegetica book pages.** Every book gets its own public page that search engines can index: cover, opening pages, contents, Read, Download EPUB and Send to Kindle. The pages carry structured data marking each book as free, and a sitemap lists them all. This channel is fully in our control.
2. **Send to Kindle.** After a one-time setup, a reader taps once and the book arrives on their Kindle.
3. **An open OPDS catalog feed.** Add one-click "add to Thorium" links, and list the feed on the MobileRead wiki's OPDS directory. Standard Ebooks' feed is now members-only, so ours would be the open alternative.
4. **Open Library Trusted Book Providers.** Exegetica would sit behind Open Library's "Read" button, as Standard Ebooks does. Nominate through openlibrary.org/book-providers or a GitHub issue, and offer to write the importer.
5. **KOReader's built-in catalogs.** These sit beside Gutenberg and Standard Ebooks; getting in is a pull request to `opds.koplugin` once our feed is stable. A Calibre "Get Books" store plugin works the same way.
6. **Internet Archive uploads,** in bulk through its command-line tool. They mirror the editions and feed Open Library and long-tail search. Each edition's design would be marked CC0 so its rights are clear.
7. **Apple Books.** It's the only retail store still open to free public-domain editions: free-only accounts need no banking. Pilot 3–5 Wave 0 titles first, with the edition named in the title ("Dracula (Exegetica Edition)"), because Apple removes exact duplicates and blocks bulk "spam".
8. **Community announcements** (MobileRead, r/ebooks, r/kindle, r/publicdomain) at milestones.

**Ruled out** (store research, 2026-10-13):

- **Google Play Books:** "Books containing public domain material are no longer accepted, except from select partners."
- **Kobo Writing Life:** "no longer accepting new public domain works."
- **Barnes & Noble Press:** dropped public-domain works in April 2026, and accounts that keep posting them may be closed.
- **Draft2Digital and Smashwords:** "We do not accept Public Domain works."
- **Amazon KDP:** accepts public domain only with a new translation, annotations or 10+ original illustrations. It names "formatting improvements" as not counting, and the minimum price is $0.99.

## Order of work

Titles are worked from most to least popular, interrupted by seasonal waves.

- **Popularity ranking:** built from Gutenberg download counts and Open Library reading-log and rating counts, with canon status as a tie-breaker. Every title gets a rank.
- **Wave 0, Halloween (now through October 31):** the most-read horror and gothic titles.
- **Wave 1, the core canon:** the top 500 titles by rank, across all shelves.
- **Wave 2, Christmas (early December):** *A Christmas Carol*, Dickens's other Christmas books, seasonal anthologies and devotional classics.
- **Then:** the remaining titles in rank order. The long tail gets the automated check and a lighter read. Only fully reviewed titles go to stores; every title stays on Exegetica.
- **Poetry:** a separate rebuild later. It stays out of all waves until then.

### Wave 0 titles

| Tier | Titles |
|---|---|
| A (Standard Ebooks reference) | Dracula, Frankenstein, The Strange Case of Dr Jekyll and Mr Hyde, The Picture of Dorian Gray, The Turn of the Screw, The Phantom of the Opera, The Castle of Otranto, The Monk, The Mysteries of Udolpho, Uncle Silas, Melmoth the Wanderer, The King in Yellow, The Invisible Man, The Island of Doctor Moreau, The Beetle, The Haunted Hotel, The Hound of the Baskervilles, Wuthering Heights, Northanger Abbey |
| B (Gutenberg) | The Legend of Sleepy Hollow, Carmilla, The Fall of the House of Usher and Poe's tales, The Great God Pan, The Lair of the White Worm, The Jewel of Seven Stars |
| Missing; add as fresh imports | Polidori's The Vampyre, Hugo's The Hunchback of Notre-Dame |

## Order of building

**The gate (Adam, 2026-10-13):** no EPUB builder, and no packaging or distribution work, until we are happy and confident with the state of our copies. The copies come first.

**Phase 1: the copies.**

1. **Deploy the interior work.** This includes the typesetting pass, the front and back cleanup, and adding pyphen to the Docker build.
2. **Review tooling:**
   - reference fetchers (Standard Ebooks GitHub, Gutenberg raw, Wikisource)
   - the fidelity aligner and its report
   - the tracking table and dashboard
   - the screenshot harness (it exists)
3. **The popularity ranking.**
4. **Reviews, wave by wave.** For each title, steps 1–5 of the review protocol, ending in a reviewed, corrected copy.

**Phase 2: packaging and distribution.** This starts only once Adam is satisfied with the reviewed copies.

5. **The EPUB builder,** with e-reader styling: a drop cap fallback, fixed-weight embedded fonts subset per book, ornaments as images, and footnotes marked up for pop-up notes. epubcheck is wired in.
6. **Send to Kindle:** an email service, plus a saved Kindle address per user.
7. **Public book pages,** with structured data and a sitemap.
8. **The OPDS feed, Open Library, KOReader, Internet Archive, Apple Books and KDP** (KDP with the illustrations).

## Timeline for Wave 0 (target: live by October 24)

| Dates | Work |
|---|---|
| Oct 13–16 | Deploy the interior. Build the review tooling. Rank the titles. |
| Oct 15–22 | Review and correct the Wave 0 copies. Tier A first; about 25 titles total. |
| ~Oct 22 | Adam reviews the corrected copies in the reader. Packaging and distribution begin only once he is satisfied. |
| After that | EPUB, Send to Kindle, public pages, OPDS and stores, as fast as the gate allows. |

The gate comes first, so Halloween distribution may slip. Whatever happens, the corrected copies will be live in the Reading Room for Halloween.

## Throughput, honestly

| Tier | Time per title (Claude session time) |
|---|---|
| A | about 20–40 minutes |
| B | about an hour |
| C | several hours |

At that pace the top 500 titles take weeks. The full 15,000 take many months, which is why the long tail gets the automated check plus a lighter read, and only fully reviewed titles enter stores.

Any bulk paid model run, such as AI proofreading of OCR against scans, will be proposed with a cost estimate first and never started without approval.

## What Adam provides

- **Approval** of each wave's release batch and of every public listing.
- **Accounts** that need his identity: an Apple Books for Authors free-only account (it uses the legal name, and needs no banking for free books), an email service for Send to Kindle, and later an Internet Archive account.
- **A Kindle for testing.** His wife has kindly volunteered.

## Open questions

- **Publisher name on store listings:** "Exegetica"?
- **Credits:** Apple's metadata for a translated work may need the translator named, even though the book itself carries no credits. Decide before the Apple pilot.
- **KDP later?** Amazon accepts public-domain editions with 10+ original illustrations or real annotations. Our cover motifs and an annotated school edition could qualify someday, but the minimum price would still be $0.99.
