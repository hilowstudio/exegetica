# 10. Persuasion, behaviour change, ethics, privacy and security, policy

Serves CMU courses:
- Persuasive Design in HCI (05-315/615)
- Psychological Foundations for Designing for Impact
- Usable Privacy and Security (05-436/836)
- Building Technologies for the Resistance
- Design and/of Policy
- Justice Through Design
- Designing for the Present and Future of Work
- Computing for Good

## Persuasive technology
- Fogg, Persuasive Technology (2003). Computers persuade as:
  - tools: reduction, tunneling, tailoring, suggestion, self-monitoring, surveillance, conditioning
  - media: simulation of cause and effect
  - social actors: praise, reciprocity, similarity
- Fogg Behavior Model: behaviour happens when motivation, ability and a prompt come together at the same moment.
  - Low ability needs high motivation, and the reverse.
  - Prompts work as a spark (when motivation is low), a facilitator (when ability is low) or a signal (when both are present).
  - Ability rises as these get simpler: time, money, physical effort, mental effort, social deviance, and departure from routine.
- Persuasive Systems Design (Oinas-Kukkonen and Harjumaa 2009) groups techniques four ways: primary task support, dialogue support, system credibility, social support.

## Influence and judgment
- Cialdini's principles: reciprocity, commitment and consistency, social proof, authority, liking, scarcity, and unity (added in 2016).
- Dual-process thinking (Kahneman): fast, automatic System 1 against slow, effortful System 2.
- Biases with design reach:
  - anchoring
  - framing
  - loss aversion (prospect theory)
  - default effects: organ donation consent rates differ hugely between opt-in and opt-out countries (Johnson and Goldstein 2003)
  - present bias
  - status quo bias
  - availability
- Choice overload: the famous jam study (Iyengar and Lepper 2000) does not generalize reliably. A meta-analysis found an average effect near zero with wide variation (Scheibehenne et al. 2010).
- Nudge and choice architecture (Thaler and Sunstein 2008): libertarian paternalism, meaning every design has a default and some ordering, so choose them well. The UK Behavioural Insights Team's EAST checklist: make it Easy, Attractive, Social, Timely.
- Evidence check: nudge effects in published academic studies are larger than those run at scale by government nudge units, about 1.4 percentage points on average (DellaVigna and Linos 2022). A large meta-analysis found little evidence for nudging overall after correcting for publication bias (Maier et al. 2022). Expect small effects and test them.

## Behaviour change models
- COM-B and the Behaviour Change Wheel (Michie, van Stralen and West 2011):
  - Behaviour arises from Capability, Opportunity and Motivation.
  - Nine intervention functions include education, persuasion, incentivization, training, environmental restructuring, modelling and enablement.
  - The Behaviour Change Technique Taxonomy (v1) lists 93 techniques.
- Theory of Planned Behaviour (Ajzen): attitudes, subjective norms and perceived control predict intention, which predicts behaviour, with an intention-behaviour gap.
- Goal setting (Locke and Latham): specific, challenging goals beat "do your best".
- Implementation intentions (Gollwitzer): "if situation X, then I will do Y" plans. They had a medium-to-large effect on goal attainment in meta-analysis (Gollwitzer and Sheeran 2006).
- Habits (Wood and Neal): context-cued automatic behaviour.
  - Stable contexts build habits. Changing context (moving house) breaks them.
  - Lally et al. (2010): forming a habit took a median of 66 days, ranging from about 18 to 254.
- Fresh-start effect (Dai, Milkman and Riis 2014): people start goals at temporal landmarks such as Mondays, birthdays and new terms.
- Feedback and social comparison:
  - Home energy reports comparing households with neighbours cut use by about 2 percent.
  - Descriptive norms alone can make low users drift up (a boomerang). Adding an injunctive cue such as a smiley face prevents it (Schultz et al. 2007).
- Self-monitoring, commitment devices, reminders, and tailoring of all three.
- Transtheoretical "stages of change" (Prochaska): widely used and weakly supported as a basis for staging interventions.
- Gamification (Deterding et al. 2011, "game design elements in non-game contexts"):
  - Meta-analyses find small positive effects that fade with novelty.
  - Leaderboards can demotivate low performers.
  - Rewards for already interesting tasks can crowd out intrinsic motivation. See self-determination theory in [07](07-learning-science.md).

## Psychological foundations for designing for impact (05-899)
The course's six themes:
1. Cognitive, social and self-related biases: confirmation bias, motivated reasoning, fundamental attribution error, false consensus, self-serving bias.
2. Mind, body and behaviour links: embodied cognition. Several famous findings failed to replicate, including power posing and ego depletion, so cite with care.
3. Fiction and games:
   - narrative transportation (Green and Brock) lowers counter-arguing, so stories persuade
   - the Proteus effect (Yee and Bailenson 2007): people's avatars change their behaviour
4. Goal pursuit and habit formation: see above.
5. Anonymity and online behaviour:
   - the online disinhibition effect (Suler 2004), from dissociative anonymity, invisibility, asynchronicity and minimized authority
   - the SIDE model: anonymity can strengthen group identity and norms rather than dissolve them
6. Unconscious associations and goals: implicit association measures have limited reliability for individuals, and many priming effects failed to replicate.

Replication context: the Open Science Collaboration (2015) replicated well under half of a sample of psychology findings. Treat single striking studies as hypotheses.

## Ethics of persuasion
- Berdichevsky and Neuenschwander (1999):
  - the creators of persuasive technology answer for reasonably predictable outcomes
  - methods and intended outcomes must both be ethical
  - a golden rule: never seek to persuade someone of something you would not consent to be persuaded of
- Manipulation (Susser, Roessler and Nissenbaum 2019): covertly influencing someone by exploiting their weaknesses, bypassing their capacity to decide. Persuasion that works through reasons is not manipulation.
- Dark patterns:
  - Brignull coined the term in 2010.
  - Gray et al. (CHI 2018) group them into five strategies: nagging, obstruction, sneaking, interface interference, forced action.
  - Mathur et al. (2019) found dark patterns on about 11 percent of roughly 11,000 shopping sites.
  - Regulators now act. The FTC's 2022 report "Bringing Dark Patterns to Light" and the EU Digital Services Act prohibit some designs.
- The attention economy: designs that capture time against the user's reflective interest (Williams, Stand Out of Our Light).
- Children: the UK Age Appropriate Design Code (2021) sets high-privacy defaults and bans nudges against children's interests. Similar US state laws face court challenges.
- Value Sensitive Design (Friedman and Hendry 2019):
  - conceptual, empirical and technical investigations
  - direct and indirect stakeholders
  - value tensions made explicit
  - envisioning cards

## Participation, justice, speculation
- Participatory design (the Scandinavian tradition, e.g., the UTOPIA project): workers and users share design decisions.
- Co-design (Sanders and Stappers 2008): people take part as experts of their own experience.
- Design Justice (Costanza-Chock 2020, Design Justice Network principles):
  - centre the voices of those directly affected
  - put community impact above designers' intentions
  - see the designer as a facilitator
  - share power
  - work toward sustainable, community-led outcomes
- Speculative and critical design (Dunne and Raby 2013):
  - design to raise questions rather than solve problems
  - the futures cone (probable, plausible, possible, preferable)
  - design fiction
- Justice Through Design: histories of professional ethics and activism, and communities building alternative objects, systems and organizations.

## Design and policy (Design and/of Policy)
- The course rejects the sequence of build, then use, then regulate. Policy and design shape each other and should be engaged together.
- Examples:
  - GDPR shaped consent interfaces
  - COPPA and FERPA shape education technology
  - content moderation policy shapes interface affordances
  - labour law shapes gig platforms
- Methods: policy prototyping, speculative scenarios, case analysis of "knotty" problems such as privacy, moderation, gig work and AI safety.

## Future of work
- Algorithmic management: Lee et al. (2015) found Uber and Lyft drivers working with algorithmic assignment, information asymmetry and opaque ratings.
- Automation shifts tasks and deskills or reskills. Worker agency and governance matter.
- Participatory approaches centre worker expertise in tool design. Case studies include fast food, logistics and knowledge work.

## Usable privacy and security (05-436/836)
- Security is a secondary task. People want to do their work, not be secure.
- Whitten and Tygar (1999), "Why Johnny Can't Encrypt":
  - most participants could not correctly encrypt email with PGP 5.0 within 90 minutes
  - the properties that make security hard to use: the unmotivated user, abstraction, lack of feedback, the barn door (once a secret leaks it is gone), the weakest link
- Adams and Sasse (1999), "Users Are Not the Enemy": insecure behaviour stems from policies that ignore how people work.
- Herley (2009): rejecting security advice is often rational once its cost is compared with its benefit.
- Warnings:
  - Wogalter's Communication-Human Information Processing model: source, channel, attention, comprehension, attitudes and beliefs, motivation, behaviour. A warning can fail at any stage.
  - Habituation makes repeated warnings invisible. Varying them helps.
- Phishing education: CMU's Anti-Phishing Phil game and embedded training (Sheng, Kumaraguru, Cranor and colleagues).
- Passwords:
  - CMU studies (Komanduri et al. 2011, Ur et al. 2012) found long passwords with few composition rules beat short complex ones. Strength meters shape behaviour.
  - NIST SP 800-63B moved away from forced composition rules and periodic rotation. It favours length, checks against breached-password lists, allows paste and password managers, and requires change only on compromise. The 2024 to 2025 revision raised the minimum for single-factor passwords. I recall 15 characters, which should be checked before use.
  - Multi-factor authentication and passkeys (WebAuthn) remove phishable secrets.
- Privacy:
  - Notice and choice fails at scale. McDonald and Cranor (2008) estimated that reading the privacy policies of the sites a person visits would take about 200 hours a year.
  - Privacy nutrition labels (Kelley, Bresee, Cranor and Reeder 2009, CMU) made policies comparable. They are the ancestor of app store privacy labels.
  - Contextual integrity (Nissenbaum): privacy is appropriate information flow given the norms of a context. A flow is described by sender, recipient, subject, information type and transmission principle. The same data can be fine in one flow and a violation in another.
  - Privacy by design (Cavoukian): proactive, private by default, embedded, positive-sum, end-to-end security, visibility, respect for users.
  - Data minimization and purpose limitation (GDPR Article 5).
  - The "privacy paradox" (stated concern against actual behaviour) is better explained by resignation and a lack of real choice (Draper and Turow 2019).
  - Children and students: COPPA (verifiable parental consent under 13), FERPA (education records, with a "school official" exception for vendors under the school's control), and state student-privacy laws.
- Vulnerable users: intimate partner abusers exploit ordinary features (location sharing, account access). Freed et al. (2018) recommend designing for an adversary who shares the household.

## Technologies of resistance
- The problem: surveillance capitalism (Zuboff 2019) harvests and monetizes data and attention with weak consent and accountability.
- Tactics:
  - obfuscation (Brunton and Nissenbaum 2015, tools such as TrackMeNot and AdNauseam)
  - data poisoning and protective perturbation (Glaze and Nightshade against image-model training)
  - computer-supported collective action (Turkopticon for crowd workers, Irani and Silberman 2013)
  - non-participation
- Such tools must be useful and usable enough for sustained use. They must also be ethical: they should shift power toward people who have little, and not hand capabilities to bad actors.

## Computing for Good
- Projects with communities, non-profits and agencies in health, development, disaster relief, education and civic engagement.
- Stakeholder-centred design, sustainable deployment (maintenance after the students leave), project management.

## Sources
From training: Fogg 2003 and the behavior model. Oinas-Kukkonen and Harjumaa 2009. Cialdini 2021. Kahneman 2011. Johnson and Goldstein 2003. Scheibehenne et al. 2010. Thaler and Sunstein 2008. DellaVigna and Linos 2022 (Econometrica). Maier et al. 2022 (PNAS). Michie et al. 2011. Gollwitzer and Sheeran 2006. Lally et al. 2010. Dai et al. 2014. Schultz et al. 2007. Deterding et al. 2011. Open Science Collaboration 2015. Berdichevsky and Neuenschwander 1999. Susser et al. 2019. Gray et al. 2018. Mathur et al. 2019. Friedman and Hendry 2019. Costanza-Chock 2020. Dunne and Raby 2013. Lee et al. 2015. Whitten and Tygar 1999. Adams and Sasse 1999. Herley 2009. Wogalter 2006. McDonald and Cranor 2008. Kelley et al. 2009. Nissenbaum 2010. Cavoukian 2009. Draper and Turow 2019. Freed et al. 2018. Brunton and Nissenbaum 2015. Irani and Silberman 2013.
