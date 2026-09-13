# Revised ingestion plan — clone the corpus, don't crawl it

**Supersedes** the "Phase 2 archive.org adapter → Phase 3 fetch-per-work" build order in
[reformed-pd-ingestion.md](reformed-pd-ingestion.md). That manifest is still the **target list**
(what belongs in the MCP); this document is the **method** (how we get it in).

## The pivot
A source spike (GitHub deep + HuggingFace + Internet Archive/aggregators, 2026-09-13) established
that **the entire target corpus already exists as pre-built, cleanly-licensed collections.** We can
`clone` / `download` a handful of them and ingest from local files — no per-work fetching, no
gutendex throttling, no archive.org adapter, no live CCEL crawler.

Two problems this also retires for free:
- **Gutenberg is thin on Reformed depth** (a catalog match confirmed only ~16/69; it has the
  classics — Augustine, à Kempis, Bunyan — not Owen/Ryle/Spurgeon's theology). The depth is on CCEL.
- **Verse-keying (the hard part of `[C]` commentary ingestion) is pre-solved** — the CCEL dataset
  ships scripture refs per paragraph, and the patristic dataset is already indexed by verse.

## The sources (all verified; clone/download handles)

### Whole CCEL — the motherlode (Reformed / Puritan / medieval depth)
- **`jncraton/ccel-paragraphs`** (HuggingFace dataset) — **738 titles, 2.2M paragraphs**, the bulk of
  CCEL. Parquet, 8.8 GB. Columns: `text`, `thml` (CCEL markup), **`refs` (scripture refs per
  paragraph)**, `author`, `author-short-form`, `title`, **`rights` (per-work license → filter to
  clean PD)**, `published`, plus a precomputed embedding.
  - License: **CC BY-SA 4.0**. Use per our locked policy — **ground & derive, attribute, never
    redistribute CCEL's verbatim text/ThML**. Filter `rights` to genuinely PD works.
  - Get it: `hf download jncraton/ccel-paragraphs --repo-type dataset` (or stream/filter the Parquet
    with `pandas`/`pyarrow` so we never hold all 8.8 GB in memory).

### Church fathers (§A) — pick one, both clean
- **`gregorycrane/nicenefathers`** (GitHub) — complete ANF + NPNF as **24 tidy TEI-XML volumes**,
  47 MB. Cleanest *structure*. `git clone https://github.com/gregorycrane/nicenefathers`.
- **Internet Archive `the-complete-ante-nicene-nicene-and-post-nicene-church-fathers`** — the whole
  ANF+NPNF as one **87 MB plain-text** file under a **CC Public Domain Mark** (cleanest *license*).
  `ia download the-complete-ante-nicene-nicene-and-post-nicene-church-fathers <file>_djvu.txt`.
- **`sermonindex/early-church-fathers`** (HuggingFace) — 68k patristic passages **keyed to the exact
  Bible verse** (349 fathers), CC BY 4.0. Drops straight into the catena / `get_commentary` shape and
  complements the catena we already ship.

### Big-author sets — clean, structured, ready
- **`lyteword/*`** (GitHub, **CC0**, Markdown): `chspurgeon-sermons` (63 vols), `chspurgeon-tod`
  (Treasury of David — verse-keyed `[C]`), `chspurgeon-mae` (Morning & Evening), `chspurgeon-fcb`
  (Faith's Checkbook), `mhenry-complete` + `mhenry-concise` (Matthew Henry — we already ship Henry,
  so optional). CC0 is the cleanest license available.
- **`eddyekofo94/works_of_owen_epub_conversion`** (GitHub) — the **Complete Works of John Owen**
  (16-vol Goold + 7-vol Hebrews + Biblical Theology) as finished EPUBs. PD content, no repo license.

### Creeds, confessions & catechisms (§K)
- **`NonlinearFruit/Creeds.json`** (GitHub, 28★) — **40+** Reformed + ecumenical standards as JSON
  (Westminster WCF/WLC/WSC, 1689 LBCF, Heidelberg, Belgic, Dort, Savoy, Helvetic 1st/2nd, Scots,
  French, Waldensian, the ecumenical creeds). Expands our current 21 → 40+.
  `git clone https://github.com/NonlinearFruit/Creeds.json`.

### Discovery-only / excluded (do NOT ingest)
- **Monergism** — their terms *explicitly* forbid incorporating their editions into "an
  **artificial-intelligence system**, database, or other distribution platform." Hard no; link-out
  for discovery only.
- **CCEL direct** — publishes no bulk download and requires permission to *republish*; we take CCEL
  content via `ccel-paragraphs` and only *derive* from it.
- **PRDL** — a link catalog (110k titles → external hosts). Discovery only.
- **sacred-texts.com** — bulk is a paid DVD; mostly off-topic.
- `timothyhartzog/theology-corpus` — advertises CCEL/Gutenberg ThML but the prose is gitignored
  crawler output; the populated dirs are Greek/Hebrew + lexicons we already have.

## Licensing framework (applied at ingest)
| Class | Sources | Rule |
|---|---|---|
| **CC0 / PD Mark** | lyteword/*, IA fathers, BobTheUnicorn Spurgeon | Freely usable — ingest and, for US-clear works, may publish full_text. |
| **PD content, no repo license** | nicenefathers, Owen, Creeds.json | The underlying works are pre-1929 PD → usable; attribute the source repo as courtesy. |
| **CC BY-SA 4.0** | ccel-paragraphs, sermonindex fathers | Ground & derive; attribute (Craton/CCEL, SermonIndex); filter `rights` to PD; do not redistribute the verbatim CCEL edition/ThML. |
| **Prohibited** | Monergism editions | Never ingest. Discovery link-out only. |

## How each maps to the MCP (the two shapes)
- **Verse-keyed `[C]` → the reference tools** (`get_commentary`, catena): the `ccel-paragraphs` `refs`
  column and the `sermonindex/early-church-fathers` verse index give us passage→text rows directly —
  the reference-index parser we feared building is largely replaced by *reading a column*.
- **Treatises / sermons `[T] [S] [H]` → the derivative pipeline**: Owen, Spurgeon's sermons, the
  Puritan treatises become grounded, browsable derived works (summary/themes/objectives).
- **Confessions `[Sym]` → `get_confession`**: `Creeds.json` loads as structured documents.

## Patristic full works → Living Library (decided 2026-09-13)
The MCP already covers the fathers verse-keyed (`patristic_catena`, 85,654 excerpts / 302 fathers),
so **full patristic works go to the teacher Living Library** (browsable derived works), **not** a
duplicate MCP table. Source choice, after evaluation: **take them as the patristic slice of the
Phase B `ccel-paragraphs` pull** (already per-`title`/`author`, English, with `refs`) — do *not*
build a bespoke splitter. Rejected sources: `ntwkst/patristics` (Portuguese, not English) and
`gregorycrane/nicenefathers` (English TEI but work boundaries are only in `<head>` text → needs
one-off heuristics; and it's CC BY-SA anyway, same class as `ccel-paragraphs` but harder to split).

## Phase A status (done)
- **Confessions → MCP:** `scripts/import_creeds_json.py` added **21 net-new** PD confessions to
  `historical_documents` (get_confession: 21 → 42 docs), dedup-verified, PD-gated. Local-ingest path
  proven. (Live tool serves them after an MCP restart — DB is opened read-only/immutable.)
- **Fathers:** routed to the Living Library via Phase B (above), not ingested standalone.

## Revised build order
1. **Phase A — prove the local-ingest path** on the smallest, cleanest sets:
   - `Creeds.json` → expand `get_confession` (21 → 40+).
   - `nicenefathers` (or the IA plain-text bundle) → a few patristic full works (§A).
   - Deliverable: a `scripts/ingest_local.py` that reads a local collection and writes MCP rows /
     Living Library derivatives, proven on these two.
2. **Phase B — the CCEL bulk** (`ccel-paragraphs`): download, filter `rights` to PD, group paragraphs
   by `title` into works, ingest — `[C]` works indexed by `refs`, `[T]` works through the derivative
   pipeline. This is the ~585-manifest's Reformed/Puritan/medieval depth in one pull.
3. **Phase C — the CC0 author sets**: Spurgeon (Treasury of David `[C]`, sermons `[S]`), Owen, and
   the verse-keyed `sermonindex` fathers into the catena.
4. **Retired**: the archive.org adapter, the live CCEL crawler, and per-work gutendex verification.
   Gutenberg stays only for the handful of classics it uniquely carries well (Augustine's *Confessions*
   #3296, Bunyan #131, à Kempis, d'Aubigné, hymnody) — sourced via the adapter we already trust, now
   fixed for pre-modern names.

## Open decisions
- **Publish full_text vs ground-only, per class.** CC0/PD-Mark works that are US-clear (pre-1930) can
  store full_text; CC BY-SA CCEL content grounds/derives only. The `rights` + `published` columns
  drive this per work.
- **Dedup against what we already ship** (Matthew Henry, Calvin, JFB, Gill, Clarke, K&D, Barnes, the
  existing catena) so we don't double-ingest.
- **Storage**: 8.8 GB Parquet + a 500 MB fathers set — stream/filter rather than committing blobs;
  cache under `.seed_cache/` like the classics seed.
