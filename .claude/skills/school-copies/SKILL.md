---
name: school-copies
description: >-
  Bring school-provided book PDFs (book-copies/) into the Reading Room as school-only titles, and proof them by hand:
  extract (text layer first, Tesseract OCR for pages without one), map the chapters, build a clean working text,
  proof it in context and against the page images, record every correction, load it for YCS accounts only. Use when
  Adam supplies more books for the school, or asks to fix, re-proof or publish a school copy.
---

# School copies: from PDF to the Reading Room

Yorkville Christian's principal and curriculum lead provide these books for use with YCS school accounts (Adam,
2026-11-09). Treat files that come this way as authorized; don't ask for the school's agreements. They are in
copyright, so the PDFs stay in `book-copies/` (gitignored) and every working file stays in
`.seed_cache/school/<slug>/` (gitignored). Nothing here calls a model or the network.

Two scripts do the work:
- `scripts/ingest_school_copy.py`: `extract`, `propose`, `build`, `load`.
- `scripts/proof_school_copy.py`: `measure`, `suspects`, `second`, `triage`, `marks`, `crop`, `fix`.

Both print their usage with `-h`. Tesseract lives at `C:\Program Files\Tesseract-OCR`; pypdfium2 and pytesseract are
in `.venv`.

## The steps, for each PDF

1. **Name it.** Slug `author-name_title` in lowercase with hyphens (`warren-w-wiersbe_be-daring`).
2. **Extract.** `ingest_school_copy.py extract book-copies/<file>.pdf --slug <slug>`. Pages already read by OCR are
   kept on a re-run (`--fresh` redoes them). Runs at about 5 seconds per OCR page; start several books in the
   background at once.
3. **Propose the chapters.** `propose <slug> --title "…" --author "…"`. Read what it prints: chapters come from the
   PDF's outline or its printed contents page, with the page offset from the running heads.
   - Check every title and start page against the book.
   - Contents, praise pages and ads are marked `"skip": true`.
   - `text_ends` must be the last page of prose (ads, reader surveys and the back cover come after).
   - Correct `book.json` by hand where it's wrong.
4. **Rights.** Read the copyright page (`crop`, or the text in `pages.jsonl`) and set `book.json`:
   - `rights`: `© <year> <holder>, provided by Yorkville Christian School for its students and staff`
   - `isbn` and `edition`, noting when the file's edition differs from the school's list
     (`docs/school/` has the list; the curriculum workbook sits at the repo root)
   - `dedication`, checked against the page image (italic display type is often misread)
   - When the file has no copyright page, ask Adam for the year and publisher.
5. **Build.** `build <slug>` writes `work.md`, `proof.md` and, once fixes exist, `corrections.md`.
6. **Measure.** `proof_school_copy.py measure <slug>`. Read the gates (below).
7. **Proof** (below).
8. **Load locally.** `load <slug>` writes the book into `db/books.db` with `access='school'`. Restart the 8100 server
   for Adam and let him read it. Nothing is published until he says so.

## The gates, and when to call a stronger model

`measure` prints these. Each one tripped means look before you trust the book:
- **More than 1% of paragraphs start in lowercase.** Paragraph breaks are wrong; the text layer may be out of reading
  order or misplacing words.
- **A chapter opens mid-sentence.** The opener's display lines were mishandled, or a chapter start page is wrong.
- **More than 5 short quotations.** They may be subheadings set centred and bold at text size (Crazy Love), or hymn
  stanzas (fine). Read them.
- **More than 2 unusual words per 1,000.** A heavy proof; expect pen marks or a poor scan.
- **A chapter with more than 15 subheadings.** Body lines are being read as headings.

When a gate trips because the pipeline's rules don't fit a new layout (not just a few bad words), stop and say so.
That work needs Opus at high effort. Routine books (an ebook, a clean scan, every gate quiet after build) are fine on
Sonnet at medium effort.

## Proofing by hand

Adam's rule: read each suspect in its sentence and hand-fix it. Never guess a garbled word: where the sentence isn't
enough, read the page image. Twice in the first batch a guess would have been wrong ("lead" where the scan says
"teach", "orders" where it says "directions").

1. `suspects <slug>`: words outside a wide vocabulary, in context.
2. `second <slug>` then `triage <slug>`: a second, independent reading. Its disagreements catch misreads that are real
   words, which no dictionary can (Be Daring's layer read l as f: light became "fight", lives "fives", lie "He").
3. `marks <slug>`: stray marks from pen strokes and OCR (lone quotation marks, `|`, `_`, doubled half-words).
4. `crop <slug> <page> "<words on the line>" --up 1 --down 2` to read any spot against the scan.
5. Record each correction with `fix <slug> "<from>" "<to>"`, or `fix <slug> --near "<start>" "<end>" "<to>"` for spots
   with hard-to-type characters. `fix` refuses text that isn't in the book, text that occurs more than once (add words
   around it, or `--all` for a correction meant everywhere, like `w.` to `vv.`), and spans over 600 characters. For a
   fix that contains line breaks, append `[from, to]` to `book.json` from Python with the same checks.
6. Rebuild, rerun the lists, and repeat until what's left is real words, names and the book's own spellings.
7. Load, and tell Adam the counts by kind, what was rebuilt from the page image, and what was left as printed.

Rules that hold while proofing:
- **Restore what the book printed.** A misspelling the book itself prints (Be Daring's "Aeropagus", "McQuilken")
  stays, and is listed for Adam.
- **Fixes live in `book.json`**, applied by `build`, so a rebuild keeps them. A fix that stops matching is reported,
  never dropped silently. `corrections.md` lists them all for review.
- **Freeze the shared rules mid-review.** A problem in one book is fixed in that book's `book.json`. Change the
  pipeline only when a new layout needs it, then rebuild every book and check that its counts still hold.
- **Don't reproduce the books' text in chat** beyond a phrase. They're in copyright.

## What the scans have taught (each cost a rebuild)

- An archive.org text layer has a box per word, not in reading order. Lines are rebuilt from the characters'
  positions.
- U+FFFE marks a line-end hyphen, and the layer misplaces the rest of the word on the next line. So a lowercase line
  after one without a sentence end always continues the paragraph.
- Tesseract writes a line-end hyphen as `¬`.
- Both scans read `vv.` as `w.` (and `wv.`, `vw.`).
- A library copy someone underlined makes OCR drop or scramble whole lines. Rebuild those passages from the image.
- Italics are not carried over from any file yet.
- Tesseract at 2,000 pixels wide reads as well as the scans' own text layers; more resolution gains nothing.

## Other kinds of file (added with the second batch, 2026-11-09)

- **EPUB.** `extract` reads it into `blocks.jsonl`; `propose` maps chapters from the contents list
  (`--toc-depth`, `--toc-under` for one book of a collection, `--headings h2,h3` for the book's own headings).
  Ebooks made from scans need the per-book switches in `book.json`: `requote` (pair quotation marks within a
  paragraph), `split_dialogue`, `dashes` (spaced hyphens are dashes), `patterns` ([regex, replacement] for a
  book's systematic misreads), `drop_text` (furniture set as paragraphs).
- **A PDF whose chapters start mid-page** (a text file set as a PDF): `flow <slug>` rebuilds the paragraphs into
  the same block stream, then map chapters by block as for an EPUB.
- **A maths textbook.** OCR can't read equations. `scripts/vision_transcribe.py <slug>` sends each page image to
  Claude Haiku 5.5 for Markdown with TeX (the reader renders it with KaTeX); about $0.0008 a page, so ask Adam
  before a run. Set `"kind": "vision"`; `build` stitches the pages by chapter page range and falls back to OCR
  for a page the API's content filter blocks. Used copies carry readers' handwriting and answers: the prompt
  transcribes print only; check fallback pages for handwriting.
- **Access.** `"access": "school"` shelves a copy for YCS accounts; `"access": "reference"` (textbooks,
  curricula) never appears on a shelf and is found by teachers in the Prep Room's book search.
- **Front matter.** `dedication`, `epigraphs` ([{lines, cite}]) and `shelf` go in `book.json`; `rights_source`
  says where a rights line came from when the file has no copyright page.
- **Scans with drop caps.** `"opener": "after_title"` keeps a chapter's first line that OCR would drop as display
  type; then read every opening against the page image (crop) and restore it. Guessing failed twice ("Soon"
  for "Shortly", a lost first line).
- `running_heads` names heads and feet to drop (top or bottom margin, a page number beside them allowed).

## Publishing (only when Adam says)

Commit the code (never the PDFs or `.seed_cache`), publish `db/books.db` to R2 with
`scripts/publish_db.py books` (production fetches it, about 9 minutes for the 8.5 GB file), and deploy through
`scripts/predeploy.py --deploy` from a clean worktree. School copies are served only to signed-in YCS accounts,
teachers and admins (`webapp/reader.py`, `may_read_school`); everyone else gets "not found".
