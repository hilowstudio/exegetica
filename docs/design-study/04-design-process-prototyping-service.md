# 4. Design process, sketching, critique, prototyping, service design

Serves: CMU IxDF (process, critique, reframing, divergent thinking), Prototyping Algorithmic Experiences (PAX), Programming Interactive Experiences (PIX), Rapid Prototyping of Computer Systems, Service Design (05-452/652), Digital Service Innovation (05-470/670), HCI Project I and II, AI Innovation in Healthcare (matchmaking). Also RISD Design Studio 1 to 4 (search, research, analysis, ideation, prototyping).

## Process models
- Double Diamond (UK Design Council, 2005): Discover (diverge), Define (converge), Develop (diverge), Deliver (converge). The first diamond finds the right problem, the second the right solution.
- Stanford d.school: empathize, define, ideate, prototype, test. IDEO's human-centred design uses the same loop.
- Lean UX and Lean Startup: state hypotheses, build the smallest test, measure, learn.
- These are maps, not recipes. Real projects loop back.

## How designers think
- Wicked problems (Rittel and Webber 1973): no definitive formulation, no stopping rule, solutions are better or worse rather than true or false, every attempt counts.
- Schön, The Reflective Practitioner (1983): reflection-in-action. Design is a "reflective conversation with the materials of a situation". The designer makes a move, the situation talks back, and the designer reframes.
- Reframing (Dorst, Frame Innovation 2015): a frame takes the form "if we look at the situation as X, then doing Y will lead to Z". New frames open solution spaces the given problem statement hid. IxDF teaches reframing a given problem to generate multiple solutions.
- Cross, Designerly Ways of Knowing: designers are solution-focused and reason abductively, from a desired value to a "what" and "how" that could produce it.

## Divergent thinking and ideation
- Osborn's brainstorming rules (and IDEO's versions):
  - defer judgment
  - encourage wild ideas
  - build on others' ideas
  - go for quantity
  - one conversation at a time
  - stay on topic
  - be visual
- Group brainstorming suffers production blocking and evaluation apprehension. Brainwriting (6-3-5: six people, three ideas, five minutes, pass on) and solo-then-group sessions produce more ideas.
- Other tools:
  - Crazy 8s (eight sketches in eight minutes)
  - SCAMPER (substitute, combine, adapt, modify, put to other use, eliminate, reverse)
  - analogies from other domains
  - bodystorming (acting out the situation in place)
  - improv "yes, and" (Digital Service Innovation uses improv brainstorming)
- Design fixation (Jansson and Smith 1991): showing an example narrows the ideas that follow. Show several diverse examples or none.

## Sketching (Buxton, Sketching User Experiences, 2007)
- Qualities of a sketch: quick, timely, inexpensive, disposable, plentiful. It has a clear vocabulary (its style says "sketch"), distinct gestures, minimal detail, and just enough refinement. It suggests and explores rather than confirms, and stays ambiguous.
- Sketches are for getting the right design. Prototypes are for getting the design right.
- Tohidi, Buxton, Baecker and Sellen (2006): when users see several designs side by side, they criticize more freely than when shown one.

## Storyboards
Truong, Hayes and Abowd (2006) found the elements that make storyboards work:
- level of detail kept low
- some text, but not too much
- people and their emotions included
- a small number of frames (about 3 to 6)
- the passage of time shown

A storyboard communicates context, motivation, use and outcome without building anything.

## Speed dating (Davidoff, Lee, Dey and Zimmerman 2007, CMU, Zimmerman and Forlizzi 2017)
- Show participants many storyboarded concepts quickly (need validation), then enact a few with simple prototypes in user enactments.
- It reveals which needs are real and where social boundaries lie (what feels creepy or presumptuous) before anything is built.
- The authors describe it as a menu of possible futures to choose among.

## Critique
- Connor and Irizarry, Discussing Design (2015): critique is analysis of a design against its objectives. It is not reaction ("I don't like it") and not direction ("make it blue").
  - Useful questions: what is the objective, which elements relate to it, are they effective, why or why not.
  - The presenter states the goals and the kind of feedback wanted. Critics ask questions before giving opinions.
- Liz Lerman's Critical Response Process:
  1. Statements of meaning (what was striking).
  2. The artist asks questions.
  3. Responders ask neutral questions.
  4. Responders offer opinions, with permission.
- Lightweight frame (d.school): "I like, I wish, what if".
- Feldman's model for art criticism (description, analysis, interpretation, judgment) holds off judgment until the work has been seen.
- IxDF asks students to facilitate structured critique. Service Design asks them to draw actionable insights from critique of their own and others' work. RISD courses ask students to speak about peers' work in supportive, respectful ways.

## Communicating design work
Persuasive interim and final artifacts (an IxDF outcome): concept posters, annotated wireframes, storyboards, flows, video sketches. A presentation arc: problem, insight, concept, evidence, open questions, ask.

## Prototyping theory
- Houde and Hill (1997), "What do prototypes prototype?". Three dimensions:
  - role: what the artifact does in the user's life
  - look and feel: sensory experience
  - implementation: techniques and components that make it work
  An integration prototype covers all three. Pick the dimension that matches the open question.
- Lim, Stolterman and Tenenberg (2008), "The anatomy of prototypes":
  - Prototypes are filters: each one lets designers explore some qualities (appearance, data, functionality, interactivity, spatial structure) while ignoring others.
  - They are manifestations: material, resolution and scope.
  - Economic principle: the best prototype is the simplest one that makes the possibilities and limits of an idea visible and measurable.
- Fidelity has several dimensions (McCurdy et al. 2006):
  - visual refinement
  - breadth of functionality
  - depth of functionality
  - richness of interactivity
  - richness of the data model
  A prototype can be high on one and low on others ("mixed fidelity").
- PAX says it directly: students learn to judge whether a prototyping approach fits a given design or research question.

### Prototyping methods
- Paper prototyping (Snyder 2003): a person plays the computer, swapping paper screens. It finds flow and comprehension problems before code, and people criticize rough work more freely.
- Wizard of Oz (Kelley 1984, developed at CMU for natural-language systems): a hidden human simulates the system's intelligence. It is essential for testing speech, conversation and AI concepts before models exist. Debrief participants afterwards.
- Experience prototyping (Buchenau and Suri 2000): any representation that lets people experience a design rather than see it. It serves to understand existing experiences, explore ideas, and communicate.
- Video prototypes and video sketches (Digital Service Innovation): act out the service on video to communicate value and pitch it.
- Parallel prototyping (Dow et al. 2010): making several designs in parallel and getting feedback on each produced better results and more designer confidence than iterating on one design in sequence.
- Algorithmic and AI experiences (PAX):
  - prototype with realistic data and realistic errors
  - simulate model outputs, including wrong and low-confidence ones
  - use Wizard of Oz when the capability is uncertain
  - prototype the failure states and recovery, not only the happy path
- IoT and spatial computing prototyping: Arduino-class boards, sensors, quick 3D prints, laser-cut parts.
- Rapid prototyping of computer systems (05-540/872):
  - derive specifications from a perceived need
  - partition functions between hardware and software
  - write interface specifications between subsystems
  - integrate and debug
  - evaluate with the end application
- Iteration cadence (HCI Project II): weekly build, test, reflect cycles. Fidelity rises as uncertainty falls.

## Service design
- Services are often characterized as intangible, produced and consumed at once, perishable and variable. Service-dominant logic (Vargo and Lusch 2004) holds that value is co-created in use, not delivered in a product.
- Service blueprint (Shostack 1982/84, Bitner, Ostrom and Morgan 2008). Rows:
  - physical evidence
  - customer actions
  - frontstage employee actions
  - backstage actions
  - support processes
  Separating lines: interaction, visibility, internal interaction. Mark fail points and wait points. The backstage is what makes the frontstage possible.
- Customer journey map: the customer's view over time. A blueprint adds the organization behind it.
- Other models:
  - stakeholder maps
  - ecosystem and system maps
  - touchpoint inventories
  - moments of truth
  - service prototypes (enactments, desktop walkthroughs with figures)
- Product-service systems (Tukker 2004): product-oriented, use-oriented (leasing, sharing) and result-oriented (paying for outcomes).
- Platforms: multi-sided markets, network effects, and the cold-start problem (each side waits for the other).
- The Service Design course asks students to show how a service unfolds through design and communication. That means time-based representations.

## Innovation framing
- Desirability (people want it), feasibility (it can be built), viability (it can sustain itself). IDEO's three lenses. Digital Service Innovation assesses all three.
- Business Model Canvas (Osterwalder), nine blocks: customer segments, value propositions, channels, customer relationships, revenue streams, key resources, key activities, key partners, cost structure.
- Matchmaking (Bly and Churchill 1999, used by Zimmerman for AI): start from a technical capability and search for the people and situations where it creates value. This inverts the usual user-first start, and suits new technologies like AI.
- Research through Design (Zimmerman, Forlizzi and Evenson 2007): design artifacts as knowledge contributions. Judge them on process, invention, relevance and extensibility.

## Sources
From training: Design Council 2005. Rittel and Webber 1973. Schön 1983. Dorst 2015. Cross 2006. Buxton 2007. Tohidi et al. 2006 (CHI). Truong et al. 2006 (DIS). Davidoff et al. 2007 (UbiComp). Zimmerman and Forlizzi 2017 (She Ji). Connor and Irizarry 2015. Lerman and Borstel 2003. Houde and Hill 1997. Lim et al. 2008 (TOCHI). McCurdy et al. 2006 (CHI). Snyder 2003. Kelley 1984 (TOIS). Buchenau and Suri 2000 (DIS). Dow et al. 2010 (TOCHI). Shostack 1984 (HBR). Bitner et al. 2008. Vargo and Lusch 2004. Tukker 2004. Osterwalder and Pigneur 2010. Zimmerman et al. 2007 (CHI).
