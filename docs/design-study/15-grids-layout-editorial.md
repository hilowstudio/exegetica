# 15. Composition, grids, layout and editorial design

Serves RISD courses:
- Design Studio 1 to 4
- Newly Formed (3324)
- Reframing the Poster (2010)
- ABCs of Book DNA (2211)
- Design for Publishing (3302)
- Introduction to Book Arts (2355)
- (Counter)Publishing Studio
- Typography I and II

## Composition fundamentals
Lupton and Phillips, Graphic Design: The New Basics, gives the working vocabulary:
- Point, line, plane: the elementary marks.
- Rhythm and balance. Symmetry is static and formal. Asymmetry is dynamic and balanced by weight and tension.
- Scale. It is relative, and cropping changes perceived scale and intimacy.
- Texture: visual and actual.
- Colour. See [16](16-color.md).
- Figure and ground: positive and negative shapes, sometimes deliberately ambiguous (stable, reversible, ambiguous).
- Framing: what the edge includes and excludes, and how crops direct attention.
- Hierarchy: order of importance through size, position, colour, space.
- Layers and transparency: overlapping planes, simultaneous readings.
- Modularity: units that combine.
- Grid. See below.
- Pattern: repetition by rules.
- Diagram: relationships made visible.
- Time and motion: sequence, pacing, change.
- Rules and randomness: systems that generate variation. See [17](17-identity-branding-systems.md).

Other working ideas:
- Visual weight depends on size, value (darkness), colour saturation, isolation (a lone object weighs more), texture and position (higher and farther from centre weighs more).
- Every composition needs an entry point and a path for the eye. One clear focal point beats several competing ones.
- Negative space is active. It groups, separates, gives emphasis and lets things breathe.
- Alignment creates order. Strong shared edges make a layout feel intentional. Near-misses look like mistakes.
- Basic checklist (Robin Williams, The Non-Designer's Design Book): contrast, repetition, alignment, proximity.

## Form study as research (Newly Formed)
- The course states that form need not follow function. Form is studied for its own sake on any surface, using generative and iterative approaches.
- Abstract compositions train judgment of balance, tension, rhythm and scale. That judgment is then available for applied work.
- Make many variations, curate the strongest, and articulate why they work.

## Grid systems
- Müller-Brockmann, Grid Systems in Graphic Design (1981):
  - The grid orders content and expresses clarity and objectivity.
  - The page divides into fields (modules) separated by gutters. Field height is a whole number of text lines, so text and images align across modules. The gutter often equals one line of leading.
  - Type size, leading and column width are chosen together.
  - Images take heights that are multiples of the field.
- Grid types (Samara, Making and Breaking the Grid):
  - manuscript: one text block, for books and essays
  - column: several columns for flexible text and image placement
  - modular: columns crossed by rows, for complex content and systems
  - hierarchical: proportions set by the content, for web pages and posters
- Gerstner's mobile grid for Capital magazine (1962): a 58-unit grid that divides into 1, 2, 3, 4, 5 and 6 columns, so one grid supports many layouts.
- Breaking the grid: a deliberate departure gets attention only because the grid established order first.
- Web grids:
  - 12 columns divide by 2, 3, 4 and 6
  - fluid columns with fixed gutters
  - breakpoints chosen by content, not devices
  - CSS Grid makes real typographic grids possible on screen
  - intrinsic layout lets content size the tracks

## Page proportions and margins
- Common page ratios:
  - 2:3, the classic book page
  - 3:4
  - 1:√2, the ISO A series (halving keeps the ratio)
  - 1:1.618, the golden section
  - US letter at 8.5 by 11
- The Van de Graaf canon, Villard's figure, and Tschichold's reconstruction of medieval page design (The Form of the Book):
  - on a 2:3 page, the text block has the same proportion as the page
  - margins are one-ninth and two-ninths of the page dimensions
  - inner, top, outer and bottom margins run in the ratio 2:3:4:6
  - the text block's height equals the page's width
- The rationale:
  - the unit is the two-page spread, so the two inner margins combine into one
  - the bottom margin is largest, giving visual support and room for thumbs
  - outer margins hold the book and can carry notes
- Modern practice keeps the logic and adjusts for binding (allow for the gutter lost in perfect binding), sidenotes and economy.

## Baseline grid and styles (ABCs of Book DNA)
- The leading of the body text defines a baseline grid. Everything else aligns to it or to simple fractions of it:
  - captions at half-line increments
  - headings whose space above and below adds up to whole lines, so text returns to the grid
  - marginalia aligned to body baselines
- Text across facing pages and columns should back up. This is called register: lines align across the spread and through the paper.
- Choosing a text face for a book:
  - suited to long reading, the paper and the printing method
  - sizes generally 9 to 12 points for adult readers, larger for children
  - leading and measure set together
- Paragraph and character styles (InDesign) automate consistency and changes. They also force semantic thinking (body, caption, heading, emphasis), the same idea as CSS classes.
- Parent (master) pages, object styles and GREP styles extend this.
- Exporting for offset printing: see [20](20-print-motion-history-critique.md).
- Illustrations made from typographic characters, and integrating illustration with text in a children's book:
  - picture books are commonly 32 pages, set by printing signatures
  - the page turn is a narrative device (suspense, reveal)
  - text sits in quiet areas of the image
  - early readers need larger type and generous spacing

## Editorial design and pacing (Design for Publishing)
- The sequence of spreads has rhythm. Alternate dense and open spreads, vary scale, and build to climaxes as a film does.
- Image editing:
  - selection
  - order (adjacency creates meaning)
  - pairing across a spread
  - cropping
  - scale contrast (one large image against many small ones)
- Photographic books:
  - Tonal reproduction matters. Black-and-white photographs print as duotones or tritones (black plus one or two grey or warm inks) to extend tonal range and depth beyond a single ink.
  - Paper choice (coated or uncoated, warm or cool white) changes everything.
- Dust jacket: front, spine, back, flaps. The front works as a poster for the book. US spines read top to bottom.
- Book arts (Introduction to Book Arts):
  - structures: pamphlet stitch, accordion, codex, Coptic, Japanese stab
  - type set by hand and digitally to match the concept
  - artists' books treat the book form itself as a medium
  - the course says craft is what lets the form carry the story

## Posters (Reframing the Poster)
- Distance reading works in three layers:
  1. Attract from afar with one strong image or word.
  2. Engage nearer with the headline and the main relationship.
  3. Inform up close with the details.
- One idea, made iconic. The course calls this the poster's capacity to turn ideas into iconic picture planes.
- Typography and image act as one composition rather than one sitting on the other.
- From single posters to sequences and series, to site-specific installations and screens (motion posters).
- Lineage:
  - Jules Chéret's colour lithographs in 1880s Paris
  - Toulouse-Lautrec, Mucha
  - Plakatstil (Lucian Bernhard: just the object and the brand name)
  - Cassandre's Art Deco travel posters
  - Constructivist posters (Lissitzky's "Beat the Whites with the Red Wedge", Rodchenko)
  - Swiss concert posters (Müller-Brockmann)
  - the Polish poster school
  - psychedelic posters
  - Paula Scher's Public Theater posters

## Design studio method (Design Studio 1 to 4)
- RISD's sequence:
  - search (formal and intellectual), research, analysis, ideation, prototyping
  - projects grow from guided inquiry to self-generated method
  - finished form is weighted more in later years as evidence that craft and method have matured
- Working habits:
  - many quick studies before commitment
  - series thinking (variations on a constraint)
  - precedents studied, not copied
  - process documented
  - constraints used as generators
- The BFA's form-making methods: visual research, ideation, experimentation, iteration, curation, interpretation.

## Publishing as making public ((Counter)Publishing Studio, Experimental Publishing Studio)
- The full publication cycle: gather and generate content (archives, writing, photography, illustration), edit, design, produce in multiples, distribute physically and digitally.
- History:
  - self-publishing and zines (science fiction fanzines, punk, riot grrrl, Factsheet Five)
  - small presses
  - artists' books (Ed Ruscha's Twentysix Gasoline Stations, 1963)
- Counter-narratives: publishing as a community tool for sharing urgent information.
- Post-digital publishing (Ludovico, Post-Digital Print, 2012): print and networks feed each other. "Posting" and publishing blur.
- The courses ask what publishing is today: substrate, blankness, circulation, authorship, copyright, the networked artist.

## Sources
From training: Lupton and Phillips, Graphic Design: The New Basics (2nd ed.). Müller-Brockmann 1981. Samara 2002/2017. Gerstner, Designing Programmes. Tschichold, The Form of the Book. Hochuli and Kinross, Designing Books. Hendel, On Book Design. Williams, The Non-Designer's Design Book. Ludovico 2012. RISD course descriptions (verified this session).
