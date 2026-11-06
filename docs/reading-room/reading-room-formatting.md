# Reading Room — per-book formatting passes

A hand pass on every book to make it *truly* beautiful, beyond what the bulk seeding script
could do uniformly. Each title is reviewed and edited individually (no automation across
books, no fan-out) and logged here after it's finished.

## Method / conventions

- **Order:** by genre, then alphabetically by title (leading article "The/A/An" ignored).
- **Current genre:** Theology (908 CCEL works).
- **Preserve the text.** Archaic spelling and original orthography (e.g. "soveraign",
  "Councel", "Lords Supper") are kept — beautification fixes *formatting and artifacts*, never
  the historical wording.
- **Standard fixes checked each pass:** inject the chapter title as an `<h2>` heading when the
  reader would otherwise show none; strip stray entities/markup leaked into titles or body
  (`&gt;`, `&lt;`, replacement chars); normalize hard-wrapped source whitespace into flowing
  paragraphs; drop pure editorial/software boilerplate (kept when it's genuine provenance);
  verify chapter boundaries, headings, and clean semantic tags only.
- **Scope:** edits are written to the local `db/books.db`. Production is refreshed by
  re-publishing books.db to R2 periodically (in batches — not once per title).

## Progress — Theology

| # | Title | Author | Status | Notes |
|---|-------|--------|--------|-------|
| 1 | The 1677/89 London Baptist Confession of Faith | Anonymous | ✅ done | 45 ch. Injected all chapter headings (reader showed none). Fixed ch. 40 title (`&gt;` leak → "Some Biographical Materials…"). Normalized hard-wrap whitespace to flowing text. Kept original 1677 orthography and all scholarly apparatus (appendix, subscribers, historical essays, definitions, bibliography, transcription note). No mojibake — apostrophes are genuine U+2019. |
| 2 | Abandonment to Divine Providence | Jean-Pierre de Caussade | ✅ done | 169 ch. Cleaner source than #1 (well-formed body already). Injected all headings; light whitespace tidy (stripped leading spaces inside `<p>`). Renamed CCEL artifact "Second Title Page" → "Title Page" (kept its content: Strickland translator credit + Faber/Matt 11:25–26 epigraphs). No artifacts. |

| 3 | Absolute Surrender | Andrew Murray | ✅ done | 9 ch (sermons). Clean source — only needed heading injection + whitespace tidy. No artifacts, no drops/renames. |

| 4 | Abstract of Systematic Theology | James P. Boyce | ✅ done | 42 ch, ~202k w. Headings injected; stripped 19 empty `<p><br/></p>` paragraphs (added empty-paragraph removal to the baseline); unwrapped a stray `<sup>` that had wrapped the "v" of "very good". No other artifacts. |

| 5 | The Adornment of the Spiritual Marriage | John of Ruysbroeck | ✅ done (1 caveat) | 127 ch. Deep clean: the volume is **three works** flattened with dividers dropped. Cross-checked the cached CCEL TOC and **qualified every chapter** by work/book — "First Book · Chapter I", "Second Book · Chapter LXVII", "The Sparkling Stone · Chapter I", "The Book of Supreme Truth · Chapter I" — so the previously-ambiguous repeating "CHAPTER I" runs are now navigable. Headings injected. **Caveat:** The Adornment's Third Book (§97) has its 4 chapters merged into one section by the original segmentation; splitting them cleanly needs a re-fetch from CCEL — flagged, not fabricated. |

| 6 | Against War | Desiderius Erasmus | ✅ done | 2 ch (Introduction + essay; confirmed complete via CCEL TOC). Restored 2 lost drop-cap initials ("he Treatise"→"The Treatise", "t is"→"It is"); removed a redundant all-caps "AGAINST WAR" title line (heading covers it); unwrapped inert `<span>` tags; headings injected. |

| 7 | Aids to Reflection | S.T. Coleridge | ✅ done (1 caveat) | 93 ch. Headings injected; unwrapped `<span>`s; fixed OCR typo "ASPHORISM XXXVI"→"APHORISM XXXVI"; stripped trailing heading punctuation. **Caveat:** the work's aphorism-and-comment structure leaves many generic repeated "COMMENT" entries in the TOC; qualifying each to its parent aphorism needs careful source mapping (deferred, not fabricated). |
| 8 | All of Grace | C. H. Spurgeon | ✅ done | 20 ch. Clean source — headings + whitespace only. |
| 9 | All Things Considered | G. K. Chesterton | ✅ done | 26 essays. Headings injected; unwrapped `<span>`s; fixed OCR title typo "Cockeneys"→"Cockneys and Their Jokes". |
| 10 | The Almost Christian Discovered | Matthew Mead | ✅ done | 9 ch. Headings injected; unwrapped `<span>`s. Clean otherwise. |
| 11 | An Alphabetical List of M. E. Preachers | Nathan Bangs | ✅ done | 1 ch (short reference list, ~550 w). Heading injected. |

| 12 | An American Religious Movement | Winfred Ernest Garrison | ✅ done | 11 ch. Headings + spans unwrapped. Single work, no ambiguity. |
| 13 | The Analogy of Religion, Natural and Revealed | Joseph Butler | ✅ done | 20 ch. Headings + spans. Descriptive chapter titles, clean. |
| 14 | ANF01. The Apostolic Fathers w/ Justin Martyr & Irenaeus | Philip Schaff (ed.) | ✅ baseline (caveat) | 624 ch, ~495k w. Headings injected; spans unwrapped; `<q>` and legit content preserved. Chapter titles are descriptive (e.g. "Chapter I.—The salutation…"), so usable as-is. **Caveat:** this is a multi-work patristics volume — chapters aren't yet prefixed with their parent Father's work. See patristics-series note below. |
| 15 | ANF02. Fathers of the Second Century | Philip Schaff (ed.) | ✅ baseline (caveat) | 399 ch, ~500k w. Headings + spans. Kept legitimate `<sup>` (math exponent x², etc.). Same multi-work caveat. |
| 16 | ANF03. Latin Christianity: Tertullian | Philip Schaff (ed.) | ✅ baseline (caveat) | 746 ch, ~610k w. Headings + spans. Kept legitimate `<sup>` (ordinals "28ᵗʰ", "Monʳ", footnote refs). Same multi-work caveat. |

_908 Theology titles total; 16 done, 892 remaining._

| 17 | The Antichrist | Arthur W. Pink | ✅ done | 19 ch. Clean; headings only. |
| 18 | Apology of the Augsburg Confession | Philip Melanchthon | ✅ done | 38 ch. Headings; unwrapped 220 spans; normalized "Part" numbering ("Part I"→"Part 1", "Part13"→"Part 13"). Source labels sections bare "Part N" (no Article titles in the TOC) — kept faithful. |
| 19 | The Apostolic Fathers | J. B. Lightfoot | ✅ done | 15 ch. Each section is a complete work (First Clement, the Ignatian epistles…), not sub-chaptered — headings only; reads well. |
| 20 | The Apostolic Fathers: I/II Clement, Ignatius… | Kirsopp Lake | ✅ done | 26 ch (one work per section). Headings; unwrapped spans; kept a legitimate `<sup>` (Greek numeral overline β̅). |
| 21 | An Appeal to All That Doubt | William Law | ✅ done | 4 ch. Clean; headings only. |

| 22 | The Art of Divine Contentment | Thomas Watson | ✅ done + **gap repaired** | Was 15 ch with a corrupt V→VIII gap. On inspection the CCEL copy was worse than a numbering skip: Ch V was **spliced** (opening of "resolving questions" jumped mid-sentence to the tail of the reasons section), and chapters VI ("Shewing the Nature of Contentment") + VII ("Reasons Pressing to Holy Contentment") were **missing entirely**. Sourced complete V/VI/VII from the gracegems.org edition, replaced the corrupt V, inserted VI + VII, renumbered → **17 sections, contiguous I–XV**. Verified no duplicated content, headings render. Caveat: the gracegems text is lightly **modernized** ("Showing"/"you" vs the surrounding CCEL chapters' "Shewing"/"ye"), and VI is brief in that edition — provenance noted here. |
| 23 | Assorted Sermons | Martin Luther | ✅ done | 20 sermons. Headings only. Source title casing is mixed (some Title Case, some ALL CAPS) — left faithful. |
| 24 | At the Master's Feet | Sadhu Sundar Singh | ✅ done | 10 ch. Clean; headings only. |
| 25 | Autobiography of George Fox | George Fox | ✅ done | 23 ch. Headings; unwrapped 15 spans. |
| 26 | Autobiography of Madame Guyon | Madame Guyon | ✅ done | 51 ch. Headings; unwrapped 6 spans. |

| 27 | The Autobiography of St. Ignatius | Ignatius of Loyola | ✅ done | 11 ch. Headings; unwrapped 17 spans. |
| 28 | The Backslider in Heart | Charles G. Finney | ✅ done | 1 ch (sermon). Clean; heading only. |
| 29 | Baxter's Second Innings | Henry Drummond | ✅ done | 7 ch. Clean; headings only. |
| 30 | The Beatitudes: An Exposition of Matthew 5:1–12 | Thomas Watson | ✅ done | 23 ch. Headings; unwrapped 2 spans. |
| 31 | Bede's Ecclesiastical History of England | The Venerable Bede | ✅ done | 141 ch across 5 Books. Detected Book boundaries from roman-numeral **resets** (DB had no Book dividers) → prefixed "Book 1 · I…", fixed roman-spacing glitches ("XX III"→"XXIII"). Stripped empty `<sup>`/`<sub>` footnote-marker residue (kept real ones — ordinals, footnote numbers). Also hardened the shared helper to always re-inject headings (idempotent). |

| 32 | The Beginnings of Christianity, Vol. I | Paul Wernle | ✅ done | 22 ch. Headings; unwrapped 22 spans. |
| 33 | The Beginnings of Christianity, Vol. II | Paul Wernle | ✅ done | 13 ch. Headings; unwrapped 31 spans; fixed OCR typo "Devlopment"→"Development". |
| 34 | Biography of John Owen | Encyclopaedia Britannica | ✅ done | 2 ch. Headings; unwrapped span; fixed a literal newline in the author field ("Encyclopaedia\nBritannica" → "Encyclopaedia Britannica"). |
| 35 | A Body of Divinity | Thomas Watson | ✅ done | 43 ch. Clean; headings only. (Numbered doctrines reset per topical part; descriptive titles keep them navigable.) |
| 36 | A Book of Hymns for Public and Private Devotion | Samuel Longfellow | ⚠️ shell — content missing | Only 3 sections (title/preface/index, ~200 w). The CCEL TOC lists **608 entries** (hundreds of hymns) — the hymn text was dropped in seeding. Baseline applied, but this needs **re-ingestion** to restore the hymns. Flagged. |

_908 Theology titles total; **70 done** (36 alphabetical + 34 further patristics), 843 remaining — but see the shell-books flag below._

### Ingestion repair (2026-09-18) — root cause + fixes + strategy
**Root-cause bug FIXED:** `seed_theology_reader._ancestors()` split CCEL division ids on `_`
as well as `.`, so a main-work id like `ii_1` was treated as a child of front-matter `ii`
("Publishers' Note") and the **entire work was dropped as front matter**. Fixed to split on
`.` only. Proof: *The Scale of Perfection* 1 ch/13k w → 74 ch/108k w.

**Shells fixed by targeted re-extraction** (from the stage db, fixed chaptering; written per-book
so the 65 already-formatted books are untouched — a global rebuild would wipe them):
- *The Scale (or Ladder) of Perfection* — 13,456 → 109,192 w (74 ch)
- *Centuries of Meditations* (Traherne) — 63,485 → 82,864 w (6 ch)

**Strategy for the rest — `scripts/audit_theology_ingestion.py`** (reusable): compares each book's
words to (a) the local `theology_texts`, and flags (b) source-thin works needing CCEL. A full
`--reextract` pass over the stage confirmed only those 2 were recoverable from local data.

**Remaining shells = CCEL re-fetch needed** (the HF source dataset itself is thin): the real ones
are *Divine Comedy* (7 paras vs 108 TOC entries), *Hitchcock's Bible Names Dictionary*, *NT Song
Database*, *A Book of Hymns* (Longfellow), and several hymn/song collections (*Hymns of the Early
Church*, *Olney Hymns*, *Hymns of the Russian Church*, *Sacred Poems*, etc.). **Not shells** (short
but complete): Pascal's *Memorial*, elegies, the M.E. Preachers list, ECF fragments — flagged so
the CCEL pass skips them. *NPNF2-09 (Hilary)* and *Touching Incidents* read large in `theology_texts`
but the reader stage is thin for them → they also fall to the CCEL bucket. **CCEL re-fetch is a
separate build (fetch full text from ccel.org + ThML-chapter it); not yet done.**

| 37 | The Book of Jasher | Anonymous | ✅ shell **repaired** via CCEL | Was 1 ch (11.6k-word intro only) — the 91 chapters were missing (verses live in `<ol><li>`, which the `<p>`-based ingestion skipped; the long intro hid it from the word-count detectors). Re-fetched from CCEL → **92 ch / 161k w** (Introduction + Book of Jasher 1–91, verses as numbered lists). |
| 38 | A Brief Account of the Rise of the Quakers | William Penn | ✅ done | 8 ch. Headings; spans unwrapped. |
| 39 | A Brief Declaration…of the Trinity | John Owen | ✅ done | 7 ch. Headings; 144 spans unwrapped; kept legit `<sup>`/`<cite>`. |
| 40 | A Brief Instruction in the Worship of God | John Owen | ✅ done | 53 Q&A ch. Headings; 169 spans unwrapped; kept 180 legit footnote-letter `<sup>`s. |
| 41 | Broken Bread | John Wright Follette | ✅ done | 20 ch. Headings; span unwrapped. |

| 42 | Brooks by the Traveller's Way | John Henry Jowett | ✅ done | 27 ch. Headings; spans unwrapped. |
| 43 | A Call to the Unconverted to Turn and Live | Richard Baxter | ✅ done | 4 sermons. Headings; spans unwrapped. |
| 44 | Callista: a Tale of the Third Century | J. H. Newman | ✅ done | 36 ch (novel). Headings; 325 spans unwrapped. |
| 45 | The Canon of the Old and New Testaments | Archibald Alexander | ✅ done | 34 sections. Headings; 439 spans unwrapped. |
| 46 | Catena Aurea — Gospel of Mark | Thomas Aquinas | ✅ done | 17 ch (Preface + Mark 1–16). Clean; headings only. |

| 47 | Catholic Tales and Christian Songs | Dorothy L. Sayers | ✅ done | 24 poems. Headings; stripped an empty `<p>`; kept verse `<br>`s. |
| 48 | The Causes and Danger of Slighting Christ | Richard Baxter | ✅ done | 6 ch. Clean; headings only. |
| 49 | The Causes of the Corruption of the Traditional Text | J. W. Burgon | ✅ done | 20 ch. Headings; 1,952 spans unwrapped; kept 92 legit footnote `<sup>`s. |
| 50 | The Celestial Hierarchy | Dionysius the Areopagite | ✅ done | 15 ch. Clean; headings only. |
| 51 | The Cell of Self-Knowledge | Edmund G. Gardner (ed.) | ✅ done | 19 ch (7 English mystical treatises). Headings; empty `<p>`s stripped; verse `<br>`s kept. Structure clear (only Treatise I has "Cap." sub-chapters) — no qualification needed. |

| 52 | Centuries of Meditations | Thomas Traherne | ✅ done | 6 ch. (Content restored earlier via the `_ancestors` fix.) Finalized: spans unwrapped, headings. |
| 53 | The Change of the Sabbath | Thomas Shepard | ✅ done | 1 ch (single discourse; TOC=3, complete). Clean; heading. |
| 54 | The Character of Jesus | Horace Bushnell | ✅ done | 1 ch (single discourse). Headings; 56 spans unwrapped. |
| 55 | The Chorale Book for England | Catherine Winkworth | 🗑️ deleted (hymnal shell) | 24 ch ingested but TOC has 265 hymns — only front matter + samples present. Deleted per the low-value-hymnal-shell policy. |
| 56 | Christ Altogether Lovely | John Flavel | ✅ done | 3 ch. Clean; headings only. |

| 57 | Christ and His Salvation | Horace Bushnell | ✅ done | 21 ch. Headings; spans unwrapped. |
| 58 | The Christ of History | John Young | ✅ done | 19 ch. Headings; spans unwrapped. |
| 59 | Christian Doctrine of Sin | John Tulloch | ✅ done | 27 ch. Headings; spans unwrapped. |
| 60 | The Christian Ecclesia | F. J. A. Hort | ✅ done | 14 lectures. Headings; 446 spans unwrapped; 4 legit sups kept. |
| 61 | Christian Ethics, Vol. I | Adolf Wuttke | ✅ done | 46 ch. Headings; 284 spans unwrapped. |

| 62 | Christian Ethics, Vol. II | Adolf Wuttke | ✅ done | 19 ch. Headings; spans unwrapped. |
| 63 | The Christian Hymn Book | Alexander Campbell | 🗑️ deleted (hymnal shell) | TOC has 1,390 hymns; only 59 topical headers ingested. Deleted per policy. |
| 64 | Christian Hymns of the First Three Centuries | Ruth Ellis Messenger | ✅ done | 9 ch — a scholarly *study* of early hymns (not a hymnal), complete. Headings; spans unwrapped. |
| 65 | Christian Morals | Sir Thomas Browne | ✅ done | 5 ch. Headings; spans unwrapped; 4 legit sups kept. |
| 66 | Christian Mysticism | W. R. Inge | ✅ done | 14 ch. Headings; spans unwrapped. |

| 67 | Christian Nurture | Horace Bushnell | ✅ done | 16 ch. Headings; spans unwrapped. |
| 68 | Christian Singers of Germany | Catherine Winkworth | ✅ done | 106 ch. Substantially complete prose (not a shell). Headings. |
| 69 | Christian View of God and the World | James Orr | ✅ done | 48 ch. Headings; spans unwrapped. |
| 70 | Christian Workers' Commentary on the OT & NT | James M. Gray | ✅ done | 67 ch, ~340k w. Clean; headings. |
| 71 | The Christian Year | John Keble | ✅ shell **repaired** via CCEL | Was 76 ch of scripture epigraphs only — the poems were missing (they live in `<verse>`/`<l>` tags). Re-fetched → **111 ch / 47k w** (each poem: epigraph + verse stanzas). |

| 72 | The Christian's Great Interest | William Guthrie | ✅ done | 19 ch. Headings; spans unwrapped. |
| 73 | The Christian's Secret of a Happy Life | Hannah Whitall Smith | ✅ done | 23 ch. Clean; headings. |
| 74 | Christologia | John Owen | ✅ done | 22 ch. Headings; 249 spans unwrapped; 90 legit sups kept. |
| 75 | The Church and the Ministry in the Early Centuries | T. M. Lindsay | ✅ done | 11 ch. Headings; spans unwrapped. |
| 76 | The Church in Rome in the First Century | George Edmundson | ✅ done | 16 ch. Headings; spans unwrapped; 4 legit sups kept. |

| 77 | The Cloud of Unknowing | Anonymous | ✅ done | 80 ch. Headings; spans unwrapped (12 empty `<span>`s were cruft, not lost drop-caps — words intact). |
| 78 | A Collection of Gospel Songs in Ojibway | Intl. Evangelical Mission | 🗑️ deleted (shell) | Only the 1899 imprint/colophon present; songs entirely missing. Deleted per policy. |
| 79 | A Collection of Letters | William Law | ✅ done | 24 ch. Clean; headings. |
| 80 | The Colloquies of Erasmus, Vol. I | Desiderius Erasmus | ✅ done | 40 ch. Headings; 6,999 spans unwrapped. |
| 81 | Comfort for Christians | A. W. Pink | ✅ done | 18 ch. Headings; spans unwrapped. |

| 82 | A Commentary on Acts of the Apostles | J. W. McGarvey | ✅ done | 31 ch. Headings; spans unwrapped. |
| 83 | Commentary on Revelation | E. W. Bullinger | ✅ done | 44 ch. Headings; spans unwrapped; 477 legit sups kept; fixed author newline. |
| 84 | A Commentary on…Galatians | Martin Luther | ✅ done | 8 ch. Headings; spans unwrapped. |
| 85 | A Commentary on…Ephesians | Charles Hodge | ✅ done | 6 ch. Headings; 1,163 spans unwrapped. |
| 86 | Commenting and Commentaries | C. H. Spurgeon | ✅ done | 4 ch. Clean; headings. |

| 87 | The Complete Works of Menno Simon, Vol. 1 | Menno Simon | ✅ done | 53 ch. Headings; spans unwrapped. |
| 88 | The Complete Works of Menno Simon, Vol. 2 | Menno Simon | ✅ done | 79 ch. Headings; spans unwrapped; removed a stray `&gt;` in a Scripture-ref list. |
| 89 | The Complete Works of Thomas Manton, Vol. 1 | Thomas Manton | ✅ done | 32 ch. Headings; spans unwrapped. |
| 90 | The Complete Works of Thomas Manton, Vol. 2 | Thomas Manton | ✅ done | 36 ch. Headings; spans unwrapped. |
| 91 | The Complete Works of Thomas Manton, Vol. 3 | Thomas Manton | ✅ done | 30 ch. Headings; spans unwrapped. |

| 92 | The Complete Works of Thomas Manton, Vol. 4 | Thomas Manton | ✅ done | 6 ch (commentary on James 1–5; verbose but complete). Headings; spans unwrapped. |
| 93 | The Complete Works of Thomas Manton, Vol. 5 | Thomas Manton | ✅ done | 34 ch. Headings; spans unwrapped. |
| 94 | The Complete Works of Thomas Manton, Vol. 8 | Thomas Manton | ✅ done | 54 ch. Headings; spans unwrapped. |
| 95 | Concerning Christian Liberty | Martin Luther | ✅ done | 2 ch. Clean; headings. |
| 96 | The Conferences of John Cassian | John Cassian | ✅ done (qualified) | 443 ch across 24 Conferences. Ran the patristics qualifier → prefixed "Conference N · Chapter M" (0 unmatched). Headings; spans unwrapped. |

| 97 | The Confession of St. Patrick | St. Patrick | ✅ done | 10 ch. Clean; headings. |
| 98 | Confessions and Enchiridion | St. Augustine (Outler) | ✅ done | 14 ch. Headings; spans unwrapped. |
| 99 | The Confessions of Saint Augustine | St. Augustine (Pusey) | ✅ done (qualified) | 211 ch. Books I–V are single blobs (kept); Books VI–XIII are chaptered — qualified "Book N · Chapter M" via roman-reset (fixed 2 false resets caused by lowercase-i romans "XXi"/"Xi", now normalized). |
| 100 | The Confutatio Pontificia | Anonymous | ✅ done | 3 ch. Clean; headings. |
| 101 | The Consolation of Philosophy | Boethius | ✅ done | 9 ch. Headings; spans unwrapped. |

| 102 | Creeds of Christendom, Vol. III | Philip Schaff | ✅ done | 49 ch. Headings; spans unwrapped. |
| 103 | Creeds of Christendom, Vol. I | Philip Schaff | ✅ done | 119 ch, ~445k w. Headings; 4,493 spans unwrapped; 5 legit sups kept. |
| 104 | Creeds of Christendom, Vol. II | Philip Schaff | ✅ done | 40 ch. Headings; spans unwrapped; 3 sups kept. |
| 105 | The Crook in the Lot | Thomas Boston | ✅ done | 3 ch. Clean; headings. |
| 106 | The Crowd is Untruth | Søren Kierkegaard | ✅ done | 1 ch (complete short essay). Clean; heading. |

| 107 | Daily Light on the Daily Path | Anonymous | ✅ done | 732 ch (daily devotional). Headings; spans unwrapped. |
| 108 | Daily Meditations and Prayers | John Bradford | ✅ done | 21 ch. Clean; headings. |
| 109 | Daily Prayers of Master John Bradford | John Bradford | ✅ done | 8 ch. Clean; headings. |
| 110 | Davids Hainous Sinne, Heartie Repentance… | Thomas Fuller | ✅ shell **repaired** via CCEL | Was 285 w (colophon only); the poem is in `<verse>`/`<l>` tags. Re-fetched → 3 parts / 7,938 w (verse stanzas). |
| 111 | De Contemptu Mundi | Eucherius of Lyon | ✅ done | 2 ch. Headings; span unwrapped. |

| 112 | De Servo Arbitrio (On the Enslaved Will) | Martin Luther | ✅ done | 167 ch. Inert `<span>` (small-caps emphasis) unwrapped; headings; clean titles. |
| 113 | Death's Duel | John Donne | ✅ done | 1 ch (sermon). Headings; clean. |
| 114 | Dialog of Catherine of Siena | Catherine of Siena | ✅ done | 89 ch, descriptive titles intact. Baseline. |
| 115 | Dialogue of Comfort Against Tribulation | Thomas More | ✅ done | 68 ch. **Structural fix**: bare roman chapters ("I", "II"…) reprefixed to "Book One/Two/Three · Chapter N"; all-caps dividers title-cased. |
| 116 | Dionysius the Areopagite, Works (1897) | Dionysius the Areopagite | ✅ done | 55 ch. **Structural fix**: Vol-2 dropped its two treatise names; Caputs reprefixed by treatise from cached TOC (On Divine Names / On the Heavenly Hierarchy / Ecclesiastical Hierarchy), "Caput Ii" → "Caput II". Spans unwrapped. |

| 117 | Directions to Church-Wardens | Humphrey Prideaux | ✅ done | 11 ch. Spans unwrapped; headings. |
| — | Divine Comedy | Dante | ✅ (already repaired) | Skipped — formatted in an earlier CCEL repair. |
| — | Divine Songs and Meditacions | Anne Collins | 🗑 **deleted (copyright)** | CCEL edition = 1961 Augustan Reprint Society facsimile; its substance is Stewart's 1961 copyrighted intro + a modern subscription ad, and Collins's PD poems were never in our source. Not PD → removed. |
| 118 | Doctrinal Theology | Heinrich Schmid | ✅ done | 69 ch. Source title glitches fixed (bare "Chapter" → "Chapter II."; "Chapter Chapter IV…" → "Chapter IV…"). Spans unwrapped. |
| 119 | Early Christian Doctrine | Leighton Pullan | ✅ done | 11 ch. Baseline; headings. |
| — | Early Christian Fathers | Cyril C. Richardson | 🗑 **deleted (copyright)** | 1953 Library of Christian Classics translation — modern copyright, not PD. Removed. |
| 120 | Easton's Bible Dictionary | M.G. Easton | ✅ done | 25 letter-sections (A–Z), PD 1897. Baseline. |
| 121 | ECF: Ambrose of Milan: Letters | (Pearse, PD tr.) | ✅ done | 11 ch grouped letters. Spans unwrapped; footnote `<sup>` preserved. |
| 122 | ECF: Aphrahat: Demonstrations | Aphrahat (Pearse) | ✅ done | 2 ch (De Caritate; On Penitents). Baseline. |

| 123 | ECF: Aristides the Philosopher: Apology | (Pearse, PD trs.) | ✅ done | 8 ch. **Filename titles** ("aristides_01_intro.htm"…) replaced with accurate headings — it bundles the ANF translation + the Cambridge *Texts and Studies* (Harris & Robinson) edition. Spans unwrapped. |
| 124 | ECF: Asterius: Ancient Sermons for Modern Times | (Pearse) | ✅ done | 6 ch. Baseline. |
| 125 | ECF: Basil the Great: Address to Young Men | (Pearse) | ✅ done | 2 ch. Spans unwrapped. |
| 126 | ECF: Chromatius of Aquileia: Sermons | (Carlson, PD) | ✅ done | 1 ch (Prologue). Explicitly public-domain (Carlson 2005). |
| 127 | ECF: Cyril of Alexandria: Against Diodore & Theodore | Cyril (Pearse) | ✅ done | 3 ch. Spans unwrapped. |

| 128 | ECF: Cyril of Alexandria: Against Julian | Cyril (Pearse) | ✅ done | 2 ch (Prefatory Address; Book II). Baseline. |
| 129 | ECF: Cyril of Alexandria: Against the Synousiasts | Cyril (Pearse) | ✅ done | 1 ch. Spans unwrapped. |
| 130 | ECF: Cyril of Alexandria: Commentary on John | Cyril (Pearse) | ✅ done | 14 ch (Books I–XII + intro/praefatio). Spans unwrapped. |
| 131 | ECF: Cyril of Alexandria: Commentary on Luke | Cyril (Pearse) | ✅ done | 16 ch (grouped sermons). Spans unwrapped. |
| 132 | ECF: Cyril of Alexandria: Five Tomes Against Nestorius | Cyril (Pearse) | ✅ done | 6 ch (Books I–V + intro). Spans unwrapped. |

| 133 | ECF: Cyril of Alexandria: Scholia on the Incarnation | Cyril (Pearse) | ✅ done | 1 ch. Fixed source typo in heading ("incarnatino" → "Incarnation"). Spans unwrapped. |
| 134 | ECF: Cyril of Alexandria: That Christ is One | Cyril (Pearse) | ✅ done | 1 ch. Spans unwrapped. |
| 135 | ECF: Dionysius of Alexandria: Newly Discovered Letters | Dionysius (Pearse) | ✅ done | 4 ch. Baseline. |
| 136 | ECF: Epiphanius of Salamis: Weights and Measures | (Pearse) | ✅ done | 4 ch. Spans unwrapped. |
| 137 | ECF: Eunomius: The First Apology | (Pearse) | ✅ done | 2 ch. Spans unwrapped. |

| 138 | ECF: Eusebius: Against Hierocles | Eusebius (Pearse) | ✅ done | 2 ch. Spans unwrapped. |
| 139 | ECF: Eusebius: Demonstratio Evangelica | Eusebius (Pearse) | ✅ done | 14 ch (Books 1–10 + intro). Spans unwrapped. |
| 140 | ECF: Eusebius: Encomium on the Martyrs | Eusebius (Pearse) | ✅ done | 1 ch. Baseline. |
| 141 | ECF: Eusebius: On the Star | Eusebius (Pearse) | ✅ done | 3 ch. Spans unwrapped. |
| 142 | ECF: Eusebius: Onomasticon | Eusebius (Pearse) | ✅ done | 67 ch (scholarly intro → Section A/B/G/D… gazetteer → appendices). Spans unwrapped. |

| 143 | ECF: Eusebius: Praeparatio Evangelica | Eusebius (Pearse) | ✅ done | 395 ch. **Structural fix**: chapters were bare "CHAPTER I" repeating across 15 books (Book dividers dropped in extraction). Aligned to cached TOC (0 residual mismatches) and reprefixed "Book I…XV · Chapter N"; all-caps normalized. Spans unwrapped. |
| 144 | ECF: Eusebius: The History of the Martyrs in Palestine | Eusebius (Pearse) | ✅ done | 20 ch. Spans unwrapped. |
| 145 | ECF: Eusebius: Theophania | Eusebius (Pearse) | ✅ done | 6 ch (Books 1–5 + preface). Spans unwrapped. |
| 146 | ECF: Eusebius: Letter to Carpianus | Eusebius (Pearse) | ✅ done | 1 ch. Baseline. |
| 147 | ECF: Gregory of Nyssa: Life of St. Macrina | Gregory (Pearse) | ✅ done | 2 ch. Dropped a modern publisher-advert section ("Adverts"). Spans unwrapped. |

| 148 | ECF: Hegesippus | (Pearse) | ✅ done | 7 ch (Books I–V + intro/prologue). Spans unwrapped. |
| 149 | ECF: Hermias: Derision of Gentile Philosophers | Hermias (Pearse) | ✅ done | 3 ch. Spans unwrapped. |
| 150 | ECF: Irenaeus: Proof of the Apostolic Preaching | (Pearse) | ✅ done | 4 ch. Spans unwrapped. |
| 151 | ECF: Jerome: Biblical Prefaces | Jerome (Pearse) | ✅ done | 21 ch (one preface per book). Spans unwrapped. |
| 152 | ECF: Jerome: Commentary on Daniel | Jerome (Pearse) | ✅ done | 17 ch. Spans unwrapped. |

| 153 | ECF: Jerome: Letter 120 (Ad Hedibiam) | Jerome (Pearse) | ✅ done | 15 ch. Spans unwrapped. |
| 154 | ECF: John Chrysostom: Four Discourses | Chrysostom (Pearse) | ✅ done | 28 ch. **Structural fix**: Discourses I & III have chapters that reset to "Chapter 1"; reprefixed "Discourse I/III · Chapter N" (+ their Footnotes). Spans unwrapped. |
| 155 | ECF: Marcionite & Anti-Marcionite Prologues | (Pearse) | ✅ done | 2 ch. Baseline. |
| 156 | ECF: Marutha of Maiperqat: On the Council of Nicaea | (Pearse) | ✅ done | 2 ch. Spans unwrapped. |
| 157 | ECF: Nestorius: 2nd & 3rd Letters to Pope Celestine | Nestorius (Pearse) | ✅ done | 1 ch. Baseline. |
| 158 | ECF: Nestorius: The Bazaar of Heracleides | Nestorius (Pearse) | ✅ done | 8 ch. Spans unwrapped. |
| 159 | ECF: Optatus of Milevis: Against the Donatists | (Pearse) | ✅ done | 20 ch (Books I–VII). Spans unwrapped. |
| 160 | ECF: Origen: On Prayer | Origen (Pearse) | ✅ done | 1 ch. Spans unwrapped. |
| 161 | ECF: Origen: Philocalia | (Lewis/Pearse) | ✅ done | 4 ch. Spans unwrapped. |
| 162 | ECF: Palladius: The Lausiac History | Palladius (Pearse) | ✅ done | 2 ch. Spans unwrapped. |

| 163 | ECF: Philostorgius: Ecclesiastical History | (Pearse) | ✅ done | 16 ch (Books I–XII). Baseline. |
| 164 | ECF: Polycarp: Fragments from Victor of Capua | (Pearse) | ✅ done | 3 ch. `<cite>` preserved. |
| 165 | ECF: Possidius: Life of St. Augustine | (Pearse) | ✅ done | 1 ch. Spans unwrapped. |
| 166 | ECF: St. Augustine: Enchiridion | Augustine (Pearse) | ✅ done | 34 ch. Spans unwrapped. |
| 167 | ECF: St. Ephraim: Prose Refutations, Vol. 1 | Ephraim (Pearse) | ✅ done | 6 ch. Spans unwrapped. |
| 168 | ECF: St. Ephraim: Prose Refutations, Vol. 2 | Ephraim (Pearse) | ✅ done | 9 ch. Spans unwrapped. |
| 169 | ECF: Thaumaturgus: Homily on the Holy Mother of God | (Pearse) | ✅ done | 1 ch. Spans unwrapped. |
| 170 | ECF: The Apocriticus of Macarius Magnes | (Pearse) | ✅ done | 7 ch. Baseline. |
| 171 | ECF: The Extant Works of St. Pacian | Pacian (Pearse) | ✅ done | 6 ch. Baseline. |
| 172 | ECF: The Western Text of the Acts of the Apostles | Wilson (Pearse) | ✅ done | 24 ch. Spans unwrapped. |

| 173 | ECF: Theodore of Mopsuestia: Commentary on the Lord's Prayer & Sacraments | (Pearse) | ✅ done | 8 ch. Spans unwrapped. |
| 174 | ECF: Theodore of Mopsuestia: Commentary on the Nicene Creed | (Pearse) | ✅ done | 13 ch. Spans unwrapped. |
| 175 | ECF: Theodore of Mopsuestia: Prologue to the Acts | (Pearse) | ✅ done | 2 ch. Spans unwrapped. |
| — | Eclectic Ethereal Encyclopedia | (CCEL) | 🗑 **deleted (stub)** | 116-word CCEL navigational meta-page ("About these Articles"), not a work. |
| 176 | Eight Sermons Preach'd at the Boyle Lectures | Richard Bentley | ✅ done | 9 ch. Spans unwrapped. |
| 177 | Entire Sanctification | Adam Clarke | ✅ done | 2 ch (bio + treatise). Baseline. |
| 178 | Epistles to the Seven Churches in Asia | R.C. Trench | ✅ done | 10 ch. Spans unwrapped. |
| 179 | Eshcol: A Cluster of the Fruit of Canaan | John Owen | ✅ done | 18 ch (Rules I–XV). Spans unwrapped. |
| 180 | Essays and Reviews | Frederick Temple et al. | ✅ done | 8 ch (seven essays). Spans unwrapped. |
| 181 | Euchology: A Manual of Prayers | G.V. Shann | ✅ **re-chaptered from external source** | Our ThML source had the whole 103k-word manual in one flat block. Cross-referenced the CCEL page HTML (which keeps the office headings as plain `<p>` text) to recover the printed structure, located all 30 numbered offices (I–XXX) in our clean text, and split the blob into 31 chapters (front matter + 30 offices). Fixed the printed "III."→VIII typo on The Daily Nocturns. No content lost. |

| 182 | Eugenics and Other Evils | G.K. Chesterton | ✅ done | 18 ch. Spans unwrapped. |
| 183 | Evidence of Christianity | William Paley | ✅ done | 43 ch (Parts I–III). Spans unwrapped. |
| 184 | Exposition of Genesis, Vols. 1–2 | H.C. Leupold | ✅ done | 52 ch. Spans unwrapped. |
| 185 | Expositions of Holy Scripture: Deuteronomy | Alexander Maclaren | ✅ done | 114 sermons. Spans unwrapped. |
| 186 | Expositions of Holy Scripture: Ezekiel, Daniel, Minor Prophets | Alexander Maclaren | ✅ done | 104 sermons. Disambiguated 3 same-titled "A Dialogue with God" sermons by Malachi reference (i.6-7 / ii.12-14 / iii.7). |
| 187 | Expositions of Holy Scripture: Genesis, Exodus, Leviticus, Numbers | Alexander Maclaren | ✅ **structural repair** | The 51 Genesis sermons were merged into one 109k-word blob (chaptering bug on the `ii.i.*` hierarchy). Split them using the stage DB's per-sermon divisions + TOC titles → 112 chapters (front matter + 51 Genesis sermons + 60 Exodus/Lev/Num sermons). No content lost. |
| 188 | Expositions of Holy Scripture: Isaiah & Jeremiah | Alexander Maclaren | ✅ done | 121 sermons. Spans unwrapped. |
| 189 | Expositions of Holy Scripture: Luke | Alexander Maclaren | ✅ done | 99 sermons. Spans unwrapped. |
| 190 | Expositions of Holy Scripture: Mark | Alexander Maclaren | ✅ done | 80 sermons. Spans unwrapped. |
| 191 | Expositions of Holy Scripture: Matthew IX–XXVIII | Alexander Maclaren | ✅ done | 83 sermons. Spans unwrapped. |

| 192 | Expositions of Holy Scripture: Psalms | Alexander Maclaren | ✅ done | 81 sermons. Disambiguated 1 repeated title by Psalm ref. |
| 193 | Expositions of Holy Scripture: Romans & Corinthians | Alexander Maclaren | ✅ done | 91 sermons. Disambiguated repeats — incl. the 4-part "Still Another Triplet" (Rom xii.13-21) — by reference. |
| 194 | Expositions of Holy Scripture: Second Corinthians & Timothy | Alexander Maclaren | ✅ done | 87 sermons. Disambiguated "Risen with Christ" ×2 by ref. |
| 195 | Expositions of Holy Scripture: St John Chs. I–XIV | Alexander Maclaren | ✅ done | 77 sermons. Baseline. |
| 196 | Expositions of Holy Scripture: St John Chs. XV–XXI | Alexander Maclaren | ✅ done | 45 sermons. Baseline. |
| 197 | Expositions of Holy Scripture: The Acts | Alexander Maclaren | ✅ done | 102 sermons. Disambiguated "Philip the Evangelist" ×2 by ref. |
| 198 | Expositions of the Holy Scriptures: Second Kings–Ecclesiastes | Alexander Maclaren | ✅ done | 112 sermons. Spans unwrapped. |
| 199 | Expositor's Bible: Judges and Ruth | Robert A. Watson | ✅ **structural fix** | Bare "Chapter I…" reset between the two books; reprefixed "Judges · Chapter I–XXV" and "Ruth · Chapter I–V". |
| 200 | Expositor's Bible: The Book of the Twelve Prophets, Vol. 2 | George Adam Smith | ✅ done | 39 ch. Disambiguated the two "Zechariah" dividers → proto (I.–VIII., Zech 4:6) / deutero (IX.–XIV., Zech 9:9). |
| 201 | Expositor's Bible: The First Book of Samuel | W.G. Blaikie | ✅ done | 36 ch. Spans unwrapped. |

| 202 | Expository Thoughts on Matthew | J.C. Ryle | ✅ done | 37 ch. Baseline. |
| 203 | Faith's Checkbook | C.H. Spurgeon | ✅ done | 14 ch. Baseline. |
| — | Favourite Welsh Hymns | Joseph Morris | 🗑 **deleted (shell)** | 524-word shell — only category headers ("Jesus", "Heaven"…), no hymn content. |
| 204 | Felon's Maxims of the Saints | T.C. Upham | ✅ done | 44 ch. Baseline. |
| 205 | Fifteen Sermons Preached at the Rolls Chapel | Joseph Butler | ✅ done | 16 ch. Spans unwrapped. |
| 206 | First Principles of the Reformation | Martin Luther | ✅ done | 18 ch. Spans unwrapped. |
| 207 | Food for the Lambs | James Orr | ✅ done | 46 ch. Baseline. |
| 208 | Freedom of the Will | Jonathan Edwards | ✅ done | 32 ch. Spans unwrapped. |
| 209 | From the Talmud and Hebraica | John Lightfoot | ✅ **structural fix** | "Chapter N" reset across the four Gospels; reprefixed by Gospel (Matthew/Mark/Luke/John · Chapter…) using the intro dividers. |
| 210 | Funeral Sermon on Dr John Owen | David Clarkson | ✅ done | 1 ch. |
| 211 | Gathering Clouds: A Tale of the Days of Chrysostom | F.W. Farrar | ✅ done | 74 ch. Baseline. |
| 212 | God's Way of Peace | Horatius Bonar | ✅ done | 13 ch. Baseline. |
| 213 | Godly Meditations upon the Lord's Prayer, Creed, Commandments | John Bradford | ✅ done | 15 ch. Baseline. |
| 214 | Golden Grain | J.W. Follette | ✅ done | 50 ch. Baseline. |
| 215 | Good Thoughts in Bad Times & Other Papers | Thomas Fuller | ✅ done | 134 ch (compilation; repeated section names across sub-works left as-is). Spans unwrapped. |
| 216 | Gospel Grounds and Evidences of the Faith | John Owen | ✅ done | 7 ch. Spans unwrapped. |
| 217 | Grace Abounding | John Bunyan | ✅ done | 5 ch. Spans unwrapped. |
| 218 | Grace and Personality | John Oman | ✅ **structural fix** | "CHAPTER I–VIII" reset across 3 parts; reprefixed "Part I/II/III · Chapter N" (part dividers dropped in extraction). |
| 219 | Handbook on Faith, Hope, and Love | Augustine | ✅ done | 33 ch. Spans unwrapped. |
| 220 | Helps to the Study of the Bible | Oxford University Press | ✅ **structural fix** | Two bare A–Z runs; reprefixed "The Oxford Index · A…" and "The Oxford Concordance · A…". |

| 221 | Heretics | G.K. Chesterton | ✅ done | 19 ch. |
| 222 | Historia Calamitatum | Peter Abelard | ✅ done | 18 ch. |
| 223 | Historic Creeds and Confessions | Brannan (ed.) | ✅ done | 57 ch. Disambiguated repeated "Rejection of Errors" (Canons of Dordt heads) & "Introduction" by their parent document. |
| 224–231 | History of the Christian Church, Vols. 1–8 | Philip Schaff | ✅ done | 112/194/188/172/134/82/122/169 ch. Recurring per-chapter "Literature" bibliographies disambiguated by their parent section; two adjacent split-section repeats marked "(continued)". |
| 232 | History of the Rise of the Huguenots | Henry M. Baird | ✅ done | 14 ch. |
| 233 | Hitchcock's Bible Names Dictionary | R.D. Hitchcock | ✅ done | 23 A–Z sections (already CCEL-repaired; sparse F/Q are correct — few Bible names start with those). |
| 234 | Hobart's Analysis of Bishop Butler's Analogy | C.E. West | ✅ done | 18 ch. |
| 235 | Holiness Teachings | B.H. Roberts | ✅ done | 39 ch. |
| 236 | Holiness: Its Nature, Hindrances, Difficulties, and Roots | J.C. Ryle | ✅ done | 21 ch. |
| 237 | Holy Dying | Jeremy Taylor | ✅ done | 36 ch. |
| 238 | Holy Living | Jeremy Taylor | ✅ **structural fix** | Bare "Section I–VII" reset across chapters; disambiguated each by its parent chapter/topic. |
| 239 | Holy Wisdom | Augustine Baker | ✅ done | 93 ch. |
| 240 | How to Become Like Christ | Marcus Dods | ✅ done | 6 ch. |

| 241 | How to Live a Holy Life | James Orr | ✅ done | 48 ch. |
| 242 | How to Pray | R.A. Torrey | ✅ done | 15 ch. |
| 243 | Hymn Writers of the Church | C.S. Nutter | ✅ done | 309 ch (biographical entries — prose study of hymnody, kept). |
| 244 | Hymns and Hymnwriters of Denmark | J.C. Aaberg | ✅ done | 19 ch (prose study, kept). |
| — | **14 hymn-text collections** | Brownlie / Cox / Borthwick / Bevan / Eells / Neale | 🗑 **deleted (per policy)** | Per Adam's call: keep only prose studies of hymnody; delete all hymn-text collections. Removed: Brownlie ×7 (Hymns from the East / Morningland / Office Book / Apostolic / Latin / Greek / Holy Eastern + Indexes), Cox (From the German), Borthwick (Land of Luther), Bevan ×2 (Ter Steegen 1 & 2), Eells (Chinook), Neale (Hymns of the Eastern Church). |
| 245 | In His Steps | Charles M. Sheldon | ✅ done | 31 ch. |
| 246 | In Praise of Folly | Erasmus | ✅ done | 2 ch. |

| — | Indian Methodist Hymn-Book | Thomas Crosby | 🗑 **deleted (hymn policy)** | Hymn-text collection. |
| 247 | Inspiration and Interpretation | J.W. Burgon | ✅ done | 31 ch. |
| 248 | Introduction to the Devout Life | Francis de Sales | ✅ done | 102 ch. |
| 249 | Introduction to the New Testament | Louis Berkhof | ✅ done | 32 ch (1915, PD). |
| 250 | Jacob Behmen, An Appreciation | Alexander Whyte | ✅ done | 2 ch. |
| 251 | Jeremiah (Baird Lectures) | George Adam Smith | ✅ done | 21 ch. |
| — | Jesus and His Sacrifice | Vincent Taylor | 🗑 **deleted (copyright)** | 1937 work (preface dated 1936) — modern copyright. |
| 252 | John Calvin and the Psalmody of the Reformed Churches | L.F. Benson | ✅ done | 13 ch. |
| 253 | John Donne's Devotions | John Donne | ✅ done | 28 ch. |
| 254 | John Donne's Sermon at Paul's Cross | John Donne | ✅ done | 1 ch. |
| 255 | Josephus: The Complete Works | Flavius Josephus | ✅ **structural fix** | 372 ch. "CHAPTER N" reset across ~30 books (Antiquities I–XX, Wars, Against Apion); aligned to cached TOC and reprefixed "Antiquities, Book I · CHAPTER N" etc. (366 chapters), 0 remaining dups. |
| 256 | Kept for the Master's Use | F.R. Havergal | ✅ done | 16 ch. |
| 257 | Lectures on Revivals of Religion | C.G. Finney | ✅ done | 22 ch. |
| 258 | Lectures on the Acts of the Apostles | John Dick | ✅ done | 29 ch. |
| 259 | Lectures on the Doctrine of Election | A.C. Rutherford | ✅ done | 10 ch. |
| 260 | Lectures to Professing Christians | C.G. Finney | ✅ done | 23 ch. |
| 261 | Lenten Meditation | Mark Pasko | ✅ done | 4 ch. |
| 262 | Letters of Master John Bradford | John Bradford | ⚠️ done, **one blob** | 100k words in one chapter — source ThML has no per-letter divisions and no heading paragraphs in our text, so per-letter splitting isn't recoverable without deeper CCEL cross-reference (flagged; not attempted). Heading corrected; baseline applied. |
| 263 | Life of Dr Owen | Andrew Thomson | ✅ done | 6 ch. |
| 264 | Life of Master John Bradford | John Bradford | ✅ done | 4 ch. |

| 265 | Life of St. Declan of Ardmore | (tr.) | ✅ done | 2 ch. |
| 266 | Life of William Carey | George Smith | ✅ done | 17 ch. |
| 267 | Light and Peace | Quadrupani | ✅ done | 27 ch. |
| 268 | Light in the Dark Places | Augustus Neander | ✅ done | 26 ch. |
| 269 | Light, Life, and Love | W.R. Inge | ✅ done | 24 ch. |
| 270 | Lord, Teach Us To Pray | Alexander Whyte | ✅ done | 24 ch. |
| 271 | Love Enthroned | Daniel Steele | ✅ done | 23 ch. |
| 272 | Luther and Other Leaders of the Reformation | John Tulloch | ✅ done | 5 ch. |
| 273 | Luther's Little Instruction Book (Small Catechism) | Martin Luther | ✅ done | 1 ch. |
| — | Lyra Germanica (First & Second Series) | C. Winkworth | 🗑 **deleted ×2 (hymn policy)** | German hymn translations. |
| 274 | Martyrs Mirror | T.J. van Braght | ✅ **§22 split from CCEL** | Century sections baselined; dup "Twelfth Century" → (continued). The §22 "Old Book" 714k-word blob had no source divisions; recovered the martyr-account headers from the CCEL page (centered "NAME, A. D. YEAR" runs, incl. multi-line names), matched them into our clean text, and split into **332 martyr chapters** titled "Name (A.D. Year)". Book now 355 ch, largest 48k (a different section), 0 dups. |
| 275 | Matelda and the Cloister of Hell | Mechthild of Magdeburg (Bevan tr.) | ✅ done | 37 ch (mystical work, not a hymnal — kept). |
| 276 | Maxims of the Saints | Fénelon | ✅ done | 5 ch. |
| — | Meditating on Scripture with the Saints | Mark Pasko | 🗑 **deleted (copyright)** | Contemporary first-person devotional. Also retroactively removed his *Lenten Meditation* (#261) for the same reason. |
| 277 | Meditations and Discourses on the Glory of Christ | John Owen | ✅ done | 18 ch. |
| 278 | Meditations on the Life and Passion of Christ | John Tauler | ✅ done | 55 ch. |
| 279 | Meister Eckhart, Vol. 1 (Pfeiffer/Evans) | Eckhart | ⚠️ done, **very granular** | 1884 numbered "Section N" (source is fragmented to that level; no dups). Baselined as-is; grouping into Sermons/Tractates/Sayings would be a separate pass. |
| 280 | Meister Eckhart's Sermons | Eckhart | ✅ done | 8 ch. |
| — | Meister Eckharts Mystische Schriften | Eckhart | 🗑 **deleted (non-English)** | German-language text mislabeled 'en'; corpus is English-only. |

_Theology: **872** titles; 279 alphabetical done + 34 further patristics; shells resolved (13 deleted-as-shell, 17 deleted-as-hymn-policy, 4 deleted-as-copyright, 1 deleted-as-non-English, 7 CCEL-repaired, 2 locally repaired, 1 stage-rechaptered). One-blob flags remaining: Bradford Letters (#262), Kronstadt My Life in Christ (#290), Eckhart Vol.1 granularity (#279)._

| 281 | Memorial | Blaise Pascal | ✅ done | 1 ch (the famous brief text — complete, not a shell). |
| 282 | Messages From the Epistle of Hebrews | Handley Moule | ✅ done | 14 ch. |
| 283–284 | Messiah, Vols. 1–2 | John Newton | ✅ done | 26 + 25 ch. |
| 285 | Miscellaneous Pieces | John Bunyan | ✅ done | 4 ch. |
| 286 | Moody's Anecdotes and Illustrations | D.L. Moody | ✅ done | 61 ch. Numbered the 22 recurring "Gold" interlude sections → "Gold (1…22)". |
| 287 | Morning and Evening Prayers | Johann Habermann | ✅ done | 7 ch. |
| 288 | Morning and Evening | C.H. Spurgeon | ✅ done | 744 ch (daily readings). |
| 289 | Music in the History of the Western Church | Edward Dickinson | ✅ done | 14 ch. |
| 290 | My Life in Christ | John of Kronstadt | ⚠️ done, **2 big blobs** | English (Goulaeff tr.). Parts I & II are ~120k words each; the work is a stream of short reflections without chapter divisions — split not attempted (flagged). |
| 291 | Mysticism | Evelyn Underhill | ✅ done | 23 ch. |
| 292 | Natural Law in the Spiritual World | Henry Drummond | ✅ done | 17 ch. |
| 293 | Nature and Causes of Apostasy | John Owen | ✅ done | 14 ch. |
| 294 | Nature and Grace (Summa selections) | Thomas Aquinas | ✅ done | 105 ch. |
| 295 | Necessary Doctrine | Thomas Cranmer | ✅ done | 1 ch (short excerpt on justification). |
| 296 | New Evangelism and Other Papers | Henry Drummond | ✅ done | 7 ch. |
| 297 | Ninety-five Theses (Latin) | Martin Luther | ✅ done | 2 ch. |
| 298–324 | **NPNF full series** — Series 1 (vols 1–14) + Series 2 (vols 1–13), 27 volumes | Philip Schaff (ed.) | ✅ **series-wide dedup fix** | Built `scripts/requalify_npnf.py`: (1) re-aligns every chapter to its cached CCEL TOC and rebuilds the title as the full "Work · Book · Chapter" path (inserting the Book/Dialogue level the earlier patristics pass skipped); (2) pulls canonical numbers ("Letter XXIII", "Epistle IV", "Homily L") from the body for repeated same-recipient sections; (3) sequential "(n)" fallback. **0 duplicate titles across all 27 volumes**, headings ✓, 0 leaks, 0 residual spans. Idempotent. |

| (ANF) | Ante-Nicene Fathers, vols. 1–9 | Philip Schaff (ed.) | ✅ **series-wide dedup fix** | Same `requalify_npnf.py` treatment (they had the same latent multi-Book dups from the earlier pass — anf04 alone had 524). All 9 → 0 dups, headings ✓, 0 leaks, 0 spans. `--all` now covers ANF + both NPNF series. |

_Theology alphabetical march past the NPNF block (~333 done). **Entire ANF + NPNF patristic reference set (36 volumes) fine-deduped and navigable.**_

### Batch: "N/O" range (post-patristics)
| — | NT Song Database | Faith Alive | 🗑 **deleted (shell)** | 31-word empty song stub. |
| 325 | Of Communion with God the Father, Son and Holy Ghost | John Owen | ✅ **structural fix** | "Chapter I…" reset across 3 parts; prefixed "Part I/II/III · Chapter N" (Digressions → "Part II · Digression"). |
| 326 | Of God and His Creatures (Summa Contra Gentiles) | Aquinas | ✅ done | 384 ch. |
| 327 | Of Schism | John Owen | ✅ done | 21 ch. |
| 328 | Of Temptation | John Owen | ✅ done | 10 ch. |
| 329 | Of the Mortification of Sin in Believers | John Owen | ✅ done | 15 ch. |
| 330 | Old Testament Types and Teachings | H.W. Smith | ✅ done | 25 ch. |
| 331 | On Christian Doctrine | Augustine | ✅ done | 46 ch. |
| 332 | On Cleaving to God | Albert the Great | ✅ done | 17 ch. |
| 333 | On Keeping the Heart | John Flavel | ✅ done | 17 ch. |
| 334 | On Loving God | Bernard of Clairvaux | ✅ done | 15 ch. |
| 335 | On Religion: Speeches to Its Cultured Despisers | Schleiermacher (Oman tr.) | ✅ done | 7 ch. |
| 336 | On the Government of God | Salvian | ✅ done | 18 ch. |
| 337 | On the Incarnation of the Word | Athanasius | ✅ done | 9 ch. |
| 338 | Origen on Prayer | Origen | ✅ done | 20 ch. |
| 339 | Origin of the Four Gospels | Tischendorf | ✅ done | 1 ch. |
| 340 | Orthodox Daily Prayers | Anonymous | ✅ done | 10 ch (prayer book, kept). |
| 341 | Orthodoxy | G.K. Chesterton | ✅ done | 10 ch. |
| 342 | Our Daily Homily | F.B. Meyer | ✅ done | 241 ch. |
| 343 | Outlines of Moral Science | Archibald Alexander | ✅ done | 30 ch. |

_Theology: **871** titles; alphabetical march at "O" (~343 done)._

### Batch: "O/P" range
| 344 | Outspoken Essays | W.R. Inge | ✅ done | 12 ch. |
| 345 | Paley's Natural Theology | William Paley | ✅ done | 20 ch. |
| 346 | Paradise Lost | John Milton | ✅ done | 10 ch (books). |
| 347 | Paul Gerhardt as a Hymn Writer | T.B. Hewitt | ✅ done | 95 ch (English thesis/study of hymnody — kept per policy). |
| — | Paul Gerhardt's Spiritual Songs | Gerhardt (Kelly tr.) | 🗑 **deleted (hymn policy)** | Hymn-text collection. |
| 348 | Pensées | Blaise Pascal | ✅ done | 14 ch. |
| 349 | Pneumatologia (Discourse on the Holy Spirit) | John Owen | ✅ **dedup** | "Chapter I…" reset across 5 books; TOC-requalified to "Book · Chapter". 0 dups. |
| 350 | Pneumatologia: A Treatise of the Soul of Man | John Flavel | ✅ done | 10 ch. |
| 351 | Poema | John Owen | ✅ done | 1 ch (short complete piece). |
| 352 | Poems of St. Teresa | Teresa of Ávila | ✅ done | 5 ch (devotional poetry, not a hymnal — kept). |
| 353 | Power Through Prayer | E.M. Bounds | ✅ done | 20 ch. |
| 354 | Practical Discourses on Regeneration | Philip Doddridge | ✅ done | 9 ch. |
| 355 | Practical Mysticism | Evelyn Underhill | ✅ done | 11 ch. |
| 356 | Prayer and Praying Men | E.M. Bounds | ✅ done | 16 ch. |
| 357 | Prayer Availeth Much | T.M. Anderson | ✅ done | 16 ch. |
| 358 | Preface to the Letter of St. Paul to the Romans | Luther | ✅ done | 2 ch. |
| 359 | Primitive Christianity | William Penn | ✅ **dedup** | Chapters reset across 2 parts; TOC-requalified. |
| 360–361 | Private Thoughts Upon Religion / Upon a Christian Life | William Beveridge | ✅ done | 24 + 10 ch. |
| 362 | Proslogium; Monologium; Cur Deus Homo; Gaunilo | Anselm | ✅ **dedup** | Preface/Chapter reset across the 4 works; TOC-requalified to "Work · Chapter". 74→0 dups. |

_Theology: **870** titles; march at "P" (~362 done)._

### Batch: "P/Q/R" range
| 363 | Pseudepigrapha | W.J. Deane | ✅ done | 11 ch. |
| 364 | Purpose in Prayer | E.M. Bounds | ✅ done | 13 ch. |
| 365–372 | Quiet Talks (Jesus / Following the Christ / John's Gospel / Power / Prayer / Service / Crowned Christ / World Winners) | S.D. Gordon | ✅ done | 8 volumes, PD (early 1900s). |
| — | Reflections on the Christian Faith | Mark Pasko | 🗑 **deleted (copyright)** | Contemporary author. |
| 373 | Religio Medici | Thomas Browne | ✅ dedup (TOC) | 8 ch, 0 dups. |
| 374 | Religion and Theology (sermon) | John Tulloch | ✅ done | 1 ch. |
| 375 | Religious Affections | Jonathan Edwards | ✅ done | 29 ch. |
| — | Religious Poems | Harriet Beecher Stowe | 🗑 **deleted (shell)** | Only title page + contents survived; the verse poems were dropped. |
| 376 | Revelations of Divine Love | Julian of Norwich | ✅ dedup (TOC) | 70 ch, 0 dups. |
| 377 | Revival Addresses | R.A. Torrey | ✅ done | 20 ch. |
| 378 | Robinson Crusoe | Daniel Defoe | ✅ done | 27 ch. |
| — | Romans Verse-by-Verse | William R. Newell | 🗑 **deleted (copyright)** | 1938 Moody Press work (references 1935 events); modern copyright. |
| 379 | Ruysbroeck | Evelyn Underhill | ✅ done | 9 ch. |

_Theology: **867** titles; march at "R" (~379 done)._

### Batch: "S" range (sermons)
| 380 | Sacramental Discourses | John Owen | ✅ done | 28 ch. |
| — | Sacred Hymns From the German | F.E. Cox | 🗑 **deleted (hymn policy)** | Hymn-text collection. |
| 381 | Santa Teresa, An Appreciation | Alexander Whyte | ✅ done | 16 ch. |
| 382 | Scottish Confession of Faith (1560) | Anonymous | ✅ done | 27 ch. |
| 383 | Scripture and Truth | Benjamin Jowett | ✅ done | 8 ch. |
| 384 | Select Sermons | Jonathan Edwards | ✅ done | 20 ch. |
| 385 | Selected Sermons of George Whitefield | Whitefield | ✅ done | 59 ch. |
| 386 | Selected Sermons of Schleiermacher | Schleiermacher | ✅ done | 27 ch. |
| 387 | Selections from the Writings of Kierkegaard | Kierkegaard | ✅ done | 6 ch (PD tr.). |
| 388 | Sermon Preached to the Lords (Easter) | John Donne | ✅ done | 1 ch. |
| 389 | Sermons and Tracts | John Bradford | ✅ done | 7 ch. |
| 390 | Sermons by Hugh Latimer | Hugh Latimer | ✅ done | 21 ch. |
| 391 | Sermons for the New Life | Horace Bushnell | ✅ done | 23 ch. |
| 392 | Sermons on Faith and Doctrine | Benjamin Jowett | ✅ done | 21 ch. |
| 393 | Sermons on Gospel Themes | C.G. Finney | ✅ dedup (TOC) | 40 ch, 0 dups. |
| 394 | Sermons on Proverbs | C.H. Spurgeon | ✅ done | 44 ch. |
| 395 | Sermons on Several Occasions | John Wesley | ✅ dedup (TOC) | 142 ch, 0 dups. |
| 396–398 | Sermons Preached Upon Several Occasions, vols. 1–3 | Robert South | ✅ done (vol.1 deduped) | 23 + 21 + 17 ch. |

_Theology: **866** titles; march at "S" (~398 done)._

### Batch: "S" range (cont.)
| 399–402 | Sermons Preached Upon Several Occasions, vols. 4–7 | Robert South | ✅ done | 21/25/22/21 ch. |
| 403–406 | Sermons, vols. 1–4 | Henry Edward Manning | ✅ done | 26/20/23/22 ch. |
| 407 | Several Discourses Concerning Acceptance | Benjamin Hoadly | ✅ done | 18 ch. |
| 408 | Several Practical Cases of Conscience | John Owen | ✅ done | 14 ch. |
| 409 | Short Papers on Church History | Andrew Miller | ✅ done | 18 ch. |
| 410 | Sketches of Jewish Social Life | Alfred Edersheim | ✅ done | 21 ch. |
| 411 | Smith's Bible Dictionary | William Smith | ✅ done | 25 A–Z sections. |
| 412 | Some Facts of Religion and of Life | John Tulloch | ✅ done | 14 ch. |
| 413 | Some Letters of Saint Bernard | Bernard of Clairvaux | ✅ done | 77 ch. |
| 414 | Song of Songs (Explanation) | Madame Guyon | ✅ done | 8 ch. |
| — | Songs and Hymns of the Earliest Greek Christian Poets | Chatfield | 🗑 **deleted (hymn policy)** | Hymn/song collection. |
| 415 | Spirit of Love | William Law | ✅ done | 4 ch. |
| 416 | Spiritual Progress | Guyon / Fénelon | ✅ done | 101 ch. |
| 417 | Spiritual Torrents | Madame Guyon | ✅ done | 11 ch. |

_Theology: **865** titles; march at "S" (~417 done)._

### Batch: "S" range — Spurgeon series
| 418 | Spiritual Works of Louis of Blois | Louis of Blois | ✅ dedup (TOC) | 69 ch, 0 dups. |
| 419–437 | Spurgeon's Sermons, Vols. 1–19 | C.H. Spurgeon | ✅ done | ~50–85 sermons each (PD). Vol. 4 had 1 TOC-dup, deduped. NONENG flags on several vols are false positives (Latin/Greek quotations). |

| 438–457 | Spurgeon's Sermons, Vols. 20–39 | C.H. Spurgeon | ✅ done | ~52–69 sermons each (PD). All clean. |

| 458–477 | Spurgeon's Sermons, Vols. 40–59 | C.H. Spurgeon | ✅ done | ~51–53 sermons each (PD). All clean. |

| 478–481 | Spurgeon's Sermons, Vols. 60–63 | C.H. Spurgeon | ✅ done | PD; completes the 63-volume set. |
| 482 | St. Anselm's Book of Meditations | Anselm | ✅ done | 21 ch. |
| 483 | St. Bernard's Life of St. Malachy | Bernard of Clairvaux | ✅ done | 15 ch. |
| 484 | St. Dionysius of Alexandria | C.L. Feltoe | ✅ done | 42 ch. |
| — | St. Ephraim's Prose Refutations | Ephraim | 🗑 **deleted (redundant shell)** | Preface-only fragment; full text already present as the Pearse edition (#167–168). |
| 485 | St. Paul the Traveler and the Roman Citizen | W.M. Ramsay | ✅ done | 18 ch. |
| 486 | Stones Rolled Away | Henry Drummond | ✅ done | 8 ch. |
| 487 | Story of a Soul | Thérèse of Lisieux | ✅ done | 45 ch. |
| 488 | Studies in the Book of Common Prayer | H.M. Luckock | ✅ done | 13 ch. |
| 489 | Summa Theologica | Thomas Aquinas | ✅ done | 1313 ch, 2.53M words. 0 dups. |
| 490 | Sweet Singers of Wales | H. Elvet Lewis | ✅ done | 32 ch (prose study of Welsh hymnody — kept per policy). |
| 491 | Swiss Family Robinson | J.D. Wyss | ✅ done | 18 ch. |
| 492 | Synod of Dort (Canons) | Anonymous | ✅ done | 5 ch. |
| 493 | Synthetic Bible Studies | J.M. Gray | ✅ done | 64 ch. |
| — | Systematic Theology; Summary of Christian Doctrine | Louis Berkhof | 🗑 **deleted ×2 (copyright)** | 1932/1938/1949 Eerdmans works — modern copyright. (His 1915 *Intro to the NT*, #249, stays — PD.) |
| 494 | Systematic Theology — Index | Charles Hodge | ✅ done | Index vol completing Hodge's 3-vol set (all PD). |

_Theology: **862** titles; march at "S/Sy" (~494 done). Spurgeon's 63-vol sermon set complete._

### Batch: "Sy/T" range
| 495–497 | Systematic Theology, Vols. I–III | Charles Hodge | ✅ done (I & III deduped via TOC) | 89/92/85 ch. |
| 498 | Systematic Theology [1878] | C.G. Finney | ✅ done | 53 ch (PD). |
| 499 | Table Talk | Martin Luther | ✅ done | 48 ch. |
| 500 | The 1677/89 London Baptist Confession | Anonymous | ✅ done | 45 ch. |
| 501 | The Adornment of the Spiritual Marriage | Ruysbroeck | ✅ done | 127 ch. |
| 502 | The Almost Christian Discovered | Matthew Mead | ✅ done | 9 ch. |
| 503 | The Analogy of Religion | Joseph Butler | ✅ dedup (TOC) | 20 ch, 0 dups. |
| 504 | The Antichrist | A.W. Pink | ✅ done | 19 ch (1923, PD). |
| 505 | The Apostolic Fathers | J.B. Lightfoot | ✅ done | 15 ch (each father a chapter; Hermas = the 74k one, one continuous work). Fixed "fo"→"of" typo. |
| 506 | The Apostolic Fathers: I Clement etc. (Loeb) | Kirsopp Lake | ✅ done | 26 ch (1912, PD). |
| 507 | The Art of Divine Contentment | Thomas Watson | ✅ done | 17 ch (previously CCEL-repaired). |
| 508 | The Autobiography of St. Ignatius Loyola | Ignatius | ✅ done | 11 ch. |
| 509 | The Backslider in Heart | C.G. Finney | ✅ done | 1 ch. |
| 510 | The Beatitudes | Thomas Watson | ✅ done | 23 ch. |
| 511–512 | The Beginnings of Christianity, Vols. 1–2 | Paul Wernle | ✅ done | 22 + 13 ch (1903 ET, PD). |
| 513 | The Book of Jasher | Anonymous | ✅ done | 92 ch (previously CCEL-repaired). |
| 514 | The Canon of the Old and New Testaments | Archibald Alexander | ✅ done | 34 ch. |

### Batch: "The C" range
| 515 | The Causes and Danger of Slighting Christ | Richard Baxter | ✅ done | 6 ch. |
| 516 | The Causes of the Corruption of the Traditional Text | J.W. Burgon | ✅ done | 20 ch. |
| 517 | The Celestial Hierarchy | Dionysius | ✅ done | 15 ch. |
| 518 | The Cell of Self-Knowledge | E.G. Gardner (ed.) | ✅ done | 19 ch. |
| 519 | The Change of the Sabbath | Thomas Shepard | ✅ done | 1 ch. |
| 520 | The Character of Jesus | Horace Bushnell | ✅ done | 1 ch. |
| 521 | The Christ of History | John Young | ✅ dedup (TOC) | 19 ch. |
| 522 | The Christian Ecclesia | F.J.A. Hort | ✅ done | 14 ch. |
| 523 | The Christian Year | John Keble | ✅ done | 111 ch (devotional poetry; previously CCEL-repaired — kept). |
| 524 | The Christian's Great Interest | William Guthrie | ✅ done | 19 ch. |
| 525 | The Christian's Secret of a Happy Life | H.W. Smith | ✅ done | 23 ch. |
| 526 | The Church and the Ministry in the Early Centuries | T.M. Lindsay | ✅ done | 11 ch. |
| 527 | The Church in Rome in the First Century | George Edmundson | ✅ done | 16 ch. |
| 528 | The Cloud of Unknowing | Anonymous | ✅ done | 80 ch. |
| 529 | The Colloquies of Erasmus, Vol. 1 | Erasmus | ✅ done | 40 ch. |
| 530–531 | The Complete Works of Menno Simons, Vols. 1–2 | Menno Simons | ✅ dedup (TOC) | 53 + 79 ch, 0 dups. |
| 532–534 | The Complete Works of Thomas Manton, Vols. 1–3 | Thomas Manton | ✅ done (vol.1 deduped) | 32/36/30 ch. |

### Batch: "The C/D" range
| 535–537 | The Complete Works of Thomas Manton, Vols. 4/5/8 | Thomas Manton | ✅ done (vol.5 deduped) | vol.4 = James commentary (Ch I = 99k, his exposition of James 1). |
| 538 | The Conferences of John Cassian | John Cassian | ✅ dedup (TOC) | 443 ch, 0 dups. |
| 539 | The Confession of St. Patrick | Patrick | ✅ done | 10 ch. |
| 540 | The Confessions of Saint Augustine | Augustine | ✅ done | 211 ch. |
| 541 | The Confutatio Pontificia | Anonymous | ✅ done | 3 ch. |
| 542 | The Consolation of Philosophy | Boethius | ✅ done | 9 ch. |
| 543 | The Crook in the Lot | Thomas Boston | ✅ done | 3 ch. |
| 544 | The Crowd is Untruth | Kierkegaard | ✅ done | 1 ch. |
| 545 | The Death of Christ | James Denney | ✅ done | 9 ch (1902, PD). |
| 546 | The Death of Death in the Death of Christ | John Owen | ✅ done | 35 ch. |
| 547 | The Deeper Christian Life | Andrew Murray | ✅ done | 8 ch. |
| 548 | The Defendant | G.K. Chesterton | ✅ done | 18 ch. |
| 549 | The Deity of Christ | Frank Bartleman | ✅ done | 7 ch. |
| 550 | The Demonstration of the Apostolic Preaching | Irenaeus | ✅ done | 7 ch. |
| 551 | The Devotions of Bishop Andrewes | Lancelot Andrewes | ✅ done | 14 ch. |
| 552 | The Devotions of Saint Anselm | Anselm | ✅ done | 45 ch. |
| 553 | The Divine Inspiration of the Bible | A.W. Pink | ✅ done | 15 ch (1917, PD). |
| 554 | The Doctrine of Justification | A.W. Pink | ✅ done | 10 ch. |

### Batch: "The D/E" range
| 555 | The Doctrine of Justification by Faith | John Owen | ✅ done | 39 ch. |
| 556 | The Doctrine of the Saints' Perseverance | John Owen | ✅ done | 21 ch. |
| 557 | The Dolorous Passion of Our Lord | A.C. Emmerich | ✅ dedup (TOC) | 80 ch. |
| 558 | The Doré Bible Gallery | Gustave Doré | ✅ dedup (TOC) | 6 ch (engraving gallery). |
| 559 | The Dream of Gerontius | J.H. Newman | ✅ done | 7 ch. |
| 560 | The Duty of Pastors and People Distinguished | John Owen | ✅ done | 11 ch. |
| 561 | The Early Years of Christianity | E. de Pressensé | ✅ done | 48 ch. |
| 562 | The Epistle of St James (Greek Text) | F.J.A. Hort | ✅ done | 6 ch. |
| 563 | The Epistle to the Hebrews | B.F. Westcott | ✅ done | 26 ch. |
| 564 | The Epistles of St. Paul (Jowett) | Benjamin Jowett | ✅ done | 11 ch. |
| 565 | The Epistles of St. Peter | J.H. Jowett | ✅ done | 29 ch. |
| 566 | The Epistles of St. Peter and St. Jude | Luther | ✅ dedup (TOC) | 12 ch. |
| 567 | The Essentials of Mysticism | Evelyn Underhill | ✅ done | 14 ch (1920, PD). |
| 568 | The Essentials of Prayer | E.M. Bounds | ✅ done | 14 ch. |
| 569 | The Everlasting Man | G.K. Chesterton | ✅ done | 17 ch (1925, PD). |
| 570 | The Evidences of Christianity (Doddridge) | Philip Doddridge | ✅ done | 3 ch. |
| 571 | The Evidences of the Christian Religion (Addison) | Joseph Addison | ✅ done | 21 ch. |
| 572 | The Evidences of the Christian Religion (Alexander) | A. Alexander | ✅ done | 12 ch. |
| 573 | The Existence of God | Fénelon | ✅ done | 93 ch. |
| 574 | The Expositor's Bible: Colossians & Philemon | Alexander Maclaren | ✅ done | 32 ch. |

### Batch: "The Expositor's Bible" series
| 575–592 | The Expositor's Bible (Ezra–Nehemiah–Esther, Acts I–II, Daniel, Deuteronomy, Ecclesiastes [deduped], Exodus, Ezekiel, Genesis [Dods], Isaiah I–II, Jeremiah II, Job, Joshua, Leviticus, Numbers, Proverbs, Revelation, Minor Prophets I) | various (PD) | ✅ done | 18 volumes baselined. |
| — | The Expositor's Bible: Genesis (bare-title copy) | Marcus Dods | 🗑 **deleted (duplicate)** | Same 134k-word Dods Genesis as the descriptive-title copy (`dods-expositor1`); kept the better one. |

| 593–612 | The Expositor's Bible (Chronicles [Bennett], Romans, Ephesians, Galatians, Hebrews, Philippians, Epistles of John, Peter, Thessalonians, 1 Kings, 1 Corinthians, James & Jude, Luke, Mark, John I–II, Matthew, Pastorals, Jeremiah I, Psalms I) | various (PD) | ✅ done | 20 volumes baselined. |

### Batch: "The Ex/F/G" range
| 613–618 | The Expositor's Bible: Psalms II–III, 2 Kings, 2 Samuel, 2 Corinthians, Song of Solomon & Lamentations | various (PD) | ✅ done | Closes the Expositor's Bible run. |
| 619 | The Fire of Love | Richard Rolle | ✅ dedup (TOC) | 61 ch, 0 dups. |
| 620 | The First Blast of the Trumpet | John Knox | ✅ done | 4 ch. |
| 621 | The Following of Christ | John Tauler | ✅ done | 20 ch. |
| 622 | The Formulae of St. Eucherius | Eucherius | ✅ done | 11 ch. |
| 623 | The Founders of the New Devotion | Thomas à Kempis | ✅ dedup (TOC) | 61 ch. |
| 624 | The Fountain of Life Opened Up | John Flavel | ✅ done | 44 ch. |
| 625 | The Four-Fold Gospel | McGarvey & Pendleton | ✅ done | 186 ch. |
| 626 | The Friend on the Road | J.H. Jowett | ✅ done | 59 ch. |
| 627 | The General Epistles: James, Peter, Jude | James Moffatt | ✅ dedup (TOC) | 9 ch (1928, PD). |
| 628 | The General Menaion | Anonymous | ✅ done | 29 ch (Orthodox service book — kept). |
| 629 | The Genesis to Revelation Bible Commentary | W.M. Groom | ✅ done | 61 ch (no copyright signal). |
| 630 | The German Pulpit | R. Baker (ed.) | ✅ done | 21 ch (English trs. of German sermons). |
| 631 | The God of All Comfort | H.W. Smith | ✅ done | 17 ch. |
| 632 | The Godhood of God | A.W. Pink | ✅ done | 5 ch. |

### Batch: "The G/H/I" range
| 633 | The Government of the Tongue | Richard Allestree | ✅ done | 14 ch. |
| 634 | The Grace and Duty of Being Spiritually Minded | John Owen | ✅ done | 22 ch. |
| 635 | The Greatest Thing in the World | Henry Drummond | ✅ dedup (TOC) | 19 ch. |
| 636 | The Grounds and Reasons of Christian Regeneration | William Law | ✅ done | 1 ch. |
| 637 | The Grounds of Faith | H.E. Manning | ✅ done | 4 ch. |
| 638 | The Guide for the Perplexed | Maimonides | ✅ dedup (TOC) | 189 ch (Friedländer tr., PD). |
| 639 | The Heidelberg Catechism | Anonymous | ✅ done | 4 ch. |
| 640 | The History and Life of Tauler | S. Winkworth | ✅ done | 41 ch. |
| 641 | The History of the Reformation (Scotland) | John Knox | ✅ done | 49 ch. |
| 642 | The Holy Rule of St. Benedict | Benedict | ✅ done | 74 ch. |
| 643 | The Holy War | John Bunyan | ✅ done | 21 ch. |
| 644 | The Hymn as Literature | J.B. Reeves | ✅ done | 11 ch (1924 prose study of hymnody — kept). |
| — | The Hymnal (Protestant Episcopal, 1916) | Anonymous | 🗑 **deleted (hymnal)** | Hymn-text collection. |
| 645 | The Hymns of Methodism in their Literary Relations | Henry Bett | ✅ done | 7 ch (prose study — kept). |
| — | The Hymns of Prudentius | Prudentius | 🗑 **deleted (hymn collection)** | Verse hymn texts. |
| — | The Hymns of Wesley and Watts | B.L. Manning | 🗑 **deleted (copyright)** | 1942, references 1933 events. |
| 646 | The Idea of the Holy | Rudolf Otto | ✅ done | 24 ch (1923 ET, PD). |
| 647 | The Ideal Life | Henry Drummond | ✅ done | 17 ch. |
| 648 | The Imitation of Christ | Thomas à Kempis | ✅ done | 105 ch. |
| 649 | The Inner Way | John Tauler | ✅ done | 42 ch. |

### Batch: "The I/J/K/L" range
| 650 | The Interior Castle | Teresa of Ávila | ✅ done | 31 ch. |
| 651 | The Johannine Writings | Paul Schmiedel | ✅ dedup (TOC) | 102 ch. |
| 652 | The Journal of John Wesley | John Wesley | ✅ dedup (TOC) | 264 ch. |
| 653 | The Journal of John Woolman | John Woolman | ✅ done | 15 ch. |
| 654 | The Keyes of the Kingdom of Heaven | John Cotton | ✅ done | 7 ch. |
| 655 | The Kneeling Christian | "An Unknown Christian" | ✅ done | 13 ch (1924, PD). |
| 656 | The Large Catechism | Martin Luther | ✅ done | 12 ch. |
| 657 | The Last Twelve Verses of Mark | J.W. Burgon | ✅ done | 24 ch. |
| 658 | The Law and the Saint | A.W. Pink | ✅ done | 3 ch. |
| 659 | The Letters to the Seven Churches | W.M. Ramsay | ✅ done | 32 ch. |
| 660 | The Life and Death of Mr Badman | John Bunyan | ✅ done | 3 ch. |
| 661 | The Life and Doctrine of St. Catherine of Genoa | Catherine of Genoa | ✅ dedup (TOC) | 91 ch. |
| 662 | The Life and Times of Jesus the Messiah | Alfred Edersheim | ✅ done | 127 ch, 771k words. |
| 663 | The Life of Blessed Henry Suso | Suso | ✅ done | 56 ch. |
| 664 | The Life of David | Alexander Maclaren | ✅ done | 16 ch. |
| 665 | The Life of God in the Soul of Man | Henry Scougal | ✅ done | 3 ch. |
| 666 | The Life of Jesus Christ | Augustus Neander | ✅ dedup (TOC) | 181 ch. |
| 667 | The Life of John Wesley Redfield | J.G. Terrill | ✅ done | 67 ch. |
| 668 | The Life & Rule of St. Benedict (Gregory's Dialogues II) | Gregory the Great | ✅ dedup (TOC) | 115 ch. |
| 669 | The Life of St. Teresa of Jesus | Teresa of Ávila | ✅ done | 56 ch. |

### Batch: "The L/M/N" range
| 670 | The Life of the Blessed Virgin Mary | A.C. Emmerich | ✅ done | 22 ch. |
| 671 | The Life of the late Rev. Mr. John Flavel | Flavel | ✅ done | 1 ch. |
| 672 | The Life of the Spirit and the Life of To-day | Evelyn Underhill | ✅ done | 11 ch (1922). |
| 673 | The Limits of Religious Thought | H.L. Mansel | ✅ done | 17 ch. |
| 674 | The Little Flowers of St. Francis | Ugolino | ✅ done | 80 ch. |
| 675 | The Little Treasure of Prayers | Anonymous | ✅ done | 101 ch. |
| 676 | The Lively Oracles Given to Us | Richard Allestree | ✅ done | 10 ch. |
| 677 | The Lord's Prayer | Thomas Watson | ✅ done | 7 ch. |
| 678 | The Lord's Table | Andrew Murray | ✅ done | 12 ch. |
| 679 | The Ascent of Man (Lowell Lectures) | Henry Drummond | ✅ done | 15 ch. |
| 680 | The Marrow of Modern Divinity | Edward Fisher | ✅ done | 24 ch. |
| 681 | The Master's Indwelling | Andrew Murray | ✅ done | 13 ch. |
| 682 | The Meaning of Prayer | H.E. Fosdick | ✅ dedup (TOC) | 25 ch (1912/1915, PD). |
| 683 | The Method of Grace | John Flavel | ✅ done | 37 ch. |
| 684 | The Mind's Road to God | Bonaventure | ✅ done | 11 ch. |
| 685 | The Miracles of Jesus | Karl Beth | ✅ done | 3 ch. |
| 686 | The Monkey who Wouldn't Kill | Henry Drummond | ✅ done | 3 ch. |
| 687 | The Nature of the Atonement | J.M. Campbell | ✅ dedup (TOC) | 17 ch. |
| 688 | The Nature, Power, Deceit… of Indwelling Sin | John Owen | ✅ done | 18 ch. |
| 689 | The Necessity of Prayer | E.M. Bounds | ✅ done | 14 ch. |

### Batch: "The N/O/P" range
| 690 | The Necessity of Regeneration | Stephen Charnock | ✅ done | 1 ch. |
| 691 | The New Life | Andrew Murray | ✅ done | 52 ch. |
| 692–696 | The New Schaff-Herzog Encyclopedia, vols. 1/2/9/13/13a | Schaff/Jackson (eds.) | ⚠️ done, **letter-blobs** | PD reference set (incomplete, 5 of 13 vols). Each letter is one huge chapter (vol. 1 "A" = 413k words); TOC has no article-level structure, so per-article split would need CCEL-header detection (flagged, like Martyrs Mirror — not attempted). |
| 697 | The New Testament Commentary Vol. III: John | B.W. Johnson | ✅ dedup (TOC) | 71 ch. |
| 698 | The People's New Testament | B.W. Johnson | ✅ dedup (TOC) | 259 ch. |
| 699 | The Oratory of the Faithful Soul | Louis of Blois | ✅ done | 24 ch. |
| 700 | The Passion for Souls | J.H. Jowett | ✅ done | 7 ch. |
| — | The Passion-Hymns of Iceland | Pilcher (tr.) | 🗑 **deleted (hymn collection)** | |
| — | The Pearl | Ephraim | 🗑 **deleted (32w shell)** | |
| 701 | The Person and Work of the Holy Spirit | R.A. Torrey | ✅ done | 22 ch. |
| 702 | The Person of Christ | Philip Schaff | ✅ done | 41 ch. |
| 703 | The Philosophy of Revelation | Herman Bavinck | ✅ done | 10 ch (1909, PD). |
| 704 | The Pilgrim's Progress | John Bunyan | ✅ dedup (TOC) | 20 ch. |
| — | The Poetical Works of John and Charles Wesley | Wesley | 🗑 **deleted (hymn shell)** | 3.6k-word Wesley hymn/poetry shell. |
| 705 | The Practice of Piety | Lewis Bayly | ✅ done | 42 ch. |
| 706 | The Practice of the Presence of God | Brother Lawrence | ✅ done | 18 ch. |

### Batch: "The P/R/S" range
| 707 | The Provincial Letters | Blaise Pascal | ✅ done | 20 ch. |
| — | The Psalms and Hymns of Isaac Watts | Watts | 🗑 **deleted (hymn collection)** | |
| 708 | The Pulpit of the Reformation | John Welch | ✅ done | 6 ch. |
| 709 | The Reality of Prayer | E.M. Bounds | ✅ done | 15 ch. |
| 710 | The Redeemer's Return | A.W. Pink | ✅ done | 83 ch (1918, PD). |
| — | The Reformed Doctrine of Predestination | Loraine Boettner | 🗑 **deleted (copyright)** | 1932 Eerdmans (author d. 1990). |
| 711 | The Reformed Pastor | Richard Baxter | ✅ dedup (TOC) | 18 ch. |
| 712 | The Rent Veil | Horatius Bonar | ✅ done | 13 ch. |
| 713 | The Revision Revised | J.W. Burgon | ✅ done | 28 ch. |
| 714 | The Rise and Progress of Religion in the Soul | Philip Doddridge | ✅ done | 31 ch. |
| 715 | The Romance of M. Renan | Philip Schaff | ✅ dedup (TOC) | 4 ch. |
| 716 | The Saints' Everlasting Rest | Richard Baxter | ✅ done | 18 ch. |
| 717 | The Scale (or Ladder) of Perfection | Walter Hilton | ✅ dedup (TOC) | 74 ch (previously locally repaired; now deduped). |
| 718 | The School of Calvary | J.H. Jowett | ✅ done | 7 ch. |
| 719 | The School of Obedience | Andrew Murray | ✅ done | 10 ch. |
| — | The Scriptural Expositions of Dr. Neander (umbrella) | Neander | 🗑 **deleted (21w stub)** | Empty stub; the real expositions are the separate Phil./James/1 John volumes. |
| 720–722 | The Scriptural Expositions of Dr. Neander: Philippians / James / 1 John | Augustus Neander | ✅ done | 3/6/4 ch. |
| 723 | The Secret of Guidance | F.B. Meyer | ✅ done | 9 ch. |

### Batch: "The Se/So/Sp/St/Sy" range
| 724 | The Sermons of John Owen | John Owen | ✅ dedup (TOC) | 87 ch. |
| 725 | The Silver Lining | J.H. Jowett | ✅ done | 26 ch. |
| 726 | The Sinlessness of Jesus | Carl Ullmann | ✅ dedup (TOC) | 32 ch. |
| 727 | The Six Enneads | Plotinus | ✅ done | 54 ch. |
| 728 | The Smalcald Articles | Luther | ✅ done | 4 ch. |
| 729 | The Snares of the Devil | John Gerson | ✅ done | 3 ch. |
| 730 | The Song of Angels | Walter Hilton | ✅ done | 1 ch. |
| 731 | The Soul of Prayer | P.T. Forsyth | ✅ done | 8 ch. |
| — | The Southern Harmony | William Walker | 🗑 **deleted (shape-note tunebook)** | Hymn/tune collection. |
| 732 | The Sovereignty of God | A.W. Pink | ✅ done | 19 ch (Pink's PD text; 1949 is Herendeen's publisher foreword). |
| 733 | The Spirit of Prayer | William Law | ✅ done | 5 ch. |
| 734 | The Spiritual Exercises of St. Ignatius | Ignatius Loyola | ✅ done | 17 ch. |
| 735 | The Spiritual Guide | Miguel de Molinos | ✅ dedup (TOC) | 67 ch. |
| 736 | The Story of Our Hymns | E.E. Ryden | ✅ done | 84 ch (1930 prose study of hymnody — kept, PD). |
| 737 | The Story of the Other Wise Man | Henry Van Dyke | ✅ done | 6 ch. |
| 738 | The Sufferings of Christ | George Griffin | ✅ done | 28 ch. |
| 739 | The Superstition of Divorce | G.K. Chesterton | ✅ done | 9 ch. |
| 740–741 | The System of Doctrines, Vols. 1–2 | Samuel Hopkins | ✅ done | 17 + 17 ch. |
| 742 | The Temple: Its Ministry and Services | Alfred Edersheim | ✅ done | 20 ch. |

### Batch: "The T/U/V/W" range
| 743 | The Ten Commandments | Thomas Watson | ✅ done | 23 ch. |
| 744 | The Theological Tractates | Boethius | ✅ done | 7 ch. |
| 745 | The Theology of Schleiermacher | George Cross | ✅ done | 12 ch (1911). |
| 746 | The Three Additions to Daniel | W.H. Daubney | ✅ dedup (TOC) | 43 ch. |
| — | The Treasury of Sacred Song | F.T. Palgrave | 🗑 **deleted (sacred-verse anthology)** | |
| 747 | The Trinity is One God | Boethius | ✅ done | 3 ch. |
| 748 | The True Vine | Andrew Murray | ✅ dedup (TOC) | 31 ch. |
| 749 | The Truth of the Christian Religion | Hugo Grotius | ✅ done | 109 ch. |
| 750 | The Tryal & Triumph of Faith | Samuel Rutherford | ✅ done | 27 ch. |
| 751 | The Two Covenants | Andrew Murray | ✅ done | 25 ch. |
| 752 | The Upper Room | J.C. Ryle | ✅ dedup (TOC) | 24 ch. |
| 753 | The Vicarious Sacrifice | Horace Bushnell | ✅ done | 19 ch. |
| 754 | The Way Into the Holiest | F.B. Meyer | ✅ done | 36 ch. |
| 755 | The Way of Peace | James Allen | ✅ done | 7 ch. |
| 756 | The Way of Perfection | Teresa of Ávila | ✅ done | 47 ch. |
| — | The WAY to CHRIST (Behmen) | Böhme | 🗑 **deleted (duplicate)** | Identical to the Boehme copy; kept the better-titled one. |
| 757 | The Way to Christ | Jakob Böhme | ✅ dedup (TOC) | 14 ch. |
| 758 | The Way to Divine Knowledge | William Law | ✅ done | 3 ch. |
| 759 | The Weapon of Prayer | E.M. Bounds | ✅ done | 12 ch. |
| 760 | The Westminster Larger Catechism | Anonymous | ✅ done | 8 ch. |

### Batch: "The W(estminster)/Whole Works" range
| 761 | The Westminster Shorter Catechism | Anonymous | ✅ done | 1 ch. |
| 762–765 | The Whole Works of Rev. John Howe, Vols. 5–8 | John Howe | ✅ done | 47/43/57/47 ch. |
| 766 | The Work of Christ | P.T. Forsyth | ✅ done | 9 ch (1910). |
| 767 | The Work of the Holy Spirit | Abraham Kuyper | ✅ dedup (TOC) | 112 ch (1900 ET, PD). |
| 768–774 | The Works of Dr. John Tillotson, Vols. 4–10 | John Tillotson | ✅ done (vols. 4 & 10 deduped) | 7 volumes. |
| — | The Works of Dr. John Tillotson (tillotson08/09/10) | Tillotson | 🗑 **deleted ×3 (duplicates)** | Redundant copies of works08/09/10 under a second naming scheme. |
| 775–777 | The Works of James Arminius, Vols. 1–3 | James Arminius | ✅ done | 88/118/40 ch. |

### Batch: "The Works…/Th/Ti" range
| 778 | The Works of John Knox, Vol. 1 | John Knox | ✅ done | 23 ch. |
| 779–780 | The Works of Jonathan Edwards, Vols. 1–2 | Jonathan Edwards | ✅ dedup (TOC) | 302 + 215 ch, 1.42M words each. |
| 781 | The Works of Philo Judaeus | Philo | ✅ dedup (TOC) | 67 ch. |
| 782–784 | The Works of Thomas Manton, Vols. 6/7/20 | Thomas Manton | ✅ done | 53/50/47 ch. |
| — | The Works of Thomas Manton, Vol. 6 (manton_thomas) | Manton | 🗑 **deleted (duplicate)** | Identical to manton-manton06. |
| 785 | The Works of Thomas Shepard | Thomas Shepard | ✅ dedup (TOC) | 30 ch. |
| 786 | Theism | John Tulloch | ✅ done | 34 ch. |
| 787 | Theologia Germanica | Anonymous | ✅ done | 57 ch. |
| 788 | Theological Essays of Benjamin Jowett | Benjamin Jowett | ✅ done | 7 ch. |
| — | Theological Essays… (jowett-theological) | mislabeled | 🗑 **deleted (dup)** | Mislabeled copy of J.H. Jowett's *Silver Lining* (#725). |
| 789 | Theses Theologicae / Apology (Quakers) | Robert Barclay | ✅ done | 22 ch. |
| 790 | Things That Matter Most | J.H. Jowett | ✅ done | 35 ch. |
| 791 | Thomas Boston (life) | Anonymous | ✅ done | 1 ch (short bio, kept). |
| 792 | Three Friends of God | Frances Bevan | ✅ done | 61 ch. |
| — | Thy Sea is Great… | Henry Van Dyke | 🗑 **deleted (186w hymn shell)** | |
| 793 | Till He Come | C.H. Spurgeon | ✅ done | 22 ch. |
| 794 | Tithing | A.W. Pink | ✅ done | 2 ch. |

### Batch: "To/Tr/Tw/U/V/W" range
| 795 | To Be Near Unto God | Abraham Kuyper | ✅ done | 110 ch. |
| 796 | To My Younger Brethren | Handley Moule | ✅ done | 14 ch. |
| 797 | Torrey's New Topical Textbook | R.A. Torrey | ✅ done | 24 ch. |
| — | Touching Incidents and Remarkable Answers to Prayer | S.B. Shaw | 🗑 **deleted (593w shell)** | Only the intro survived; anthology dropped. |
| 798 | Tracts for the Times | J.H. Newman | ✅ done | 11 ch. |
| 799 | Training of the Twelve | A.B. Bruce | ✅ done | 53 ch. |
| 800 | Treatise on Grace | Jonathan Edwards | ✅ done | 3 ch. |
| 801 | Treatise on Prayer | John Knox | ✅ done | 2 ch. |
| 802 | Treatise on the Love of God | Francis de Sales | ✅ done | 193 ch. |
| 803 | Treatise Written to a Devout Man | Walter Hilton | ✅ done | 16 ch. |
| 804 | True Christianity | Johann Arndt | ✅ dedup (TOC) | 175 ch (110→0 dups). |
| 805 | Truth and Innocence Vindicated | John Owen | ✅ done | 7 ch. |
| 806 | Twenty-one Sermons | Samuel Hopkins | ✅ done | 19 ch. |
| 807 | Two Short Catechisms | John Owen | ✅ done | 30 ch. |
| 808 | Uniformity with God's Will | Alphonsus Liguori | ✅ done | 8 ch. |
| — | Uniformità alla Volontà di Dio | Alphonsus | 🗑 **deleted (Italian dup)** | Non-English copy of #808. |
| 809 | Union and Communion | J. Hudson Taylor | ✅ done | 9 ch. |
| 810 | Varieties of Religious Experience | William James | ✅ done | 17 ch. |
| 811 | Vindiciæ Evangelicæ | John Owen | ✅ dedup (TOC) | 41 ch. |
| 812 | Waiting On God! | Andrew Murray | ✅ done | 35 ch. |

### Batch: "W/Y" range — end of alphabetical march
| 813 | Was Christ Born in Bethlehem? | W.M. Ramsay | ✅ done | 14 ch. |
| 814 | Wesley's Notes on the Bible | John Wesley | ✅ dedup (TOC) | 1121 ch, 1.04M words (838→0 dups, reprefixed per Bible book). |
| 815 | Westminster Confession of Faith | Anonymous | ✅ done | 38 ch. |
| 816–817 | What is Catechism? / What is The Gospel | Zacharias Ursinus | ✅ done | 5 + 5 ch. |
| 818 | What is Darwinism? | Charles Hodge | ✅ done | 8 ch. |
| 819 | What's Wrong With the World | G.K. Chesterton | ✅ done | 40 ch. |
| 820 | When Were Our Gospels Written? | Tischendorf | ✅ done | 5 ch. |
| 821 | Why Four Gospels? | A.W. Pink | ✅ done | 12 ch. |
| 822 | With Christ in the School of Prayer | Andrew Murray | ✅ done | 33 ch. |
| 823 | Words of John Robinson | John Robinson | ✅ done | 15 ch. |
| 824 | Working For God! | Andrew Murray | ✅ done | 32 ch. |
| 825 | Young's Night Thoughts | Edward Young | ✅ done | 4 ch. |

### Gap-closure sweep (leading-article titles + stragglers)
A full-corpus QA sweep found **58 titles never baselined** and **13 with residual dup titles** — almost all leading-article works ("**A** Discourse…", "**A** History…", "**An** …") that sorted outside the march's window, plus a few (Aquinas *Catena Aurea*, Rolt's *Dionysius*, several Charnock *Discourses on Regeneration*, Owen treatises, Bangs, Jenyns) and the missed **NPNF 2-14** (my `requalify_npnf --all` had stopped at 2-13). Baselined all 58; requalified all 13 dup books to 0.

**Final verification — entire Theology genre (841 titles): 0 missing headings, 0 duplicate titles, 0 entity leaks, 0 residual spans.** Alphabetical hand-formatting pass COMPLETE._

### One-blob works cleaned
- **Bradford, *Letters of Master John Bradford* (#262):** the 100k-word blob had a "Letter N. To …" header per letter (present in our text). Used the front TOC's canonical titles to catch all **79 letters** (incl. long descriptive titles a length filter would miss); split → 81 chapters (Contents + 79 letters + Brief Admonition), dropped the redundant header line, 0 dups.
- **Kronstadt, *My Life in Christ*:** a continuous devotional diary with NO internal headings (verified: only Part I/II in the source) — nothing to split *on*. Broke each 120k-word part into even ~3,000-word reading sections → **80 sections** ("Part I · 1 of 39" … "Part II · 41 of 41"). These are reading divisions, not authorial ones.
- **New Schaff-Herzog Encyclopedia (5 vols):** article-level split not reliably feasible (headwords are inline in our extracted text; CCEL's h2 mixes headwords with intra-article subsections). Vols. 13/13a were already well-chaptered (~5k/ch, left alone). Chunked the giant letter-blobs in vols. 1/2/9 (vol. 1 "A" was 413k words) into ~6,000-word reading sections → 93/91/90 chapters. Underlying 1908–14 text is PD (a Baker Book House reprint claim doesn't re-copyright PD content).

### Additional blobs cleaned (2nd pass)
- **Newman, *Tracts for the Times*:** tract structure was OCR-garbled (CCEL headers only reach No. 57; the blob had stray "No. 61.]" citation-footers) → chunked the 195k "No. 57" chapter into ~6k reading sections. 11ch → 43ch.
- **Wace, *Dictionary of Christian Biography*** & **Schaff, *Dictionary of the Bible*:** letter-organized like the encyclopedia; article headwords inline → chunked oversized letter-chapters (~6k). 25→191ch and 30→103ch.
- **Wuttke, *Christian Ethics*, Vol. II:** §LXXVIII had swallowed everything to the end (89k while other sections are 1–4k); headers inline → chunked. 19→33ch.
- **Charnock, *A Discourse of the Nature of Regeneration*:** not a blob (single continuous sermon; the "1./First/I." are rhetorical points), just a glitched chapter title "by" → renamed. The other Charnock discourses are legit single sermons, left as-is.

_Post-2nd-pass verification: **0 chapters over 100k words**; the 6 remaining >70k are all legitimately-long single works (Manton on James 1, Origen's *Philocalia*, Shepherd of Hermas, Nestorius Bk II, Knox Bk I, Cyril). Full genre still 0 missing-headings / 0 dups / 0 leaks / 0 spans across 841 titles._

### Shell resolution (2026-09-18): deleted 8, re-fetched 2 from CCEL
Per Adam's call: **deleted 8 low-value shells** (hymn/song/poetry collections + a hymn index) —
Longfellow *Book of Hymns*, *Olney Hymns*, Montgomery *Sacred Poems*, Winkworth *Cumulative
Indexes*, Brownlie *Russian Church* & *Early Church* hymns, Watts *Divine and Moral Songs*,
Waring *Hymns and Meditations*. Theology corpus 908 → **900**.

**Re-fetched the 2 high-value shells directly from CCEL ThML** (the HF dataset had ~none of their
content because it lives in non-`<p>` markup):
- **Divine Comedy** (Dante) — verse is in `<pre>` blocks under div3 cantos; extracted 100 cantos +
  Appendix + Postscript = **102 chapters / 113k words**, verse rendered as terza-rima stanzas,
  titled "Inferno · Canto I" etc. (was 223 w).
- **Hitchcock's Bible Names Dictionary** — content is 2,623 `<term>`/`<def>` pairs; rebuilt as 23
  A–Z letter chapters, **all 2,623 entries** ("Aaron — a teacher; lofty; mountain of strength").
  (was 24 w.)

### ⚠️ Systemic issue found (2026-09-18): near-empty "shell" books
A word-count scan found ~20 Theology books under 600 words. Some are genuinely short (Pascal's *Memorial*; the M.E. Preachers list; short elegies/poems), but several dropped major content during seeding and are effectively empty: **Divine Comedy (Dante, 223 w)**, **Hitchcock's Bible Names Dictionary (24 w)**, **NT Song Database (31 w)**, and multiple hymnals (Longfellow's above, *Hymns of the Early Church*, etc.). These need **re-ingestion from CCEL**, not formatting. There are likely also *partial*-ingestion cases above the 600-word threshold. Decision pending: dedicated re-ingestion pass vs. handle-as-found.

### Patristics series (ANF/NPNF, 37 volumes) — ✅ DONE as a dedicated pass
Built `scripts/qualify_patristics.py`: for each volume it aligns every DB section to the cached
CCEL TOC by in-order title matching (both are in reading order), derives each chapter's parent
**work** from the TOC's dotted-id ancestry (preferring a short "label-like" ancestor — the L2
work for ANF, the L1 work for NPNF where L2 is a descriptive Book), and re-titles chapters
"Work · Chapter" as both TOC label and injected heading. Idempotent (recovers the original title
before re-aligning). Also unwraps spans and applies the baseline.

Ran across **all 37** volumes — ~19,000 chapters. Alignment near-perfect (unmatched: 0 for 33
volumes; 1–3 for NPNF101/102/110, which keep their original title). Artifact sweep over all 37:
**zero** missing headings / entity leaks / mojibake / stray spans. Verified titles read well
across structures: "City of God · What Solomon…", "Against Heresies: Book I · Chapter III",
"Book IV · The Bishops of Rome…" (Eusebius), "Origen Against Celsus · Chapter XXVI".

This completes #14–16 (ANF01–03) fully **and** the other 34 ANF/NPNF volumes ahead of their
alphabetical turn (ANF04–09 + all 28 NPNF) — they'll be skipped/verified when reached.
(Running tally is tracked at the top of the progress table above.)

_(Baseline mechanics factored into `scripts/format_theology.py` — driven per-title after individual inspection, not batched.)_

---

## Genre pass 2: Biography (+ Autobiography, merged)

Extending the per-book pass to the non-CCEL genres. **Biography + Autobiography = 42 books, all Standard Ebooks** (zero Gutenberg here). SE is richly + cleanly formatted (semantic `h2` parts / `h3` chapters, `header`/`hgroup`, tables, figures, blockquotes) and its ingestion already stripped production boilerplate (no colophon/imprint/uncopyright). So — as expected — the CCEL baseline does NOT apply (it would destroy SE markup); this pass is verify + one targeted fix.

**The one systemic SE issue: dup chapter titles from part/section resets.** Flattening lost the part context, so numbered chapters collide in the reader TOC ("I, II … I, II …"). Built **`scripts/requalify_se.py`**: fetches the book's `toc.xhtml` from the SE GitHub org, reads the part→chapter hierarchy, aligns to our chapters (matching on the leaf's leading number token, since SE ToC leaves carry descriptive titles our bare "I" lacks), and rewrites title + leading heading. Rules: **≥2 real parts → prefix every part-nested chapter uniformly** ("Book I: In Domremy · I: When Wolves Ran Free in Paris"); a lone wrapper node (SE nests the whole book under one node = its title, e.g. Hull House) → no prefix, just adopt the richer leaf label ("I: Earliest Impressions"). Idempotent (strips any prior prefix before matching).

- 9 of 42 books had dup titles → all fixed to 0: Roosevelt, Eminent Victorians, Kropotkin (6 parts), Tagore, Twain *Joan of Arc* (3 books), Gandhi (5 parts), Keller, Hull House, Lindbergh *"We"*.
- Other 33 already clean (verified: 0 dups, 0 leaks, headings intact).
- **Merged Autobiography → Biography** (35 books retagged; dedup preserved order). Biography shelf now **42 books**; Autobiography shelf removed.
- Final QA: all 42 — 0 dup-titles, 0 entity-leaks. Not yet published/deployed.

## Genre pass 3: Memoir (merged into Biography)

**Memoir = 29 books, all Standard Ebooks** (5 already also-Biography, fixed in pass 2). Same SE recipe. Only 2 had dup titles → fixed via `requalify_se.py`: Twain *Roughing It*, Dostoevsky *House of the Dead* ("Part I · I: The House of the Dead" …). Other 27 verified clean (0 dups, 0 leaks). **Merged Memoir → Biography** (29 retagged, 5 overlap). Biography shelf now **66 books**; Memoir shelf removed. 28 genres remain. Uncommitted / not yet published.

## Spirituality → Theology reconciliation

Checked the 37-book Spirituality shelf (all SE) against Theology for overlap.
- **9 exact duplicates** (SE ↔ CCEL): kept the SE edition (hand-formatted for format fixes — Chesterton *Everlasting Man* & Kempis *Imitation of Christ* had part-reset dup titles, fixed via `requalify_se.py`), **deleted the 9 CCEL copies** (incl. the hand-repaired Divine Comedy / Pilgrim's Progress — per Adam's call to standardize on SE). Reshelved the SE copies to Theology (dropped Spirituality, kept Fiction/Poetry/Philosophy where present).
- **8 net-new Christian works reshelved to Theology + verified**: Augustine *City of God*, Tozer *Pursuit of God*, MacDonald *Unspoken Sermons*, Moody *The Way to God*, Spurgeon *Art of Illustration*, A. Alexander *A Day at a Time*, Newman *Verses on Various Occasions*, Tolstoy *Kingdom of God Is Within You*.
- **Left in Spirituality** (non-Christian / not theology): Tao Te Ching, Siddhartha, Demian, Gitanjali, The Pilgrim Kamanita, Polynesian Mythology, Weber, Tawney, Belloc (travel), The Necromancers, Mary Olivier, Festus, MacDonald *Short Fiction*, Gandhi (Biography), + borderline kept per Adam (Gibran *Jesus the Son of Man*, Tolstoy *A Confession*, *Barlaam and Ioasaph*, *Malleus Maleficarum*).

Net: Theology 841 → **849**; Spirituality 37 → **20**; total books −9. All 17 reshelved SE copies verified 0 dups / 0 leaks.

---

## Genre pass 4: Religion (Gutenberg) → triage into Theology / Biography / stay-Religion

Religion = 288, **all Project Gutenberg** — the first genuinely dirty shelf (14 with PG boilerplate, 11 entity-leaks, 22 single-chapter blobs, 59 dup-titles, 10 missing-headings). Built **`scripts/format_gutenberg.py`** (`clean_book`): strips PG licence blocks + transcriber notes ("Transcribed…by…pglaf.org", "*** START/END OF…"), drops leading provenance `<p>` so each chapter opens on its heading (injects `<h2>` from title if none), unwraps inert spans, normalizes whitespace — preserves rich markup + chapter structure. Triage per Adam's rule: Christian doctrine/devotion/sermons/Bible/church-history → Theology; Christian biography → Biography; non-Christian + comparative religion/mythology → stay Religion.

**Batch 1 (21, alphabetical A–):** heavy on LDS/Baha'i/Islam/Theosophy.
- → **Theology (6):** Ward *A Coal from the Altar*, Purchas *English Church in NZ*, Bridges *Practical Discourse* (hymnody/worship), Snowden *A Wonderful Night* (Nativity), Kingsley *All Saints' Day and Other Sermons*, Bunyan *An Exhortation to Peace and Unity*.
- → **Biography (1):** Gronniosaw *A Narrative…* (spiritual autobiography).
- 🗑 **Deleted (2):** Tolstoy *Kingdom of God* (Gutenberg dup of the SE copy already in Theology), *Gospel Hymns in Ojibway* (hymn-text collection).
- **Stayed Religion (12):** 8 LDS (Roberts, Widtsoe, O. Hyde, P. Pratt, O. Pratt ×2, N. Anderson, J. Taylor), Baha'i, Islam, Theosophy, Josephus *Against Apion*. All cleaned; deduped *Added Upon* & *A Voice of Warning* (two prefaces retitled by edition).

**Judgment call to confirm:** kept **LDS/Mormon works in Religion** (not Theology), matching the Theology shelf's orthodox-Christian scope. Counts: Theology 849→**855**, Biography 66→**67**, Religion 288→**279**.

**Batches 2–4 (63 more, alphabetical B–H):** added `dedup_book` helper to `format_gutenberg.py` (context-prefix + sequential fallback, for Gutenberg books with no ToC). Big Baha'i / LDS / comparative-religion presence (mostly stayers, cleaned + deduped in place — Essentials in Church History had 80 dup-title fixes, Baha'i compilations deduped).
- → **Theology (13):** Kingsley *Discipline*, Luther *Disputation* (English 95 Theses), Graebner *Evolution* critique, Whipple *Five Sermons*, Beard *Beside the Still Waters*, Daly *Catholic Problems in W. Canada*, Bancroft *Deaconesses in Europe*, Talmage *Ecclesiastical Relations* (China missions), MacCaffrey *History of the Catholic Church* ×2, Rufus Anderson *History of the ABCFM Missions* ×2.
- → **Biography (1):** Morison *Andrew Melville*.
- 🗑 **Deleted (1):** Howe *Herein is Love* (© 1961, modern copyright).
- **Stayed Religion:** LDS, Baha'i, Hindu/Buddhist (Eliot, Blavatsky), Jewish (Talmud), Theosophy, Egyptian, Wells.

Running after 4 batches (~84 books): Theology **867**, Biography **68**, Religion **265** (from 288).

**Batches 5–6 + recovered gap (~65 more, I–R range):** caught a batching bug — an index-based slice skipped the I–L range once books started leaving the shelf; switched to a strict alphabetical cursor and recovered the 23 skipped titles.
- → **Theology:** New Tabernacle Sermons (T. De Witt Talmage), Quaker *On Singing and Music*, Kennedy *Life and Work in Benares* (LMS missions), Benson *Lourdes* (Catholic), Newman *Parochial & Plain Sermons* VII–VIII, *Rays of Living Light*, Episcopal *Commemorative Services*.
- → **Biography:** *Martin Luther* (Koppenhaver), *Norman Macleod*, *John Knox*, Begbie *Painted Windows*, *Principal Cairns*.
- **Stayed Religion:** heavy LDS (incl. Talmage's *Jesus the Christ*, Key to the Science of Theology, journals), Christian Science (Mary Baker Eddy ×5), Baha'i, Judaism (Pirke Avot, Rashi), Islam, comparative religion/mythology (Lang, Carpenter, Egyptian/Greek/Chinese), freethought (Ingersoll).

Running after ~6 batches: Theology **875**, Biography **73**, Religion **252** (from 288).

**Religion pass COMPLETE (2026-09-19).** Triaged all 288 Gutenberg-era Religion titles alphabetically (13 batches), cleaning every book with the Gutenberg recipe (clean_book + dedup_book) and reshelving by content:
- **→ Theology (~64):** Christian sermons (Kingsley, F.W. Robertson, Latimer, Shedd, Talmage-DeWitt, Baring-Gould, Swift, *World's Great Sermons* ×5), church history/polity (Killen *Ancient Church*, *Acts of Uniformity*, *Acts of the General Assemblies*, *Church and the Empire*, *Divine Right of Church Government*), Catholic/Anglican works (Aquinas *Summa* ×4, *Divine Office*, Jewel *Apology*, *Prayer Book Explained*, *Serious Hours of a Young Lady*), Christian classics/devotion (Charnock *Existence & Attributes*, *Cell of Self-Knowledge*, *Messiah in Moses & the Prophets*, Butler, Van Dyke *What Peace Means*, *Wonders of Prayer*), Orthodox (Velimirović *Religious Spirit of the Slavs*).
- **→ Biography:** *Saint Augustin* (Bertrand), *Thomas Chalmers* (Blaikie).
- **→ Fiction:** Van Dyke *The Spirit of Christmas* (literary allegory, not instruction).
- **Deleted:** *Confessions of St. Augustine* (Gutenberg dup of the CCEL copy already in Theology).
- **Stayed Religion (206):** heavy LDS (Book of Mormon, Talmage, B.H. Roberts incl. *Seventy's Course in Theology*, Orson/Parley Pratt, Joseph Smith, Woodruff/Taylor, anti- and pro-Mormon histories), Baha'i (Baha'u'llah, 'Abdu'l-Bahá, Shoghi Effendi), Christian Science (Eddy), Islam (Qur'an ×3 translations, Sell, Blunt), Judaism (Ginzberg *Legends*, Kent, Landman, Rashi), Hinduism/Buddhism (Vedanta-Sutras ×2, Yogananda, Zen), comparative religion/mythology (Frazer *Golden Bough*/*Balder*, Lang, Egyptian/Babylonian/Roman/Celtic religion), freethought (Paine, d'Holbach, Mangasarian, Brooks), and Christian heterodoxy kept out of the orthodox shelf (Swedenborg, Universalist sermons).
- **Final QA (whole Religion shelf, 206):** 0 missing headings · 0 dup titles · 0 entity leaks · 0 real PG cruft (12 residual regex hits are legitimate body prose, e.g. "produced by similar means"). Trailing Mormon-Texts-Project credit stripped from *Plan of Salvation*; stray `&gt;`/`&lt;` + an HTML comment + escaped `<i>` tags cleaned from 7 books.

Running totals after Religion: **Theology 917 · Biography 75 · Religion 206.**

**Bible pass COMPLETE (2026-09-19) — shelf retired.** Adam's call: the app already serves the Bible text via MCP + the ESV API, so raw scripture volumes in the Reading Room are redundant.
- **Deleted (45 raw-text volumes):** the 40 individual KJV books (Genesis…Malachi, Luke/Acts/Corinthians, etc.), the complete KJV, the KJV Complete Contents, the Douay-Rheims Job, the WEB Job, and the Deuterocanonical Apocrypha. (All were David-Widger Gutenberg verse blobs — one section per book, "01:001:001 …" verse markers.)
- **→ Theology (9 studies/commentaries):** Maclaren *Expositions of Holy Scripture* ×4 (Deut/Josh/Judg; Ezekiel/Daniel/Minor Prophets; 2 Cor/Gal; 2 Kings), Palmer *A Bird's-Eye View of the Bible*, Hunting *Hebrew Life and Times*, Chappell *Sermons on Biblical Characters*, Erdman *The Gospel of Luke: an exposition*, Kent *The Origin and Permanent Value of the Old Testament*.
- **→ Religion (3):** Widtsoe *What Jesus Taught* (LDS study manual), *The First Book of Adam and Eve* (OT pseudepigrapha), *The Four-Faced Visitors of Ezekiel* (fringe interpretive pamphlet).
- **QA on all 12 reshelved:** 0 cruft · 0 missing headings · 0 dup titles · 0 entity leaks. (KJV credit-block pre-strip logic — drop everything before the first `<h[1-6]>` — was written for the text books but they were deleted instead.)

Bible shelf: 57 → **0** (retired). Running totals: Theology **926** · Religion **209** · Biography 75. Total corpus 10,638 → **10,593**.

**History & Biography — biography extraction pass (2026-09-19).** Adam: pull the biographies out into the Biography shelf, hand-clean them, and leave non-biography history for a later pass. Rule applied: a work centered on a **specific person's life/career** (biography, autobiography, personal life-memoir, or a named person's collected letters/diary) → **Biography**; accounts centered on an **event/campaign/unit, a place, a court/dynasty, or a topic** — and all **travel/exploration narratives** (a Travel shelf handles those) — stay in History & Biography for the later pass.
- **Reshelved 90 → Biography**, hand-cleaned (clean_book + dedup_book; 20 deduped). Includes the title-obvious (Life of Nelson/Napoleon/Gladstone/Flinders/Joan of Arc; Memoirs of Sherman/Napoleon/Casanova/Du Barry; autobiographies of Margot Asquith, George Francis Train, Sgt. Lawrence, Mifflin Gibbs; slave narratives of Douglass/Bibb/Hughes/Steward/Thompson; letters of Queen Victoria & Nelson; life-and-letters of Walter Page) AND name-titled biographies the title-regex misses (Abraham Lincoln ×3, Cardinal Wolsey, Burke, Henry VIII, James Watt, Josephus, Gandhi, Ulysses S. Grant, Lord Randolph Churchill, Wm Lloyd Garrison, William Wallace, Obed Hussey, RLS, Napoleon's Marshals, Plutarch's *Lives* ×4) and career autobiographies (Roberts *Forty-one Years in India*, Schofield *Forty-Six Years in the Army*).
- **QA on all 90:** 0 missing headings · 0 dup titles · 0 entity leaks · 0 real cruft. Fixes applied: excised a trailing "Transcriber's Note + download-volumes + errata" table from both *Letters of Queen Victoria* volumes; cleaned stray `&gt;`/`&lt;` + `==>`/`<==` arrow artifacts from 6 books (Sherman, T. Roosevelt, Lord Randolph Churchill, Victoria girlhood, Garrison).
- **LEFT for the history pass (examples):** single-battle/campaign accounts (*Shiloh as Seen by a Private Soldier*, Chickamauga/Gallipoli/Sumter narratives), regimental/unit histories, court & dynasty memoirs (*Court of Queen Elizabeth*, *Dukes of Urbino*, Saint-Simon), national/regional/place histories (Holinshed, Dio's Rome, Tacitus, the county/city volumes), and travel/exploration narratives (Burton, Humboldt, Mungo Park, Himalayan/Inca journals).
- **FLAG — duplicate edition:** Sherman's *Memoirs* is now in Biography as two overlapping editions (a 4-part split #11799/11800/11798/11801 + a Complete/Vol1/Vol2 set #11804/11802/11803). Same text; pending a dedup decision.

History & Biography: 1317 → **1227** (history-only remainder). Biography: 75 → **165**.

**History & Biography — deep content-based biography sweep (2026-09-19, follow-up).** Adam flagged that the title-heuristic first pass (90 bios) likely missed many. Switched to reading each book's actual content instead of trusting titles. Method: (1) content scan of every book's preface + opening chapters for biographical signal → strong/maybe/unlikely buckets; (2) read all strong (48) + maybe (32) openings; (3) re-checked the 260 "unlikely" books carrying any weak signal or a person-name title by reading their openings; (4) a memoir/personal-narrative *title* net (119 hits) to catch memoirs that open in medias res (which content-opening scans miss); (5) a final residual net.
- **+151 more biographies → Biography** this pass (on top of the 90 from the title pass): third-person lives the regex missed (Bismarck & Foch in the *Heroes of the Nations* mold, Stonewall Jackson, Robert E. Lee, Edith Cavell, Robert the Bruce, Kaiser Wilhelm, Baden-Powell, Champlain, Kirkcaldy of Grange, Sergeant York), collective biographies (*Builders of United Italy*, *Fathers of Biology*, *Eminent Literary & Scientific Men* ×2), autobiographies & slave narratives (Douglass *My Bondage*, Keckley, Jacobs, W.W. Brown, Mary Antin, Cole Younger), and a large body of **personal war memoirs / diaries / letters** (Grant's & Sheridan's *Personal Memoirs*, Chesnut's *Diary from Dixie*, Cox's *Military Reminiscences*, Semmes, escape/POW memoirs, WWI soldiers' letters, Whitman's *Wound Dresser*, Napoleon's & Nelson's collected letters).
- **DELETED (this pass): 1 copyrighted work** — *Blood Brothers: A Medic's Sketch Book* (© 1985, Carlton Press) — and **15 duplicate memoir editions**: kept Grant's *Personal Memoirs, Complete* (deleted 9 vol/part/alt editions incl. GT#192) and Sheridan's *Personal Memoirs* complete (deleted 6). (Earlier same day: kept Sherman's *Memoirs — Complete*, deleted 6.)
- **Left in History & Biography (1062):** national/regional/topical histories, chronicles (Holinshed, Dio's Rome, Tacitus, Hume, Macaulay), unit/regimental/ship histories & single-battle papers, court/dynasty memoirs, folklore/ethnography, political/economic tracts, official document compilations, and all travel/exploration narratives (Burton, Humboldt, Livingstone, Mungo Park journals, the county/city guidebooks) — for the later history pass.
- **QA on every reshelved book:** 0 missing headings · 0 dup titles · 0 entity leaks; residual "cruft" hits verified as body prose. Targeted fixes: excised leading "E-text prepared by the Project Gutenberg…" credit blocks from 2 books (one whole boilerplate section deleted); cleaned escaped `<<br>`/`--&gt;` artifacts.

**JUDGMENT FLAG for Adam:** the biography set now includes a large body of **personal war memoirs, diaries, and soldiers' letters** (WWI & US Civil War especially) — treated as memoirs → Biography. Unit/regimental *histories* and single-battle "paper read before…" accounts were left as history. If you'd rather personal war narratives stay with military history, they're a clean, separable subset I can move back.

History & Biography: 1227 → **1062**. Biography: 165 → **309**.

**Shelf renamed (2026-09-19):** "History & Biography" → **"History"** across all 1062 remaining books (Biography having been split out). The combined-shelf name is retired.

**LOC/Dewey cross-reference (2026-09-20).** Cross-referenced the whole corpus against OpenLibrary (which carries LOC's MARC-derived classifications) via `scripts/classify_loc.py` — DDC-primary, LCC fallback, aggressive multi-pass matching (title+author → title → exact → work-editions) with an author-agreement guard, all cached to `.seed_cache/loc_classify.json`. Stored on each book in new columns **`ddc` / `lcc` / `loc_subjects` / `loc_how`** (non-destructive; `genres` untouched).
- **Coverage (10,571 books):** direct Dewey 5,812 (54%; incl. 744 `FIC` markers), LCC-only 2,105, **DDC-or-LCC 7,917 (74%)**, neither 2,654 (25% — mostly genre fiction/children's that OpenLibrary never assigns a Dewey to).
- **Decision — Dewey is a SECOND AXIS, not the shelving.** A pure-Dewey reshelve was rejected because it (a) collapses all genre fiction into one ~4,100-book "800 Literature" blob (Dewey can't tell mystery from romance), (b) flattens the curated Theology-vs-Religion split into "200 Religion", and (c) disperses the Biography shelf. So the genre + hand-curated shelves stay; the Dewey/LCC class rides along as per-book metadata for a future call-number sort / filter inside a shelf.
- **Note:** R2 currently holds a partial-classification `books.db` (published mid-run at ~1,950 books). The local DB now has the full classification, but since the reader UI doesn't consume these columns yet, no republish is needed until a Dewey/call-number view is built (or to sync the metadata + the Magna Carta fix).

### Horror & Gothic — sourced additions (2026-09-21)
Compiled a list of notable public-domain horror/gothic titles **not already in the corpus** by cross-referencing six curated sources (Gutenberg bookshelf 42, RavenKingCrafts, steve-calvert.co.uk, a Goodreads PD-horror shelf, a books.db diff; Reddit's r/horrorlit thread was unreachable — it blocks WebFetch, Firecrawl, and direct curl alike). Diffed every book-level candidate against the full 10,561-book corpus (verified against each author's actual holdings), then **sourced, chaptered, and shelved** the gaps via `scripts/seed_horror.py` (single-file) + `scripts/seed_horror_multivol.py` (volume-merge). **Horror & Gothic shelf: 80 → 100 (+20).**

- **Single-file (17):** The Terror (Machen) · Hauntings (Vernon Lee — a new author to the corpus) · The Book of Were-Wolves (Baring-Gould) · The House by the Churchyard (Le Fanu, 103 ch) · Carnacki, the Ghost-Finder (Hodgson) · More Ghost Stories of an Antiquary (M. R. James — the 1911 collection, distinct from the two James vols already held) · The Slayer of Souls & The Mystery of Choice (Chambers) · The Centaur, The Human Chord, Incredible Adventures, Pan's Garden, The Empty House and Other Ghost Stories (Blackwood ×5) · Black Magic (Marjorie Bowen — new author) · The Romance of the Forest (Radcliffe) · Varney the Vampyre (Prest/Rymer — 233 ch, 654k w) · Skull-Face (R. E. Howard).
- **Volume-merged into one book each (3):** In a Glass Darkly (3 vols → 76 ch) · The Purcell Papers (3 vols → 15 ch) · Sidonia the Sorceress (Meinhold, 2 vols → 90 ch).
- **Chaptering fixes (baked into `seed_horror._FORCE_SPLIT`):** three books defeated `gb._raw_chapters`' div.chapter/heading heuristic and were force-split — **Varney** (227 *empty* `<div class="chapter">` anchors, prose in siblings → split on `<h2>`), **Pan's Garden** (same empty-anchor trap → `<h2>` story titles), **Skull-Face** (no headings at all; chapter titles are `<p class="ph2">`). Without the override these came through as 41 words / 1 chapter; after, 17 ch / 22 ch.
- **Covers:** all 20 fetched from the Gutendex cover image, WebP'd (max-w 400, q80) into `covers.db` (8,794 → 8,814), and `cover_url` finalized to `/api/cover/{slug}` — self-hosted like the rest, no external hotlinks.
- **Metadata:** each book `source=gutenberg`, `license=PD-US`, `section`=`genres`=`["Horror & Gothic"]`, PG author string (`_display_name` form, consistent with the corpus), PG subjects, concise display title (raw PG title kept in `title_backup`).
- **Excluded — not PD:** The Werewolf of Paris (Endore, 1933; US copyright to 2029).

#### Alt-source pass (same day) — the 5 titles not on Gutenberg/Standard Ebooks
`scripts/seed_horror_alt.py` handles two more clean PD repositories: **Project Gutenberg Australia** (single-file HTML) and **Wikisource** via the ws-export EPUB tool (per-chapter XHTML; chapter titles derived from the spine filenames — the pages carry no `<h*>`). **3 of 5 sourced, +3 shelved → Horror & Gothic now 103; 23 added this session.**
- **The Maker of Moons** (Chambers) — PGA `0605441h`, 9 stories / 69k w. Dropped the author-name front-matter section.
- **The Italian** (Radcliffe) — Wikisource EPUB, **complete in all 3 volumes**, 38 ch / 174k w (this is the full novel PG only had 2 of 3 volumes of). Titled "Volume N · Chapter M".
- **The Beast with Five Fingers** (W. F. Harvey) — PGA `0609231h`, the **title story only** (1 ch, 10k w); the full 1928 collection isn't digitized clean anywhere (PGA has only 3 Harvey stories total).
- Covers for all 3 pulled from OpenLibrary (matched by title + publish year 1797/1896/1928), WebP'd and self-hosted like the rest.
- **Still deferred (2), genuinely unavailable as clean text:**
  - **The Dark Chamber** (Leonard Cline, 1927) — no digital text exists anywhere; the only artifact online is a 2024 **LibriVox audiobook**. Would need someone to scan + OCR a physical copy.
  - **Zofloya** (Charlotte Dacre, 1806) — the only full text is a 1806 Google-scan on archive.org with badly corrupted OCR (running-header bleed, "y Google" watermarks, broken line-wrapped words, `ſ`/`f` confusions); Wikisource has only a partial (vol 1) transcription. Not shippable at the shelf's quality bar without a manual OCR-restoration pass.

### Christianity — *Colloquia Peripatetica* (John Duncan), OCR restoration (2026-09-24)
Not on Gutenberg, Standard Ebooks, CCEL, or Wikisource; the only text is archive.org scan OCR. Restored by hand from **`colloquiaperipat02dunciala`** (Knight's **5th edition, enlarged, Edinburgh: David Douglas, 1879**), and shelved as one book: **200 chapters / 57.9k words / 20 footnotes** → Christianity. Seeder: `scripts/seed_duncan_colloquia.py` (reads the proofed working file `.seed_cache/duncan/work.md`).
- **Method.** ABBYY XML (not the flat djvu.txt) parsed with page/line geometry and italic runs, so italics survive and running heads/folios can be cut by position. Text proofed against the **page images** (line crops pulled by ABBYY coordinates) wherever the OCR was doubtful, and cross-checked word-by-word against a **second independent scan** (`colloquiaperipat00knig`) with difflib alignment to catch real-word substitutions a dictionary can't (e.g. "marts" for πίστις, "time" for "true"). A non-dictionary sweep against the library's own clean vocabulary found no residue beyond period coinages (*Morelled*, *uncreaturifies*, *cloudification*, *theologeme*…).
- **Every Greek passage re-read from the scan** (63 spans: πρῶτον ψεῦδος, χρίσμα τοῦ ἁγίου, ἡ μονὰς πλατυνθεῖσα γέγονε τριάς, Gal. 6:11, the Chrysostom footnote…) — OCR had rendered them all as Latin-letter gibberish. Print forms kept where they differ from the critical text (λογικός for Apollos; χρίσμα).
- **Structure.** Front matter (Prefatory Note, Preface to the Third Edition + *Reminiscences*, Biographical Sketch) then one chapter per colloquy, titled from Knight's bracketed headings in title case; the dozen or so colloquies whose headings the OCR lost or fused (Plato and Aristotle, Evil, Ferme…, the V. V. conversation, Mästricht…) restored from the scan and the printed Contents. "Additional Colloquia" kept as a divider chapter with Knight's note. Drop-cap debris (`HTHEKE'S`, `T^HE`, `/APPOSITE`…) fixed to sentence case at every colloquy opening; Knight's bracketed questions kept verbatim.
- **Footnotes.** Page-bottom notes had been spliced into running text mid-sentence (and one Aquinas note split across two pages and a heading); all extracted, reassembled, and set as numbered notes at the chapter end. Knight's print cross-references ("See p. 27") rewritten to the colloquy title, since the edition has no pages.
- **OCR-dropped blanks restored:** "Dr. ——— opened his mouth", "the Bishop of ——", "A—— was a great man", "Priest G—— of L——", "Arianism, and ———". Kept print spellings (Mästricht/Maestricht, Fenelon, *cachination*, *give* for gave) and æ ligatures as printed.
- **Cover:** the decorated red-and-black title page (scan page n6), WebP'd into `covers.db` and finalized to `/api/cover/{slug}`.
- Slug `john-duncan_colloquia-peripatetica-ia`, `source=archive.org`, `license=PD-US`, full title + edition in `title_backup`.

## Pulp issue collections: Weird Tales and Fantastic Adventures (2026-10-04)

**108 issue collections** (`weird-tales_YYYY-MM`, `fantastic-adventures_YYYY-MM`), one book per magazine issue, built by `scripts/seed_pulp_issues.py` from `docs/reading-room/pulp-eligible-stories.csv` (`scripts/build_pulp_eligibility.py`: FictionMags contents + Online Books Page renewal records + Gutenberg catalog). Per Adam's calls:

- **Every issue with at least one public-domain story in clean text** becomes a collection now (66 hold a single story); re-run the seeder as more stories are transcribed and issues fill in.
- **Serialized novels:** the complete novel goes into every issue that carried an installment, with a note naming the part that issue ran. Included only when every installment's issue is public domain.
- **Stories already in the library as standalone books stay standalone** and are also included in their issue.

Structure: chapter 1 is **Contents**, the issue's full fiction and verse with each item marked (in this collection / public domain, not yet transcribed / public domain from 2027-01-01 / under copyright through YYYY). Each story opens with `<h2>` title and an italic byline; multi-chapter stories are named "Story: chapter". Cleanup at assembly: Gutenberg drop-cap images restored to their letter (fixed in `webapp/sources/gutenberg.py`, so all future Gutenberg imports get it), source bylines / repeated titles / "Transcribed from" notes / title-page chapters / page-number markers removed. Covers: each issue's own cover from Galactic Central, self-hosted via `build_covers_db.py` (+ `--finalize`; the seeder resets `cover_url`, so finalize after every run).

Skipped (Gutenberg match was a different, longer work with the same title): *The Killer* (Feb 1924), *Dracula's Guest* (Dec 1927), *The Ruling Passion* (Jul 1930).

## Dime novels from Project Gutenberg (2026-10-04)

**284 English dime novels** added, one book per novel (each dime-novel issue was a single story), by `scripts/seed_dime_novels.py` from Gutenberg's catalog (subject/bookshelf "Dime novels", English; the 96 Dutch *Lord Lister* issues and writing *about* dime novels excluded). 14.6M words; Nick Carter, Frank Reade, Buffalo Bill, Frank Merriwell, Deadwood Dick, Old Sleuth, the Bradys, Bertha M. Clay's story-paper romances. Shelved from Gutenberg subject headings: Adventure 204 · Children's 63 · Science Fiction 52 · Mystery & Crime 48 · Romance 36 (multi-shelf). Covers self-hosted.

Two `webapp/sources/gutenberg.py` fixes came out of it (help every future Gutenberg import): `<div class="chapter">` blocks are trusted only when they hold at least half the book's text (many dime novels, like *Varney*, wrap only the heading in the div, which kept headings and dropped the prose: 54 books first came in as 32–300 words), and files with no heading tags split on plain `<p>CHAPTER IV.</p>` paragraphs.

**Root cause of the 20 chapterless horror books:** `seed_horror.py` and `seed_horror_multivol.py`'s `_store` never inserted `book_chapters` (only deleted them). Fixed in both; the importers now write chapters.

## Pulp scans from the Internet Archive: pilot on Weird Tales, October 1927 (2026-10-04)

`scripts/scan_pulp_issue.py "Weird Tales" 1927 10` recovers the issue's public-domain stories that have no clean text yet: ABBYY layout + IA's page-number map (`scripts/ia_pulp_ocr.py`) → cut by the FictionMags start pages (mid-page boundaries by title, or by the capitalized opening word when the title is decorative art) → follow "(Continued on page N)" jumps into the back pages, chained, misread-tolerant → drop running heads, folios, ornaments → conservative correction by Claude Sonnet 5 (numbered paragraphs in chunks of 60; a paragraph the model drops or reshapes keeps its raw text; ads/captions/teasers returned as [OMIT]) → `.seed_cache/pulp/scan/<issue>/`, which `seed_pulp_issues.py` uses only where Gutenberg and the library have nothing, adding a source note. Serial installments are skipped (a serialized novel goes in complete).

Measured against Gutenberg's text of two stories from the same issue: raw scan text differs by ~1.8–2.1% of words after cleanup; after correction ~1%, almost all of which is Gutenberg's own additions (transcriber note, illustration captions) — about one real error per story left. Cost ≈ $1.10 per issue. October 1927 went from 4 to 12 of its 13 pieces.
