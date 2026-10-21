# History people and events graph: design

**Status:** design, 2026-10-20. Nothing built. Phase 3 of `docs/social-sciences-sources.md`, built together with World History (phase 5).
**Goal:** give the Historian what the Theologian has in its people and places graph: who someone was, whom they were connected to, what they took part in, and where and when it happened. The answers come from structured data on our own server, not from the model's memory.

## What the Bible graph does today

The Study Bible graph comes from Theographic (people, places, events, people groups). It is small: 3,069 people, 1,274 places, 450 events, and 4,321 family edges. It ties into Scripture through 53,120 verse mentions. Its tools:

| Bible tool | What it answers |
|---|---|
| `explore_genealogy` | Ancestors and descendants (a recursive query over father and mother edges) |
| `explore_person_events` | A person's events in order, with places |
| `explore_place` | Events at a place, people born or died there |
| `find_connection` | Shortest family path between two people (breadth-first search) |
| `people_in_passage` | People, places, and events mentioned in a verse or chapter |
| `graph_enriched_search` | A verse with its people and their immediate family |

Each tool also draws a Mermaid diagram.

**Weak points to fix in the history build:**
- It quietly takes the first person matching a name, so a question about one Mary can get another Mary's answer.
- The only links are four family types, and a person's tie to an event carries no role.
- Dates are a single year, with no precision.
- Name search has no full-text index.
- The path search reloads every edge on each call.
- Facts carry no source.

## The parallel

| Bible graph | History graph |
|---|---|
| Theographic | Wikidata (CC0), a harvested slice |
| `graph_people` | `h_people`: name, aliases, birth and death with date precision, short description, Wikidata id |
| `graph_places` | `h_places`: Wikidata places joined to GeoNames and Pleiades coordinates, with former names by date |
| `graph_events` | `h_events`: wars, battles, treaties, revolutions, elections, laws, court cases, councils, with start, end, and precision |
| family edges (4 types) | `h_edges`: typed and dated. Family (father, mother, spouse, child, sibling), office held, party, served in, commanded, participated in (with role), signed, authored, succeeded, part of (battle → war), followed by, influenced by, student of, religion |
| verse mentions | `h_mentions`: which people and events appear in our primary sources and court cases |
| a verse reference | a document passage or a Supreme Court case |

Links into what we already have:
- **Congress:** our congress-legislators table carries each member's Bioguide id, which Wikidata also stores.
- **The Supreme Court:** Wikidata's justices and cases link to our cases table, through the Supreme Court Database's justice names and U.S. Reports citations.
- **Documents:** Wikidata's "author" and "signatory" fields connect people to the documents in our corpus: the Declaration's signers, a treaty's parties, a speech's speaker.
- **The Bible:** a small crosswalk of New Testament-era figures (the Herods, the Caesars, Pilate) lets the Historian step from the Gospels into Rome. Church history links run through religion, office held (bishops, popes), and the Theologian's church-fathers tool.

## Tools

1. **`lookup_person`:** who someone was. When a name matches several people, it lists each with dates and a one-line description and asks which one, or takes the id. This fixes the Bible graph's silent first match.
2. **`explore_family`:** genealogy (the Adamses, the Roosevelts, royal houses), with marriages between houses.
3. **`explore_life`:** a person's timeline: born, educated, offices held, wars fought, documents signed, died. Each item is dated and sourced.
4. **`explore_event`:** an event's when, where, and who (each person with a role: commander, signatory, delegate), what it was part of, and what came before and after.
5. **`explore_place`:** what happened there, who was born or died there, what it was called at the time.
6. **`find_connection`:** the shortest meaningful path between two people, with each link's type and date: "Lincoln appointed Salmon Chase Chief Justice (1864)." The search runs both ways over a stored link table, and leaves out links that would make every path trivial (sharing a citizenship, for example).
7. **`timeline`:** what was happening in a span of years and a region. "What else was going on in 1776?" Built for history; the Bible graph has nothing like it.
8. **`succession`:** who held an office or throne before and after someone, or the full list of holders.
9. **`people_in_document`:** the parallel to `people_in_passage`, for a document or a case.

Every answer carries the Wikidata id and a link for each fact. The persona treats the graph as structure (who, when, where) and leaves interpretation to the primary sources and books.

## Building it

- **Harvest:** paged queries against the Wikidata query service by class (people with notable offices or occupations, wars, battles, treaties, and so on). This avoids the full 156 GB dump. A notability cutoff (the number of Wikipedia language editions with an article on the item) keeps the set to people a student might meet. We set the cutoff by sampling, aiming at tens of thousands to a few hundred thousand people.
- **Scope:** U.S. history in full; world history from 1400 on (the World History course); ancient and church history to the extent the Bible crosswalk and the church-history links need.
- **Mentions:** a local name-matching pass over our documents and cases, with no paid API. It matches names and aliases, and uses dates to rule out anyone who wasn't alive when the document was written. Only confident matches are stored, so a wrong "Washington" is left out rather than guessed.
- **Storage:** new tables in `social_sciences.db`, with full-text search over names and aliases and an index on every link. The link table is stored in both directions, so the path search never reloads it.
- **Size:** likely a few hundred MB.

## Decisions

Counts from Wikidata (2026-10-20), by the number of Wikipedia language editions with an article on the person:

| People | 3+ | 5+ | 10+ | 20+ |
|---|---|---|---|---|
| Everyone | 1.58M | 830k | 309k | 90k |
| U.S. citizens | 266k | 142k | 56k | 19k |
| Born in Illinois | 12k | 6.8k | 2.8k | 917 |
| Living | 789k | 433k | 160k | 47k |
| Living, holds or held public office | 103k | 52k | 18k | 5.8k |

1. **Living people (decided 2026-10-20): office holders plus people with a historic public role.** Presidents, justices, members of Congress, governors, heads of state, plus a curated role list: civil-rights leaders, astronauts, Nobel laureates, military commanders, church leaders. Living athletes, entertainers, and private people are left out.
2. **Notability (decided 2026-10-20): tiered, plus anyone with a role.** Born in Illinois at 3+ articles, Americans at 5+, everyone else at 10+ (20+ for those who died before 1400). Anyone else who holds an office, signed a document, or took part in an event in the graph also comes in. Roughly 200,000 people.
3. **Mentions (decided 2026-10-20): a hybrid.** Reading every document, opinion, and book with a model would take about 440M tokens (some $1,800 at Opus input rates), so mentions come in three layers:
   - **Stated links, for everything:** Supreme Court Database justices on all 36,842 cases, parties from the case names, Miller Center speakers, Avalon authors, and Wikidata authors and signatories.
   - **Confident automatic matches, for everything:** a full name or distinctive alias whose dates fit the document; uncertain matches are left out.
   - **Hand tagging, for the core set students read:** Claude tags every person, place, and event (with roles) in NARA's 93 Milestone Documents and the Constitution Test documents, about 0.5M tokens, done in a working session with no API bill.

   A paid model pass over the founding-era Avalon documents and the presidential speeches (about 10M tokens) was considered and declined.
4. **Diagrams:** draw Mermaid family trees, timelines, and connection paths like the Bible tools do.
5. **Fix the Bible graph too:** give it the history graph's name disambiguation and dated, sourced edges. Two small bugs to fix along the way:
   - `graph_enriched_search` looks family up again by name, so it can show the wrong Mary's family.
   - `lookup_name` reads the wrong column, so its "Key References" line never appears.

   Done 2026-10-20 (both bugs, plus a list of other matches with ids on every person answer).
6. **Event scope (decided 2026-10-21): broad.** Adam widened the events beyond wars, treaties, and councils to legislation, speeches, expeditions, notable disasters, inventions, discoveries, and achievements; eras yes; inventions from every era to the present; significant Olympics yes. Each category has its own fame bar (the fewest Wikipedia language editions it needs, worldwide and in the United States; anything located in Illinois needs one). Claude set the bars from a count of each category, since Adam was away:

   | Category | Classes (examples) | World | U.S. |
   |---|---|---|---|
   | Conflict | wars, battles, sieges, revolutions, massacres, assassinations, terrorist attacks, armistices | 5 | 2 |
   | Law and government | treaties, legislation, constitutions, charters, declarations, trials, scandals, conferences and summits | 5 | 2 |
   | U.S. law | Acts of Congress, amendments, executive orders, presidential proclamations, impeachments | 1 | 1 |
   | Court | every Supreme Court decision | always | |
   | Elections | elections and referendums (every U.S. presidential election) | 10 | 2 |
   | Speeches and texts | speeches, inaugural addresses, sermons, manifestos, open letters, proclamations, edicts, political slogans | 5 | 2 |
   | Exploration | expeditions, spaceflights, space probes, circumnavigations, first ascents | 5 | 2 |
   | Disasters | earthquakes, storms, floods, eruptions, fires, famines, epidemics, shipwrecks, air, rail, mining, industrial, and nuclear disasters | 10 | 3 |
   | Society | movements, strikes, protests, boycotts, riots, migrations, gold rushes, world's fairs, transfers of sovereignty | 5 | 2 |
   | Economy | financial and economic crises, recessions | 5 | 2 |
   | Eras | historical periods, eras, ages, cultural movements | 10 | 2 |
   | Church | ecumenical councils, synods, Great Awakenings, schisms, persecutions, revivals, Imperial Diets | 3 | 2 |
   | Olympics | every Summer and Winter Games | always | |
   | Inventions and discoveries | anything with an inventor or discoverer or a date of invention (not stars, species, genes, proteins, or people) | 10 | 5 |

   Classes were chosen from about 200 examples a Yorkville student would ask about, looked up to see how Wikidata classifies them; every class id was checked against its English label. Taking part in a conflict, a political event, an expedition, a reform movement, or a church council brings a person into the graph; an election, a disaster, an invention, an era, or the Olympics does not.
7. **Church history (checked 2026-10-21):** the Study Bible's tools hold the texts (42 creeds and confessions, 308 church fathers in the catena, the theology library) and no events: its graph (Theographic) ends with Acts. So the history graph carries church-history events and people and points to the Study Bible's tools for the texts (a council's confession through get_confession, writings through search_theology and get_church_fathers), copying none of them.
8. **Living roles, narrowed (2026-10-21) to match decision 1:** commanders (generals, admirals, flag officers, military commanders and leaders) and church leaders (bishops, cardinals, pastors, ministers, preachers, evangelists, religious leaders), with civil-rights and human-rights leaders, astronauts, and Nobel laureates. The first harvest had admitted every living military officer and theologian.
