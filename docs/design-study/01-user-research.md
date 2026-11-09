# 1. User research

Serves: CMU User-Centered Research and Evaluation (05-410/610), Applied Research Methods (05-816, 05-821 qualitative, 05-822 quantitative), HCI for Product Managers / for Technology Executives, Interaction Design Studio 2 (guerrilla research), HCI Project I (capstone research phase), Learning Media Design.

## Stance
- Research exists to lower the risk of building the wrong thing. Start from the decisions the research must inform, then pick methods.
- People's words, actions and artifacts differ. What they say (interviews, surveys), what they do (observation, logs), and what they make (co-design, diaries) each catch different truths (Sanders). Behaviour outranks stated preference.
- Two axes organize the method landscape (Rohrer, NN/g): attitudinal vs behavioural, and qualitative vs quantitative. A third axis is context of use: natural, scripted, decontextualized.
- Generative research finds needs and opportunities. Evaluative research tests a design against them.

## Planning a study
- Write research questions first, then the method, sample, recruiting screener, protocol, consent, analysis plan and the deliverable.
- Recruit the real population, segmented by behaviour, not demographics alone.
- Qualitative sample sizes: themes saturate early in homogeneous groups (Guest, Bunce and Johnson 2006 found most codes by about 12 interviews). Run 5 to 8 per distinct segment for usability-style studies.
- Ethics: informed consent, right to stop, data minimization. With minors: parental consent plus the child's own assent, and plain-language explanations.

## Contextual Inquiry (Beyer and Holtzblatt, Contextual Design, 1998, 2nd ed. 2017)
Four principles:
1. Context: go where the work happens and gather ongoing, concrete experience instead of summaries. Ask for the last real instance ("show me the last time you...").
2. Partnership: a master and apprentice relationship. The participant is the expert, the researcher learns by watching and asking during the work.
3. Interpretation: share your reading of what you see in the moment ("so you keep that list because...?") so the participant can correct it. Facts only matter once interpreted.
4. Focus: a defined project focus tells the researcher what to attend to and what to probe.

Session shape: introduction and consent, transition into the work, about two hours of observation with questions, then a wrap-up where the researcher summarizes and the participant corrects.

Interpretation session within 48 hours: the team replays the interview and writes short notes (observations, breakdowns, design ideas, questions).

Work models capture different aspects:
- flow (roles and communication)
- sequence (steps, intents, triggers, breakdowns)
- artifact (things people make and use)
- physical (space)
- cultural (influences, values, pressures)

The 2nd edition adds day-in-the-life, identity, relationship and collaboration models.

Affinity diagram: bottom-up clustering of individual notes (often 50 to 100 per interview) into groups labelled in the user's voice, then grouped again into higher levels. The rule is no predefined categories. The structure has to emerge from the data. A "wall walk" lets the team read the whole affinity and generate design ideas from it.

## Interviewing (Portigal, Interviewing Users, 2013/2023)
- Open, non-leading questions, one at a time. Use silence and let the participant fill it. Follow up with "tell me more about that."
- Ask about specific past behaviour, not hypothetical futures. "Would you use X" predicts little.
- Critical incident technique (Flanagan 1954): ask for a memorable recent success or failure and walk through it in detail.
- Ask to see artifacts (notes, files, workarounds). Workarounds point at unmet needs.
- Avoid pitching, jargon, and correcting the participant. Notice contradictions between what is said and shown, and probe them gently.
- The Mom Test (Fitzpatrick) for early product ideas: talk about their life, not your idea. Ask about specifics in the past. Listen more than talk. Compliments are not data.

## Observation and field methods
- Modes: fly-on-the-wall, shadowing, participant observation.
- Field notes: jot in the moment, write full notes the same day. Separate what you saw from what you think it means. Thick description (Geertz) records context and meaning, not only behaviour.
- Diary studies and experience sampling for behaviour that is longitudinal, private, or spread across time and place.
- Guerrilla research: quick intercepts and hallway tests. Cheap and directional, never conclusive.
- Online ethnography for communities and digital practices.

## Surveys
- Surveys measure prevalence and attitudes. They rarely explain why.
- Item writing: one concept per item (no double-barrelled questions), neutral wording, balanced response scales, an opt-out ("not applicable"), no leading premises. Watch question-order and context effects.
- Likert items: 5 or 7 points. Label all points or at least the ends.
- Pilot with a few respondents using think-aloud to catch misreadings (cognitive interviewing).
- Prefer validated instruments: SUS and UMUX-Lite for perceived usability, NASA-TLX for workload.
- Threats: sampling bias, non-response bias, social desirability, acquiescence.

## Qualitative analysis
- Grounded theory (Glaser and Strauss, then Strauss and Corbin):
  - open coding labels concepts in the data
  - axial coding relates them
  - selective coding builds a core story
  - constant comparison and analytic memos run throughout, until theoretical saturation
- Thematic analysis (Braun and Clarke 2006), six phases: familiarize, generate initial codes, search for themes, review themes, define and name themes, write up. Their later "reflexive" stance treats the researcher's interpretation as a resource and rejects reliability scores.
- Codebook approaches do use inter-rater reliability:
  - Cohen's kappa for two coders, Fleiss' kappa for more
  - Landis and Koch's conventions: above 0.6 is substantial, above 0.8 near perfect
  - disagreements get resolved by discussion and the codebook revised
- Descriptive statistics alongside qualitative work (course 05-821):
  - frequencies of codes
  - chi-square for association between categorical variables
  - correlations
- Content analysis applies a coding scheme to documents, posts or artifacts.

## From data to insight
- An insight is a non-obvious truth about people that explains behaviour and implies an opportunity. A useful format: what we saw, why it happens, what it means for design.
- Personas (Cooper): archetypes built from observed behaviour patterns and goals, not demographics. One primary persona per interface. Personas invented without research mislead.
- Journey maps: stages, actions, thoughts, emotions, pain points, opportunities over time.
- Jobs to be Done (Christensen): "when [situation], I want to [motivation], so I can [outcome]." People hire products for progress in a circumstance.
- "How might we" questions turn insights into design prompts. Scope them neither so broad they give no direction nor so narrow they contain the answer.
- Communicating to stakeholders:
  - lead with findings tied to the decisions at hand
  - show evidence (quotes, clips, counts)
  - rate severity and frequency
  - separate findings from recommendations

## Mixed methods
- Triangulation: qualitative work explains why, quantitative work says how many and how much.
- Sequential designs (Creswell): explanatory runs quantitative first, then qualitative to explain the pattern. Exploratory runs qualitative first, then quantitative to test how widespread the finding is.

## Quantitative research basics (05-822, 05-816)
- Variables: independent (manipulated), dependent (measured), controls, confounds.
- Between-subjects designs avoid carryover. Within-subjects designs have more power but need counterbalancing (Latin square) against order and practice effects. Random assignment is what licenses causal claims.
- Validity (Shadish, Cook and Campbell):
  - internal: did the manipulation cause the effect?
  - external: does it generalize?
  - construct: are we measuring what we claim?
  - statistical conclusion: are the stats sound?
- Tests:
  - t-test for two groups, ANOVA for three or more (factorial ANOVA reveals interactions)
  - chi-square for categories
  - correlation and regression (linear, logistic)
  - factor analysis to check that a multi-item scale measures what it should
  - nonparametric alternatives (Mann-Whitney, Wilcoxon, Kruskal-Wallis) for ordinal data or small skewed samples
- Report effect sizes and confidence intervals, not only p-values. Cohen's d conventions: 0.2 small, 0.5 medium, 0.8 large. Plan sample size with a power analysis. Correct for multiple comparisons.
- Social network analysis: nodes, ties, degree, betweenness, clustering, weak and strong ties.

## Sources
Beyer and Holtzblatt, Contextual Design. Holtzblatt and Beyer, Contextual Design 2nd ed. Portigal, Interviewing Users. Goodman, Kuniavsky and Moed, Observing the User Experience. Hanington and Martin, Universal Methods of Design. Braun and Clarke 2006 (Qualitative Research in Psychology). Strauss and Corbin, Basics of Qualitative Research. Shadish, Cook and Campbell, Experimental and Quasi-Experimental Designs. Rohrer, "When to Use Which User-Experience Research Methods" (NN/g). All from training knowledge, not re-fetched.
