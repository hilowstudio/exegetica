<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U26-L1-John-20-1-2.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["37 - The Empty Tomb (John 20-1-10).md", "38 - The First Witnesses (John 20-1-18).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 20:1-2.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.20.1-2] Teach John 20:1-2 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 20:1-2

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 133 of 150.
UNIT (use this exact name): U26 The empty tomb.  LESSON WITHIN UNIT: 1/8.
PASSAGE: John 20:1-2.  DAY TYPE: Regular (50 min) (use the matching variant).

MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16, John 4:24, John 6:35, John 8:12, John 10:11, John 11:25, John 13:34-35, John 14:6, John 15:5, John 16:33, John 17:3, John 19:30); the next new one comes in John 21:17 (Unit 27).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 20:1-31, "The empty tomb" (Unit 26)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Eight lessons, the resurrection, the climax and near-close of the Gospel. Unit 25 laid a dead man in a sealed tomb and went quiet. This unit breaks the quiet, and the tone lifts to joy, wonder, and worship. We come to behold the living Lord and to be sent. Three paired sermons cover the whole chapter: 37 "The Empty Tomb" (20:1-10), 38 "The First Witnesses" (20:1-18), and 39 "Peace Be With the Doubter" (20:19-31). Quote the ESV in the finished materials, above all the anchor 20:31. This unit plants no new memory verse; its climax is the home text of the course's very first anchor, 20:31.

## The christotelic center

Jesus of Nazareth was crucified, buried, and on the third day rose bodily in a glorified body that will never die, and the whole Gospel was written to bring the reader to believe it and live. The unit lands on the risen Lord who defeated death once for all. It lands on "I am the resurrection and the life" (11:25) now standing outside an empty tomb in a body of flesh and bone, the grave clothes left folded (20:6-7), a resurrection and not a resuscitation. It lands on the good shepherd who calls his own sheep by name (10:3) saying one word, "Mary" (20:16). It lands on the ascending Lord who makes his Father our Father (20:17). It lands on the crucified-and-risen Lord breathing peace and the Spirit on the very men who ran (20:19-22). It lands on the highest confession in the book, "My Lord and my God" (20:28), which closes the circle opened at 1:1, "the Word was God." And it lands on the aim of the whole Gospel and the whole course: "these are written so that you may believe that Jesus is the Christ, the Son of God, and that by believing you may have life in his name" (20:31).

- L1 (20:1-2) lands on the risen Lord whom the sealed tomb could not hold, met first as grief walking toward a grave.
- L2 (20:3-10) lands on the risen Christ whose ordered grave clothes are the first sign of resurrection, and the first Easter faith of the beloved disciple.
- L3 (20:11-16) lands on the good shepherd who calls his own by name, known by his voice.
- L4 (20:17-18) lands on the ascending Lord who makes his God our God and his Father our Father, with Mary the first herald.
- L5 (20:19-20) lands on the crucified-and-risen Lord bringing peace to the ones who abandoned him, known by his wounds.
- L6 (20:21-23) lands on the risen Lord who breathes the Spirit and sends the church with the gospel that forgives.
- L7 (20:24-29) lands on the God worshiped, the deity theme at its height, and the blessing spoken over the reader.
- L8 (20:30-31) lands on Christ the Son of God, the whole book written that you may believe and have life, the course's first anchor arriving home.

## The contested points, ruled

**The stone rolled away (20:1).** Rule it the open door to the risen life, not an exit Jesus needed. The glorified body passed through grave clothes left lying (20:6-7) and later through locked doors (20:19, 26), so the stone was not moved to let him out. It was moved to let the witnesses in, and to let the world see an empty tomb. Mary reads the open door as grave robbery and says so twice (20:2, 13), the honest first reading of anyone standing at a rifled grave. The stone is rolled back for us.

**The grave clothes lying and the face cloth folded (20:6-7).** Rule it the ordered sign of resurrection, and rule against grave robbery. John records the linen and the separately folded face cloth to counter any suggestion that thieves took the body, since thieves would have taken such expensive clothes, not undressed the body and neatly folded the linens. Sermon 37 presses the same evidence and the same wonder: whatever happened here did not happen in a rush, and there was care given to folding up the face cloth, the risen Lord setting it aside and walking out. The orderliness is the argument, and it is what persuaded the beloved disciple.

**"He saw and believed" (20:8), with "they did not yet understand the Scripture" (20:9).** Rule 20:8 the first Easter faith: even without fully understanding, the beloved disciple knew God had done this and realized Jesus was alive. Rule 20:9 the after-the-fact understanding pattern John has taught before (2:22 and 12:16, they did not understand until Jesus was glorified, and then they remembered). The tomb was empty before the Scriptures made sense of it, and then the empty tomb made the Scriptures make sense. The cross-references name which ones the risen Christ opened: Psalm 16:10 first, then Isaiah 53, and Luke 24:44-46, Moses and the Prophets and the Psalms.

**Resurrection, not resuscitation.** Rule it clearly and tie it to Unit 15. Lazarus came out bound hand and foot with grave clothes, his face wrapped (11:44), a living man dressed as a dead one, and he rose to die again. Jesus left his grave clothes lying and the face cloth folded (20:6-7), and he rose in a glorified body to die no more. The two tombs rhyme on purpose. "I am the resurrection and the life" (11:25) is no longer only a promise spoken outside a friend's grave. It is now embodied in the one who said it. Paul's summary belongs here: raised on the third day in accordance with the Scriptures (1 Corinthians 15:4).

**"Mary" (20:16).** Rule it the good shepherd calling his own by name. Mary does not recognize his face; she recognizes her name in his mouth. Chrysostom saw it: the recognition was not by his appearance but by his voice, for when he called her "Mary," then she knew him. This is 10:3 fulfilled, he calls his own sheep by name and leads them out, and 10:4, the sheep follow him, for they know his voice. The shepherd discourse of Unit 14 pays off in a garden at dawn. Sermon 38 lands the whole scene here: the resurrected Lord of the universe calls you by name. Keep it tender and personal. He knows her, and he speaks the name he has always known.

**"Do not cling to me... I am ascending to my Father and your Father, to my God and your God" (20:17).** Rule it the ascension and the new relationship of adoption, and guard hard against reading it as coldness. The verb is a present imperative, "stop clinging to me," a gentle word to someone already holding on. The reason he gives is a greater nearness coming, not distance. Sermon 38 puts it exactly: do not cling yet, we are almost there, go get my brothers, then you can cling to me, because the ascended Christ sends the Spirit to indwell every believer at once. The cross-references gather the two gifts of the verse. Ascension: John 16:28, Ephesians 4:8-10, 1 Peter 1:3. Adoption: Galatians 4:6-7, Galatians 3:26, and Hebrews 2:11-13, where the risen Christ is not ashamed to call them brothers. His Father is now their Father because of what he did in the grave. The 1:12 anchor, the right to become children of God, is enacted in the risen Lord's word to his brothers.

**"Peace be with you" and the wounds (20:19-20).** Rule it the crucified-and-risen Lord bringing peace to the ones who abandoned him. The doors are locked for fear, and he does not scold the fear. He stands among them and says peace, then shows the hands and the side. The disciples rejoice only after they see the wounds (20:20), and the wounds are the point of recognition. Sermon 39 dwells here: in glory the thing most familiar to the disciples about the risen Christ are the wounds he bore. This is the peace he promised in the upper room delivered in person (14:27; 16:33, an anchor). He brings peace to the very men who ran.

**"As the Father has sent me, so I send you" and "Receive the Holy Spirit" (20:21-22).** Rule it the commissioning of the church and a pledge of Pentecost, and handle the breathing carefully. The verb (emphysao) means to breathe upon or into, and it appears once in the New Testament. It sends us straight to Genesis 2:7, where God breathed into Adam the breath of life, and to Ezekiel 37:9, the breath over the dry bones. This is new-creation breath. The risen Lord breathes resurrection life on his church. Chrysostom guards the timing: Jesus said "receive the Holy Spirit," not "you have received," a first installment fitting them to receive the fullness at Pentecost (Acts 2). Teach it as the down payment, with Pentecost as the flood.

**"If you forgive the sins of any" (20:23).** Rule it the church's ministry of the gospel, and guard against priestly absolution. The forgiveness the church announces is the forgiveness the gospel carries, declared to faith and withheld from unbelief. Heidelberg Catechism Q84 is the exact guard: the kingdom of heaven is opened and shut by the preaching of the holy gospel, so that whenever people receive the promise of the gospel by a true faith, all their sins are really forgiven them of God, for the sake of Christ's merits. Sermon 39 preaches precisely this: you can sincerely look at someone and say, my brother, your sins are forgiven, because there is one mediator between God and man, the Lord Jesus Christ. No priest grants absolution here. The gospel forgives, on the lips of the whole church.

**Thomas's doubt (20:24-25).** Rule it honest doubt met by a patient Christ, and refuse to weaponize it. Thomas was no coward. He said "let us also go, that we may die with him" (11:16), and he asked the honest question at 14:5. His demand for evidence is the demand of a grieving man who will not be fooled twice. Jesus returned eight days later and offered the exact proof Thomas had asked for. Sermon 39: our good Lord cares about the one as much as the nations, and he waits eight days until Thomas is there.

**"My Lord and my God" (20:28).** Rule it the highest confession in the Gospel and the climax of its deity theme, forming an inclusio with 1:1. The cross-references confirm the arc: 20:28 points first to John 1:1, then Isaiah 9:6, and John 5:23 (the Son honored as the Father). The fathers are a wall of witnesses. Athanasius: let them confess, even they who previously denied that the crucified was God, for Thomas cried out, "my Lord and my God." Ambrose: you find the Son to be both Lord and God. Rule against the minority reading that took the words as mere astonished praise of God for a miracle. The text says Thomas said it "to him" (20:28), addressing Jesus, and the whole tradition and the 1:1 inclusio read it as worship of Christ. The Word who was God (1:1) is the Lord and God whom Thomas worships (20:28). The two ends of the book meet.

**"Blessed are those who have not seen and yet have believed" (20:29).** Rule it the blessing spoken over the reader, over the students themselves. Chrysostom: here he pronounces blessed not the disciples only, but those also who after them should believe. Sermon 39 says it straight: now he is talking about us, blessed are those who have not seen and yet have believed. Every Christian since the first Easter believes on the apostles' witness. The blessing lands in the classroom.

**The purpose statement (20:30-31).** Rule it the aim of the whole Gospel and the whole course. John chose these signs so that you may believe that Jesus is the Christ, the Son of God, and that by believing you may have life in his name. This is where the whole book has been driving. It is also where the course has been anchored since Day 1. Teach it as the anchor coming home (see the memory section).

## Christological and covenantal connections

- **The risen Lord, death defeated once for all.** Sermon 37 gathers why the Christ must rise: to keep God's promises, to vindicate his sinless life, to secure our justification (Romans 4:25, raised for our justification), to unite us to a living Lord, and to be our King forever. Revelation 1:17-18 crowns it: I died, and behold I am alive forevermore, and I have the keys of Death and Hades.
- **The glorified body, resurrection and not resuscitation.** Flesh and bone that eats and is touched, and yet passes through locked doors. Lazarus rose in his grave clothes to die again (11:44). Christ rose leaving them folded to die no more (20:6-7).
- **The good shepherd calling by name (10:3 into 20:16).** The voice the sheep know, now calling one grieving woman home.
- **The ascension and adoption (20:17).** His Father becomes our Father, his God our God (Galatians 4:6-7; Hebrews 2:11-13). The 1:12 anchor, the right to become children of God, enacted in the risen Lord's word to his brothers.
- **The commissioning and the Spirit (20:21-22).** New-creation breath (Genesis 2:7; Ezekiel 37:9), the church sent as the Father sent the Son, the pledge of Pentecost.
- **The deity of Christ confessed, the 1:1 inclusio (20:28).** The Word who was God is worshiped as my Lord and my God. The book opens and closes on his deity.
- **The aim of the book, belief unto life (20:31).** The new-covenant gift of life in his name, received by faith, offered to every reader.

## Reaching the three-tier room

The contact points here are among the strongest in the course, and they need no Bible knowledge to feel.

- **The searching student.** The floor is grief at a grave turning to joy. Mary goes in the dark to be near a dead body and finds an open, empty tomb, and her hope collapses before it is remade. Sermon 38 is built for this student: have you ever visited the grave of someone you loved, wanting to be where you last saw them. Then the risen Lord says one word, her name, and everything turns. Ask the plain questions. What if the grave were empty? What if someone who knew your name were alive to say it? The searching student also meets Thomas, who wanted evidence and got it. Wanting proof is welcome in this Gospel.
- **The churched but passive student.** Their mirror is a disciple with the report who still hides behind a locked door, and Mary comforting herself at a tomb with the memory of Jesus while the living Jesus stands behind her. Sermon 38 presses it: an empty tomb is not the same as the risen Christ, so comfort yourself with a living person. Press this at the autopilot Christian who knows the facts of Easter and has never met the risen Lord. Their second mirror is grace they cannot believe they get: the disciples who ran are the ones he breathes peace on, and forgives, and sends.
- **The maturing disciple.** Give them the weight. The folded grave clothes as John's deliberate counter to grave robbery. The 2:22 and 12:16 pattern of understanding after the fact, and the Scriptures of 20:9 (Psalm 16:10; Isaiah 53). The once-only "breathed" of 20:22 as new-creation breath (Genesis 2:7; Ezekiel 37:9). The gospel-forgiveness reading of 20:23 with Heidelberg Q84. The 1:1 to 20:28 inclusio, Thomas's confession as the deity theme's summit. Let them trace how one chapter holds the empty tomb, the naming, the ascension, the adoption, the Spirit, the deity of Christ, and the aim of the whole book.

Keep faith content invitational and participation assignable. Every student can analyze the folded cloths, the recognition by voice, the ascension words, the deity confession, and the purpose statement. No student is required to profess.

## Memory: the review-and-land of 20:31, no new plant

This unit plants no new graded verse. Its climax is the home text of the course's very first anchor, John 20:31, carried since Unit 0, Day 1. Handle it as review-and-land on L8 (20:30-31). Do not re-teach it as if new. Teach it as the aim of the whole Gospel and the whole course arriving where John wrote it, the anchor coming home. The move for the room: from Day 1 you have carried the sentence that tells you why this book exists, and today we finally stand in the place it lives, at the end of John's own account, right after Thomas worships the risen Lord. John wrote everything you have read so that you would believe Jesus is the Christ, the Son of God, and have life in his name. The confessions make the review rich: the Westminster Shorter Catechism defines the faith John calls for as receiving and resting upon Christ alone for salvation, as he is offered in the gospel, and the Larger Catechism cites 20:31 for why the Scriptures were written. Belief and life, exactly John's two words.

Keep the 15 anchors sharp with a joyful cumulative pass across the unit, letting the chapter embody the ones it fulfills: 11:25 (I am the resurrection and the life) now embodied in a risen body; 10:11 (the good shepherd) whose calling-by-name of 10:3 lands at 20:16; 19:30 (It is finished) now vindicated by the rising, since a finished atonement needs a living Savior; 1:14 and 1:12 (the Word made flesh, the right to become children of God) enacted in the adoption of 20:17; 16:33 (peace, take heart) delivered in person at 20:19; 14:6 and 3:16, life in the risen Son. The 15 held anchors are 20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35, 14:6, 15:5, 16:33, 17:3, 19:30.

No separate optional stretch verse this unit. "20:30-31" appears on the taught-not-memorized stretch list, and 20:31 is also the Unit 0 graded anchor students already hold, so it is not optional here. It is a full graded anchor landing in its home text, and the L8 review-and-land is the memory work. Offer no additional stretch verse. The next new anchor is 21:17 in Unit 27, the final one.

## Reaching doubters well through Thomas

Thomas is the patron of the honest doubter, and Jesus treats him gently. He was devoted enough to say "let us also go, that we may die with him" (11:16). His grief made him demand to see and touch before he would believe (20:25). Jesus returned eight days later and offered the exact evidence Thomas had asked for, then said "do not disbelieve, but believe" (20:27), an invitation and not a shaming. Thomas answered with the highest words in the Gospel, "my Lord and my God" (20:28). Sermon 39 names the whole arc "peace be with the doubter" and closes: go as you doubt, go while you are scared, a needy people bringing a message of hope to needy people.

Guard against two things. Do not use Thomas to shame anyone who struggles to believe. The nickname "doubting Thomas" as an insult misses that Christ met him with patience and evidence and never with contempt, and it forgets that the same Thomas carried the gospel as far as India. And do not let a student hear that doubt disqualifies them. The blessing of 20:29 falls on those who believe without seeing, which describes every student in the room, and the road there can run straight through honest questions.

## Pitfalls with teenagers

- **Treating the resurrection as a metaphor or a "spiritual" idea.** The chapter insists on a real body. The folded grave clothes, the hands and the side, Thomas's touch, and the breath of 20:22 all make it physical. Rule the rising bodily and historical every time. Sermon 37: we saw him dead, and now he is alive forevermore.
- **Using Thomas to shame doubters.** Jesus met him gently, with the exact evidence he asked for.
- **Over-reading 20:23 into priestly absolution.** Guard with Heidelberg Q84. The gospel forgives, declared by the whole church.
- **Reading "do not cling to me" as coldness.** He is telling Mary a greater nearness is coming by the Spirit, and sending her with the first Easter sermon. Keep it warm.
- **Missing that "blessed are those who have not seen" is spoken over the students.** Name it. Jesus is blessing them across the centuries.
- **Letting the joy go flat or sentimental.** This is the earthquake of death defeated, not a soft sunrise. Keep the worship high and the wonder concrete.
- **Rushing past 20:31 as if it were new.** It is the anchor the whole course was built on. Give it the recognition of a homecoming.

## The eight-lesson split

The seams keep the four scenes legible where the arithmetic allows, keep the run to the tomb whole (20:3-10), keep the Thomas confession whole (20:24-29), and give the purpose statement its own landing (20:30-31). Eight lessons over thirty-one verses run the two long morning scenes across two adjacent lessons each, cut at their natural internal seams (recognition, then commission), so each scene stays legible while each lesson lands a distinct beat. Both Thursdays (L3, L8) get a tight, self-contained passage. Sermons 37 and 38 cover the tomb and Mary (L1-L4); sermon 39 covers the disciples, Thomas, and the purpose statement (L5-L8).

- **L1 (i=133, Tue Apr 27, regular 50), John 20:1-2. Sermon 37/38.** Mary comes in the dark, the stone taken away, her report, "they have taken the Lord." Carries the unit opening and a brief recap of the burial from Unit 25. Lands on: the risen Lord whom the sealed tomb could not hold, met first as grief at a grave.

- **L2 (i=134, Wed Apr 28, regular 50), John 20:3-10. Sermon 37.** The race, the linen cloths lying, the face cloth folded by itself, "he saw and believed," "they did not yet understand the Scripture that he must rise." Keep the run to the tomb whole. Lands on: the risen Christ whose ordered grave clothes are the first sign of resurrection, and the beloved disciple's first Easter faith.

- **L3 (i=135, Thu Apr 29, Thursday 36, single-focus), John 20:11-16. Sermon 38.** Mary weeping, the two angels, the supposed gardener, "Mary!" and "Rabboni!" A tight, self-contained short day ending on the recognition. One key question: "Mary is looking right at Jesus and does not know him until he says one word. What is the word, and why does that one word change everything?" Lands on: the good shepherd who calls his own by name (10:3 into 20:16), known by his voice.

- **L4 (i=136, Fri Apr 30, regular 50), John 20:17-18. Sermon 38.** "Do not cling to me... I am ascending to my Father and your Father, to my God and your God," and Mary the first herald, "I have seen the Lord." A short passage carrying a full period on the ascension, the adoption, and the first proclamation. Lands on: the ascending Lord who makes his God our God and his Father our Father.

- **L5 (i=137, Mon May 3, regular 50), John 20:19-20. Sermon 39.** The locked doors, "Peace be with you," the hands and the side shown, "the disciples rejoiced when they saw the Lord." Lands on: the crucified-and-risen Lord bringing peace to the ones who abandoned him, recognized by his wounds.

- **L6 (i=138, Tue May 4, regular 50), John 20:21-23. Sermon 39.** "As the Father has sent me, so I send you," "Receive the Holy Spirit," and the forgiving and withholding of sins. Teach the once-only "breathed" as new-creation breath and 20:23 as the gospel the church proclaims (Heidelberg Q84). Lands on: the risen Lord who breathes the Spirit and sends the church with the gospel that forgives.

- **L7 (i=139, Wed May 5, regular 50), John 20:24-29. Sermon 39.** Thomas absent, his demand, eight days later the locked doors again, "Put your finger here," "My Lord and my God," "Blessed are those who have not seen and yet have believed." Keep the Thomas confession whole. Lands on: the God worshiped, the deity theme's summit and the 1:1 inclusio, the blessing over the reader.

- **L8 (i=140, Thu May 6, Thursday 36, single-focus), John 20:30-31. Sermon 39.** The purpose statement, and the review-and-land of the Unit 0 anchor 20:31 in its home text. A tight, single-focus short day on the aim of the whole Gospel and the whole course. One key question: "John chose these signs out of many, and he tells you why he wrote them. What does he want to happen in you, and has it?" Lands on: Christ the Son of God, the whole book written that you may believe and have life, the course's first anchor arriving home.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# The Empty Tomb (John 20:1-10)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 20:1-10

---

[00:00] And so here we are. We've been working left to right through the gospel account of John for, about fifteen to eighteen months now at Mercy's Door. And so we've just slowly walked through all the events leading up to this text here. We have seen a Jesus who has been beaten, mocked, scorned, crucified, killed. We saw a spear pierce through his side.

[00:22] We saw him pour out blood and water. We saw the Son of God declare, it is finished. And we saw him dead dead. We saw him taken off the cross and carried to a tomb cut from the rock, Joseph of Arimathea's tomb. And we saw the stone rolled over that tomb, and then we saw it go quiet.

[00:42] And last week, we spent significant time talking about what was happening on the Earth and what was happening underneath the Earth as we declared that Jesus Christ was putting death to death by his own. And here we pick up in this morning's passage with his disciples wandering back to the tomb to mourn. If you were with Mercy's Door while we were preaching the Lazarus account, the death of Lazarus, then you started to see kind of what the Jewish morning ritual was like. You would go back and forth to the tomb, from to the tomb to your home, from your home to the tomb, back and forth, in many cases, for weeks. You you would go to the tomb to weep, and then you would return to your home.

[01:22] And that's what's happening here. We see Mary Magdalene go to the tomb to cry, to be near the body of her dead Lord. But when she gets there, she sees that the stone is rolled away, and that the body is missing. And so she runs and she gets Peter and John and she tells them they've taken the Lord out of the tomb and we don't know where they've laid him. This is her only logical conclusion, is somebody's removed the body.

[01:52] Preached that last week. This was Joseph's tomb. So maybe Joseph moved the body. Maybe they found a different spot for him. Maybe the soldiers moved the body.

[01:59] Maybe somebody took the I don't know what happened, but the body is not there. And I just wanted to go near the body that I might mourn. And now I don't even know where his body lay. This is like another and the and the and the and the and the

[02:12] and the and the and the and the

[02:13] and the and the and the and the and the and the and the and the and the and the and the and the and the and the scattered very few were even there to see him crucified because they were so scared at his betrayal. And here, we just don't even know where his body lay that we can mourn near it, that we can cry near it. And so, Peter and John accompany Mary and other women back to the tomb. And it says this, that when John outran Peter and reached the tomb first, he was too scared to go in. He peeked, but he wouldn't enter.

[02:51] Peter walks right in. Verse six, went into the tomb, and he saw the linen cloths lying there and the face cloth, which had been on Jesus' head, not lying with the linen cloth, but folded up in a place by itself. And then John goes in and and and he saw and it says that he believed. We'll talk about that phrase in a second. Shroud had been removed and folded up and placed in a in a different spot than the body shroud, than the linen cloth.

[03:30] Something stood out to Peter, even in this moment about the orderliness of the contents of the tomb. That whatever happened here didn't happen in a rush. That there was care given to folding up this face route and placing it in a place by itself, while the linen cloths remained on the bed where the body had lay. And this called to mind a really beautiful portrait for me, as I pictured, and I want you to picture it with me, the dead and decaying body of Christ steeped in what we preached last week was $200,000 worth of myrrh and aloe and spices, eyes opening, three days later, sitting up in the tomb in a glorified body, removing the face shroud, folding it up nicely, setting it aside, and strolling out of the tomb. Peter does not yet understand that this is their nature by which this face shroud came to be folded up nicely and set off to the side.

[04:41] But the grace with which our Lord reentered the earth is just marvelous to me. And I thought I'd hold out that tidbit to you. But then it says that when John entered that he saw and believed. We might be tempted to think that we mean that he saw and believed that Jesus had resurrected like he said, but then the rest of the sentence takes that away from us. It says, for as yet, they did not understand the scripture that he must rise from the dead.

[05:10] So it was upon seeing with his own eyes entering and seeing the body missing that he believed the account of Mary, that they had taken Jesus's body and moved it somewhere else. This is what he believed. He's not here. He's not here. And as yet, they did not understand the scripture that he must rise from the dead, then the disciples went back to their homes.

[05:38] Preach to you all. And saw that the tomb was empty. Their response was to go back to their homes because they did not yet understand risen Christ. An empty tomb brought them into further despair such that all they could do is say, we'll go back home tomorrow. We'll return to our homes.

[06:13] There's nothing here to more. But the risen Christ ends the morning altogether and brings you instead to joyful celebration. And I pray that we are going to find our way into that celebration as we behold the risen Christ this morning, not merely an empty disciples understood this, that he died. That he was buried. They understood this.

[06:51] But then this, that he was raised on the third day in accordance with the scriptures. Then he appeared to more than 500 brothers at one time, most of whom are still alive, so you can go ask him, though some have fallen asleep. And then he appeared to and And last of all, as to one untimely born, he appeared also to me. Paul says, I delivered to you as first importance that Christ died for us, was buried, and that he was raised on the third day in accordance with the scriptures, and that he appeared to a great cloud of witnesses, not only the disciples, but another bodily resurrection of Jesus that he Christian. And the Christian.

[08:10] And the Christian. And the Christian. And the Christian. And the Christian. And the Christian.

[08:13] And the Christian. And the Christian. And the Christian. And the Christian. And the Christian.

[08:21] And the Christian. And the Christian. And the Christian. If Christ has not been raised, then your faith is futile, and you are still in your sins. Verse 19 says, if in Christ we have hope in this life only, we are of all people to be pitied.

[08:35] Be In fact, Christ has been raised from the dead. And that's what we've gathered here this morning to discuss. You know, in that, same book of Acts, a couple chapters later in Acts chapte

# The First Witnesses (John 20:1-18)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 20:1-18

---

[00:00] It's fitting, given that it's resurrection Sunday, that we take a look this morning at John chapter 20 verse one to 18, if you wanna find your way there. John chapter 20 verses one to 18. This morning, we will be exploring the resurrection account of Jesus. Give you a minute to find your way there. John chapter 20 verse one to 18.

[00:29] Let me read it for you. Now on the first day of the week, Mary Magdalene came to the tomb early while it was still dark, and she saw that the stone had been taken away from the tomb. And so she ran and went to Simon Peter and the other disciple, the one whom Jesus loved, and said to them, they have taken the Lord out of the tomb, and we do not know where they have laid him. So Peter went out with the other disciple, and they were going toward the tomb. Both of them were running together, but the other disciple outran Peter and reached the tomb first.

[01:02] And stooping to look in, he saw the linen cloths lying there, but he did not go in. Then Simon Peter came following him and went into the tomb. He saw the linen cloths lying there and the face cloth which had been on Jesus' head, not lying with the linen cloths, but folded up in a place by itself. Then the other disciple who had reached the tomb first also went in, and he saw and believed, for as yet they did not understand the scripture that he must rise from the dead. Then the disciples went back to their homes.

[01:35] But Mary stood weeping outside the tomb, and as she wept, she stooped to look into the tomb, and she saw two angels in white sitting where the body of Jesus had lain, one at the head and one at the feet. They said to her, woman, why are you weeping? She said to them, they've taken away my Lord, and I do not know where they have laid him. Having said this, she turned around and saw Jesus standing, but she did not know that it was Jesus. And Jesus said to her, Woman, why are you weeping?

[02:08] Whom are you seeking? Supposing him to be the gardener, she said to him, Sir, if you have carried him away, tell me where you have laid him, and I will take him away. And Jesus said to her, Mary. She turned and said to him in Aramaic, Rabbonai, which means teacher. Jesus said to her, Do not cling to me, for I have not yet ascended to the Father, but go to my brothers and say to them, I am ascending to my father and your father, to my God and your God.

[02:39] Mary Magdalene went and announced to the disciples, I have seen the Lord, and that he had said these things to her. This is the word of the Lord for us this morning. Beginning in verses one to two, what I want you to see is a Mary Magdalene, a beloved disciple of Jesus Christ, approaching what she believed to be a full tomb. In verse one to two, we see Mary Magdalene, a beloved friend and disciple of Jesus Christ, approaching his tomb expecting to find it full, not empty. Full and not empty.

[03:21] Mary Magdalene, since we're jumping into chapter 20 and you guys may not be familiar with her, she was a beloved friend and disciple of Jesus. She loved him. She's recognized as one of the most central female figures in all of the New Testament and in all of Christian tradition. It's her life that portrays to that's portrayed to us in the gospel that gives us a picture of profound transformation in a person's life. If you need an example, men and women, of what it looks like to have things just totally turned upside down because you have encountered Jesus Christ as Lord, you can look at Mary Magdalene.

[03:56] She had this extreme transformation that gave her an enduring commitment to her Lord. She came from the town of Magdala on the Western shore of the Sea Of Galilee. That's where you get Mary Magdalene from. And the Gospels introduce her first as a woman. This is in Luke chapter eight in Mark 16, from whom Jesus cast out seven demons.

[04:19] That's where we first meet Mary, filled with seven demons. Then Jesus shows up, and with this dramatic healing, he casts the seven demons out of her, and this is what begins the discipleship of Mary Magdalene. This is what begins the devotion that she has in her heart towards Jesus Christ. She's been freed from her afflictions, and Mary starts following him everywhere and even supporting his ministry out of her own means. She follows him on his travels all throughout his three years on of his public ministry, and she's completely devoted everywhere that he goes.

[04:53] Her role in the gospel is especially prominent in this part of the Bible, starting around John 19, where we see her devotion to him in his final hour, at his crucifixion, at his burial, and at his and at his resurrected. She's shown in the Gospels to be one of the few faithful ones who remained with Jesus and right at his side at the cross. Peter wasn't there. Most of the disciples were not there. Mary was there.

[05:22] Mary saw him crucified. She stayed with him at his darkest hour. That was in Matthew 27 and Mark 15. And following his death, she saw him buried. She followed along, and she observed the place where he was buried.

[05:34] It's how she knew where to go in this passage. And following him to his burial, and then coming again here three days later is showing that she remains faithfully devoted to him, even here in his death. She loves him, and her love and devotion to him is sincere, even here, in her faithless and dark hour, where he has been killed. The most significant contribution in the Bible to the life and ministry of Mary Magdalene is right here in John chapter 20. Jesus Christ came into the world, the one in whom, through whom, and for whom all things were made, came into the world, born of a virgin, lived thirty three years, a life of perfection, perfectly fulfilling the law of God, perfectly obedient to the will of the Father, teaching only the words which proceeded from the mouth of God.

[06:30] He would say to to Philip that if you have seen me, Philip, you have seen the Father, the very incarnation of God, Jesus Christ. And for those thirty three years living a perfect life of righteousness, it culminates to Good Friday, just a few days ago, where we soberly recognize that that God, that Lord, the Son of God Jesus Christ, living that perfect life, sinless in every way, turned Himself over to wicked men like you and I, and permitted himself to be killed at the hands of sinners as a right sacrifice, an atoning sacrifice for the sins of the very ones who put him on the cross, such that anybody who is united with him by faith is credited with that perfect life of righteousness that he lived for us. And he offers his death as a substitutionary death for the death that we ought to die on account of our sin, this sinless one exchanging his life for ours, his death for ours. And then he's laid in the tomb, and Mary knows where it is. And she approaches th
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.20.1-2`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
