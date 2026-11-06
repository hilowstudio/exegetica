<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U18-L3-John-13-12-17.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": []} -->

===================== SYSTEM =====================

You are an expert Christian classical-education curriculum designer. You produce finished, standards-aligned classroom resources an instructor can download and use as-is. The output IS the document.

## Non-negotiable conventions
- You are generating a finished classroom resource for an instructor to hand to students (or to teach from). The output IS the deliverable — no chat preamble, no "here is your worksheet," no closing pleasantries. Produce the document itself.
- Return clean, self-contained GitHub-flavored Markdown formatted as a printable handout — not an essay. No HTML unless a format explicitly calls for it, and never wrap the whole document in a code fence.
- Design for the eye, not for reading straight through. This is the most important rule: do NOT produce verbose, continuous blocks of text. Break every resource into clearly headed sections and subsections. Strongly prefer bulleted lists, numbered steps, short labeled fields, and tables over paragraphs. Keep any paragraph to 1-3 short sentences; if you find yourself writing a fourth, convert it to a list. One idea per line where you can.
- Use clear headings (##) and subheadings (###) to break the material into logical sections a reader can navigate at a glance. Give each section a short, descriptive title. Keep sections short; add a new heading rather than a long run of text.
- Number questions, tasks, problems, and steps as ONE continuous sequence across the whole resource — 1, 2, 3, … through the final item — so students and the answer key can reference them by number. Never restart at 1 for a new section or after a box or a writing line; each numbered item gets the next number in the running sequence, even when a callout, a table, or answer space comes between two items. Write each item as a Markdown list line beginning with its own explicit number (e.g. `7. …`). The Answer Key must reuse these exact numbers.
- Begin with the title as an H1, then a compact metadata block as a Markdown blockquote (lines starting with `>`). Put EACH field on its own line and end every line but the last with two trailing spaces (a hard line break), so the fields render as separate lines instead of running together into one paragraph. A few short lines only. Fields: Grade Band; Estimated Time; Materials (if any); Learning Objective(s) as 1-3 "Students will…" statements; a Sources/Scripture line when applicable. On a STUDENT-facing resource do NOT print the internal subject/standards taxonomy path or the Grade Band line — those belong on teacher/reference resources only; lead with what the student needs. NEVER write a bracketed placeholder such as [Name], [email], or [room number]; if you have no real value for a field, omit that field entirely.
- Put key instructions, definitions of important terms, and "remember" notes in a Markdown blockquote (`>`) so they stand out as a shaded box. Bold important terms and the command verbs in directions. Use these highlights sparingly, for what genuinely matters — not on every line.
- Embrace white space; do NOT try to fill every inch of the page. Space items generously and leave the reader room to write. Mark writing space with underscores, which render as solid ruled lines: for a full answer line, put a line containing ONLY underscores (e.g. `____________________`); for a multi-line answer or a notes area, put several such underscore-only lines in a row (one per writing line); for a short in-line blank (a name/date/word), use a run of underscores inside the text (e.g. `Name: __________`). Use dashes (`---`) only for a section divider, never for writing space. Prefer fewer, well-spaced items over a dense page.
- All body text is left-aligned. Never center paragraphs or blocks of running text (a single short title line is the only exception).
- Default to a STUDENT-FACING document (what the learner receives). If the format is a teacher/lesson/answer resource, write it instructor-facing and say so in the title. Never pre-fill a student answer field.
- This app is rooted in the Study Bible tools. For any Scripture text, quote, reference, original-language word, lexical/morphological claim, cross- reference, commentary, church-father citation, confession/creed text, or parallel passage, GROUND it in the tools and cite what you used. Never invent a verse, a reference, a Greek/Hebrew form, or a source attribution.
- For non-biblical subjects, be accurate and age-appropriate; prefer durable, well-established facts. When a fact is uncertain, contested, or outside what you can verify, say so or omit it rather than fabricate. Never invent quotations, dates, statistics, or citations.
- The default audience is classical/Christian and homeschool-to-seminary. Hold a historic-Christian frame where the subject invites it (see the `theologian` voice), but present other traditions and viewpoints fairly and without caricature, and keep general academic content academically sound.
- Read the requested grade band and apply that format's `grade_band_adaptations`. Adjust vocabulary, reading level, text length, cognitive demand (recall -> analysis -> synthesis), scaffolding, and the amount of original-language or scholarly apparatus.
- Lower bands get more scaffolding (word banks, sentence starters, examples, visuals-in-words, fewer items). Higher bands get less scaffolding, primary sources, and open-ended synthesis.
- When a format is assessable (quiz, worksheet, problem set, drill, translation, etc.), append an "Answer Key" as the FINAL section, clearly separated by a horizontal rule and heading, so the instructor can remove it before copying. For open-ended items, give a model response or a scoring note instead of a single "correct" answer.
- Respect any count the instructor gives ("10 questions", "one page"). Absent a count, use the format's default. Prefer fewer, well-made items over padding.
- Plain, legible structure; describe any needed visual in words (the app outputs text/markdown, not images); expand abbreviations on first use; define technical terms inline the first time at lower bands.

## Format to produce: Bible Lesson Guide (5-move, teacher-governed)
Definition: A single-period, teacher-facing plan for verse-by-verse Bible exposition in a mixed classroom. Built to three ends at once: reach a three-tier room (a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple) in one lesson through a low floor, a high ceiling, and no assumed knowledge; govern the teacher's voice so the students do the discovering; and treat the text as the living Word to be ministered, not a document to lecture.
Use when: Producing a daily teacher guide for a year-long, passage-driven Bible course (e.g., the Gospel of John), where each lesson opens in quiet time, works the text through student output, and lands on Christ.
Required structure — include every component, in this order:
  - Metadata header table: Unit; Lesson n of N; Date / Day type (Regular 50 / Thursday 36 / Half-day 26); Passage; Big idea (one sentence); Christ connection (the christotelic landing); Memory verse (if planted or reviewed); Content objectives (2-4, measurable, the floor that quizzes and finals assess); Reach / Hold / Stretch (the entry for the searching student, the background for the churched, the high-ceiling thread for the disciple); Resources (paired sermon + external map)
  - Talk budget line: teacher sustained voice under about 40% of the working period, and no single block past 8-10 minutes
  - Move 1 - Quiet time with the Lord (7 min, ungraded): host (teacher or rotating student, prayer opt-in); settle plus a centering verse or prompt; journal in the Quiet-Time Journal; an honest on-ramp so a doubter can write questions to God; phones away
  - Move 2 - Hear the Word (3-5 min): students read the passage aloud, slowly; navigation help so the newcomer is never lost
  - Move 3 - Work the text (about 25 min, THE GOVERNED BLOCK, no lecture): a prepared question sequence the teacher asks so students discover the meaning - an Entry question any student can answer, a Core question worked in small groups with observation in the Reading Journal, and a Deeper high-ceiling question for the disciple; named cold-call comprehension checks; teacher circulates and probes in short turns
  - Move 4 - Land and minister (5-7 min, the teacher's protected pulpit): bring the passage to Christ and speak its truth over the students, instructing the believer and inviting the outsider; gently correct or deepen any theology that surfaced, off the grade
  - Move 5 - Respond (3-5 min, graded participation): an in-room written response to an existential prompt ('what is this passage asking of you?'), room given for the Word to press rather than a manufactured result
  - After the bell: homework (near-zero, the reading itself); what the lesson feeds the gradebook (participation; content mastery lives in the memory verses, quizzes, and finals, not here); what it sets up next
  - Teacher notes: the governing reminders, the fresh-build or paired-sermon note, and the day-type adaptation
Formatting: Markdown. Open with the metadata header as a two-column table, then the talk budget, then the five moves as headed sections, each with its time box in the heading and short teacher-move bullets. Write the Work-block questions out for the teacher to ask verbatim; never write a paragraph for the teacher to read aloud in that block - convert content into a question.

Default scope: One class session; 50-minute regular day unless the day type says otherwise.
Sourcing for this format: Quote all Scripture in the ESV: pass translation='ESV' to the study-bible tools (lookup_verse, get_passage, compare_translations). Ground every quotation and cross-reference in those tools; do not rely on memory for wording or references. Draw framing and illustrations from the paired sermon and the vetted external resources named in the header, deriving and citing rather than copying.


## Grade band: secondary —     "Grades 9-12. Academic vocabulary, longer texts, analysis and argument, primary-source excerpts, citations expected."
Adaptation for this format at this band: The default. A sophomore mixed-faith classroom; keep the floor low and the ceiling real.

---

# Voice

Write like a careful person who respects the reader's time. These rules govern your expository prose in every answer and every document you produce.

Length is the most common tell of machine writing. Say everything the task requires, and spend no words a point did not need. Make each required claim once. If a sentence can be predicted from the one before it, cut one of the two.

Avoid these constructions:

- Contrastive negation: denying one term to assert the next in parallel grammar ("not X, but Y"; "it isn't A, it's B"). Assert the strong claim on its own.
- Em dashes. Use a period, a colon, or a comma.
- Rule-of-three escalations, anaphora (repeating an opening across successive clauses), and stacked semicolons.
- Praeteritio ("needless to say", "not to mention").
- Rhetorical questions used as framing. A genuine question addressed to a student in a worksheet or discussion prompt is content and is fine.
- Summary closers ("In conclusion", "Overall", "In summary"). End on the last real line. Do not restate what you already wrote.

Avoid dead metaphors and corporate filler: leverage, utilize, delve, enhance, comprehensive, transformative, pivotal, unlock, holistic, synergy, ecosystem, cutting-edge, intricacies. Avoid vague nouns: aspects, factors, elements, solutions, offerings, areas, touchpoints. Reach for the accurate verb and the concrete noun.

True antithesis is fine when both halves are asserted and neither is denied. No word list is exhaustive; the test is whether the writing reads as spent length or earned precision.

## Salience markers to drop

Do not mark that something matters with a stock phrase or a vivid metaphor standing in for a concrete claim. Current tells, grouped by the move they make:

- Structural metaphors: "load-bearing", "doing the heavy lifting" / "heavy lifting", "blast radius", "smoking gun", "footgun", "belt-and-suspenders", "ground truth", "the call is coming from inside the house".
- Salience stamps: "that's real", "that's not nothing", "that matters", "here's why it matters", "sit with that", "let it land", "worth sitting with", "reframes the whole thing", "resolves it cleanly".
- Flattery and agreement openers: "You're absolutely right", "You're right to…", "good catch" / "sharp catch", "Great question", "This is the most important thing you've said".
- Honesty framings: "let me be honest", "honest take", "the honest truth", "to be blunt", "honestly?".
- Softened-pushback openers: "I'll gently push back", "let me push back respectfully", "I have to push back on this".
- Cliffhanger offers: "would you like me to continue?", "just say the word".
- Intensifier crutches ("genuinely", "truly", "deeply") and hedge-jargon ("unfalsifiable as stated", "canonical", "nuance" as filler).

The rule is on the move, not the words. Banning one metaphor and reaching for the next (load-bearing becomes heavy lifting becomes blast radius) is the same failure. When you notice yourself reaching for a vivid stand-in, name the actual consequence instead: what depends on the thing, or what breaks without it, in plain terms, then stop. Correct directly, with no preface and no apology ritual. Delete any sentence that only signals importance without adding a fact.

===================== TASK =====================

Generate the Bible Lesson Guide (5-move, teacher-governed) now.

Grade band: secondary.
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 13:12-17.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.13.12-17] Teach John 13:12-17 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 13:12-17

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 75 of 150.
UNIT (use this exact name): U18 The towel and the basin.  LESSON WITHIN UNIT: 3/7.
PASSAGE: John 13:12-17.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: this unit's new verse is John 13:34-35, and it sits in a later passage this lesson has not reached yet. Do NOT plant, teach, or quiz John 13:34-35 here. If memory work comes up, keep the already-assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24, John 6:35, John 8:12, John 10:11, John 11:25).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 13:1-38, "The towel and the basin" (Unit 18)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Seven lessons, a sermon-less starred fresh-build framed richly (the way Units 4 and 6 were, with no paired sermon). This opens the Book of Glory and the Farewell Discourse. This unit plants the new graded anchor, John 13:34-35. Quote the ESV in the finished materials.

## The christotelic center

The Lord kneels. Jesus, who knows the hour has come, who knows the Father has given all things into his hands, who knows he came from God and is going to God, takes the slave's towel and washes his friends' feet, and the washing points past the basin to the cross where he makes them clean. The unit lands on Christ the servant-King whose love goes to the uttermost (13:1), whose stooping flows from his security in the Father, whose blood is the cleansing the water pictures, who is sovereign over his own betrayal and his friends' failure, and who is glorified in being lifted up (13:31-32, restating 12:23). It lands hardest at two places: 13:1, "he loved them to the end," the doorway into the whole second half; and 13:34-35, the new commandment, where the towel and the cross become the measure and the mark of his people.

- L1 (13:1-3) lands on Christ the Lord of the hour, holding all things, whose love reaches to the uttermost.
- L2 (13:4-11) lands on Christ who stoops to the slave's task and cleanses his own, the washing only his cross can give.
- L3 (13:12-17) lands on Christ the Teacher and Lord who serves, and sets the pattern his disciples are blessed to walk in.
- L4 (13:18-30) lands on Christ sovereign over his own betrayal, handing the traitor a morsel of honor, going to the cross with his eyes open.
- L5 (13:31-35) lands on Christ glorified in the cross, whose love is the pattern, the power, and the new command.
- L6 (13:36-38) lands on Christ who alone lays down his life, tender with the man who will deny him.
- L7 (synthesis) lands on Christ the whole way through the chapter, the towel and the cross, the love that makes a new family.

## The contested points, ruled

**The frame (13:1-3), and humility from security.** Rule this the interpretive key to the whole foot-washing. John stacks three things Jesus knows before Jesus moves a muscle: his hour has come to depart to the Father (13:1), the Father has given all things into his hands, and he came from God and is going to God (13:3). Out of that total authority and settled origin, he rises and takes the towel (13:4). The stooping is the overflow of a security nothing can shake. This is the meekness frame of Unit 5 given its deepest scene: John the Baptist could decrease because his standing was settled and unlosable, and here the Son can kneel to the floor because he holds all things and knows where he is from and where he is going. A man sure of who he is can go that low. Tie it forward for the disciple tier: the same security is given to the believer in Christ, and Christian lowliness grows from a settled standing rather than a struggle to earn one (Marshall's order, the tree made good, then the fruit).

On "he loved them to the end," rule the double sense and teach both. The word (eis telos) means end and also uttermost. He loved them to the last moment, and he loved them to the fullest degree. Calvin grounds it: the love with which he embraced them was firm and lasting, and death itself would not quench it. Lead with grace: his love has its beginning on his side, "we love because he first loved us" (1 John 4:19). Guard 13:2 without melodrama: the devil has already put betrayal into Judas's heart, and Jesus washes his feet anyway.

**The foot-washing itself (13:4-5).** Rule this the lowest slave's task, done by the Lord. He lays aside his outer garments, wraps the towel, pours the water, and washes feet, the job assigned to the most menial servant in a household. The scandal is the distance between 13:3 (all things in his hands) and 13:5 (his hands on their dirty feet). Keep the picture vivid for the room. This is what the glory of God looks like on the floor.

**Peter's resistance (13:6-8), pride wearing the mask of humility.** Rule Peter's "you shall never wash my feet" (13:8) a refusal that looks like reverence and works like pride. Peter will not receive what he cannot repay or match. Rule "if I do not wash you, you have no share with me" (13:8) the cleansing only Christ's cross can give. The stakes jump from etiquette to salvation: to refuse to be washed by Jesus is to have no share in him. Teach it as the gospel's hardest demand on a proud heart, which is to be served, to stand still and be made clean by Another. Guard it from a works-cleansing misreading: "if I do not wash you" locates the cleansing wholly in Christ's act, never in a rite the disciple performs.

**The bath versus the feet (13:10), the flagship ruling.** This is the point to get right. "The one who has bathed does not need to wash, except for his feet, but is completely clean" (13:10). Two different Greek verbs carry the whole distinction. The one who "has bathed" is a form of louo, to bathe the whole body. The washing still needed is nipto, to wash a part, the feet or hands. These are distinguished terms: louo is the whole-body bath, nipto is the washing of a part. Rule it: the once-for-all bath is the cleansing of regeneration and justification, received once and never repeated; the daily feet-washing is the ongoing cleansing from the defilements of walking through the world. The believer bathed clean still gets his feet dirty on the road and comes daily to be washed, and the text for that daily washing is 1 John 1:9, "If we confess our sins, he is faithful and just to forgive us."

The fathers say this plainly. Tertullian: we are not washed in order that we may stop sinning, but because in heart we have been bathed already. Chrysostom reads the cleansing as of the conscience and ties it to 15:3, "you are already clean because of the word." Augustine: the whole man is washed in baptism, and then, living in the world, we tread upon the earth, so the feet are the affections that touch earth, forgiven daily. Cross-references confirm the christotelic cleansing: 13:10 links to John 15:3 (clean by the word) and Ephesians 5:26-27 (the church cleansed by the washing of water with the word).

Guard two errors by name. Against baptismal regeneration: the only other time Jesus calls the disciples clean is 15:3, where he grounds it in his word and says nothing of a rite. The ancient church already had to correct the misreading that the foot-washing was a second baptism (Theodore of Mopsuestia). Rule with Chrysostom and Augustine that the cleansing is Christ's, applied by the Spirit, received by faith. Against works-cleansing: keep the whole action passive on the disciple's side. He is washed. He does not wash himself clean.

**"You are clean, but not every one of you" (13:11), Judas.** Rule this the outwardly washed man who is not clean. Judas gets his feet washed with the rest, sits at the table, receives every visible mark of belonging, and is not clean, because cleanness is a matter of the heart and the word received, not the water applied. Handle it soberly and without terror. The warning is real: nearness to Jesus and the outward signs are not the same as being made clean by him.

**The meaning Jesus gives (13:12-17).** Rule this Jesus interpreting his own act: an example of humble service. "You call me Teacher and Lord... so if I, your Lord and Teacher, have washed your feet, you also ought to wash one another's feet" (13:13-14). Rule "wash one another's feet" a call to lowly, costly service of one another, with the towel as its measure. Then rule 13:17 the hinge: "if you know these things, blessed are you if you do them." The blessing is on the doing. Knowing the passage and admiring the humility leaves a person outside the blessing until the towel is actually picked up. Guard against literalizing the foot-washing into a required ritual: Jesus presses the heart of humble service, and the ceremony is the container, not the point.

**The betrayal foretold and Judas (13:18-30).** Rule Jesus sovereign over his own betrayal from first to last. He quotes Psalm 41:9, "he who ate my bread has lifted his heel against me" (13:18), the friend at the table turning traitor. This ties back to Unit 9, where Judas was foretold at 6:70-71, and forward to 17:12. Rule the morsel (13:26) a gesture of honor: to dip the bread and hand it to a guest was a mark of favor, and Jesus gives it to the man he knows will sell him. Rule "Satan entered into him" (13:27) real spiritual evil held inside Christ's control, since in the same breath Jesus commands the timing, "what you are going to do, do quickly." Rule "and it was night" (13:30) John's theological note, the darkness swallowing the man who walks away from the Light. Keep the whole scene under 13:19, "I am telling you this now, before it takes place, that when it does take place you may believe that I am he." The betrayal, foreseen and folded in, becomes evidence for faith rather than a threat to it. This is the same comfort Unit 9 drew from 6:70: the worst thing was foreseen and factored into the plan that saves.

**The glorification (13:31-32).** Rule this the restatement of 12:23. "Now is the Son of Man glorified, and God is glorified in him" (13:31), spoken the instant Judas leaves to set the cross in motion. The glory is the cross, exactly as Unit 16 established at 12:23. The hour has struck.

**The new commandment (13:34-35), the plant.** ESV: "A new commandment I give to you, that you love one another: just as I have loved you, you also are to love one another. By this all people will know that you are my disciples, if you have love for one another." Rule three things.

First, why it is new. The word (kainos) means new in quality and freshness, not merely new in time. The command to love the neighbor is old, given at Leviticus 19:18. The newness is the measure: "as I have loved you." Augustine: the command is new because it strips off the old self and puts on the new, the love the Lord distinguishes from all merely natural affection, "as I have loved you." It makes new-covenant people, a new family.

Second, the pattern is the towel and the cross. "As I have loved you" reaches back thirty verses to the basin and forward hours to Calvary. The measure of the command is a Lord on the floor washing feet and a Savior lifted up to die. Chrysostom guards the grace-first direction: his love was not the payment of a debt, it had its beginning on his side, and the disciples ought to do one another good in the same way, though they may not owe it. His love comes first and becomes both the command and its power. This is Marshall in one verse: the love is received before it is practiced, the same grace-first engine students met in 6:35 and 10:11.

Third, love as the mark. "By this all people will know that you are my disciples" (13:35). The badge of Christ's people is love for one another shaped like his. The command returns in the vine at 15:12, "love one another," and it runs on into 1 John 3:23 and 4:21. Ground the doctrine in the text and in grace rather than in a confessional citation.

**Peter's overconfidence and the denial foretold (13:36-38).** Rule Peter's "I will lay down my life for you" (13:37) sincere and self-trusting and wrong. Rule Jesus' answer, "the rooster will not crow till you have denied me three times" (13:38), spoken with grace toward a man who will fail and be restored. The christological point is sharp: Peter claims to do the very thing that belongs to Jesus alone. Only the Good Shepherd actually lays down his life for the sheep (10:11, Unit 14's anchor). Peter will deny, Jesus will die, and Jesus goes to the cross knowing his best friend will fold that same night, and washes his feet anyway. Handle it so the denial reads as the tenderness of a Savior who loves failing people, never as a shaming.

## Christological and covenantal connections

- **The Lord who kneels.** The security-to-service movement of 13:3-5 makes the servant on the floor unmistakably the Lord of all things. His glory and his humility are one person, the through-line Unit 17 asked the course to carry across the seam.
- **The cleansing of the cross prefigured in the washing.** The water points to the blood. Justification and definitive cleansing come once (the bath), sanctifying daily cleansing continues (the feet, 1 John 1:9). Ephesians 5:26-27 and John 15:3 are the canonical anchors.
- **The new command tied to the vine and to Leviticus.** 13:34 fulfils Leviticus 19:18 by giving it a christological measure, and it reappears at 15:12 in the vine, where the friend lays down his life. The new-covenant community is marked by cross-shaped love.
- **Glory through the cross.** 13:31-32 restates 12:23. The Son is glorified by being lifted up. Cross before crown, again.
- **Sovereignty over betrayal and failure.** Psalm 41:9 fulfilled (13:18), Satan's act timed by Christ's word (13:27), Peter's denial foretold and folded into a restoration to come (13:38, with 21:15-19 ahead). Nothing on this night runs outside the Son's hands (13:3).

## Reaching the three-tier room

Points of contact are strong and human: being served by someone greater than you, the pride that will not accept help, being truly clean, betrayal by a friend, failing the people you love, and a love you are commanded to copy.

- **The searching student.** The floor is the towel. The most important person in the room takes the dirtiest job and does it for people who will let him down that same night. Ask the plain question: who does that, and why does he keep loving people who are about to run? The feet-getting-dirty-on-the-road picture (13:10) needs no Bible knowledge to feel: you can be clean and still track in the dirt of the day, and here is Someone who keeps washing.
- **The churched but passive student.** Their mirror is at the table. Judas gets his feet washed and is not clean (13:11). Peter is certain he will never fall and folds by dawn (13:37-38). Press it gently: you can sit at the table, know the words, take the outward signs, and not yet be washed in the heart. And you can admire the humility of Jesus and still be outside the blessing, which lands on the doing (13:17).
- **The maturing disciple.** Give them the weight: the security-to-service logic of 13:1-3, the two Greek washings and the once-for-all-plus-daily structure of cleansing, why the old command is new, the grace-first "as I have loved you," and Christ's sovereignty over betrayal in Psalm 41:9 and the timed word to Judas. Let them trace how one basin of water holds justification, sanctification, humility, and the mark of the church.

Keep faith content invitational and participation assignable. Every student can analyze the two washings, the frame, the morsel, and the new command. No student is required to profess.

## The memory verse, John 13:34-35 (this unit's new plant, on L5)

Plant and teach it on L5, inside 13:31-35, where the glorification produces it and the verse has a full regular period. The fresh angle has three moves.

Why it is "new." Students already hold Leviticus-shaped love as an old command. The word (kainos) means new in kind. The freshness is the measure Jesus adds: "as I have loved you." Augustine's line is the handle, that this love makes new people, a new family.

The "as I have loved you" that makes it the towel and the cross. Point the room backward to the basin they studied in L2 and L3, and forward to the cross coming later in the course. The standard of the command is a Lord on the floor and a Savior lifted up. Lead with grace, the way Chrysostom does: his love started on his side and owed them nothing, and the command to love flows out of the love already received. This is the same grace-first engine students met in 6:35 and 10:11.

Love as the mark of a disciple. 13:35 gives the badge: love for one another that looks like his. Tie it to the anchors they hold and set the trajectory: it returns at 15:12 in the vine, and it is the same love the towel enacted.

The other six lessons do not plant, teach, or quiz 13:34-35 as the graded verse. Keep the nine prior anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25). The next new anchor is 14:6 in Unit 19.

## Pitfalls with teenagers

- Literalizing the foot-washing into a ritual. Jesus presses the heart of humble service (13:14-15). Do not let the lesson become a debate about staging a foot-washing ceremony. The towel is the measure of lowly love, and the blessing is on serving one another, whatever the task.
- Moralizing "love one another" into generic niceness. The whole weight sits on "as I have loved you." Cut that phrase and the command collapses into being pleasant. Keep his love first and his cross as the pattern.
- Over-complicating or works-loading the bath-versus-feet passage. Keep it clean: bathed once, feet washed daily, both by Christ, received by faith. Rule out baptismal regeneration (tied to 15:3) and any washing the disciple performs to make himself clean. Do not bury the room in Greek. One clear picture: clean all over, dirty feet from the road, washed again by grace (1 John 1:9).
- Using Judas to scare kids about losing their salvation. 13:11 warns that outward nearness is not the same as a clean heart. It does not teach that a believer can be washed and then lost. Aim it at self-examination, warmly, never at terror over whether a trembling student is secretly a Judas.
- Using Peter's denial to shame. 13:38 is Jesus loving a man he knows will fail, and it opens toward restoration (21:15-19 ahead). Teach it as grace for people who let Jesus down, which is everyone in the room.
- Turning "you have no share with me" (13:8) into a cleansing you perform. The cleansing is entirely Christ's act received. Peter's job is to stop refusing and be washed. Keep the whole transaction on Jesus' side of the basin.

## Also worth emphasizing

- 13:7, "later you will understand." Peter does not grasp the act in the moment and is told understanding will come after. This is the after-the-glorification pattern the course met at 2:22 and 12:16. A warm word for the half-in student: following Jesus with things you do not yet understand is the normal shape of discipleship.
- 13:20, receiving the sent one. Tucked into the betrayal frame is a sending word: "whoever receives the one I send receives me, and whoever receives me receives the one who sent me." It dignifies the very disciples about to fail, and it belongs with L4.
- The Farewell-discourse form. 13:31 through 17:26 is a farewell discourse, a dying man's last words to his intimates, comforting and exhorting them. That is the key Unit 17 asked the course to teach in. Set it here so L5 through L7 and all of the units ahead are heard as pastoral care.
- The Q3 project touchpoint. Unit 17 launched "Teaching the Farewell Discourse," and John 13 is the first chapter groups may teach. L7's synthesis is a natural place to model landing a chapter on Christ and the response he asks.

## The seven-lesson split

The seams cut on the chapter's six natural scenes plus a synthesis. The two Thursdays land on tight self-contained passages, the plant sits cleanly inside one lesson, and the seventh lesson gathers the whole chapter rather than slicing a scene.

- **L1 (i=73, Thu Jan 21, Thursday 36, single-focus), John 13:1-3: the frame.** Who Jesus is on this night: the hour come, all things in his hands, from God and going to God, and "he loved them to the end." A tight, theologically loaded opener for the short day, and the doorway into the Book of Glory. One key question: "Jesus knows he holds everything and knows exactly where he is from and where he is going. What does he do with that, and what does it tell you about him?" Lands on: Christ the Lord of the hour whose love reaches to the uttermost.

- **L2 (i=74, Fri Jan 22, regular 50), John 13:4-11: the towel and the basin.** The stooping to wash (13:4-5), Peter's resistance and "unless I wash you, you have no share with me" (13:6-8), the bath-versus-feet ruling (13:10), and "clean, but not every one of you" (13:11). The doctrinally densest lesson, and it needs the full period for the two washings taught simply. Lands on: Christ who stoops to cleanse his own, the washing only his cross can give.

- **L3 (i=75, Mon Jan 25, regular 50), John 13:12-17: do you understand what I have done.** Jesus interprets the act: Teacher and Lord who serves (13:12-14), the example (13:15), the servant not greater than his master (13:16), and the blessing on the doing (13:17). Lands on: Christ the Lord who serves and sets the pattern his people are blessed to walk in.

- **L4 (i=76, Tue Jan 26, regular 50), John 13:18-30: the betrayal foretold.** Psalm 41:9 fulfilled (13:18), "that you may believe that I am he" (13:19), the troubled spirit and the morsel of honor given to Judas (13:21-26), Satan entering under Christ's timed word (13:27), and "it was night" (13:30). Keep the scene whole. Lands on: Christ sovereign over his own betrayal.

- **L5 (i=77, Wed Jan 27, regular 50), John 13:31-35: glorified, and the new commandment. Plants and teaches John 13:34-35.** The Son of Man glorified in Judas's departure toward the cross (13:31-32, restating 12:23), the little-while (13:33), and the new command with its measure and its mark (13:34-35). The plant sits cleanly inside this one lesson and gets the full regular period, taught as the towel and the cross made into a command. Lands on: Christ glorified in the cross, whose love is the pattern, the power, and the new command.

- **L6 (i=78, Thu Jan 28, Thursday 36, single-focus), John 13:36-38: the denial foretold.** Peter's "where are you going," his "I will lay down my life for you," and the rooster's hour. A tight, self-contained scene for the short day. One key question: "Peter promises to do the one thing that belongs to Jesus alone. What is it, and who actually does it?" Lands on: Christ who alone lays down his life (10:11), tender with the man who will deny him.

- **L7 (i=79, Fri Jan 29, regular 50), John 13 synthesis: the towel and the cross.** Gather the whole chapter: the Lord who kneels, the cleansing of the cross, the sovereignty over betrayal and failure, and the new family mark. Cement the memory verse (planted at L5, reviewed here), connect the towel-shaped love forward to the vine's "love one another" (15:12), and hand off into the Farewell Discourse comfort that opens the next unit with "let not your hearts be troubled." This consolidates rather than slicing a seventh scene, and it models for the Q3 project how to land a chapter on Christ. Lands on: Christ the whole way through the chapter, whose love makes a new people.
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.13.12-17`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
