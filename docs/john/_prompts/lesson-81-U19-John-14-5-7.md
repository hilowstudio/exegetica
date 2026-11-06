<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U19-L2-John-14-5-7.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["23 - The Way, The Truth, and The Life (John 14-1-11).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 14:5-7.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.14.5-7] Teach John 14:5-7 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 14:5-7

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 81 of 150.
UNIT (use this exact name): U19 The way to the Father.  LESSON WITHIN UNIT: 2/8.
PASSAGE: John 14:5-7.  DAY TYPE: Regular (50 min) (use the matching variant).

UNIT MEMORY VERSE: John 14:6 (ESV). This lesson's passage contains it. PLANT it here as this unit's one new graded verse and teach it fresh. It is the only new verse this unit.
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 14:1-31, "The way to the Father" (Unit 19)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Eight lessons inside the Farewell Discourse, three of them built on paired sermons: 23 "The Way, The Truth, and The Life" (14:1-11), 24 "Ask." (14:12-14), and 25 "I Will Not Leave You" (14:15-31). This unit plants the new graded anchor, John 14:6, the fifth predicated "I am." Quote the ESV in the finished materials.

## The christotelic center

Christ himself is the road home. The night before he dies, Jesus steadies frightened friends by handing them not a map to the Father but his own person: the way, the truth, and the life (14:6), the exact showing of the Father (14:9), the one who goes through the cross to prepare their place and comes back to carry them to it (14:2-3), and the one who sends another Helper so that he stays present with them by the Spirit (14:16-18). The unit lands on Christ the only way to the Father, opened by his death, who does not leave his own as orphans. It bookends on comfort: "let not your hearts be troubled" opens the chapter (14:1) and closes it as "peace I leave with you" (14:27).

- L1 (14:1-4) lands on Christ the trustworthy one who goes through the cross to prepare a place and returns to carry his own home.
- L2 (14:5-7) lands on Christ himself as the only road home to the Father. Plants 14:6.
- L3 (14:8-11) lands on Christ one with the Father, the Father made visible, whose works testify.
- L4 (14:12-14) lands on Christ ascended to the Father, extending his work through the church by the Spirit and answering prayer for the Father's glory.
- L5 (14:15-17) lands on Christ who asks the Father and gives the Spirit to make obedience the fruit of love.
- L6 (14:18-24) lands on Christ who does not abandon his own but with the Father makes his home in them.
- L7 (14:25-27) lands on Christ who secures his church's memory of him by the Spirit and hands his own peace to frightened people.
- L8 (14:28-31) lands on Christ the Son, equal with the Father and ordered under him in mission, going sinless and willing to the cross.

## The contested points, ruled

**Troubled hearts and the Father's house (14:1-3).** Rule 14:1 the frame for the whole chapter and the bookend with 14:27. "Let not your hearts be troubled. Believe in God; believe also in me" (ESV). The fear is rational. It sizes up a real situation, a betrayal, a denial, a coming crucifixion, and Jesus answers by moving their eyes off the circumstances onto himself, "believe also in me." Rule the "many rooms" (14:2) as dwelling with Jesus in the Father's presence. The Greek for rooms (monai) comes from the verb to remain or abide, and the same word returns at 14:23 as the "home" the Father and Son make with the believer. The point is a permanent place with him, sealed by 14:3, "that where I am you may be also." Rule "I will come again and will take you to myself" (14:3) as Christ's return to gather his own, the homecoming he prepares by going through the cross first. Guard against literal real estate. The treasure is being with Jesus, and the rooms of 14:2 and the home God makes in the believer at 14:23 are the same picture seen from both ends.

**"I am the way, and the truth, and the life. No one comes to the Father except through me" (14:6), the plant.** Rule three things and hold them together. First, the way is a Person, and he says it to comfort a scared friend. Thomas admits he is lost, "we do not know where you are going. How can we know the way?" (14:5), and Jesus does not hand him directions, he hands him himself. Ignatius said it plainly, that the way is unerring, namely Jesus Christ, and this way leads to the Father. Second, the exclusivity is comfort and it is total. Teach both halves of the sentence as one thing. One true way home means there is a way home, and it is open, which is the kindest news there is if it is true. The confessions ground the exclusivity: since the fall there is no salvation except in the mediation of Christ alone (1689 22.2), and men outside Christ cannot be saved in any other way whatsoever, be they never so diligent (Westminster). The wider witness stacks up on the same point: Acts 4:12, Ephesians 2:18, 1 John 5:11-12. Third, this is the fifth predicated "I am," standing in the line students already hold: bread (6:35), light (8:12), door and good shepherd (10), resurrection and life (11:25), and now the way. See the memory-verse section for how to teach it fresh, and the pitfalls section for both guardrails.

**"Whoever has seen me has seen the Father" (14:8-11).** Rule this the deity thread from 1:18 and 12:45 reaching its clearest single line. Philip asks to see the Father, and Jesus answers that seeing him is seeing the Father, "because I am in the Father and the Father is in me" (14:10-11). Calvin reads the seeing as the manner of revelation, God fully made known in Christ, so that his goodness and wisdom and power are visible in the Son. This is Jesus as the truth about God, the correction of every false picture of the Father a student carries. Rule "believe on account of the works themselves" (14:11) the fallback rung Jesus offers, the same move as 10:37-38 and 12:37-38. The works to look at are Calvary and the empty tomb.

**The "greater works" (14:12).** Rule these greater in scope and reach, the worldwide harvest of the church through the Spirit after Jesus goes to the Father. The commentators on file rule scope rather than spectacle, near unanimously: JFB (the conversion of thousands in a day by his Spirit), Gill (not greater in nature and kind, but more in number, in all the world), Clarke (the immense multitudes brought to God by the apostles), Henry (greater victories by the gospel). The engine is stated in the verse itself, "because I am going to the Father," which sends the Spirit. Adam's sermon 24 makes it concrete: the boring works were the bread and the healings, and a bread factory outdoes the feeding of the five thousand. The great works are foot-washing and disciple-making, the church gathering more people across more nations and centuries than Jesus's own earthly ministry did. Guard against a name-it-claim-it misreading, since the verse aims every work at the Father's glory (14:13).

**"Whatever you ask in my name, this I will do" (14:13-14).** Rule "in my name" as praying according to Christ's character and will, on the ground of who he is, aimed at the Father's glory. The verse carries its own purpose clause, "that the Father may be glorified in the Son" (14:13). Adam's sermon 24 is the model here. To pray in his name is to come on the standing of the Son who reigns, who passed through death, who sealed our approval with his blood, and the one caveat the text names is the Father's glory. His warning against tacking "in Jesus' name" onto a prayer as a cheat code is exactly the guard the room needs. Guard hard against magic-formula and prosperity readings.

**"If you love me, you will keep my commandments" (14:15).** Rule this the fruit of love and the grace-first order, love first and obedience flowing, tied straight to the new command of 13:34 the previous unit planted. Read the verse as a promise as much as a command, "you will," with the power supplied by the Helper given in the very next breath (14:16). This is Marshall's order exactly, holiness received in union before it is practiced, obedience as the fruit of a heart persuaded it is loved. Guard against reading obedience as earning salvation.

**The first Paraclete promise, "another Helper" (14:16-17).** Rule this the key point of the unit and the one Unit 17 asked the course to hold. Jesus asks the Father, who gives "another Helper, to be with you forever, even the Spirit of truth" (ESV). The word "another" (allos parakletos) means another of the same kind, and the fathers rule it precisely this way. Gregory of Nazianzus: he is called "another" Comforter so that you might acknowledge his co-equality, a name of equal lordship, not of inequality. Ambrose adds that "another" also keeps the Son and the Spirit distinct. Rule the Spirit a Person with a job. Adam's sermon 25 keeps him concrete: the Spirit dwells with them now and will be in them, and his ministry always magnifies Christ, so that when you try to look at the Spirit you end up seeing Jesus. Guard against making the Spirit vague or spooky. Rule "I will not leave you as orphans; I will come to you" (14:18) Christ's real presence with his own through the Spirit, the answer to feeling alone or abandoned.

**The indwelling, "we will come to him and make our home with him" (14:23).** Rule this the triune indwelling, Father and Son by the Spirit making their home (mone, the same root as the rooms of 14:2) in the one who loves and keeps Christ's word. Judas, not Iscariot, asks why Jesus shows himself to them and not to the world (14:22), and the answer is love and the word kept, the mark of those in whom God dwells.

**"He will teach you all things and bring to your remembrance" (14:26).** Rule this the ground of the apostles' witness, and through them the Gospel we hold. The Helper the Father sends in Christ's name teaches the eleven and reminds them of everything Jesus said. This is the promise standing behind John's own book.

**Peace "not as the world gives" (14:27).** Rule this the bookend with 14:1, Christ's own peace handed to men about to watch him die, a settled peace the world cannot manufacture or match. Sermon 25 closes the chapter here on purpose, reading 14:27 back over the frightened room.

**"The Father is greater than I" (14:28), the hard one.** Rule this the Son's subordination in role and mission, the sent one in his incarnate humiliation. It is never a lesser deity. Hold it together with "I and the Father are one" (10:30, Unit 14's anchor) and the equality of 5:18. The pre-Nicene fathers rule it exactly here, and Alexander of Alexandria, writing against Arius, is the anchor: in this alone is the Son inferior to the Father, that he is not unbegotten, for he is the very exact image of the Father, in nothing differing from him. Cyprian catches the pastoral point Jesus is actually making, that the disciples should rejoice at his going, "if you loved me, you would have rejoiced, because I am going to the Father." The ordered relation shows across the canon: 1 Corinthians 11:3, Philippians 2:6-11, John 20:17. Guard hard against Arianism. Rule 14:30, "the ruler of this world is coming. He has no claim on me," as Christ's sinlessness, Satan finds nothing in him he can hold. Rule 14:31, "rise, let us go from here," his willing march to the cross out of love for the Father, "so that the world may know that I love the Father."

## Christological and covenantal connections

- **Jesus the only way to the Father, opened by his death.** 14:6 with Acts 4:12, Ephesians 2:18, and the sole-mediator language of the confessions.
- **The Son who reveals the Father exactly.** The deity thread from 1:18 and 12:45 now at 14:9-11, standing on the "I am" progression: bread (6:35), light (8:12), door and good shepherd (10:7-11), resurrection and life (11:25), the way (14:6), with the vine (15:5) next.
- **The Spirit promised.** The living-water thread from 7:39 (Unit 10) now named as the Paraclete (14:16-17, 26). The Spirit is how Jesus keeps his word, "I will come to you" (14:18).
- **Love then obedience.** Tied to the new command of 13:34, powered by the Helper (14:15-16). Marshall's order, the tree made good and then the fruit.
- **The peace of Christ (14:27)** as a new-covenant gift, his own peace, bookending the troubled hearts of 14:1.
- **The Father and the Son, one in essence (10:30; 5:18) and ordered in mission (14:28).** The Father sends, the Son obeys and is sent, the Spirit is given by both.

## Reaching the three-tier room

The contact points are unusually strong, because this is a dying man steadying scared friends.

- **The searching student.** Fear and a troubled heart (14:1). Wanting to know the way when you do not (Thomas, 14:5). Whether there is really only one way to God (14:6). Feeling alone or abandoned (14:18, "orphans"). A peace the world cannot give (14:27). The plain question: who talks like this the night before he is killed, and keeps comforting the very people about to run.
- **The churched but passive student.** Seeing what God is actually like (14:9), against a secondhand or scary picture of the Father. Unanswered prayer and what "in my name" really means (14:13-14), against praying at the wall and tacking on a formula. The Spirit as a Person with a job (14:16-17, 26), against a vague force.
- **The maturing disciple.** The weight of allos parakletos and the Spirit's co-equality (Gregory of Nazianzus). The greater works as the church's worldwide harvest (14:12 with the commentators). "The Father is greater than I" held with "I and the Father are one" (14:28 with 10:30, Alexander of Alexandria). The triune indwelling of 14:23. Let them trace how one conversation holds the way, the Father, the Spirit, obedience, peace, and the cross.

Keep faith content invitational and participation assignable. Every student can analyze the "I am," the two guardrails on 14:6, the Paraclete's job description, and the ruling on 14:28. No student is required to profess.

## The memory verse, John 14:6 (this unit's new plant, on L2)

Plant and teach it on L2, inside 14:5-7, where Thomas's question produces it and the verse gets a full regular period with room. ESV: "Jesus said to him, 'I am the way, and the truth, and the life. No one comes to the Father except through me.'" Three fresh moves.

The way is a Person, and he says it to comfort a scared friend. Thomas admits he is lost. Jesus does not hand him directions, he hands him himself. Ignatius: the way is unerring, namely Jesus Christ, and this way leads to the Father. The picture for the room: the difference between being handed directions and having Someone come and carry you there.

The exclusivity is the kindest news there is, if it is true. Teach the whole sentence. One true way home means there is a way home, and it is open. Acts 4:12 and Ephesians 2:18 give the room the wider witness.

This is the fifth predicated "I am." Set it in the line students already hold: bread (6:35), light (8:12), door and shepherd (10), resurrection and life (11:25), now the way (14:6), and tell them the vine (15:5) comes next, in Unit 20.

The other seven lessons do not plant, teach, or quiz 14:6 as the graded verse. Keep the ten prior anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35). The next new anchor is 15:5 in Unit 20.

## Pitfalls with teenagers

- **14:6 flattened into intolerance.** Cut Thomas and the comfort, and it becomes a weapon. Keep it a word spoken to steady a frightened friend, and keep it tender.
- **14:6 softened into "all roads are fine."** Delete the second half of the verse and it collapses. Teach "No one comes to the Father except through me" plainly and warmly.
- **"Greater works" read as more spectacular miracles.** The commentators rule scope, the worldwide harvest through the Spirit. Adam's bread-factory point makes it stick.
- **"Greater works" read as name-it-claim-it.** The verse aims every work at "that the Father may be glorified in the Son" (14:13). Christ builds his Father's kingdom.
- **"Ask in my name" as a magic formula or a prosperity promise.** It means praying according to his character and will for the Father's glory. Adam's warning against the tacked-on "in Jesus' name" cheat code is the corrective.
- **"The Father is greater than I" read as Jesus being a lesser God.** This is subordination in role and mission, held with 10:30 and 5:18. Alexander of Alexandria against Arius is the anchor.
- **The Paraclete made vague or spooky.** Teach the job: another of the same kind, the Spirit of truth, who abides forever, teaches, reminds, and magnifies Christ.
- **"Keep my commandments" read as earning salvation.** Love comes first, the Helper supplies the power, obedience is the fruit. Guard the closing so grace praised at the top does not turn into self-discipline as the mechanism at the end.
- **The Father's house made into literal real estate.** The rooms (14:2) are dwelling with Jesus, the same word as the home God makes in the believer at 14:23.

## Also worth emphasizing

- **The "I am" progression as a spine.** John is repetitive on purpose, building a case. Naming 14:6 as the fifth "I am" lets students feel the case being built toward the vine.
- **14:1 and 14:27 as a deliberate bookend.** "Let not your hearts be troubled" opens and closes the chapter. Teaching them as a frame lets the whole unit be heard as one pastoral movement, comfort to comfort.
- **The Spirit's ministry always magnifies Christ.** Sermon 25 makes this the load-bearing point: try to look at the Spirit and you end up seeing Jesus. It keeps the Paraclete concrete and Trinitarian at once, and it is the antidote to a "spooky Spirit."
- **The Q3 project touchpoint.** John 14 is a chapter groups may teach. This unit models landing each scene on Christ and naming the response he asks, which is the whole assignment from Unit 17.

## The eight-lesson split

The seams cut on the chapter's own scene and thought boundaries, cover 14:1-31 with no gaps or overlaps, match the three sermons, land 14:6 in its own lesson with room, and give the short Thursday a tight self-contained passage. Sermon 23 covers L1 through L3, sermon 24 is the Thursday L4, sermon 25 covers L5 through L8.

- **L1 (i=80, Mon Feb 1, regular 50), John 14:1-4: let not your hearts be troubled.** Rational fear answered by "believe also in me," the Father's house with room and a prepared place, and "I will come again and will take you to myself." Builds on sermon 23. Lands on: Christ the trustworthy one who goes through the cross to prepare their place and returns to carry his own home.

- **L2 (i=81, Tue Feb 2, regular 50), John 14:5-7: the way, the truth, and the life. Plants and teaches John 14:6.** Thomas's lostness, the fifth "I am," the one way to the Father, and the turn to knowing the Father in the Son. The plant sits cleanly inside this one lesson and gets the full period it deserves. Builds on sermon 23. Lands on: Christ himself as the only road home to the Father.

- **L3 (i=82, Wed Feb 3, regular 50), John 14:8-11: whoever has seen me has seen the Father.** Philip's request, the exact revelation of the Father, the mutual indwelling, and "believe on account of the works themselves." Builds on sermon 23. Lands on: Christ one with the Father, the Father made visible, whose works testify.

- **L4 (i=83, Thu Feb 4, Thursday 36, single-focus), John 14:12-14: greater works, and ask in my name.** A tight, self-contained passage for the short day, exactly the scope sermon 24 covers. Greater works as the church's worldwide harvest through the Spirit, and prayer in his name for the Father's glory. One key question: "Jesus says his people will do greater works than he did. Bigger miracles, or something else? What does 'because I am going to the Father' tell you?" Builds on sermon 24. Lands on: Christ ascended to the Father, extending his work through the church by the Spirit and answering prayer for the Father's glory.

- **L5 (i=84, Fri Feb 5, regular 50), John 14:15-17: if you love me, and the first Helper.** Love then obedience tied to 13:34, and the first Paraclete promise, another Helper of the same kind, the Spirit of truth who abides forever and will be in them. The command and the Helper belong together, the way sermon 25 pairs them. Builds on sermon 25. Lands on: Christ who asks the Father and gives the Spirit to make obedience the fruit of love.

- **L6 (i=85, Mon Feb 8, regular 50), John 14:18-24: I will not leave you as orphans.** Christ's presence through the Spirit, "because I live, you also will live," love and self-revelation, Judas's question, and the triune home God makes with the one who loves and keeps his word (14:23, the rooms of 14:2 from the other end). Builds on sermon 25. Lands on: Christ who does not abandon his own but with the Father makes his home in them.

- **L7 (i=86, Tue Feb 9, regular 50), John 14:25-27: he will teach you, and peace I leave with you.** The Spirit who teaches and reminds the apostles, the ground of their witness, and the peace not as the world gives, bookending 14:1. Builds on sermon 25. Lands on: Christ who secures his church's memory of him by the Spirit and hands his own peace to frightened people.

- **L8 (i=87, Wed Feb 10, regular 50), John 14:28-31: the Father is greater than I, and "let us go."** The subordination-in-mission held with the deity of the Son (10:30; 5:18), the reason to rejoice at his going (Cyprian), Christ's sinlessness (the ruler has no claim), and the willing march to the cross out of love for the Father. A natural place to gather the chapter and hand off toward John 15. Builds on sermon 25. Lands on: Christ the Son, equal with the Father and ordered under him in mission, going sinless and willing to the cross.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# The Way, The Truth, and The Life (John 14:1-11)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 14:1-11

---

[00:00] This opening sentence is kinda gonna be our compass for the whole morning. Guys, we'll just look at it together real quick. Let not your hearts be troubled. Let not your hearts be troubled. Mercy store.

[00:13] This sentence from our Lord Jesus spoken to his closest friends is the heart, the posture from which all the rest of our text this morning is going to flow. Jesus Christ in the flesh is looking at His beloved, and He's speaking over them, Let not your heart be troubled. And then He's going to say a whole lot more to the end of achieving what He's commanding. He desires to to show compassion and tender care, and to encourage troubled hearts with all that we are going to read this morning. And so in order to get the maximum benefit of spending time looking at this interaction with Jesus, I think we need to bring before him our troubled hearts to allow him to speak these truths, which he considered to be effective to speaking to the troubled hearts of his dearest friends, to let these words wash over us this morning.

[01:12] I'll confess that, yesterday I yesterday afternoon, I I conducted a funeral, and it was a hard one. As a pastor, there are funerals that you, maybe look forward to. The 100 year old old lady who dies in a rocking chair with a bible in her lap. We don't get to do a lot of those. Right?

[01:37] Was especially difficult in that the deceased was a 24 year old woman who had endured unspeakable things in her life, grew up faster than she should've had to, brought children into the world as a teenager, lost them, several stays in prison, and the end cap was an overdose on heroin. And a funeral like that, it draws a certain kind of crowd. And so filled in the room yesterday as I'm preaching over this funeral are really two rooms. One are those who ran with the deceased in her addiction, and the other being those who desperately loved her and desired to see her pulled from it, and ultimately didn't get to see that. And so preaching the gospel at this space, you know, I talked to a friend who planted a church in, rural North Carolina, and he does about 20 of these, opioid overdose funerals for members of his church a year.

[02:49] And I called him and I said, help me, man. I've never done this before. And he said, Preach to the believers first. Remind them of their hope in Christ, and then turn to those who could be next, and make sure that they hear the gospel. And so I did.

[03:11] I spent twenty two minutes ish preaching the gospel to a room of addicts, and I watched the Lord doing some things in a handful of them that I'm praying. He carries with them home and and continues to do a work there. I'm praying. But I recognize in in that I the reason I bring it up is because I've been preparing this sermon for today, and it's this text that ended up being central to my sermon yesterday, and so I'm preaching it again to a different room for a different reason. But if this text was sufficient to be a comfort in that space last night, then it's sufficient to be a comfort to you in this space today.

[03:59] But maybe the difference between the two rooms is that that room, there was no denying its brokenness. The tears were already flowing. The awareness of self was high. So there wasn't a front end labor to do, to to bring somebody to an awareness that I need hope and encouragement, before speaking that hope and encouragement over them. And yet, for some of us, we came in here this morning hardened.

[04:29] Maybe not feeling like we need encouragement this morning, and so you're gonna be unable to receive it from me because you're believing that this is for someone else. I want you to hear it squarely on the front end this morning that I'm preaching to you. And my prayer is that as we work through the way that Jesus works this encouragement into the hearts of his beloved, that you will see how this is for you. Now he starts with, let not your hearts be troubled. Why is he saying this?

[04:58] We've been working left to right through this book for some time. We know why he's saying this. I mean, let's go back. He just said Peter's going to deny him three times. He had just said that one of the 12 was going to betray him, but didn't tell them who it was gonna be.

[05:16] We see in the chapter before that, that there's a plot that is moving forward among the Jews to kill Jesus after he raises Lazarus. Which he intends to die, that he was going to die by crucifixion. So if you are in the inner circle of Jesus, you've been walking with him for three years, you've hedged all of your bets on him, and you are walking with him this week, on this day, and you're hearing one's gonna betray you, one of us is going Peter's going to deny you, you're gonna be crucified talking about crucifixion? Jesus. Your heart's gonna be troubled.

[05:59] He's not talking about general anxiety, general agitation. He's talking about very rational fear that sizes up the situation, and measures our ability in the flesh, sees that it doesn't stack up, and rightly feels an agitated heart, a troubled heart. At the funeral yesterday, as we talked about the brokenness of the world, what I hope that you'll see here is what we're talking about is evil advancing on the face of the earth. Evil in your own life, evil around you, evil in the news. We're talking about a people who were seeing with their own eyes evil advancing, persecution heating up, pursuit of Jesus to kill him.

[06:56] And it had made its way into their inner circle. One was gonna be a betrayer. So it wasn't evil out there, evil right here. Peter's gonna deny him. This is super intimate.

[07:10] Okay? Similarly, you look out at the world, you look out at your life, and you see evil advancing in different corners of your world. New forms of evil taking root in the cult in the culture, right? New types of sin cropping up in your family. New stories of brokenness and hurt advancing to where we're asking, Lord, is the plan still good?

[07:35] Is it still in play? Are you still in control? Are you still Messiah? Are you still King? Are you still doing this all the stuff that you promised?

[07:43] Have we got this wrong? Jesus says, let not your hearts be troubled in light of all that I've just said. Peter denying me. Judas betraying me. Me being crucified.

[07:58] Let not your hearts be troubled. Why? Believe in God. Believe also in me. This word belief for believing in God, believing in Jesus, Christian circles, right?

[08:18] Like, I believe in Jesus. I don't mean believing in Jesus, and Jesus doesn't mean believing in Jesus like a child believes in Santa Claus, or or that you you something becomes true because you believe in it. We're talking about something being so true that it's worthy of your belief. It's an earned belief. It's a belief that like in a in a game of tug of
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.14.5-7`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
