# 14. Type design, lettering, calligraphy, letterpress

Serves RISD courses:
- Type Design (GRAPH 3859): a serif text typeface
- Type + Code (Glyphs)
- Workshop: Calligraphy (3195)
- Workshop: Letterpress (3178)
- Typography I (constructing letters)

## Lettering, calligraphy and type
- Calligraphy is written: each letter is made in a few strokes with a tool.
- Lettering is drawn: built up and refined for one specific use.
- Type is a system of reusable glyphs designed to combine with any other glyph.
- The three train each other. Calligraphy teaches stroke logic and rhythm, lettering teaches form, and type design teaches systems and spacing.

## Calligraphy (the workshop's focus: broad-edged tools, humanist scribes, italic)
- A broad-edged pen held at a constant angle produces thick and thin strokes automatically. The pen angle sets where the thins fall:
  - roughly 30 degrees for foundational and roman-derived hands
  - roughly 40 to 45 degrees for italic
- Proportion is measured in nib widths. The x-height of a hand is a set number of nib widths, about 4 to 5 for the common hands, so letters scale consistently with the pen.
- Ductus: the order and direction of strokes. Good letters come from consistent ductus.
- Spacing: even areas of white inside and between letters, and the rhythm of the stems.
- Lineage:
  - Edward Johnston's Foundational Hand, from the 10th-century Ramsey Psalter. He set it out in Writing and Illuminating and Lettering (1906).
  - Humanist minuscule (Poggio and Niccoli, early 1400s Florence) became the model for roman type (Jenson, Venice 1470).
  - Chancery italic (Ludovico degli Arrighi, La Operina, 1522) is the ancestor of italic type. The first italic type was cut by Francesco Griffo for Aldus Manutius in 1501.
  - The course singles out Renaissance italics as a model for modern handwriting.
- Where serifs came from: Edward Catich (The Origin of the Serif, 1968) argued that the Roman inscriptional capitals were painted with a flat brush before being cut. That would make serifs the traces of brush strokes.
- What it trains: the hand, the eye (proportion, rhythm, spacing) and the mind (the logic of letterforms). It also explains why type looks the way it does.

## Contrast models (Noordzij, The Stroke)
- Translation: a broad nib moved at a constant angle. Thick and thin follow the pen angle, and the stress is diagonal. This is the humanist and garalde model.
- Expansion: a pointed pen whose stroke swells with pressure. Thick and thin follow direction, and the stress is vertical. This is the didone and modern model.
- Knowing which model a face follows keeps its contrast consistent.

## Designing a text typeface (Type Design course: serif text face)
- Brief: intended use (books, screens, small sizes), voice, constraints (width, economy, languages).
- Control characters first:
  - lowercase n and o (straight and round), then a, e, s, g and the rest
  - capitals H and O, then the others
  - n sets the stem weight, x-height, arches and serifs. o sets the round proportions and overshoot.
- Proportions:
  - x-height relative to cap height and ascenders
  - a larger x-height reads better at small sizes but looks less classical
  - ascenders slightly taller than capitals in many text faces
  - descender length
- Weight and contrast: stem thickness relative to x-height sets the colour on the page. Contrast and axis follow the chosen stroke model.
- Optical corrections (where the eye overrides geometry):
  - Overshoot: round and pointed letters extend past the baseline and x-height (by a few percent) to look the same size as flat letters.
  - Horizontal strokes are drawn thinner than vertical ones of the same apparent weight, even in a "monoline" sans.
  - Joins are thinned. Ink traps open junctions at small sizes and in some print processes.
  - The optical centre sits above the geometric centre. The crossbar of H sits slightly high, and the top halves of B, S and 8 are smaller than the bottoms.
  - o is wider than n. Round letters need more width to look equal.
- Bézier drawing:
  - points at the extremes (top, bottom, left, right of curves) with horizontal or vertical handles
  - as few points as possible
  - smooth tangent continuity
  - no kinks
  - fonts use cubic curves (PostScript and CFF) or quadratic curves (TrueType)
- Spacing comes before kerning (Tracy, Letters of Credit, Cheng, Designing Type):
  - Space letters to balance the white inside them (counters) with the white between them.
  - Method: set the sidebearings of n in strings like "nnnnn", and of o in "nonon". Derive other letters from those (straight sides like n, round sides like o, plus the exceptions). Use H and O the same way for capitals.
  - Proof in real words and paragraphs at text size.
- Kerning fixes only the exceptions spacing cannot solve:
  - pairs such as To, AV, Ty, LT, f followed by a quote, and numerals
  - kerning classes keep the work manageable
  - over-kerning shows good spacing was missing
- Character set:
  - basic Latin plus accented letters for target languages (Latin-1 and Latin Extended-A at minimum)
  - figures (oldstyle and lining, tabular and proportional)
  - punctuation and symbols
  - small caps and ligatures
  - a companion italic: usually narrower, cursive in construction, sloped, with its own spacing
- Proofing:
  - test words like "hamburgefonstiv" and "adhesion"
  - real texts in several languages
  - print at intended sizes, check colour evenness
  - iterate many times
- Production:
  - tools: Glyphs (Mac only, as the course notes), FontLab, RoboFont
  - masters and interpolation to make weight families and variable fonts. Masters must be point-compatible (same contours and point order).
  - export to OTF and TTF, and WOFF2 for the web
  - licensing models: desktop, web, app, and the SIL Open Font License

## Variable fonts
- One file holds a design space defined by axes (weight, width, optical size, slant, custom). Instances are named points in that space.
- Uses:
  - responsive typography (adjust width and weight to the container)
  - optical sizing
  - grade for dark mode
  - animation and interaction (Type + Code, Advanced Type Studio)

## Letterpress (workshop: from letterpress to inkjet)
- Vocabulary:
  - a sort is one piece of type
  - type cases (the upper case held capitals, the lower case small letters, hence the names)
  - leading was literally strips of lead between lines
  - furniture (wood spacing), chase (frame), quoins (locks)
  - composing stick
  - makeready (evening the impression)
  - impression and "bite" into soft paper
  - wood type for large sizes
  - Vandercook proof presses
- Discipline: physical type makes spacing, measure and leading concrete, because every space is a piece of metal.
- Hybrid practice (the course): run letterpress prints through inkjet plotters, digitize metal type, combine analog texture with digital precision.
- The course frames effective graphic design as integrating the human factor, technology and aesthetics.

## Sources
From training: Noordzij, The Stroke. Johnston 1906. Catich 1968. Cheng, Designing Type (2nd ed.). Tracy 1986. Smeijers, Counterpunch. Unger, Theory of Type Design. Glyphs Handbook. Gaskell, A New Introduction to Bibliography (letterpress practice). RISD course descriptions (verified this session).
