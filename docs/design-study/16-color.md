# 16. Colour

Serves RISD courses:
- Color + Surface (GRAPH 3211)
- Workshop: Pre-Press and Risograph Printing (3181)
- Screenprinting (3319)
- Design for Publishing (duotones)
- Mapping Information (colour in information)

Bridges to CMU visualization ([12](12-data-visualization.md)) and accessibility ([08](08-accessibility.md)).

## Physics and perception
- Visible light runs roughly 380 to 700 nanometres.
- Additive colour (light: screens, projectors) mixes red, green and blue toward white. Subtractive colour (pigment and ink) mixes cyan, magenta and yellow (plus black) toward dark.
- The course states it as colour being a phenomenon of light and pigment. It exists as ink on paper, pixels, paint, light on screens and reflections from surfaces.
- Cones and opponent channels: see [06](06-human-factors-cognition-perception.md).
- Metamerism: two colours match under one light and not another.
- Colour constancy: we see a surface's colour as stable across lighting, but only roughly.

## Dimensions and systems
- Hue, value (lightness) and saturation (chroma).
- Munsell's system orders colours perceptually by hue, value (0 to 10) and chroma.
- Value carries form and legibility. Test a design in greyscale: if the hierarchy collapses, the values are wrong regardless of the hues.
- CIELAB (1976) aimed at perceptual uniformity. OKLab and OKLCH (Ottosson 2020) improve on it, so equal steps look more equal. CSS Color Level 4 supports oklch(), which makes perceptually even palettes and tints practical on the web.
- Colour difference is measured as delta E.

## Albers, Interaction of Color (1963)
Josef Albers taught at the Bauhaus, Black Mountain and Yale.
- His thesis: colour is the most relative medium in art. The same colour looks different in different surroundings. Train the eye by observation before theory.
- The exercises, done with coloured paper (Color-aid):
  - one colour made to look like two by changing its ground
  - two different colours made to look the same
  - the illusion of transparency and overlap from opaque papers
  - vibrating boundaries: complementary hues of equal value make edges shimmer
  - the Bezold effect: changing one colour changes the whole composition
  - afterimages
  - middle mixtures
  - colour intervals (steps of hue, value and saturation)
  - free studies
- RISD's Color + Surface takes the same approach: see colour in action, examine and create colour relationships, and practise through observation and articulation.

## Itten, The Art of Color (1961)
Seven contrasts:
1. Hue.
2. Light-dark.
3. Cold-warm.
4. Complementary.
5. Simultaneous: a colour induces its complement in its neighbours.
6. Saturation.
7. Extension (proportion): harmony comes from balancing area against strength. Goethe's light values (yellow 9, orange 8, red and green 6, blue 4, violet 3) imply that yellow needs much less area than violet to balance it.

Itten also taught that people have subjective palettes.

## Contrast phenomena
- Simultaneous contrast (Chevreul 1839, from his work on the dyes of Gobelins tapestries): adjacent colours push each other apart in hue and value.
- Successive contrast: afterimages.
- Assimilation (spreading): fine patterns pull toward each other, the opposite of contrast.

## Harmonies
- Complementary, split-complementary, analogous, triadic, tetradic.
- These are starting points. Context, proportion and value decide whether a palette works.
- Colour wheels:
  - the traditional painter's wheel uses red, yellow and blue primaries
  - the process wheels are RGB and CMY
  - perceptual wheels place opposites differently
  - say which wheel you mean

## Colour and surface
- The same specification looks different on coated against uncoated paper, matte against gloss, emissive screens, fabric and coated metal. The course is built around how colour gets applied to surfaces.
- Print:
  - Spot colour (Pantone Matching System) is mixed ink, exact and consistent, with C (coated) and U (uncoated) swatches.
  - Process colour is CMYK halftones.
  - Gamut: CMYK can't reproduce many saturated RGB colours (bright greens, blues, oranges). Soft-proof before committing.
  - Dot gain darkens midtones, more on uncoated stock.
  - Colour management: ICC profiles for devices and papers (GRACoL and FOGRA print conditions), soft proofing, rendering intents.
- Screens: sRGB against wide-gamut Display P3. Calibration and ambient light change perception. You never fully control colour on users' screens.

## Meaning and context
- Associations are learned and vary by culture and context:
  - white for mourning in parts of East Asia
  - red for luck in China and danger in many Western signage systems
  - green with Islam and with environmentalism
- Popular colour-psychology claims rest on thin evidence. Reviews (Elliot and Maier 2014) find effects context-dependent and often small. Use colour meaning with care and test it with the actual audience.
- Brand colour gets its meaning from consistent use over time. See [17](17-identity-branding-systems.md).
- Keep semantic colours (error, warning, success) apart from the brand accent so meaning stays clear.

## Proportion
- 60-30-10 (dominant, secondary, accent) comes from interior design. It is a useful start, not a law.
- Itten's contrast of extension gives a more principled basis: balance area against strength.

## Colour in interfaces and accessibility
- WCAG contrast ratio is (L1 + 0.05) / (L2 + 0.05), using relative luminance:
  - 4.5:1 for body text
  - 3:1 for large text, UI component boundaries and focus indicators
  See [08](08-accessibility.md).
- APCA, a candidate method for WCAG 3, accounts for text weight, size and polarity (light on dark against dark on light). It is a draft, not a requirement.
- Never rely on colour alone.
- Dark mode:
  - not an inversion
  - avoid pure black under pure white (halation for some readers, notably those with astigmatism)
  - desaturate and lighten accents
  - show elevation with lighter surfaces
  - recheck every contrast pair
- Colour tokens in layers: primitives (a scale per hue), then semantic tokens (surface, text, accent, danger), then component tokens.

## Risograph and screen printing (workshops)
- Risograph:
  - a stencil duplicator printing soy-based, translucent spot inks, one drum per colour
  - each colour is a separate greyscale file. Darkness becomes ink density through a halftone or grain screen.
  - overprinting translucent inks makes new colours
  - registration shifts between passes, so design with that in mind: avoid hairline fits, let colours overlap, embrace the texture
  - heavy coverage smudges and sets off, so limit solid areas and use absorbent uncoated paper
  - signature inks include fluorescent pink and metallic gold
- The course's stated lesson: well-planned files make high-quality output that can be reproduced and shared. Technical limits demand creative solutions.
- Screen printing: stencils on mesh, opaque or translucent inks, layered colours, coarse halftones, and interplay with digital prints.

## Sources
From training: Albers 1963. Itten 1961/1970. Chevreul 1839. Munsell. Ottosson 2020 (OKLab blog). W3C CSS Color 4. Elliot and Maier 2014 (Annual Review of Psychology). Hunt, The Reproduction of Colour. Pantone documentation. RISD course descriptions (verified this session).
