# 9. Human-AI interaction, AI as a design material, conversation

Serves CMU courses:
- Human AI Interaction (05-318/618)
- Design of AI Products and Services (05-317/617)
- The AI Augmented Designer (05-312/612)
- Prototyping Algorithmic Experiences
- Human-Centered NLP
- Augmenting Intelligence
- FATE in Sociotechnical Systems
- Designing for Conversation (05-897)
- Social Agents
- AI Innovation in the Healthcare Sector
- Ubiquitous Personal Smart Agents
- Applied Machine Learning

## Why designing with AI is hard
- Yang, Steinfeld, Rosé and Zimmerman (CHI 2020) name two sources of difficulty:
  - uncertainty about what the AI can do
  - the complexity of its outputs
  They sort systems into four levels, from fixed outputs with probabilistic behaviour up to systems that keep learning and produce open-ended outputs. Higher levels break the usual sketch-and-prototype methods.
- The CMU course description makes the same point. Designers rarely spot situations where AI could help. When they do, they treat it like magic and imagine things that can't be built. Machine-learning experts who can build it rarely know how to give it a valuable form.

## AI as a design material
- Know the capabilities in the abstract:
  - detect, classify, recognize
  - predict and forecast
  - rank and recommend
  - cluster
  - find anomalies
  - estimate
  - transcribe and translate
  - summarize and extract
  - generate
  - converse
  - act (agents)
- Yildirim et al. (DIS 2023, CMU), verified by search: built a design resource from 40 AI features common across domains to support ideation.
- A secondhand summary of a Zimmerman talk (not the paper) reports a finding: a capability taxonomy alone led to more AI-flavoured ideas that still could not be built. Teams that focused on simple capabilities and moderate performance produced more valuable and buildable concepts.
- The working heuristic: prefer situations where a moderately accurate model still creates value and errors are cheap to notice and fix. Avoid concepts that need near-perfect accuracy.
- Matchmaking (see [04](04-design-process-prototyping-service.md)): start from capabilities and look for people and situations they serve.
- The healthcare course's list of why most AI innovations fail (verified on the CMU course page):
  - they need model performance that can't be reached
  - they don't address a real challenge, so nobody adopts them
  - they cost more than they earn
  - they violate policy
  - the domain experts don't trust or accept them
  - they introduce an ethical risk
  A concept must clear all six.

## Mixed-initiative interaction (Horvitz, CHI 1999)
Twelve principles, in brief:
1. Add significant value through automation.
2. Consider uncertainty about the user's goals.
3. Consider the user's attention when timing a service.
4. Weigh the costs and benefits of acting under uncertainty.
5. Use dialogue to resolve key uncertainties.
6. Allow efficient direct invocation and termination.
7. Minimize the cost of poor guesses about action and timing.
8. Scope the precision of the service to match the uncertainty.
9. Provide mechanisms for user and agent to refine results together.
10. Use socially appropriate behaviour.
11. Keep a working memory of recent interactions.
12. Continue to learn by observing.

The core logic: act, ask, or stay out of the way, depending on the expected value of each under uncertainty.

## Microsoft's Guidelines for Human-AI Interaction (Amershi et al., CHI 2019)
The 18 guidelines are grouped by phase. The four phases are verified on the HAX toolkit page. The list is from training.
- Initially:
  1. Make clear what the system can do.
  2. Make clear how well it can do it.
- During interaction:
  3. Time services based on context.
  4. Show contextually relevant information.
  5. Match relevant social norms.
  6. Mitigate social biases.
- When wrong:
  7. Support efficient invocation.
  8. Support efficient dismissal.
  9. Support efficient correction.
  10. Scope services when in doubt.
  11. Make clear why the system did what it did.
- Over time:
  12. Remember recent interactions.
  13. Learn from user behaviour.
  14. Update and adapt cautiously.
  15. Encourage granular feedback.
  16. Convey the consequences of user actions.
  17. Provide global controls.
  18. Notify users about changes.

The HAX toolkit adds a design library of patterns, a workbook for prioritizing guidelines with the team, and a playbook for anticipating failures.

## Google PAIR People + AI Guidebook
The six chapters are verified by search. The guidebook was updated for generative AI.
1. User needs and defining success.
   - Is AI the right tool? Should it augment or automate?
   - Choose the reward function deliberately. Weigh false positives against false negatives for this user. Tune precision against recall to match.
2. Data collection and evaluation: representative data, labelling quality, evaluation with real users.
3. Mental models: set expectations about what the product can and cannot do. Introduce features gradually. Explain limits before users find them by failing.
4. Explainability and trust:
   - aim for calibrated trust
   - explain at the level the decision needs
   - show confidence only when it helps the decision
   - be clear about the data sources
5. Feedback and control: implicit and explicit feedback, user control over automation, and making clear how feedback changes the system.
6. Errors and graceful failure:
   - Distinguish system limits, context errors and background errors.
   - Give users a path forward, including a fallback to a non-AI option.
   - Treat errors as a chance to correct mental models and collect feedback.

## Trust and reliance
- Calibrated trust (Lee and See 2004): trust should match the system's real reliability. Overtrust leads to misuse, distrust to disuse (Parasuraman and Riley 1997).
- Overreliance: people accept AI suggestions even when wrong.
  - Explanations can increase acceptance whether or not the AI is right (Bansal et al. 2021).
  - Cognitive forcing functions reduce overreliance, at some cost to how pleasant the experience feels (Buçinca, Malaya and Gajos 2021). Examples: ask for the person's own answer first, or require a deliberate step before revealing the AI's answer.
- Human-AI complementarity: a team beats either party alone only when each brings strengths the other lacks and the human can tell when to defer. Holstein (CMU) and others study how to design for it.
- Confidence display: helpful when well calibrated and when users can act on it. Raw probabilities often mislead, and categories or ranges can work better.

## Explainability
- People want different explanations for different questions. Liao, Gruen and Miller (2020) built an XAI question bank:
  - how (global logic)
  - why
  - why not
  - what if
  - how to be that (counterfactual: what would change the outcome)
  - how to still be this
  - performance
  - data
  - output
- Miller (2019): human explanations are contrastive (why this rather than that), selected (a few causes, not all), and social (tailored to the listener). Probabilities matter less to people than causes.
- Techniques: feature attributions (SHAP, LIME, with known instability), counterfactuals, example-based explanations (similar cases), model documentation.

## Agency, initiative and adaptation
- Levels of automation (Sheridan, and Parasuraman, Sheridan and Wickens 2000). See [03](03-interaction-design-principles.md).
- Proactive agents must weigh the value of an interruption against its cost. See attention in [06](06-human-factors-cognition-perception.md).
- Adaptive interfaces (Gajos et al.): adaptation helps when it is accurate and predictable. Inaccurate or unpredictable adaptation is worse than none.
- Recommender systems:
  - explain recommendations
  - offer controls (more of this, less of that)
  - manage the cold start
  - add diversity and serendipity against filter bubbles
  - watch the feedback loops that amplify popularity
- Programming by example and demonstration (Cypher, Watch What I Do, Lieberman, Gulwani's FlashFill 2011): users show examples and the system infers a program. Examples underdetermine the intent, so show the inferred rule, let users correct it with more examples, and make generalization visible.

## Large language models and human-centered NLP
- The course's framing, paraphrasing a quip it cites from Yang et al. 2019: HCI people design useful things NLP people can't build, and NLP people build things nobody uses. The course works on closing that gap.
- Strengths and weaknesses in interaction:
  - fluent but sometimes wrong (hallucination)
  - sensitive to phrasing
  - non-deterministic
  - verbose
  - inclined to agree with the user (sycophancy)
  - hard to evaluate at scale
- Design patterns:
  - ground answers in retrieved sources and show the sources
  - constrain outputs where structure matters
  - express uncertainty in words
  - make editing and regeneration easy
  - keep humans in the loop for high-stakes outputs
- Shared HCI and NLP topics:
  - agents
  - model trust
  - task delegation (Lubars and Tan 2019: people's willingness to delegate depends on motivation, difficulty, risk and trust, and they keep high-stakes or personally meaningful tasks)
  - data curation (annotator disagreement is signal, not noise)
- Prompting is end-user programming. Zamfirescu-Pereira et al. (CHI 2023, "Why Johnny Can't Prompt") found non-experts generalize from single examples, expect human-like understanding, and struggle to debug prompts systematically.
- Evaluation: human evaluation with clear rubrics, task-based measures, and caution with LLM-as-judge (position and verbosity bias, self-preference).

## Augmenting intelligence
- Historical visions:
  - Bush's memex (1945)
  - Licklider's "Man-Computer Symbiosis" (1960)
  - Engelbart's "Augmenting Human Intellect" (1962), where a human is augmented by language, artifacts, methodology and training together
- Sensemaking (Pirolli and Card 2005): a foraging loop (search, filter, read, extract) and a sensemaking loop (schematize, build the case, tell the story).
- The course designs and evaluates systems that augment decision-making, sensemaking, learning, perception and creative problem-solving, for individuals and groups. Collective intelligence (Malone) and CSCW contribute group-level views.
- Risks: deskilling, homogenized output, and loss of the productive struggle that builds skill. This connects to desirable difficulties in [07](07-learning-science.md).

## The AI-augmented designer
The course covers AI across the design process: synthetic users, automated research tools, qualitative analysis, ideation, critique, coding and testing. Known cautions:
- Synthetic humans: LLM "participants" reproduce stereotypes, flatten variation and lack lived experience. Useful for piloting protocols, not as a substitute for people.
- AI-assisted qualitative coding: a second coder at most. Check agreement and read the data yourself.
- Generative ideation: AI examples can cause design fixation, as any example can. Generate your own ideas first, then use AI to widen them.
- The course asks students to reflect critically on when and where AI helps their work.

## Fairness, accountability, transparency, ethics (FATE)
- Group fairness definitions:
  - demographic parity (equal selection rates)
  - equalized odds (equal true and false positive rates)
  - equal opportunity (equal true positive rates)
  - calibration (equal meaning of scores)
- Individual fairness: similar people treated similarly.
- Impossibility results (Kleinberg, Mullainathan and Raghavan 2016, Chouldechova 2017): when base rates differ, calibration and equal error rates cannot all hold at once, so choosing a definition is a value choice.
- Cases:
  - COMPAS recidivism scores (ProPublica 2016)
  - Gender Shades (Buolamwini and Gebru 2018): commercial face classifiers erred far more on darker-skinned women (error rates up to about 35 percent) than on lighter-skinned men (under 1 percent)
- Sources of harm (Suresh and Guttag 2021): historical, representation, measurement, aggregation, learning, evaluation and deployment bias. Harms can be allocative (resources) or representational (stereotypes, erasure).
- Documentation:
  - model cards (Mitchell et al. 2019)
  - datasheets for datasets (Gebru et al.)
  - algorithmic audits (Raji and Buolamwini 2019)
  - everyday user-driven auditing (Shen, DeVos, Eslami and Holstein 2021)
- Accountability:
  - contestability and recourse (people can challenge decisions and know what would change them)
  - clear human responsibility
  - transparency aimed at a specific audience for a specific purpose

## Designing for conversation (05-897)
- Dubberly and Pangaro, "What is conversation?" (Interactions 2009, verified this session):
  - They separate conversation from Shannon-style communication. Communication selects among messages known in advance. Conversation creates new meaning and confirms understanding.
  - Most human-computer interaction is the selection kind.
  - Their model of conversation runs in six steps:
    1. Open a channel, with a first message that establishes common ground.
    2. Commit to engage. Both sides have to see enough value to justify the "bio-cost" of attention.
    3. Construct meaning.
    4. Evolve: a participant is changed by the exchange.
    5. Converge on agreement over an understanding, confirmed by restating it in a different form.
    6. Act or transact.
  - Conversation serves learning, coordination and collaboration (agreeing on goals). Its limits come from the infrastructure and from the participants.
  - The theory comes from Gordon Pask's cybernetic conversation theory, whose "teachback" is how understanding gets checked. Paul Pangaro teaches the CMU course.
- Grice's cooperative principle and maxims: quantity (as informative as needed, no more), quality (truthful, with evidence), relation (relevant), manner (clear, brief, orderly).
- Conversation analysis (Sacks, Schegloff and Jefferson 1974):
  - turn-taking
  - adjacency pairs (question and answer, offer and acceptance)
  - preference organization (agreement comes quickly, refusal with delay and account)
  - repair (speakers fix trouble, and self-initiated self-repair is preferred)
- Grounding (Clark and Brennan 1991): participants build common ground with the least collaborative effort. Evidence of understanding includes continued attention, a relevant next turn, acknowledgment, demonstration and verbatim display.
- Chatbot limits: Luger and Sellen (2016) found a gulf between users' expectations of conversational agents and what they deliver, and users learned to speak in economical commands.
- Practical conversational design:
  - set expectations of capability at the start
  - keep a consistent persona
  - confirm implicitly or explicitly according to the risk of the action
  - handle no-match and no-input with escalating, helpful reprompts
  - offer repair ("did you mean...")
  - keep voice turns short with one idea each
  - offer discoverable options, since voice lacks visible signifiers
- The course claims a formal conversation model can guide interfaces in any modality: voice, text, prose, gesture or movement.

## Social agents
- The media equation (Reeves and Nass 1996, Nass and Moon 2000): people apply social rules to computers. They show politeness, respond to flattery, apply gender stereotypes and in-group bias, even while knowing it is a machine.
- Anthropomorphism (Epley, Waytz and Cacioppo 2007) rises with human-like cues, the need to explain behaviour, and loneliness.
- The ELIZA effect (Weizenbaum 1966): people attribute understanding to simple pattern-matching.
- Uncanny valley (Mori 1970).
- Risks with heavy users and young people: parasocial attachment and dependency.
- Agent-based models simulate social theories: Schelling's segregation model, social influence and collective action. Shirado and Christakis (2017) found simple bots in human networks helped groups coordinate.
- LLM-driven "generative agents" (Park et al. 2023) simulate social behaviour. Treat them as a simulation, not a measurement of real people.

## Context-aware personal agents
- Context (Dey 2001): any information that characterizes the situation of an entity relevant to the interaction.
- Context-aware systems need intelligibility and control (Bellotti and Edwards 2001): users must be able to tell what the system sensed and why it acted, and to override it.
- Privacy in ubiquitous computing (Langheinrich 2001): notice, choice, proximity, locality, minimization.

## Sources
Verified this session:
- Microsoft HAX toolkit guidelines page (the four phases)
- Google PAIR guidebook chapters (search)
- Dubberly and Pangaro "What is conversation?" (dubberly.com)
- Yildirim et al. DIS 2023 (search). The moderate-performance claim comes from a secondary summary only.
- CMU course pages

From training: Yang et al. 2020. Horvitz 1999. Amershi et al. 2019. Lee and See 2004. Bansal et al. 2021. Buçinca et al. 2021. Liao et al. 2020. Miller 2019. Gajos et al. 2006/2008. Lubars and Tan 2019. Zamfirescu-Pereira et al. 2023. Kleinberg et al. 2016. Chouldechova 2017. Buolamwini and Gebru 2018. Suresh and Guttag 2021. Mitchell et al. 2019. Gebru et al. 2021. Grice 1975. Sacks et al. 1974. Clark and Brennan 1991. Luger and Sellen 2016. Reeves and Nass 1996. Dey 2001. Bellotti and Edwards 2001.
