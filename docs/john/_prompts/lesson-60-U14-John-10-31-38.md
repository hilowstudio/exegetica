<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U14-L4-John-10-31-38.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": []} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 10:31-38.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.10.31-38] Teach John 10:31-38 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 10:31-38

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 60 of 150.
UNIT (use this exact name): U14 The Good Shepherd.  LESSON WITHIN UNIT: 4/5.
PASSAGE: John 10:31-38.  DAY TYPE: Regular (50 min) (use the matching variant).

UNIT MEMORY VERSE: John 10:11 (ESV) was planted earlier in this unit, in the passage where it appears. REVIEW it here. Do NOT re-plant it.
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 10:1-42, "The Good Shepherd" (Unit 14)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Five lessons. L1 and L2 build on Adam's sermon 15, "I Am the Good Shepherd" (which covers 10:1-18). L3, L4, and L5 are framed fresh (no sermon covers 10:19-42). This unit plants the new graded anchor, John 10:11. Quote the ESV in the finished materials.

A word to set the room. John 10 has no chapter break in Jesus' mind. He is still standing in front of the men who cast out the blind man (9:34), still answering the Pharisees who said "we see" (9:41). The shepherd discourse is aimed first at shepherds who fed themselves and threw a healed man into the street. Ezekiel 34 is the text underneath the whole unit, and this is not a guess: at the Feast of Dedication the priests examined their own service using Ezekiel 34 as their main text. Jesus stands in the temple at the one feast built for shepherd self-examination and says: I am the good shepherd, and you are the hirelings Ezekiel named.

## The christotelic center

The unit lands on Jesus as the LORD the Shepherd of Ezekiel 34 and Psalm 23, come in person to gather and keep the flock, and it lands hardest on the shepherd's goodness spending itself in his death and resurrection for the sheep. Ezekiel 34 promised two things at once: "I myself will search for my sheep" (34:11) and "I will set up over them one shepherd, my servant David" (34:23). John 10 shows both fulfilled in one person. The God who comes to shepherd and the Davidic shepherd he sends are the same man standing in Solomon's Colonnade. The center in one sentence: the good shepherd is the LORD himself, and his goodness is a cross he lays down of his own accord and a life he takes up again, so that the sheep the Father gave him can never be lost.

- L1 (10:1-10) lands on Christ the door of the sheep, the one way in to salvation and pasture.
- L2 (10:11-18) lands on Christ the good shepherd who lays down his life for the sheep and takes it up again.
- L3 (10:19-30) lands on Christ one with the Father, whose hand and the Father's hand hold the sheep so no one can snatch them.
- L4 (10:31-38) lands on Christ the Son of God, consecrated and sent, whose works testify that the Father is in him and he in the Father.
- L5 (10:39-42) lands on Christ vindicated where his ministry began, the one about whom the Baptist told the truth, believed by many at the Jordan.

## The contested points, ruled

**The sheepfold, the door, and the voice (10:1-6).** Rule this an extended figure (John calls it a figure of speech, 10:6), not an allegory to decode piece by piece. A walled communal fold holding several flocks, one gate, a gatekeeper, and shepherds who each call their own out by a voice the sheep know. The load-bearing point is the voice. Sheep are sorted by whose voice they answer to, and Jesus is proving it as he speaks: the men in front of him do not recognize the voice, which is the evidence that they are not his. Do not over-assign the gatekeeper. Jesus never identifies him, so leave him unidentified.

**"I am the door" (10:7-10).** Rule the door saying a second, distinct figure inside the same imagery. Jesus is the gate. Entry to salvation and access to pasture both run through him alone, "If anyone enters by me, he will be saved" (10:9). Rule "life abundantly" (10:10) against every prosperity reading. The abundant life stands over against a thief who comes "to steal and kill and destroy," so its content is rescue, safety, and pasture in the shepherd's keeping, the eternal life named plainly at 10:28. It is not a promise of comfort, health, or gain on demand. The world wants the pasture without the gate, and Jesus says every other way leads to death. Cross before crown.

**"I am the good shepherd" and the word "good" (10:11).** The word is kalos, and it is worth teaching. It means beautiful, fair, noble, honorable, the appearance matching the essence. The good shepherd is the beautiful and model shepherd, the true one against every counterfeit, and his beauty shows itself in the one act named in the same breath: "The good shepherd lays down his life for the sheep." Clement of Alexandria saw it in the second century: so good was he that he died for us. Rule the shepherd's goodness inseparable from his death. A shepherd painted as gentle and near, with the cross removed, is not the good shepherd of this verse.

**The hired hand who flees (10:11-13).** Rule the contrast one of ownership and love, not competence. The hired hand can do real work, feed and water and clean the fold, and do it well. What he will not do is die, because "the sheep are not his own" (10:12). Jesus will always stand between his sheep and the danger. Keep the guard against sentimentality here, the sermon's best single move: Jesus did not throw himself off a cliff shouting "look how much I love you." A real wolf, sin and the enemy, was coming for the sheep, and he stepped between them and it and let it kill him.

**"I know my own and my own know me" (10:14-15).** Rule the knowing mutual, personal, and grounded in the life of God: "just as the Father knows me and I know the Father." The sheep are known by name (10:3), and the shepherd's knowledge of them is measured by the Father and Son's knowledge of each other. This is the pastoral floor of the unit and the strongest contact point for the room.

**"Other sheep, one flock, one shepherd" (10:16).** Rule this the Gentile mission, and rule the order deliberate. "I have other sheep" (present tense, already his) "that are not of this fold. I must bring them also... and they will listen to my voice." Somehow they are his before he calls them, and because they are his they respond to his voice. The cross-references confirm the reach: Isaiah 56:8, John 11:52, Ephesians 2:13-18, 1 Peter 2:25. Rule against flattening "one flock" into a slogan about unity in general. It is Jew and Gentile made one flock under one shepherd by his blood.

**"I lay down my life that I may take it up again... I have authority" (10:17-18).** Rule the death voluntary and the resurrection his own act under the Father's charge. "No one takes it from me, but I lay it down of my own accord. I have authority to lay it down, and authority to take it up again." He took your sin and death into the grave, and then he came up alone, victorious over sin and death for you. The cross-references anchor both halves: John 2:19-21, Isaiah 53:10-12, Hebrews 5:6-9, John 6:38. Rule the "authority to take it up again" a claim to divine power over his own life, made by the man they are about to try to stone.

**The Old Testament shepherd, and Jesus as the LORD the Shepherd.** Rule this the interpretive key to the whole unit. God was the shepherd of Israel (Genesis 49:24; Psalm 23; 78:52-53; Isaiah 40:10-11), and the leaders were shepherds who failed (Ezekiel 34; Jeremiah 23:1-4). Read the three texts to the room. Ezekiel 34: "Ah, shepherds of Israel who have been feeding yourselves" (34:2), then "I myself will search for my sheep" (34:11), then "I will set up over them one shepherd, my servant David" (34:23). Psalm 23:1: "The LORD is my shepherd." Isaiah 40:10-11: "the Lord GOD comes with might," and in the same breath "he will tend his flock like a shepherd; he will gather the lambs in his arms." The claim Jesus makes by saying "I am the good shepherd" is the claim of Isaiah 40, that the LORD who comes with might is the shepherd who carries lambs. This is a deity claim before he ever says "I and the Father are one." The cross-references on 10:11 make the point: Psalm 23:1, Isaiah 40:11, Ezekiel 34:23, 1 Peter 2:24-25, Revelation 7:17.

**The division tied back to the blind man (10:19-21).** Rule this the same division chapter 9 produced, still running. "There was again a division among the Jews" (10:19). One side: "He has a demon, and is insane." The other: "Can a demon open the eyes of the blind?" (10:21). That line reaches straight back into Unit 13. The healing of the man born blind is still the exhibit, and it is now the argument against the charge of demon-possession. Teach the continuity plainly.

**The Feast of Dedication (10:22).** Rule the setting load-bearing. It is Hanukkah, winter, the feast remembering the rededication of the temple after Antiochus defiled it, when Judas Maccabeus reclaimed it in 164 BC. Two facts do real work. First, priests used Ezekiel 34 for self-examination at this feast, so Jesus' shepherd claim lands on exactly the men Ezekiel indicted. Second, the feast is about the true temple and true worship being restored, and John has already made Jesus the true temple (2:19-21). He stands at the festival of the temple's rededication and puts himself at its center.

**"My sheep hear my voice... no one will snatch them out of my hand" (10:27-29), the security of the sheep.** Rule this the doctrine of perseverance, grounded in the Father's gift and the Son's grip, and rule the two verses a double hand. "I give them eternal life, and they will never perish, and no one will snatch them out of my hand" (10:28), and then "My Father, who has given them to me, is greater than all, and no one is able to snatch them out of the Father's hand" (10:29). The sheep are held in the Son's hand and the Father's hand at once. This is the payoff of Unit 9: the cross-references on 10:28 run first to John 6:37 and 6:39-40, the "I lose none the Father gives me" students met in the Bread of Life discourse, and forward to John 18:9, Hebrews 7:25, Philippians 1:6. The confessions cite 10:28 for perseverance across the whole tradition (Westminster, 1689, Savoy 17.1) and Heidelberg Q1, "not a hair can fall from my head without the will of my heavenly Father." On teaching this to teenagers, see the pitfalls.

**"I and the Father are one" (10:30).** Rule this the ground of the security just promised, and a claim to deity. Read the seam. Verse 28 is the Son's hand, verse 29 is the Father's hand, verse 30 explains how one flock can be held safe in two hands: "I and the Father are one." The oneness is introduced to seal the keeping of the sheep. It is also, as the next verse proves, a claim the hearers took as deity. Teach it as the neuter "one" the Greek uses: one in being and power, two persons (Father and Son named as two), which the creeds guard exactly.

**The stoning, "you, being a man, make yourself God" (10:31-33).** Rule the crowd's reading of Jesus correct. They picked up stones for blasphemy, "because you, being a man, make yourself God" (10:33). They understood him. Chrysostom is decisive: our Lord did not correct the Jews as if they misunderstood, but confirmed and defended his words in the very sense they had taken them. Rule against the modern dodge that Jesus never claimed deity and was misheard. He heard their charge and answered it without retracting it. Note the beauty in their own words: Jesus says he has shown them many good works (10:32, the same root as the good shepherd), and they stone him for the beautiful works.

**The Psalm 82 argument (10:34-36), the hard one.** Rule it an argument from the lesser to the greater, and rule firmly against the two misreadings. Jesus quotes Psalm 82:6, "I said, you are gods." In the psalm, God addresses Israel's judges, the men "to whom the word of God came" (10:35), and calls them "gods" because they held a God-given office of judgment, then sentences them: "like men you shall die" (Psalm 82:7). The argument runs: if Scripture, which cannot be broken, could call those men "gods" because the word of God came to them, how is it blasphemy for the one "whom the Father consecrated and sent into the world" to call himself the Son of God (10:36)? Chrysostom states the logic: if those who received this honor by grace are not blamed for being called gods, how can he who has it by nature deserve to be rebuked? That carries the whole ruling. The judges were called gods by grace and office. Jesus is Son by nature. The argument does not lower Jesus to their level. It shames the charge of blasphemy by showing the word "god" is not itself a lightning rod, then presses to his true and higher claim, sealed at 10:38, "the Father is in me and I am in the Father." Rule out both errors by name. This is not "we are all gods" (the psalm calls the judges gods and then condemns them to die), and it is not "Jesus denied being God" (he moves from the argument straight to mutual indwelling with the Father, the strongest claim yet). For sophomores, teach it as a courtroom move: "You say I blaspheme for calling myself God's Son. Your own Scripture calls your judges 'gods.' If the office-holders could be called that, how much more the one the Father set apart and sent?"

**The withdrawal beyond the Jordan (10:40-42), the Baptist vindicated.** Rule this the quiet resolution of the whole divided chapter, and the payoff of Units 1 and 2. Jesus goes back "to the place where John had been baptizing at first" (10:40), and the people say, "John did no sign, but everything that John said about this man was true" (10:41). Rule the point double. The Baptist's witness, given at the very start of the Gospel (1:19-34, "Behold, the Lamb of God"), is now confirmed by events. And the chapter that opened in a stoning closes in belief: "many believed in him there" (10:42). Where Jerusalem reached for stones, the Jordan reaches for faith.

## Christological and covenantal connections

- **Jesus is the LORD the Shepherd of Ezekiel 34 and Psalm 23.** The two promises of Ezekiel 34 (God coming himself, 34:11; God sending the Davidic shepherd, 34:23) meet in one man. Isaiah 40:11 makes the shepherd claim a deity claim.
- **The good shepherd lays down his life, the cross foretold and freely chosen (10:17-18).** The death voluntary, the resurrection his own act under the Father's charge (Isaiah 53:10-12; John 2:19-21; Hebrews 5:6-9).
- **One flock of Jew and Gentile (10:16).** The New Covenant people, gathered from both folds under one shepherd (Isaiah 56:8; John 11:52; Ephesians 2:13-18). The church as the one flock of the one shepherd.
- **The keeping of the sheep tied to 6:37-39 (Unit 9).** 10:28-29 is the same sovereign keeping students met in the Bread of Life discourse, now doubled (Son's hand and Father's hand) and sealed by 10:30 (John 6:37; 6:39-40; 18:9).
- **"I and the Father are one" on the deity thread.** This joins the "I am" sayings of Units 9, 12, and this unit, and the deity claims that drew stones at 8:58-59 (Unit 12) and draw them again here at 10:31.
- **The Baptist's witness vindicated (10:40-42), tying back to Units 1 and 2.** The first witness of the Gospel is confirmed true at the place where he witnessed.

## Reaching the three-tier room

The contact points are strong and concrete: being known by name (10:3, 10:14), whose voice you actually follow (10:4-5, 10:27), being led versus being used (10:11-13), the security of belonging to someone who will not let go (10:28-29), and a shepherd who dies for the sheep (10:11).

- **Searching student.** The floor is the voice and the name. A shepherd who knows every sheep by name, whose sheep know his voice and will not follow a stranger. Ask the plain question: who are you actually listening to, and does that voice want you or want something from you? The rancher-versus-shepherd frame is built for this student. Everyone has been under someone who fattened them for market. Here is a shepherd who dies instead of selling. No Bible knowledge is assumed to feel the difference.
- **Churched but coasting.** Their mirror is the men in the temple. They knew Ezekiel 34 cold, kept the feast, ran the synagogue, and could not hear the shepherd's voice standing in front of them (10:6, 10:25-26). Press it gently with 10:26, "you do not believe because you are not among my sheep." The danger is hearing the voice every week and following a stranger. Their other mirror is the hired hand, doing all the shepherd's work with none of the shepherd's love, present for a wage.
- **Maturing disciple.** Give them the weight: kalos and its tie to the good works the crowd stones him for, Isaiah 40:11 as a deity claim, the double hand of 10:28-29 grounded in the oneness of 10:30 read as one argument, the Psalm 82 logic worked out with Chrysostom (grace-gods versus the Son by nature), and the Ezekiel 34 background of the Dedication feast. Let them trace how the shepherd discourse, the security promise, and the deity claim are one continuous argument.

Keep faith content invitational and participation assignable. Every student can analyze the voice, the two hands, and the Psalm 82 argument. No student is required to profess.

## The memory verse, John 10:11 (this unit's new plant, on L2)

Plant and teach it on L2 (10:11-18), where the verse heads its own lesson. ESV: "I am the good shepherd. The good shepherd lays down his life for the sheep."

The fresh angle: students hold seven anchors already, and three are "I am" sayings (6:35 bread, 8:12 light, and 4:24 nearby). Every prior "I am" tells them what Jesus gives. This is the "I am" that dies. The predicate spends itself in the same sentence: "I am the good shepherd. The good shepherd lays down his life for the sheep." Teach "good" (kalos) as beautiful and true, and then show the beauty is a cross. Two words carry the plant. "Good," the real and beautiful shepherd whose goodness is his dying. And "for the sheep," his own, the ones he calls by name, which makes the verse a promise of belonging and not a general fact about Jesus being nice. The angle in one line for the room: this is the memory verse where "I am" and "I die for you" are the same sentence. Let 10:11 sit next to 8:12 in the cumulative pass. Last unit's anchor said "I am the light of the world." This unit's says the light lays down his life for the sheep.

The other four lessons do not plant, teach, or quiz 10:11 as the graded verse. Keep the seven earlier anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12), plus 10:11 once planted. The next new anchor is 11:25 in Unit 15.

## Pitfalls with teenagers

- Sentimentalizing the shepherd. Cute lambs, a soft-focus Jesus, the cross edited out. The best guard is the sermon's: a real wolf was coming, and he stepped between it and the sheep and let it kill him. Kalos is beautiful, and the beauty is the dying (10:11).
- Prosperity misreads of "life abundantly" (10:10). The abundant life stands against a thief who steals, kills, and destroys, so its content is rescue and pasture and eternal life (10:28), not health or gain on demand. Cross before crown.
- Eternal security twisted into presumption. "I prayed a prayer, so I can live how I want." Guard it with the verse itself: the secure ones are the ones who "hear my voice... and follow me" (10:27). A sheep that follows no shepherd has no ground to claim the shepherd's hand. Assurance here is for followers, and following is the mark of a sheep, never the price of the shepherd's grip. Marshall's order holds: the keeping comes first and produces the following.
- Eternal security twisted into anxiety. "What if I'm not really a sheep." Aim 10:28-29 straight at this student. The security rests on the Father's gift and the Son's grip and their oneness (10:30), not on the strength of the sheep. The question is not whether your hand is strong enough to hold him. It is whose hand holds you, and there are two, and they are one. Heidelberg Q1 is the pastoral word: not a hair can fall without the will of the Father.
- Misusing the Psalm 82 argument. Two errors, both named above. It does not teach "we are all gods" (the psalm sentences those gods to die, 82:7). It does not mean "Jesus denied being God" (he moves straight to "the Father is in me, and I am in the Father," 10:38). Teach it as a lesser-to-greater courtroom move.
- Anti-Jewish reading of the stoning crowd. "The Jews" in 10:19, 24, 31, 33 names the hostile leadership and those gathered against him. Jesus, the Baptist, the divided crowd (10:19, 21), and the many who believe at the Jordan (10:42) are all Jewish. John shows Jews divided over Jesus. The line measures response to Christ, and it falls on the churched student as readily as anyone. Carry the same guard Unit 13 carried on 9:22.
- "One flock" flattened into generic unity. It is Jew and Gentile made one under one shepherd (10:16), the church of the New Covenant, purchased by his blood.

## Also worth emphasizing

- The Ezekiel 34 setting is the sharpest historical detail in the unit. Priests examined themselves against Ezekiel 34 at the Feast of Dedication. Jesus makes the shepherd claim at the one feast built for shepherd self-examination, to the very shepherds Ezekiel indicted. This ties 10:1-18 and 10:22-30 together and should be surfaced in L2 or L3.
- The shepherd who finds the cast-out man carries straight into this unit. Unit 13 ended with Jesus finding the man thrown out of the synagogue (9:35). Chapter 10 opens with the shepherd who calls his own by name and leads them out, spoken to the men who did the throwing out.
- The double hand (10:28-29) is the structural gift of L3. Do not teach the security and the oneness as two separate topics. Verse 30 is the answer to how two hands keep one flock. Teach them as one argument and the deity claim lands with pastoral force.
- "Believe the works" (10:38) is a real invitation to the doubter. Jesus meets the ones who cannot yet believe him and offers a lower rung: even if you do not believe me, believe the works. A warm word for the searching student who is not there yet. Belief in this Gospel has an on-ramp.

## The five-lesson split

The seams cut on the chapter's own thought units. Every lesson lands on Christ, L1 through L4 are regular, and L5 is the tight single-focus Thursday and the last passage.

- **L1 (i=57, Fri Dec 4, regular 50), John 10:1-10: the fold, the voice, and the door.** The sheepfold figure (10:1-6), sheep sorted by the shepherd's voice, then the door saying (10:7-10), "I am the door," the one way to salvation and pasture, and abundant life over against the thief. Keep the door saying whole. Set the Ezekiel 34 background and the still-present audience from chapter 9 here. Lands on: Christ the door, the only way in. Build on sermon 15.

- **L2 (i=58, Mon Dec 7, regular 50), John 10:11-18: the good shepherd. Plants and teaches John 10:11.** The whole shepherd discourse in one room: kalos (10:11), the hired hand who flees (10:12-13), "I know my own and my own know me" (10:14-15), the other sheep and one flock (10:16), the voluntary death and resurrection (10:17-18). The memory verse heads its own lesson and gets the full period the plant deserves. Lands on: Christ the good shepherd who lays down his life and takes it up again. Build on sermon 15.

- **L3 (i=59, Tue Dec 8, regular 50), John 10:19-30: division, the Dedication, and the two hands.** The division tied back to the blind man (10:19-21), the Feast of Dedication setting (10:22-23), "tell us plainly" and "you do not believe because you are not my sheep" (10:24-26), and the heart of the lesson: the sheep who hear his voice, eternal life, the two hands no one can snatch from (10:27-29), sealed by "I and the Father are one" (10:30). Cut at the strongest seam in the chapter, between the claim (10:30) and the stones (10:31). Teach the security and the oneness as one argument. Lands on: Christ one with the Father, whose hand and the Father's hand keep the flock. Framed fresh.

- **L4 (i=60, Wed Dec 9, regular 50), John 10:31-38: the stoning and the Psalm 82 argument.** The stones and the charge, "you, being a man, make yourself God" (10:31-33), the Psalm 82 argument worked lesser-to-greater (10:34-36), and the appeal to the works, "the Father is in me and I am in the Father" (10:37-38). Keep the Psalm 82 argument whole, with room to teach it carefully and rule out both misreadings. Lands on: Christ the Son of God, consecrated and sent, whose works testify to his oneness with the Father. Framed fresh.

- **L5 (i=61, Thu Dec 10, Thursday 36, single-focus), John 10:39-42: vindicated at the Jordan.** A self-contained closing scene. They reach for him a last time and he slips their grasp (10:39), and he withdraws across the Jordan to where the Baptist first baptized (10:40), where the people say everything John said about this man was true and many believed (10:41-42). One key question: "This whole chapter has been a fight over who Jesus is. Where does it finally land, and on whose word?" The answer vindicates the Baptist of Units 1 and 2 and ends the divided chapter in belief. Lands on: Christ believed, the one about whom the first witness told the truth. Framed fresh.
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.10.31-38`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
