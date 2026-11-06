# Historical significance: honors research

Research, 2026-10-26. Counts from Wikidata through QLever. Companion to `scripts/socialsci/curation/honors_candidates.csv`, which holds every row below with its family of award items, the query for anything not found by award received (P166), and example recipients.

## Summary

The current list has 59 honors. This research adds 206 candidates in fifteen groups and recounts all 265. Of the new candidates, 51 are recommended in, 80 are left to decide, and 75 are recommended out.

The current list undercounts several awards because people hold the sub-award, and the harvester's path query timed out and fell back to the parent item. With the corrected families, the Nobel Prize goes from 0 people to 899, the Academy Awards from 19 to 2,523, the Wolf Prize from 2 to 375, the Kyoto Prize from 5 to 121, and Olympic gold from 109 to 4,494. The Baseball and Basketball halls of fame go from 42 to 355 and from 52 to 470 through their inductee IDs.

The strongest additions for the courses:

- Illinois: the Order of Lincoln (with a hand list) and Illinois county namesakes.
- U.S. History and Government: the National Statuary Hall Collection, the Hall of Fame for Great Americans (hand list), the Labor Hall of Honor, the Profile in Courage Award, the 1945 Medal of Freedom, and the history prizes (Bancroft, Parkman, Lincoln Prize).
- Church history: canonized saints (P411) and the Doctors of the Church.
- World History: the Garter, the Thistle, the Companions of Honour, Germany's Pour le Merite for Sciences and Arts, and the Academie francaise.
- Geography: the Royal Geographical Society medals and the Hubbard, Daly and Cullum medals.
- Science and engineering: the American Philosophical Society, the aviation honors, and the economics prize.

Five recognitions are not modeled in Wikidata and need hand lists if wanted: the Hall of Fame for Great Americans, most of the Order of Lincoln, the National Native American Hall of Fame, the Chicago Literary Hall of Fame and the U.S. Business Hall of Fame.

## How the counts were made

- Recipients are distinct people (instance of human, Q5) who hold any item in the award's family (P166), or who match the award's query when it is modeled another way.
- An award's family is every item that points at the award by subclass of (P279), instance of (P31) or part of (P361), walked two levels, kept when people hold it. Items that point at an award without being part of it were dropped (the Oscars' scientific and technical awards; a Spanish sports order filed as a subclass of the Legion of Honour's Grand Cross).
- Under 10 sitelinks counts recipients with fewer than 10 Wikimedia sitelinks, the measure the harvester's fame tiers use.
- New to graph counts recipients missing from the 325,286 people now in `social_sciences.db`. Anyone missing with 10 or more sitelinks is almost always living (kept out by the living rule) or died before 1400 (under the 20-sitelink bar). So when most of an award's new people are famous, the living rule decides them.
- About 145 requests went to Wikidata in all.

## U.S. civic honors

The four existing honors stay. Three additions reach people fame misses: the 1945-1961 Medal of Freedom (Danish and Norwegian resistance members, Allied civilians), the Profile in Courage Award (mayors, state officials, diplomats), and the Liberty Medal, which is small and confirms.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Presidential Medal of Freedom (existing) | Q17144 | 657 | 142 | 124 | in | The nation's highest civilian honor. |
| Congressional Gold Medal (existing) | Q721743 | 233 | 102 | 55 | in | Congress's highest honor; family adds two special medals. |
| Presidential Citizens Medal (existing) | Q1582967 | 93 | 43 | 24 | in | Presidential honor for service, often to people of modest fame. |
| Spingarn Medal (existing) | Q1994926 | 105 | 42 | 22 | in | NAACP's highest honor since 1915; Black Americans across a century. |
| Medal of Freedom (1945-1961) | Q1330790 | 181 | 141 | 73 | in | The predecessor of the Presidential Medal of Freedom; WWII civilians and Allied figures, most of them obscure now. |
| Liberty Medal | Q7182737 | 33 | 0 | 2 | in | National Constitution Center's award; statesmen and constitutional figures, small and on-topic for Government. |
| Profile in Courage Award | Q219070 | 64 | 26 | 29 | in | Officials who took a principled political risk; many state and local officials fame misses. |
| Ronald Reagan Freedom Award | Q1801104 | 12 | 0 | 0 | out | Twelve recipients, every one already famous. |
| Sylvanus Thayer Award | Q4311715 | 5 | 0 | 0 | out | West Point's award; only 5 recipients recorded in Wikidata. |
| Ellis Island Medal of Honor | Q5365910 | 125 | 36 | 64 | out | About 100 a year, mostly business and community leaders. |
| Distinguished Eagle Scout Award | Q5282987 | 198 | 116 | 88 | out | Recognizes the later careers of Eagle Scouts. |
| Silver Buffalo Award | Q7515877 | 13 | 5 | 4 | out | Boy Scouts service award; small and mostly famous. |
| National Teacher of the Year | Q6978846 | 1 | 1 | 1 | out | One recipient recorded in Wikidata. |

## Illinois and Chicago

Illinois has one statewide honor, the Order of Lincoln. Wikidata links only 26 of its several hundred laureates, so a hand list from the Lincoln Academy's roll would complete it. The 80 people Illinois counties are named after (the Earl of Effingham, John Edgar, Isaac White) are nearly all in the graph already. Chicago's halls of fame are local honors and thinly modeled.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Order of Lincoln | Q132166072 | 26 | 5 | 10 | in | Illinois's highest honor (Lincoln Academy laureates); Wikidata records only a fraction, so a hand list from the Academy's roll would complete it. |
| namesake of an Illinois county | Q1204 | 80 | 21 | 7 | in | Early Illinois figures (governors, judges, pioneers); 80 people, 73 already in the graph, so it mostly confirms. |
| Chicago Women's Hall of Fame | Q26709752 | 11 | 9 | 7 | decide | City honor; 11 recorded, mostly local civic figures. |
| Chicago Gay and Lesbian Hall of Fame | Q5095618 | 64 | 52 | 36 | out | City honor for service to Chicago's LGBT community; recipients are mostly local activists the courses do not cover. |
| Carl Sandburg Literary Award | Q28935563 | 33 | 5 | 21 | out | Library fundraising award to authors who are already famous. |
| Chicago Literary Hall of Fame | Q138845587 | 0 | 0 | 0 | decide | Wikidata links no inductees; a hand list of the few dozen would cover it. |
| Chicagoland Sports Hall of Fame | Q5095912 | 1 | 1 | 1 | out | One inductee recorded. |

## National halls of fame and commemorations

The National Statuary Hall Collection fits the courses best: each state chose two people, and the list reaches state founders and pioneers such as Mother Joseph Pariseau, Standing Bear and Jason Lee. Nearly all are in the graph already, so it mostly confirms. The Hall of Fame for Great Americans (1900, 102 honorees) has only 4 linked people and needs a hand list. County namesakes are a nationwide signal of 18th and 19th century standing, with 418 people not yet in the graph.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| National Statuary Hall Collection | Q1134223 | 115 | 12 | 6 | in | The two people each state chose for the Capitol; 115 people including replaced statues. Nearly all are already in the graph, so it mostly confirms. |
| Hall of Fame for Great Americans | Q1508557 | 4 | 0 | 0 | in | The original national hall of fame (1900, 102 honorees); Wikidata links only 4, so a hand list is needed. |
| National Women's Hall of Fame (existing) | Q1967852 | 278 | 52 | 46 | in | Women across American history, many of modest fame. |
| Labor Hall of Honor | Q17277947 | 53 | 26 | 9 | in | Department of Labor's roll of labor leaders and reformers; Economics and U.S. History. |
| Library of Congress Living Legend | Q6542686 | 104 | 8 | 35 | decide | Mostly living artists and writers who are already famous. |
| National Native American Hall of Fame | Q123474567 | 0 | 0 | 0 | decide | Wikidata links no inductees; a hand list of the few dozen (since 2018) would cover it. |
| National Mining Hall of Fame | Q6974351 | 1 | 1 | 1 | out | One inductee recorded. |
| National Cowgirl Museum and Hall of Fame | Q6971983 | 68 | 45 | 42 | out | Mostly rodeo and western entertainers. |
| Library Hall of Fame | Q6542501 | 129 | 120 | 93 | out | Professional honor for librarians. |
| namesake of a U.S. county | Q47168 | 1,186 | 735 | 418 | decide | A nationwide signal of 18th and 19th century standing (governors, soldiers, congressmen); large, and partly redundant with office holding. |

## Ranked lists

Of the ranked lists, only Time's appear in Wikidata as awards. The BBC's Great Britons, Discovery's Greatest American, the Greatest Canadian and Michael Hart's The 100 have items, but no people link to them. Time Person of the Year is small and every recipient is famous, so it confirms.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Time Person of the Year | Q207826 | 47 | 6 | 8 | in | Small, and every recipient is famous; it confirms. |
| Time 100 | Q604370 | 513 | 116 | 392 | out | Annual list since 2004, mostly living celebrities. |
| BBC 100 Women | Q16153104 | 1,176 | 547 | 1,050 | out | Annual list since 2013 of living women in current affairs. |
| Great Britons (BBC poll) | Q165177 | 1 | 0 | 0 | out | Not modeled: one person links to it. |
| The Greatest American (Discovery poll) | Q2301958 | 0 | 0 | 0 | out | Not modeled: no person links to it. |
| The 100 (Michael Hart) | Q852868 | 0 | 0 | 0 | out | Not modeled: the book's item lists no subjects; every entry is famous anyway. |
| The Greatest Canadian | Q1999819 | 1 | 0 | 0 | out | Not modeled: one person links to it. |

## Peace, human rights and humanitarian

Additions favor prizes with long, international rolls: the Gandhi Peace Prize, the UN human-rights prize, the Nansen Refugee Award (aid workers fame misses), the Charlemagne Prize (European statesmen) and the World Food Prize (agricultural scientists). The Lenin Peace Prize is flagged and left out. Righteous Among the Nations, already on the list, is the largest addition anywhere: see the problems section.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Ramon Magsaysay Award (existing) | Q777181 | 274 | 175 | 183 | in | Asia's leading public-service prize; many recipients fame misses. |
| Righteous Among the Nations (existing) | Q112197 | 28,574 | 28,367 | 28,218 | in | Rescuers of Jews in the Holocaust; 26,294 of the 28,218 it adds have no article in any language, so consider requiring at least one sitelink. |
| Four Freedoms Award (existing) | Q284381 | 188 | 40 | 48 | in | Roosevelt Institute's award; holders sit on the five sub-medals, which the family walk finds. |
| Sakharov Prize (existing) | Q48786 | 55 | 2 | 16 | in | European Parliament's human-rights prize. |
| Gandhi Peace Prize | Q1324269 | 11 | 2 | 3 | in | India's international peace prize; small (Mandela, Tutu, Nyerere, King's associates). |
| United Nations Prize in the Field of Human Rights | Q27028 | 55 | 20 | 21 | in | The UN's human-rights prize since 1968, given every five years. |
| Nansen Refugee Award | Q663005 | 76 | 49 | 49 | in | UNHCR's award for service to refugees; aid workers fame misses. |
| Charlemagne Prize | Q152337 | 65 | 0 | 6 | in | Statesmen of European unity since 1950 (Monnet, Schuman, Adenauer, Churchill). |
| World Food Prize | Q772112 | 55 | 40 | 38 | in | Agricultural scientists who fought hunger (Borlaug's prize); Economics and Geography. |
| Right Livelihood Award | Q152770 | 170 | 61 | 92 | decide | Activists in development and the environment; many unknown, but the award is advocacy-driven. |
| Princess of Asturias Awards | Q329157 | 375 | 64 | 191 | decide | Spain's leading prize in eight fields; mostly famous recipients. |
| Peace Prize of the German Book Trade | Q265920 | 78 | 2 | 15 | decide | Writers and thinkers since 1950 (Schweitzer, Buber, Havel). |
| Carnegie Medal of Philanthropy | Q18162079 | 6 | 3 | 2 | decide | Major philanthropists; 6 recorded, all famous. |
| Albert Schweitzer Prize for Humanitarianism | Q4711197 | 6 | 2 | 2 | decide | Small humanitarian prize; 6 recorded. |
| Lenin Peace Prize | Q308907 | 124 | 27 | 23 | out | Flagged: a Soviet political prize (the Stalin Peace Prize before 1956) given to Moscow-aligned figures; those who matter enter on other grounds. |
| Felix Houphouet-Boigny Peace Prize | Q1479435 | 24 | 2 | 3 | out | UNESCO prize; recipients are famous statesmen already in. |
| Indira Gandhi Peace Prize | Q3241794 | 25 | 2 | 3 | out | Recipients are mostly famous already. |
| Jawaharlal Nehru Award for International Understanding | Q3295156 | 44 | 5 | 5 | out | Recipients are mostly famous already. |
| Olof Palme Prize | Q1324648 | 48 | 15 | 23 | out | Small Swedish activist prize. |
| Robert F. Kennedy Human Rights Award | Q1527634 | 44 | 25 | 17 | out | Current activists; advocacy-driven. |
| Wateler Peace Prize | Q2521339 | 33 | 11 | 13 | out | Small Dutch prize. |
| Sydney Peace Prize | Q1975046 | 22 | 4 | 10 | out | Small Australian prize. |
| Eleanor Roosevelt Award for Human Rights | Q3312309 | 22 | 15 | 12 | out | Presidential award given only 1998-2000. |

## Religion and church history

Wikidata records sainthood as canonization status (P411), with many values for the same standing (saint, Catholic saint, canonized saint, hieromartyr). The saint family covers 7,102 people, 5,684 of them not yet in the graph; about 1,300 of those died after 1400, inside the World History window. The Doctors of the Church are modeled as an honorific prefix or a role; all 36 tagged are in the graph already. The Laetare Medal reaches American Catholics since 1883. Protestant calendars of commemoration are not modeled: the feast-day qualifiers in Wikidata cover the Roman and Orthodox calendars only, and no person links to the Lutheran Calendar of Saints item.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Templeton Prize (existing) | Q603631 | 56 | 10 | 16 | in | Religion's best-known prize. |
| canonized saint | Q43115 | 7,102 | 5,010 | 5,684 | in | Church history's own roll; of the 5,684 not yet in the graph about 1,300 died after 1400. Keep the graph's fame bar for earlier saints. |
| Doctor of the Church | Q192499 | 36 | 0 | 0 | in | All 36 tagged Doctors are already in the graph; it confirms. Irenaeus (named 2022) is not yet tagged. |
| beatified (Blessed) | Q2369287 | 2,489 | 1,881 | 1,904 | decide | One step below sainthood; many 20th-century martyrs fame misses, plus many minor local figures. |
| Laetare Medal | Q1800135 | 127 | 81 | 61 | in | Notre Dame's medal to American Catholics since 1883; many fame misses. |
| Gospel Music Hall of Fame | Q5587398 | 52 | 28 | 30 | decide | Church music history (Fanny Crosby, Thomas Dorsey, the Fisk Jubilee Singers' era). |
| Pacem in Terris Award | Q973645 | 45 | 19 | 16 | decide | Catholic peace award since 1964; mostly famous. |
| Grawemeyer Award for Religion | Q132643811 | 3 | 2 | 2 | decide | Theology book prize; 3 recorded. |
| Venerable or Servant of God | Q12774503 | 1,471 | 1,148 | 1,183 | out | Early stages of a cause for sainthood; too provisional to mark significance. |
| Order of St. Gregory the Great | Q946960 | 1,375 | 1,152 | 1,084 | out | Papal knighthood for lay service and benefaction; mostly donors. |
| Pro Ecclesia et Pontifice | Q976101 | 495 | 445 | 420 | out | Papal service medal; many minor figures. |
| Supreme Order of Christ | Q735298 | 61 | 21 | 21 | out | Papal order given to heads of state. |
| Order of the Golden Spur | Q93716 | 115 | 55 | 53 | out | Papal order given to heads of state. |
| GMA Dove Award | Q909430 | 57 | 40 | 56 | out | Contemporary Christian music industry awards. |
| Christopher Award | Q4377086 | 31 | 10 | 18 | out | Catholic media award for books and films. |
| Cross of St Augustine | Q5188481 | 1 | 1 | 0 | out | One recipient recorded. |
| Lutheran Calendar of Saints | Q905917 | 0 | 0 | 0 | out | Not modeled: no person links to it, and Wikidata's feast-day qualifiers cover the Roman and Orthodox calendars only. |

## Military valor

The George Cross, Britain's highest civilian gallantry award, joins the Medal of Honor and Victoria Cross. Second-tier valor awards (Distinguished Service Cross, Navy Cross, U.S. Air Force Cross) are left to decide: their recipients with articles are mostly WWI and WWII officers. Hero of the Soviet Union and the Knight's Cross of the Iron Cross are flagged and left out. The Pour le Merite item also carries some civil-class holders.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Medal of Honor (existing) | Q203535 | 3,203 | 3,129 | 553 | in | The highest U.S. award for valor; nearly all recipients are people fame misses. |
| Victoria Cross (existing) | Q219578 | 1,356 | 1,323 | 51 | in | The highest British and Commonwealth award for valor. |
| George Cross | Q1143510 | 146 | 143 | 44 | in | Britain's highest civilian gallantry award, equal in rank to the Victoria Cross. |
| Distinguished Service Cross (U.S. Army) | Q833376 | 258 | 216 | 43 | decide | Second-tier valor; recipients with articles are mostly WWI and WWII officers. |
| Navy Cross | Q833465 | 571 | 517 | 62 | decide | Second-tier valor (Navy and Marine Corps). |
| Air Force Cross (U.S.) | Q407132 | 12 | 10 | 2 | decide | Second-tier valor (Air Force); 12 recorded. |
| Param Vir Chakra | Q1650629 | 21 | 0 | 1 | decide | India's highest valor award; 21 recipients. |
| Companion of the Liberation | Q2990283 | 1,056 | 999 | 344 | decide | The Free French resistance order of WWII; about 1,000 people, most of them obscure. |
| Pour le Merite (military class) | Q156478 | 1,160 | 801 | 487 | decide | Prussia's highest order to 1918 (imperial era); WWI aces and generals. The item also carries some civil-class holders. |
| Hero of the Soviet Union | Q178473 | 12,751 | 12,255 | 6,621 | out | Flagged: Soviet title for WWII heroism and for political leaders; very large and Eastern Front commanders enter through their commands. |
| Knight's Cross of the Iron Cross | Q165558 | 3,542 | 2,932 | 366 | out | Flagged: Nazi Germany's decoration; commanders who matter enter through their commands. |
| Distinguished Service Medal (U.S. Army) | Q1774648 | 678 | 525 | 94 | out | Rewards senior command service; overlaps the commanders already admitted. |
| Silver Star | Q852071 | 1,467 | 1,290 | 216 | out | Third-tier valor; very large. |
| Distinguished Service Order | Q615838 | 3,015 | 2,752 | 770 | out | British officers' award; very large. |
| Distinguished Service Cross (British) | Q1229529 | 222 | 210 | 90 | out | British naval officers' gallantry award; large. |
| Air Force Cross (British) | Q2427600 | 403 | 384 | 109 | out | A non-combat flying award. |

## National orders (top grades)

Wikidata records each grade of an order as its own item, so top grades can be counted alone (Companion of the Order of Canada, Grand Cross of the Legion of Honour). The British orders with small, merit-based rolls are recommended: Garter, Thistle, Companions of Honour, with the Order of Merit already in. Germany's Pour le Merite for Sciences and Arts reaches scholars and artists since 1842. The old monarchies' senior orders (Golden Fleece, Holy Spirit, Black Eagle, St. Andrew) mark the courtiers and soldiers of early modern Europe and are left to decide. Orders given mainly to heads of state are left out.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Bharat Ratna (existing) | Q322132 | 49 | 0 | 4 | in | India's highest civilian award. |
| Order of Merit (existing) | Q94056 | 169 | 16 | 23 | in | The British monarch's personal order for achievement, limited to 24 living members. |
| Order of the Garter | Q215248 | 1,008 | 374 | 339 | in | England's senior order since 1348; Tudor and Stuart statesmen and soldiers. |
| Order of the Thistle | Q721030 | 152 | 84 | 67 | in | Scotland's senior order; small. |
| Order of the Companions of Honour | Q1137694 | 210 | 43 | 58 | in | Britain's order for achievement in arts, science and public life; capped at 65. |
| Pour le Merite for Sciences and Arts | Q15056034 | 663 | 99 | 110 | in | Germany's order for scholars and artists since 1842 (Humboldt, Gauss, Liszt). |
| Order of the Golden Fleece | Q465774 | 1,331 | 585 | 523 | decide | Habsburg and Spanish order since 1430; kings and grandees of early modern Europe. |
| Knight of the Order of the Holy Spirit | Q11599352 | 497 | 288 | 200 | decide | France's senior order under the monarchy (1578-1830). |
| Order of the Black Eagle | Q94145 | 826 | 317 | 216 | decide | Prussia's senior order (1701-1918). |
| Order of St. Andrew | Q1126563 | 1,036 | 339 | 226 | decide | Imperial Russia's senior order. |
| Companion of the Order of Canada | Q15278107 | 533 | 354 | 371 | decide | Top grade only; Canada's leading people since 1967. |
| Companion of the Order of Australia | Q9680541 | 590 | 471 | 487 | decide | Top grade only (the Knight grade is a separate item). |
| Order of Culture | Q530124 | 434 | 275 | 283 | decide | Japan's honor for culture and science. |
| Padma Vibhushan | Q672392 | 347 | 100 | 137 | decide | India's second civilian award. |
| Grand Cross of the Legion of Honour | Q10855226 | 1,644 | 721 | 363 | decide | Top grade only; heavily diplomatic (foreign heads of state and ministers). |
| Order of the Elephant | Q976544 | 692 | 184 | 196 | out | Denmark's order, mostly royals and heads of state. |
| Royal Order of the Seraphim | Q1331130 | 670 | 259 | 211 | out | Sweden's order, mostly royals and heads of state. |
| Grand Cordon of the Supreme Order of the Chrysanthemum | Q5361043 | 160 | 14 | 15 | out | Given to heads of state. |
| Knight Grand Cross of the Order of the Bath | Q12177451 | 1,081 | 687 | 196 | out | Senior officers and officials, for rank held. |
| Grand Cross Special Class, Order of Merit of Germany | Q10904959 | 174 | 6 | 14 | out | Given to heads of state. |
| Order of Lenin | Q185493 | 35,514 | 33,678 | 25,524 | out | Flagged: Soviet decoration given to tens of thousands of officials, workers and soldiers. |

## Letters, history and journalism

The history prizes reach the historians students read: the Bancroft and Parkman Prizes, the Lincoln Prize, and the NEH's Jefferson Lecture. The poets laureate are small rolls; the British one is modeled as a position held (P39) and runs from Dryden through Laurence Eusden to today. The Academie francaise (749 members since 1635, modeled as membership) reaches French clergy, writers and statesmen fame misses.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Pulitzer Prize (existing) | Q46525 | 1,406 | 895 | 897 | in | America's leading prize in journalism, letters and music. |
| Newbery Medal (existing) | Q622813 | 93 | 62 | 56 | in | Children's books students read. |
| Caldecott Medal (existing) | Q1026417 | 79 | 61 | 50 | in | Children's illustrators. |
| National Book Award (existing) | Q572316 | 381 | 148 | 161 | in | America's leading book award. |
| National Humanities Medal (existing) | Q1571938 | 234 | 117 | 143 | in | The national humanities honor. |
| Bancroft Prize | Q724144 | 179 | 147 | 122 | in | The leading prize for books on American history; the historians students cite. |
| Francis Parkman Prize | Q5482142 | 64 | 51 | 46 | in | Society of American Historians' prize for American history. |
| Lincoln Prize | Q6550969 | 35 | 29 | 30 | in | Civil War and Lincoln scholarship; Illinois tie. |
| Jefferson Lecture | Q6175526 | 44 | 7 | 12 | in | The federal government's highest honor in the humanities. |
| United States Poet Laureate | Q981258 | 22 | 3 | 2 | in | The national poet (Consultant in Poetry before 1986). |
| Poet Laureate of the United Kingdom | Q877838 | 28 | 3 | 6 | in | Every laureate since Dryden; a small roll through four centuries. |
| Academie francaise | Q161806 | 749 | 200 | 209 | in | The forty "immortals" since 1635; French writers, statesmen and clergy fame misses. |
| Wolfson History Prize | Q4020686 | 80 | 43 | 62 | decide | Britain's leading history book prize. |
| Booker Prize | Q160082 | 57 | 0 | 32 | decide | Leading English-language novel prize; modern novelists. |
| Prix Goncourt | Q187300 | 262 | 99 | 159 | decide | France's leading novel prize since 1903. |
| Miguel de Cervantes Prize | Q81466 | 51 | 1 | 9 | decide | The Spanish-language world's leading literary honor. |
| Bollingen Prize | Q194944 | 52 | 10 | 9 | decide | American poetry prize. |
| Hans Christian Andersen Award | Q327154 | 101 | 41 | 60 | decide | International children's literature honor. |
| Children's Literature Legacy Award | Q354323 | 29 | 16 | 13 | decide | The former Laura Ingalls Wilder Medal; lifetime awards to children's authors. |
| Coretta Scott King Award | Q5170318 | 40 | 28 | 27 | decide | Black authors and illustrators of children's books. |
| Elijah Parish Lovejoy Award | Q5360983 | 77 | 57 | 48 | decide | Colby College's award for courage in journalism; named for the editor killed at Alton, Illinois, in 1837. |
| MacArthur Fellows Program | Q1543268 | 1,156 | 780 | 976 | decide | Broad and mostly living; it marks standing in a field. |
| Neustadt International Prize for Literature | Q580574 | 28 | 0 | 8 | out | Small; overlaps the Nobel. |
| Camoes Prize | Q752134 | 37 | 3 | 15 | out | Portuguese-language literature; outside the courses. |
| Georg Buchner Prize | Q2640154 | 80 | 6 | 27 | out | German-language literature; outside the courses. |
| Jerusalem Prize | Q277787 | 49 | 18 | 23 | out | Small; mostly famous. |
| Robert Frost Medal | Q955178 | 57 | 19 | 15 | out | Poetry society award; overlaps the laureates. |
| Carnegie Medal (children's book) | Q1043985 | 78 | 36 | 57 | out | British children's book award. |
| George Polk Award | Q845188 | 927 | 819 | 821 | out | Large and mostly working journalists. |
| Peabody Awards | Q838121 | 291 | 174 | 178 | out | Given mostly to programs. |
| Maria Moors Cabot Prizes | Q2113 | 321 | 290 | 281 | out | Working journalists. |
| Guggenheim Fellowship | Q1316544 | 19,790 | 17,484 | 16,757 | out | A research grant to 20,000 people. |

## Arts, music and film

The architecture medals (AIA Gold Medal, RIBA Royal Gold Medal) reach 19th and early 20th century architects. NEA Jazz Masters is an American story with many people fame misses. Most music and film honors are left to decide, since their recipients are famous already.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| National Medal of Arts (existing) | Q1789030 | 296 | 57 | 89 | in | The national arts honor. |
| Kennedy Center Honors (existing) | Q1738793 | 231 | 6 | 80 | in | Lifetime honors in the performing arts. |
| Academy Awards (existing) | Q19020 | 2,523 | 994 | 1,428 | in | Approved; the family counts the competitive and honorary Oscars and leaves out the scientific and technical awards. |
| Grammy Lifetime Achievement Award (existing) | Q935843 | 170 | 2 | 20 | in | Approved; lifetime honor in recorded music. |
| Rock and Roll Hall of Fame (existing) | Q179191 | 262 | 21 | 91 | in | Approved; the inductee ID (P3162) finds people the award statement misses. |
| Pritzker Architecture Prize (existing) | Q133160 | 55 | 2 | 33 | in | Architecture's leading prize. |
| AIA Gold Medal | Q3317387 | 42 | 7 | 7 | in | American Institute of Architects' highest honor since 1907 (Jefferson posthumously, Wright, Sullivan). |
| Royal Gold Medal | Q920783 | 177 | 67 | 83 | in | RIBA's architecture medal since 1848; 19th-century architects fame misses. |
| NEA Jazz Masters | Q488296 | 171 | 11 | 43 | in | Jazz is an American story; many masters fame misses. |
| Praemium Imperiale | Q268670 | 165 | 5 | 75 | decide | Japan's international arts prize since 1989; mostly famous. |
| Polar Music Prize | Q754841 | 37 | 0 | 23 | decide | Small; mostly famous. |
| Gershwin Prize | Q2422622 | 16 | 1 | 12 | decide | Library of Congress song prize; all famous. |
| Songwriters Hall of Fame | Q861660 | 468 | 125 | 149 | decide | American songwriting from Tin Pan Alley on; the inductee ID (P4757) finds the people. |
| Country Music Hall of Fame | Q680685 | 12 | 4 | 4 | decide | Poorly modeled: 13 recorded of about 150 inductees. |
| Blues Hall of Fame | Q258100 | 13 | 2 | 2 | decide | Poorly modeled: 13 recorded. |
| Royal Philharmonic Society Gold Medal | Q26183322 | 99 | 9 | 19 | decide | Classical music since 1871 (Brahms, Elgar). |
| AFI Life Achievement Award | Q292044 | 45 | 0 | 19 | decide | Film careers; all famous. |
| Grammy Trustees Award | Q5593916 | 95 | 19 | 14 | decide | Producers and industry figures. |
| Tony Awards | Q191874 | 891 | 341 | 530 | out | Broadway competitive awards; theater professionals. |
| Emmy Award | Q123737 | 2,575 | 1,226 | 1,959 | out | Television competitive awards; very large. |
| star on Hollywood Walk of Fame | Q17985761 | 2,318 | 224 | 586 | out | A paid sponsorship of the entertainment industry. |

## Science and scholarship

The new science honors with the longest rolls are the Royal Astronomical Society's gold medal (since 1824) and the Royal Society of Arts' Albert Medal (since 1864). The American Philosophical Society (Franklin's, 1743; 2,913 members, 998 not in the graph) covers American scholars and statesmen since the founding. Election to the Royal Society (6,841 people) or the National Academy of Sciences (6,266) is a scholarly signal, but large; both are left to decide.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Nobel Prize (existing) | Q7191 | 899 | 1 | 1 | in | Holders sit on the five prizes (Physics, Chemistry, Medicine, Literature, Peace), which are subclasses (P279). |
| Lasker Award (existing) | Q921415 | 413 | 194 | 162 | in | Holders sit on the four Lasker awards (P361). |
| Albert Lasker Award for Basic Medical Research (existing) | Q999734 | 174 | 49 | 47 | in | Already in the Lasker family; a duplicate row. |
| Copley Medal (existing) | Q28003 | 280 | 1 | 8 | in | The Royal Society's oldest medal (1731). |
| Fields Medal (existing) | Q28835 | 68 | 0 | 46 | in | Mathematics. |
| Abel Prize (existing) | Q188184 | 29 | 0 | 22 | in | Mathematics. |
| Turing Award (existing) | Q185667 | 79 | 0 | 41 | in | Computing. |
| Wolf Prize (existing) | Q739936 | 375 | 70 | 182 | in | Holders sit on the six field prizes (and Architecture under Arts). |
| National Medal of Science (existing) | Q737051 | 548 | 125 | 135 | in | The national science honor. |
| Kyoto Prize (existing) | Q658444 | 121 | 19 | 52 | in | Holders sit on the three field prizes. |
| Crafoord Prize (existing) | Q583069 | 78 | 13 | 34 | in | Holders sit mostly on the four field prizes. |
| Japan Prize (existing) | Q908745 | 105 | 44 | 61 | in | Holders sit on the prize itself; no family. |
| Royal Medal (existing) | Q746756 | 440 | 119 | 136 | in | Royal Society. |
| Max Planck Medal (existing) | Q317038 | 86 | 21 | 31 | in | Physics. |
| Priestley Medal (existing) | Q826100 | 85 | 31 | 22 | in | Chemistry. |
| Canada Gairdner International Award (existing) | Q1031994 | 370 | 162 | 184 | in | Medicine. |
| Shaw Prize (existing) | Q584250 | 107 | 22 | 74 | in | Holders sit on the prize and its three field prizes. |
| Kavli Prize (existing) | Q1094530 | 80 | 32 | 58 | in | Holders sit on the three field prizes. |
| Lomonosov Gold Medal (existing) | Q1340199 | 116 | 38 | 39 | in | Russian Academy of Sciences. |
| Darwin Medal (existing) | Q756994 | 67 | 19 | 20 | in | Royal Society. |
| Rumford Medal (existing) | Q285167 | 106 | 26 | 26 | in | Royal Society. |
| Davy Medal (existing) | Q220842 | 155 | 58 | 59 | in | Royal Society. |
| Faraday Medal (existing) | Q1396110 | 84 | 44 | 49 | in | The Institution of Engineering and Technology's medal (electrical engineering). |
| Benjamin Franklin Medal (existing) | Q817496 | 169 | 56 | 88 | in | Franklin Institute; family adds the field medals. |
| Elliott Cresson Medal (existing) | Q1332315 | 205 | 84 | 48 | in | Franklin Institute, 1875-1998; 19th-century inventors fame misses. |
| Holberg Prize | Q1624297 | 21 | 1 | 14 | in | The humanities' leading international prize. |
| Kluge Prize | Q1776592 | 11 | 1 | 5 | in | Library of Congress prize for the humanities and social sciences. |
| Enrico Fermi Award | Q931545 | 73 | 24 | 17 | in | U.S. government's science and energy award since 1956 (Oppenheimer, von Neumann). |
| Gold Medal of the Royal Astronomical Society | Q753072 | 251 | 58 | 66 | in | Astronomy since 1824 (Herschel, Hubble). |
| American Philosophical Society | Q466089 | 2,913 | 1,494 | 998 | in | Franklin's society (1743); its members include the founders and two centuries of American scholars. |
| Albert Medal (Royal Society of Arts) | Q4710826 | 159 | 42 | 48 | in | Since 1864 (Rowland Hill, Faraday, Pasteur, Edison, Bell). |
| Balzan Prize | Q628457 | 176 | 58 | 91 | decide | Broad scholarly prize (history, law, the sciences); mostly specialists. |
| Breakthrough Prize | Q17278140 | 180 | 82 | 148 | decide | Recent (2012 on) science prizes; mostly living specialists. |
| Bruce Medal | Q330957 | 115 | 7 | 14 | decide | Astronomy since 1898. |
| Fellow of the Royal Society | Q15631401 | 6,841 | 4,272 | 4,332 | decide | Election to Britain's academy since 1660; large but a real scholarly signal. |
| National Academy of Sciences | Q270794 | 6,266 | 3,861 | 3,633 | decide | Election to the U.S. academy since 1863; large. |
| Hughes Medal | Q844872 | 109 | 27 | 30 | decide | Royal Society physics medal. |
| Sylvester Medal | Q899402 | 42 | 1 | 12 | decide | Royal Society mathematics medal. |
| Wollaston Medal | Q832424 | 195 | 65 | 64 | decide | Geology since 1831 (Agassiz, Lyell). |
| Linnean Medal | Q1635542 | 208 | 106 | 110 | decide | Natural history since 1888. |
| NAS Public Welfare Medal | Q4811818 | 85 | 33 | 23 | decide | Science in public service. |
| Fellow of the American Academy of Arts and Sciences | Q52382875 | 3,551 | 2,134 | 2,158 | out | Very large and mostly living academics. |
| Perkin Medal | Q1385301 | 107 | 73 | 57 | out | Industrial chemistry. |
| Matteucci Medal | Q1419938 | 73 | 6 | 10 | out | Overlaps the Nobel physicists. |
| Robert Koch Prize | Q505132 | 102 | 72 | 80 | out | Specialist medical prize. |
| Louisa Gross Horwitz Prize | Q899039 | 111 | 26 | 35 | out | Specialist; overlaps the Nobel. |
| Albert Einstein Medal | Q17712 | 37 | 3 | 9 | out | Small; overlaps the Nobel. |

## Invention, engineering, aviation and space

The aviation honors are the gap in the current list: the National Aviation Hall of Fame, the Langley Gold Medal, the Daniel Guggenheim Medal and the Collier Trophy. The John Fritz Medal covers engineering since 1902. The astronaut honors confirm (every recipient is already in).

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| National Inventors Hall of Fame (existing) | Q1366018 | 608 | 254 | 196 | in | Inventors. |
| National Medal of Technology and Innovation (existing) | Q937629 | 215 | 123 | 110 | in | The national technology honor. |
| IEEE Medal of Honor (existing) | Q678414 | 104 | 32 | 29 | in | Electrical engineering. |
| Charles Stark Draper Prize (existing) | Q1063447 | 64 | 22 | 33 | in | Engineering. |
| Millennium Technology Prize (existing) | Q1853663 | 11 | 1 | 8 | in | Technology. |
| National Aviation Hall of Fame | Q488005 | 258 | 109 | 36 | in | Aviation and space pioneers (Wrights, Earhart, Doolittle). |
| United States Astronaut Hall of Fame | Q742943 | 92 | 0 | 0 | in | Astronauts. |
| Congressional Space Medal of Honor | Q1126046 | 30 | 0 | 0 | in | Small; astronauts and the Challenger and Columbia crews. |
| John Fritz Medal | Q6234290 | 109 | 65 | 50 | in | Engineering since 1902 (Kelvin, Westinghouse, Edison, Bell). |
| Daniel Guggenheim Medal | Q3332195 | 93 | 51 | 36 | in | Aeronautics since 1929 (Orville Wright, Boeing, Douglas). |
| Langley Gold Medal | Q6486246 | 22 | 6 | 1 | in | Smithsonian's aviation medal since 1909 (the Wrights, Lindbergh). |
| Collier Trophy | Q1109489 | 15 | 6 | 5 | in | America's aviation achievement award since 1911. |
| Edison Medal | Q678263 | 113 | 61 | 35 | decide | IEEE's electrical engineering medal since 1909. |
| Hoover Medal | Q17132005 | 52 | 26 | 19 | decide | Engineers in public service. |
| Harmon Trophy | Q5659178 | 77 | 27 | 14 | decide | Aviators since 1926. |
| International Space Hall of Fame | Q99951011 | 136 | 21 | 14 | decide | New Mexico museum's hall; space pioneers worldwide. |
| Internet Hall of Fame | Q6055547 | 130 | 85 | 111 | decide | Internet pioneers; recent and mostly living. |

## Geography and exploration

Nothing on the current list covers exploration. The Royal Geographical Society's two gold medals (Founder's and Patron's, since 1832), the National Geographic Society's Hubbard Medal and the American Geographical Society's Daly and Cullum medals reach explorers and surveyors fame misses.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Founder's Medal (Royal Geographical Society) | Q26268774 | 189 | 82 | 68 | in | The RGS gold medal since 1832; explorers and surveyors fame misses. |
| Patron's Medal (Royal Geographical Society) | Q26837312 | 186 | 82 | 78 | in | The RGS's second gold medal; same standing. |
| Hubbard Medal | Q4287207 | 43 | 5 | 8 | in | National Geographic Society's exploration medal since 1906 (Peary, Amundsen, Byrd). |
| Charles P. Daly Medal | Q2654823 | 50 | 20 | 11 | in | American Geographical Society's medal since 1902. |
| Cullum Geographical Medal | Q402425 | 68 | 28 | 19 | in | American Geographical Society's exploration medal since 1896. |
| Vega Medal | Q3332237 | 75 | 25 | 25 | decide | Swedish geography medal since 1881. |
| Livingstone Medal | Q10568200 | 43 | 1 | 8 | decide | Royal Scottish Geographical Society. |
| David Livingstone Centenary Medal | Q3650805 | 27 | 10 | 8 | decide | American Geographical Society; Antarctic explorers. |
| Polar Medal | Q1093361 | 143 | 102 | 68 | decide | British medal to members of polar expeditions; large and uneven. |

## Economics and business

The economics prize needs its own row: Wikidata does not class it under the Nobel Prize, so the Nobel family leaves its 101 laureates out. Business halls of fame are thinly modeled.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Nobel Memorial Prize in Economic Sciences | Q47170 | 101 | 0 | 48 | in | Wikidata does not class it under the Nobel Prize, so it needs its own row. |
| John Bates Clark Medal | Q839677 | 47 | 17 | 31 | decide | Economists under 40; overlaps the economics Nobel. |
| Horatio Alger Award | Q28950956 | 140 | 57 | 58 | decide | Self-made business and civic leaders; Economics. |
| U.S. Business Hall of Fame | Q7863100 | 1 | 1 | 0 | decide | Not modeled in Wikidata (one inductee linked); a hand list is needed. |
| Automotive Hall of Fame | Q787908 | 10 | 1 | 2 | out | Poorly modeled (10 recorded). |

## Sports

Four of the approved awards needed a different query: Olympic champions are recorded mostly as a qualifier on "participant in" statements, and the Baseball and Basketball halls are complete only through their inductee-ID properties (P4164, P3646). Other major halls with the same standing are left to decide. Annual athlete awards go to famous people. World Cup winners could not be resolved.

| Award | QID | Recipients | Under 10 sitelinks | New to graph | Recommend | Reason |
|---|---|--:|--:|--:|---|---|
| Olympic gold medal (existing) | Q15243387 | 4,494 | 129 | 3,191 | in | Approved; champions are recorded mostly as a qualifier on "participant in" statements, which the query reads. |
| National Baseball Hall of Fame and Museum (existing) | Q809892 | 355 | 119 | 98 | in | Approved; the inductee ID (P4164) finds the members. |
| Pro Football Hall of Fame (existing) | Q778412 | 336 | 187 | 146 | in | Approved; the inductee IDs (P6930, P3581) complete it. |
| Naismith Memorial Basketball Hall of Fame (existing) | Q290922 | 470 | 184 | 250 | in | Approved; the inductee ID (P3646) finds the members. |
| Hockey Hall of Fame | Q1136687 | 402 | 183 | 243 | decide | The same standing as the approved halls. |
| International Tennis Hall of Fame | Q52454 | 268 | 27 | 94 | decide | The same standing as the approved halls. |
| World Golf Hall of Fame | Q258851 | 174 | 90 | 106 | decide | The same standing as the approved halls. |
| International Boxing Hall of Fame | Q572227 | 545 | 327 | 301 | decide | The same standing as the approved halls; includes 19th-century bare-knuckle fighters. |
| International Swimming Hall of Fame | Q744713 | 272 | 32 | 140 | decide | Swimmers and divers; overlaps Olympic gold. |
| College Football Hall of Fame | Q747833 | 32 | 24 | 24 | decide | Poorly modeled: 32 recorded of about 1,000 inductees. |
| Ballon d'Or | Q166177 | 47 | 0 | 30 | decide | World football's top individual award; all famous. |
| Sports Illustrated Sportsperson of the Year | Q1653207 | 27 | 2 | 22 | decide | Small; all famous. |
| Associated Press Athlete of the Year | Q743122 | 135 | 15 | 79 | decide | All famous. |
| Heisman Trophy | Q1035067 | 30 | 11 | 23 | decide | College football's top award. |
| International Women's Sports Hall of Fame | Q28227923 | 6 | 4 | 3 | out | Poorly modeled (6 recorded). |
| National Track and Field Hall of Fame | Q1087567 | 6 | 2 | 3 | out | Poorly modeled (6 recorded); Olympic gold covers most. |
| U.S. Olympic & Paralympic Hall of Fame | Q7890852 | 3 | 0 | 3 | out | Poorly modeled (3 recorded); Olympic gold covers it. |
| National Soccer Hall of Fame | Q1134590 | 1 | 0 | 1 | out | Poorly modeled (1 recorded). |
| James E. Sullivan Award | Q2720648 | 18 | 1 | 14 | out | Amateur athletes; small. |
| FIFA World Cup winner | Q19317 | 0 | 0 | 0 | out | Unresolved: player wins aren't modeled in a way a query could read in time; winners are mostly famous. |

## Modeling notes

The `query` column in the CSV holds a complete SELECT returning `?p ?s` for every honor not found by P166 alone. When it is filled it replaces the P166 lookup, and `family_qids` lists the items the query reads.

- Olympic champions: 4,442 carry gold as a qualifier on a "participant in" (P1344) statement for the event, and 25 on a "victory" (P2522) statement; only 109 hold the medal through P166. The query unites the three.
- Six halls of fame have inductee IDs: Baseball (P4164), Pro Football (P6930 and the older P3581), Basketball (P3646), Rock and Roll (P3162), Songwriters (P4757) and Tennis (P3363). Each query unites the ID with the P166 statement. The Rock and Roll ID also covers groups, and members of inducted bands are not recorded one by one.
- Saints, the beatified, and causes in progress are recorded as canonization status (P411). The saint family is 19 status values (saint, Catholic saint, canonized saint, pre-congregation saint, Orthodox and Anglican saint, and the Orthodox ranks such as hieromartyr and equal-to-apostles).
- Doctors of the Church carry an honorific prefix (P511) or a role (subject has role, P2868). The occupation branch (P106) added only an error, and one stray P511 is filtered out.
- The National Statuary Hall Collection is read through its statues: items in the collection (P195) that depict (P180) the person. The 115 people include statues since replaced.
- The academies use member of (P463): the Academie francaise, the National Academy of Sciences and the American Philosophical Society. Fellowship of the Royal Society is recorded both ways; the P166 family (Fellow, Foreign Member, Royal Fellow) is used.
- The British poet laureate is a position held (P39); the American one is held as P166 or P39.
- County namesakes are people a county of the United States (P31/P279 of Q47168) named after (P138) the person, limited to Illinois (located in, P131, Q1204) for the Illinois row. The `qid` column holds Q47168 and Q1204 for these two rows, since there is no award item.
- Not modeled at all: the Hall of Fame for Great Americans, the National Native American Hall of Fame, the Chicago Literary Hall of Fame, the U.S. Business Hall of Fame, Protestant calendars of commemoration, and the ranked lists other than Time's. World Cup winners appear only as team results and on player statements the query service could not group in time. People on U.S. currency, stamps and federal holidays have no recognition item; they are a few dozen famous people and were not pursued.

## Problems found in the current list

| Award | People found before | People with the corrected family or query |
|---|--:|--:|
| Nobel Prize | 0 | 899 |
| Academy Awards | 19 | 2,523 |
| Wolf Prize | 2 | 375 |
| Kyoto Prize | 5 | 121 |
| Kavli Prize | 8 | 80 |
| Shaw Prize | 36 | 107 |
| Crafoord Prize | 23 | 78 |
| Olympic gold medal | 109 | 4,494 |
| National Baseball Hall of Fame | 42 | 355 |
| Naismith Basketball Hall of Fame | 52 | 470 |
| Pro Football Hall of Fame | 314 | 336 |
| Rock and Roll Hall of Fame | 257 | 262 |
| Lasker Award | 413 | 413 |
| Japan Prize | 105 | 105 |

- The harvester's honors stage walks `(P279|P31|P361)*` from each award and falls back to the award item when the walk times out. For the first eight rows the walk failed and the fallback found only people who hold the parent item. The CSV's `family_qids` replaces the walk with an explicit list.
- The Lasker Award and the Japan Prize were counted correctly. The Japan Prize has no sub-awards, and the Lasker walk succeeded.
- The economics prize is outside the Nobel family and needs its own row (added here).
- The Albert Lasker Award for Basic Medical Research duplicates a member of the Lasker family. It is harmless but can be dropped.
- Righteous Among the Nations would add 28,218 people to the graph, and 26,294 of them have no article in any language. Requiring at least one sitelink would add about 1,900.
- Olympic gold and the Academy Awards are approved, but most of the people they would add are living. 3,073 of Olympic gold's 3,191 additions and 676 of the Academy Awards' 1,428 have 10 or more sitelinks, so the living rule keeps them out unless it changes.
- The Medal of Honor has 3,203 recipients, but only 553 are new: most already entered through taking part in a conflict.
- Some holders are mislinked: the Grammy Lifetime Achievement Award lists an electrical engineer and an education writer, and the Pour le Merite item mixes civil and military holders. Such errors are rare, and the curation exclusion list (`exclude_people.csv`) can absorb them.
