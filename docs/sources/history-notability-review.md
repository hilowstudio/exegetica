# History graph notability: the two review lists

Measured 2026-10-26 against the local graph (325,286 people). Companion to `docs/sources/history-honors-research.md` (the honors research) and `docs/sources/history-graph-design.md` (the rules as built). Code: `scripts/socialsci/notability_review.py`.

## Summary

The graph admits most people by fame: the number of Wikipedia language editions with an article on them. Fame measures attention, so it lets in many athletes and entertainers and misses significant people who never drew much attention. This review compares fame with four signals of judgment:

- an entry in a curated reference work (40 of them, modern national biographies and the encyclopedias of the 19th century)
- a place on Wikipedia's Vital Articles lists
- a mention in the OpenStax U.S. History, World History, or American Government textbook
- a major honor (the reviewed list, plus the candidates from the honors research)

Two lists came out of it. The drop list has the 144,885 people who are in the graph on fame alone, with no office, signature, or event role; 100,229 of them have no strong signal. The add list has the 268,390 historical people outside the graph who hold at least one signal; most of them come from European national biographies, and 70,782 have no Wikipedia article in any language.

My recommendation is to tighten only where fame misleads most and to add only from the sources closest to the courses:

- Drop the fame-only people in sports, entertainment, and music who have no strong signal, keeping anyone born in Illinois: 37,474 people.
- Add the historical people in American National Biography and the Biographical Directory of Federal Judges, the Vital Articles people the graph misses, and the holders of a listed honor who have a Wikipedia article: 18,239 people.

The graph would go from 325,286 people to about 306,000, with fewer athletes and entertainers and more of the Americans a U.S. History course meets.

## The signals

| Signal | People with it | In the graph | Outside, historical |
|---|--:|--:|--:|
| Modern reference work (23, such as American National Biography, the Oxford DNB, Britannica) | 234,316 | 64,081 | 159,158 |
| 19th-century reference work (17, such as Appletons', the old DNB, Brockhaus and Efron) | 165,719 | 36,941 | 115,313 |
| Vital Articles (levels 4 and 5) | 14,149 | 11,092 | 238 |
| Textbook mention | 1,437 | 1,437 | none (matched to graph names only) |
| Honors, current and recommended | 63,790 | 18,015 | 23,140 |

A person can hold several signals, so the rows overlap.

## The drop list: fame alone

Of the 144,885 fame-only people, 44,656 have a strong signal (a modern reference entry, Vital Articles, a textbook mention, or an honor on the current or recommended list). Another 8,546 have only a 19th-century reference entry. The remaining 91,683 have no signal of any kind.

| Field | Fame-only | No strong signal | Share |
|---|--:|--:|--:|
| Sports | 21,215 | 18,965 | 89% |
| Entertainment | 14,383 | 12,658 | 88% |
| Science and medicine | 21,317 | 11,813 | 55% |
| Politics and government | 16,274 | 10,359 | 63% |
| Music | 10,287 | 7,937 | 77% |
| Visual arts and architecture | 10,697 | 6,914 | 64% |
| Scholarship and teaching | 10,702 | 6,441 | 60% |
| Literature | 8,581 | 5,247 | 61% |
| Religion | 8,630 | 4,758 | 55% |
| Royalty and nobility | 3,826 | 2,857 | 74% |
| Journalism and media | 3,848 | 2,492 | 64% |
| All other fields | 15,125 | 10,788 | 71% |

A person's field is the first match among their occupations, in an order that puts public life first, so an actor who became a governor counts under politics.

The most famous people with no strong signal show what a blanket rule would cost. In entertainment and music they include Val Kilmer, Michael Clarke Duncan, Robbie Coltrane, Sinéad O'Connor, and Chester Bennington; in sports, Diogo Jota and Raymond Kopa. In the other fields the list mixes people whose Wikipedia counts were inflated by language campaigns (a minor French artist with 100 editions) with real figures whose roles Wikidata never recorded: the Confederate general George H. Steuart, a South Carolina governor, and Chester Greenwood, who invented earmuffs. A signal requirement in those fields would drop real U.S. history along with the noise.

### The options

| Rule for fame-only people | Dropped |
|---|--:|
| A. A strong signal required of everyone | 100,229 |
| A2. As A, but a 19th-century reference also counts | 91,683 |
| B. A strong signal, or 20+ language editions | 87,818 |
| B2. As B, with anyone born in Illinois exempt | 83,601 |
| B3. As B2, with Americans needing only 10+ editions | 74,475 |
| C. A strong signal required only in sports, entertainment, and music | 39,560 |
| C2. As C, with anyone born in Illinois exempt (recommended) | 37,474 |
| D. B3 in sports, entertainment, and music; elsewhere, drop only people with no signal of any kind and under 10 editions | 42,350 |

C2 cuts where fame-only people are almost all noise for these courses and leaves the history-bearing fields alone until their missing roles can be fixed. D goes a little further for about 5,000 more people.

## The add list: signals outside the graph

Living people outside the graph (52,249 with a signal) stay out under the living-people rule, so these counts are historical people only.

| Source | Outside | Died 1400 or later | Americans | With a Wikipedia article |
|---|--:|--:|--:|--:|
| Oxford Dictionary of National Biography | 47,613 | 45,384 | 275 | 39,382 |
| Dizionario Biografico degli Italiani | 23,441 | 21,367 | 11 | 17,735 |
| Dictionary of National Biography (1885-1900) | 21,896 | 20,553 | 51 | 19,217 |
| Brockhaus and Efron | 21,287 | 19,901 | 31 | 19,948 |
| Diccionario Biográfico Español | 20,592 | 19,655 | 14 | 15,038 |
| Allgemeine Deutsche Biographie | 19,017 | 18,046 | 2 | 16,362 |
| Österreichisches Biographisches Lexikon | 18,335 | 18,335 | 43 | 12,367 |
| Polish Biographical Dictionary | 18,093 | 17,916 | 22 | 11,472 |
| Righteous Among the Nations | 14,329 | 14,329 | 7 | 1,740 |
| Australian Dictionary of Biography | 12,607 | 12,607 | 34 | 7,493 |
| Encyclopædia Britannica | 7,160 | 5,823 | 979 | 6,889 |
| American National Biography | 6,809 | 6,809 | 4,121 | 5,662 |
| Dictionary of Canadian Biography | 5,142 | 5,140 | 101 | 4,499 |
| Canonized saints | 4,810 | 1,800 | 2 | 4,624 |
| Appletons' Cyclopædia of American Biography | 3,088 | 3,085 | 1,265 | 2,163 |
| Biographical Directory of Federal Judges | 1,449 | 1,449 | 1,449 | 1,449 |
| American Philosophical Society | 816 | 816 | 493 | 678 |
| Medal of Honor | 535 | 535 | 253 | 522 |
| Vital Articles | 238 | 142 | 15 | 238 |

The full table, with every source and honor and example people, is in the stats output (`notability_review.py stats`).

American National Biography is the source that fits U.S. History best. The people it adds include Jacob Leisler of Leisler's Rebellion, Laura Keene (the actress on stage at Ford's Theatre), the colonial architect Peter Harrison, the Moravian bishop August Spangenberg, and the labor organizer Sara Estela Ramírez. The federal judges serve Government and Street Law. The big European biographies would add some 150,000 people, nearly all of them local figures a high-school course would never meet.

### The options

| Rule for bringing people in | Added |
|---|--:|
| American National Biography, federal judges, Vital Articles, and honors held by someone with a Wikipedia article (recommended) | 18,239 |
| The same without saints who died before 1400 | 15,344 |
| The recommended rule plus the Dictionary of Canadian Biography | 23,297 |
| Two or more sources of any kind, died 1400 or later | 46,721 |
| Any modern reference entry with a Wikipedia article, died 1400 or later | 117,672 |

In the recommended rule, honors bring in 10,103 people: canonized saints 4,624, Righteous Among the Nations 1,740 (of 14,329; the rest have no article), the American Philosophical Society 678, the Medal of Honor 522, the Order of the Garter 307, the Pulitzer Prize 200, the Académie française 172, and the Academy Awards 162. American National Biography and the federal judges bring in 8,230 and Vital Articles 238. Of the 18,239, 6,863 are Americans and 3,032 died before 1400 (mostly saints).

## Honors

The research (`docs/sources/history-honors-research.md`, `scripts/socialsci/curation/honors_candidates.csv`) found that the first honors harvest undercounted badly: people hold the sub-award, and the query fell back to the parent. With the corrected families the Nobel Prize has 899 laureates (it had none), the Academy Awards 2,523 (19), Olympic gold 4,494 (109), and the Wolf Prize 375 (2). The list now has the 59 current honors (your nine approvals included), 51 new candidates the research recommends, 80 to decide, and 75 it recommends leaving out.

On the drop list, the current honors confirm 5,959 fame-only people and are the only signal for 2,779 of them (Olympic gold 1,238, the Academy Awards 976, the Pulitzer Prize 413). The recommended additions confirm 4,334 more and are the only signal for 941 (the American Philosophical Society 1,340, canonized saints 939, Pour le Mérite 391, the Académie française 386, the Order of the Garter 289). The largest of the to-decide honors are the National Academy of Sciences (1,927 fame-only members, the only signal for 372) and the Fellows of the Royal Society (1,811, the only signal for 40).

Five recognitions have no usable Wikidata link and would need hand lists: the Hall of Fame for Great Americans, most of the Order of Lincoln, the National Native American Hall of Fame, the Chicago Literary Hall of Fame, and the U.S. Business Hall of Fame.

## Other findings

- Famous people can go missing because the query service's copy of Wikidata held vandalism: George Berkeley is typed there as a "mutant," and Lizzie Borden's name reads "ludmila." Yermak Timofeyevich (50 editions) is missing too, for a reason not yet traced. A check that every Vital Articles person is in the graph, with the live Wikidata service as the tiebreaker, would catch this class of error on every rebuild.
- Biblical people (Mary, John the Baptist, the apostles) are typed "human biblical figure" rather than "human," so the history graph leaves them to the Bible tools. That fits the design, which hands church history before Acts to the Bible graph, but it is a choice worth confirming.
- Most of the people Olympic gold (3,073 of 3,191) and the Academy Awards (676 of 1,428) would add are living, so the living-people rule keeps them out whatever the honors decision.
- Many politics and military figures are fame-only because Wikidata has no office or battle linked to them (state legislators, foreign officials, generals whose battles aren't linked). That is the reason to leave those fields alone in the drop rule for now.

## Decisions for you

1. The drop rule: C2 (recommended), D, B3, or A.
2. Whether a 19th-century reference entry counts as a confirming signal (it decides 8,546 fame-only people under rule A).
3. The add rule: the recommended one, with or without saints who died before 1400, and with or without the Dictionary of Canadian Biography.
4. The honors: approve the 51 recommended candidates, decide the 80 open ones (the research doc gives a reason for each), and say whether you want hand lists for the Hall of Fame for Great Americans and the Order of Lincoln.
5. The vandalism check: add it to the build.

## Files

- `.seed_cache/socialsci/review/fame_only.csv`: the 144,885 fame-only people, most famous first, with name, description, Wikipedia editions, field, occupations, dates, fame tier, and one column per signal (`refs_modern`, `refs_historic`, `vital`, `textbook`, `honors`, `honors_recommended`, `honors_to_decide`).
- `.seed_cache/socialsci/review/outside_with_signal.csv`: the 320,626 people outside the graph with a signal (living ones included and marked), with the same signal columns plus offices held.
- Both open in Excel. They live in the git-ignored cache because together they run to 74 MB; `notability_review.py lists` rebuilds them from the harvest.
