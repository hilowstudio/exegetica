# Academic and scholarly sources: research spike

**Status:** research pass, 2026-10-20. Nothing built. Same rule as the other Modes: prefer sources we can download once and self-host; a live API is a fallback.

## Recommendations

1. **Metadata backbone (self-hosted): OpenAlex snapshot.** About 626 million scholarly works, CC0, free quarterly snapshot on S3 with no account. Load only the fields each Mode needs (History, Political Science, Education for Social Sciences) rather than the full ~745 GB. Abstracts come only as a word-position index, not running text.
2. **Citation checking: Crossref.** 180 million records; the 2026 Public Data File is 208 GB; metadata is effectively free of copyright.
3. **Open full text: PubMed Central Open Access** (8.3 million articles, free S3 bucket; serve only articles whose license is CC BY or CC0). **Semantic Scholar's s2orc_v2** (16 million full-text papers, ODC-BY) is the broadest set for other subjects; check its per-dataset rights before serving passages.
4. **Live API fallback: OpenAlex API** (free key, $1 of usage per day).
5. **By subject:**
   - **Education: ERIC.** 2.1 million records, 528,000 with full text, free bulk XML, no key; government-authored reports are public domain.
   - **Science: PubMed Central** with **PubMed**, and **arXiv** (CC0 metadata and abstracts; link to arXiv for full text, don't serve it).
   - **Humanities and history: OpenAlex** filtered to those fields, **DOAJ** (CC0, open-access journals), and the **Library of Congress** for primary sources.

## Not a fit

| Source | Why |
|---|---|
| CORE | Its terms require a license for projects that serve only one organization's users, which is us; its dataset is for machine processing, not reading |
| JSTOR Constellate | Shut down July 1, 2025 |
| Internet Archive Scholar (fatcat) | Frozen since February 2024 (third-party reports) |
| Unpaywall data feed | Subscriber-only; OpenAlex now covers the same open-access links under CC0 |
| BASE | API limited to whitelisted users |
| HathiTrust Extracted Features | Word counts per page, not readable text: good for analysis, not for grounding answers |

## Licensing rule of thumb

Store and serve metadata freely (CC0 or uncopyrightable). Treat abstracts as possibly publisher-copyrighted: quote briefly, cite, and link; don't republish them in bulk. Serve full text only when the article's own license is CC BY or CC0.

## Not verified

Semantic Scholar download keys and per-dataset rights; Unpaywall license; Europe PMC limits; BASE terms; fatcat's frozen status; arXiv's Kaggle license; ERIC and NCBI rate limits.

## Key links

OpenAlex snapshot: help.openalex.org/download-all-data/openalex-snapshot (license: openalex.s3.amazonaws.com/LICENSE.txt) · Crossref Public Data File: crossref.org/services/metadata-retrieval/public-data-file/ · Semantic Scholar datasets: api.semanticscholar.org/datasets/v1/release/latest · PMC on AWS: pmc.ncbi.nlm.nih.gov/tools/pmcaws/ · ERIC downloads: eric.ed.gov/?download · DOAJ data dump: doaj.org/docs/public-data-dump/ · arXiv bulk data: info.arxiv.org/help/bulk_data.html · CORE terms: core.ac.uk/terms · Library of Congress API limits: loc.gov/apis/json-and-yaml/working-within-limits/
