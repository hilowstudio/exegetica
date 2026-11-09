# 7. Learning science and educational technology

Serves CMU courses:
- E-Learning Design Principles and Methods (05-823)
- Evidence-Based Educational Design (05-738)
- Personalized Online Learning (05-432/832)
- Tools for Online Learning (05-840)
- Design of Educational Games (05-418/818)
- Transformational Game Design Studio
- Learning Media Design and Learning in Museums
- Design of Large-scale Peer Learning Systems
- Learning Analytics and Educational Data Science
- Research Methods for the Learning Sciences (05-748)
- The Role of Technology in Learning in the 21st Century
- MSLE capstones

## Foundations

### CMU's seven principles (Ambrose et al., How Learning Works, 2010, verified on the Eberly Center page)
1. Prior knowledge can help or hinder learning. It helps when it is accurate and activated at the right time. It hinders when it is inert, insufficient, wrongly activated or wrong (misconceptions).
2. How knowledge is organized shapes how well it can be retrieved and applied. Experts' knowledge is richly connected around deep principles. Novices' is sparse and surface-organized.
3. Motivation decides, directs and sustains learning behaviour. It depends on the value of the goal, the expectation of success, and perceived support from the environment.
4. Mastery requires component skills, practice integrating them, and knowing when to apply them (transfer). Experts' "expert blind spot" hides these components from them.
5. Goal-directed practice with targeted feedback improves learning. Practice should aim at specific criteria, at the right level of challenge, often enough. Feedback should say how performance compares with the criteria, how to improve, and come in time to use.
6. Students' development interacts with the course's social, emotional and intellectual climate. Climate can help or block learning.
7. To become self-directed, students must learn to monitor and adjust their own learning (metacognition), which they rarely do by default.

### Knowledge-Learning-Instruction framework (Koedinger, Corbett and Perfetti 2012, CMU)
- Knowledge components (KCs): units of knowledge inferred from performance (facts, concepts, rules, skills, principles).
- Three kinds of learning process, each suited by different instruction:
  - Memory and fluency building: spacing, retrieval practice, repetition.
  - Induction and refinement: varied examples, worked examples, comparison, feedback, categorization practice.
  - Understanding and sense-making: self-explanation, argumentation, accountable talk.
- Match the instructional principle to the kind of KC and process. With so many possible combinations of instructional choices, only evidence can settle which work. This is the argument for learning engineering.

## Cognitive load theory (Sweller 1988, and Sweller, van Merriënboer and Paas 1998, 2019)
- Working memory is limited, so instruction should spend it on learning rather than on decoding the presentation.
- Load types:
  - intrinsic: the complexity of the material, set by element interactivity
  - extraneous: imposed by poor design
  - germane: the effort that builds schemas (later folded into intrinsic)
- Effects with design consequences:
  - Worked example effect: novices learn more from studying worked solutions than from solving equivalent problems.
  - Completion problems: partly worked examples. Fading moves from full examples to independent solving (Renkl and Atkinson).
  - Split-attention effect: integrate related text and pictures rather than separating them.
  - Modality effect: narration with a picture beats on-screen text with a picture, for brief complex content.
  - Redundancy effect: identical spoken and written text together hurts. So does unneeded material.
  - Expertise reversal (Kalyuga 2003): guidance that helps novices burdens experts, so fade support as competence grows.
  - Goal-free effect: open goals ("find all you can") reduce means-ends load for novices.
  - Transient information effect: long narrated animations overload memory, so segment them or give learners control.

## Multimedia learning (Mayer, Multimedia Learning, 3rd ed. 2021, Clark and Mayer, e-Learning and the Science of Instruction)
- Assumptions: dual channels (verbal and pictorial), limited capacity, active processing. Learning means selecting, organizing and integrating (the SOI model).
- Principles grouped by what they do.
- Reduce extraneous processing:
  - coherence: cut interesting but irrelevant words, pictures and sounds
  - signaling: highlight the essential and the organization
  - redundancy: don't add printed text to narrated graphics
  - spatial contiguity: put words next to the graphics they describe
  - temporal contiguity: narration at the same time as the animation
- Manage essential processing:
  - segmenting: learner-paced chunks
  - pre-training: teach names and characteristics of key parts first
  - modality: spoken rather than printed words with graphics
- Foster generative processing:
  - multimedia: words plus pictures beat words alone
  - personalization: conversational style, "you" and "I"
  - voice: a friendly human voice
  - embodiment: on-screen agents with humanlike gesture
  - image: a talking-head image alone does not help
  - generative activity: summarizing, mapping, drawing, self-explaining
- Boundary conditions: the effects are strongest for novices, complex material and fast-paced lessons, and they shrink for experts.
- Clark and Mayer's e-learning chapters add:
  - worked examples with self-explanation prompts
  - practice that is spaced, mixed and aligned to the job
  - explanatory rather than merely corrective feedback
  - learner control kept low for novices
  - scaffolding for games and simulations, because discovery alone underperforms

## Practice, memory and learning by doing
- Retrieval practice (testing effect, Roediger and Karpicke 2006): recalling information strengthens memory more than re-reading it, even without feedback.
- Spacing (Cepeda et al. 2006): spread practice out. The best gap grows with how long the knowledge must last, roughly 10 to 20 percent of the retention interval.
- Interleaving (Rohrer and Taylor): mixing problem types improves the ability to choose a strategy, compared with blocked practice.
- Desirable difficulties (Bjork 1994): conditions that slow initial performance (spacing, interleaving, retrieval, variation) often improve long-term retention and transfer. Learners misjudge this. Fluent re-reading feels like learning and isn't.
- Dunlosky et al. (2013) rated ten study techniques:
  - high utility: practice testing and distributed practice
  - moderate: elaborative interrogation, self-explanation, interleaved practice
  - low: highlighting, re-reading, summarization (without training), keyword mnemonics, imagery for text
- Generation effect: producing an answer beats reading it. Pre-questions prime later learning.
- The "doer effect" (Koedinger et al. 2015, CMU Open Learning Initiative data): doing interactive practice predicted learning far more strongly than reading or watching, about six times more per unit of time.
- Deliberate practice (Ericsson et al. 1993): specific goals at the edge of ability, immediate feedback, a coach, focused repetition with refinement. Later meta-analyses find it explains less variance than first claimed, but the design ingredients hold.

## Self-explanation and engagement
- Self-explanation (Chi et al. 1989, 1994): learners who explain worked examples and texts to themselves learn more. Prompting self-explanation helps most learners.
- ICAP (Chi and Wylie 2014) ranks engagement modes by overt behaviour, from most to least learning:
  - Interactive: co-constructing with a partner
  - Constructive: producing something beyond the given material
  - Active: manipulating the material (highlighting, copying)
  - Passive: receiving
  Design activities that call for constructive or interactive engagement.
- Accountable talk (Michaels, O'Connor and Resnick): discussion accountable to the learning community, to accurate knowledge, and to rigorous reasoning.

## Metacognition and self-regulation
- Zimmerman's cyclical model: forethought (goals, planning, self-efficacy), performance (strategy use, self-monitoring), self-reflection (evaluation, attribution).
- Learners are often poorly calibrated about what they know. Retrieval with feedback improves calibration.
- Help-seeking (Aleven et al.): students over-use hints (gaming the system) or avoid help. A Help Tutor that gives feedback on help-seeking behaviour has been studied as a metacognitive tutor.

## Motivation
- Expectancy-value theory (Eccles and Wigfield): effort follows expectancy of success times value. Value has four parts: attainment (identity), intrinsic (interest), utility (usefulness) and cost (effort, opportunity, emotional).
- Self-efficacy (Bandura): belief in one's capability for a specific task. Its strongest source is mastery experience, then vicarious experience, verbal persuasion, and physiological state.
- Self-determination theory (Deci and Ryan): autonomy, competence and relatedness sustain intrinsic motivation. Expected, tangible rewards for an already interesting task can undermine intrinsic motivation (the overjustification effect).
- Interest develops in four phases (Hidi and Renninger): triggered situational, maintained situational, emerging individual, well-developed individual.
- Utility-value interventions (Hulleman and Harackiewicz 2009): writing about the relevance of the material raised interest and grades, especially for low-expectancy students.
- Belonging interventions (Walton and Cohen).
- Growth mindset (Dweck): later meta-analyses find small average effects (Sisk et al. 2018), larger for at-risk students.
- ARCS model (Keller): Attention, Relevance, Confidence, Satisfaction.

## Backward design and alignment
- Understanding by Design (Wiggins and McTighe 1998/2005) works in three stages:
  1. Desired results: transfer goals, enduring understandings, essential questions, knowledge and skills.
  2. Assessment evidence: performance tasks (the GRASPS frame: goal, role, audience, situation, product, standards) plus other evidence.
  3. Learning plan: the WHERETO elements.
  Their six facets of understanding: explain, interpret, apply, have perspective, empathize, have self-knowledge.
- Constructive alignment (Biggs): objectives, activities and assessment all target the same performances.
- Revised Bloom's taxonomy (Anderson and Krathwohl 2001):
  - cognitive processes: remember, understand, apply, analyze, evaluate, create
  - knowledge types: factual, conceptual, procedural, metacognitive
  Write objectives with observable verbs.
- The agile version (05-823, as the course describes it): learning engineers iterate on goals, assessments and instruction together. An expert thinks aloud through an assessment, and the results change the goals. Course data and A/B experiments refine the design.

## Cognitive task analysis
- Clark, Feldon, van Merriënboer, Yates and Early (2008): experts leave out a large share of the decisions and steps when describing their own skill, by some estimates up to about 70 percent, because the knowledge has become automatic.
- Expert blind spot (Nathan and Koedinger 2000): teachers predicted that algebra word problems would be harder than equations. For beginning students the reverse was true.
- Methods:
  - think-aloud during real tasks
  - the critical decision method (Klein): probing past incidents
  - difficulty factors assessment (Koedinger): compare variants of problems to learn what makes them hard
  The results feed knowledge-component models, objectives and assessment items.

## Assessment and feedback
- Formative assessment (Black and Wiliam 1998, "Inside the Black Box"): classroom assessment used to adjust teaching produces substantial gains.
- Evidence-centered design (Mislevy): a student model (what we want to know), an evidence model (what behaviour shows it), and a task model (situations that elicit that behaviour).
- Validity (Messick's unified view): evidence from test content, response processes, internal structure, relations with other measures, and consequences of use. Reliability is consistency (Cronbach's alpha, test-retest).
- Item writing for multiple choice:
  - a clear stem that poses the question
  - one best answer
  - plausible distractors drawn from real misconceptions
  - no "all of the above"
  - no grammatical cues
- Psychometrics:
  - classical test theory gives item difficulty (proportion correct) and discrimination
  - item response theory models ability and item parameters (Rasch or 1PL, 2PL, 3PL)
- Rubrics are analytic (criteria scored separately) or holistic.
- Feedback research:
  - Hattie and Timperley (2007): good feedback answers three questions (Where am I going? How am I going? Where to next?) at four levels (task, process, self-regulation, self). Feedback about the self ("good girl") is least useful.
  - Shute (2008): be specific and elaborated, focus on the task, give it in manageable units. Immediate feedback helps procedural skills and novices, and some delay can aid transfer.
  - Kluger and DeNisi (1996): about a third of feedback interventions made performance worse, mostly when feedback drew attention to the self.

## Intelligent tutoring and personalization (05-432/832)
- Two loops (VanLehn 2006): the outer loop picks the next task, the inner loop gives step-level feedback and hints within a task.
- VanLehn (2011) meta-analysis: step-based tutoring systems came close to human tutors (effect sizes around 0.76 and 0.79 against no tutoring). Answer-based systems were far lower (about 0.31). Gains plateau once interaction reaches the step level.
- Model tracing: a cognitive model of correct and buggy production rules (ACT-R) traces each student step and diagnoses errors. Anderson, Corbett, Koedinger and Pelletier (1995) summarize the Cognitive Tutor lessons.
- Knowledge tracing (Corbett and Anderson 1995, Bayesian Knowledge Tracing):
  - four parameters per skill: prior knowledge, learning rate, guess, slip
  - it estimates mastery and drives mastery learning (practice until the probability of knowing passes about 0.95)
- Bloom's "2 sigma problem" (1984): one-to-one tutoring plus mastery learning gave very large gains. Later estimates are smaller but still substantial.
- Example-tracing tutors (Aleven et al.) built with CTAT (Cognitive Tutor Authoring Tools, CMU): authors demonstrate solutions to build behaviour graphs, so a tutor can be made without programming a cognitive model.
- Hints should escalate: point to the relevant feature, then teach the principle, then give the bottom-out answer.
- Learning curves (from CMU's DataShop) check whether a KC model is right. Error rate should fall smoothly across practice opportunities for each KC. Bumpy curves mean the KC model needs splitting or merging. Learning Factors Analysis and the Additive Factors Model automate this.
- Personalization by metacognition, affect and motivation:
  - detectors of boredom, confusion, frustration and "gaming the system" (Baker and colleagues)
  - boredom is persistent and linked to gaming and poorer learning
  - confusion that resolves can be productive
- What doesn't hold up: matching instruction to "learning styles". Pashler et al. (2008) found no adequate evidence for the meshing hypothesis. The course stresses telling proven personalization apart from popular ideas.

## Peer learning at scale (Design of Large-scale Peer Learning Systems)
- Peer Instruction (Mazur 1997): a conceptual question, individual vote, discussion with neighbours, revote. Porter, Bailey Lee and Simon (2013) found it halved fail rates across four computer science courses.
- Calibrated peer assessment: students first grade sample work and get feedback on their grading. Kulkarni et al. (2013) found peer grades in massive online classes landed close to staff grades for most submissions after calibration.
- PeerStudio (Kulkarni, Bernstein and Klemmer 2015): students review others' drafts to earn quick feedback on their own, so feedback arrives within minutes at any hour.
- Talkabout (Kulkarni et al. 2015): geographically diverse discussion groups in online courses were linked to better outcomes.
- Design patterns: rubrics with examples, calibration, review as the price of feedback, aggregation of several reviews, highlighting disagreement.
- The teacher's role becomes orchestration.
- Ethics: unpaid peer labour, fairness of grades, privacy of drafts.

## Tools for online learning and learning engineering (05-840)
- The course's three mechanics: feedback with active learning, collaboration between learners, and data-driven improvement.
- CMU's Open Learning Initiative: an evaluation found students in the OLI statistics course reached outcomes as good as or better than traditional students in about half the time (Lovett, Meyer and Thille 2008).
- The improvement loop: design, deploy, collect data, find weak spots (learning curves, item statistics), redesign, test with A/B experiments. "Close the loop" studies show redesigns from data analysis raising learning.
- Evaluation levels (Kirkpatrick): reaction, learning, behaviour, results. Satisfaction is not learning.

## Learning analytics and educational data mining
- The cycle (Clow 2012): learners, data, metrics, interventions, back to learners.
- Methods:
  - prediction (dropout, performance)
  - knowledge tracing (BKT, deep knowledge tracing, performance factors analysis)
  - clustering
  - process and sequence mining
  - visualization
  - discovery with models
- Teacher-facing tools: Lumilo (Holstein, McLaren and Aleven, CMU) gave teachers real-time analytics through mixed-reality glasses in classrooms using tutors, which helped teachers target help.
- Cautions:
  - predictions can become self-fulfilling labels
  - models can encode bias against groups
  - privacy law (FERPA, COPPA under 13) and consent
  - a dashboard number is not an intervention

## Educational games
- The CMU course names an "EDGE framework". The underlying published framework is Aleven, Myers, Easterday and Ogan (2010), "Toward a framework for the analysis and design of educational games" (CMU). I verified the paper this session. I did not confirm the "EDGE" acronym. It combines three things:
  1. A precise statement of learning objectives.
  2. The MDA model.
  3. Instructional design principles from the learning sciences.
  It was tested by analyzing Zombie Division.
- MDA (Hunicke, LeBlanc and Zubek 2004): mechanics produce dynamics, which produce aesthetics. Designers work from mechanics, players experience aesthetics first. The eight kinds of fun: sensation, fantasy, narrative, challenge, fellowship, discovery, expression, submission.
- Intrinsic integration (Habgood and Ainsworth 2011): when the learning content is the core mechanic (Zombie Division's division-based combat), children learned more and played longer than with an extrinsic version where quizzes interrupt play.
- Flow (Csikszentmihalyi): clear goals, immediate feedback, challenge balanced with skill.
- Gee's learning principles in good games: just-in-time information, "pleasantly frustrating" challenge, sandboxes, identity, well-ordered problems.
- Evaluate three things separately: fun (playtests, observation, voluntary play), learning (pre and post tests, transfer), and their integration (does playing well require the learning?).
- Evidence: meta-analyses find learning advantages for games over conventional instruction that are modest (about d = 0.3), larger when games include instructional support. Games were not consistently more motivating (Wouters et al. 2013, Clark, Tanner-Smith and Killingsworth 2016).
- Transformational games (Culyba, The Transformational Framework, CMU ETC 2018):
  - define the purpose and the player transformation sought
  - name the barriers to it
  - bring in domain experts
  - decide what evidence would show the change
  - playtest iteratively with real players
  The studio course pairs this with real clients and the discipline of reworking ideas that aren't fun.

## Informal learning, museums and learning media
- Contextual Model of Learning (Falk and Dierking): learning in free-choice settings is shaped by personal, sociocultural and physical contexts, accumulated over time.
- Visitor identity-related motivations (Falk): explorers, facilitators, professionals and hobbyists, experience seekers, rechargers.
- Six strands of science learning in informal settings (NRC 2009): interest, understanding, practice, reflection, use of tools and language, identity.
- Learning has cognitive, social and affective dimensions (Learning Media Design). Families learn through conversation, so design for talk among visitors.
- Design-based research (Brown 1992, Collins): iterative design in real settings that produces both better designs and theory.
- Evaluation types: front-end (before design), formative (during), remedial (after opening), summative (impact). Logic models connect activities to outcomes.

## Inclusive learning design and climate
- Universal Design for Learning (CAST): multiple means of engagement (the why), representation (the what) and action and expression (the how). Guidelines version 3.0 was released in 2024.
- Positive behaviour supports (PBIS): explicit expectations taught and acknowledged, tiered support. Evidence-Based Educational Design names "promoting positive behavior" and "community norms and habits of practice".
- Climate and belonging (Ambrose principle 6): stereotype threat, inclusive examples, clear norms, centralized versus marginalizing climates.

## Research methods for the learning sciences (05-748)
- Designs: randomized controlled trials (the What Works Clearinghouse standards), quasi-experiments, design experiments.
- Students are nested in classes and schools, so use hierarchical linear models.
- Fidelity of implementation (Dane and Schneider): adherence, exposure or dosage, quality of delivery, participant responsiveness, program differentiation.
- Efficacy is impact under ideal conditions, effectiveness under routine conditions. IES funding goals run exploration, development, efficacy, effectiveness, measurement.
- Protocol and discourse analysis:
  - think-aloud protocols coded for strategies
  - classroom talk patterns such as Initiation-Response-Evaluation versus dialogic talk
- Also: surveys and psychometrics, educational data mining, cognitive task analysis.

## Technology in learning (05-838)
- Technology alone does not raise learning. Pedagogy, teacher capacity and context decide outcomes (Cuban, Oversold and Underused).
- One Laptop per Child: a randomized evaluation in Peru (Cristia et al. 2012) found greatly increased computer access but no measurable gains in math or language scores.
- Sesame Street's model: formative research integrated with production (writers, researchers, educators together), testing segments with children for appeal and comprehension.
- Design for the real constraints: connectivity, shared devices, teacher time, language, culture.

## Sources
Verified this session: CMU Eberly Center "Learning Principles" page. Search confirmation of Aleven et al. 2010 (DIGITEL). From training: Ambrose et al. 2010. Koedinger, Corbett and Perfetti 2012 (Cognitive Science). Sweller et al. 2019 (Ed Psych Review). Mayer 2021. Clark and Mayer 2016/2023. Roediger and Karpicke 2006. Cepeda et al. 2006. Bjork 1994. Dunlosky et al. 2013 (PSPI). Koedinger et al. 2015 (L@S). Chi and Wylie 2014. Wiggins and McTighe 2005. Anderson and Krathwohl 2001. Clark et al. 2008 (CTA chapter). Nathan and Koedinger 2000. Black and Wiliam 1998. Hattie and Timperley 2007. Shute 2008. Kluger and DeNisi 1996. VanLehn 2006, 2011. Corbett and Anderson 1995. Aleven et al. 2016 (CTAT, IJAIED). Pashler et al. 2008. Porter et al. 2013 (SIGCSE). Kulkarni et al. 2013, 2015. Lovett et al. 2008. Hunicke et al. 2004. Habgood and Ainsworth 2011. Wouters et al. 2013. Clark et al. 2016. Falk and Dierking 2000. NRC 2009. CAST 2024. Cristia et al. 2012 (NBER/IDB).
