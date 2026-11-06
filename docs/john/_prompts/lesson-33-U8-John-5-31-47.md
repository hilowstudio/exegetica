<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U8-L5-John-5-31-47.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["06 - The Savior\u2019s Authority (John 5-18-47).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 5:31-47.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.5.31-47] Teach John 5:31-47 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 5:31-47

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 33 of 150.
UNIT (use this exact name): U8 Sign 3 & the Son's authority.  LESSON WITHIN UNIT: 5/5.
PASSAGE: John 5:31-47.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24); the next new one comes in John 6:35 (Unit 9).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 5:1-47, "Sign 3 and the Son's authority" (Unit 8)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Five lessons. The discourse lessons (L3, L4, L5) build on Adam's sermon 06, "The Savior's Authority" (John 5:18-47). The Bethesda healing and Sabbath conflict (5:1-17) have no paired sermon, so frame those fresh. Quote the ESV in the finished materials.

## The christotelic center

Jesus heals a man who has been down for thirty-eight years, does it on the Sabbath on purpose, and when they come to kill him for it he answers with the highest claim in the Gospel so far: the Son does everything the Father does, holds the Father's own power to give life and to judge, and is owed the honor owed to God (5:19-23). The unit lands on Christ as the Son who shares the Father's authority over life and death, the one to whom every witness points and about whom Moses wrote (5:39, 46), so that hearing his word and believing is to cross over from death to life now (5:24) and to rise to life at the last day (5:28-29).

- L1 (5:1-9) lands on Christ who comes to the man no one helps and gives by his word what thirty-eight years and a pool could not.
- L2 (5:10-18) lands on Christ who calls God his own Father and works the Father's work, equal with God (5:18).
- L3 (5:19-23) lands on Christ the Son, equal with the Father in work, in giving life, in judgment, and in honor.
- L4 (5:24-30) lands on Christ who raises the spiritually dead to life now by his word and will raise all the dead at the last day.
- L5 (5:31-47) lands on Christ to whom John, the works, the Father, and the Scriptures all testify, the one Moses wrote of.

## The contested points, ruled

**The textual note at 5:3b-4 (the angel stirring the water).** Rule it almost certainly not original. The words about the sick "waiting for the moving of the water" and all of verse 4 (the angel who stirred the pool, the first one in healed) are missing from the earliest and best manuscripts and read as an early explanatory gloss added to account for verse 7. The ESV drops verse 4 to a footnote, so a sharp student will see the jump from verse 3 to verse 5. Tell them why, plainly. The man's own words in 5:7 still mention the stirred water, so the belief about the pool is old and real, and John reports the man's hope in it without vouching for the angel-mechanics. Turn the footnote into a teaching moment: we can trust our Bible because scholars track every line like this, and nothing in the passage hangs on the pool's reputed magic. Jesus heals with a word and never touches the water.

**"Do you want to be healed?" (5:6).** Rule it a real, desire-drawing question, aimed to expose helplessness and awaken hope. The verb is plain wanting. Chrysostom reads it as Christ showing the man's perseverance, and Cyril calls it proof of Christ's goodness, that he does not wait to be begged. The question lands on the man's answer, "I have no one" (5:7). He has no helper, no claim, no way in. Then grace walks up and asks if he wants it. Teach it as Christ drawing out a hopeless man, never as Christ scolding him for lying there.

**The man's character (given his report in 5:15).** Rule him an ordinary sufferer healed by sheer grace, and refuse to make him a villain or a hero. He never asks Jesus for healing, does not know who healed him (5:13), offers no confession of faith, and when Jesus warns him in the temple he tells the authorities it was Jesus (5:15). John does not tell us his motive, so we do not either. The restraint is the teaching. This healing lands on a man with no faith-credentials at all, which guards the grace-first frame: Jesus gives before the man believes, knows, or thanks. Plant a quiet contrast with the man born blind in chapter 9, who grows louder in confession the more they press him (a later payoff). The Bethesda man is the picture of grace to the undeserving. Do not moralize his silence or his report in either direction.

**"Sin no more, that nothing worse may happen to you" (5:14), and the sin-and-suffering link.** Rule out "your sickness was your sin," and guard it hard for teenagers. Jesus links sin and a worse outcome, and the "something worse" is judgment, not another illness. Suffering entered the world through sin in general (the whole race under the Fall), and Jesus himself blocks the individual-scoreboard reading three chapters later: the man born blind sinned neither himself nor his parents (9:3). Hold both. Suffering came into the world through sin, and this man's thirty-eight years were not a tally of his private guilt. The warning is that a healed body is a small thing next to an unhealed soul, and worse than paralysis is to stand before the Judge unforgiven. Teach the seriousness. Refuse the cruelty of telling a sick teenager their illness is God's punishment.

**"My Father is working until now, and I am working" (5:17), and equality (5:18).** Rule it a claim to divine prerogative that the hearers understood correctly. Jesus does not argue the Sabbath law away. He argues that healing is the Father's own work and the Son does it alongside him. The Jewish reasoning the sermon reconstructs is sound and worth teaching: God rested on the seventh day, yet God plainly sustains the world every Sabbath, feeds the birds, holds the stars, so God works on the Sabbath, and no one else may. By taking the Sabbath as his own working day, Jesus takes the place only God holds. John tells us they heard it right. They sought to kill him because "he was even calling God his own Father, making himself equal with God" (5:18). The word for "equal" is the same one Paul uses in Philippians 2:6, Christ "equal with God." This is the interpretive key to the whole discourse, and where the sermon opens.

**"The Son can do nothing of his own accord" (5:19), dependence and equality together.** Rule both, and hold them in one breath, because the verse does. The Son can do nothing by himself "but only what he sees the Father doing," and in the same sentence, "whatever the Father does, that the Son does likewise" (5:19). The first clause is the Son's perfect unity with the Father, never a solo act, never out of step. The sermon presses this as intimacy: by the love between the Father and the Son, the Father shows the Son all that he is doing. The dependence is the proof of the equality. A rival god would act on his own. The true Son does only and exactly what the Father does, including raising the dead (5:21) and judging (5:22). Teach dependence and equality as one claim.

**The two resurrections in 5:25-29.** Rule two distinct raisings, marked by John's own time-stamps. In 5:25 the hour "is coming, and is now here," when "the dead will hear the voice of the Son of God, and those who hear will live." The "and is now here" makes this present, the spiritual raising of the dead-in-sin to new life through Christ's word, already happening in his ministry. In 5:28-29 the hour "is coming" with no "now," and the scope widens to "all who are in the tombs," who come out to "the resurrection of life" or "the resurrection of judgment." That is the future, bodily, universal resurrection at the last day. The sermon reads it exactly this way, the already and the not yet. Anchor the bodily half in Daniel 12:2. Teach both clearly. The believer is raised twice, once now from spiritual death, once at the end from the grave.

**The fourfold witness (5:31-47).** Rule four witnesses to Jesus, given because their own law required more than one (Deuteronomy 19:15, which Jesus is invoking at 5:31): John the Baptist, "a burning and shining lamp" (5:33-35); the works the Father gave him to accomplish (5:36); the Father himself (5:37-38); and the Scriptures (5:39-40). Note for the disciple tier that the discourse calls the deeds "works" (erga, 5:36) rather than "signs," so the Bethesda healing is Exhibit A in the works that witness. This is where the sign and the discourse tie together.

**"You search the Scriptures... it is they that bear witness about me" (5:39), and Moses as accuser (5:45-47).** Rule 5:39 a rebuke of a Bible reading that misses its own subject, and rule Moses their accuser rather than their defense. These are the most careful Bible readers alive, and Jesus says they read for eternal life and walk right past the One the words are about. The christotelic hinge is here: Jesus says Moses "wrote of me" (5:46), so the man they hope in is the man who accuses them, because they took his books and missed his subject. This is the Emmaus-road reading in Jesus' own mouth before Emmaus: "beginning with Moses and all the Prophets, he interpreted to them in all the Scriptures the things concerning himself" (Luke 24:27). Teach 5:39 as the danger of knowing the Book and missing the Lord of the Book. Guard it (see the pitfalls) so it never becomes a club against students who study.

## Christological and covenantal connections

**Shared authority to give life and to judge.** The Father "has life in himself," and "so he has granted the Son also to have life in himself" (5:26). The Son gives life "to whom he will" (5:21) and holds "all judgment" (5:22), "because he is the Son of Man" (5:27), the Daniel 7:13-14 figure given everlasting dominion. The Reformed confessions gather this: the Westminster Confession, the 1689, the Savoy, and the Heidelberg Catechism all cite 5:22 for Christ as the appointed Judge to whom all power and judgment is given by the Father. The life-giving and the judging are one authority, both the Father's own, handed to the Son so that "all may honor the Son, just as they honor the Father" (5:23).

**The whole Old Testament witnessing to Christ (Luke 24, the christotelic reading).** This is the covenantal spine of the unit and the payoff of the course's method. Moses wrote of Christ (5:46), the Scriptures testify of Christ (5:39), and the risen Jesus says the same on the Emmaus road (Luke 24:27, 44). For the disciple tier, this is where the whole covenantal frame becomes Jesus' own claim: the promise, the type, the shadow, all of it was pointing here. The prophet like Moses (Deuteronomy 18:15) has come.

**Life now and resurrection to come.** The believer has already "passed from death to life" (5:24) and will be raised bodily at the last day (5:28-29). Tie this to the life-word carried from Unit 7. There the boy "will live" (4:50, 53); here "those who hear will live" (5:25), and the word John threaded to "that by believing you may have life in his name" (20:31) reaches its fullest statement. The assurance texts the whole course leans on gather here (5:24; John 3:36; Romans 8:1; John 10:27-30).

**Ties back to the deity claims of Units 1 and 3.** The Word who "was God" (1:1) and through whom "all things were made" (1:3) now claims the Father's own working (5:17) and the Father's own honor (5:23). Let the Prologue's deity and this chapter's equality shake hands.

## Reaching the three-tier room

The points of contact are strong: chronic suffering, a long wait, rule-keeping that misses the person, the question of who Jesus thinks he is, and reading the Bible while missing its point.

- **Searching student.** The floor is L1. A man has been sick for thirty-eight years, longer than most of their parents have been alive, and nobody helps him into the water. Jesus walks up, asks if he wants to be well, and heals him with one sentence. Every searching student should leave L1 able to find John 5 and say one thing: Jesus healed a man nobody else would help, by his word, and asked nothing of him first. The point of contact is the long wait and the helplessness. Grace reaches first.
- **Churched but coasting.** Their mirror is the opponents in the back half. A person can know the Bible better than anyone in the room, keep every rule, and stand face to face with Jesus wanting him gone. Press the sermon's edge gently: a person can read Scripture for years and walk past the One it's about (5:39). Then hand them 5:24 as relief. The one who hears and believes has already passed from death to life, settled.
- **Maturing disciple.** Give them the weight: "equal with God" at 5:18 against Philippians 2:6, the dependence-and-equality of 5:19, the two time-stamped resurrections in 5:25 and 5:28, the works (erga) that witness (5:36) tying the sign to the discourse, the fourfold witness on Deuteronomy 19:15, and the Luke 24:27 christotelic claim under 5:39 and 5:46. Let them trace how a Sabbath healing becomes the highest self-disclosure in the Gospel so far.

Keep faith content invitational and participation assignable. Every student can analyze what Jesus claims and how John builds the case. No student is required to profess it.

## Memory: review only

This unit plants no new graded verse. Students keep the five anchors they already hold: 20:31, 1:14, 1:12, 3:16, and 4:24 (planted in Unit 6). The next new anchor is John 6:35 in Unit 9. Assign nothing from chapter 5 to the graded memory line and quiz nothing new. Run a light cumulative review, and let 20:31 ("that by believing you may have life in his name") sit next to 5:24, since 5:24 is the same promise at full strength.

Offer John 5:24 as an optional stretch off the graded line, on L4 where it lives: "Truly, truly, I say to you, whoever hears my word and believes him who sent me has eternal life. He does not come into judgment, but has passed from death to life." It is short, it carries the assurance heart of the whole discourse, and it is already on the taught-not-memorized list. Keep it off the graded set. It is a gift for the anxious student, not another line to fail.

## Pitfalls with teenagers

- Blaming the sick for their sickness (from 5:14). The big one. Do not let a student walk out thinking illness is God's punishment for their sin. The "something worse" is judgment, and 9:3 blocks the private-scoreboard reading. Teach the seriousness of sin without weaponizing suffering.
- Making the Sabbath conflict into "rules are bad." The opponents were not wrong to guard the Sabbath, and their fence of prohibited works was a real attempt to honor God. Jesus breaks it on purpose to reveal who he is. The issue is that they had the rules and missed the Lord of the Sabbath standing in front of them.
- Turning the resurrection and judgment discourse into fear-leverage. The two resurrections and "the resurrection of judgment" (5:29) are sober, and the passage's own answer to the fear is 5:24: no judgment for the one who hears and believes. Lead with the rescue held out in the same breath as the danger. Never fear as the engine of faith.
- Abstracting the authority discourse into theology-class material with no pulse. The temptation with 5:19-30 is a whiteboard on the Trinity. Keep it a person making a claim that forces a verdict. The sermon's frame is the antidote: Jesus makes you either kill him or worship him, with no "good teacher" exit. Teach the doctrine as a claim aimed at the student.
- Anti-Jewish readings of the opponents. "The Jews" in John names the hostile leadership in this scene, not a people or a race, and Jesus, the healed man, and every early witness are Jewish. Do not let the class hear contempt for Jews. The warning of 5:39-44 lands on every careful Bible reader who misses Christ, which includes the churched student in the room.
- Using 5:39 to bash people who study the Bible. The rebuke is not "stop studying." These men studied hard and Jesus never faults the study. He faults reading the Scriptures for life while refusing to come to the Life they point to (5:40). Aim it at the heart that knows the words and will not come to the Word, and keep it off the diligent student who is doing what this course asks.

## Also worth emphasizing

- The "truly, truly" (amen amen) stacked three times in the discourse (5:19, 24, 25). John's road sign for bedrock. Jesus stakes his authority on what follows each time. Name it once so students hear the weight.
- The sermon's three questions are the teaching spine for the discourse. Is Jesus God (5:19-23). What happens when we die (5:24-30). Does how we lived have anything to do with it (the witnesses, answered by faith in Christ alone). Map L3, L4, and L5 onto those three.
- "The record of your deeds or the record of Christ's deeds." The sermon's sharpest line for the churched student quietly banking on teamwork with Jesus. On the last day one of two records is read over each person, and the only difference is whether they received Christ or came on their own merit. This is the grace-first center of the back half, and it belongs in L5. Guard it from curdling into "so try harder to believe." The merit is Christ's alone.
- Jesus slips away (5:13). He heals and disappears into the crowd, no audience, no credit. The Bethesda healing has no theatrics, the same restraint the Cana signs showed in Unit 7. The deed points past itself to the person.
- The Father-first note carried from Unit 7. The Son can do nothing by himself and seeks "not my own will but the will of him who sent me" (5:19, 30). This is the same Father-first frame the last unit built on, now on Jesus' own lips. The perfect Son lives entirely from the Father, and by union with him so do we.

## The five-lesson split

The seams cut on the chapter's own movements (sign, conflict and charge, the Son's equality, life and resurrection, the witnesses), keep 5:19-30 whole, and put the whole witness section on its own day. The two internal discourse seams (5:23/24 and 5:30/31) map onto the sermon's three questions. Each lesson lands on Christ, and the loads fit the day types.

- **L1 (i=29, Tue Oct 20, regular 50), John 5:1-9: the man who could not get to the water.** The feast, the pool, the thirty-eight-year invalid, "Do you want to be healed?", "I have no one," and the bare-word healing, "Get up, take up your bed, and walk." A full period on the sign itself. Frame this one fresh, no sermon covers it. Handle the 5:3b-4 textual note honestly and the "Do you want to be healed?" question as Christ drawing out a hopeless man. End on "Now that day was the Sabbath" (5:9) as the turn into L2. Lands on: Christ who comes to the man nobody helps and gives by his word what thirty-eight years could not.

- **L2 (i=30, Wed Oct 21, regular 50), John 5:10-18: the Sabbath, the temple word, and the claim that gets him killed.** The challenge over the carried mat, the man who does not know who healed him, Jesus finding him in the temple ("Sin no more, that nothing worse may happen"), the man's report (5:15), the persecution, and the hinge, "My Father is working until now, and I am working" (5:17), heard as "making himself equal with God" (5:18). Carry the two pastoral cruxes here (the sin-and-suffering guard on 5:14, the man's character on 5:15) and land the deity claim at 5:17-18, where sermon 06 opens. Lands on: Christ who calls God his own Father and works the Father's work, equal with God.

- **L3 (i=31, Thu Oct 22, Thursday 36, single-focus), John 5:19-23: the Son does what the Father does.** One tight passage for the short day, one key question: "What is Jesus claiming about himself, and does he leave us the option of calling him only a good teacher?" The dependence-and-equality of 5:19, the life-giving (5:21), the handing over of all judgment (5:22), and the equal honor (5:23). Build on the first movement of the sermon and its trilemma, no middle ground, worship him or reject him. Lands on: Christ the Son, equal with the Father in work, in giving life, in judgment, and in honor. (The sermon's first question, "Is Jesus God?")

- **L4 (i=32, Fri Oct 23, regular 50), John 5:24-30: life now, and the resurrection to come.** The gold verse 5:24 (hear, believe, passed from death to life, no judgment), the hour "now here" and the spiritual raising (5:25), the Son with life in himself and authority to judge as Son of Man (5:26-27), the hour "coming" and the bodily resurrection to life or judgment (5:28-29), and the summary, "I seek not my own will but the will of him who sent me" (5:30). The two-resurrections ruling lives here. Build on the second movement of the sermon, the already and the not yet. Offer John 5:24 as the optional stretch verse on this lesson, off the graded line, and run the light cumulative review of the five anchors. Lands on: Christ who raises the dead to life now by his word and will raise all the dead at the last day. (The sermon's second question, "What happens when we die?")

- **L5 (i=33, Mon Oct 26, regular 50), John 5:31-47: the witnesses, and the one Moses wrote about.** The fourfold witness (John, the works, the Father, the Scriptures, 5:31-40), the diagnosis (you do not have the love of God, you receive glory from one another, 5:41-44), and Moses the accuser (5:45-47). Build on the third movement of the sermon and its verdict, that we stand on Christ's record or our own. Land the christotelic capstone here: the whole Old Testament testifies to Christ (5:39, 46; Luke 24:27), the unit's payoff and the course's method in Jesus' own words. If the period runs short, 5:31-40 (the four witnesses) is the load-bearing half and 5:41-44 can compress. Lands on: Christ to whom every witness points, whom you must come to for life. (The sermon's third question, answered by faith in Christ alone.)
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# The Savior’s Authority (John 5:18-47)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 5:18-47

---

[00:00] Church, we took a short break from the gospel account of John last week in order that pastor Michael would preach that beautiful farewell sermon to us, and I pray that you were blessed in that. So I'll take a minute and remind you how we got where where we got. It's important because if we don't, then this is gonna fall, and we're gonna miss some things. Okay? Last week or two weeks ago rather, we kinda left off in the gospel account with the story of Jesus hearing healing that paralytic, at the pool in Bethesda, if you were here.

[00:26] Jesus goes up to a man who had been paralyzed for many years, who was seeking healing, and he just says to him, you wanna be healed? Yes, you do. Take up your bed and walk. And this paralytic gets up, and he picks up his bed, and he starts walking. Right?

[00:40] And and and at this point, the Jews say to him, it is not lawful for you to take up your bed. And this paralytic who is miraculously healed, who's carrying his bed says back to them, well, the one who healed me, that man said to take up your bed and walk. So they asked him, who is this man who said to you to take up your bed and walk? And he didn't know. And later in the temple, Jesus sees him and says, look, you're well.

[01:02] Go and sin no more that nothing worse may happen to you. Declaring over him that you've received temporal temporary healing for a far lesser issue, that you need healing for your spirit, for your soul, that you need healing for sin. The man, now knowing who it was that healed him, runs and tells the Jews, hey, it was Jesus. And so it says there at the end that this was why the Jews were persecuting Jesus because he was doing these things on the Sabbath. But Jesus answered them, my father is working until now and I am working.

[01:39] So this is how the last sermon in in our sermon series kinda ended up. I want you guys to hear some things in order that we could set the stage correctly. The first is that when Jesus healed the man, he told him, take up your bed and walk. So if we don't know the context, then we can miss it. That in Orthodox Judaism, the Sabbath was to be observed in 39 different ways.

[02:01] They had a code book that they called the Mishnah, and they had 39 different ways that you were to observe the not working part of the, of the Sabbath day. And so number one of the list of 39 ways that you were to not work on the Sabbath was you were not to carry stuff. Number one, don't carry stuff. And in particular, they said, you're not to carry things from one domain to another. So to carry something from your from your inside your home to outside your home was to violate the Sabbath.

[02:30] In the city of Jerusalem, they literally drew lines in order to delineate how far you could walk before you could think I've just carried something from one domain to another. Okay? So to perfectly obey, rule number one of the Sabbath was to carry nothing. Carry nothing, and I mean trivial things, like you can't carry your keys in a handkerchief. Right?

[02:50] That would be perfect obedience to the Sabbath, but you're especially not supposed to carry things across the domain. So when Jesus says to the paralytic, take up your bed here on the Sabbath and walk, he is inviting him and telling him to violate rule number one that the Jews had written around the Sabbath. And so he invites controversy by doing that. And he gets the controversy that he was seeking. And so the Jews then charged the man, it is not permissible for you to be doing this.

[03:17] He says, well, Jesus told me to do it. So they go to Jesus and it says all the more they were persecuting him because he violated the Sabbath. Well, these Jews who really cared about getting the Sabbath right, they wrote the 39 things. They really thought through what does work mean in order that we may not do it. They reasonably asked the question, does God have to obey the Sabbath?

[03:40] And this sounds funny, but it's a good question to ask. Does the God who instituted the Sabbath require it of himself? This God who rested on the seventh day, does he work on the Sabbath? And they rightly concluded, yes. God works on the Sabbath.

[03:54] The God who by the power of His word upholds all things, who is feeding the birds, we know each morning, the God who sustains all things. He doesn't take a day off on the Sabbath. God can work on the Sabbath. But no one else can work on the Sabbath. And so Jesus, knowing this, creating this controversy, setting up this moment where they come and they charge him, they persecute him for doing these things on the Sabbath, Jesus said to them, I know that only God can work on the Sabbath.

[04:24] That's why I'm working. This is the earliest kind of direct direct statement that Jesus makes that where he likens himself to God. My hope as we walk through these words from Jesus, every word in today's passage are directly from Jesus's mouth. And it's a long passage. I'm gonna try to get through in a reasonable time, but we're reading it all in one bit and going through all in one bit because they heard it all in one bit.

[04:49] This is one interaction with Jesus, so we want to hear all his words together. So Jesus has set up this interaction and they're charging him, only God can work on the savage. And Jesus says, that's right. That's why I'm My father is working until now, and I am working. Verse 18 starts our passage this morning, that this was why the Jews were seeking all the more to kill him, because not only was he breaking the Sabbath, but he was even calling God his own father, making himself equal with God.

[05:24] Now, I'm hoping that by looking at directly at Jesus's words this morning, that we're going to be able to answer three questions. We're gonna let Jesus answer for himself three questions. Now, question number one that we're gonna see, if Jesus can answer for himself here is, is Jesus God? Is Jesus God? We need to let him answer that for himself.

[05:43] The first thing is that Christianity kind of lives and dies on the claim that Jesus is himself God. It's where we part ways with most other world religions. Right? Whether you are a Mormon or a Muslim or a or a Jew or a Latter day Saint. Right?

[05:58] Like you don't believe that either Jesus is God or that he is equal with the father. Right? But what Christians uniquely claim is that Jesus is himself God equal with the father. Not that's true unless Jesus made that claim of himself. Right?

[06:18] And there have been charges, like the world has made charges that this these were things that people started saying about Jesus later, but he never intended for us to understand him that way, to see him that way, or whatever. And so we need to let Jesus speak for himself. And here, Jesus, who created the controversy on purpose, creates this interaction, has people cha
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.5.31-47`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
