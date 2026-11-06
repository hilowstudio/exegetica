# Community Book Batch — Grades 8–12 (first seeding set)

**Purpose.** The first batch of literary works to seed the Living Library's shared catalog —
books that recur across US secondary curricula. Grounded in real, published reading lists
(not model memory), cross-referenced across three independent curriculum segments, then
split by US public-domain status because that decides the ingest route.

**Method.** Three parallel research passes, each pulling titles from published sources with
URLs (see Sources). A title's **consensus** = how many of the three segments it appears in:

- **P — Public school:** Common Core Appendix B text exemplars; AP English Literature
  (College Board FRQ + Albert.io aggregation); ALSCW national survey + 2025 RAND/NCTE report.
- **C — Classical / Christian:** Memoria Press; Veritas *Omnibus* I–VI; AmblesideOnline Y7–12;
  *The Well-Educated Mind* (Bauer); an ACCS-style school required-reading list.
- **H — Homeschool / popular:** Sonlight; BookShark; RethinkELA "100 Novels"; k-12readinglist.com.

**Ingest route (why the PD split matters).**
- **PD / US-clear (published ≤ 1930)** → auto-ingest via the pipeline's Gutenberg + CCEL
  adapters with **no upload**, and `full_text` is publishable. *This is the true first batch —
  we can process it today.*
- **In-copyright** → needs a teacher to upload a lawfully-accessed copy (upload path); only the
  transformative derivative is shared, never `full_text`.
- **Ancient / foreign works:** we ingest a **public-domain translation** (Gutenberg/CCEL carry
  older PD translations); modern translations remain in-copyright. The pipeline already encodes
  this — Gutenberg is `us_clear`, CCEL grounds derivation only.

---

## Batch A — Public-domain consensus (auto-ingest NOW)

These recur across segments **and** are US-public-domain, so they seed with zero uploads.
Consensus in brackets; grade band is the modal band across sources.

### Tier 1 — all three segments (P+C+H)
| Work — Author | Grade | Note |
|---|---|---|
| The Odyssey — Homer | 9 | PD translation (Butler/Lang on Gutenberg) |
| Hamlet — Shakespeare | 11–12 | |
| Romeo and Juliet — Shakespeare | 9 | most-taught text overall (RAND 2025) |
| King Lear — Shakespeare | 12 | |
| The Tempest — Shakespeare | 10–12 | |
| The Scarlet Letter — Hawthorne | 10–11 | already validated in our pipeline |
| The Great Gatsby — Fitzgerald | 11 | **PD since 2021** (pub. 1925) |
| Adventures of Huckleberry Finn — Twain | 11 | |
| The Adventures of Tom Sawyer — Twain | 8 | |
| Jane Eyre — Charlotte Brontë | 9–10 | |
| Pride and Prejudice — Austen | 9 | |
| Frankenstein — Mary Shelley | 10–12 | |
| Wuthering Heights — Emily Brontë | 12 | |
| Don Quixote — Cervantes | 11–12 | PD translation |
| Crime and Punishment — Dostoevsky | 11–12 | PD translation (Garnett) |
| Heart of Darkness — Conrad | 10–11 | |
| Moby-Dick — Melville | 10–11 | |
| The Canterbury Tales — Chaucer | 11–12 | |
| A Tale of Two Cities — Dickens | HS | |
| The Importance of Being Earnest — Wilde | 11 | |
| Oedipus Rex — Sophocles | 9–10 | PD translation |
| Little Women — Alcott | 8 | |

### Tier 2 — two segments, public domain
| Work — Author | Grade | Segments |
|---|---|---|
| The Iliad — Homer | 9–12 | C+H |
| The Aeneid — Virgil | 9–12 | C+H (PD translation) |
| The Epic of Gilgamesh | 12 | C+H (PD translation) |
| The Divine Comedy / Inferno — Dante | 11–12 | C+H (PD translation) |
| Beowulf | 11–12 | C+H (PD translation) |
| Sir Gawain and the Green Knight | 12 | C+H (PD translation) |
| Paradise Lost — Milton | 12 | C+H |
| The Pilgrim's Progress — Bunyan | 9 | C+H (validated in pipeline) |
| Gulliver's Travels — Swift | 12 | C+H |
| Robinson Crusoe — Defoe | 9–10 | C+H |
| Oliver Twist — Dickens | 9 | C+H |
| Great Expectations — Dickens | 9 | P+H |
| The Count of Monte Cristo — Dumas | 8–10 | C+H (PD translation) |
| The Red Badge of Courage — Crane | 10 | C+H |
| Candide — Voltaire | 9–10 | P+H (PD translation) |
| Macbeth — Shakespeare | 10 | P+C |
| Julius Caesar — Shakespeare | 9–10 | P+C |
| A Midsummer Night's Dream — Shakespeare | 9–10 | P+C |
| Othello — Shakespeare | 11–12 | P+C |
| Antigone — Sophocles | 10 | P+C (PD translation) |
| The Call of the Wild — London | 8–10 | H (+ near-canon) |
| The Metamorphosis — Kafka | 10 | P+H (PD translation) |

### On-mission PD classics from the classical/Christian spine (seed alongside)
Single-segment (mostly **C**) but public-domain, on-mission, and several already flow through
our CCEL adapter — high value for Exegetica specifically:
Augustine *Confessions* · Augustine *City of God* · Boethius *Consolation of Philosophy* ·
Athanasius *On the Incarnation* · Dante *Divine Comedy* (full) · Malory *Le Morte d'Arthur* ·
Spenser *The Faerie Queene* · More *Utopia* · Machiavelli *The Prince* · Plato *Republic* /
*Apology* · Aristotle *Poetics* · Herodotus *Histories* · Plutarch *Lives* · Walden — Thoreau ·
Of Plymouth Plantation — Bradford · Narrative of the Life of Frederick Douglass ·
Up From Slavery — Washington · Uncle Tom's Cabin — Stowe · Les Misérables — Hugo ·
The Brothers Karamazov / War and Peace / Anna Karenina · Dracula — Stoker ·
Dr Jekyll and Mr Hyde / Treasure Island — Stevenson · Sherlock Holmes — Doyle ·
The Picture of Dorian Gray — Wilde · Silas Marner — Eliot · Tess of the d'Urbervilles — Hardy ·
Leaves of Grass — Whitman · the poems of Dickinson, Frost, Poe, Longfellow.

---

## Batch B — In-copyright consensus (upload-gated wishlist)

Recur across segments but **not** public domain → a teacher must upload a lawfully-accessed
copy; only derivatives become shared. Ranked by consensus.

| Work — Author (pub.) | Grade | Consensus |
|---|---|---|
| To Kill a Mockingbird — Lee (1960) | 9–10 | P+C+H |
| Death of a Salesman — Miller (1949) | 11 | P+C+H |
| Fahrenheit 451 — Bradbury (1953) | HS | P+C+H |
| Our Town — Wilder (1938) | 11 | P+C+H |
| 1984 — Orwell (1949) | HS | P+C+H |
| Animal Farm — Orwell (1945) | 8–9 | P+C+H |
| Brave New World — Huxley (1932) | 9–10 | P+C+H |
| Things Fall Apart — Achebe (1958) | 10 | P+H |
| Their Eyes Were Watching God — Hurston (1937) | 11 | P+H |
| Of Mice and Men — Steinbeck (1937) | 9 | P+H |
| The Grapes of Wrath — Steinbeck (1939) | 11 | P+H |
| The Old Man and the Sea — Hemingway (1952) | 10–11 | C+H |
| Lord of the Flies — Golding (1954) | 9 | P+H |
| The Catcher in the Rye — Salinger (1951) | 9 | P+H |
| Night — Wiesel (1956/60) | 9–12 | P+H |
| A Separate Peace — Knowles (1959) | 11 | P+H |
| Invisible Man — Ellison (1952) | 11–12 | P+H |
| Catch-22 — Heller (1961) | 11 | P+H |
| The Color Purple — Walker (1982) | 11 | P+H |
| A Streetcar Named Desire — Williams (1947) | 11 | P+H |
| A Raisin in the Sun — Hansberry (1959) | 11 | P+C |
| The Crucible — Miller (1953) | 10–11 | P |
| The Stranger — Camus (1942) | 12 | C+H |
| The Hobbit / The Lord of the Rings — Tolkien (1937/54) | 8 | C+H |
| All Quiet on the Western Front — Remarque (1929) | 10 | C+H (translation still ©) |

*(Contemporary/diverse AP titles — Butler *Kindred*, Whitehead *Nickel Boys*, Adichie
*Purple Hibiscus*, Morrison *Beloved*, Vuong — appeared on a single source each and are not
yet in the survey-confirmed canon; hold for a later batch.)*

---

## Sources (grounded)

**Public school:** Common Core Appendix B (achievethecore.org / CCSSO PDF) · AP English Lit
2025 FRQ Set 1 (apcentral.collegeboard.org) · Albert.io AP Lit reading list · ALSCW "Literary
Study in Grades 9, 10, 11" (Stotsky et al.) · NCTE/RAND 2025 secondary-classroom texts report.
**Classical/Christian:** Memoria Press literature sequence + grade pages · Veritas *Omnibus*
book list PDF · AmblesideOnline Y7–Y12 · *The Well-Educated Mind* (Bauer) · Cornerstone
Christian HS required-reading list.
**Homeschool/popular:** Sonlight literature courses 130–630 · BookShark Levels I/J + World
Historical Lit · RethinkELA "100 Novels Every High School Student Should Read" ·
k-12readinglist.com grades 8–10.

## Caveats
- PD status is US copyright, published ≤ 1930 (matches the pipeline's `us_clear` gate). *The
  Great Gatsby* (1925) is PD as of 2021. *All Quiet* (1929) is out of copyright in the original
  but common English translations are not — treat as upload-gated.
- Ancient/foreign works: only a **PD translation** is `us_clear`. The pipeline prefers Gutenberg
  (US-clear) and grounds on CCEL without republishing — so a modern-translation copyright is
  never at risk from auto-ingest.
- Grade bands are approximate (modal across sources); many titles legitimately span 9–12.
