# 6. Human factors, cognition and perception

Serves: CMU Human Factors (05-413/813), Perception (05-814), Applications of Cognitive Science (05-395/795), Cognitive Modeling for HCI (05-811), Intro to HCI (cognition and perception), Interactive Extended Reality (perception basics).

## Scope of human factors
- Physical (anthropometry, biomechanics, environment), cognitive (perception, attention, memory, decision), organizational (teams, procedures, incentives, culture).
- The course stresses that organizational arrangements can amplify or correct human factors problems. Errors are system outcomes.
- Anthropometry: design for the 5th to 95th percentile of the relevant population, or make it adjustable. Size clearances for the largest users and reach for the smallest. Averages fit almost no one.

## Perception
- Perception is construction (course framing): the senses deliver ambiguous signals, and top-down knowledge, expectation and context interpret them.
  - Examples: the same shape read as B or 13 depending on its neighbours, the word superiority effect, size and lightness constancy.
- Gestalt grouping: proximity, similarity, closure, continuity, common fate (things moving together group), figure and ground, symmetry, Prägnanz. These are the working rules of layout. See [15](15-grids-layout-editorial.md).
- Colour vision:
  - three cone types (L, M, S) feed opponent channels (red-green, blue-yellow, light-dark)
  - about 8 percent of men and 0.5 percent of women have a red-green deficiency
  - luminance contrast, not hue, carries edges, legibility and fine detail
- Acuity is sharp only in the fovea (about 2 degrees). The periphery detects motion and change.
- Reading:
  - fixations of about 200 to 250 ms, saccades of about 7 to 9 letters
  - the perceptual span in English extends roughly 3 to 4 letters left and 14 to 15 right of fixation
  - word recognition runs on letters recognized in parallel, not on whole-word shape
- Hearing spans about 20 Hz to 20 kHz. Sound localization works from timing and level differences. Touch involves spatial acuity, vibration and force.
- Psychophysics:
  - Weber's law: the just-noticeable difference is a constant fraction of magnitude.
  - Stevens' power law: perceived magnitude is a power function of physical magnitude. Area is underestimated, so do not encode quantities by area when precision matters.
  - Signal detection theory: hits, misses, false alarms, correct rejections. Sensitivity (d') is separate from response criterion (beta). Alarm design trades misses against false alarms, and frequent false alarms train people to ignore alarms (the cry-wolf effect).
- Perception changes with learning and development (course goal). Experts literally see differently.

## Attention
- Kinds: selective (the cocktail party effect), divided, sustained. Vigilance declines over 15 to 30 minutes of monitoring.
- People miss what they do not attend to:
  - inattentional blindness (Simons and Chabris 1999, the gorilla study)
  - change blindness (Rensink)
  - banner blindness on the web
- Wickens' multiple resource theory: tasks interfere less when they draw on different resources. The dimensions are stages (perception and cognition vs response), modalities (visual vs auditory), codes (spatial vs verbal) and visual channels (focal vs ambient). Pairing a visual task with an auditory one works better than two visual tasks.
- SEEV model (Wickens): where attention goes depends on salience, effort (inhibits), expectancy and value. Put important information where people expect it, make it salient, keep it near.
- Interruptions cost a resumption lag. Interrupting at task breakpoints costs less (Iqbal and Bailey). CMU research (Fogarty, Hudson and colleagues) showed that simple sensors can predict when a person can be interrupted.

## Memory
- Working memory (Baddeley): phonological loop, visuospatial sketchpad, central executive, episodic buffer.
  - Capacity is about 4 chunks (Cowan 2001). Miller's 7 plus or minus 2 is an older span estimate.
  - Unrehearsed items fade within about 15 to 30 seconds.
- Long-term memory: episodic, semantic and procedural.
  - Encoding depth matters (levels of processing).
  - Retrieval depends on cues.
  - Recognition beats recall.
  - Interference, not decay, causes much forgetting.
- Prospective memory (remembering to do something later) fails often. Post-completion errors happen when the main goal is met before a cleanup step: the card left in the ATM, the original left in the copier. The fix is to order the steps so the cleanup comes before the goal (card returned before cash).

## Decision making
- Heuristics and biases (Tversky and Kahneman): availability, representativeness, anchoring. See [10](10-persuasion-ethics-privacy.md).
- Bounded rationality and satisficing (Simon): people choose the first option that is good enough.
- Naturalistic decision making (Klein, recognition-primed decisions): experts in time-pressured settings match situations to patterns and simulate one option rather than compare many.

## Skill and error
- Skill acquisition (Fitts and Posner): cognitive, then associative, then autonomous stages. Automatic behaviour is fast but hard to change, and it fires in the wrong context (capture errors).
- Rasmussen's skill-, rule- and knowledge-based levels map onto Reason's error types:
  - slips and lapses at the skill level
  - rule-based mistakes (a good rule misapplied, or a bad rule)
  - knowledge-based mistakes in novel situations
  - violations are deliberate departures from procedure
- Reason's Swiss cheese model: accidents happen when holes in several defensive layers line up. The layers are latent conditions (design, management, training) plus active failures at the sharp end. A "just culture" separates honest error from recklessness so that people report problems.
- Situation awareness (Endsley 1995) has three levels: perception of the elements, comprehension of their meaning, projection of their future state.

## Automation
- Bainbridge, "Ironies of Automation" (1983): automation leaves operators the hardest tasks (taking over when it fails) while eroding the skills and awareness those tasks need. Monitoring a reliable system is itself a hard task humans do badly.
- Misuse and disuse (Parasuraman and Riley 1997):
  - automation bias: accepting automated advice without checking
  - complacency: reduced monitoring
  - disuse: ignoring useful automation after it has erred
- Mode errors: "what's it doing now?" (Sarter and Woods). Make modes visible and minimize them.
- Trust calibration (Lee and See 2004): appropriate reliance matches trust to the automation's real capability. Trust rests on performance, process and purpose. Continues in [09](09-human-ai-interaction.md).

## Applied domains named in the course
- Medicine:
  - "To Err Is Human" (Institute of Medicine 1999) estimated 44,000 to 98,000 US deaths a year from medical error
  - infusion pump programming errors
  - look-alike and sound-alike drug names, addressed with Tall Man lettering (hydrOXYzine, hydrALAZINE)
  - barcode medication administration
  - checklists (Pronovost's central line checklist, Gawande's surgical checklist)
- Driving: glances away from the road longer than about 2 seconds sharply raise crash risk. NHTSA's guidelines for in-vehicle tasks call for single glances of 2 seconds or less and 12 seconds total.
- Voting: the 2000 Palm Beach County "butterfly ballot" misaligned candidate names with punch holes, a mapping failure that likely changed votes.
- Buildings: stair risers and treads must be consistent, since people stop looking after the first steps. Most consumer injuries trace to predictable human behaviour.

## Cognitive modeling
- Model Human Processor (Card, Moran and Newell 1983), approximate cycle times:
  - perceptual processor about 100 ms (50 to 200)
  - cognitive processor about 70 ms (25 to 170)
  - motor processor about 70 ms (30 to 100)
  These predict simple reaction times of about 240 ms and support KLM estimates.
- GOMS family: KLM, CMN-GOMS, NGOMSL, CPM-GOMS. See [02](02-evaluation-and-measurement.md). These models predict expert performance cheaply before a system exists.
- ACT-R (Anderson):
  - declarative memory of chunks with activation that rises with use and decays with time
  - procedural memory of production rules (if-then)
  - a subsymbolic layer for timing and errors
  ACT-R underlies the Cognitive Tutors' model tracing. See [07](07-learning-science.md). Other architectures: Soar, EPIC.

## From cognitive science to applications (05-395)
The course looks at how basic research becomes application and what gets in the way.
- Cognitive tutors: the success case.
- Eyewitness testimony (Loftus, Wells and colleagues):
  - leading questions and post-event information alter memories
  - reforms: double-blind lineup administration, fair fillers, recording the witness's confidence at once
- Navigation: turn-by-turn GPS reduces spatial learning compared with map use. Track-up maps suit immediate turns, north-up maps suit planning.
- VR: presence, vection, cybersickness from visual-vestibular conflict, vergence-accommodation conflict.
- Speech: recognition errors cluster by accent and speech condition. Synthesized speech needs natural prosody.
- Neuromarketing: often overclaims from reverse inference (activity in a region does not prove a mental state).
- Obstacles to application: ecological validity, scale, cost, ethics, and the gap between effect sizes in the lab and in the field.

## Sources
From training: Wickens, Hollands, Banbury and Parasuraman, Engineering Psychology and Human Performance. Reason, Human Error (1990). Endsley 1995. Bainbridge 1983. Parasuraman and Riley 1997. Lee and See 2004. Card, Moran and Newell 1983. Anderson, How Can the Human Mind Occur in the Physical Universe? Simons and Chabris 1999. Cowan 2001. Baddeley 2000. Kohn et al. (IOM) 1999. Wolfe et al., Sensation and Perception. Rayner 1998 (reading eye movements). Wells et al. 2020 eyewitness recommendations.
