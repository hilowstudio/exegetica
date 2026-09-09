<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U10-L1-John-7-1-13.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["10 - Lost Brothers (John 7-1-13).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 7:1-13.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.7.1-13] Teach John 7:1-13 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 7:1-13

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 42 of 150.
UNIT (use this exact name): U10 Rivers of living water.  LESSON WITHIN UNIT: 1/5.
PASSAGE: John 7:1-13.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24, John 6:35); the next new one comes in John 8:12 (Unit 12).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 7:1-52, "Rivers of living water" (Unit 10)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Five lessons. L1 builds on sermon 10 ("Lost Brothers," 7:1-13). L2 and L3 build on sermon 11 ("Can This Be the Christ?," 7:14-36). L4 and L5 build on sermon 12 ("Rivers of Living Water," 7:37-52). This unit plants no new graded verse. Quote the ESV in the finished materials.

## The christotelic center

At the feast that remembered God giving Israel water from the rock in the wilderness, Jesus stands up on the last day, when the water ceremony has fallen silent, and cries that he himself is the water: "If anyone thirsts, let him come to me and drink" (7:37). The unit lands on Christ as the living water, the Spirit-giver, the true source every thirsty heart was made for, and John tells us plainly what the water is: the Holy Spirit, poured out once Jesus is glorified (7:39). Unit 6 opened the living-water thread at the well (4:10-14) and left it half-drawn. John 7 names it: the living water is the Spirit, and the fountain is Christ crucified and raised.

- L1 (7:1-13) lands on Christ who moves on the Father's clock toward his hour, rejected by his own brothers, going his own way to the feast.
- L2 (7:14-24) lands on Christ the Sent One whose teaching is the Father's own.
- L3 (7:25-36) lands on Christ who comes from the Father, unseizable until his hour, returning to the One who sent him.
- L4 (7:37-44) lands on Christ the living water, from whom the Spirit flows to everyone who believes.
- L5 (7:45-52) lands on Christ whose word disarms the men sent to arrest him.

## The contested points, ruled

**The brothers' unbelief and "show yourself to the world" (7:3-5).** Rule it real unbelief, and rule the taunt a temptation to self-display. John states it flatly: "for not even his brothers believed in him" (7:5). They tell him to go to Judea and show himself to the world (7:4), a goad to prove himself on demand and in public. Teach two things sermon 10 presses. First, this is evidence for the sovereign grace of chapter 6: if thirty years in his own home did not produce faith in his brothers, then "no one can come to me unless the Father draws him" (6:44) is confirmed in his own family. Second, the brothers come to faith after the resurrection (James leads the Jerusalem church, Acts 1:14; James 1:1), so their present unbelief is a door grace later walks through. Do not shame families with this. It is comfort for the student whose household does not believe.

**"My time has not yet come" (7:6-8).** Rule "time" his appointed hour of the cross, not merely a travel delay. Jesus will not let his brothers move his timeline up even one meal. He goes to the feast, but at the Father's word and in his own way (7:10). The refusal is obedience to a fixed hour, and it is not fear, since he walks into the temple and teaches openly days later (7:14). This is the same hour that keeps his enemies' hands off him twice in this chapter (7:30, 44) and reaches its center at 12:23 and 17:1. Teach it as the Son living entirely on the Father's timing, the Father-first frame Unit 8 planted on Jesus' own lips (5:19, 30).

**The Feast of Booths and the water ceremony (essential for 7:37-39).** Rule the ceremony the interpretive key John hands us, and teach it. Each day of the feast a priest carried water from the pool of Siloam and poured it out at the altar while the people remembered God's water in the wilderness and prayed for rain, singing Isaiah 12:3, "with joy you will draw water from the wells of salvation." Sermon 12 adds the detail that carries the sermon: on the eighth and greatest day the ceremony stopped, no pitcher, no pouring, and the people's cry turned to longing for the promised Messiah. Into that silence Jesus stands and cries that he is the water. The feast also lit great lamps in the temple court, which is why Jesus says "I am the light of the world" at this same feast in 8:12 (next unit). Give the whole room the plain picture (the feast celebrated God's water in the desert, and the true water was standing in the temple) and give the disciple tier Siloam, Isaiah 12:3, and Zechariah 14:8.

**"My teaching is not mine" and the test at 7:17.** Rule 7:16 a claim that his doctrine is the Father's own, and rule 7:17 a real test with the order reversed from what we expect. Jesus says the teaching comes "from him who sent me" (7:16). Augustine catches it: "My teaching is not mine" holds together because Christ is himself the Word of the Father, so the doctrine is his (he is it) and not his (it is the Father's). The test in 7:17 is the load-bearing verse: "If anyone's will is to do God's will, he will know whether the teaching is from God." The will to obey comes first, and the knowing follows. Chrysostom rules it: clear out the malice and envy that darken judgment, and nothing hinders you from recognizing the words as God's. Sermon 11 gives the mark: the teaching that comes from the Father draws you to the Son (John already made belief in the Sent One "the work of God," 6:29). Teach the test as grace and warning together. A proud heart cannot recognize Christ's teaching because the will is bent, not because the evidence is missing, and the Spirit is the one who bends the will to obey.

**The Moses, circumcision, and Sabbath argument (7:19-24), and "judge with right judgment."** Rule it a lesser-to-greater argument from their own law, and rule 7:24 the unit's verdict on how the crowd is failing. Jesus reaches back to the Bethesda healing (Unit 8, John 5): they circumcise a boy on the Sabbath to keep Moses' law, so why the rage when he made a whole man well on the Sabbath (7:23)? If cutting one member is lawful on the Sabbath, healing the whole man is more lawful. Then the ruling: "Do not judge by appearances, but judge with right judgment" (7:24). This is the same fault Unit 8 exposed in the careful Bible readers who missed the Lord of the Book (5:39). They read the surface (a Sabbath rule broken) and miss the substance (the Father's work of healing in front of them). Teach it as the danger of a verdict reached on appearances, the exact mistake the crowd then repeats about his origin.

**The confusion about his origin (7:27 and 7:41-42).** Rule both a true fact wielded to reach a false verdict. In 7:27 the Jerusalemites say "we know where this man comes from," leaning on a folk idea that the Messiah would appear from nowhere. In 7:41-42 others say the Christ must come from Bethlehem and David's line (Micah 5:2), so a Galilean cannot be he. John works irony with both hands. They are right that Messiah comes from Bethlehem and David (Jesus does, Luke 2:4-7) and ignorant of the fact, so their correct doctrine indicts them because they never checked. And they are wrong that they know where Jesus is really from, because his true origin is the Father (7:28-29). Jesus answers by moving the question up: "You know me, and you know where I come from. But I have not come of my own accord. He who sent me is true, and him you do not know" (7:28-29). Teach the irony to the disciple tier. The men most sure they have Jesus placed have him most wrong.

**"You will seek me and you will not find me" (7:33-36).** Rule it his return to the Father through death and ascension, misheard by the crowd as travel. Jesus says "I am going to him who sent me" (7:33), and they guess he means the dispersion among the Greeks (7:35). Sermon 11 reads it straight: he is returning to the right hand of the Father, a saying they will only understand after the resurrection (as the disciples do, 2:22; 12:16). For the searching student, the warning inside it is real: there is a time to seek him and find him, and a settled refusal can harden past the door. Hold the warning gently, and lead with the open invitation of 7:37.

**The big ruling: "if anyone thirsts, let him come to me and drink" (7:37-38), with the punctuation and the source.** Rule the water the Holy Spirit, on John's own authority, and rule Christ the source you drink from.

- The substance is settled by John: "Now this he said about the Spirit, whom those who believed in him were to receive, for as yet the Spirit had not been given, because Jesus was not yet glorified" (7:39). This is John glossing his own Gospel, the same move that let Unit 6 rule 4:14 the Spirit. The living water is the Spirit, and the eternal life the Spirit conveys. Do not let it drift into a vague feelings-and-experience thing (see the pitfalls). The fathers are unanimous: Irenaeus, Cyril of Jerusalem, and Ambrose all read the living water as the Spirit.
- The "Scripture" is a composite, not one proof-text. No single Old Testament verse reads verbatim as John quotes it. It gathers the prophetic living-water hope: Isaiah 55:1 behind "if anyone thirsts," Isaiah 44:3 (I will pour water on the thirsty and my Spirit on your offspring), Isaiah 12:3 (sung at the ceremony), Zechariah 14:8 (living waters from Jerusalem), and the temple-river of Ezekiel 47. Give the room the concept (the prophets promised a day when God would pour out water and Spirit), and give the disciple tier the texts.
- The punctuation and source. The Greek carried no punctuation, and the phrase turns on one word that means "belly" or "the inmost person, the heart." Two readings result. Read it "out of the believer's heart" (as the ESV does, "out of his heart"), and the believer who has drunk becomes a channel the Spirit flows through. Read it "out of his [Christ's] heart," and the water flows from Christ. The ruling: the ultimate source is Christ on either reading, because 7:37 already fixed it ("come to me and drink"). Christ is the fountain, the believer is the streambed, and the streambed only runs because it was filled at the fountain. Teach the ESV rendering the pipeline supplies (the believer overflows with the Spirit), and keep the source clear (you overflow only because you first came to Christ and drank). Give the disciple tier one sentence on the debate and no more.
- The grace-first weight, which is the sermon's whole burden. Sermon 12 turns 7:37 on the two ways people refuse the water: the sinner drinking dirty water (chasing sin to fill the thirst) and the self-righteous person who will not come back to the fountain until he has cleaned himself up first. Both are told the same thing: come and drink, by faith alone, daily, with no toll to pay at the well. This is Marshall's order. Holiness (the Spirit's rivers) is received in union with Christ before it is practiced, and the believer who thinks he must produce fruit before returning to Christ has reversed the gospel. The confessions cite 7:38-39 for Christian liberty, freedom from the dominion of sin (Westminster 20.1; 1689 21.1). The Spirit who flows from Christ is that liberty. Land L4 here: come and drink, and keep coming.

**Nicodemus's return and the sneer "no prophet arises from Galilee" (7:45-52).** Rule the officers' report honest awe, rule Nicodemus a man edging out of the dark, and rule the sneer a self-inflicted blindness. The officers sent to arrest Jesus come back empty: "No one ever spoke like this man!" (7:46). Sermon 12 reads it as the word itself disarming them. The leaders answer with contempt for the crowd (7:49) and for Nicodemus. Nicodemus, "who had gone to him before" (7:50, the man of Unit 4, John 3), asks only that the law give Jesus a hearing (7:51). Rule him neither a coward nor a finished convert. Unit 4 set his arc as bookends (night visit in chapter 3, careful defense here, costly public burial in 19:39), a man moving out of the dark over years. Do not overclaim his conversion, and do not despise his caution. The sneer "no prophet arises from Galilee" (7:52) is the crowd's own error from 7:24 hardened into policy, a verdict on appearances that never checked the facts (Jonah was a Galilean, 2 Kings 14:25; Isaiah 9:1-2 promised light from Galilee). Their contempt for Galilee blinds them to the Bethlehem-born Christ in the temple.

## Christological and covenantal connections

**Christ the true water at the feast of God's wilderness water.** Tabernacles remembered forty years of God providing water in the desert, and its ceremony reenacted it. The deepest layer is the rock that gave water at Meribah (Exodus 17:6; Numbers 20:11), which Paul reads christologically: "they drank from the spiritual Rock that followed them, and the Rock was Christ" (1 Corinthians 10:4). The covenantal spine of the unit: the rock struck in the wilderness so water could flow was a type, and the antitype is Christ struck at the cross so the Spirit could flow (7:39, "not yet given, because Jesus was not yet glorified"). Give the disciple tier the rock and 1 Corinthians 10:4.

**The Spirit given after Jesus is glorified (7:39).** The unit's forward hinge into the whole Gospel. The rivers wait on the cross and the resurrection and the ascension. John threads it to 16:7 ("if I do not go away, the Helper will not come to you") and 20:22. For the room: the water Jesus promises is the Spirit, and the Spirit comes because Jesus is lifted up.

**The living-water thread from Unit 6, closed.** Unit 6 ruled 4:10-14 the Spirit and pointed forward to 7:39 as the verse where John says so. This unit is that payoff. Build on it: what the woman was offered at the well, the whole crowd is now offered at the feast, and John finally says the word "Spirit" out loud (7:39).

**The feast setting up 8:12.** The same Tabernacles that lit the temple with great lamps is where Jesus says "I am the light of the world" (8:12), the next new anchor in Unit 12. Plant nothing of 8:12 here. Let the feast frame stand so it pays off next unit.

**The tabernacling Word keeping the Feast of Tabernacles.** Sermon 10 presses the wordplay only this Gospel can: John 1:14 says the Word "dwelt" (tabernacled) among us, and here he tabernacles at the Feast of Tabernacles, the God who commanded the feast now keeping it in the flesh. A rich beat for L1 and a tie back to the Unit 1 Prologue.

## Reaching the three-tier room

The contact points are strong for teenagers: a family that does not get you, a thirst nothing satisfies, sides taken over a person, secret belief with a public cost, and the pull to follow the crowd's opinion instead of examining the evidence.

- **Searching student.** The floor is thirst, and sermon 12 preaches it straight at them: you have been thirsty your whole life and tried to fill it with everything. Jesus stands up and says the thirst has an address, "come to me and drink" (7:37). Every searching student should leave able to find John 7 and say one sentence: at a feast about water in the desert, Jesus said he is the real water, the Spirit, and the way to drink is to come to him and trust him. The floor at L1 is the family point: Jesus' own brothers did not believe him, so a student whose home does not believe is in the company of the Lord himself.
- **Churched but coasting.** Their mirror is in two places. First, 7:17 and sermon 11: a person can decide whether God has spoken by whether he likes it, building a God shaped like themselves who never disagrees. Press it gently: if your God never contradicts you, ask who you are worshiping. Second, sermon 12's most common churchgoer, the one who will not come back to the fountain until he has cleaned himself up, treating self-punishment as a down payment on grace. Hand him the ruling: you never move to a partnership where you earn the next drink. The grace you first received is the grace you daily need.
- **Maturing disciple.** Give them the weight: the water ceremony and the eighth-day silence, the punctuation question, John's Spirit gloss (7:39) closing the 4:14 thread, the rock of 1 Corinthians 10:4, the double irony of the origin debate (7:27, 41-42), Chrysostom and Augustine on 7:16-17, and the confessional link from 7:38-39 to Christian liberty. Let them trace how a feast about water in the wilderness becomes Christ's clearest offer of the Spirit.

Keep faith content invitational and participation assignable. Every student can analyze the claim and the crowd's division. No student is required to profess it.

## Memory: review only

This unit plants no new graded verse. Students hold the six anchors they already carry: 20:31, 1:14, 1:12, 3:16, 4:24, and 6:35 (planted last unit in Unit 9). Assign nothing from chapter 7 to the graded line and quiz nothing new. Run a light cumulative pass on the six, and let 6:35 ("whoever believes in me shall never thirst") sit next to 7:37 ("if anyone thirsts, come to me and drink"), since 7:37 is the same promise the crowd hears out loud. The next new anchor is 8:12 in Unit 12.

Offer John 7:37-38 as an optional stretch off the graded line, on L4 where it lives. It is on the taught-not-memorized list, it is the unit's namesake and christological summit, and it is the sermon's one-point charge. Keep it off the graded set, the way earlier units offered 2:11, 3:30, 4:50, and 5:24. It is a gift for the student who wants to carry the living-water cry.

## Pitfalls with teenagers

- Turning "rivers of living water" into a vague feelings or experience thing. John blocks it: the water is the Spirit (7:39). Teach the Spirit, grounded in the 4:14 thread, not an inner glow.
- Making the brothers' unbelief a lesson in family-shaming. The point is that Jesus was rejected by his own and still went to the cross for them, and they later believed (Acts 1:14; James 1:1). It is comfort for the student with an unbelieving household.
- Flattening the division into "just pick a side." The crowd's failure is the verdict reached on appearances (7:24) without examining the evidence (7:52). Teach them to examine the claim, the opposite of following the room's opinion.
- Anti-Jewish readings of "the Jews" and the leaders. "The Jews" here names the hostile authorities in this scene. Jesus, his brothers, the officers, the believing crowd, and Nicodemus are all Jewish, and John shows Jews divided over Jesus, some believing (7:31). No contempt. The warning of 7:17 and 7:24 lands on every heart that judges Christ by appearances, the churched student included.
- Reading Nicodemus as a coward or as fully converted. He is a man edging out of the dark (Unit 4's bookend arc). Do not moralize him into "be brave," and do not baptize him early.
- Prosperity misreads of the thirst-satisfied promise. The water is the Spirit and eternal life, not a life without want. The God who answers "give me the thing I want" on demand is an idol of our own making. Christ satisfies the deepest thirst, and the cross comes before the crown.
- Legalist side door on 7:37. Watch the close of the L4 lesson. The invitation is "come and drink," by faith alone, and the believer's overflow is the Spirit's work, not the student's resolve. Sermon 12's whole burden is that you do not clean yourself up before you drink.

## Also worth emphasizing

- "No one ever spoke like this man" (7:46). The arresting officers cannot arrest him because his word stops them. Sermon 12's application is sharp: whatever you thought you could do with Jesus (handle him, mold him, fit him in a box), take your hands off and listen. The best single beat for the short Thursday.
- The Spirit and gospel community (sermon 11). Jesus grounds his teaching in the Sender (7:16-18), and the priesthood-of-believers payoff follows: the same Spirit indwells the church, so a student's mouth can carry God's truth to the room. It dignifies peer discipleship, which is the course's engine.
- The twice-failed arrest (7:30, 44). No hand touches him because his hour had not yet come. Tie it to L1's "my time has not yet come" (7:6-8). The whole chapter is bracketed by the sovereignty of his hour.

## The five-lesson split

The seams cut on the text's own scenes and match the three sermons (10 to L1, 11 to L2 and L3, 12 to L4 and L5). This keeps the temple-teaching unit whole (7:14-24), keeps the "is this the Christ" dialogue whole (7:25-36), and keeps the rivers-of-living-water cry joined to the division it produces (7:37-44). L5 is the short Thursday and gets the tightest single scene.

- **L1 (i=42, Fri Nov 6, regular 50), John 7:1-13: lost brothers and the hidden ascent.** The brothers' unbelief and their taunt to show himself to the world (7:3-5), "my time has not yet come" (7:6-8), the secret going-up (7:10), and the muttering crowd, "a good man" against "he is leading the people astray" (7:12). Build on sermon 10. Set the Feast of Booths frame here (the wilderness water, the tabernacling Word of 1:14) as the setup for the whole unit. Lands on: Christ who moves on the Father's clock toward his hour, rejected by his own, going his own way to the feast.

- **L2 (i=43, Mon Nov 9, regular 50), John 7:14-24: teaching in the temple, and the test.** Jesus teaching mid-feast (7:14), "my teaching is not mine" (7:16), the test at 7:17 (the will to obey precedes the knowing, Chrysostom and Augustine), the Moses, circumcision, and Sabbath argument reaching back to the Bethesda healing (7:19-23), and "judge with right judgment" (7:24). Build on the first half of sermon 11 (the Father-sent teaching, the self-made God who never disagrees). Lands on: Christ the Sent One whose teaching is the Father's own.

- **L3 (i=44, Tue Nov 10, regular 50), John 7:25-36: can this be the Christ?** The Jerusalemites' origin confusion (7:25-27), Jesus' cry "he who sent me is true, and him you do not know" (7:28-29), the first failed seizure "because his hour had not yet come" (7:30), the many who believe (7:31), the officers dispatched (7:32), and "you will seek me and you will not find me" (7:33-36). Build on the second half of sermon 11 (where he comes from, who sent him, where he is going). Keep the dialogue whole. Lands on: Christ who comes from the Father, unseizable until his hour, returning to the One who sent him.

- **L4 (i=45, Wed Nov 11, regular 50), John 7:37-44: rivers of living water.** The great cry on the last day (7:37), "out of his heart will flow rivers of living water" (7:38), John's Spirit gloss (7:39), and the division it produces (the Prophet, the Christ, the Galilee objection, the Bethlehem irony, 7:40-44). The christological summit and the unit's namesake, given a full period. Carry the big ruling in full: the water is the Spirit, Christ is the fountain, the believer is the streambed, drink by faith and keep coming. Teach the water ceremony and the eighth-day silence. Offer John 7:37-38 as the optional stretch here, off the graded line. Lands on: Christ the living water, from whom the Spirit flows to everyone who believes.

- **L5 (i=46, Thu Nov 12, Thursday 36, single-focus), John 7:45-52: no one ever spoke like this man.** One tight scene for the short day, one key question: "What does it cost to speak up for Jesus, and what happens to people who judge him by appearances?" The officers return disarmed (7:45-46), the leaders' contempt for the crowd (7:47-49), Nicodemus's careful defense (7:50-51), and the sneer "no prophet arises from Galilee" (7:52). Build on the closing of sermon 12 (the word that arrests the arresters, the box the leaders will not let Jesus out of). Handle Nicodemus with Unit 4's bookend arc, neither coward nor finished convert. Lands on: Christ whose word disarms the men sent to seize him, and the honesty of a man edging toward the light.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# Lost Brothers (John 7:1-13)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 7:1-13

---

[00:00] No. Before I get started, though, guys, I just wanted to celebrate with you guys just one more announcement. You know, last week was our inaugural, compassion Sunday at Mercy's Door. If you were here, we we brought in, Benton and Kristen, who are both sick with COVID this morning. You guys will be praying for them.

[00:16] But they came and they gave testimony before the church to talk about their relationship with Compassion International and these kids that they've been sponsoring for several years. And we reached out to you guys and we said, know, we'd really love to see Mercy's Door respond and and initiate a partnership with Compassion International. And I was kind of stressed about it. I was praying about it a ton, because, I mean, if you look around in the summers, every summer, really, attendance on a Sunday morning fluctuates a ton as people travel and visit their families and celebrate their vacations and all that. And so we don't really know what to expect on a given Sunday morning, what we're gonna see.

[00:50] And so it was a labor to kind of determine, like, Lord, how many children would you have us put on this table? It's really what it comes down to. The numbers don't matter in here, but I I don't wanna grab any kids and put them on that table if they're not gonna be sponsored. Because, for three weeks they'll be out of the registry as we hold them out to our church. And so we brought 15 children before you guys, and by the end of service, 14 of them had been sponsored.

[01:13] Thank you so much. You guys can clap. Just really wonderful. Really wonderful. And then there was this one little girl left, little Arlette, four years old from Bolivia, who had not been sponsored.

[01:24] And by midweek, somebody in the church picked her up. And so all 15 children have been accounted for. Just wanted to celebrate that with you guys. Thank you for that. And then give you next steps.

[01:32] Okay? So what it means for you now is firstly, we weren't praying that all of the packets would be picked up off the table, we were praying that they would all be sponsored. So if you haven't sponsored them yet, if you took the packet and you haven't completed the sponsorship process, you've got, like, ten days to make that happen before they'll go back in the registry. Okay? So I just want to encourage you to complete the process if you haven't done that yet.

[01:53] Secondly, I wanted to invite you guys to start and initiate correspondence with your sponsored child. Okay? You can do it now through the Compassion International app, if you download that. I've tried it. I can see both my sponsorships right in the app and communicate, through letter writing right through the app.

[02:09] So they make it super easy now. Would love for you guys to think about how, not just with your $38 a month, you're able to meet their needs for clean water and food and education and things like that, but that you now have access to somebody somewhere else in the world to be a gospel influence in their life, that you would begin that that interaction with them. So do that this week. And then, lastly, I wanted to invite you guys to start thinking about how you might integrate these kiddos into your gospel communities. Okay?

[02:36] So what I would like is that six months from now, that I could walk into any GC and ask any member about the compassion kids that have been sponsored by members of your GC, and that they would know them by name. Because you guys are bringing out the cards or pulling up the app and praying for them as a gospel community for those kids, that we might believe that more than $38 a month that the Lord can do abundantly more for them. Right? And so, let's create a culture of loving these kids in order that a year from now, when on Father's Day we have another compassion Sunday, then maybe it's one of you who's gonna be up here speaking to the church about what you've seen the Lord doing through our partnership with Compassion International, as we invite other people into that. Okay.

[03:14] So just super pleased to see the spirit move in you guys last week, and celebrating that with you. Now, I think it was maybe in year one or two of Mercy's Door, somewhere in between those two years, we had a guy, his name was Kyle, who initiated a men's only camping trip for the church. And he was a survivalist. He worked in the military. He jumped out of airplanes and would, like, teach guys how to survive behind enemy lines until help came.

[03:43] And so a really cool guy to organize a camping trip is what I'm trying to say. And when he got all of the guys together, I brought my, two older kids. My middle kid, Boaz, was five ish at the time. And I wasn't sure if he'd be ready for a camping trip, just because he was five and still was afraid of the dark. Right?

[04:00] And so was he ready to sleep in a tent in a strange place. Right? Well, it was incredible. Right? So, Kyle, he, sun dried a snake on a rock for eating.

[04:10] Right? Like, he taught, like, the kids, like, that like, that you could eat ants. Right? He taught Boaz how to use a flint and steel to strike a fire, and and and and he showed him a lot of different methods for starting a fire. They went on trail blazing excursions and, splashed around in a brook, and it was like just an incredible camping trip.

[04:30] Okay? We were singing worship songs around a bonfire, till the middle of the night, and then it came time to go to bed. And Boaz is sleeping with me, and so I take him into our little two person tent, and we've got kind of one of those mesh openings on the dome of the tents, that when you lay down, you can see straight through. I mean, no light pollution, beautiful, clear skies. You can see all the stars in the sky.

[04:53] You can see the moon. And we just sat there, his head tucked onto my wing, and we looked up and just marveled together at the night sky. And I'm talking to him about how these stars just testify the majesty of our God. We talked about father Abraham and how he would have been looking at these same stars when the Lord made his promise to him that his children would outnumber these stars, but that he didn't know when God said that to him, that he'd be talking about us. Right?

[05:23] That we were counted among the stars. And it was amazing. Just an incredible night. And Bo fell asleep so peacefully and wonderfully. And the next afternoon, when we left, I asked him, you know, of all the things that we did on this camping trip, what was your favorite part of your first camping trip?

[05:41] And he says, without a moment's hesitation, sleeping under the stars. Sleeping under the stars. And this story came to my heart as I was preparing this morning's message because this morning's message takes place during what's called the Feast of Booths. And the Feast of Boo
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.7.1-13`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
