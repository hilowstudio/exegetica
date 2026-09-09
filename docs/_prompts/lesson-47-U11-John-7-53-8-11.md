<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U11-L1-John-7-53-8-11.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": []} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 7:53-8:11.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.7.53-8.11] Teach John 7:53-8:11 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 7:53-8:11

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 47 of 150.
UNIT (use this exact name): U11 A note on the text.  LESSON WITHIN UNIT: 1/1.
PASSAGE: John 7:53-8:11.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24, John 6:35); the next new one comes in John 8:12 (Unit 12).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 7:53-8:11, "A note on the text" (Unit 11)

Adam's theological framing for this single light lesson, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). One lesson only (i=47, Fri Nov 13, regular 50 min, LIGHT, role "note"). No paired sermon, so frame it fresh. The unit does two honest jobs at once: it teaches the textual-criticism question as a trust-builder, and it teaches the passage's content faithfully and pastorally. Memory is review only, and no line from this passage is offered even as an optional stretch (see below). Quote the ESV in the finished materials.

## The christotelic center

At a temple trap meant to catch him between Moses and Rome, the only man in the courtyard qualified to throw the stone is the one who lays it down. Grace and truth stand in one person (1:14). He names the sin plainly and refuses to condemn the sinner, and he can do both at once because the condemnation she has earned will fall on him at the cross. The lesson lands on Christ the sinless Judge who came to save (3:17), holding the stone he alone had the right to throw and dropping it.

## The textual question, ruled for sophomores

This is the design heart of the unit. Rule it honestly and confidently. It is the Unit 8 model (the 5:3b-4 "angel stirring the water" note) at full strength.

**What the manuscript evidence is.** The story is absent from the earliest and best Greek manuscripts of John. The study notes are blunt: it was likely added to John's Gospel later, since it is not in the earliest Greek manuscripts, and it is likely a true story from the life of Jesus (Tyndale). The earliest and most reliable manuscripts do not contain this section, so it is almost certainly not part of the original text of John, and yet the passage is very old and may well contain a real event from Jesus' life (SIL). The ULT and the ESV set the verses in brackets to show John probably did not include them in his original text.

Two more facts for the disciple tier, both grounded:
- The passage floats. Adam Clarke records that where the story appears, it appears in different places: at the end of this Gospel in some manuscripts, in a blank space in this chapter in others, and after Luke 21 in others. A wandering location is a strong sign it was not original to this seam. Clarke also notes the clean join between 7:52 and 8:12, which is why a sharp student reading the ESV sees the bracket and the jump.
- The story is ancient anyway. Papias of Hierapolis, around 130 AD, already knew a story of a woman accused of many sins before the Lord (preserved through Eusebius, Church History 3.39.16). The account is older than the manuscripts of John that carry it, and the church has treated it as a true event from Jesus' life.

**The consensus and the range of faithful views.** The consensus is that these verses were most likely not part of what John wrote. Faithful Christians hold a range inside that: many (Calvin, JFB, the Tyndale and SIL editors) judge it a real event from Jesus' life, consistent with everything else we know of him, rightly kept in our Bibles; a minority argues for its authenticity in John. Calvin is the model of confident honesty: this passage was unknown anciently to the Greek churches, and yet it has always been received by the Latin churches, is found in many old Greek manuscripts, and contains nothing unworthy of an apostolic spirit, so there is no reason we should refuse to apply it to our benefit. JFB: the internal evidence in its favor is almost overpowering.

**How to say it to fifteen-year-olds so it builds trust.** The plain, non-alarming way:

Open your Bible to John 8 and look at the note. Your ESV puts a bracket and a footnote around this story. That is not a mistake, and nobody is hiding it. The oldest copies of John we have do not include these verses, so the people who make our Bibles tell you that, right on the page, in the open. Here is why that should make you trust your Bible more. We have thousands of ancient copies of the New Testament, and scholars compare them line by line, letter by letter. When something shows up later, or moves around, they flag it. They flagged this one. That is what careful looks like. And notice what does not change: not one teaching of the Christian faith rests on this passage. Jesus is still God in chapter 1. He still dies and rises. The doctrine of Scripture rests on the whole New Testament, thousands of manuscripts agreeing, and not on any single disputed paragraph. So we can read this story with open eyes. It is very old, the church has always believed it really happened, and it fits Jesus exactly. We hold it honestly and read it for our good.

Give the whole room one sentence: the note in your Bible is proof the people who gave it to you were telling you the truth. Keep the three disciple-tier facts (Papias, the floating location, the clean 7:52 to 8:12 join) in your pocket for the group that goes deep.

## The content, ruled

**The trap (8:3-6).** Rule it a deliberate ambush using a real woman as bait. The Law of Moses said both the woman and the man must die, and the Roman government had taken capital jurisdiction from the Jewish authorities (see 18:31), so "what do you say?" (8:5) is a vise. Say stone her, and Jesus breaks Roman law and contradicts the mercy he preaches. Say release her, and he appears to set Moses aside. John states the motive flatly: "This they said to test him, that they might have some charge to bring against him" (8:6). The woman is a prop in a plan to trap the teacher.

**Where is the man (8:4).** Press this, because it exposes the whole thing as unjust. They say she was "caught in the act of adultery" (8:4). Adultery in the act has two people in it, and the Law they quote requires both to die (Leviticus 20:10; Deuteronomy 22:22). The man is missing. These men are breaking Moses' law to weaponize half of it against a woman and against Jesus. Name the injustice out loud. It is one of the strongest contact points in the room.

**What Jesus writes on the ground (8:6, 8:8).** Rule the speculation honestly: we do not know. When Scripture is silent, we are silent, and the guesses are guesses. What we can see is the posture. He stoops, he is unhurried, and he refuses to be rushed by the mob.

**"Let him who is without sin among you be the first to cast a stone at her" (8:7).** Rule it a stroke that exposes the accusers without abolishing the law. The Law says the hands of the witnesses shall be first in putting the guilty to death (Deuteronomy 17:7), so Jesus makes the witnesses look at their own hands. "Without sin" here means a conscience clear of this kind of sin (JFB). He honors the law in the very sentence, and he makes it impossible for these particular men to be the ones to carry it out, because they came with dirty hands and a rigged case. The law stands, and the trap collapses.

**They leave, oldest first (8:9).** They went away one by one, beginning with the older ones, until only Jesus was left with the woman. The oldest go first because they have the longest record to remember. This is the mirror in the text (Romans 2:1-3).

**"Neither do I condemn you; go, and from now on sin no more" (8:11).** Hold mercy and truth together, and get the order right, because a teenager will hear only one half unless you make them hear both.
- The mercy is real and free. He does not extract a confession, a penance, or a promise first. He gives the word of release, then the command. Augustine catches the balance: the Lord condemned sins, not the woman, because if he were a patron of sin he would have said "neither will I condemn you, go and live as you please," and he said no such thing.
- The command is real too. "Go and sin no more" is the fruit of the mercy, growing out of it. It is the same word Jesus gave the healed man at Bethesda in Unit 8 (5:14). Grace names the sin as sin, and grace does not leave her in it. The command rests on the pardon already given, so it is a freed woman's new road and never a toll she pays for the mercy.

**Who is qualified to condemn.** Only one person in that courtyard could honestly pick up a stone, the one man there without sin. He is the rightful Judge (5:22, 27, from Unit 8), and he chooses to save. The sinless One holds the only clean hands in the story and uses them to lift her up.

## Christological and covenantal connections

**Grace and truth in one person (1:14, 1:17).** Unit 1 planted it: grace and truth came through Jesus Christ. Here it walks. Truth: "go and sin no more." Grace: "neither do I condemn you." Both from one mouth in one breath, with no strain between them. This scene is the Prologue's line acted out in a courtyard.

**Judgment self-selected (3:17-21, from Unit 4).** The top cross-reference on 8:11 is John 3:17, that Christ came not to condemn but to save. Unit 4 taught that the light comes and people sort themselves by whether they step into it. Here it happens in real time. The accusers walk out into their own verdict, oldest first (8:9), and the woman stays in the light with the Judge and is not condemned.

**The stone he was entitled to throw.** Every other hand in that courtyard was disqualified by sin. His was not. The one man who could have thrown it is the one who dropped it. That is the gospel in a gesture.

**Foreshadow of the cross.** This is the deepest layer for the disciple. Here the guilty woman goes free and is not condemned. At the cross the condemnation she and every sinner earned falls on the sinless One instead. He can say "neither do I condemn you" today because he is walking toward the day he will be condemned in her place. The stone he refuses to throw becomes the judgment he agrees to bear.

**A quiet guard against overclaiming.** No Reformed confession or catechism cites John 8:11 or John 3:17 as a proof text. The great confessions built the doctrine of Scripture, of Christ the Judge, and of free grace on undisputed texts. The house does not lean on this one paragraph. Nothing essential rides on it, which is exactly why we can read it with such calm honesty.

## Reaching the three-tier room

The contact points here are strong for teenagers: being exposed and shamed in public, being used by others to get at someone else, hypocrisy and pointing fingers, and mercy that reaches real guilt.

- **Searching student.** The floor is the shame. A person is dragged into the middle of a crowd on her worst day, used as a tool, and every hand is holding a rock. Then the only one with the right to judge her refuses to. Every searching student should leave able to find John 8 and say one sentence: they used a guilty woman to trap Jesus, and Jesus sent her accusers away and told her he would not condemn her. The point of contact is being exposed with no defense. Grace speaks first.
- **Churched but coasting.** Their mirror is the men with the stones. Religious, correct about the law, sure of the verdict, and walking out one by one when the light hits their own record. Press it gently with Romans 2:1: in passing judgment on another you condemn yourself. If your favorite thing about the Bible is how clearly it condemns other people, read this story again and find yourself in it, oldest first.
- **Maturing disciple.** Give them the weight on both tracks. On the text: Papias at 130 AD, the floating location, the clean 7:52 to 8:12 join, and why the doctrine of Scripture rests on the whole and not on one paragraph. On the content: Deuteronomy 17:7 under 8:7, the missing man against Leviticus 20:10 and Deuteronomy 22:22, Augustine on condemning the sin and not the man, and the line from "neither do I condemn you" to the cross where condemnation lands on him. Let them see that honest scholarship and deep worship are friends.

Keep faith content invitational and participation assignable. Every student can analyze the trap, the manuscript question, and the mercy. No student is required to profess it.

## Pitfalls with teenagers

- The antinomian misread. The biggest danger. A teenager will hear "neither do I condemn you" and stop there, landing on "Jesus doesn't judge, so anything goes." Augustine already answered it: he condemned the sin and told her to leave it. Always read 8:11 to its end. The mercy and the "sin no more" are one sentence.
- Using it to shame. The passage is a rescue from shame. Do not turn it into a lecture that re-shames the guilty student in the room. Christ lowered his eyes and cleared the crowd before he spoke to her. Teach it his way.
- The "never judge anyone" proof-text. The verse does not forbid all moral judgment. Jesus makes a judgment in it and calls sin sin. Matthew 7:1-5 corrects hypocritical judgment and ends by commissioning clear-eyed help ("then you will see clearly to take the speck out of your brother's eye"). Rule out the bumper-sticker reading.
- Textual honesty tipping into "so none of the Bible is reliable." Guard this hard and get ahead of it. The move from "this paragraph is disputed" to "so maybe it's all made up" has nothing under it. Make the opposite case out loud: the flag in the margin is evidence of care, the disputed passages are few and marked, and no doctrine turns on them. End the textual segment on trust.
- Prurience about her sin. The passage is a rescue from shame, and John does not dwell on the adultery. Name the sin once, plainly, and move to what Jesus does with it.
- Ignoring the missing man and the injustice. Do not skip 8:4. Leaving out the absent man hides the hypocrisy and the injustice that are half the point.
- Over-claiming or under-claiming the passage's authority. Do not preach it as though nothing were in question, and do not wave it off as a legend the church tacked on. Rule it the settled middle the sources give: very old, held by the church as a true event from Jesus' life, probably not part of what John wrote, safe and good to read.

## Also worth emphasizing

- Christ with nowhere to sleep (7:53-8:2). Everyone went to his own house while Jesus went to the Mount of Olives. He could not so much as borrow a place to lay his head, and he is back early in the morning to teach. A quiet contact point: the Lord who has nowhere to sleep is the one with mercy to spare in the morning.
- The word that empties a courtyard. This ties straight back to Unit 10's close, "no one ever spoke like this man" (7:46). There, his word disarmed the officers sent to seize him. Here, one sentence scatters a mob with stones in their hands. Same power, and a clean bridge from last unit.
- The eight-word gospel. "Neither do I condemn you. Go and sin no more" is grace and truth compressed to a single line. Say it slowly. It is much of the course in eight words.

## The single-lesson shape (light density)

The design goal is two honest treatments in one light period, neither rushed. Read the passage first, then take the textual note, then teach the content, giving the note and the content roughly equal time. Reading first lets students meet the story on its own terms and surfaces the question naturally, since the ESV bracket and footnote are right there on the page they just read. Mapped onto the 5-move template:

- Quiet time with the Lord (7 min). Standard open, rotating student host, prayer opt-in.
- Hear the Word (about 5 min). Read John 7:53-8:11 aloud, then have students find the bracket and footnote in their own ESV and read the note silently. First question, cold and simple: "What did you notice at the top of this story?" A student names the footnote, which hands you the textual segment.
- Work the text, front half, the textual note (about 13 min). Teach the note as a trust-builder. One governed question for the groups: "Your Bible tells you, right on the page, that the oldest copies do not have this story. Does that make you trust it more or less, and why?" Land the segment on trust. Keep the disciple-tier facts (Papias, the floating location) for the group that goes deep.
- Work the text, back half, the content (about 13 min). Move to the story. One governed sequence: the trap and the missing man (8:4-6), the stone (8:7), and the ending (8:10-11, "what are the two things Jesus says to her, and why both?"). Keep it light, one clean pass, cold-call checks, no lecture block.
- Land and minister (about 6 min, the protected pulpit). Grace and truth in one person (1:14). The only man with clean hands drops the stone. "Neither do I condemn you. Go and sin no more," the mercy first and the command as its fruit. For the disciple tier, one sentence: he can refuse to condemn her because at the cross the condemnation will fall on him.
- Respond (about 6 min, graded participation). In-room writing, theology coached and not scored. Prompt options: "Where in this story do you see yourself, the woman or the men with the stones, and why?" or "What is one thing you now know about how we got our Bible, and does it make you trust it more?" Let students keep it private if they choose.

## Memory: review only, no stretch verse

This unit plants no new graded verse. Students hold the six anchors they already carry: 20:31, 1:14, 1:12, 3:16, 4:24, and 6:35. Run a light cumulative review, and let 3:16 sit next to today's mercy.

Do not offer any line from this passage as an optional stretch verse, not even "neither do I condemn you; go, and from now on sin no more." The whole honest point of the unit is that these verses do not sit on the same manuscript footing as the rest of John, so handing students a disputed line to memorize would quietly undercut the lesson just taught. This differs from the earlier optional stretch verses (2:11, 5:24, 7:37-38), which are textually secure. The next new anchor is 8:12 in Unit 12, one lesson away. Point forward to it and plant nothing here.
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.7.53-8.11`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
