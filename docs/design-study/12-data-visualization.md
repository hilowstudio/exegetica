# 12. Data visualization and interactive data science

Serves CMU courses:
- Data Visualization (05-319/619)
- Visualization in HCI
- Interactive Data Science (05-839)
- UX Research with Quantitative Data Sources

Also serves RISD Mapping Information. See [18](18-information-and-exhibit-design.md) for its information-design side.

## Purpose
- The course says good visualizations improve comprehension, communication and decision making, not only display data.
- Card, Mackinlay and Shneiderman (1999) define visualization as computer-supported, interactive, visual representations of data that amplify cognition.
- Exploratory visualization helps you find things (Tukey, Exploratory Data Analysis, 1977). Explanatory visualization shows others what you found. Design them differently.
- Anscombe's quartet (1973) and the Datasaurus Dozen: data sets with identical summary statistics look completely different when plotted. Always look at the data.

## Munzner's framework (Visualization Analysis and Design, 2014)
- What: the data abstraction.
  - Dataset types: tables, networks and trees, fields, geometry.
  - Attribute types: categorical, ordinal, quantitative (sequential or diverging).
- Why: the task abstraction.
  - Actions: analyze (discover, present, enjoy), search (lookup, browse, locate, explore), query (identify, compare, summarize).
  - Targets: trends, outliers, features, distributions, correlations, topology, paths.
- How: the idiom.
  - Encode: arrange space, map colour and other channels.
  - Manipulate: change, select, navigate.
  - Facet: juxtapose, partition, superimpose.
  - Reduce: filter, aggregate, embed.
- The nested model has four levels: domain situation, then data and task abstraction, then encoding and interaction idiom, then algorithm. Each level has its own threats to validity and its own validation method. A good algorithm cannot rescue a wrong abstraction.

## Marks and channels
- Bertin, Semiology of Graphics (1967), visual variables: position, size, shape, value (lightness), colour hue, orientation, texture. Later work added motion, saturation and others.
- Cleveland and McGill (1984) ranked accuracy for quantitative judgments, most to least accurate:
  1. Position on a common scale.
  2. Position on non-aligned scales.
  3. Length, direction, angle.
  4. Area.
  5. Volume and curvature.
  6. Shading and colour saturation.
- Mackinlay's APT (1986):
  - Expressiveness: encode all the data and only the data. Don't imply order where there is none.
  - Effectiveness: use the most accurate channel for the most important attribute.
  - The rankings differ by data type. For nominal data, position, hue and shape rank high and length ranks low.
- Separable channels can be read independently (position and hue). Integral channels fuse (width and height read as area).
- Pre-attentive features (Healey and Enns): hue, intensity, orientation, size, motion, enclosure and curvature pop out at a glance when one feature differs. Conjunctions of features need slow serial search. Use a single distinct feature to make the key thing pop.
- Gestalt grouping (proximity, similarity, enclosure, connection) organizes charts as it does layouts.

## Colour in visualization
- Categorical palettes: distinct hues of similar lightness. Only about 6 to 12 categories stay distinguishable. Beyond that, group, facet or label directly.
- Sequential palettes: vary lightness monotonically for ordered data.
- Diverging palettes: two hues from a meaningful midpoint (zero, average, target).
- Use perceptually uniform colormaps (viridis and its family). Avoid rainbow and jet, which create false boundaries and lack a lightness order (Borland and Taylor 2007).
- ColorBrewer (Cynthia Brewer) gives tested palettes, including colourblind-safe ones.
- About 8 percent of men have a colour vision deficiency. Check palettes in simulation and pair colour with position, labels or shape.
- Lightness carries order. Hue carries category.

## Tufte
From The Visual Display of Quantitative Information (1983), Envisioning Information (1990) and Beautiful Evidence (2006).
- Graphical integrity. The lie factor is the size of the effect shown in the graphic divided by the size of the effect in the data, and it should be about 1. Show data variation, not design variation. Give context.
- Maximize the data-ink ratio within reason. Remove chartjunk: heavy grids, 3D effects, decoration that encodes nothing.
- Small multiples: the same chart repeated across a variable, so the eye compares.
- Sparklines: word-sized graphics embedded in text.
- Layering and separation, and micro and macro readings: a design that rewards both the overview and close reading.
- Counterpoint: Bateman et al. (2010) found embellished charts were remembered better with no loss of comprehension. Minimalism is a default, not a law.

## Shneiderman's information-seeking mantra (1996)
- "Overview first, zoom and filter, then details on demand."
- Seven data types: 1D, 2D, 3D, temporal, multidimensional, tree, network.
- Seven tasks: overview, zoom, filter, details on demand, relate, history, extract.

## Choosing a chart
- Comparing values: bars on a zero baseline (bar length must be honest). Dot plots when zero is irrelevant.
- Change over time: lines. They need no zero baseline. Choose the aspect ratio so slopes average about 45 degrees ("banking", Cleveland).
- Distributions: histograms, box plots, violins, strip and beeswarm plots. Show the raw points when the sample is small.
- Relationships: scatterplots. Add a trend line with uncertainty.
- Part to whole: stacked bars, or a pie only with a few parts and clear differences. People judge angles and areas poorly.
- Matrices: heatmaps.
- Geography: maps only when location matters. Choropleths must show rates (normalized), not raw counts, or they become population maps. Proportional symbols suit counts.
- Networks: node-link diagrams for small sparse graphs, adjacency matrices for dense ones (Ghoniem, Fekete and Castagliola 2004).
- Avoid:
  - 3D charts for 2D data
  - dual y-axes (they suggest false relationships)
  - truncated bar axes
  - too many categories in one colour scheme

## Uncertainty
- Error bars are often misread, as if values outside the bar were impossible.
- Better formats: frequency framing. Quantile dot plots (Kay et al. 2016) and hypothetical outcome plots (animated draws, Hullman, Resnick and Adar 2015) improve decisions.
- Always say what the interval means.

## Narrative visualization
- Segel and Heer (2010) identify seven genres: magazine style, annotated chart, partitioned poster, flow chart, comic strip, slide show, film or animation. They range from author-driven (linear, heavy messaging) to reader-driven (free exploration).
- The "martini glass" structure: an author-driven opening narrows to the point, then opens into reader exploration.
- Titles should state the takeaway. Annotate the key points directly on the chart. Label lines directly instead of using a legend.
- Animated transitions help viewers track changes when the animation is staged and simple (Heer and Robertson 2007). Rosling's Gapminder is the canonical example.

## Interaction techniques for visualization
- Brushing and linking across views.
- Dynamic queries: sliders filter in real time (Ahlberg and Shneiderman, FilmFinder 1994).
- Details on demand: tooltips and detail panes.
- Navigation: zoom and pan, focus plus context (fisheye views), overview plus detail.

## Grammar of graphics and tools
- Wilkinson, The Grammar of Graphics (1999): a chart is a mapping from data to aesthetics with marks, scales, coordinates and facets. ggplot2 (Wickham) implements it in R.
- Vega-Lite (Satyanarayan, Moritz, Wongsuphasawat and Heer 2017) is a declarative JSON grammar with interaction (selections). Altair is its Python API. Dominik Moritz, a co-instructor of the CMU course, co-created Vega-Lite.
- D3 (Bostock, Ogievetsky and Heer 2011) binds data to the DOM for custom visualizations.
- Draco (Moritz et al. 2018) encodes visualization design knowledge as constraints and recommends designs.
- Streamlit builds interactive data apps (used in 05-839).

## The data pipeline (Interactive Data Science)
- Obtain: APIs, web data, formats (CSV, JSON, XML), parsing.
- Tidy data (Wickham 2014): each variable is a column, each observation a row, each type of observational unit a table.
- Clean and wrangle (Kandel et al., Wrangler). Common problems:
  - structural problems
  - missing values (and why they are missing)
  - duplicates
  - inconsistent units and formats
  - outliers (errors or real?)
  - dirty and heterogeneous sources
- Sampling and bias in collection:
  - selection bias
  - survivorship bias
  - measurement bias
  - Simpson's paradox: aggregation reverses a relationship
- Analyze: feature generation, statistics, classification. State the assumptions of the data.
- Experiment: A/B tests with attention to reliability (would it repeat?) and validity (does it measure what we think?). See [02](02-evaluation-and-measurement.md).
- Tell the story: from question to insight to a visual argument.

## Human-centered data science
- Ethics, fairness and interpretability. See FATE in [09](09-human-ai-interaction.md).
- Data Feminism (D'Ignazio and Klein 2020):
  - examine power
  - challenge power
  - elevate emotion and embodiment
  - rethink binaries and hierarchies
  - embrace pluralism
  - consider context
  - make labour visible

## Accessible visualization
- Give text alternatives for charts. Lundgard and Satyanarayan (2022) describe four levels of semantic content:
  1. Encoded elements (chart type, axes).
  2. Statistical facts (extremes, averages).
  3. Perceptual trends (patterns).
  4. Context and domain insight.
  Blind readers valued levels 2 and 3 most. Sighted readers also wanted level 4.
- Provide the data table. Don't depend on colour alone. Consider sonification.

## Dashboards
- Few, Information Dashboard Design: a single screen for monitoring at a glance, high data density, little decoration, bullet graphs and sparklines.
- Group related measures. Show comparisons to targets and past values.

## Sources
From training: Munzner 2014. Bertin 1967/1983. Cleveland and McGill 1984 (JASA). Mackinlay 1986 (TOG). Healey and Enns 2012 (TVCG). Ware, Information Visualization. Borland and Taylor 2007. Brewer, ColorBrewer. Tufte 1983, 1990, 2006. Bateman et al. 2010 (CHI). Shneiderman 1996. Ghoniem et al. 2004. Kay et al. 2016 (CHI). Hullman et al. 2015 (PLOS One). Segel and Heer 2010 (TVCG). Heer and Robertson 2007. Ahlberg and Shneiderman 1994. Wilkinson 1999. Satyanarayan et al. 2017. Bostock et al. 2011. Moritz et al. 2018. Wickham 2014 (JSS). Kandel et al. 2011. D'Ignazio and Klein 2020. Lundgard and Satyanarayan 2022 (TVCG). Few 2006.
