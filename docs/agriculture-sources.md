# Agriculture Mode: sources and plan

**Status:** planning, 2026-10-20. A first look at sources; a full research pass (licenses and bulk access verified per source) comes before building. Nothing built.
**Rule:** self-hosted, like the Bible and Social Sciences Modes. Download once, keep it, serve it ourselves. Live calls only where the data is current by nature (today's market prices, the weather), the same exception the Economics investing unit makes.

## Why it's next

Agriculture is Yorkville's signature program. Every agriculture student is enrolled in FFA and carries a Supervised Agricultural Experience (SAE) project, and the middle school's Agriculture elective feeds the high school track. The academic spine already has a full Agriculture, Food & Natural Resources subject (7 strands, 672 objectives), so the Generator can already make materials for these courses; this Mode gives students and the teacher a grounded assistant to go with them.

## Courses served

| Course | Grades | Prerequisite | What it needs from the tools |
|---|---|---|---|
| **Introduction to Agriculture** | 9-12 | none | The whole field at survey depth: animal, plant and soil science, horticulture, natural resources, agribusiness, mechanics, careers, and the economics of agriculture in Illinois, the U.S., and the world |
| **Animal Science I** | 10-12 | Intro to Ag | Livestock (beef, dairy, sheep, goats, swine), poultry, equine: genetics, anatomy and physiology, nutrition, reproduction, animal health, meat science |
| **Agricultural Business 1** | 11-12 | an Ag course | Business ownership, planning, financing, records, agricultural law, taxes |
| **Agricultural Business 2** | 11-12 | an Ag course | Sales, marketing, commodity marketing, risk, international agribusiness |
| **Environmental Science** | 10-12 | Intro to Ag | Natural resources, environmental systems, energy, waste, outdoor recreation and ethics |
| **Introduction to Ag Mechanics** | 10-12 | Intro to Ag | Safety, electricity, small engines, construction, plumbing, surveying |
| **Introduction to Food Science** | 10-12 | Intro to Ag | Preservation, processing, food biochemistry, food selection, consumer health, inspection careers |
| **Horticultural Science & Landscaping** | 10-12 | Intro to Ag | Plant anatomy, propagation, pest management, hydroponics, plant ID, greenhouse crops, floral design, landscape design, rain gardens |
| **Independent Study** and the middle school **Agriculture** elective | 6-12 | | Whatever the project needs; SAE research |

## Candidate sources

Verdicts marked "verified" were checked 2026-10-20; the rest are for the research pass.

### Statistics and markets

| Source | What it holds | Self-host? | Notes |
|---|---|---|---|
| **USDA NASS Quick Stats** | U.S. crops, livestock, prices received, farm economics and demographics, back to the 1800s | **Yes, verified.** Bulk files by sector (crops, animals and products, economics, demographics, environmental), refreshed daily. Public domain | The backbone for Intro to Ag, Animal Science and Ag Business |
| **FAOSTAT** | World food and agriculture statistics, 245 countries, 1961 on | **Yes, verified.** Bulk downloads; CC BY 4.0 since July 2024, credit required; check any third-party datasets | Global comparisons for Ag Business and Intro to Ag |
| **USDA ERS ARMS** | Farm finances: balance sheets, income, costs, household income | Yes, via ERS downloads; public domain | Ag Business |
| **USDA AMS Market News (MARS)** | Daily local cash prices for grain and livestock | History yes; today's prices live | Commodity marketing in Ag Business 2 |
| **USDA ERS data products** | Farm income, food prices, trade, the food dollar | Likely yes; public domain | To verify |

### Food and nutrition

| Source | What it holds | Self-host? | Notes |
|---|---|---|---|
| **USDA FoodData Central** | Nutrient data for foundation, survey and branded foods | Yes; full CSV and JSON downloads; believed CC0 (to re-verify) | Food Science |
| **FDA Food Code** | The model code for food safety in retail and food service | Likely yes; a federal publication | Food Science, inspection careers |
| **USDA FSIS directives and guides** | Meat and poultry inspection, food safety | Likely yes; public domain | Food Science, Animal Science (meat science) |

### Plants, soil, land, and weather

| Source | What it holds | Self-host? | Notes |
|---|---|---|---|
| **USDA PLANTS Database** | Every U.S. plant: names, ranges, characteristics, invasive status | Likely yes; public domain | Horticulture plant ID, landscaping |
| **NRCS Web Soil Survey / SSURGO** | Soil maps and properties | Likely yes, by county or state; public domain | Soil science; Illinois counties only, to keep it small |
| **NOAA climate data, NASA POWER** | Weather and solar history by location | Yes, public domain; current weather would be live | Crops, growing seasons, energy units |
| **EPA data and guidance** | Water, air, waste, pesticides | Likely yes; public domain | Environmental Science |

### Reading and reference

| Source | What it holds | Self-host? | Notes |
|---|---|---|---|
| **USDA and agency publications** (Agriculture Handbooks, Farmers' Bulletins, Yearbooks of Agriculture) | Generations of practical agricultural writing | Yes; public domain, many already digitized (HathiTrust, Internet Archive, Library of Congress) | A deep "commentary" layer, the counterpart to the Reading Room's history shelves |
| **University extension publications** (Illinois Extension and others) | Current practical guidance | Varies by publication | Some are openly licensed, many are copyrighted: check one by one |
| **OSHA agricultural safety** | Tractors, machinery, chemicals, confined spaces | Likely yes; public domain | Ag Mechanics safety |
| **OpenAlex** (agronomy, animal, food and soil science) | Scholarly papers | **Yes, verified.** CC0 snapshot | The same slice approach as for History |
| **The Reading Room** | Public-domain agriculture and natural-history books | Ours | Check what the Science & Nature shelf holds |

### Not a fit, or later

| Source | Why |
|---|---|
| Google Agricultural Understanding Platform | A cloud service; nothing to self-host |
| The Official FFA Manual and FFA curriculum | Copyrighted by the National FFA Organization; link out, don't store |
| National Electrical Code | Copyrighted (NFPA) |
| PCSE crop-simulation software | Open source and runs locally, but a classroom activity more than a reference source; consider later |

## Proposed tools

1. **search_agriculture:** hybrid keyword and meaning search over the publications library (USDA bulletins and handbooks, public-domain extension material, agency guidance) and the Reading Room's agriculture books.
2. **get_crop_stats** and **get_livestock_stats:** NASS figures by commodity, state or county, and year; FAOSTAT for other countries.
3. **get_market_price:** grain and livestock prices, history stored and today's live.
4. **get_nutrition:** FoodData Central nutrients for a food.
5. **lookup_plant:** the PLANTS Database (names, range, characteristics, invasiveness), for plant ID and landscape design.
6. **get_soil:** soil properties for an Illinois location (SSURGO).
7. **get_weather_history:** growing-season climate for a place (NOAA, NASA POWER).
8. **get_food_code** and **get_safety_guidance:** the FDA Food Code, FSIS guidance, OSHA agricultural safety.
9. **search_research:** an OpenAlex slice for agronomy, animal, food, and soil science.
10. **The persona:** an agricultural educator's voice, written with Yorkville's Ag teacher. A natural frame is creation and stewardship (Genesis 1:28; 2:15): dominion as care, work as vocation, honest about debated questions in agriculture.

## Build order

1. **Statistics:** NASS Quick Stats and FAOSTAT. This serves every course and is the most ready.
2. **Publications library:** USDA handbooks and bulletins plus the Reading Room's agriculture books, with search_agriculture.
3. **Food Science:** FoodData Central, the FDA Food Code, FSIS guidance.
4. **Horticulture and the land:** the PLANTS Database, Illinois soils, weather history.
5. **Markets:** AMS price history plus today's prices live; ARMS farm finances.
6. **Research:** the OpenAlex slice.

## Open items

- A full research pass to verify each "likely" source's license and bulk access.
- **The Ag teacher:** the persona's voice and rulings (stewardship, debated questions such as biotechnology, organic versus conventional, and animal welfare), and the course materials, the way the Bible and U.S. History teachers shaped theirs.
- Which extension publications Yorkville uses, so their licenses can be checked.
- FFA and SAE: the tools can support SAE record-keeping research (market prices, production figures) without storing FFA's copyrighted materials.
