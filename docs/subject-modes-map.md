# Subject Modes: a map of every Yorkville department

**Status:** planning map, 2026-10-20. Bible is live, Social Sciences is live (Phase 2 shipping now), Agriculture has a plan (`docs/agriculture-sources.md`). This page sketches the rest, so each department can get its own research pass in turn.
**Rule:** every Mode is self-hosted like the Bible build. We download a source once, keep it, and serve it from our own server. Licenses marked **verified** were checked 2026-10-20; the rest are for each Mode's research pass.

## The whole school at a glance

| Department | Courses | Required credits | Mode and persona | Backbone we'd own | Readiness |
|---|---|---|---|---|---|
| Biblical Studies | 6 | 4.0 | **Theologian** | Study Bible + theology DBs | **Live** |
| Social Sciences | 8 | 3.0-3.5 | **Historian** | Avalon, NARA, Supreme Court, statutes, Reading Room | **Live** |
| Language Arts | 9 | 4.0 | **Literature teacher** | The Reading Room (14,977 books), WordNet, Webster 1828 | **High**: the library already exists |
| Science | 7 | 3.0-4.0 | **Scientist** | OpenStax Biology, Chemistry, Physics, A&P; PubChem; SymPy | **High**, once the teacher's rulings on origins are set |
| Mathematics | 8 | 3.0-4.0 | **Math tutor** | SymPy as the engine; Illustrative Mathematics (2019); OpenStax Algebra through Calculus | **High** |
| Agriculture | 9 | elective | **Ag educator** | NASS, FAOSTAT, FoodData Central, USDA publications | Planned |
| World Language | 3 | 2.0 (college prep; all students from 2028-29) | **Spanish tutor** | Reina-Valera 1909, Tatoeba, Wiktionary (Spanish), PD Spanish literature | **Medium-high** |
| Fine Arts | 3 | 0.5 | **Art and theater mentor** | The Met, Art Institute of Chicago, National Gallery (all CC0); Reading Room plays | **High** for art history; drawing and painting are practice-led |
| Business / Communications and Media | 8 | 0.5-1.0 | **Business and media mentor** | OpenStax Introduction to Business, SEC EDGAR, the speeches corpus, Reading Room rhetoric | **Medium**: Business and Speech are strong; the design-software courses have little to ground |
| Health and PE | 4 | 3.5 | **Coach and health teacher** | Dietary Guidelines, CDC, FoodData Central, free-exercise-db | **Medium**; health topics need the school's policies first |
| Engineering (Waubonsee) | 4 | dual credit | none for now | | Waubonsee runs the course |
| Preparatory (Life Skills 101) | 2 | | Folds into the Historian's economics tools | CFPB, IRS publications, the investing plan | **Medium** |

## Shared layers

Several Modes draw on the same sources, so each layer is built once and shared:

- **The Reading Room** serves Language Arts, History, Science (590 Science & Nature books), Fine Arts (374 plays, 83 art and music books), and Spanish (PD Spanish literature to add).
- **The Study Bible and theology tools.** The Historian already calls them, and every Mode can: Christian approaches to literature, science, art, work, and the body all sit there.
- **SymPy**, a local math engine (BSD, **verified**), serves Math, Science (chemistry and physics problems), and Agriculture (feed rations, yields). It replaces any need for a hosted service like Wolfram.
- **FoodData Central** serves Agriculture (Food Science) and Health.
- **OpenAlex** (CC0) gives every Mode a scholarly-papers slice.

## By department

### Language Arts (Freshman to Senior Literature, Honors sections, Newsprint/Journalism)

Every student takes four years, and the corpus is already built: 2,357 literary classics, 529 poetry, 414 short-story, and 374 drama titles in the Reading Room.
- **Sources:** the Reading Room; Princeton WordNet (BSD-style, free for any use with its notice, **verified**); Webster 1828 (already in the Historian's glossary); Wiktionary through kaikki.org (CC BY-SA 4.0, **verified**) for etymology.
- **Grammar and usage (checked 2026-10-20):** a public-domain shelf, all **verified**. Kittredge and Farley, *An Advanced English Grammar* (1913, Gutenberg #45814), for grammar. Reed and Kellogg, *Higher Lessons in English* and *Graded Lessons in English*, for sentence diagramming; both are already in the Reading Room. Fowler, *A Dictionary of Modern English Usage* (1926, US public domain since 2022; Internet Archive scan, OCR needs cleanup), for usage. Strunk, *The Elements of Style* (1918, Gutenberg #37134), for style. Woolley, *Handbook of Composition* (1907, scan only), for mechanics. For modern wording: Excelsior OWL (CC BY-NC 4.0) and *Writing for Success* (CC BY-NC-SA 4.0), which are fine for school use and would block a commercial version.
- **Grammar sites we link to only:** Cambridge English Grammar Today, Purdue OWL, EnglishGrammar.org, EnglishClub, British Council LearnEnglish, and the Blue Book (GrammarBook.com). Every one forbids storing its content or limits it to personal use, and EnglishGrammar.org bars AI use outright. Cambridge sells an offline data license (price by quote), and the British Council grants written permission; those two are the only ones worth asking.
- **Tools:** search the works, read a passage, a grammar and usage lookup over the shelf above, a literary-terms glossary we write ourselves, word lookup and etymology, poetry scansion (a local syllable and stress counter).
- **Teacher questions:** each grade's reading list, which modern (copyrighted) works they teach so the tool links to them without storing them, and how much writing help the tool gives (feedback on a draft or writing it for them).

### Science (Biology, Honors Biology, Chemistry, Honors and AP/Dual Credit Chemistry, Physics, Anatomy and Physiology)

OpenStax has a textbook for every course. **Verified catch:** most current OpenStax editions moved to CC BY-NC-SA 4.0. School use is fine. To stay on CC BY, pin the previous editions (Biology, Chemistry, A&P still CC BY 4.0) or High School Physics (CC BY 4.0).
- **Sources:** OpenStax source repositories on GitHub (`openstax/osbooks-*`); PubChem (no restrictions on use, **verified**) for compounds and the periodic table; NIST constants; Gray's Anatomy (1918, public domain); the Reading Room's natural-history shelf.
- **Tools:** search the textbooks, look up a compound or element, unit conversion and worked problems (SymPy), anatomy lookup.
- **Teacher questions:** this Mode needs the Theologian-and-teacher rulings first, the way the Historian's did: creation and the age of the earth, evolution, and how to present the positions Christians hold.

### Mathematics (Algebra I, Geometry, Algebra II, Trigonometry, Pre-Calculus, AP Calculus AB, Honors sections)

Math is computation more than retrieval, so the engine is the heart of it.
- **Sources:** SymPy (solve, simplify, graph, check a student's steps); Illustrative Mathematics 9-12 (the 2019 first edition is CC BY 4.0, **verified**; the newer v.360 is non-commercial; no bulk download, so a careful one-time copy); OpenStax Algebra and Trigonometry, Precalculus, Calculus Volume 1 (current editions CC BY-NC-SA; previous editions CC BY).
- **Tools:** solve and check, step-by-step hints that stop short of the answer, graphing (images drawn on our server), practice problem generator, the textbook search.
- **Avoid:** CK-12. Its license is custom and educational-only, and a reported clause bars AI use without a separate agreement (**verified** custom license; the AI clause is unconfirmed).
- **Teacher questions:** hint policy (how far the tutor goes before it gives the answer), calculator policy, AP Calculus pacing.

### World Language (Spanish I, Spanish II, Honors Spanish II)

Required for every student starting with freshmen entering 2028-29, so it grows.
- **Sources:** Reina-Valera 1909 (public domain, clean download from eBible.org, **verified**), which also adds a Spanish Bible to the Study Bible tools; Tatoeba sentence pairs (CC BY 2.0 FR, **verified**); Spanish Wiktionary through kaikki.org (CC BY-SA 4.0, **verified**); a verb conjugator (an open-source library); Spanish public-domain literature from Gutenberg.
- **Tools:** word lookup, conjugation, example sentences, a vocabulary drill by chapter, Spanish Bible passages side by side with English.
- **Teacher questions:** the textbook and its chapter vocabulary, which Spanish dialect and usage to favor.

### Fine Arts (Drawing, Painting, Theater Showcase)

- **Sources:** The Met Open Access (CC0, 470,000+ records, **verified**); Art Institute of Chicago data dump (CC0, with descriptions CC BY 4.0, **verified**), a natural fit for a school in Illinois; National Gallery of Art (CC0, **verified**). The dumps hold records only: we would fetch only public-domain images once, at build time. Theater draws on the Reading Room's plays.
- **Tools:** search artworks by artist, period, technique, or subject; art-history background; scene and monologue finder for Theater Showcase.
- **Teacher questions:** the course's projects and artists studied; a theology of art and beauty for the persona.

### Business / Communications and Media (Introduction to Business, Speech, Mass Communications, Critical Film Analysis, Yearbook/Journalism, Photoshop/Illustrator, Illustration and Graphic Design, 3D Rendering)

- **Sources:** OpenStax Introduction to Business (first edition CC BY 4.0, **verified**); SEC EDGAR filings (public domain) for real companies; the Historian's speeches corpus (presidential speeches, founding oratory) for Speech; Reading Room rhetoric and oratory; Wikidata film records (CC0) for Film Analysis; public-domain films on the Internet Archive.
- **Tools:** business-concept search, company lookup, a speech finder by occasion and technique, a film-history lookup.
- **Thin spots:** the design-software courses (Adobe, 3D) are skills taught in the software itself; the AP Stylebook and most journalism ethics codes are copyrighted.

### Health and Physical Education (Health and Wellness, Sports Performance, Intro to Team Sports, Competitive Team Sports)

- **Sources:** Dietary Guidelines and MyPlate (public domain, **verified**; the icon follows its style guide); CDC health pages (public domain except marked third-party images, **verified**); FoodData Central; free-exercise-db (800+ exercises, Unlicense, **verified**; where its data came from is unconfirmed). Skip wger: its data is licensed entry by entry and has no bulk file.
- **Tools:** nutrition lookup, exercise library by muscle group and equipment, training-plan builder, rules of the sports taught.
- **Teacher questions:** Health and Wellness touches sensitive topics. The school's policies and handbook decide what this Mode covers, and the Theologian should shape the persona with the teacher.

### Life Skills 101, Engineering, and the middle school

- **Life Skills 101:** CFPB financial-education material and IRS publications (both public domain, **verified**) plus the investing plan (`docs/investing-data-sources.md`). These fit inside the Historian's economics tools.
- **Engineering:** Waubonsee Community College teaches it under its own curriculum. Leave it out.
- **Middle school electives:** the high school Modes cover most of them. Archeology fits the Historian, the Study Bible's places, and Open Context (per-project CC licenses with strict attribution, **verified**). Agriculture, Art, PE, and Spanish use their high school Modes at a younger reading level. Social Media and Me matches the spine's Personal Relationships, Identity & Digital Discipleship subject, which the Theologian covers. Robotics and Study Skills have no strong source; leave them for later.

## Suggested order

1. **Language Arts:** every student, four years, and the library is already built. The fastest Mode to ship.
2. **Science:** required, a textbook per course, waits only on the origins rulings.
3. **Mathematics:** required, and SymPy does the heavy work.
4. **Agriculture:** Yorkville's signature program; its plan is written.
5. **Spanish:** grows to every student in 2028-29, and its Bible doubles as a Study Bible addition.
6. **Fine Arts, Business and Media, Health and PE.**

## Licensing notes

- **Share-alike:** OpenStax's current editions, Wiktionary, and some exercise data. Fine to serve inside the school; anything we adapt and hand out keeps the same license.
- **Attribution:** Tatoeba, OpenStax, Illustrative Mathematics, the Art Institute's descriptions, and Open Context (the strictest, which asks for credit even in AI answers). Each tool's answer carries its credit line, the way the Historian's sources do.
- **Images:** museum dumps hold records only; images come from public-domain works, fetched once at build time.
- **Federal sources:** use the text freely; leave out logos and seals.
- **Still to confirm:** the CK-12 AI clause, the Dietary Guidelines PDF's status, free-exercise-db's sources, and whether the OpenStax repositories hold the full text in a usable format.
