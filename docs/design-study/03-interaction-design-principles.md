# 3. Interaction design principles

Serves: CMU Interaction Design Fundamentals (05-360/660), Advanced Interaction Design (05-361/661), Designing Human-Centered Software, Intro to HCI (05-180), Interaction Design Studio 2. Bridges to RISD Design for Interaction and Web Design (see [19](19-interface-and-web.md)).

## Norman, The Design of Everyday Things (revised 2013)
- The two goals are discoverability (can I work out what actions are possible?) and understanding (what does it all mean, how is it supposed to work?).
- Affordance: a relationship between an object's properties and an agent's capabilities that decides how the object could be used (from Gibson). Signifier: a perceivable cue that tells people where and how to act. Designers mostly control signifiers. Norman added the term in 2013 because "affordance" had been stretched to mean "visible cue".
- Mapping: the relation between controls and their effects. Natural mapping uses spatial correspondence (stove knobs laid out like the burners) or cultural conventions.
- Constraints narrow the possible actions. There are four kinds: physical, cultural, semantic and logical.
- Feedback: immediate, informative, proportionate. Too much feedback is noise. Slow or absent feedback breeds repeated presses and errors.
- Conceptual model: the designer's model reaches the user only through the "system image", meaning the product, its behaviour and its documentation. If the system image misleads, the user builds a wrong model.

### The seven stages of action and the two gulfs
- The stages: form the goal. Then the execution side (plan, specify, perform) and the evaluation side (perceive, interpret, compare against the goal).
- Gulf of execution: the gap between what the user wants and what the system lets them do ("how do I...?"). Bridge it with signifiers, constraints, mappings and a good conceptual model.
- Gulf of evaluation: the gap between the system's state and the user's understanding of it ("what happened?"). Bridge it with feedback and a visible state.

### Human error
- Slips: the goal is right, the execution is wrong.
  - Action-based slips: capture errors (a familiar sequence takes over), description-similarity errors (acting on the wrong similar object), mode errors.
  - Memory-lapse slips: forgetting a step or the goal.
- Mistakes: the wrong goal or plan. They can be rule-based, knowledge-based or memory-lapse.
- Design for error:
  - understand the causes and minimize them
  - add sensibility checks
  - make actions reversible (undo) instead of confirming everything
  - make errors easy to detect and correct
  - treat a so-called error as an approximation to what the person wanted
- Forcing functions:
  - interlocks force the right order
  - lock-ins prevent premature stopping
  - lockouts prevent entry into a dangerous state
- Blame the design, not the person. Most errors come from systems (see Reason's Swiss cheese model in [06](06-human-factors-cognition-perception.md)).

### Knowledge in the head and in the world
Recognition is easier than recall. Put needed knowledge in the world (labels, visible options, defaults) when users cannot be expected to remember it. Constraints and conventions reduce what people must know.

## Shneiderman's eight golden rules (Designing the User Interface)
1. Strive for consistency.
2. Seek universal usability.
3. Offer informative feedback.
4. Design dialogs to yield closure.
5. Prevent errors.
6. Permit easy reversal of actions.
7. Keep users in control.
8. Reduce short-term memory load.

## Direct manipulation (Shneiderman 1983)
- Continuous representation of the objects of interest.
- Physical actions (pointing, dragging) instead of complex syntax.
- Rapid, incremental, reversible operations whose effects are immediately visible.

Hutchins, Hollan and Norman (1985) explain directness as small distances: semantic distance (does the system speak in terms of my goals?) and articulatory distance (does the form of input and output match the meaning?). They add engagement, the feeling of acting on the objects themselves.

## Laws of UX (Yablonski, lawsofux.com, verified list)
- Perception (Gestalt): proximity, similarity, common region, uniform connectedness, Prägnanz (people read ambiguous images in the simplest way).
- Cognition:
  - Miller's law
  - working memory
  - chunking
  - cognitive load
  - Hick's law (decision time grows with the number and complexity of choices)
  - choice overload
  - selective attention
  - serial position effect (first and last items are remembered best)
  - von Restorff effect (the item that differs is remembered)
  - Zeigarnik effect (unfinished tasks are remembered)
  - mental model
  - cognitive bias
- Experience and behaviour:
  - peak-end rule
  - aesthetic-usability effect
  - goal-gradient effect
  - flow
  - Doherty threshold (productivity rises when the system responds within about 400 ms)
  - Jakob's law (users spend most of their time on other products and expect yours to work the same way)
  - paradox of the active user (people do not read manuals, they start using)
  - Parkinson's law
- Design principles:
  - Fitts's law
  - Postel's law (be liberal in what you accept, conservative in what you send)
  - Tesler's law (complexity that cannot be removed has to live somewhere, so the system should carry it rather than the user)
  - Occam's razor
  - Pareto principle

Caveats worth holding:
- Miller's 7 plus or minus 2 describes immediate memory span. Working-memory capacity is closer to 4 chunks (Cowan 2001). It is not a limit on menu length, because menus rely on recognition, not recall.
- Hick's law fits simple choices among known, equally likely options. People scan long lists rather than decide among all items at once.
- Choice-overload effects are inconsistent in meta-analysis (see [10](10-persuasion-ethics-privacy.md)).

## Cooper, About Face (4th ed. 2014)
- Goal-directed design: design for users' goals (life, experience and end goals), not for tasks or features alone.
- Personas, one primary per interface. Scenarios: context scenarios first, then key-path and validation scenarios.
- Three models:
  - the implementation model (how it works)
  - the mental model (how users think it works)
  - the represented model (how the interface presents it)
  The represented model should follow the mental model, not the implementation.
- Posture:
  - sovereign apps take the screen for long sessions and reward rich, dense, keyboardable interfaces
  - transient apps come and go quickly and need large, clear, self-explanatory controls
  - daemonic apps run in the background
- Perpetual intermediates: most users are neither beginners nor experts. Design for intermediates, give beginners an on-ramp and experts shortcuts.
- Excise: work the tool demands that serves no user goal (navigation, confirmation, configuration). Remove it.
- Do not ask permission for routine actions. Prefer undo to confirmation dialogs. Raskin (The Humane Interface) adds that habituation makes confirmations useless, and that modes cause errors.

## Feedback timing (Miller 1968, Card et al. 1991, Nielsen 1993)
- About 0.1 s feels instantaneous. Direct manipulation needs this.
- About 1 s keeps the user's flow of thought. Show subtle progress.
- About 10 s is the limit of attention on the dialogue. Beyond it, show a progress indicator with an estimate and allow other work.

## Progressive disclosure and information architecture
- Progressive disclosure (Nielsen 2006): show the core options, put advanced ones a step away. Staged disclosure walks through steps.
- Information architecture (Rosenfeld, Morville and Arango): organization schemes, labeling, navigation, search. Card sorting (open, closed, hybrid) reveals users' categories. Tree testing checks findability without visual design.
- Information foraging (Pirolli and Card 1999): people follow "information scent", the cues that predict whether a path leads to their goal. Labels must give strong scent.

## Forms and errors
- Labels above fields scan fastest (Wroblewski, Web Form Design).
- Validate inline once a field is done, not while typing.
- Error messages say what happened and how to fix it, in plain language, next to the field, without blame.
- Ask only for what is needed. Every field is a cost.

## Microinteractions (Saffer 2013)
A microinteraction has four parts: a trigger (user or system), rules, feedback, and loops and modes. Small moments (toggles, likes, saving) carry much of a product's feel.

## Interaction design materials and dimensions
- Crampton Smith's dimensions, with Silver's fifth:
  - 1D words
  - 2D visual representation
  - 3D physical objects and space
  - 4D time
  - 5D behaviour
- IxDF asks students to "explore interaction design materials". Advanced Interaction Design adds data and AI as materials, and design systems as a medium.

## Advanced interaction design: prediction, assistance, automation, systems
- Levels of automation:
  - Sheridan and Verplank's ten-level scale
  - Parasuraman, Sheridan and Wickens (2000): automation applies separately to four stages (information acquisition, information analysis, decision selection, action implementation). Each can sit at a different level.
- "Predict, assist, automate" is a spectrum. The more the system acts on its own, the more it needs transparency, override and recovery (see [09](09-human-ai-interaction.md)).
- Systems thinking (Meadows, Thinking in Systems): stocks, flows, feedback loops (reinforcing and balancing), delays, leverage points. Enterprise products serve many roles, permissions, handoffs and integrations. Map actors and flows before screens.
- Design systems:
  - Atomic Design (Frost 2016): atoms, molecules, organisms, templates, pages
  - design tokens for colour, type, spacing and motion
  - documented components with states
  - governance and contribution rules
  A design system makes consistency cheap and frees attention for the hard problems.
- Data as a material: what data exists, its quality, latency, bias and privacy, and what feedback loops the product creates.

## Sources
Verified this session: lawsofux.com list. From training: Norman, DOET revised. Shneiderman et al., Designing the User Interface (6th ed.). Shneiderman 1983 (IEEE Computer). Hutchins, Hollan and Norman 1985. Cooper et al., About Face 4. Raskin 2000. Nielsen, Usability Engineering. Rosenfeld, Morville and Arango, Information Architecture 4. Pirolli and Card 1999. Wroblewski 2008. Saffer 2013. Parasuraman, Sheridan and Wickens 2000. Meadows 2008. Frost 2016.
