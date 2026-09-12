# Reformed & historic PD ingestion list — Phase 1

The public-domain, actually-ours-to-ingest subset of the Reformed/historic-Christian canon that Monergism, CCEL, and the Banner/Puritan tradition curate — the target for enriching the study-Bible **MCP** (distinct from the teacher-facing Living Library).

**Triage rule.** Include a work only when it is **US public domain** — the safe proxy is **author died ≤ 1928** *and* a **PD English edition/translation exists** (first published ≤ 1929). Modern works distributed free-by-permission on Monergism (Piper, Sproul, Beeke, Reformation Trust, Banner reprints) are **excluded** — link-out for discovery, never ingest. Foreign-language authors are marked **⚠tr** where the standard English translation is modern (so ingest only if a PD translation exists, or ground the original).

**Source priority.** `CCEL` (most of the Reformed/Puritan corpus, adapter built) → `Gb` Project Gutenberg (popular classics, adapter built) → `Ar` archive.org (**the long tail — needs a new adapter, Phase 2**).

**Shape.** `[C]` verse-keyed commentary (slots into `get_commentary`, needs the reference-index parser) · `[T]` treatise/book · `[S]` sermons · `[D]` dictionary/reference/topical · `[H]` hymnody/devotional · `[Sym]` creed/confession/catechism.

**Counts:** ~150 authors · **~560 works** flagged ingestible. ★ = top-priority first wave.

---

## A. Patristic & medieval full works (behind the catena)
The catena already quotes ~300 fathers in fragments; these are the **complete works** the exegesis tools should be able to open.

- **Augustine of Hippo (d. 430)** [T/C] ★ — Confessions; City of God; On Christian Doctrine; Enchiridion; On the Trinity; Homilies on John; Expositions on the Psalms; Anti-Pelagian writings. — CCEL / Gb
- **Athanasius (d. 373)** [T] ★ — On the Incarnation; Life of Antony; Four Discourses Against the Arians. — CCEL
- **John Chrysostom (d. 407)** [C] ★ — Homilies on Matthew, John, Romans, 1–2 Corinthians, Hebrews (verse-keyed gold). — CCEL
- **Irenaeus (d. 202)** [T] — Against Heresies. — CCEL
- **Tertullian (d. 220)** [T] — Apology; Prescription Against Heretics; On the Flesh of Christ. — CCEL
- **Cyprian (d. 258)** [T] — On the Unity of the Church; Epistles. — CCEL
- **Origen (d. 253)** [T] ⚠ — On First Principles; Against Celsus. — CCEL
- **Eusebius (d. 339)** [T] — Ecclesiastical History. — CCEL / Gb
- **Basil of Caesarea (d. 379)**, **Gregory of Nazianzus (d. 390)**, **Gregory of Nyssa (d. 394)** [T] — Cappadocian dogmatic + Trinitarian works. — CCEL
- **Cyril of Jerusalem (d. 386)** [T] — Catechetical Lectures. — CCEL
- **Leo the Great (d. 461)**, **Gregory the Great (d. 604)** [S/T] — Sermons; Pastoral Rule. — CCEL
- **John of Damascus (d. 749)** [T] — Exposition of the Orthodox Faith. — CCEL
- **Anselm (d. 1109)** [T] ★ — Cur Deus Homo; Proslogion; Monologion. — CCEL / Gb
- **Bernard of Clairvaux (d. 1153)** [T] — On Loving God; Sermons on the Song of Songs. — CCEL
- **Thomas Aquinas (d. 1274)** [T] ⚠tr — Summa Theologica (English Province tr., PD); Catena Aurea. — CCEL / Gb
- **Thomas à Kempis (d. 1471)** [H] ★ — The Imitation of Christ. — Gb / CCEL
- **John Wycliffe (d. 1384)**, **Jan Hus (d. 1415)** [T] — select treatises. — CCEL / Ar

## B. The Reformation (16th century)
- **Martin Luther (d. 1546)** [T/C/S] ★ — Bondage of the Will; Commentary on Galatians; Commentary on Genesis; Table Talk; Ninety-Five Theses; Small & Large Catechisms [Sym]; select sermons. — CCEL / Gb
- **John Calvin (d. 1564)** [T/C] ★ — Institutes of the Christian Religion (Beveridge & Allen trs., PD); Commentaries (whole Bible, Calvin Translation Society, PD); Tracts & Treatises; Geneva Catechism [Sym]. — CCEL
- **Huldrych Zwingli (d. 1531)** [T] — On True and False Religion; select works. — CCEL / Ar
- **Heinrich Bullinger (d. 1575)** [T] — Decades. — CCEL / Ar
- **Philip Melanchthon (d. 1560)** [T] ⚠tr — Loci Communes; Augsburg Confession [Sym]. — CCEL / Ar
- **Martin Bucer (d. 1551)** [T] ⚠tr — select. — Ar
- **Theodore Beza (d. 1605)** [T] — Life of Calvin; select treatises. — CCEL / Ar
- **Peter Martyr Vermigli (d. 1562)** [T] ⚠tr — Common Places. — Ar
- **John Knox (d. 1572)** [T/S] — History of the Reformation in Scotland; select works. — CCEL / Gb
- **Thomas Cranmer (d. 1556)**, **Hugh Latimer (d. 1555)**, **Nicholas Ridley (d. 1555)** [S/T] — Works & sermons; Book of Common Prayer 1552/1662. — CCEL / Gb
- **William Tyndale (d. 1536)** [T] — Doctrinal Treatises; Obedience of a Christian Man. — CCEL / Gb
- **Zacharias Ursinus (d. 1583)** [C] — Commentary on the Heidelberg Catechism. — CCEL / Ar
- **Girolamo Zanchi (d. 1590)** [T] ⚠tr — Absolute Predestination (Toplady's tr.). — Ar
- **William Perkins (d. 1602)** [T] — A Golden Chain; The Art of Prophesying. — CCEL / Ar

## C. English Puritans (17th century) — the heart of the collection
- **John Owen (d. 1683)** [T/C] ★ — Mortification of Sin; Communion with God; The Glory of Christ; Indwelling Sin; Of Temptation; The Death of Death in the Death of Christ; Exposition of Hebrews (7 vols) [C]; Pneumatologia (Holy Spirit). — CCEL / Ar
- **Richard Baxter (d. 1691)** [T] ★ — The Saints' Everlasting Rest; The Reformed Pastor; A Call to the Unconverted; Directions for a Sound Conversion. — CCEL / Gb
- **John Bunyan (d. 1688)** [T/H] ★ — The Pilgrim's Progress; The Holy War; Grace Abounding; The Heavenly Footman; Come and Welcome to Jesus Christ. — Gb / CCEL
- **Thomas Watson (d. 1686)** [T] ★ — A Body of Divinity; The Ten Commandments; The Lord's Prayer; The Doctrine of Repentance; The Art of Divine Contentment; All Things for Good. — CCEL / Ar
- **Richard Sibbes (d. 1635)** [T] ★ — The Bruised Reed; The Soul's Conflict. — CCEL / Ar
- **Thomas Goodwin (d. 1680)** [T] — The Heart of Christ in Heaven; Christ Set Forth; select from Works (12 vols). — CCEL / Ar
- **Thomas Brooks (d. 1680)** [T] ★ — Precious Remedies Against Satan's Devices; The Mute Christian; Heaven on Earth. — CCEL / Ar
- **John Flavel (d. 1691)** [T] — The Mystery of Providence; Keeping the Heart; The Fountain of Life. — CCEL / Ar
- **Stephen Charnock (d. 1680)** [T] — The Existence and Attributes of God; Discourses. — CCEL / Ar
- **Thomas Manton (d. 1677)** [C/S] — Exposition of James; Exposition of Jude; sermons on Psalm 119. — CCEL / Ar
- **Jeremiah Burroughs (d. 1646)** [T] ★ — The Rare Jewel of Christian Contentment; Gospel Worship. — CCEL / Ar
- **William Gurnall (d. 1679)** [T] — The Christian in Complete Armour. — CCEL / Ar
- **John Howe (d. 1705)** [T] — The Blessedness of the Righteous. — CCEL / Ar
- **Thomas Vincent (d. 1671)** [T] — The Shorter Catechism Explained; Christ's Certain and Sudden Appearance. — CCEL / Ar
- **Joseph Alleine (d. 1668)** [T] ★ — An Alarm to the Unconverted. — CCEL / Gb
- **George Swinnock (d. 1673)**, **David Clarkson (d. 1686)**, **William Bridge (d. 1670)** [T] — select from Works. — Ar
- **William Gouge (d. 1653)** [C] — Commentary on Hebrews; Of Domestical Duties. — Ar
- **Edward Reynolds (d. 1676)**, **Joseph Caryl (d. 1673)** [C] — Caryl's Exposition of Job. — Ar
- **John Preston (d. 1628)**, **Richard Greenham (d. 1594)**, **Obadiah Sedgwick** [T] — select. — Ar
- **Anthony Burgess**, **Thomas Manton**, **Edward Leigh** — Westminster-divine treatises. — Ar

## D. The Marrow / sanctification core ★ (the app's own doctrine)
The theologian persona is built on Marshall and the Marrow stream — none of it is in the corpus yet. Highest *identity* value.

- **Walter Marshall (d. 1680)** [T] ★★ — The Gospel Mystery of Sanctification (1692). — CCEL / Ar
- **Edward Fisher (fl. 1645)** [T] ★ — The Marrow of Modern Divinity. — CCEL / Ar
- **Thomas Boston (d. 1732)** [T/C] ★ — Human Nature in its Fourfold State; The Crook in the Lot; notes on The Marrow; A View of the Covenant of Grace. — CCEL / Ar
- **Ebenezer Erskine (d. 1754)** & **Ralph Erskine (d. 1752)** [S/H] — sermons; Gospel Sonnets (Ralph). — CCEL / Ar
- **John Colquhoun (d. 1827)** [T] ★ — A Treatise on the Law and the Gospel; Spiritual Comfort. — CCEL / Ar
- **Robert Traill (d. 1716)** [T] — Justification Vindicated; The Lord's Prayer. — CCEL / Ar

## E. Scottish divines & Covenanters
- **Samuel Rutherford (d. 1661)** [H/T] ★ — Letters; Lex, Rex; The Trial and Triumph of Faith. — CCEL / Gb
- **James Durham (d. 1658)** [C] — Commentary on Revelation; Christ Crucified (Isaiah 53); The Law Unsealed. — Ar
- **David Dickson (d. 1663)** [C] — Commentaries on Psalms, Matthew, Hebrews. — Ar
- **William Guthrie (d. 1665)** [T] — The Christian's Great Interest. — CCEL / Ar
- **Hugh Binning (d. 1653)**, **Andrew Gray (d. 1656)** [S] — sermons & treatises. — Ar
- **Thomas Halyburton (d. 1712)** [T] — Memoirs; Natural Religion Insufficient. — Ar
- **John Willison (d. 1750)** [T] — Sacramental Meditations; The Afflicted Man's Companion. — Ar
- **Robert Murray M'Cheyne (d. 1843)** [S/H] ★ — Memoir & Remains (Bonar); sermons; letters. — CCEL / Gb
- **Thomas Chalmers (d. 1847)** [S/T] — The Expulsive Power of a New Affection; select works. — CCEL / Ar
- **Andrew Bonar (d. 1892)** [T] — Commentary on Leviticus; Memoir of M'Cheyne. — CCEL / Ar
- **Horatius Bonar (d. 1889)** [T/H] ★ — God's Way of Holiness; God's Way of Peace; The Everlasting Righteousness; hymns. — CCEL / Gb
- **Robert S. Candlish (d. 1873)** [C] — The Atonement; Commentary on 1 John; on Genesis. — Ar
- **William Cunningham (d. 1861)** [T] — Historical Theology; The Reformers and the Theology of the Reformation. — Ar
- **James Buchanan (d. 1870)** [T] — The Doctrine of Justification; The Office and Work of the Holy Spirit. — CCEL / Ar
- **George Smeaton (d. 1889)** [T] — The Doctrine of the Atonement as Taught by Christ / by the Apostles; The Holy Spirit. — Ar
- **John "Rabbi" Duncan (d. 1870)** [T] — Colloquia Peripatetica. — Ar
- **George Müller (d. 1898)** [H] — Autobiography / A Narrative of Some of the Lord's Dealings. — Gb / CCEL

## F. 18th-century awakening & evangelical Calvinism
- **Jonathan Edwards (d. 1758)** [T/S] ★ — Religious Affections; The Freedom of the Will; Original Sin; Sinners in the Hands of an Angry God; The End for Which God Created the World; A History of the Work of Redemption; Charity and Its Fruits; the Life of David Brainerd. — CCEL / Gb
- **George Whitefield (d. 1770)** [S] ★ — Sermons; Journals; Letters. — CCEL / Gb
- **John Newton (d. 1807)** [H/T] ★ — Cardiphonia (Letters); Olney Hymns (with Cowper); The Life of John Newton. — CCEL / Gb
- **Augustus Toplady (d. 1778)** [T/H] — The Doctrine of Absolute Predestination; hymns ("Rock of Ages"). — Ar
- **John Wesley (d. 1791)** [C/S] — Explanatory Notes on the New Testament [C]; Standard Sermons; A Plain Account of Christian Perfection *(Arminian — include for breadth, tag distinctly)*. — CCEL / Gb
- **William Romaine (d. 1795)** [T] — The Life, Walk, and Triumph of Faith. — Ar
- **Andrew Fuller (d. 1815)** [T] — The Gospel Worthy of All Acceptation; select works. — CCEL / Ar
- **Philip Doddridge (d. 1751)** [T/H] — The Rise and Progress of Religion in the Soul. — Gb / CCEL
- **Isaac Watts (d. 1748)** [H] — Psalms & Hymns; The Improvement of the Mind. — Gb
- **William Law (d. 1761)** [T] — A Serious Call to a Devout and Holy Life. — Gb / CCEL
- **Henry Scougal (d. 1678)** [T] — The Life of God in the Soul of Man. — CCEL / Gb

## G. 19th-century British Reformed
- **Charles H. Spurgeon (d. 1892)** [S/C/H] ★★ — The Treasury of David (Psalms) [C]; Morning & Evening *(have)*; All of Grace; Around the Wicket Gate; The Cheque Book of the Bank of Faith; Lectures to My Students; Metropolitan Tabernacle Pulpit (thousands of sermons) [S]; John Ploughman. — CCEL / Gb
- **J.C. Ryle (d. 1900)** [C/T] ★★ — Expository Thoughts on the Gospels (Matthew–John) [C]; Holiness; Practical Religion; Old Paths; Knots Untied. — CCEL / Gb
- **Octavius Winslow (d. 1878)** [T] — No Condolence Like Christ's / Personal Declension and Revival of Religion in the Soul. — Ar
- **J.B. Lightfoot (d. 1889)**, **B.F. Westcott (d. 1901)**, **F.J.A. Hort (d. 1892)** [C] — Lightfoot on Galatians/Philippians/Colossians; Westcott on John/Hebrews/1 John [C]. — Ar / CCEL
- **Henry Alford (d. 1871)** [C] — The Greek Testament (critical commentary). — Ar
- **Charles J. Ellicott (d. 1905)** [C] — Critical commentaries on Paul's epistles; Ellicott's Commentary for English Readers. — Ar
- **John Eadie (d. 1876)** [C] — Commentaries on Galatians, Ephesians, Philippians, Colossians, Thessalonians. — Ar
- **Patrick Fairbairn (d. 1874)** [T/C] — The Typology of Scripture; Prophecy; Commentary on the Pastoral Epistles. — Ar
- **Robert Haldane (d. 1842)** [C] — Exposition of the Epistle to the Romans. — CCEL / Ar
- **John Brown of Edinburgh (d. 1858)** [C] — Expositions of Romans, Galatians, Hebrews, 1 Peter; The Sufferings and Glories of the Messiah. — Ar
- **William Symington (d. 1862)** [T] — On the Atonement and Intercession of Jesus Christ; Messiah the Prince. — Ar
- **Richard C. Trench (d. 1886)** [D] — Synonyms of the New Testament; Notes on the Parables / Miracles. — Gb / Ar
- **Handley Moule (d. 1920)** [C/T] — commentaries on Romans/Ephesians/Philippians; Outlines of Christian Doctrine. — Ar
- **F.W. Krummacher (d. 1868)** [T] ⚠tr — The Suffering Saviour; Elijah the Tishbite. — Gb / Ar
- **J.C. Philpot (d. 1869)** [S] — sermons; Through Baca's Vale. — Ar

## H. American / Princeton & Southern Reformed
- **Archibald Alexander (d. 1851)** [T] — Thoughts on Religious Experience; Evidences of the Christian Religion. — CCEL / Ar
- **Charles Hodge (d. 1878)** [T/C] ★ — Systematic Theology (3 vols); Commentaries on Romans, 1–2 Corinthians, Ephesians [C]; The Way of Life. — CCEL / Ar
- **A.A. Hodge (d. 1886)** [T] — Outlines of Theology; The Atonement; Commentary on the Westminster Confession. — CCEL / Ar
- **B.B. Warfield (d. 1921)** [T] ★ — The Plan of Salvation; Counterfeit Miracles; Studies collections; select essays. — CCEL / Ar
- **Robert L. Dabney (d. 1898)** [T] — Systematic Theology; The Five Points of Calvinism; Discussions. — CCEL / Ar
- **James H. Thornwell (d. 1862)** [T] — Collected Writings. — Ar
- **W.G.T. Shedd (d. 1894)** [T/C] — Dogmatic Theology; Commentary on Romans. — Ar
- **John L. Girardeau (d. 1898)** [T] — Calvinism and Evangelical Arminianism; The Will in its Theological Relations. — Ar
- **James P. Boyce (d. 1888)** [T] — Abstract of Systematic Theology. — CCEL / Ar
- **John A. Broadus (d. 1895)** [C] — Commentary on Matthew; On the Preparation and Delivery of Sermons. — Ar
- **J.L. Dagg (d. 1884)** [T] — Manual of Theology. — Ar
- **B.M. Palmer (d. 1902)** [T] — The Theology of Prayer; select. — Ar
- **Joseph Addison Alexander (d. 1860)** [C] — Commentaries on Isaiah, Psalms, Mark, Acts. — Ar
- **William Henry Green (d. 1900)** [T] — The Unity of the Book of Genesis; General Introduction to the Old Testament. — Ar

## I. Verse-keyed commentary sets (consolidated — the `get_commentary` win)
Whole- or large-Bible sets not tied to one author above; all PD; each needs the reference-index parser.

- **Matthew Poole (d. 1679)** — Annotations upon the Holy Bible. — CCEL / Ar ★
- **The Pulpit Commentary** (Spence & Exell, 1880s) — whole Bible. — Ar ★
- **Jamieson-Fausset-Brown** *(have)* · **John Gill** *(have)* · **Adam Clarke** *(have)* · **Matthew Henry** *(have)* · **Keil & Delitzsch** *(have)* · **Barnes' Notes** *(have)*.
- **Cambridge Bible for Schools and Colleges** (Perowne, ed.) — Ar
- **Ellicott's Commentary for English Readers** — Ar
- **Lange's Commentary on the Holy Scriptures** (Schaff, ed.) ⚠tr — Ar
- **Meyer's Critical & Exegetical Handbook (NT)** ⚠tr — Ar
- **Frédéric Godet (d. 1900)** ⚠tr — Commentaries on John, Luke, Romans, 1 Corinthians. — Ar
- **Bengel's Gnomon of the New Testament** ⚠tr — Ar
- **The Expositor's Bible** (Nicoll, ed., 1880s–90s) — Ar
> Excluded (not PD): **Robertson's Word Pictures** (renewal 1960); **Vine's Expository Dictionary**; the ICC volumes still in copyright.

## J. Bible dictionaries, encyclopedias & topical (`get_bible_dictionary`)
- **ISBE — International Standard Bible Encyclopedia (1915, Orr ed.)** [D] ★ — Ar / CCEL
- **Smith's Bible Dictionary (1863)** [D] ★ — Gb / Ar
- **Fausset's Bible Dictionary (1878)** [D] — Ar
- **Nave's Topical Bible (1897)** [D] ★ — Ar
- **Torrey's New Topical Textbook (R.A. Torrey, d. 1928)** [D] — Ar
- **McClintock & Strong, Cyclopaedia of Biblical, Theological, and Ecclesiastical Literature** [D] — Ar
- **Cruden's Complete Concordance (1737)** [D] — Gb / Ar
- **Kitto's Cyclopaedia of Biblical Literature** [D] — Ar
- **Buck's Theological Dictionary (1802)** [D] — Ar
- **Trench, Synonyms of the New Testament** [D] — see §G.

## K. Creeds, confessions & catechisms to add (`get_confession`)
Beyond the 21 already loaded — the Lutheran and continental symbols, and the Reformed subordinate standards:

- **Augsburg Confession (1530)** & **Apology** — Ar
- **Formula of Concord (1577)** — Ar
- **The French (Gallican) Confession (1559)** — Ar
- **The Tetrapolitan Confession (1530)** — Ar
- **The National Covenant (1638)** & **Solemn League and Covenant (1643)** — Ar
- **Calvin's Geneva Catechism (1545)** — CCEL
- **Craig's Catechism (1581)** — Ar
- **The New Hampshire Baptist Confession (1833)** — Ar
- **The Waldensian Confession** · **Ten Theses of Bern (1528)** — Ar
- **The Canons of the Council of Orange (529)** — CCEL

## L. Hymnody & devotional classics (`get_devotional`)
- **Isaac Watts** — Hymns and Spiritual Songs; Psalms of David Imitated. — Gb
- **John Newton & William Cowper (d. 1800)** — Olney Hymns. — Gb
- **Rutherford** — Letters (see §E) · **Ralph Erskine** — Gospel Sonnets (see §D).
- **Baxter** — The Saints' Everlasting Rest (see §C) · **Boston** — Fourfold State (see §D).
- **Brother Lawrence (d. 1691)** — The Practice of the Presence of God. — Gb / CCEL
- **Spurgeon** — All of Grace; The Cheque Book of the Bank of Faith (see §G).

---

## Excluded — too modern to ingest (link-out only)
PD-adjacent but **not** clear US-PD; serve as discovery links to Monergism, never full text:
**Geerhardus Vos (d. 1949)**, **J. Gresham Machen (d. 1937)**, **Louis Berkhof (d. 1957)**, **Herman Bavinck (d. 1921, but standard English translations are modern ⚠tr)**, **Abraham Kuyper (d. 1920, most English translations modern ⚠tr)**, **Cornelius Van Til**, and all living/20th–21st-c authors Monergism distributes by permission (Piper, Sproul, Beeke, Ferguson, Packer, etc.).

## Ingestion notes
- **Shape split:** `[C]` and `[D]` works flow to the **MCP reference tools** (need the verse/entry-index parser); `[T] [S] [H]` flow through the **derivative pipeline** as grounded, browsable works.
- **Multi-volume sets** (Owen's Works, Calvin's Commentaries, the Pulpit Commentary) resolve to many source files — count each volume as a fetch unit.
- **⚠tr** works need a confirmed PD English edition at fetch time; the adapters already fail-closed, so a missing PD translation simply skips rather than ingesting a copyrighted one.
- **Archive.org adapter (Phase 2)** unlocks the `Ar`-only long tail — the majority of §C–§K.
