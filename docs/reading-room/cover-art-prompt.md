# Cover art prompt: the Exegetica cloth edition

A boilerplate prompt for generating Reading Room covers that look native to the app. Fill in the four variables per book; everything else stays fixed so the library reads as one series.

## Template and why

**Model series:** Penguin Clothbound Classics (Coralie Bickford-Smith, 2008 onward). Its rules: never more than two colors per cover, a rectangular border, title at the top and author at the bottom, and one motif from the story repeated as a pattern in the middle. It reads at thumbnail size, it makes a shelf of hundreds of books look like one edition, and the Reading Room's cloth-bound book wraps already follow the same idea.

**Our twist:** the motif is drawn in the app's own illustration style (the garden art behind the chat page): flat, layered gouache shapes with dry-brush edges, no outlines, soft and slightly muted. Clothbound uses crisp foil line art; ours is painted.

**Palette:** three brand colors only: parchment, ink and rose (table below). Every book gets two editions that mirror the app's two modes. The **light edition** is parchment cloth, and the **dark edition** is ink cloth. The second color, the "foil" that the border and motif are drawn in, is rose or the opposite neutral, chosen per section. No other colors.

**Type:** the app sets titles in Spectral (a literary serif, semibold) with labels in IBM Plex Mono capitals. The prompt asks the generator to letter the title in a Spectral-like serif and the author in small spaced capitals, both in the foil color. Generators still slip on lettering, so check spelling on every image and regenerate rather than retouch. Version A (art only, typeset afterwards) remains as a fallback for a model that can't letter.

## The prompt (Version B: with lettering, the house prompt)

```
A book cover in the style of a cloth-bound classic edition, flat design. Portrait orientation, 2:3 aspect ratio, 1600 × 2400 pixels.

The whole cover is a single flat field of {CLOTH COLOR NAME} ({CLOTH HEX}), like matte book cloth with a faint linen weave texture. A thin rectangular border, inset about 5% from the edges, in {FOIL COLOR NAME} ({FOIL HEX}).

Across the top 20% inside the border, the title "{TITLE}" in a refined literary serif typeface (like Spectral semibold) in {FOIL COLOR NAME} ({FOIL HEX}), centered, set large in title case, breaking onto two or three balanced lines if it is long. Across the bottom 10% inside the border, the author line "{AUTHOR}" in small, widely spaced capital letters in the same {FOIL COLOR NAME}, centered on one line. Spell the title and author line exactly as given, letter for letter, with no extra words. Keep both bands clear of pattern.

Between the title and the author, the middle of the cover is filled with a repeating pattern of {MOTIF}, arranged in an even, slightly staggered (half-drop) grid of 4 to 5 rows, every repeat the same size and orientation, like a Victorian binding pattern. Draw each motif as a simple flat silhouette in {FOIL COLOR NAME} ({FOIL HEX}), in a hand-painted gouache screen-print style: layered flat shapes, soft dry-brush edges, no outlines, no shading, no gradients.

Exactly two colors: the {CLOTH COLOR NAME} cloth and the {FOIL COLOR NAME}. Calm, elegant, restrained, timeless.

No other text anywhere: no subtitle, no publisher name, no logo, no watermark, no signature. No photograph, no 3D, no book mockup, no spine, no shadows, no glossy or metallic shine, no frame around the cover, no other colors.
```

## The prompt (Version A: art only, fallback)

Use Version B, replace its "Across the top 20%..." paragraph with this, and change the last paragraph's opening to "No text, no letters, no numbers, no title,":

```
Leave a plain band of empty cloth across the top 20% and the bottom 10% inside the border, with nothing in them (the title and author will be added later).
```

## Variables

| Variable | How to fill it |
|---|---|
| `{CLOTH COLOR NAME}` / `{CLOTH HEX}` | Parchment (light edition) or ink (dark edition) |
| `{FOIL COLOR NAME}` / `{FOIL HEX}` | The section's foil, from the table below |
| `{MOTIF}` | One object from the book, named concretely (see the motif guide) |
| `{TITLE}`, `{AUTHOR}` | The title as the Reading Room shows it (spell out "Vol." as "Volume"). The author line is the author's name, "Edited by ..." for an editor, or the original title-page pen name. No nested quotation marks. |

### Colors and editions

| Brand color | Hex | Role |
|---|---|---|
| Parchment | `#f0e8dc` | Light-edition cloth; foil on ink |
| Ink | `#1e2026` | Dark-edition cloth; foil on parchment |
| Rose | `#c05a64` | Foil on parchment |
| Soft rose | `#dd8089` | Foil on ink (the app's dark-mode rose, so it reads on the dark cloth) |

| Edition | Cloth | Foil options |
|---|---|---|
| Light | parchment `#f0e8dc` | rose `#c05a64`, or ink `#1e2026` |
| Dark | ink `#1e2026` | soft rose `#dd8089`, or parchment `#f0e8dc` |

Each section picks one foil per edition, and every book in it follows. Generate both editions of a book with the same motif, so the two read as one book in two bindings. A book on several shelves takes its first section's assignment.

| Section | Light edition | Dark edition |
|---|---|---|
| Sports & Recreation | parchment + rose | ink + soft rose |

Other sections are assigned as they're generated.

### Motif guide

Clothbound's strength is that each motif comes from inside the story, not from the genre. Pick one thing a reader would recognize once they've read the book, and name it concretely enough to draw as a silhouette:

- **Good:** "a wolf's head in profile" (*The Hound of the Baskervilles*), "a single brass key" (*The Secret Garden*), "a bat with folded wings" (*Varney the Vampyre*), "a ringed planet" (a *Galaxy* issue), "a lantern" (*The Pilgrim's Progress*).
- **Avoid:** people's faces or full figures (they don't repeat well and drift off-style), scenes, anything that needs text to read, symbols with a meaning outside the book.
- **For a pulp issue collection,** take the motif from the lead story, or from the issue's own cover art.

## Worked examples

**Fish Stories** (Sports & Recreation): light edition is cloth `warm parchment (#f0e8dc)`, foil `rose (#c05a64)`. Dark edition is cloth `deep ink charcoal (#1e2026)`, foil `soft rose (#dd8089)`. Motif: `a big-mouthed bass leaping clear of a small ripple`. Full prompts for the section are in [covers/sports-recreation.md](covers/sports-recreation.md).

## Generating and checking

- **Size:** 1600 × 2400 px (2:3 portrait). If a model caps lower, use 1024 × 1536 or its nearest 2:3 option (Midjourney: `--ar 2:3`). Store as usual; the cover tool resizes to 400px WebP.
- **Check every image for:**
  - exactly two colors, and the right two for the edition;
  - a pattern that is even and repeats;
  - title and author spelled exactly, with no extra words (empty bands for Version A);
  - no stray letters, signatures or watermarks.
- **Keep the series honest:** generate a pilot set of five sections first and view them side by side on the shelf before doing the library. If one drifts (too detailed, extra colors, a different painting style), add a correction to the prompt for everyone rather than fixing that one book.
