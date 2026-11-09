# 2. Evaluation and measurement

Serves: CMU UCRE (usability evaluation), Special Topics "Evaluate Research: Think Aloud Protocol and Usability Testing", "UX Research with Quantitative Data Sources", HCI for Product Managers (Heuristic Analysis, Think-Aloud), Interactive Data Science (A/B experiments), Cognitive Modeling for HCI (GOMS/KLM), PUI and capstones (test, then revise).

## What usability means
- ISO 9241-11: the extent to which specified users can achieve specified goals with effectiveness, efficiency and satisfaction in a specified context of use.
- Nielsen's five components: learnability, efficiency, memorability, errors (few, recoverable), satisfaction.

## Usability testing
- Plan:
  - goals and questions
  - participants (5 to 8 per distinct user group)
  - tasks
  - metrics
  - moderator script
  - pilot session
- Tasks are realistic scenarios with a goal and a reason. They avoid the interface's own words (do not say "click Settings").
- Moderation: neutral, no helping, no leading. Ask about expectations before an action and about what happened after it.
- RITE (Rapid Iterative Testing and Evaluation, Medlock et al., Microsoft games): fix an issue as soon as it is clearly understood and continue testing on the new version.

### Think-aloud
Verified on NN/g (Nielsen, "Thinking Aloud: The #1 Usability Tool").
- Participants voice their thoughts while using the system. Nielsen calls it cheap, robust, flexible, convincing to stakeholders, and easy to learn. Its weaknesses: it is an unnatural situation, people filter what they say, and moderators can bias the session.
- Theory (Ericsson and Simon, Protocol Analysis, 1980/1993):
  - Level 1 verbalizes thoughts already in words.
  - Level 2 recodes non-verbal thoughts (images, spatial reasoning) into words.
  - Level 3 asks for explanations and reasons, and this changes the thinking itself.
  - Classic protocol keeps to Levels 1 and 2, with neutral "please keep talking" prompts.
- Boren and Ramey (2000) proposed a speech-communication approach: brief acknowledgment tokens ("mm-hm", "OK") keep talk natural without steering it.
- Concurrent think-aloud slows people down, so do not combine it with time-on-task measures. Retrospective think-aloud (watching the recording afterwards) preserves timing but loses detail and invites rationalization.
- Experts thinking aloud through a task is also a cognitive task analysis tool. See [07](07-learning-science.md).

### How many users
- Nielsen and Landauer (1993) model the share of problems found as 1 - (1 - p)^n. With an average per-user detection rate p of about 0.31, five users find about 85 percent of problems.
- Caveats: p varies widely by product and problem. The rule applies per distinct user group. Rare but severe problems need more users (Faulkner 2003 showed wide variance between samples of five). Several small iterative tests beat one large test.

### Metrics
- Task success: binary, or levels (success, success with difficulty, failure). Report completion rates with adjusted-Wald confidence intervals for small samples (Sauro and Lewis).
- Time on task: skewed, so report the geometric mean for small samples. Count successful attempts only, or report both.
- Errors and their severity.
- Single Ease Question (SEQ): one 7-point item after each task. The average is around 5.5 (Sauro).
- System Usability Scale (SUS). Verified on MeasuringU:
  - Created by John Brooke in 1986.
  - Ten items with five response options, alternating positive and negative wording.
  - Scoring: odd items score the response minus 1, even items score 5 minus the response. Sum the ten, multiply by 2.5, giving 0 to 100.
  - The mean across about 500 studies is 68. Above 80.3 is roughly an A (top 10 percent). Below 51 is an F (bottom 15 percent).
  - A SUS score is not a percentage. Convert to a percentile for stakeholders.
  - Items 4 and 10 form a learnability subscale, the other eight a usability subscale.
- UMUX-Lite: two items, correlates highly with SUS.
- NASA-TLX: six-dimension workload measure (mental, physical, temporal demand, performance, effort, frustration).
- NPS: popular but weak for usability decisions. Prefer task-level measures.

## Severity ratings (Nielsen)
- 0 not a problem, 1 cosmetic, 2 minor, 3 major, 4 catastrophe.
- Judge severity on three factors: frequency, impact, and persistence (whether users get past it once they have learned it).

## Heuristic evaluation (Nielsen and Molich 1990, Nielsen 1994)
The ten heuristics (verified on NN/g):
1. Visibility of system status.
2. Match between the system and the real world.
3. User control and freedom.
4. Consistency and standards.
5. Error prevention.
6. Recognition rather than recall.
7. Flexibility and efficiency of use.
8. Aesthetic and minimalist design.
9. Help users recognize, diagnose and recover from errors.
10. Help and documentation.

Procedure:
- 3 to 5 evaluators work independently, each making two passes (one to learn the flow, one to inspect elements).
- Findings are aggregated, then rated for severity.
- A single evaluator finds roughly a third of problems. Five find around three quarters.

Limits: false positives, and misses of domain-specific or task-flow problems. Use domain heuristics where they exist (for learning tools, games, AI systems).

## Cognitive walkthrough (Wharton, Rieman, Lewis and Polson 1994)
- Purpose: to judge learnability for first-time users by exploration. Analysts step through the correct action sequence for a task.
- At each action, ask four questions:
  1. Will the user try to achieve the right effect?
  2. Will the user notice that the correct action is available?
  3. Will the user associate the correct action with the effect they want?
  4. If the correct action is performed, will the user see that progress is being made?
- Spencer's streamlined version (2000) asks two questions, to fit fast-paced teams.

## GOMS and the Keystroke-Level Model (Card, Moran and Newell, The Psychology of Human-Computer Interaction, 1983)
- GOMS stands for Goals, Operators (elementary actions), Methods (operator sequences that achieve goals) and Selection rules (which method when). It predicts expert, error-free task time.
- KLM operators with standard times:
  - K keystroke, about 0.2 s for an average skilled typist (0.08 to 1.2 s range)
  - P point with a mouse, about 1.1 s
  - B mouse button press or release, about 0.1 s
  - H home the hands between devices, about 0.4 s
  - M mental preparation, about 1.35 s
  - R system response time
- Heuristic rules place M operators before actions that need a decision.
- Use KLM to compare designs before building them. Small differences per task become large across millions of repetitions.
- CogTool (CMU, Bonnie John) builds KLM models from storyboards.
- CPM-GOMS models parallel activity. In Project Ernestine it predicted, and a field trial confirmed, that a new telephone-operator workstation would be slower than the old one (Gray, John and Atwood 1993).

## Controlled online experiments (A/B tests)
Kohavi, Tang and Xu, Trustworthy Online Controlled Experiments, 2020.
- Define an Overall Evaluation Criterion (OEC) tied to long-term value, plus guardrail metrics that must not get worse (performance, errors, unsubscribe rates).
- Choose the randomization unit (user, session, class). Compute power and the minimum detectable effect before starting.
- Check sample-ratio mismatch: if the split is not the planned ratio, the experiment is broken.
- Run whole weeks to cover weekly cycles. Do not stop when the result first looks significant ("peeking"). Use fixed horizons or proper sequential methods.
- Expect novelty and primacy effects. Twyman's law says any figure that looks unusual is probably wrong, so check the data before celebrating.
- Use A/A tests to validate the pipeline. Watch for interference between units (shared classrooms, social networks).
- Ethics: experiments on people need respect for persons and minimal risk. The Facebook emotional contagion study (2014) is the standard cautionary case.

## Quantitative UX data
- Instrument events deliberately: name events, record properties and context.
- Common analyses: funnels, cohort retention, paths, segmentation.
- Google's HEART framework (Rodden, Hutchinson and Fu 2010): Happiness, Engagement, Adoption, Retention, Task success. Each is mapped through Goals, then Signals, then Metrics.
- Data skepticism:
  - provenance and definitions
  - sampling and survivorship bias
  - Simpson's paradox (a trend reverses when groups are combined)
  - correlation is not causation
  - seasonality
- Designers collaborate with data owners. The course frames the role as fluent partner rather than data scientist. Frame the question, ask for the right cut, visualize the finding, translate it into a design decision.

## Other evaluation forms
- Expert review: heuristic evaluation plus a guidelines checklist.
- Competitive and benchmark testing: the same tasks across products or versions.
- Field deployments and longitudinal studies (ubiquitous computing): systems used in the wild over weeks, with logs, interviews and diaries. They reveal adoption, abandonment and social fit that lab tests cannot.
- Accessibility evaluation: see [08](08-accessibility.md).

## Sources
Verified this session: NN/g ten heuristics page and thinking-aloud article, MeasuringU SUS article. From training: Nielsen, Usability Engineering (1993). Nielsen and Landauer 1993 (INTERCHI). Wharton et al. 1994. Card, Moran and Newell 1983. Gray, John and Atwood 1993. Sauro and Lewis, Quantifying the User Experience. Kohavi, Tang and Xu 2020. Rodden et al. 2010.
