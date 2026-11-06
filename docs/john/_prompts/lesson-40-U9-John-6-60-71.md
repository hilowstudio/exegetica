<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U9-L7-John-6-60-71.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["09 - Who Will Eat the Bread of Life- (John 6-60-71).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 6:60-71.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.6.60-71] Teach John 6:60-71 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 6:60-71

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 40 of 150.
UNIT (use this exact name): U9 Bread of Life.  LESSON WITHIN UNIT: 7/7.
PASSAGE: John 6:60-71.  DAY TYPE: Regular (50 min) (use the matching variant).

UNIT MEMORY VERSE: John 6:35 (ESV) was planted earlier in this unit, in the passage where it appears. REVIEW it here. Do NOT re-plant it.
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 6:1-71, "Bread of Life" (Unit 9)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Seven lessons. L1 and L2 build on sermon 07 ("The Savior's Power," 6:1-21). L3 through L6 build on sermon 08 ("The Bread of Life," 6:22-59). L7 builds on sermon 09 ("Who Will Eat the Bread of Life?," 6:60-71). This unit plants the new graded anchor, John 6:35. Quote the ESV in the finished materials.

## The christotelic center

Jesus feeds a Passover crowd in the wilderness, walks to his disciples across the sea saying "It is I" (6:20), and then tells the crowd that hunts him down that he himself is the true bread God sends from heaven: whoever comes to him will never hunger, and whoever eats his flesh, given for the life of the world, has eternal life and will be raised at the last day. The unit lands on Christ as the bread of life (6:35), the true and greater manna (6:49-51), whose flesh given at the cross (6:51) is the food a sinner feeds on by faith and lives forever. It lands hardest at 6:35 and again at 6:51, where the bread becomes the crucified body given for the life of the world.

- L1 (6:1-15) lands on Christ who sees the crowd's hunger before they ask and provides in abundance, the true Shepherd-King who will not be seized on the crowd's terms.
- L2 (6:16-24) lands on Christ who walks to his own across the dark water and says "It is I; do not be afraid," the divine name spoken over their fear.
- L3 (6:25-29) lands on Christ the sealed Son of Man who gives the food that endures, received by the one work God requires, to believe.
- L4 (6:30-40) lands on Christ the bread of life, given by the Father to all the Father gives him, losing none of them.
- L5 (6:41-51) lands on Christ the living bread whom no one comes to unless the Father draws him, whose flesh is given for the life of the world.
- L6 (6:52-59) lands on Christ whose flesh and blood are true food and drink, fed on by faith, so that the one who feeds on him abides in him.
- L7 (6:60-71) lands on Christ who has the words of eternal life, confessed by Peter when the crowd walks away, sovereign even over his betrayer.

## The contested points, ruled

**The Passover note (6:4).** Rule it load-bearing, the interpretive key John hands us for the whole chapter. John dates the feeding, the sea-crossing, and the synagogue discourse to Passover (6:4; the discourse is "in the synagogue at Capernaum," 6:59). Sermon 08 builds the whole reading on this: Jesus deliberately reenacts the Exodus, leading a crowd into the wilderness, providing bread from heaven, at the feast that remembers the lamb whose blood turned the destroyer away. In each scene Jesus himself replaces an element of the feast. So 6:4 tells us to read the bread through the Exodus and toward the cross, where Jesus is the true Passover lamb (1:29, Unit 2; 19:14). Give the disciple tier the weight; give the whole room the plain point: the God of the Exodus is standing in the wilderness handing out bread.

**"Make him king by force" (6:15).** Rule it a true sight rejected in the wrong form. They were about to seize him and make him king (6:15), and Jesus withdrew alone. They saw something real: he is a king, and he can provide. They wanted the provision without the person, a bread-king to feed them and fight Rome. Sermon 07 states it cleanly: we do not make Jesus a king, he is the king. He refuses a throne the crowd builds for him because he is moving toward a greater throne, the cross. Teach the refusal as the same restraint the Cana signs showed (Unit 7): the deed points past itself to who he is, and he will not be reduced to useful.

**"It is I; do not be afraid" (6:20), and the walking on water.** Rule 6:20 an "I am" (ego eimi) that carries the divine name, and the walking on the sea a disclosure of who he is. Hold the continuity carefully. Unit 6 established the absolute "I am he" at 4:26. John 6 gives it again on the water (6:20) and then gives the first predicated "I am" in the synagogue (6:35, "I am the bread of life"). Do not re-explain the absolute sense; build on it. What sermon 07 presses is that John leaves out the calming of the storm the other Gospels record, so John's miracle is that Jesus gets into the boat: Jesus will do whatever he needs to do to get to you in your hour of need. The one who treads the sea (Job 9:8; Psalm 77:19) speaks the divine name over their fear and joins them in the trouble.

**"You seek me because you ate your fill" (6:26), the diagnostic.** Rule it Jesus reading the crowd's motive to the bone. Sermon 08 makes this the hinge of the discourse: there is a major difference between seeking Jesus as your treasure and seeking Jesus to get some lesser thing he gives. They chase the Bread-maker for more bread. This is the diagnostic that exposes the churched-but-coasting heart, and the door into everything Jesus says next.

**"The work of God is that you believe" (6:29), faith as the one work.** Rule it the end of works-righteousness. They ask, "What must we do to be doing the works of God?" (6:28), and Jesus answers that the work of God is to believe in the one he has sent (6:29). Sermon 08 reads it right: he moves the work off the people, puts it back on God, and says the work of God is that you would not work but would believe. The crowd wants a task; Jesus hands them a gift to receive. Teach the grace against their instinct, the instinct sermon 08 names, that no matter how often we hear salvation is free, our next words are "so what must I do?"

**The manna typology (6:31-33, 49-51; Exodus 16).** Rule the manna a real gift and a true type, fulfilled and surpassed in Christ. The crowd quotes "he gave them bread from heaven to eat" (6:31, from Psalm 78:24; Exodus 16). Jesus corrects the source and the substance: it was not Moses who gave the bread, but the Father gives the true bread from heaven (6:32). The manna fed the body and the fathers still died (6:49, 58); the true bread is a person who gives life that death cannot end (6:50-51). This is the covenantal spine of the unit: Christ is the antitype the manna shadowed. Deuteronomy 8:3 ("man shall not live by bread alone") is the seam Jesus is pulling. Teach the type plainly to the whole room and give the disciple tier the Exodus 16 backing.

**The sovereign-grace texts (6:37, 44, 65), taught without fatalism or coldness.** Be explicit and be glad, the way Unit 4 taught 3:8. Three statements: "All that the Father gives me will come to me, and whoever comes to me I will never cast out" (6:37); "No one can come to me unless the Father who sent me draws him" (6:44); "no one can come to me unless it is granted him by the Father" (6:65). The verb in 6:44 is a strong one, to draw or haul, and sermon 08 presses "drag." Guard it from coldness with Augustine, who read this verse for the room fifteen centuries ago: the mind is drawn by love, a person is drawn to Christ when they delight in him, not by necessity but by pleasure. God does not haul an unwilling captive to a Christ they hate. He gives the dead a new taste, and they come gladly. Teach it in this order:

1. Lead with the comfort in 6:37b: whoever comes is never cast out. That is the pastoral floor.
2. Then put the security under it. Your coming was the Father's gift, so it rests on him and not on your grip. Sermon 08's application lives here: your security in Christ's hand comes from the fact that you did not earn your standing with him in the first place.
3. Refuse fatalism from the passage itself. The same chapter calls people to come, look, and believe (6:35, 40, 47). Augustine again: you are not yet drawn? Pray that you may be drawn. The doctrine drives to prayer, never to "why bother."
4. For the anxious teenager: your job is to come to Christ, not to inspect the machinery of whether you were drawn. The proof you are drawn is that you come.

The Reformed confessions ground effectual calling on exactly these verses (6:44 in the Westminster Confession and the 1689, 6:37 in the same). Give the disciple tier the term: this is effectual calling, God's free and special grace.

**The big ruling: "unless you eat the flesh and drink the blood" (6:53-56).** Rule it primarily about feeding on Christ by faith, with a fair and real sacramental resonance. Defend it from the passage's own brackets.

- The internal argument is decisive. Jesus states the same result four ways, and the parallel settles the meaning. 6:40: everyone who looks on the Son and believes has eternal life and is raised at the last day. 6:47: whoever believes has eternal life. 6:54: whoever eats my flesh and drinks my blood has eternal life and is raised at the last day. Verses 40 and 54 carry the identical two-part predicate (eternal life now, resurrection at the last day). One says "looks and believes," the other says "eats and drinks." Same subject, same result, in parallel. To eat and drink is to come and believe. And 6:35 already fused them: coming to Christ is never hungering, believing in him is never thirsting.
- Jesus gives his own key at 6:63: "It is the Spirit who gives life; the flesh is no help at all. The words that I have spoken to you are spirit and life." A carnal, literal ingestion "is no help at all." The eating is Spirit-wrought and faith-received.
- Augustine says it in a sentence: to come to Christ is to believe in him, and "believe, and you have eaten." To have Christ by faith is to have eternal life.
- Calvin's answer to how one eats Christ's flesh is the Reformed line: union with Christ, received by faith, worked by the Spirit.
- Name the sacramental resonance fairly. The earliest voices heard the Supper here, and the language of flesh and blood, food and drink, and abiding (6:56) is the Table's own language, so the Lord's Supper is the appointed visible sign where believers feed on Christ by faith. The resonance is real. The primary meaning, set by the brackets, is feeding on Christ by faith.
- Rule out both errors. "You must take communion to be saved" is blocked by 6:47, spoken before any Table existed: the believer already has eternal life. Reducing it to nothing is blocked by the Table language itself. The Heidelberg Catechism (Q76) states the balance in a confession's own words: eating Christ is to embrace with a believing heart all his suffering and death, and so be united to his body by the Holy Spirit.

**The hard saying and mass defection (6:60-66).** Rule the defection the discourse working as intended, a sifting that reveals faith. "This is a hard saying; who can listen to it?" (6:60); "After this many of his disciples turned back and no longer walked with him" (6:66). Sermon 09 names it: the crowd was big until Jesus taught this, and once he teaches it, the crowd gets small. What offends is a Christ who says salvation is God's gift and not the crowd's achievement, and who gives himself as the only food. Teach it as the honest cost of following him, landing on the comfort of 6:37 (whoever comes is never cast out), and see the pitfall about not using it to frighten.

**"The words I have spoken are spirit and life" (6:63).** The interpretive key, ruled above. Add for the room: this is Jesus telling us how the eating happens. By the Spirit, through his words, received in faith. It answers the crowd's carnal literalism at 6:52.

**Peter's confession (6:68-69).** Rule it joyful surrender by those the Father has given. "Lord, to whom shall we go? You have the words of eternal life, and we have believed, and have come to know, that you are the Holy One of God" (6:68-69). Sermon 09 reads it as the answer of the sheep who hear his voice: we are in the camp you just said will come to you and never be let go. "Holy One of God" is a high confession. This is John's counterpart to the great confession, and it echoes the first-disciples call in Unit 2 (Andrew and Peter, 1:40-42).

**"One of you is a devil" (6:70-71, Judas).** Rule it Christ's sovereignty extending even over his betrayer. Sermon 09 gives two answers, both worth teaching: Jesus chose him so that Scripture would be fulfilled (Psalm 41:9; later 13:18; 17:12), and so we would see that no evil falls outside God's redemptive plan (Acts 4:27-28). The comfort is real and pastoral: if a Roman cross and a betrayer's kiss were folded into the plan that saved us, then the worst thing done to you or by you was foreseen and factored in. Guard it so it never becomes fuel for a teenager's paranoia about their own election (see the pitfalls).

## Christological and covenantal connections

**Jesus the true and greater manna (6:32-33, 49-51).** The manna of Exodus 16 was real bread from heaven and a true type, and the fathers who ate it died (6:49). Christ is the bread the manna pointed to, the bread one eats and does not die (6:50). Ground it in Exodus 16, Psalm 78:24-25, and Deuteronomy 8:3. This is the unit's covenantal spine: the antitype has come.

**The feeding as a Passover sign pointing to the cross (6:4, 51).** The Passover date (6:4) and the flesh "given for the life of the world" (6:51) make the bread point to Calvary. Let the Lamb of God (1:29, Unit 2), the Passover at the temple (2:13, Unit 3), and the cross at Passover (19:14) shake hands here. Christ is the true Passover lamb, and his body is the bread.

**The first predicated "I am" and the "I am" thread.** 6:35 is the first "I am ___" with a predicate in the Gospel, and the discourse repeats it (6:35, 41, 48, 51). It opens the thread that runs to the light of the world (8:12, the next new anchor in Unit 12), the door and the shepherd (10:9, 11), the resurrection and the life (11:25), the way (14:6), and the vine (15:1). Distinguish it from the absolute "I am" of the divine name (4:26 in Unit 6, and 6:20 on the water). John 6 gives both registers in one chapter.

**The Father-draws grace running back to 3:8 and 5:21.** The sovereign wind-Spirit of the new birth (3:8, Unit 4) is now the sovereign Father who draws (6:44). The Son who gives life to whom he will (5:21, Unit 8) is now the bread who loses none the Father gives (6:39). And the fourfold "I will raise him up at the last day" (6:39, 40, 44, 54) ties straight to the two resurrections of 5:25-29 (Unit 8).

**Peter's confession echoing the first-disciples call (Unit 2).** The men who first heard "come and see" (1:39, 46) now say, when the crowd leaves, "to whom shall we go?" (6:68). The same Andrew who brought his brother to Jesus (1:41-42) is the one who finds the boy with the loaves (6:8-9). Faith in John has a floor you enter and a ceiling it grows toward, and Peter is standing on the growth.

## Reaching the three-tier room

Points of contact are strong: hunger and what fills it, following Jesus for what he gives or for himself, teachings hard enough to make people quit, and staying when it costs.

- **Searching student.** The floor is hunger. Jesus feeds thousands from a boy's lunch, then says he himself is the bread, and whoever comes to him is never hungry again (6:35). Every searching student should leave able to find John 6 and say one sentence: Jesus fed a crowd, then said he is the real food, and the way you eat is to come to him and trust him. The contact point is that everyone is hungry for something that food, screens, approval, and winning never fill.
- **Churched but coasting.** Their mirror is the crowd chasing the Bread-maker for more bread (6:26). Press sermon 08's diagnostic gently: when you come to Jesus, are you coming for what he gives or for him? Then let the hard saying land (6:60, 66). A student running on the benefits of church meets a Christ who asks to be the treasure, and the question is whether they stay when he stops being merely useful.
- **Maturing disciple.** Give them the weight: the sovereign-grace texts (6:37, 44, 65) and effectual calling, the by-faith ruling on 6:53-56 defended from the brackets at 6:35, 40, 47, and 63, the manna typology out of Exodus 16, the two "I am" registers, Peter's "where else would we go," and Judas held inside Acts 4:28. Let them trace how a wilderness picnic becomes the deepest self-disclosure of the chapter.

Keep faith content invitational and participation assignable. Every student can analyze what Jesus claims and how the crowd reacts. No student is required to profess it.

## The memory verse, John 6:35 (this unit's new plant, taught on L4)

Plant and teach it on L4, inside 6:30-40 where the verse lives and where the manna question produces it. ESV: "Jesus said to them, 'I am the bread of life; whoever comes to me shall not hunger, and whoever believes in me shall never thirst.'"

The fresh angle: this is the first time in the Gospel Jesus says "I am" and finishes the sentence with what he is. Two pairs of words unlock it, and Augustine unlocked them. "Comes to me" and "believes in me" name the same act: coming to Jesus is believing in him. "Shall not hunger" and "shall never thirst" name the same promise: the eternal fullness where there is no want. So the verse is one claim said twice. Come to Jesus and be filled forever. Lead with grace: the bread is given (6:32-33), and even the coming is the Father's gift (6:37, 44). Nobody earns the bread. You receive it, the way the wilderness crowd received loaves they did not grow. Tie it back to the anchors students already hold: 3:16 (the love that gave the Son), 4:24 (worship the Father the Spirit enables), and 20:31 (that by believing you may have life). This is the same life-word carried through Units 7 and 8, now with a name: the bread.

The other six lessons do not plant, teach, or quiz 6:35 as the graded verse. On those days keep the five earlier anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24). The next new anchor after this is 8:12 in Unit 12.

## Pitfalls with teenagers

- Turning the feeding into a "share your lunch" morality tale. The boy's loaves matter because Jesus multiplied them, not because the boy was generous. It is a sign of Christ the true bread, taught as a window on who he is.
- Making the sovereign-grace texts cold or fatalistic. Lead with 6:37b (never cast out) and Augustine's "drawn by delight." God gives the dead a new taste and they come willingly. Answer "why bother" with the same chapter's call to come and believe (6:35, 40, 47), and with "pray that you may be drawn."
- Sacramental over-reading of 6:53-56 into "you must take communion to be saved." Blocked by 6:47: the believer already has eternal life. Hold the by-faith ruling.
- Under-reading 6:53-56 into nothing. The flesh-and-blood, food-and-drink, and abiding language is the Table's own, so the Supper is the appointed sign of this feeding. Name the resonance fairly (Heidelberg 76).
- Using the mass defection to scare kids into staying. Fear does not regenerate (Unit 4's rule stands). Teach 6:66 as the sifting that reveals the Father's gift, and land on the comfort of 6:37. Peter stays because he has tasted the words of life.
- Prosperity misreads of the bread. Sermon 07 guards this out of Adam's own account of a frightening pregnancy where God got in the boat without fixing the storm, and sermon 08 with the warning that we reduce Jesus to useful. The bread is Christ himself, and the sign points past the meal to the Giver. Cross before crown.
- Anti-Jewish readings of "the Jews" grumbling (6:41, 52). "The Jews" names the grumbling hearers in this scene. Jesus, the Twelve, the boy, and the whole fed crowd are Jewish. The grumbling deliberately echoes the wilderness generation who grumbled at the manna (Exodus 16:2-9), so it is a covenant-family failure John holds up as a warning. No contempt for Jews. The warning lands on every heart that receives the bread and grumbles.

## Also worth emphasizing

- The twelve baskets (6:13). Twelve disciples, twelve baskets left over. Sermon 07 presses the payoff: Christ's provision is not used up in serving others, and he feeds the servants after they feed the crowd. A gift for the student in service, and the receive-then-give pattern of the Christian life.
- "It is I; do not be afraid" (6:20). The miracle John keeps is that Jesus gets in the boat, present in the trouble before the trouble is fixed. Pastoral gold for the anxious teenager, and the clearest single beat in L2.
- "I will raise him up at the last day," four times (6:39, 40, 44, 54). The refrain of resurrection hope threaded through the discourse. The bread of life gives life that death cannot end. Tie it to 5:28-29 (Unit 8).
- The wilderness generation and the crowd. John frames the Passover crowd as the new Exodus generation who receive bread and grumble. They ask for a sign after the sign, they demand manna from the one who is the true manna. For the disciple tier, this is how John reads the whole chapter through Exodus 16.
- The exclusivity that comforts (sermon 09). A God who chooses is uncomfortable until he is your comfort. The particular, by-name love that set its affection on you before you existed is the thing every teenager is actually hungry for. Let that be the warmth under the hard doctrine.

## The seven-lesson split

The seams cut on the text's own movements and on John's own structural hinges (the grumbling at 6:41, the dispute at 6:52). The feeding stays whole, 6:35 lands cleanly and completely in one regular lesson, and the Thursday gets the tightest single-focus passage.

- **L1 (i=34, Tue Oct 27, regular 50), John 6:1-15: the feeding of the five thousand.** The crowd, the boy's five barley loaves and two fish, the abundance, the twelve baskets, and the refusal to be made king by force (6:15). Keep the sign whole. Build on the first half of sermon 07: Jesus sees the hunger before they ask, provides in abundance, and will not be seized as a bread-king. Set the Passover frame (6:4) and the Exodus backdrop here as the setup for the whole unit. Lands on: Christ the true Shepherd-King who provides, the God of the Exodus in the wilderness.

- **L2 (i=35, Wed Oct 28, regular 50), John 6:16-24: walking on the water.** The disciples on the dark, rough sea, Jesus walking to them, "It is I; do not be afraid" (6:20), the boat reaching land, and the crowd realizing the next day that he crossed without a boat (6:22-24), which sets up the hunt. Build on the second half of sermon 07: the miracle is that Jesus gets in the boat, and "It is I" is the divine name over their fear. Teach the "I am" at the disciple tier as the bridge from the absolute "I am" (4:26, 6:20) to the predicated "I am" coming in 6:35. Lands on: Christ who walks to his own in the storm and joins them in it.

- **L3 (i=36, Thu Oct 29, Thursday 36, single-focus), John 6:25-29: why are you looking for me?** One tight passage for the short day, one key question: "Are you seeking Jesus for what he gives, or for himself?" The finding (6:25), the diagnostic (6:26), "do not work for the food that perishes" (6:27), and the one work God requires, to believe (6:29). Build on the opening of sermon 08 and its contrast between treasuring Jesus and using him. Land it grace-first on 6:29, faith as the gift. This passage does not contain 6:35, keeping the anchor off the short day. Lands on: Christ the sealed Son of Man who gives the food that endures, received by faith.

- **L4 (i=37, Fri Oct 30, regular 50), John 6:30-40: I am the bread of life. Plants and teaches John 6:35.** The demand for a sign (6:30), the manna quotation and its correction (6:31-33), "give us this bread always" (6:34), the declaration "I am the bread of life" (6:35), and the Father's giving and keeping (6:37-40). The full regular period the new anchor deserves, and the verse lands inside the flow that produces it. Teach the manna typology (Exodus 16; Deuteronomy 8:3) and plant 6:35. Introduce 6:37 as the first of the three sovereign-grace texts, grace-first. Lands on: Christ the bread of life, given by the Father to all the Father gives him, losing none.

- **L5 (i=38, Mon Nov 2, regular 50), John 6:41-51: no one comes unless the Father draws him.** The grumbling of the crowd (6:41-42, John's own hinge), "No one can come to me unless the Father who sent me draws him" (6:44), "they will all be taught by God" (6:45, Isaiah 54:13), and the turn to the cross, "the bread that I will give for the life of the world is my flesh" (6:51). Build on the sovereign-grace core of sermon 08 (the "draw," the security of the given). Carry the full "how to teach election without fatalism" section here, guarded with Augustine's "drawn by delight." Land the flesh-given-for-the-world on the cross (the Passover frame from L1). Lands on: Christ the living bread, drawn to by the Father, given for the life of the world.

- **L6 (i=39, Tue Nov 3, regular 50), John 6:52-59: eat the flesh, drink the blood.** The dispute (6:52, John's second hinge), "unless you eat the flesh of the Son of Man and drink his blood, you have no life in you" (6:53), true food and true drink (6:55), and abiding (6:56). The big-ruling lesson. Carry the ruling in full: feeding on Christ by faith, defended from 6:35, 40, 47, with the sacramental resonance named fairly (Heidelberg 76). Set up 6:63 as next lesson's key. Lands on: Christ whose flesh and blood are true food and drink, fed on by faith, so the believer abides in him.

- **L7 (i=40, Wed Nov 4, regular 50), John 6:60-71: the hard saying, and where else would we go.** "This is a hard saying" (6:60), the key "It is the Spirit who gives life; the flesh is no help at all. The words that I have spoken to you are spirit and life" (6:63), the defection (6:66), Peter's confession (6:68-69), and "one of you is a devil" (6:70-71). Build on sermon 09. Teach the defection as sifting, land on Peter's "to whom shall we go," and handle Judas with sermon 09's two answers (Scripture fulfilled, and no evil outside God's plan, Acts 4:28), guarded from teenage paranoia. Lands on: Christ who has the words of eternal life, confessed when the crowd walks away, sovereign even over his betrayer.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# Who Will Eat the Bread of Life? (John 6:60-71)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 6:60-71

---

[00:00] Just wanna welcome you guys again this morning, and especially just acknowledge the dads in the room. Happy Father's Day to you if you're a father in this room. You know, somebody said to me, at some point that the voice of a father becomes the inner voice of a child. I don't know how true it is. I believe it to be, in part, true.

[00:22] But if it's true, that's surely a heavy burden. Right? And who can bear it? Certainly, I know that I don't want necessarily for my voice to be the dominant inner voice of my children. Right?

[00:35] And yet, I kinda wanna say to you guys this morning, to all the fathers in the room, firstly, that the Lord sees you, That each time that you represent the good and perfect voice of your father in heaven to your children, he sees you, and he celebrates over you the kingdom work that you are doing in your children. But way more importantly than that, I want you to hear this morning, dads, that every time that you fail to do that, every time that your voice does not reflect the perfect voice of the father in heaven, that because of Jesus, you are perfectly covered, perfectly spotless, perfectly forgiven. And your children, in all the ways that you will fail them, their father in heaven never will. And you have that assurance from him. So happy Father's Day to you.

[01:20] And to each of you this morning who are grieving, either the father you didn't have, the father that you've lost, the father that you wish you were. I also just want to offer you the comfort this morning before we get started that on this Father's Day, your father in heaven looks on you with the light and offers himself to you perfectly to be your great comforter. And I pray that this morning, as we look at him together, that we would each enter into that rest. Okay? You know, I remember a story that a good friend of mine up in Chicago told me.

[01:54] He said that, when he was nine or 10 years old, that his dad took him to a sporting event of some kind. And that, when they were in the bathroom at this venue, that he did or said something embarrassing to his father. And his father responded to his buddies, whose kid is this? Surely not my kid. Harmless enough.

[02:16] Right? But somehow, these words went directly into the heart of my friend. And for fifty years, these words stayed with him. All these other parts of his life indicating to him that he's just one misstep away from being disowned or unselected, deselected by the people who love him. And so forty ish years later, 50 years old, seeking to resolve this distress within him, he goes to his father to make peace over this sentence that was spoken all those years ago.

[02:52] And understandably, his dad had no recollection that he'd ever said any such thing. Right? You see, this is the nature of our relationship to our fathers, our relationship with one another, that we were created to desire belonging. You see, we were created as an outflow, as an overflow of the love that eternally existed between God the Father, God the Son, and God the Holy Spirit. Forever, they have loved one another perfectly.

[03:22] They have experienced perfect belonging forever. And when you and I were created, we were placed on this earth, created in the image of God, is what is written in Genesis. That we were made in his image, both male and female. We were made in his image. And this means not just to look like him, but to participate with him in the ways that he participates with himself.

[03:44] That we, as created beings reflecting the image of God, would dwell with him and enjoy him forever. A sense of true belonging. Right? We were made for this and it's why we yearn for it. And it's why when these things are broken in our human relationship, it's why we feel them so deeply, and it's why also we need our father in heaven so much to be that for us because it's what he designed us to need.

[04:12] And so if you're experiencing that more this, that, this morning, if you're needing that this morning, just know that you're joining me in needing that this morning, that you're joining the world in needing that this morning. And this morning, I have named today's sermon, did I not choose you? These are the final words of Jesus in this interaction. And I'm praying that as we work our way through it, that we are going to find peace and comfort in the truth that our God from eternity past looked upon you and chose proactively to set his care and affection and saving grace upon you, chose to adopt you very specifically. Now, over this is kind of the end cap, the third message in a series of sermons, three sermons, to kind of walk us through the bread miracle.

[05:00] Right? I told you guys we were going to preach it in three segments. That segment one, we were going to look at the miracle itself. Segment two, we were going to look at the response of the crowd. And segment three, today, we're going to look at the response of the disciples.

[05:13] And in segment one, looking at the miracle, when Jesus was brought the bread and the fish, and he multiplied it to feed the 5,000 plus the women and children, who ate? Who did he multiply the loaves and the fish for? Everybody. Right? Everybody ate.

[05:31] The whole crowd ate. And in the same way, just as the sun shines on the skin of all people on earth today, and just as a cool breeze passes over to alleviate the warmth on that same skin for all people today, our God stands ready to pour out his common grace on all men. He is extending his hand of care and invitation and love to the whole earth. But then last week, we saw a smaller group, a subgroup of that crowd, hop on boats and chase him to Capernaum in order that they might ask him for more. And last week, we looked at his interaction with that group, and he said some really hard things to them.

[06:05] In fact, this morning's message, when we look at the response of the disciples, begins with when many of his disciples heard it, they said, this is a hard saying. Who can listen to it? So let's stop and remember what he said. He said really four things last week to the crowd. The first thing that he said is that all who the Father gives to me will come to me.

[06:26] That's the first thing Jesus said. The second thing he said is that all who come to him, he will never cast out. In fact, it is the will of the father that he should not lose a one that he has given to him. The third thing he said is that no one can come to Him unless the Father draws Him. And the fourth thing that He said is that this new life that you are invited into comes by eating His flesh and drinking His blood, that you must receive Him, receive His broken body and his shed blood to be enter to enter into eternal life.

[07:02] These were these these were the four teachings of last week. And as Jesus taught this to the c
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.6.60-71`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
