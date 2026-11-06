<!-- Claude-in-chat prompt (no API). Generate the finished Markdown from the TASK below,
     obeying the SYSTEM rules and grounding ALL Scripture in the ESV via the study-bible
     tools. Save your draft, then finalize with the same subcommand plus --ingest <draft>
     (applies the guardrails and writes it, no API).
     meta: {"format": "bible_lesson_guide", "out": "C:\\Users\\adam\\study-bible\\docs\\john-lessons\\GEN_U5-L1-John-3-22-30.md", "min_chars": 3000, "student_facing": false, "title": "", "sermon": ["04 - They Shall Inherit the Earth (John 3-22-30).md"]} -->

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
Curricular location: Bible & Theology > New Testament Studies: Life and Doctrine in Christ > The Gospel of John > John 3:22-30.

Target learning objective(s) — teach or assess exactly these, matching each verb and cognitive level:
  - [JN.3.22-30] Teach John 3:22-30 faithfully so students grasp who Jesus is and the response he calls for (John 20:31). (grade 10, complexity 14)
      · Ground in: Scripture John 3:22-30

For each Scripture/confession anchor above, use the study-bible tools to quote the passage accurately and cite the confession/creed; do not rely on memory for wording or references.

Instructor's additional instructions: COURSE: Sophomore Bible (grade 10, mixed faith), verse-by-verse Gospel of John. SCHOOL: Yorkville Christian School - an evangelical private school structured like a public school, NOT a classical school (use the exact name 'Yorkville Christian School'; never a placeholder like [School Name]); use a plain, warm evangelical register and avoid classical-education idiom (no trivium, Latin, or recitation-culture framing). DESIGN INVARIANTS: reach a three-tier room in one artifact - a student new to the Bible who cannot yet find the passage, a churched but passive student, and a maturing disciple - with a low floor, a high ceiling, and no assumed knowledge; teach christotelically and land on Christ; treat the text as the living Word, not a document; quote all Scripture in the ESV and ground it in the study-bible tools. VOICE (see docs/john/John_Voice_Guide.md; applies to EVERY student- and parent-facing string): write as a warm, plain-spoken high-school teacher talking to fifteen-year-olds, not as an academic. HARD RULES, all absolute: (1) NO EM DASHES anywhere - use a period, comma, colon, or parentheses, or split into two sentences; the only exception is a Scripture quotation, which keeps the ESV's exact punctuation. (2) NO contrastive negation ('not X, it's Y' or any variant) - state the claim and stop: never deny one thing to assert another ('God's love isn't a feeling, it's a Son'; 'not just X but Y'; 'this isn't A, it's B'). The denial half is filler that fakes depth; write the real claim as a plain positive and stop. Especially watch big-idea and Christ-connection lines. (3) NO transitions or summary closers (Furthermore, Moreover, Additionally, In conclusion, Overall, It is important to note). (4) Concrete over abstract - name the actual thing; cut vague nouns like aspects, factors, elements, components, solutions, offerings. (5) Use contractions. (6) Sentence case for every heading, button, and label. (7) Concrete numbers and timeframes, not 'several' or 'soon'. (8) Vary sentence length; keep a point of view; cut hedging. (9) NO buzzwords (synergy, holistic, best-in-class, leverage), NO dead metaphors (cutting-edge, unlock, supercharge, the power of, dive in, journey), NO padding to three (tricolon), NO repeated openers (anaphora), NO metronome parallel clauses, NO hype or stacked intensifiers (blazingly, effortlessly, incredibly). Match the warm, plain voice of the course's hand-built exemplar lessons. NEVER output a bracketed placeholder like [email], [room number], [School Name], or [contact]. If you have no real value for a field, OMIT THE ENTIRE FIELD (including any Contact, email, or room line) - do not include it with a placeholder or left blank.

PRODUCE the teacher lesson guide for global lesson 20 of 150.
UNIT (use this exact name): U5 He must increase.  LESSON WITHIN UNIT: 1/2.
PASSAGE: John 3:22-30.  DAY TYPE: Regular (50 min) (use the matching variant).
MEMORY VERSES: on the 16-verse plan this unit is REVIEW ONLY. It introduces NO new memory verse, and none of its verses are memorized or quizzed. Do NOT plant, assign, plan to quiz, or invent a memory verse from this unit. If memory work comes up, say only that there is no new verse this unit and to keep the assigned verses sharp (John 20:31, John 1:14, John 1:12, John 3:16); the next new one comes in John 4:24 (Unit 6).
Propose the big idea, Christ connection, content objectives, and Reach/Hold/Stretch from the passage.

FRAMING (Adam's own theological framing for this fresh-build passage, in his Theologian's voice; treat it as his ruling: follow it on the contested points and land where it lands):
-----
# Framing: John 3:22-36, "He must increase" (Unit 5)

Adam's theological framing for this unit, in his Theologian's voice. Quote the ESV in the finished materials. Build L1 on Adam's sermon 04, "They Shall Inherit the Earth" (3:22-30).

## The christotelic center

Chapter 3 closes with the last man of the old order stepping back so the whole frame can fill with Christ. Jesus is the bridegroom who has the bride, the One who comes from above and is above all, the Son who holds the Spirit without measure and all things in his hand, and in whose hand rests every person's life. The unit lands on Christ as the bridegroom worth decreasing for, and as the Son the Father loves and has given everything, so that to have the Son is to have life. John the Baptist says the sentence the whole course asks its teacher and its students to say: "He must increase, but I must decrease" (3:30). That is joy at its fullest, a heart complete because the bridegroom has come.

## The setting: the purification dispute and "all are going to him" (3:25-26)

Rule it as jealousy handled by grace. A dispute arises between John's disciples and a Jew "over purification" (3:25), some argument about whose washing cleanses. It sours into rivalry, and John's disciples bring their teacher a complaint dressed as news: "the One you testified about, look, he is baptizing, and all are going to him" (3:26). They want John to defend his shrinking crowd. Adam's sermon reads the pressure exactly: they were tempting John to lean into his reputation while the crowds drained toward Jesus.

John answers on two levels, both grace-first. First, "a person cannot receive even one thing unless it is given him from heaven" (3:27). This is the truth Jesus taught Nicodemus with the wind and the Spirit (3:8) and the Prologue taught with "born of God" (1:13). The people crossing over to Jesus are God's gift to the Son, and John's own past influence was God's gift too. No one comes unless heaven gives him. Second, John never answers the purification question head-on, and then he answers it fully: real cleansing belongs to the bridegroom. His water pointed forward. Christ is where people are actually made clean (Ephesians 5:25-27). John hears an argument about purification and settles it by sending the bride to the bridegroom, the one who purifies.

Why John records it: to show the greatest prophet of the old covenant handing off cleanly, with joy, at the moment his ministry begins to shrink. The scene teaches that the growth of Christ's kingdom is God's work, received as gift, and that the right response to Jesus increasing is gladness.

## The friend of the bridegroom (3:29) and "He must increase" (3:30)

Teach the humility that is joy. The "friend of the bridegroom" is the shoshbin, the best man who arranged the wedding, guarded the bride, and brought the two together. His task ends the moment he hears the bridegroom's voice claiming his bride, and at that sound his joy is full. John says his joy is "now complete" (3:29) precisely as his crowd leaves. Calvin lands it: the friend honors the marriage and never claims the bride, and ministers represent the Son without appropriating what belongs to him alone.

This is humility that is confidence and joy, not low self-image. Adam's sermon does the heavy lifting through the meekness of the Beatitudes: meekness draws its lowliness from a secure status before God, a heart so sure of its standing that it can lower itself for the good of others. John can decrease because his identity as "friend of the bridegroom" is settled and unlosable. Guard this hard for teenagers. Decrease is a full heart making room for someone greater. The insecure student who already feels like nothing needs to hear that John's joy came from confidence, and that the confidence came from Christ.

The Greek reinforces it: John "rejoices with joy" (a Hebraic doubling) at the bridegroom's voice, and he who was "the voice crying in the wilderness" (1:23) now goes quiet so the bridegroom's voice can be heard. The voice makes way for the greater voice.

Tie the bridegroom motif backward and outward. Cana stands right behind this (Unit 3, 2:1-11): at a wedding where the wine ran out, Jesus supplied it, doing the bridegroom's own job and manifesting his glory. Here John names plainly what Cana pictured. Jesus is the true bridegroom. Then open the wider biblical wedding thread: God betrothing his people (Hosea 2:19), "your Maker is your husband" (Isaiah 54:5), Christ loving the church as a husband and cleansing her (Ephesians 5:25-27), and the marriage supper of the Lamb where the Bride is finally presented (Revelation 19:7-9; 21:9). The church is the bride, Christ is the groom, and John is glad to be the friend at the door.

Handle 3:30 the way Unit 3 handled 2:11: a key verse to teach and to offer as an optional stretch, kept off the graded memory line. It is short, famous, and load-bearing. Adam's sermon presses the word "must" (it is not that he should increase, it is that he must), the settled will of God from before the world. Teach that. Let a student who wants it carry 3:30 as a stretch. Do not add it to what is quizzed.

## 3:31-36: who is speaking, and what it teaches

Rule that the evangelist speaks. John the Baptist's words end at 3:30. From 3:31 forward the narrator meditates, the same voice that took over after Jesus finished with Nicodemus at 3:15 and gave us 3:16-21. The consensus is strong (the ESV, NIV, and NET all close the Baptist's speech at 3:30; Carson, Morris, Beasley-Murray, and others agree). The tell is internal: the vocabulary and viewpoint match the evangelist's meditation in 3:16-21, and a line like "no one receives his testimony" (3:32) reads as the Gospel writer's retrospect rather than the Baptist's live speech. Give the room this ruling in one sentence and move to the content. The scholarly question is not the lesson.

The content, taught plainly:
- "The one who comes from above is above all" (3:31). This picks up the Prologue directly. The Word was with God and was God (1:1), the Baptist already said "he ranks before me" (1:15), and Jesus told Nicodemus "no one has ascended into heaven except he who descended" (3:13). Jesus speaks from firsthand sight of heaven because he came from there. Every other witness, John included, speaks "from the earth."
- Testimony received or refused (3:32-33). Most refuse his testimony, an echo of 1:11, "his own people did not receive him." The one who does receive it "sets his seal to this, that God is true." Faith certifies God's truthfulness. The disciple tier can hear the sharp inverse from 1 John 5:10: to refuse the Son is to call God a liar.
- The Spirit without measure (3:34). God gives the Spirit to Jesus without limit, so his words are the words of God. Isaiah promised the Spirit resting fully on the Branch (Isaiah 11:2), and Acts 10:38 says God anointed him with the Spirit. Because the Son holds the Spirit in fullness, his speech carries God's own authority. Plant this lightly. It sets up the rivers of living water in chapter 7 and the Spirit he gives the church in chapters 14-16.
- The Father loves the Son and has given all things into his hand (3:35). This is the first clear sounding of a theme that runs to 5:20, 13:3, and chapter 17. For assurance it is enormous. The Son who holds "all things" holds your life (3:36).

## 3:36 and "the wrath of God remains"

Handle it the way Unit 4 handled 3:17-21: honest, unsoftened, unweaponized, the danger real and the rescue held out in the same breath.

Ground the words. "Whoever believes in the Son has eternal life" is present possession, not a distant reward, matched by 5:24, "he has passed from death to life." The verb under "does not obey" is apeitheo, to disobey or refuse compliance. John sets it opposite "believe," which tells us that faith in the Son is obedience to the Son, and refusing him is disobedience. Believing and obeying are one movement toward Christ. "Wrath" is orge, God's settled and righteous reaction against sin, not a temper. The verb "remains" is meno, the "abide" John loves: the wrath already rests on the person and stays there until he comes to the Son. This is the honest floor. Apart from Christ, wrath is the standing condition, and the gospel is its removal.

For a three-tier teenage room:
- Lead with life. The sentence opens with the free gift: believe in the Son and you have eternal life now. That is the headline, said first and said warmly.
- Name the wrath truthfully as the state Christ rescues from. "Remains" is the key. This is the condition every person is already in outside of Christ, and Jesus came to lift it, exactly as the bronze serpent lifted the venom in Unit 4 (3:14-15). Wrath is real, and it is the very thing the cross removes.
- Keep it off fear as a lever. Unit 4 ruled that fear diagnoses and never regenerates. Only the Son lifted up draws. Do not use 3:36 to frighten a student into a decision. Use it to make the gift precious.
- Keep faith invitational and participation assignable. Every student can say what the verse claims. No student is pressured to profess. The searching student hears an honest account of the stakes and an open door. The disciple hears why the gift matters.

The pastoral center: 3:36 is the reason the bridegroom came for the bride. Wrath that "remains" is what Christ steps between us and.

## Continuity

This unit seals two threads and reaches back into two chapters.

The witness-and-humility thread from Units 1 and 2 closes here. The Baptist said "I am not the light" (1:8), "I am not the Christ" (1:20), "among you stands one you do not know" (1:26), "the strap of whose sandal I am not worthy to untie" (1:27). Unit 5 is the last we hear from him, and his self-effacement is complete and glad: "He must increase, but I must decrease." Units 1 and 2 named this as the teacher's own posture, point at Christ and get out of the way. Unit 5 gives it its finished sentence.

3:31-36 echoes the Prologue point for point: from above (1:1-3), the Son who alone reveals God (1:18), testimony met with rejection (1:11), and believing to have life (1:12). And it picks up exactly where Nicodemus left off. Chapter 3 is one chapter with one shape, and naming that shape teaches students how John writes. Two witnesses speak (Jesus to Nicodemus, John to his disciples), and after each the evangelist meditates in his own voice (3:16-21, then 3:31-36). Both meditations say the same thing: the Son has come from the Father, believe in him and have life, refuse him and remain under judgment. Units 4 and 5 are one movement.

## The memory verse (review-only)

Unit 5 introduces no new graded verse. Students keep reviewing what they already hold: 20:31, 1:14, 1:12, and 3:16, planted in Unit 4. Run a light cumulative review, and L2's quieter close is the natural spot for it. Teach 3:30 as a famous key line and offer it as an optional stretch, exactly as Unit 3 treated 2:11. Keep 3:30 off the quizzed memory line.

## Pitfalls with teenagers

- Turning "decrease" into self-hatred or low self-image. Watch the anxious or insecure student who already feels small. John's decrease flows from a settled identity in Christ and a full heart. Teach it as confidence.
- Moralizing it into "be humble like John," a demand on the will. Humility this glad is the fruit of security in Christ and the Spirit's work, along the lines Marshall names: the tree is made good, then the fruit comes. Give the picture, then put Christ in their hands as its source.
- Flattening the passage to "don't be jealous." Comparison is the teenage room's daily air, followers and likes and status, so the point of contact is strong. The cure John gives is a secure identity as friend of the bridegroom.
- Weaponizing 3:36. Fear does not regenerate. Lead with the gift and let wrath make the gift precious.
- Softening 3:36 into vagueness. "Remains" is honest and present. Hold the danger and the rescue together, as Unit 4 held 3:17-21.
- Treating 3:22-26 as boring throat-clearing. The purification dispute is the hinge that opens onto the bridegroom.
- Spending the lesson on the speaker debate. Rule it in a sentence and teach the content.
- Over-teaching the wedding typology into loose allegory. Anchor it in Cana and the named Old Testament texts.

## Also worth emphasizing

- The two-half pattern of chapter 3, named for students, teaches John's method: a witness speaks, then the evangelist meditates. It binds Units 4 and 5 into one chapter with one message.
- 3:27 as a grace-first echo. "A person cannot receive even one thing unless it is given him from heaven" restates 3:8 and 1:13 from the Baptist's own mouth. The convert crossing to Jesus is God's gift to the Son. This guards against the decision-as-technique error and grounds the unit in grace.
- 3:33, "sets his seal that God is true." Faith certifies God's truthfulness. A clean beat for the disciple tier, sharpened by 1 John 5:10.
- 3:35, the Father's love for the Son and "all things into his hand." The first clear note of a theme running to 5:20, 13:3, and chapter 17. For assurance: the Son who holds all things holds your life (3:36).
- 3:34, the Spirit without measure. Jesus holds the Spirit in fullness, so his words are God's words. Plant lightly. It opens toward chapters 7 and 14-16.

## The two-lesson split

Both lessons are regular 50-minute exposition days. The seam is the text's own: the scene with the Baptist (3:22-30) and the evangelist's meditation (3:31-36).

- L1 (i=20, Mon Oct 5, regular 50), 3:22-30: the friend of the bridegroom. The purification dispute and the rivalry it stirs, John's grace-first answer ("a person cannot receive even one thing unless it is given from heaven," 3:27), the friend of the bridegroom whose joy is complete, and "He must increase, but I must decrease." Build on Adam's sermon 04 and its meekness frame: decrease is confidence and joy, not self-erasure. Tie the bridegroom back to Cana and out to the wedding thread (Hosea 2:19; Isaiah 54:5; Ephesians 5:25-27; Revelation 19:7-9). Teach 3:30 as the key verse, offered as an optional stretch, off the graded line. Lands on: Christ is the bridegroom, and the fullest joy is a heart glad to make room for him.
- L2 (i=21, Tue Oct 6, regular 50), 3:31-36: the One from above. Give the speaker ruling in a sentence, then teach the evangelist's meditation: the One from above is above all (the Prologue again), his testimony received or refused, the Spirit given without measure, the Father's love for the Son and all things in his hand, and the two roads of 3:36. Handle "the wrath of God remains" honestly, life first, wrath as the state Christ rescues from, no fear-lever. This is the natural place for the unit's cumulative memory review, since the unit plants nothing new. Lands on: to have the Son is to have life now, and the Son the Father loves holds your life in his hand.
-----

PAIRED SERMON (the instructor's own; derive the frame and emphasis, cite it, do not copy or read aloud):
-----
# They Shall Inherit the Earth (John 3:22-30)

**Series:** Gospel of John — Adam Vega Sermon Library
**Passage:** John 3:22-30

---

[00:00] Well, church, it's my pleasure to fill in one more week for pastor Michael. He'll be back in the pulpit next week and, and continue us through this sermon series on the Beatitudes. But I just wanted to call out to you guys, that this sermon series, if it's felt disorienting so far, just know that you're in good company. When Jesus speaks, he turns the universe upside down. Right?

[00:22] When when Jesus speaks, he speaks so counter culturally typically that our head start to spin as we try to make sense of the things that he says. And the beatitudes have been no different. And so, again, I wanna just kinda recap before I jump into this what exactly a beatitude is. Right? These are these are a series of statements that Jesus made to his disciples preceding the Sermon on the Mount.

[00:44] This is his introduction to the Sermon on the Mount. As he leaned in to teaching his followers, to teaching his disciples, he opened up with these series of statements, these two part statements called beatitudes. Now in the beatitudes, what he does is in the first part, he he announces a heart posture or a characteristic of the ideal disciple of Jesus, the ideal follower of Jesus. What he's doing is he's describing the people of God, the children of God, as he lays out the right heart posture, the right position, the right thinking of a disciple. And then he tacks on to those descriptions, these blessings, these here and now blessings as he says, blessed are.

[01:31] And when he says blessed are, he means blessed are. And so we're tempted when we when when we look at the beatitudes to treat it like wisdom literature, like we're in the Proverbs, or to treat it like law, like it's a command, like Jesus is saying, blessed are the meek for they shall inherit the earth. And and and what we wanna hear is you should become meek so that you can inherit the earth. We wanna make it law. Or we wanna hear it as wisdom literature, where where what we're saying is, it would be really good to be meek because there's reward associated with being meek.

[02:04] And so we should all try to be more meek. Really, both of these rob a little bit from what Jesus is actually doing, which he's making proclamations of truth. He's simply making declarative right now true statements that the meek are blessed. This is already true as he's speaking it, and it remains true today. And so if we if we take it and we wanna make it wisdom literature, we wanna make it law, we're gonna misunderstand it, and it's gonna start making us want to pursue something that in many ways we actually can't achieve.

[02:38] We actually can't pursue in our own strength. I'm gonna talk to you a little bit about that this morning. But in order to do that, I think first, we have to kinda try to get a right sense of what the word meek even means. I mean, meekness is so countercultural, especially in the Western culture, that I mean, opening up this sermon, like, thinking through, like like, doing my study, trying to prepare I I had to start with googling, what does meekness mean? Because meekness is such a I don't walk around talking about meekness.

[03:08] I don't I don't I don't pursue meekness. I don't I don't know that I know a lot of people that I would accurately describe as meek, because meekness oftentimes seems like weakness, and there's nothing more countercultural than desiring to be weak. Right? And so let let me just lay it out for you. Meekness is what you think it is.

[03:29] It's it's described maybe some if I wanna talk around it a little bit, it's humility, and it's lowliness, and it's gentleness, and it's quietness. Meekness is a heart posture of humility. And yet, there are a lot of ways to get to humility, and meekness gets to humility in a very specific way. And so, surely, you know humble people. I've even been called humble at times, and that blows my mind because you can arrive at humility a number of different ways.

[03:59] Some people are are humble because they've got nothing to brag about. Right? Some people are humble because they enter into a conversation, and they just acknowledge that I don't have anything to bring to this conversation, so I'm gonna shut up about it. And I'm I'm gonna I'm gonna step into this quietly, and I'm gonna be a learner here. I'm just gonna be a support a supporting voice here because I I I I acknowledge that I don't bring much to the table here.

[04:23] Humility can we can arrive there by kind of assessing ourselves and being like, okay. This isn't an area where it's appropriate for me to be proud. But when we step into an area where we're the experts or where we're we have accomplished some things, suddenly, we're no longer meek. Right? We're no longer humble.

[04:38] Now we wanna be the authority, and we wanna be assertive and all that. Right? Meekness draws its humility from something entirely different. It's not from a low self esteem or a low self regard. It's actually born out of a confidence a confidence that my status, that my name, that my security, that my approval is secure, and so secure that I don't need anything from you.

[05:04] That I'm not looking to draw from you your approval, or to impress you, or to get anything from you. And so what I'm able to do is I'm able to lay myself down before you and to make myself lower than I even am, because I don't need anything from you, because I'm so sure of my position with with with and it's and it's more secure than anything that you can offer me. See, if Jesus was described as meek, and he was, then meekness can't be a result of the absence of power. Right? It can't be the result of the absence of wisdom, because Jesus is all wise and all powerful, and yet he was meek.

[05:43] So what is it that makes meekness a unique form of humility is that it's actually born out of utter confidence of your status and estate, and specifically, what Jesus was teaching is your status and estate before God. Right? Jesus was the perfect example of meekness. We know this. Right?

[06:06] Like, Jesus being the one who, while he was in the form of God, didn't count equality with God as something to be grasped, but instead emptied himself out. Right? Taking on the likeness of man, being born in the likeness of man as a taking on the form of a servant and lowering self, humbling himself to the point of obedience, obedience to the point of death, even death on a cross, and yet now, he is highly exalted at the right hand of the father. This is Jesus. Like, he he showed us perfect meekness, the ability to lower oneself, to humble oneself so low that he can give himself away for the benefit of others.

[06:45] But the reason why Jesus said Jesus was able to do that is because of his sure confidence in the father, in his position with the father, in his position in eternity in heaven, as part of the tr
-----

Do any Scripture or study-bible tool lookups you need BEFORE you start writing. Between tool calls, emit no progress notes, plans, or commentary; your visible output must be the finished document and nothing else.
Produce only the finished resource in Markdown, beginning with the metadata header. End the main resource with a line `Standards: JN.3.22-30`.
If (and only if) this resource has answers, solutions, or model responses, put them ALL in a single final section — after a `---` rule and headed EXACTLY `## Answer Key` — and reveal no answers anywhere before it.
