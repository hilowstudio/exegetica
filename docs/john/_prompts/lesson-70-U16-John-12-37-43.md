<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U16-L4-John-12-37-43.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["21 - An Unbelief Foretold (John 12-37-43).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 12:37-43.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.12.37-43] Teach John 12:37-43 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 12:37-43

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 70 of 150.
UNIT (use this exact name): U16 The hour has come.  LESSON WITHIN UNIT: 4/5.
PASSAGE: John 12:37-43.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24, John 6:35, John 8:12, John 10:11, John 11:25); the next new one comes in John 13:34-35 (Unit 18).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 12:1-50, "The hour has come" (Unit 16)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Five lessons with an unusual shape. L1 (Fri Dec 18) is a HALF-DAY recap and cumulative memory quiz, the last class before winter break, with no new John 12 exposition. The exposition of John 12 runs across the four full-length days, L2 through L5. L2 builds on sermon 18 (12:1-8) with fresh framing for the triumphal entry. L3 builds on sermons 19 and 20. L4 builds on sermon 21. L5 builds on sermon 22. This unit plants no new graded verse. Quote the ESV in the finished materials.

A word to set the room. John 12 is the last page of the Book of Signs. After 12:36 Jesus is hidden from the crowds, and from chapter 13 he is alone with the Twelve. Everything the course has tracked since Cana lands in this chapter. The hour that "has not yet come" at 2:4, 7:30, and 8:20 arrives at 12:23. The "lifted up" of 3:14 and 8:28 is completed at 12:32. The light of 8:12 is restated at 12:35-36 and 12:46. The King Nathanael named at 1:49 rides into Zion. The other sheep of 10:16 and the scattered children of 11:52 arrive as Greeks at the feast. Teach this unit as a gathering-in of the whole first half of the Gospel, and land it where John lands it, on a cross that draws a world.

## The christotelic center

The hour has come. From his mother's request for wine, Jesus lived on the Father's clock, and the appointment at the end of the clock was the cross. In John 12 the clock strikes. "The hour has come for the Son of Man to be glorified" (12:23), and John tells us what glorification means: he said this to show by what kind of death he was going to die (12:33). The center of the unit is that the glory of the Son is a cross, that the way up is the way down, that a buried seed is how a harvest comes, and that the Son lifted up from the earth draws a world to himself (12:32). The unit lands on Christ the crucified King, anointed for burial, entering Zion humble to die, glorified in being lifted up, whom Isaiah saw enthroned in glory seven centuries before the manger (12:41).

- L1 (half-day recap) lands on the whole Book of Signs, the Christ the seven signs and the "I am" sayings have shown, and John's stated aim (20:31).
- L2 (12:1-19) lands on Christ the King anointed for his burial, entering his city humble on a donkey to die.
- L3 (12:20-36) lands on Christ whose hour has come, the grain of wheat that dies to bear a harvest of the nations, lifted up to draw all to himself.
- L4 (12:37-43) lands on Christ whose glory Isaiah saw, rejected in a hardening foretold, sovereign over the unbelief that will crucify him.
- L5 (12:44-50) lands on Christ the light who came to save, whose word is the Father's word and will judge on the last day, holding mercy's door open with his last public breath.

## The contested points, ruled

**The anointing "for the day of my burial" (12:1-8).** Rule Mary's act worship shaped by faith in his coming death, and rule against flattening it into "give generously." Jesus reads her intent: she kept this perfume for the day of his burial (12:7). Mary, who watched her brother walk out of a tomb (Unit 15), pours out a year's wages because she believes this man is going to die and she will not miss her chance to love him while he is here. Sermon 18 is the frame: three people at the table, Lazarus reclining, Martha serving, Mary anointing, and the question under all three is how you see Jesus. How you see Jesus determines how you worship him. Judas is the counter-example. He objects that the money should have gone to the poor, and John strips the mask: Judas said this because he was a thief, not because he cared for the poor (12:6). Rule the lesson: worship poured out on the Christ who dies, love that counts him worth everything, over against a calculating heart that follows Jesus for what it can get. Teach the extravagance as the fruit of seeing him rightly, and keep the power in the Christ she has seen, never in the size of the gift.

**The plot to kill Lazarus (12:9-11).** Rule this the darkening backdrop that shows unbelief hardening into murder. The crowds come to see Jesus and the raised man, so the chief priests plan to kill Lazarus too, because many were believing on account of him (12:10-11). A living proof of resurrection is a problem to be erased. The greatest sign of life (Unit 15) now generates a second murder plot. Faced with a man raised from the dead, a hard heart plots another death.

**The Triumphal Entry (12:12-19).** Rule the crowd's welcome real and their expectation wrong. They shout "Hosanna! Blessed is he who comes in the name of the Lord, even the King of Israel!" (12:13), waving palm branches, a nationalist emblem, hailing a King they expect to throw off Rome. Jesus answers the expectation by the animal he chooses. He sits on a young donkey (12:14), and John cites Zechariah 9:9: your King is coming, seated on a donkey's colt (12:15). A king on a warhorse comes for battle. A king on a donkey comes in peace. He is a King, and he comes to die. Rule the disciples' delay a feature to teach: they did not understand at first, and after Jesus was glorified they remembered (12:16). Understanding came after the resurrection, in hindsight, by the Spirit, the same pattern the course met at 2:22 (Unit 3). Then rule 12:19 the hinge: the Pharisees say "the whole world has gone after him," an unwitting prophecy, and John immediately gives us the world, "now there were some Greeks" (12:20). Frame this scene fresh, no sermon covers it.

**The Greeks who come to see Jesus (12:20-22).** Rule these ethnic Gentiles, and rule their arrival the first light of the harvest of the nations. Sermon 19 settles it: not Hellenistic Jews, ethnic Greeks coming up to a Jewish feast and asking for Jesus. Tie it to 10:16 (the other sheep, one flock, Unit 14) and 11:52 (the scattered children gathered, Unit 15). The world has begun to come, and it triggers the hour.

**"The hour has come for the Son of Man to be glorified" (12:23).** Rule this the arrival of the hour the whole Gospel has circled. Jesus often said the hour had not yet come (2:4; 7:30; 8:20), and now it has, and the arrival of the Greeks marked it. Rule "glorified" defined by 12:33, the death he was going to die. The cross-references run to 13:31-32 and 17:1-5 (the glorification thread) and to Isaiah 49:5-6 and 53:10-12 (the Servant who is a light to the nations and sees his offspring). The hour is the cross, and the cross is the glory. Teach the paradox plainly: the throne of this King is a Roman cross, and being lifted up on it is how he is exalted.

**The grain of wheat (12:24), Christ's death first.** Rule the seed Christ himself, and rule his death the cause of all fruit. Unless a grain of wheat falls into the earth and dies, it remains alone, and if it dies it bears much fruit (12:24). Sermon 19 rules it: he is the grain of wheat. The cross-references confirm the direction: 1 Corinthians 15:36-38 (the seed sown and raised), Isaiah 53:10-12 (the Servant sees his offspring), Hebrews 2:9-10 (bringing many sons to glory), and John 12:32-33 (the fruit is the drawing of all). Guard the order. The fruit is you, and he had to go first. Rule against the flattening that makes 12:24 a general maxim about self-sacrifice. Christ dies first, and the disciple's death-to-self in 12:25 flows out of his, never alongside it. This is Marshall's order in a seed: holiness received from a death already died, before it is practiced.

**"Whoever loves his life loses it" (12:25).** Rule this the shape of the fruit, given to those already joined to his death by faith. Sermon 19 guards the sequence: 12:25 is not describing how you become fruit, it describes how fruit is borne once Jesus has died. Teach the call to die to self on the ground of the cross that already died for the sinner, never as the price of getting in. The engine is grace-first: you are the fruit because of what someone else did for you. Give the command of 12:25 plainly, and put Christ in their hands as its strength.

**"Now is my soul troubled" (12:27), the Gethsemane window.** Rule this John's own glimpse of the anguish the other Gospels show in the garden. The Greek is tarasso, to be stirred and thrown into turmoil, the same verb John uses of Jesus at Lazarus's tomb (11:33) and at the betrayal (13:21). Calvin grounds it: the trouble is real human feeling, voluntary and genuine, so that death was not a game to Christ but a real torment endured for us. Sermon 20 is blunt and right: the cross for your sin scared Jesus, and he trembled. Rule "Father, save me from this hour?" a real question refused: "But for this purpose I have come to this hour" (12:27). Then "Father, glorify your name" (12:28), and the voice from heaven answers. Rule the voice a genuine Trinitarian moment given for the crowd (12:30), the Father assuring the trembling Son. Keep both natures live: he genuinely feared, and he obeyed anyway, and that is the wonder.

**"Now the ruler of this world will be cast out" (12:31) and "lifted up... will draw all people to myself" (12:32-33).** Rule 12:31 the verdict of the cross on Satan and the world, and rule 12:32 the completion of the lifted-up thread, guarded from a universalist misreading. The Greek "lifted up" is hypsoo, which carries both senses at once, to raise physically and to exalt. The New Testament uses it of the cross at 3:14, 8:28, 12:32, and 12:34. One word holds the crucifixion and the exaltation together, one event at two heights. This completes the chain the course built from the bronze serpent (Unit 4) through the "I am" lifted up (Units 8 and 12). Now guard "draw all people" against universalism. The drawing is not of every individual, since not all come to Christ. It is the drawing of people from every kind, Jew and Greek, all nations, all sorts, the harvest of the buried seed, and it draws them effectually. The 1689 cites 12:32 for effectual calling: Christ calls to himself, by his word and Spirit, those the Father gave him. Teach it as the reach of the gospel to the whole world, the point the Greeks just triggered, never as a promise that every individual is saved.

**The unbelief foretold and the two Isaiah quotations (12:37-41), the hard one.** This needs the most care in the unit. Rule the judicial hardening and real human responsibility held together, exactly as John holds them, and neither denied. The plain fact first: though Jesus had done so many signs before them, they still did not believe (12:37). They saw and would not come. John then gives two Isaiah texts. First Isaiah 53:1, "Lord, who has believed what he heard from us?" (12:38), the Servant despised and rejected. Second Isaiah 6:10, "he has blinded their eyes and hardened their heart" (12:40). Rule the "could not believe" of 12:39 God's judicial hardening, and rule 12:37 and 12:42-43 the human responsibility standing in the same passage. Calvin guards it against fatalism: the prophecy does not lay a necessity on them, it foretells what the free unbelief of hard hearts would do, and faith is shown to be an uncommon gift of God. Teach it to sophomores as two true things spoken by the same John in one breath. They would not come (real guilt, 12:37). They could not come, because God gave hard hearts over to their hardness (real sovereignty, 12:39-40). Sermon 21 lands the gospel turn: God is utterly in control, he hardened to fulfill his purpose, and through the rejection of the Son the mercy went out to the nations, a remnant spared. Rule the disciple-tier note against arrogance: do not imagine you would have believed where they did not. The difference is grace, not merit.

**"Isaiah said these things because he saw his glory" (12:41), the deity.** Rule this a plain claim that the enthroned LORD Isaiah saw in the temple (Isaiah 6:1-5) was the Son. The cross-references tie 12:41 to Isaiah 6, and to John 1:14, 1:18, 5:39, and 14:9. The fathers are unanimous and rich. Aquinas: seeing the glory of the Son, Isaiah saw the glory of the Father, and of the whole Trinity. Augustine: the Son in the form of God is invisible as the Father is, and the deity Isaiah saw was seen in a symbolic way. This is a deity claim as strong as anything in the Book of Signs, on the same shelf as "before Abraham was, I am" (8:58, Unit 12) and "I and the Father are one" (10:30, Unit 14). The prophet saw Christ on the throne. Teach it as the capstone of the whole "who is this Jesus" argument the Book of Signs has been making.

**The secret believers (12:42-43).** Rule this a gentle, serious warning about fear of man, taught without shaming the frightened student. Many of the authorities believed in him, and because of the Pharisees they would not confess him, for they loved the glory that comes from man more than the glory that comes from God (12:42-43). The tradition is split on whether these had saving faith, and the passage leans (with 5:44) toward a belief that stopped short. Present the tension fairly and land it pastorally. The love of human approval can silence a real conviction, and Jesus asks to be confessed, not hidden. Handle it so a frightened teenager hears an invitation to speak, never a verdict that they are a coward.

**The final public appeal (12:44-50).** Rule this Jesus' last public words, a summary of his whole ministry, spoken to no one in particular because they are for everyone. Sermon 22 catches why John gives no setting: these words are for you. Rule the three claims. First, to believe in Jesus is to believe in the Father, and to see him is to see the Father (12:44-45), the deity restated. Second, he came to save the world, not to judge it (12:47), and the light comes so that no one who believes stays in darkness (12:46). Sermon 22's insight on "remain" is worth keeping: darkness is the starting position, and the light has to come to a heart that cannot light itself. Third, judgment is real and deferred: the word he has spoken will judge on the last day (12:48). Rule the two comings: he came first as the Lamb to save, he returns as the Judge, and the same word that saves now will judge then. Land the unit on the open door. Mercy's door is still open, the appeal is still going out, and the Christ who trembled at the hour holds it open with his last public breath.

## Christological and covenantal connections

- **The hour arriving as the hinge of the Gospel.** From 2:4 through 7:30 and 8:20 to 12:23, and on to 13:1 and 17:1. This unit is where the clock strikes.
- **The lifted-up / cross thread completed.** hypsoo at 3:14 (the serpent, Unit 4), 8:28 (Unit 12), and now 12:32, one word for crucifixion and exaltation.
- **The King of Zechariah 9:9.** The King Nathanael confessed (1:49) enters Zion humble on a donkey, a King of peace who comes to die.
- **The grain of wheat and the harvest of the nations.** The buried seed (12:24) tied to Isaiah 53:10-12 and 1 Corinthians 15:36-38. His death is the sowing that reaps a world.
- **The world coming in, the one flock.** The Greeks (12:20) as the firstfruits of 10:16 and 11:52, the New Covenant people of Jew and Gentile, drawn by the lifted-up Christ (12:32).
- **Isaiah seeing Christ's glory, the deity.** 12:41 reads Isaiah 6 as a vision of the Son enthroned, on the deity thread with 8:58 and 10:30.
- **The light thread.** 1:4-5 and 1:9 (Prologue), claimed at 8:12 (Unit 12), restated at 12:35-36 and 12:46.
- **The close of the Book of Signs.** 12:36-37 ends the public ministry. After this Jesus is alone with the Twelve (chapter 13 opens the Book of Glory). This unit sits on the seam of the whole Gospel.

## Reaching the three-tier room

The contact points are strong for teenagers: extravagant love, wanting a Jesus who fixes your politics or your problems, what you do with your one life, dying to self to bear fruit, honest fear of what following Jesus costs socially, and unbelief in the face of evidence.

- **Searching student.** The floor is Mary and the King on the donkey. A woman pours out a year's pay on a man's feet because she loves him and knows he is going to die (12:1-8). A King rides into the capital on a borrowed donkey, refusing the army the crowd wanted (12:12-15). Ask the plain question: do you want a Jesus who solves your problems and backs your side, or the real one, who came to die and asks you to follow him there? The grain of wheat is built for this student: a seed has to be buried before anything grows, and Jesus says that is what his death is, and what yours will be (12:24-25).
- **Churched but coasting.** Their mirror is Judas and the secret believers. Judas followed Jesus for what he could get and called real worship a waste (12:4-6). The leaders believed and would not say so, because they loved human approval more than God's (12:42-43). Press it gently: a person can be near Jesus for years, know the words, and run a quiet calculation the whole time. And press the harder mirror of 12:37, people who saw every sign and still would not come. Familiarity with the signs is not faith in the Christ they point to.
- **Maturing disciple.** Give them the weight: the hour chain from 2:4 to 12:23, hypsoo holding crucifixion and exaltation in one word (3:14, 8:28, 12:32), the tarasso window into Gethsemane (12:27), the two Isaiah quotations and the judicial hardening held with human responsibility (12:37-40), and the stunning 12:41 with the fathers on Isaiah seeing the Son's glory. Let them trace how the whole Book of Signs gathers into this one chapter and lands on a cross.

Keep faith content invitational and participation assignable. Every student can analyze the donkey, the seed, the two Isaiah texts, and the open door. No student is required to profess.

## Memory: review only

This unit plants no new graded verse. Students hold nine anchors: 20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25. The next new anchor is 13:34-35 in Unit 18. Keep the nine sharp across L2 through L5 with light cumulative passes, and let 10:11 (the shepherd who lays down his life) and 11:25 (the resurrection and the life) stand right behind "the hour has come to be glorified."

Offer John 12:24 as an optional stretch off the graded line, on L3, where the grain of wheat is taught: "unless a grain of wheat falls into the earth and dies, it remains alone, but if it dies, it bears much fruit." It is on the taught-not-memorized list, short, and it carries the unit's center. Keep it off the graded set, a gift for the student who wants to hold it.

**The L1 half-day cumulative memory quiz (Fri Dec 18, 26 min, last class before winter break).** This is a recap-and-quiz beat, no new John 12 exposition, a semester wind-down that celebrates what students carry.
- Recap the Book of Signs, briefly and warmly. Walk the arc in one sweep: the Prologue (the Word made flesh, 1:14), the seven signs (Cana 2:11, the official's son 4:46-54, Bethesda 5, the feeding and walking on water 6, the man born blind 9, Lazarus 11), and the "I am" sayings collected so far (bread 6:35, light 8:12, door and good shepherd 10:7 and 10:11, resurrection and life 11:25, plus the absolute "I am" of 8:58). Tie it to John's stated aim, 20:31, the first verse they learned. Frame it as "look how far we have come, and look who these signs have shown you." A window, not a lecture.
- Quiz the nine anchors (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25). Cumulative, low-stakes, celebratory.
- Grading: it is a graded cumulative memory quiz feeding the memory and quizzes bucket, consistent with the earlier half-day memory beat in Unit 6. Keep the recap portion formative and coached, off the grade.
- Tone: it is the last class before a long break. Send them out light, having proved to themselves that they hold nine load-bearing verses and the whole first half of John. A good place for a short blessing over the break.

## Pitfalls with teenagers

- The anointing moralized into generic generosity. The point is worship poured out on the Christ who dies, faith that counts him worth everything (sermon 18). Keep it about seeing Jesus rightly.
- The triumphal entry as a happy parade. The crowd wanted a political messiah and got a King on a donkey headed for a cross (Zechariah 9:9). Do not let it become a palm-waving celebration that misses that the King comes to die.
- "Grain of wheat" flattened to generic self-sacrifice. Christ is the seed, and he dies first (Isaiah 53:10-12). The disciple's death to self flows out of his death, never beside it. Guard the order or you reverse the gospel.
- "Draw all people to myself" read as universalism. Not every individual, but people of every kind drawn effectually (1689 on effectual calling). Teach the reach of the gospel to all nations, never that all are saved.
- The Isaiah hardening turned into fatalism, or into a denial of human responsibility. Hold both, as John does. They would not believe (12:37) and could not believe (12:39-40). Calvin: the prophecy foretells, it does not compel. Never "so why bother," and never a God who is not sovereign over hard hearts.
- The secret believers used to shame the fearful student. 12:42-43 is a gentle warning about the fear of man, aimed at a room that knows that fear. Handle it so the frightened teenager hears an invitation to speak, not a verdict.
- "I have not come to judge the world" (12:47) missing that the word judges on the last day. Both are true. He came to save, and his word will judge.
- Anti-Jewish reading of the unbelief. "The Jews" here names the hostile leadership in this scene. Jesus, the disciples, Mary, the believing crowds (12:11), and the many leaders who believed (12:42) are all Jewish. The hardening of 12:40 measures response to Christ, and it falls on any hard heart, including the churched student. Never let the class hear contempt for Jewish people.

## Also worth emphasizing

- 12:16 and understanding after glorification. After Jesus was glorified, they remembered. Following Jesus with things you do not yet understand is the normal shape of discipleship, the same note struck at 2:22. A warm word for the half-in student.
- The voice from heaven for the crowd (12:30). The Father speaks audibly, and Jesus says it was for their benefit. God stoops to give evidence to unbelief. A quiet mercy.
- "Remain in darkness" (12:46). Darkness is the default, and the light has to come to a heart that cannot light itself. Grace-first anthropology in one word.
- The chapter is a hinge, and students should feel it. L5 (12:36-50) is the last of the public ministry. After this, the crowds are gone and Jesus is with his own. Mark the seam so students know they are standing at the turn of the whole Gospel, from the Book of Signs into the Book of Glory.

## The lesson split

**L1 (i=67, Fri Dec 18, half-day 26), Book of Signs recap and cumulative memory quiz.** Recap the arc from the Prologue through Lazarus and run the graded cumulative quiz on the nine anchors, as detailed above. No new John 12 exposition. A warm semester wind-down before the long break. The exposition begins Jan 4.

**L2 (i=68, Mon Jan 4, regular 50), John 12:1-19: the King anointed for burial, entering Zion to die.** The anointing at Bethany and Judas's false concern (12:1-8), the plot to kill Lazarus (12:9-11), and the triumphal entry on the donkey of Zechariah 9:9 (12:12-19). Two narrative scenes bound by one idea: this King is going to his death, and he knows it, and he enters his city humble to accomplish it. Build on sermon 18 (12:1-8) and fresh framing for the entry (12:9-19). Lands on: Christ the King anointed for his burial, coming to Zion humble on a donkey to die.

**L3 (i=69, Tue Jan 5, regular 50), John 12:20-36: the hour has come, the seed that dies, lifted up to draw all.** The Greeks arrive and the hour strikes (12:20-23), the grain of wheat and the cost of discipleship (12:24-26), the soul troubled and the voice from heaven (12:27-30), the ruler cast out and the lifting up that draws all (12:31-33), and the light among them a little longer (12:34-36). This is the christological hinge of the unit, one continuous interaction. Build on sermons 19 and 20. Offer 12:24 as the optional stretch here, off the graded line. This is the densest day, so pace it as one arc and let it land on two verses, 12:23 and 12:32. Lands on: Christ whose hour has come, the buried seed of a world-harvest, lifted up to draw all to himself.

**L4 (i=70, Wed Jan 6, regular 50), John 12:37-43: the unbelief foretold, and Isaiah who saw his glory.** The rejection John foresaw (12:37), Isaiah 53:1 and Isaiah 6:10, the judicial hardening held together with real responsibility (12:38-40), the stunning "Isaiah saw his glory" (12:41), and the secret believers who loved human praise (12:42-43). The hardest theological material in the unit gets a full period so it is not rushed. Build on sermon 21. Handle the hardening pastorally and the deity of 12:41 as the capstone of the Book of Signs' argument. Lands on: Christ whose glory Isaiah saw, rejected in a hardening foretold, sovereign over the very unbelief that will crucify him.

**L5 (i=71, Thu Jan 7, Thursday 36, single-focus, last passage), John 12:44-50: mercy's door is open.** The final public words of Jesus, a summary of the whole ministry, spoken for everyone. One key question: "These are the last public words of Jesus in John. What is the one thing he most wants you to know before he goes silent to the crowds?" Work the three claims (to believe in the Son is to believe in the Father, he came to save and not to condemn, his word will judge on the last day), and land on the open door. Build on sermon 22. Lands on: Christ the light who came to save, whose word is the Father's and will judge on the last day, holding mercy's door open with his last public breath.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# An Unbelief Foretold (John 12:37-43)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 12:37-43

---

[00:00] So this morning, I confess to you, that we're walking through more hard stuff. More hard stuff. Right? And I'll put it on the table upfront that this hard stuff has been hard stuff that's so hard over the course of church history that the church splits up over it, new denominations are formed over it, people debate it, people argue over it, and and all of that to say that I'm not gonna stand up here and settle and solve all of that, in a in a single sermon. Right?

[00:28] What I'm gonna try to do this morning is what I'm called to do every week and present what the text says. And we're gonna trust in the Holy Spirit to help us navigate what the text is saying here, and you might find that I'm heavy on scripture this morning. I ought to be heavy on scripture every morning. But I want to allow the scriptures to speak here, to speak for me, to speak through me, and to speak to you, has to say to us. See, our gospel writer, John, he opened his account, if you remember, if you've been with us, all the way back in chapter one, with a declaration that the Christ, that the light came into the world, not that while the world was made through him, the world did not know him.

[01:15] That he came to his own and his own did not receive him. But to those who did receive him, he gave the right to become children of God. Right? So that we are opened in this gospel account with this declaration that the light was rejected. That the light was rejected by his very own.

[01:34] He opens with that. And here, as I've been saying for the last couple of weeks, we are coming to the end. We are at the dead end of the public ministry of Jesus Christ. This is it. Of the public ministry of Jesus Christ.

[01:43] This is it. After this, he's going to retreat and all the rest of his time will be spent with the 12 and then the 11 and then his passion week will come. Rise again, and we're gonna walk through all of that. But this is it, as far as the public ministry goes. And so, John had written in chapter one that this was coming, that the rejection of Christ, that he led with it.

[02:11] Is John including for us the reason, an explanation for the rejection of the Christ. Why did his own people reject him? Why did his own people not receive him? And this is attention that needs to be answered. I mean, let's read it.

[02:29] When Jesus had said these things, he departed and he hid himself from them. It says, and though he had done so many signs before them, they still did not believe in him. And they still did not believe in him. And we've gone left to right from chapter one all the way through this. So we we've read the signs.

[02:46] We know the signs. We saw him restore sight to the blind. We saw him raise Lazarus from the dead. We saw him multiply the fish and the loaves. We saw the signs, so many signs, although he did so many signs.

[03:01] John writes, still they did not believe in him, And he endeavors to answer, why? Why? And before we jump into it, I know that if you're anything like me, that as you're reading these signs of the savior as we go left to right through this gospel account, that there's a part of you that's like, if I was there, if I saw it, I would have believed. Or you look at the Israelites wandering in the desert. You're like, you show me a pillar of cloud and fire.

[03:34] I'm gonna believe. But there's an arrogance in it, right, that says that there's something about them that isn't true about you, that somehow you would have been given enough evidence able to find your way, climb your way, ascend your way into saving faith in God, in the Christ. And I wanna tear that down this morning as one to say that we are not different in and of ourselves from the Israelites in all of these accounts. We're not. There is something that makes you different.

[04:02] There is something that makes you different. I'm gonna close with it instead of stealing from the wrapping point. They saw all the signs. Tension. We want to answer like, why?

[04:26] Was it was there something deficient in Jesus? Did he not do enough? But he just he didn't, he didn't do enough. He didn't go far enough. He didn't show himself in the right ways at the right time to the right people.

[04:41] Was he not who we said he was? I mean, these are his people. If anyone should have believed it, should have been them. Right? Was it failure?

[04:58] Was it a plan? What was it? This is how he answers. Though he had done so many signs before them, they still did not believe in him so that the words spoken by the prophet Isaiah might be fulfilled. Lord, who has believed what he heard from us, and to whom has the arm of the Lord been revealed?

[05:38] Flip there in a minute. But I kind of want to put you guys in the room back in Luke chapter two. I'll I'll flip there for a second and just read it over you. You guys know the story if you, if your family does like the Christmas readings every year, where you kinda read about the birth of Christ. In Luke chapter two, we read the part of that story where we meet the man, Simeon.

[06:00] Anybody remember Simeon? Simeon was shown in the spirit that he would not die, that he would not see death until his eyes beheld the Messiah, that until his eyes beheld Christ. Isaiah chapter two down in verse 30 or 28 or so. This is what it says. It says that Simeon takes the child into his arms.

[06:21] So Mary brings Jesus into Jerusalem and Simeon, led by the spirit, is brought to the Christ in baby form. He takes him into his arms and he blesses God and he says in verse 29, Lord, now you are letting your servant depart in peace according to your word. For my eyes have seen your salvation, that you have prepared in the presence of all peoples, a light for revelation to the Gentiles, and for glory to your people, Israel. Amazing prayer. And his father and his mother, Mary and Joseph, marveled at what was said about Jesus.

[06:57] In verse 34, Simeon blessed them and said to Mary, his mother, Behold, this child is appointed for the fall and rising of many in Israel, and for a sign that is opposed. And a sword will pierce through your own soul also, so that thoughts from many hearts may be revealed. So at the birth of Jesus, the one carried in the spirit, Simeon, who was told, you will behold him with your own eyes, he declares in a blessing over Mary. And he says, listen, this this this trial, it is through him that many will fall and many will rise. He will be a sword even to your own soul.

[07:43] We know that Mary would come to faith, that his own mother would come to faith in him as her savior, as the messiah. And that he would be rejected. He would be rejected. From the beginning, this was understood. So we see it at his birth.

[08:02] We see it at the beginning of the gospel account of John. And here at the end of his public ministry se
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.12.37-43`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
