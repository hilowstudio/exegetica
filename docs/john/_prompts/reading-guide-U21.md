<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_reading_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-materials\\GEN_U21_reading-guide.md", "min_chars": 1500, "student_facing": true, "title": "Reading guide, Unit 21: The Spirit and the coming joy", "sermon": []} -->

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

## Format to produce: Bible Reading Guide (per-unit, student)
Definition: A student-facing guide that carries a class through one unit of a verse-by-verse Bible course. It is a light follow-along structure used alongside the student's Reading Journal and the in-room discussion, not a worksheet to complete at home. Built for a three-tier room: a low floor (navigation help, plain language, no assumed knowledge) and a high ceiling (optional go-deeper prompts for the disciple).
Use when: The instructor wants one guide per unit that students follow across its lessons, supporting observation, interpretation, and response without take-home busywork.
Required structure — include every component, in this order:
  - Unit header: unit name; passage range; the unit's memory verse (ESV); the one big question the unit asks
  - How to use this guide: with your Reading Journal, in class; what a good observation looks like
  - For each lesson passage in the unit, a short block: the reference and 'read it'; 1-2 Observe prompts (what the text says); one Interpret prompt (what it means and who Jesus is here); one Respond prompt (what it asks of you); an optional 'Go deeper' for the disciple (a cross-reference or Old Testament echo); navigation help for the newcomer where a passage is hard to find
  - Key words to know: a few light vocabulary or background terms for the unit
  - Memory verse (ESV) with the review note
  - The whole unit points to Christ: one or two sentences naming where the unit lands on Jesus
Formatting: Markdown, addressed to the student in plain, warm language. Keep prompts short and answerable; leave the heavy lifting to the Reading Journal and the discussion. Mark 'Go deeper' prompts clearly as optional. Quote Scripture in the ESV.

Default scope: One guide per unit (typically 2-11 lessons).
Sourcing for this format: Quote all Scripture in the ESV (pass translation='ESV' to the study-bible tools) and ground it there; do not rely on memory. Keep the guide honest for a searching student as well as a believing one.


## Grade band: secondary —     "Grades 9-12. Academic vocabulary, longer texts, analysis and argument, primary-source excerpts, citations expected."
Adaptation for this format at this band: The default. A sophomore mixed-faith classroom; never assume Bible literacy.

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

Generate the Bible Reading Guide (per-unit, student) now.

Grade band: secondary.
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 16:1-7..16:33.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.16.1-7..16.33] Help a 10th grader read John 16:1-7..16:33 with understanding and response. (grade 10, complexity 14)
      · Ground in: Scripture John 16:1-7..16:33
  - [JN.16.33] Know and review the unit memory verse John 16:33. (grade 10, complexity 9)
      · Ground in: Scripture John 16:33

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the per-unit STUDENT reading guide for U21 The Spirit and the coming joy (John 16:1-7..16:33).
Give a short follow-along block for each of these lesson passages, in order: John 16:1-7; John 16:8-11; John 16:12-15; John 16:16-22; John 16:23-28; John 16:29-32; John 16:33.
UNIT MEMORY VERSE: John 16:33 (ESV, with the review note).

FRAMING (Adam's theological framing for this passage; keep the student guide consistent with its rulings and emphasis, put in plain student language):
-----
# Framing: John 16:1-33, "The Spirit and the coming joy" (Unit 21)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Seven lessons that continue and nearly close the Farewell Discourse (John 17 is the prayer). One paired sermon, 28 "Your Sorrow Will Turn Into Joy" (16:16-33), covers the back half; the persecution warning and the Spirit's convicting and guiding work (16:1-15) is a sermon-less fresh-build. This unit plants the new graded anchor, John 16:33. The Spirit material here is taught in place; the very next unit, U22, gathers all the Paraclete sayings into a synthesis, so leave the grand gathering to U22. Quote the ESV in the finished materials.

## The christotelic center

Christ's going is the door to the Spirit's coming, and the Spirit's whole work points back to Christ. On the last night, Jesus tells frightened men the truth about what is coming for them, then hands them three gifts to carry through it: the Advocate who will convict the world and guide them into all truth (16:7-15), a sorrow that his cross will turn into unstealable joy (16:20-22), and direct access to a Father who loves them himself (16:27). The unit lands on Christ who goes from the Father, through the cross, back to the Father (16:28), and whose finished victory is the ground of his people's peace: "I have overcome the world" (16:33). It lands hardest at 16:33, the discourse's climactic comfort and this unit's planted anchor, which answers the "let not your hearts be troubled" that opened the discourse (14:1).

- L1 (16:1-7) lands on Christ who forewarns his own to keep them, and whose going home opens the door to the Spirit.
- L2 (16:8-11) lands on Christ whose vindication the Spirit presses on the world, the sinless one it refused, now gone to the Father, whose enemy is already condemned.
- L3 (16:12-15) lands on Christ whom the Spirit magnifies, taking what is the Son's, which is the Father's, and declaring it to the church.
- L4 (16:16-22) lands on Christ whose cross turns his people's grief into a joy no one can take away.
- L5 (16:23-28) lands on Christ who opens direct access to a Father who loves his people himself, and who came from the Father and returns to him.
- L6 (16:29-32) lands on Christ alone at the cross yet held by the Father's presence, steady while his friends scatter.
- L7 (16:33) lands on Christ the victor over the world, whose finished conquest is his people's peace.

## The contested points, ruled

**The persecution warning (16:1-4).** Rule this forewarning given as comfort, so they will not fall away. The stated purpose is right in the text: "I have said all these things to you to keep you from falling away" (16:1), and again "I have said these things to you, that when their hour comes you may remember that I told them to you" (16:4). Jesus names the specific coming trials: they will be put out of the synagogues (16:2), and killed by men who think they are offering service to God (16:2). This is grounded in the Gospel itself. Synagogue expulsion is already the fear at work in John 9:22 and 12:42. The killer who thinks he serves God is Paul before Damascus (Acts 26:9-11), a zeal for God not according to knowledge (Romans 10:2-3). This continues 15:18-25 directly: the world hates the disciples because "they have not known the Father, nor me" (16:3). Rule it pastoral care. A shepherd who sees the ambush tells the sheep in advance, so the shock does not break their faith when it lands.

**"It is to your advantage that I go away" (16:7).** Rule the Spirit's coming genuinely better for them than Jesus' bodily presence, and guard hard against any hint that the Spirit is a downgrade. The word for the Spirit is Helper or Advocate (parakletos), one called alongside to aid. Chrysostom takes the guard head-on: is it a benefit that the master departs and the servant comes? See how great is the honor of the Spirit. The Spirit is co-equal God, the point U19 established from "another Helper" (allos parakletos) at 14:16. The advantage is real for two reasons. First, the bodily Jesus was in one place at a time, and the Spirit indwells all his people everywhere at once (Augustine). Second, the order of glory runs this way: Christ enters his glory, then pours the Spirit out. The Heidelberg Catechism gathers the benefit of the ascension, that the risen Christ is our advocate before the Father, we have our own flesh in heaven as a sure pledge, and he sends us his Spirit as a down payment (Q49, citing 16:7). His going is gain for them.

**The Spirit convicting the world "concerning sin and righteousness and judgment" (16:8-11), the hard one.** This is the famously difficult passage, and it needs a ruling on the verb and on each of the three clauses.

The verb is convict or reprove (elencho): to cross-examine, to prove guilty, to press the verdict home so it cannot be shrugged off. It is Jesus' own challenge, "which one of you convicts me of sin?" (John 8:46), and the light that exposes evil deeds (John 3:20). Rule it the Spirit's work on the world's conscience: he proves the world guilty and wrong. The world had put Jesus on trial; now the world stands trial before the Spirit, and its guilt is proven. This work runs through the church's preaching. Calvin is firm that it is no secret private revelation, but the power of the Spirit in the outward preaching of the gospel and the voice of men.

Now the three clauses, each ruled from the text's own reasons.

- Sin, "because they do not believe in me" (16:9). Rule the root sin unbelief in Christ. The Spirit exposes that the world's fundamental guilt is refusing the sinless one who stood in front of it. The Spirit shows the world that its case against Jesus was the world's own crime.
- Righteousness, "because I go to the Father, and you will see me no longer" (16:10). Rule this Christ's vindication. The world condemned Jesus as a guilty man. The Father raised him and received him home, which is the verdict overturned: the righteous one is proven righteous by going to the Father. The ascension is the Father's public declaration that Jesus was right and the world was wrong.
- Judgment, "because the ruler of this world is judged" (16:11). Rule this the sentence already passed on Satan at the cross (tie to 12:31 and 14:30, where Satan has no claim on Christ). The Spirit presses on the world that its master is a defeated, condemned power, and that the world's own judgment is sealed if it stays under him.

**"He will guide you into all the truth" and "he will glorify me" (16:12-15).** Rule the Spirit's work Christ-centered and grounded in the apostolic witness, and guard against a private-new-revelation misreading. The "all the truth" is the finished teaching about Christ that the disciples "cannot bear now" (16:12) and the Spirit will complete in them. The confessions cite 16:13 for the Spirit's inward witness to the written Word, not for fresh revelation alongside it: the Spirit persuades the heart by and with the Scriptures (1689 1.5; Westminster 1.5). The guard against a lying spirit of new revelation is as old as Ignatius, who quotes this verse: the Holy Spirit does not speak his own things, but those of Christ, "he will glorify me, for he will take what is mine." That is the U17 and U19 point held: the Spirit always magnifies Christ. Try to look at the Spirit, and you end up seeing Jesus. Note the Trinitarian ordering in 16:14-15. The Spirit will glorify Christ by taking what is Christ's (16:14), and all that the Father has is Christ's (16:15). The Spirit takes what is the Son's, which is the Father's, and declares it to the church. Teach this in place; the very next unit (U22) gathers the Paraclete sayings across the whole discourse, so hand the synthesis to U22.

**"A little while" (16:16-19).** Rule this the short gap of the cross and their grief before the resurrection joy. The disciples are baffled, and 16:17-18 records their confusion out loud ("we do not know what he is talking about"). They lose the sight of him at the cross and recover it at the resurrection, then further at Pentecost, and fully at his return. Adam's sermon 28 catches their ear: when Jesus says "you will see me no longer," what they hear is "no longer," and then he comes back in with "and again a little while, and you will see me." The near horizon is Friday's grief giving way to Sunday's joy.

**Sorrow turning to joy, and the woman in childbirth (16:20-22).** Rule the cross-shaped pattern: real anguish that gives way to a joy no one can take. "You will be sorrowful, but your sorrow will turn into joy" (16:20), and the joy "no one will take from you" (16:22). The image is labor: when the woman "has delivered the baby, she no longer remembers the anguish, for joy that a human being has been born into the world" (16:21). Calvin locks it to the cross: as the cross always contains the victory in itself, the grief arising from it is like the sorrow of a woman in labor, which receives its reward when the mother is cheered by the birth. The sorrow is not wasted, and it is not merely followed by joy. It produces the joy, the way labor produces the child. Adam's sermon 28 guards it against a cheap reading: the blood of Christ does not numb the pain or replace it or fly a baby in like a stork at the last hour. The baby is produced through the pain. The cross is the supreme case, where death becomes the entrance into eternal life. Rule this a durable comfort for anyone suffering, held under the guardrail below so it never becomes "just be positive."

**Asking in Jesus' name, and "the Father himself loves you" (16:23-27).** Rule this the new access to the Father that Christ's going opens, grounded in who he is, and land 16:27. "If you ask anything of the Father in my name, he will give it to you" (16:23) ties straight back to 14:13-14 (U19): praying in his name means praying on the ground of his person and character, for the Father's glory. Guard again against the magic-formula and prosperity readings, the same guard U19 set. Then the stunning line: "the Father himself loves you, because you have loved me and have believed that I came from God" (16:27). Adam's sermon 28 makes this the heart of the passage and the correction of a lie teenagers believe, that Jesus is a heat shield between them and an angry Father, a mediator you beg to go ask the Father on your behalf. Jesus says the opposite in 16:26-27: "I do not say to you that I will ask the Father on your behalf; for the Father himself loves you." Rule the mediation this way: Christ's blood bought direct access, so his people go to a Father who already loves them. That access is the fruit of the cross, and it changes how you pray.

**"I came from the Father... and I am going to the Father" (16:28).** Rule this the whole gospel in one sentence, incarnation to ascension. "I came from the Father and have come into the world, and now I am leaving the world and going to the Father." The pre-existent Son comes from the Father, takes flesh, finishes the work, and returns. This is the arc U19 traced at 14:28 and the Prologue set at 1:1-18, said now in a single line the disciples seize on (16:29-30).

**The scattering, and "yet I am not alone, for the Father is with me" (16:32).** Rule Christ's aloneness at the cross held together with the Father's presence. Jesus tells them plainly they will scatter, "each to his own home, and will leave me alone" (16:32). Adam's sermon 28 refuses to soften it: Jesus answers their confident "now we believe" with "do you now believe?" and tells them the truth, that they will be scattered and leave him alone. Then he holds his own comfort: "yet I am not alone, for the Father is with me." The abandonment by his friends is real, and the Father's presence with the Son is real. Teach both, and keep the deeper darkness of the cross reverent (the cry of Psalm 22 is Good Friday's mystery; here Jesus asserts the Father's presence to steady the eleven).

**The plant, "In the world you will have tribulation. But take heart; I have overcome the world" (16:33).** Rule this the discourse's climactic comfort: peace in him amid guaranteed trouble, grounded in his finished victory. "I have overcome" is a Greek perfect (nenikeka), an accomplished victory with a standing result. The perfect is the point: the win is already done, and its effect stands. Origen states the ground precisely: he has overcome the world, because the world is strong only insofar as its Victor allows, and he has received from the Father the victory over the world. The peace is "in me," settled in his person, while the tribulation is honestly promised, "you will have" it. This closes the frame U19 opened: "let not your hearts be troubled" (14:1) is answered by "take heart; I have overcome the world." Cyprian reached for this verse again and again to steady the persecuted church. Ground it in the perfect tense and in Origen and Cyprian.

## Christological and covenantal connections

- **Christ's going is the door to the Spirit's coming.** 16:7 with Heidelberg Q49. The ascension sends the Advocate. His departure is the condition of Pentecost.
- **The Spirit's whole work aims at Christ.** He convicts the world of unbelief in Christ (16:9), vindicates Christ by his going to the Father (16:10), and takes what is Christ's to declare it (16:14-15). Ignatius: he will glorify me, for he will take what is mine. The Paraclete thread from 14:16-17 and 15:26 reaches its fullest teaching here.
- **The cross-shaped sorrow-to-joy pattern.** 16:20-22 with Calvin: the cross always contains the victory. Grief produces joy the way labor produces the child. The resurrection is the first fruit, and the pattern holds for all who suffer in Christ.
- **New access to the Father in Christ's name.** 16:23-27 with 14:13-14. Christ's blood buys direct access to a Father who loves his people himself (16:27).
- **Christ from the Father, to the Father.** 16:28 with 14:28 and 1:1-18. Incarnation to ascension in one line, the shape of the whole gospel.
- **Victory over the world and its ruler.** The ruler of this world is condemned (16:11, tied to 12:31 and 14:30), and Christ has overcome the world (16:33). The defeat of the enemy and the victory of the King are the same finished work.
- **Peace as the new-covenant gift, bookending 14:27.** "Peace I leave with you" (14:27, U19) and "in me you may have peace" (16:33) frame the discourse. His own settled peace handed to frightened people.

## Reaching the three-tier room

The contact points are strong, because this is a dying man telling scared friends the truth and comforting them at the same time.

- **The searching student.** Fear of what is coming (16:1-4). Being warned honestly instead of lied to (Jesus names the ambush before it lands). Grief that feels like it will never end, met by the promise that sorrow turns to joy (16:20-22). Feeling alone (16:32). Unanswered prayer, and what "ask in my name" really means (16:23-24). Being loved by God the Father himself (16:27). Peace in the middle of trouble (16:33). The plain question: who tells his friends the hard truth about their coming suffering and in the same breath hands them joy and peace, on the night before he is killed?
- **The churched but passive student.** The mirror is the disciples' premature confidence, "now we know... we believe" (16:30), met by Jesus' "do you now believe?" and his flat prediction that they will scatter (16:31-32). Nearness and confident words are not yet a faith that stands. Press it warmly. The same Jesus who names their coming failure grounds their peace in his victory, not their steadiness (sermon 28).
- **The maturing disciple.** Give them the weight: the convict-and-expose verb and the courtroom reversal in 16:8-11, the three clauses each ruled from the text, the Trinitarian ordering of 16:14-15, the confessions grounding "all truth" in the Spirit's witness to Scripture (1689 1.5), the perfect tense of "I have overcome" in 16:33 with Origen, and Augustine's account of why the bodily form had to go so the Spirit could indwell all his people. Let them trace how one chapter holds the Spirit's conviction, the guiding into truth, the sorrow-to-joy pattern, prayer, the Father's love, and the finished victory.

Keep faith content invitational and participation assignable. Every student can analyze the three clauses, the childbirth image, the "in my name" guard, and the perfect tense of "overcome." No student is required to profess.

## The memory verse, John 16:33 (this unit's new plant, on L7)

Plant and teach it on L7, the final Thursday, whose single focus is this verse. ESV: "I have said these things to you, that in me you may have peace. In the world you will have tribulation. But take heart; I have overcome the world." Four fresh moves.

Peace in him, not in circumstances. The peace is located "in me." The circumstances stay hard, "in the world you will have tribulation." Teach the two halves as one honest sentence: the trouble is promised, the peace is real, and the peace sits in a person.

"I have overcome the world," already done. The Greek is a perfect, a completed victory whose result stands. Origen's line makes it land: the world is only ever as strong as its Victor allows. When students memorize this, they memorize a finished fact.

The honest promise of trouble plus the bigger promise of his victory. The verse refuses "everything will be fine." It promises tribulation and it promises his victory over the world that brings it. That honesty is why it holds up when a fifteen-year-old's life gets hard.

The answer to 14:1. The discourse opened with "let not your hearts be troubled" (14:1). It closes here. Show them the frame: the same night, the same worry, now answered by his overcoming.

Give the short Thursday its room by previewing 16:33 at the close of L6, so L7 is a second exposure and the first graded plant rather than a cold meeting. By L7 the students have already heard the tribulation, the joy no one can take, and his victory across L4 through L6, so the Thursday is the payoff. The other six lessons do not plant, teach, or quiz 16:33 as the graded verse. Keep the twelve prior anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35, 14:6, 15:5). The next new anchor is 17:3 in Unit 23. No optional stretch verse this unit; no John 16 verse is on the taught-not-memorized list, so the planted 16:33 is the memory work.

## Pitfalls with teenagers

- **The Spirit's conviction (16:8-11) made vague, or turned into a guilt-trip.** Teach the three clauses concretely: unbelief in Christ is the sin, Christ's going to the Father is the vindication, the ruler's condemnation is the judgment. Do not turn the verb into a proof-text for shaming students. The Spirit convicts the world of its verdict on Jesus, and he does it to bring people to Christ.
- **"Guide into all truth" (16:13) used to justify private new revelations or to bypass Scripture.** The "all truth" is the finished teaching about Christ, completed in the apostles and written for us. Ignatius already guarded it: the Spirit speaks Christ's things. The confessions ground it in the Spirit's witness to the written Word (1689 1.5). Guard against "the Spirit told me" untethered from the text.
- **The sorrow-to-joy promise (16:20-22) cheapened into "just be positive," or made a denial of real grief.** The grief is real and the tears are named (16:20). The joy comes through the sorrow, the way the child comes through labor. Do not let it become a slogan that tells a grieving student their pain is not real.
- **"Ask in my name" (16:23-24) turned into a magic formula or a prosperity promise.** The same guard as U19. Praying in his name is praying on the ground of his person for the Father's glory. It is not a cheat code, and it does not promise a comfortable life.
- **16:33 flattened into "everything will be fine."** The verse promises trouble and victory in the same breath. Keep both. A student who hears only "take heart" and misses "you will have tribulation" will feel lied to the first time life gets hard.
- **The Spirit made vague or spooky again.** The U17 and U19 guard. The Spirit here has a job: convict the world, guide into truth, glorify Christ. Keep him a Person with concrete work.
- **Making "it is to your advantage that I go" sound like the Spirit is second-best.** Chrysostom's guard: the Spirit's honor is great, and his coming is genuine gain. The bodily Jesus was in one place; the Spirit indwells all his people everywhere. The exchange is upward.

## Also worth emphasizing

- **The whole unit is a dying man telling the truth and comforting at once.** John 16 refuses to lie about the cost (persecution, expulsion, killing, scattering, tribulation) and refuses to leave them without comfort (the Advocate, the coming joy, the Father's love, the finished victory). That double honesty is the unit's pastoral key, and it is Adam's own key in sermon 28. Teach it that way and the searching student leans in, because it does not insult them with platitudes.
- **The handoff to U22.** Teach 16:7-15 fully in place. Then note lightly that the very next lesson gathers all the Paraclete sayings across the discourse. Do not preempt the synthesis. Let U22 do its work.
- **The "little while" confusion is a gift to the room.** The disciples say out loud, "we do not know what he is talking about" (16:18). That is permission for a student who does not understand to say so. Honesty about confusion is modeled in the text.
- **The Q3 project touchpoint.** John 16 is a chapter groups may teach in "Teaching the Farewell Discourse." This unit models landing each scene on Christ and naming the response he asks.

## The seven-lesson split

The seams cut on the chapter's own scene and thought boundaries, cover 16:1-33 with no gaps or overlaps, keep the Spirit's three-fold conviction (16:8-11) whole in one lesson, give both Thursdays (L2 and L7) a tight self-contained passage, match sermon 28 for the back half (16:16-33), mark 16:1-15 fresh-build, and land 16:33 in the final lesson. This corrects the naive split, which cut the conviction across two lessons and split the "little while."

- **L1 (i=96, Wed Feb 24, regular 50), John 16:1-7. Fresh-build.** The persecution warning given as comfort (16:1-4, expulsion and killing done as "service to God," tied to 15:18-25 and grounded by John 9:22, Acts 26:9-11, Romans 10:2-3), the disciples' sorrow at his going (16:5-6), and "it is to your advantage that I go away" (16:7, the Advocate comes because Christ goes). Lands on: Christ who forewarns his own to keep them, and whose going home opens the door to the Spirit.

- **L2 (i=97, Thu Feb 25, Thursday 36, single-focus), John 16:8-11. Fresh-build.** The Spirit convicts the world concerning sin, righteousness, and judgment. A tight, self-contained, famously hard passage that fills a single-focus Thursday and keeps the three clauses whole. One key question: "When the Spirit comes, he proves the world wrong about three things. What are they, and what does each one say about Jesus?" Lands on: Christ whose vindication the Spirit presses on the world, the sinless one it refused, now gone to the Father, whose enemy is already condemned.

- **L3 (i=98, Fri Feb 26, regular 50), John 16:12-15. Fresh-build.** The Spirit of truth who guides the church into all truth and glorifies Christ by taking what is his and declaring it (the Trinitarian ordering of 16:14-15, grounded against private revelation by Ignatius and the confessions). Note the light handoff toward U22 here. Lands on: Christ whom the Spirit magnifies, taking what is the Son's, which is the Father's, and declaring it to the church.

- **L4 (i=99, Mon Mar 1, regular 50), John 16:16-22. Sermon 28.** The "little while" and the disciples' confusion (16:16-19), then sorrow turning to joy and the woman in childbirth (16:20-22). Adam's sermon 28 covers this directly, joy produced through the pain rather than replacing it. Lands on: Christ whose cross turns his people's grief into a joy no one can take away.

- **L5 (i=100, Tue Mar 2, regular 50), John 16:23-28. Sermon 28.** Asking the Father in Jesus' name (16:23-24, tied to 14:13-14), the plain teaching to come (16:25), and the stunning 16:27, "the Father himself loves you," closing on 16:28, "I came from the Father, and go to the Father." Sermon 28's engine here is direct access to a Father who already loves them. Lands on: Christ who opens direct access to a Father who loves his people himself, and who came from the Father and returns to him.

- **L6 (i=101, Wed Mar 3, regular 50), John 16:29-32. Sermon 28.** The disciples' premature confidence (16:29-30), Jesus' "do you now believe?" (16:31), and the coming scattering held with "yet I am not alone, for the Father is with me" (16:32). Close the lesson by previewing 16:33 as a look-ahead, so the L7 plant is a second exposure. Lands on: Christ alone at the cross yet held by the Father's presence, steady while his friends scatter.

- **L7 (i=102, Thu Mar 4, Thursday 36, single-focus), John 16:33. Sermon 28. Plants John 16:33.** The single focus is the anchor verse and the climactic "I have overcome the world." The context built across L4 through L6 gives the short Thursday its room, and the previewed verse from L6 makes this the first graded plant rather than a cold meeting. One key question: "Jesus promises tribulation and victory in the same sentence. Where is the peace, and what makes 'I have overcome the world' something you can lean your whole weight on?" Lands on: Christ the victor over the world, whose finished conquest is his people's peace, answering "let not your hearts be troubled" (14:1).
-----
Student-facing, plain and warm; light prompts that lean on the Reading Journal and the discussion, not take-home busywork. Mark 'Go deeper' prompts optional. Keep it honest for a searching student.

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.16.1-7..16.33, JN.16.33`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
