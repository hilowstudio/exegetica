# Study Bible MCP

A self-hosted [Model Context Protocol](https://modelcontextprotocol.io) server that gives Claude
Desktop and Claude Code deep, trustworthy access to study-Bible resources — readable translations,
Hebrew & Greek lexicons, morphology, a concordance, cross-references, and public-domain
commentaries — for pastors, theologians, and seminary students.

## Design principle: own the data

~95% of capability ships as **bundled, openly-licensed data** compiled at build time into a single
portable SQLite database. There are **no required runtime external services** — every word study,
morphology parse, lexicon lookup, cross-reference, and commentary runs against owned data. The only
optional add-ons are copyrighted modern translations (ESV/NIV/etc.), reached through the user's own
API key and never load-bearing: the server works fully without them.

## Status

Early construction. See the build plan and the self-hostable resource catalog for the roadmap.
Data sources are public-domain or openly licensed (mostly PD / CC0 / CC BY / CC BY-SA, with some
pieces under Apache-2.0, MIT, ISC, GPL-3.0, or the Unlicense); see [NOTICE](NOTICE) for attributions.

## Development

```sh
python -m venv .venv
./.venv/Scripts/python -m pip install -e ".[dev]"   # Windows; use .venv/bin/python on POSIX

# Fetch data (STEPBible originals/lexicons + Aquifer study notes + ACAI entities)
python scripts/download_stepbible.py --aquifer

# Build the portable SQLite DB, then layer in the graph + cross-reference data.
# NOTE: build_database.py --rebuild recreates the DB from scratch, so the two
# import_* scripts must be re-run after any rebuild (their downloads are cached).
python scripts/download_lxx.py                      # Greek LXX (Swete) + Brenton English + Copenhagen map
python scripts/download_translations.py             # readable translations: BSB/WEB/KJV/ASV/YLT (USFM)
python scripts/download_commentaries.py              # public-domain commentaries (Henry/Gill/JFB/Clarke/Calvin/K&D)
python scripts/download_catena.py                    # patristic catena (church-father excerpts, prebuilt SQLite)
python scripts/download_theologai.py                 # creeds/confessions/catechisms + UBS parallel passages
python scripts/build_database.py --rebuild          # lexicon, verses, morphology, names, aquifer, ACAI
python scripts/import_theographic.py                # people/place/genealogy graph (CC BY-SA)
python scripts/import_cross_references.py           # OpenBible.info cross-references (CC BY)
python scripts/import_translations.py               # readable modern translations
python scripts/import_lxx.py                        # Greek Septuagint + Brenton + versification (reads the KJV)
python scripts/import_commentaries.py               # public-domain commentaries
python scripts/import_catena.py                      # patristic catena (public-domain fathers)
python scripts/import_theologai.py                   # creeds/confessions/catechisms + UBS parallels
python scripts/build_word_frequency.py               # reader-mode vocabulary (from owned tags; no download)
python scripts/import_hebrew_glosses.py              # Hebrew short definitions + entries BDB lacks, from TBESH
python scripts/download_dictionaries.py && python scripts/import_dictionaries.py   # PD dictionaries (Easton's)
python scripts/download_confessions.py && python scripts/import_confessions.py     # confession proof-texts (verse<->confession)
python scripts/download_devotionals.py && python scripts/import_devotionals.py     # verse-keyed devotionals (Spurgeon)

studybible-mcp --transport stdio                    # run the server
```

### Optional live translations (bring your own key)

ESV and NET are copyrighted and never bundled; they are fetched live at request
time and passed straight through. NET is keyless; ESV needs your own free
non-commercial key:

```sh
export ESV_API_KEY=your-key      # from https://api.esv.org (Windows: setx ESV_API_KEY ...)
```

Then request `translation: "ESV"` or `"NET"` in `lookup_verse` / `get_passage` /
`compare_translations`. Without a key, ESV degrades gracefully to the bundled text.

Data sources and their licenses are listed in [NOTICE](NOTICE). The scripts force
UTF-8 output, so Greek/Hebrew text renders correctly on Windows consoles.

## Web front-end (streaming chat)

A browser chat UI that drives the Claude API over these tools, streaming answers
with live tool activity and a Theologian / Study-Assistant voice toggle. The
Python backend co-locates the MCP server (stdio, in-process) and runs the
Anthropic tool-use loop; the API key never leaves the server. See
[webapp/README.md](webapp/README.md).

```sh
./.venv/Scripts/python -m pip install -e ".[webapp]"
export ANTHROPIC_API_KEY=sk-ant-...        # Windows: setx ANTHROPIC_API_KEY ...
python -m uvicorn webapp.app:app --port 8100   # then open http://localhost:8100 (Google sign-in is registered for localhost)
```

A [Dockerfile](Dockerfile) bakes the read-only DB into a stateless container for
the hosted deployment (add a user-auth proxy in front).

## The Theologian persona

The server ships a pastoral-theological voice, "The Theologian" (Reformed,
exegesis-first, Progressive Covenantalist, with Walter Marshall on
sanctification). It attaches two ways:

- **Always-on orientation.** The server sends a short `instructions` note at
  connect time so Claude works exegesis-first, grounds claims in these tools,
  and knows the full persona is available.
- **On-demand prompt.** The full persona is exposed as the invokable
  `theologian` MCP prompt (Claude Desktop's prompt picker). It takes an optional
  `question` argument to answer a specific question in character. The raw tools
  stay usable in a neutral voice when the prompt is not invoked.

The canonical persona text lives in
[`src/studybible_mcp/prompts/theologian.md`](src/studybible_mcp/prompts/theologian.md).
The same text is mirrored as a Claude Code skill at
[`.claude/skills/theologian/SKILL.md`](.claude/skills/theologian/SKILL.md), so
`/theologian` works inside Claude Code as well; copy that folder to
`~/.claude/skills/` to make it available in every repo. Keep the two copies in
sync when you edit the persona.

## License

Code: MIT. Bundled data: per-source (mostly PD / CC0 / CC BY / CC BY-SA) — see [NOTICE](NOTICE).
