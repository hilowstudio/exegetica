<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_reading_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-materials\\GEN_U20_reading-guide.md", "min_chars": 1500, "student_facing": true, "title": "Reading guide, Unit 20: Abide", "sermon": []} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 15:1-3..15:22-27.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.15.1-3..15.22-27] Help a 10th grader read John 15:1-3..15:22-27 with understanding and response. (grade 10, complexity 14)
      · Ground in: Scripture John 15:1-3..15:22-27
  - [JN.15.5] Know and review the unit memory verse John 15:5. (grade 10, complexity 9)
      · Ground in: Scripture John 15:5

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the per-unit STUDENT reading guide for U20 Abide (John 15:1-3..15:22-27).
Give a short follow-along block for each of these lesson passages, in order: John 15:1-3; John 15:4-5; John 15:6-8; John 15:9-11; John 15:12-13; John 15:14-17; John 15:18-21; John 15:22-27.
UNIT MEMORY VERSE: John 15:5 (ESV, with the review note).

FRAMING (Adam's theological framing for this passage; keep the student guide consistent with its rulings and emphasis, put in plain student language):
-----
# Framing: John 15:1-27, "Abide" (Unit 20)

Adam's theological framing for this unit, in his Theologian's voice (Reformed, exegesis-first, christotelic, grace-centered). Eight lessons inside the Farewell Discourse, two of them built on paired sermons: 26 "Abide in Christ" (15:1-11) and 27 "Love One Another" (15:12-17). The world's-hatred and Spirit-witness section (15:18-27) is a sermon-less fresh-build. This unit plants the new graded anchor, John 15:5, the sixth predicated "I am." Quote the ESV in the finished materials.

## The christotelic center

Christ is the true vine, and the whole life of his people flows out of him. On the same night, in the same room, the dying man who has been comforting frightened friends hands them the secret of everything they will ever do for God: stay joined to me. He is the true Israel where the old vineyard failed (15:1), the source of all fruit (15:5), the friend who lays down his life (15:13), the one who chose them before they chose him (15:16), the hated master whose servants share his lot (15:20), and the Christ to whom the Spirit and the church bear witness (15:26-27). The unit lands on Christ the vine, the engine of all fruit, obedience, love, and witness. It lands hardest at 15:5, where union with him is the one thing needful, and at 15:13, where the greatest love is his own life laid down.

- L1 (15:1-3) lands on Christ the true vine, the true Israel who succeeds where the old vineyard failed, who has already made his own clean by his word.
- L2 (15:4-5) lands on Christ the vine from whom the branch draws all its life, apart from whom his people can do nothing. Plants 15:5.
- L3 (15:6-8) lands on Christ in whom the true branch is held secure, whose Father is glorified in the fruit he himself produces.
- L4 (15:9-11) lands on Christ who loves his own with the Father's own love and gives them his own joy.
- L5 (15:12-13) lands on Christ whose laid-down life is the greatest love and the measure of the command.
- L6 (15:14-17) lands on Christ who makes servants into friends and who chose and appointed his own to bear lasting fruit.
- L7 (15:18-21) lands on Christ the hated master, whose servants are not greater than their Lord and share his rejection.
- L8 (15:22-27) lands on Christ the innocent sufferer hated without cause, testified to by the Spirit of truth and by his church.

## The contested points, ruled

**The true vine and the Israel background (15:1-2).** Rule this christotelic fulfillment. Israel was God's vineyard and failed to bear fruit: Psalm 80:8-19 (the vine brought out of Egypt, now broken down), Isaiah 5:1-7 (the vineyard that yielded wild grapes), Isaiah 27:2-3, Jeremiah 2:21 (planted a choice vine, became a wild vine). Jesus takes the image and calls himself the true vine (15:1), the real thing the old vineyard only pictured, the true Israel doing what national Israel could not. Adam's sermon 26 builds the whole opening on Isaiah 5 and lands it here: "Jesus has come to do perfectly what they have failed to do." The Father is the vinedresser (15:1). Rule the Father and Son one in essence and distinct in role, the guard Adam names so no one hears two different Gods; Chrysostom keeps the care shared, "the Father purgeth, but he keepeth them in himself, all is common."

**"Abide/remain in me" (meno), the heart of the chapter (15:4).** This is the load-bearing ruling. The verb is meno, to stay, remain, dwell, endure. It runs eleven times through 15:1-10 and is the most Johannine word in the book. Rule it union with Christ received by faith and lived by dependence. Adam's sermon 26 gets the category exactly right: abiding is a state of being before it is a state of doing, and the branch's whole job is to keep being what it is. This is Marshall's order in a picture, holiness received in union before it is practiced, the tree made good and then the fruit, fruit flowing from union. The confessions ground it on 15:5: our ability to do good works is not at all of ourselves but wholly from the Spirit of Christ (1689 and Westminster 16.3), and those implanted into Christ by a true faith bring forth fruits of thankfulness (Heidelberg Q64). Rule against the works-treadmill reading directly. Adam says it plainly: "your activities flow out of your abiding; your activities are not your abiding." Guard the opposite error too, under pitfalls.

**The Father who prunes, and the prune/clean wordplay (15:2-3).** Rule the wordplay deliberate and teach it. The verb in 15:2 is kathairo, to prune, its only use in the New Testament. The adjective in 15:3 is katharos, clean. Same root, back to back: "every branch that does bear fruit he prunes, that it may bear more fruit. Already you are clean because of the word that I have spoken to you." Rule the pruning the Father's loving discipline of a true branch to make it bear more, and rule "already clean" the settled, prior cleansing the disciples already have by Christ's word. This ties to 13:10, where the same katharos calls the disciples clean already, grounded in the word (the U18 flagship ruling). Adam's sermon 26 makes the wordplay the hinge: Jesus repeats himself so we will not miss that the agent by which we are pruned and cleaned is the word of Jesus Christ. Rule pruning as discipline aimed at more fruit (Hebrews 12:7-11). The knife that hurts is a Father's, never a judge's sentence.

**"Apart from me you can do nothing" (15:5).** Rule total dependence, and hold both guards at once. Augustine will not let the "nothing" soften: his words are not "without me you can do but little," they are "you can do nothing." Guard one kills self-reliant moralism: the branch produces nothing on its own steam. Guard two is the one teenagers need said out loud: total dependence is not permission to sit still and do nothing. The same confession that cites 15:5 (Westminster and 1689 16.3) finishes the sentence: believers are not hereupon to grow negligent, as if they were not bound to perform any duty unless upon a special motion of the Spirit. Effort is real and strenuous. It runs on borrowed life. The believer works hard, from a life already received.

**The branch thrown away and burned (15:6), the hard one.** Rule it carefully on both sides. "If anyone does not abide in me he is thrown away like a branch and withers, and the branches are gathered, thrown into the fire, and burned." Rule the burned branch a professing branch that was never truly united to Christ, and not a true believer who loses salvation. Cyril of Alexandria names the branch, those torn away by turning to what is wrong, and his example is Judas. Augustine: one of the two the branch must be in, either the vine or the fire. Hold it hard against 10:28-29 (Adam quotes it: no one will snatch them out of my hand), 6:37, and 1 John 2:19 (they went out from us, but they were not of us). Adam's sermon 26 does the pastoral work: do not let Jesus contradict himself, and do not build a doctrine of losing salvation out of a branch that was never grafted in. Guard both errors. Against easy-believism: outward nearness to the vine, church attendance, Bible facts, none of these is union with Christ. Against works-terror: a trembling believer must not be handed a scare. Adam's own move belongs in the room in spirit: "if you sincerely desire to be found in Christ, it's a really, really good sign." The fruit is confidence-building evidence of salvation, and not the price of it.

**Joy made full (15:11).** Rule this the goal of the whole vine teaching. "These things I have spoken to you, that my joy may be in you, and that your joy may be full." The abiding, the pruning, the fruit, all of it aims at the disciple sharing Christ's own joy, the joy the Son has eternally with the Father. Adam's sermon lands the section here on purpose: pruning is meant to be received by the joy of Christ. Rule against hearing 15:1-11 as a burden. Its stated end is fullness of joy.

**"Love one another as I have loved you" (15:12).** Rule this the new command of 13:34 (the U18 plant) now given its ground. In chapter 13 the command was planted with its measure, "as I have loved you." Here it is planted in the soil of abiding: only the branch drawing life from the vine can love like this. Fruit is love for the brothers. Rule it grace-first, the same Marshall engine, the love received before it is commanded.

**"Greater love has no one than this" (15:13).** Rule it first of Christ himself, then the pattern for his people. First Christ: he laid down his life for enemies, the wonder of Romans 5:8, which Adam's sermon 27 works at length. Then the pattern: as Christ laid down his life for us, we ought to lay down our lives for the brothers (1 John 3:16). Augustine guards the gap, that this is not an equality with Christ, whose death alone was shed for the remission of sins. Rule the christological order: his cross first as the ground, our sacrifice second as the fruit, never reversed, never our self-sacrifice with his cross cut out.

**"No longer servants but friends" (15:15).** Rule this stunning new-covenant intimacy, and guard it so it never cancels his Lordship. The friend knows the master's business; Christ has made known to them everything he heard from the Father. Irenaeus reads it covenantally: the Word drew slaves to God and then set them free, so the disciples become the friends of God as Abraham was. Guard against friendship read as chumminess that dissolves obedience. Augustine makes the guard from the text: two verses after "no longer servants," Jesus calls them servants again ("a servant is not greater than his master," 15:20). The bondage cast out is servile fear; the service that remains is the clean, filial love that endures. Adam's sermon 27 says it in his own key: to be a friend of God is to be a servant of God, because what he has done by grace has made him Lord. Friendship with the Son and submission to the Lord are the same relationship.

**"You did not choose me, but I chose you... I appointed you" (15:16).** Rule sovereign electing grace, taught as comfort and as mission, guarded against fatalism and boasting. Augustine is the anchor: he does not choose the good, but those whom he has chosen he makes good; there is no good work before faith, we were wicked and were chosen that by grace we might become good. Rule the purpose clause mission: "I appointed you that you should go and bear fruit and that your fruit should abide." Chrysostom keeps the vine running: I planted you, that you should extend yourselves. Election is a commission. Guard against fatalism (chosen means sent, go and bear fruit) and against boasting (grace is no more grace if merit comes first). Adam's sermon 27 lands it as assurance: it will be so; we have the confidence of assurance for those who are in Christ.

**The world's hatred and the servant-master line (15:18-21).** Rule the world's hatred the expected lot of those united to a hated Christ. "If the world hates you, know that it has hated me before it hated you." The believer is hated for union with Jesus and for his name (15:21). Rule 15:20, "a servant is not greater than his master," the echo of 13:16 (the foot-washing line) now turned toward suffering: if they persecuted me, they will persecute you. Chrysostom names the consolations Jesus gives the frightened few: they share his sufferings, they are not better than their Lord, and the Father is dishonored alongside them. Guard hard against weaponizing this into a persecution complex or a culture-war posture, under pitfalls. The hatred in view is hatred for Christ's name, borne the way he bore it.

**"They hated me without a cause" (15:25).** Rule Christ the innocent sufferer, fulfilling Scripture. The line quotes the Psalms (Psalm 69:4 and Psalm 35:19, with the "it is written in their Law" fulfillment frame, Luke 24:44). "Without a cause" rules out any guilt in him. The hatred is groundless, which makes it the sharpest evidence of the world's sin against the light: they have no excuse for their sin (15:22-24). The innocent one hated without cause is the Lamb without blemish.

**The Spirit of truth who bears witness (15:26-27).** Rule the Paraclete of 14:16-17, 26 now aimed at witness to Christ. "When the Helper comes, whom I will send to you from the Father, the Spirit of truth, who proceeds from the Father, he will bear witness about me. And you also will bear witness." Two witnesses, the Spirit and the church, one testimony, and its content is Christ. Hilary of Poitiers reads the verse for the Spirit's true deity and procession. Origen gives the title, Paraclete as comforter who bestows consolation by revealing spiritual knowledge. Rule the Spirit a Person with a job, the U17 and U19 point held: the Spirit's work here is to make Christ known and to make the disciples' witness to Christ effective. Guard against a vague Spirit, under pitfalls.

## Christological and covenantal connections

- **Christ the true Israel, the true vine.** 15:1 fulfills Psalm 80, Isaiah 5, Jeremiah 2:21. The old vineyard failed; the true vine succeeds. Jesus is what Israel was meant to be.
- **The sixth "I am."** The vine (15:5) takes its place in the line students hold: bread (6:35), light (8:12), door and good shepherd (10), resurrection and life (11:25), the way (14:6), now the vine, with two to come. John is building a case on purpose, and the room should feel it building.
- **Union with Christ as the engine of everything.** All fruit, obedience, love, prayer, and witness in this chapter run on abiding (15:4-5). Marshall and the double grace, holiness received in union and then practiced. Confessions 16.3 and Heidelberg Q64 ground it on 15:5.
- **The new command grounded in abiding.** 13:34 planted the command; 15:12 roots it in the vine. Love for the brothers is the fruit union produces.
- **Sovereign election as comfort and mission.** 15:16 with Augustine and Romans 8:30. Chosen, then appointed to go and bear lasting fruit.
- **The world's hatred and the servant-master line.** 15:20 echoes 13:16. Union with a hated Christ means sharing his rejection. Cross before crown, again.
- **The Spirit's witness to Christ.** The living-water thread (7:39), named Paraclete in chapter 14, now aimed at testimony (15:26-27). Try to look at the Spirit and you end up seeing Jesus, the U19 point, here made the church's mission.

## Reaching the three-tier room

The contact points are strong, because the chapter speaks straight to how a young person tries to be good, tries to belong, and handles being disliked.

- **The searching student.** Burnout and the exhaustion of trying to be good on your own steam (15:5, "apart from me you can do nothing," the most freeing line in the chapter for a try-hard). Wanting to belong and be connected (the branch drawing life from the vine). Being chosen when you did not choose first (15:16). Being someone's friend, and someone laying down his life for a friend (15:13). Being hated or left out for what you believe (15:18-20). Joy (15:11). The plain question: who talks like this the night before he dies, offering his friends his own joy and his own life?
- **The churched but passive student.** The mirror is the fruitless branch and the "already clean" word. You can attend, memorize, do religious things, and still be asking whether you are grafted in (15:6 with 1 John 2:19). Abiding is being in Christ, from which those things flow. Press it warmly, never as a scare.
- **The maturing disciple.** Give them the weight: meno as the Johannine heart-word, the kathairo and katharos wordplay, the "nothing" of 15:5 held by Augustine, the burned branch held with 10:28-29 and 1 John 2:19, Augustine on unconditional election in 15:16, the two kinds of "servant" resolving the friends-and-Lordship tension (Augustine on 15:20), and the Spirit's procession and witness (Hilary). Let them trace how one vine holds union, sanctification, assurance, election, love, suffering, and mission.

Keep faith content invitational and participation assignable. Every student can analyze the vine and branches, the two guards on 15:5, the ruling on the burned branch, the "as I have loved you" measure, and the Spirit's job. No student is required to profess.

## The memory verse, John 15:5 (this unit's new plant, on L2)

Plant and teach it on L2, inside 15:4-5, where the verse sits at the center of the vine teaching and gets a full regular period. ESV: "I am the vine; you are the branches. Whoever abides in me and I in him, he it is that bears much fruit, for apart from me you can do nothing." Three fresh moves.

The sixth "I am." Set it in the line students hold: bread (6:35), light (8:12), door and shepherd (10), resurrection and life (11:25), the way (14:6, last unit), now the vine. Tell them two remain. Let them feel John building the case toward it.

The vine-and-branches union. This is the picture of every other doctrine of grace they hold. The branch does nothing to make sap. It stays joined, and fruit happens. Abiding is being before doing. This is where "the tree made good, then the fruit" gets its clearest image in the whole Gospel.

"Apart from me you can do nothing" as the most freeing line for an exhausted try-hard. Teach it as good news. The kid grinding to be good enough, keeping score, running on their own steam, is told the pressure was never theirs to carry. The fruit is the vine's work through them. Augustine holds the "nothing" firm so the relief is total, and then the guard against passivity keeps that relief from curdling into doing nothing.

The other seven lessons do not plant, teach, or quiz 15:5 as the graded verse. Keep the eleven prior anchors sharp (20:31, 1:14, 1:12, 3:16, 4:24, 6:35, 8:12, 10:11, 11:25, 13:34-35, 14:6). The next new anchor is 16:33 in Unit 21. No optional stretch verse this unit; no John 15 verse is on the taught-not-memorized list, so the planted 15:5 is the memory work.

## Pitfalls with teenagers

- **Abiding turned into a works-treadmill.** The moment "abide" becomes a task to grind at, the gospel reverses. Keep it a state of being that produces doing. Adam's line is the guard: activities flow out of abiding, they are not the abiding.
- **Abiding softened into a vague "spend more quiet time" guilt-trip.** The church has long boiled 15:5 down to "pray and read your Bible," and then people measure fruit by streaks. Reading and praying are real means, and a person who plainly rejects Christ can also read and pray. Fruit is Christ taking lordship of a whole life and love that looks like his, and not a quiet-time count.
- **15:6 used to terrify a trembling believer.** The burned branch was never grafted in (Cyril names Judas; 1 John 2:19; John 10:28). Aim it at self-examination, warmly, never at making a scared kid doubt election. If a student panics, a sincere desire to be found in Christ is a really good sign.
- **15:6 softened into nothing.** The warning is real. Outward nearness to the vine is not union with it. Hold the edge and the comfort together.
- **"I chose you" (15:16) flattened into fatalism.** Election sends. The verse's own purpose clause is "go and bear fruit." Chosen means commissioned.
- **"I chose you" turned into a boast.** Grace chose us wicked, so no merit stands in front of it. The chosen have nothing to be smug about.
- **"Friends" (15:15) used to cancel Christ's Lordship.** The friend obeys and the servant obeys; what changed is knowing the master's heart. Two verses later Jesus calls them servants again. Friendship deepens submission.
- **"Greater love... lay down his life" (15:13) moralized into mere self-sacrifice.** Cut Christ's cross and it collapses into "be nice and sacrificial." Keep his death first as the ground (Romans 5:8), our love second as the fruit, and keep the guard that his blood alone was shed for sins.
- **The world's hatred (15:18-25) weaponized into a persecution complex or culture-war posturing.** The hatred in view is hatred for Christ's name, borne as he bore it, hated without a cause. Guard against a teenager reading it as license to be obnoxious and call the pushback persecution. A servant is not greater than his master, and the master was gentle.
- **The Spirit (15:26) made vague again.** Guard the U17 and U19 point. The Spirit of truth has a specific assignment here: bear witness to Christ and make the church's witness effective. Keep him concrete and Trinitarian.

## Also worth emphasizing

- **The chapter's own emotional arc is comfort.** It sits between "let not your hearts be troubled" (14:1, 14:27) and "in the world you will have tribulation, I have overcome the world" (16:33). Its stated goal is fullness of joy (15:11) and its stated frame is the friend who lays down his life. Teach the whole unit as pastoral care to frightened people, the way Adam preaches it.
- **The "rise, let us go" handoff from 14:31.** The prior unit ended with Jesus saying "rise, let us go from here," and the discourse continues into 15. The discourse is one movement across chapters 13 through 17. Note it for continuity without overexplaining.
- **The vinedresser's care is proportioned to his love for the Son.** Because Jesus is the vine and the Father loves the Son perfectly, the Father will not fail to tend the branches joined to him. The fruit will be so, which is assurance rather than pressure.
- **The Q3 project touchpoint.** John 15 is a chapter groups may teach in "Teaching the Farewell Discourse." This unit models landing every scene on Christ and naming the response he asks.

## The eight-lesson split

The seams cut on the chapter's own thought boundaries, cover 15:1-27 with no gaps or overlaps, keep the vine metaphor whole, keep the love section from splitting awkwardly, land 15:5 cleanly with room, and give both Thursdays a tight self-contained passage. Sermon 26 covers L1 through L4; sermon 27 covers L5 through L6; 15:18-27 is a fresh-build across L7 and L8.

- **L1 (i=88, Thu Feb 11, Thursday 36, single-focus), John 15:1-3: the true vine.** The true vine and the failed vineyard of Israel (Psalm 80, Isaiah 5), the Father the vinedresser, the prune-and-clean wordplay, and "already you are clean because of the word" (tied to 13:10). A tight, theologically loaded opener for the short day. One key question: "Jesus calls himself the true vine. True compared to what, and what does that make him?" Builds on sermon 26. Lands on: Christ the true vine, the true Israel who succeeds where the old vineyard failed.

- **L2 (i=89, Fri Feb 12, regular 50), John 15:4-5: abide in me. Plants and teaches John 15:5.** Abide (meno) as the heart of the chapter, the branch drawing all its life from the vine, and "apart from me you can do nothing." The plant sits cleanly inside this one lesson and gets the full regular period, taught as the freest line in the chapter for an exhausted try-hard. Builds on sermon 26. Lands on: Christ the vine from whom the branch draws all its life, apart from whom his people can do nothing.

- **L3 (i=90, Tue Feb 16, regular 50), John 15:6-8: the two branches.** The branch thrown away and burned (15:6, held with 10:28-29 and 1 John 2:19), the assurance work, answered prayer for the abiding (15:7), and the Father glorified in fruit that proves discipleship (15:8). The densest pastoral lesson, and it needs the full period to hold assurance and warning together without terror. Builds on sermon 26. Lands on: Christ in whom the true branch is held secure, whose Father is glorified in the fruit he himself produces.

- **L4 (i=91, Wed Feb 17, regular 50), John 15:9-11: abide in my love, joy made full.** As the Father loved the Son, so the Son loves his own (15:9); keep my commandments and abide in my love, as the Son kept the Father's (15:10); and the joy made full (15:11). This closes sermon 26's span and bridges toward the love command. Builds on sermon 26. Lands on: Christ who loves his own with the Father's own love and gives them his own joy.

- **L5 (i=92, Thu Feb 18, Thursday 36, single-focus), John 15:12-13: greater love.** The new command grounded in abiding (15:12, the 13:34 plant deepened), and "greater love has no one than this, that someone lay down his life for his friends" (15:13). A tight, self-contained scene for the short day that lands squarely on the cross. One key question: "Jesus names the greatest love there is. What is it, and who shows it first?" Builds on sermon 27. Lands on: Christ whose laid-down life is the greatest love and the measure of the command.

- **L6 (i=93, Fri Feb 19, regular 50), John 15:14-17: friends, chosen, sent.** "You are my friends" and no longer servants but friends (15:14-15), "you did not choose me, but I chose you, and I appointed you that you should go and bear fruit and that your fruit should abide" (15:16), closing with the command restated, "love one another" (15:17). Friendship, sovereign election, and mission held together. Builds on sermon 27. Lands on: Christ who makes servants into friends and who chose and appointed his own to bear lasting fruit.

- **L7 (i=94, Mon Feb 22, regular 50), John 15:18-21: the world's hatred.** If the world hates you, it hated me first (15:18-19); "a servant is not greater than his master" (15:20, echoing 13:16); persecution for his name (15:21). Fresh-build. Lands on: Christ the hated master, whose servants are not greater than their Lord and share his rejection.

- **L8 (i=95, Tue Feb 23, regular 50), John 15:22-27: no excuse, and the Spirit's witness.** The guilt of rejecting the light (15:22-24), "they hated me without a cause" (15:25, Psalm 69:4 and 35:19, the innocent sufferer), and the Spirit of truth who bears witness to Christ alongside the church's witness (15:26-27). The Paraclete climax closes the unit on Christ testified to. Fresh-build. Lands on: Christ the innocent sufferer hated without cause, testified to by the Spirit of truth and by his church.
-----
Student-facing, plain and warm; light prompts that lean on the Reading Journal and the discussion, not take-home busywork. Mark 'Go deeper' prompts optional. Keep it honest for a searching student.

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.15.1-3..15.22-27, JN.15.5`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
