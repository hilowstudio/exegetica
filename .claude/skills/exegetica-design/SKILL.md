---
name: exegetica-design
description: >-
  Design guidance for everything Exegetica shows or prints: web pages and
  components, layout and navigation, copy placement, the Reading Room, Prep
  Room documents, PDFs, books, covers, course pages, public pages, the
  wordmark and imagery. Holds the brief (who uses Exegetica, on what devices,
  the commitments that bind every design, the current look) and the procedure
  to follow on every design task. Use it before designing or changing any
  surface. Rules are added group by group as Adam locks them.
---

# Exegetica design

Built with Adam from `docs/design-study/`, a study of what CMU's HCII and RISD's Graphic Design department teach. Each rule carries a tag that says how firm it is:
- **Required**: law, a standard such as WCAG 2.2 AA, or a decision record.
- **House**: Adam's locked choice or standing feedback.
- **Evidence**: research, with the study note it comes from.
- **Convention**: established product practice.

Evidence may challenge a House rule (rule A11). Adam has the final say.

**Locked so far:** the brief, Group A (the procedure), Group B (learning), Group C (human-AI), Group D (accessibility), Group E (attention, ethics and privacy), Group F (interface craft), Group G (reading and screen typography), Group H (documents, PDFs and books) and Group I (marks, covers, imagery and colour), all 2026-11-08, Group J (information design) and Group K (the pre-ship checklist), 2026-11-09. Every group is now locked. The study notes in `docs/design-study/` stay as background, and `docs/design-study/skill-draft/README.md` keeps the list of approved work to design with Adam. `docs/design-guidance.md` is kept as a reference until Adam deletes it.

---

## The brief

### What Exegetica is

Exegetica is a Bible study and teaching tool for Yorkville Christian School in Yorkville, Illinois, made by A. James Vega (Hi Low Studio LLC). It answers from its own library of public-domain and openly licensed texts: Bible translations, lexicons, commentaries, church fathers, creeds and confessions, plus a Reading Room of about 15,000 books. Every reply still goes to an outside model provider.

Under the school's position statement, it is a reference work and a tool for teachers. It is never the teacher, never a companion, and never leads worship. Adam decided on 2026-11-08 that it may also be a practice tool, the way a workbook is (commitment 1, rule B3). (Sources: `docs/position-statement-christian-school.md`, memory `project-exegetica-identity`.)

### Who uses it

**Students with logins: grades 9 to 12, inside the school.**
- The school runs grades 6 to 12, but only freshmen and above get student logins. Student users are about 14 to 18 and never under 13 (Adam, 2026-11-08).
- They sign in with a school Google account, which chat requires (decision 0005).
- The school's handbook forbids AI generators unless a teacher approves the use in advance. The position statement allows a student to use AI only for a purpose a teacher has set, as a reference work whose results the student checks against the text.
- Adam's reading of his students is that many test the bot to make it break its rules. Few come to learn its proper use.
- So student interfaces are designed for adversarial use: no emotional hooks, no unprompted questions about how a student feels, and short fixed replies where code can decide (memory `feedback-student-chat-context`, decision 0011).

**Teachers.**
- Teachers of every grade, 6 to 12, can use Exegetica (Adam, 2026-11-08), so Prep Room materials and Reading Room books can reach middle-school classes through their teacher.
- They use the Prep Room and the Living Library (decision 0007).
- The position statement makes the teacher responsible for vetting, interpreting and teaching what AI produces. So teacher tools hand over raw material for a person to judge. They don't hand over finished teaching.
- Teachers are short on time.
- Still open: which teachers use the app today, and how often.

**Parents.** They don't sign in yet. They read the public pages: privacy, the position statement, the Quiet Standards statement and the FAQ. Those pages must make sense to a parent who has never used the app.

**Adam (the maker and admin).** He reads saved student studies as a mandated reporter (decisions 0009 and 0025). He runs `/ops`, the Media Studio and the covers tools. He probes the bot himself before any student prompt ships (decision 0014).

**Devices and settings.** Chromebooks, tablets and smartphones, in class and at home. Every surface works on:
- a small laptop with a keyboard and trackpad
- a tablet by touch, in either orientation
- a phone held in one hand

Input is mouse, keyboard and touch, often on the same page. School Chromebooks run Chrome with managed settings. Home devices can be old or slow. The rail becomes a bottom bar on phones.

### Surfaces

The rail shows each role its places (`webapp/shell.py`).

- **Everyone:**
  - **Chat** (`/`): study a passage with the library.
    - Each study accepts new messages for 24 hours and then opens read-only. Studies stop at 48 messages (decision 0015).
    - Daily caps and rate limits end in fixed text (0011).
    - Notes under each reply say what it drew on (0016).
    - The "Need help now?" window can open before or during a reply (0018).
  - **Scripture Memory** (`/memory`): saving and practising verses.
  - **Reading Room** (`/read`): the shelves and the book reader.
- **Teachers add:**
  - **Prep Room** (`/generate`): builds a resource from a book or from the standards. It has a Teacher and Student toggle, editing, revision by instruction, a PDF, and a source check.
  - **Living Library** (`/library`).
- **Admin adds:** **Media Studio** (`/studio`).
- **Public and built pages:** About and the FAQs, `/privacy`, `/position`, `/quiet-standards`, `/corpus`, `/ops`, the Yorkville course pages (always light), and the covers tool.
- **Printed and downloaded output:** Prep Room PDFs, course PDFs, books built by `scripts/book_pdf.py`, and a data export from Settings.

### Commitments that bind every design

Each of these already holds and has a source. Changing one needs Adam's decision, never a design argument.

1. **A tool that presupposes a person.**

   Exegetica may help students acquire information and skill the way a textbook or workbook does: look things up, practise, answer questions, get hints and feedback. Forming a person belongs to people: witness, love, handing on a way of life, accountability before God, and the bonds God makes through teaching.

   Luther wrote the Small Catechism for the head of a household to teach. The tool presupposed the person, and Exegetica's tools presuppose the teacher and the parent the same way.

   Every feature passes seven tests:
   1. **A person sets the purpose.** The teacher or the student chooses the task. The tool never decides what a student must learn or when they're finished with a subject.
   2. **It works on the task.** Questions, hints and feedback concern the text and the answer in front of it. It never reads the student's motives, feelings, character or standing.
   3. **It starts fresh with every reader.** No knowledge of the student and no memory across studies (decision 0002). What a student keeps belongs to the student. Anything that should be known about a student goes to a person, never to the model.
   4. **It holds no authority.** Practice feedback only. Grades of record, mastery for the school, discipline and verdicts on a student stay with the teacher. A person answers for the tool.
   5. **It offers no relationship and no witness.** No persona, no faith of its own, no claim to know or care for the student. Doctrine is stated in the third person (0001, 0006). The page's own copy may still be warm (B5).
   6. **It leads no worship and gives no counsel** (0010).
   7. **It hands students back to people.** Questions of faith, doubt, life or prayer go to a teacher, parent or pastor, and learning features feed what happens in class.

   Grounds:
   - Aquinas, *De Veritate* q.11: the teacher is a secondary cause who assists the learner's own growth. So the line is drawn by what is assisted, acquiring information and skill or forming a person.
   - Augustine, *De Doctrina Christiana*, prologue: God sends Cornelius to Peter, and Paul to Ananias.
   - Calvin, *Institutes* 4.3.1: God teaches through human ministers to bind us together in love.
   - James 3:1 and Hebrews 13:17: teachers will give an account.
   - Newman, "What Is a University?": the life of a subject is caught from those in whom it lives.
   - The Catholic and evangelical statements of 2025 and 2026 make the same claims. Verify their quotations and paragraph numbers against the source texts before citing them.

   Replies are labelled "Exegetica" and no persona is shown (0006). The bot discusses itself only to list its tools and sources (0001). So: no avatar, no name for the bot beyond the product, no "typing" personality, and no copy that speaks as if the bot has feelings or a relationship with the reader.
   *House* (Adam, 2026-11-08). *Required* (0001, 0002, 0006, 0010).
2. **No knowledge of a student** (0002).
   - The interface never welcomes a student back.
   - It never personalizes from what a student wrote.
   - It keeps no analytics on a student's topics or moods.
   - A student's own settings, verses and reading place belong to them and stay out of what the model sees.
3. **No AI-written worship** (0010). No prayers, devotions or exhortations. Where a resource calls for one, the document shows a placeholder for a person to lead.
4. **The Quiet Standards.**
   - No ads, analytics, notifications, streaks or gamification.
   - Design for the least attention needed.
   - People can download their data and delete their account (`docs/quiet-standards-statement.md`, decision 0013).
   - The November self-audit did not pass, and accessibility is one of the open gaps.
5. **Honesty about sources** (0016). Replies and documents say what they drew on. A reply that used no library tool says so.
6. **Plain, true answers** (memory `feedback-answer-philosophy`, decision 0022). Interfaces don't frame every question as a debate. Where churches truly divide, a short attributed note is enough unless the student asks for the comparison.
7. **Privacy stated truly** (0013, 0025).
   - The privacy page says only what is true.
   - Saved studies are readable by the maker and kept until June 1 of their school year.
   - Typefaces are served from Exegetica's own server, so pages send nothing to Google Fonts.
8. **Safety first in the layout.** The help window must open without delay, take focus, and work by keyboard and screen reader. The self-audit found focus does not move into it today (`docs/qsf-scorecard-exegetica-2026-11-02.md`, step 3).
9. **Limits explained plainly.** When a study closes, a cap is reached or a reply is refused, the reader sees a plain line saying what happened and what they can do next (0011, 0015).
10. **The house voice** (`docs/voice-and-copy.md`, lint `scripts/lint_voice.py`).
    - Concise.
    - No em dashes, contrastive negation, summary closers, flattery, or salience stamps.
    - Long documents read like books (memory `feedback-book-formatting-tells`).

### The look that exists today

- **Colour:**
  - One token set in `webapp/static/css/tokens.css`. No page may redefine it (`tests/test_rail.py`).
  - Light: paper `#f0e8dc` with ink `#1e2026`, rose accent `#8f3944`, plus iron and brass.
  - Dark: paper `#14151a` with ink `#e9e7e0` and accent `#e2858e`.
  - The secondary text colours were darkened (light) or lightened (dark) on 2026-11-08, so every text colour reads at 4.5:1 or better on every background, the garden included. `tests/test_contrast.py` checks every pair. In the light theme "faint" text is now nearly the same grey as "soft" text.
  - Light by default, dark when the system asks or the reader picks it.
- **Type:**
  - Spectral (interface serif), Public Sans (interface sans), IBM Plex Mono.
  - Fraunces for display, Libre Baskerville for tracked capitals.
  - EB Garamond for book text, with Literata as a reader setting.
- **Shared layout:** one shell for every page (`base.html`, `shell.py`), with a rail drawn by role. Every page sits on the chat page's garden, with the wordmark at the top of each page's own column. Each theme names its own garden in `tokens.css` (`--garden`): light mode uses a more colourful version (`garden-light.webp`, 2.2 times the colour) so it doesn't look washed out, and dark mode uses the original (`garden.webp`). Both lie under the paper colour at 86 percent, with paper as the fallback colour.
- **Locked by Adam:**
  - The house covers: cloth board, foil pattern and border only, engraved titles, never gold titles (memory `project-house-covers`).
  - The book interior: no provenance or translator credit in a book, and the interior follows the cover style (memory `project-exegetica-interior`).
  - PDFs: book-quality print rules, every chapter on a new page, and each Part on its own title page (memory `pdf-design`).
- **Known gaps** (a fresh audit on 2026-11-08: axe for WCAG 2.2 A and AA, a keyboard walk and a target-size check on 14 pages, both themes, three sizes. Full results are in the Group D draft.)
  - Secondary text colours on the garden fell below 4.5:1 at the image's darkest and lightest points. Fixed on 2026-11-08 by Adam's choice: adjusted text colours, a more colourful light garden, and the original garden in dark mode. `tests/test_contrast.py` guards it.
  - The audit's other findings were fixed the same day:
    - the course gold (`--gold-600`, now `#8b4f00`) and grey (`--steel-500`, now `#555e6c`) were checked against white, cream, the chips and the garden, and the test covers them
    - the two `/ops` tables became keyboard-scrollable regions
    - the covers tool's Go button uses `--on-accent`
    - every flagged target on teacher and admin pages is now 24 pixels or more
  - Still under 24 pixels, and exempt under WCAG 2.5.8:
    - the corpus page's source links, which sit inside sentences
    - the Studio's rewrite checkbox, which is the browser's default size
  - Chat, Scripture Memory and the Reading Room passed axe in the light theme, and every page could be walked by keyboard. Dark-theme reports of light text on white below the first screen were a measuring artifact (axe can't see the fixed garden). A paper background colour under the garden now prevents that.
  - The first full browser check (2026-11-09, `scripts/design_check.py`: every page, three roles, both themes, three sizes, axe, keyboard, targets, reflow at 320px, reduced motion) found and fixed: the standards page overflowing at 320px and its 23px links, two `/ops` tables widening the page, focus hidden under the covers dock, the Prep Room's wide tables, its credit-line target on touch, and Scripture Memory's list covering the page on a laptop. Students opening teacher places by URL now get a page that says who the place is for.

### Where the study bears most

The study notes in `docs/design-study/`, in order of weight for Exegetica:
1. **Learning science** (`07-learning-science.md`). The position statement treats the "friction" of learning as formation. The research agrees that retrieval, self-explanation and feedback build learning, and that being handed an answer does not.
2. **Human-AI interaction** (`09-human-ai-interaction.md`): calibrated trust, showing sources, efficient correction, saying what the system can't do, and the social-agent research behind "never a companion".
3. **Accessibility** (`08-accessibility.md`): WCAG 2.2 AA as the floor, with the self-audit gaps first.
4. **Persuasion and ethics** (`10-persuasion-ethics-privacy.md`): no dark patterns or engagement design for teenagers. Privacy for minors in a school (FERPA).
5. **Typography and editorial design** (`13-typography.md`, `15-grids-layout-editorial.md`): the Reading Room, PDFs and Prep Room documents.
6. **Interaction principles and evaluation** (`03-interaction-design-principles.md`, `02-evaluation-and-measurement.md`).

`00-index.md` maps every note and lists the claims to treat with care.

### Working with Adam

- **Scope:** everything Exegetica makes. The web interface, Prep Room documents, PDFs, books, covers, course pages, public pages, the wordmark and imagery. Locked rules for covers, interiors and PDFs are carried as they stand.
- **Disagreement:** see A11.
- **Older guidance:** `docs/design-guidance.md` and its memory copy are a reference only, until Adam deletes them.

---

## A. Procedure for every design task

The rules run roughly in order. Small changes can skip the steps marked *(substantial work)*.

**A1. Start from the person and the job.** Before designing, write one line: who uses this (role, device, place), what they are trying to get done, and what could go wrong for them. On a student surface, add how a student who wants to break the bot would misuse it.
*Evidence* (goal-directed design, `03`, and user research, `01`). *House* (memory `feedback-student-chat-context`).

**A2. Read what binds the surface first.**
- For chat behaviour, prompts, sign-in, model choice, run limits or the public statements, read the matching decision record in `docs/decisions/` (CLAUDE.md).
- For covers, book interiors and PDFs, read the locked rules in memory (`project-house-covers`, `project-exegetica-interior`, `pdf-design`).
- Check the design against the ten commitments above.
*Required.*

**A3. Start from the familiar pattern.** Name how well-made products solve the same job and start from that pattern. Depart from it only where an Exegetica commitment or the evidence calls for it, and say why. People bring their expectations from other products.
*House* (memory `feedback-ux-craft`). *Convention* (Jakob's law, `03`).

**A4. Explore before committing** *(substantial work)*. Sketch two or three distinct approaches in words, ASCII or quick HTML, and show them side by side. When the choice is Adam's, he picks. People give more honest criticism when they see several designs, and parallel exploration produces better results than polishing the first idea.
*Evidence* (Buxton, Tohidi et al. 2006, Dow et al. 2010, `04`).

**A5. List every state before building.**
- first use and empty
- loading
- partial and full
- error
- slow or offline
- closed, capped or refused (decisions 0011 and 0015)
- signed out
- each role that sees it (student, teacher, admin)
- light and dark
- keyboard focus
- long content (long titles, long verses, translated text)
- the help window opening over it (decision 0018)

A design that shows only the happy path is unfinished.
*Evidence* (feedback and error design, `03`). *Convention.*

**A6. Design for three screens and three inputs.** Every surface works on:
- a small laptop with a keyboard and trackpad, around 1366 by 768
- a tablet by touch in both orientations, around 820 by 1180
- a phone held in one hand, around 390 by 844

Mouse, keyboard and touch can each reach every action.
*House* (the brief). *Required* (WCAG 2.2 AA keyboard, reflow and target size, `08`).

**A7. Build with the shared system.**
- Colours come only from `tokens.css`.
- Pages use the shared shell and existing components.
- A new pattern becomes a shared component when a second page needs it.
- Content stays separate from styling: generated documents carry structure, and a fixed stylesheet carries the design.
*House* (`tests/test_rail.py`, memories `webapp-frontend` and `pdf-design`).

**A8. Look at it before calling it done.**
- Run the app locally with the database and storage settings blanked (memory `webapp-frontend` has the launcher).
- Screenshot every state from A5, in both themes, at the three sizes from A6.
- Read the screenshots.
- Print output gets rendered to PDF and read page by page.

A plain interface that merely works isn't done.
*House* (memory `feedback-ux-craft`).

**A9. Run three passes before handing back.**
1. A heuristic pass against Nielsen's ten heuristics.
2. An accessibility pass: a keyboard walk, visible focus, contrast for every new colour pair in both themes, target sizes, accessible names, and reduced motion.
3. A voice pass on every word of copy (`scripts/lint_voice.py`).

Anything mechanical that the passes check gets a test so it stays fixed. Run `python -m pytest`.
*Evidence* (`02`). *Required* (`08`, CLAUDE.md). *House* (voice rules).

**A10. Ask for real users through Adam.** When a design question needs evidence from students or teachers, propose a small test: about five people, realistic tasks, think-aloud, and what would count as success. Adam runs or approves it. Claude never probes the student bot on Adam's key.
*Evidence* (`02`). *House* (memory `feedback-manual-probing`).

**A11. Challenge with evidence, then follow Adam's decision.** When a request or a house rule runs against the evidence or a commitment, say so once, cite the source in `docs/design-study/`, and propose the alternative. Adam decides, and his decision is added to this skill as a House rule.
*House* (2026-11-08).

**A12. Report plainly.** Say:
- what changed
- what was checked, and how
- what couldn't be checked
- any open conflict with the evidence

No process narration. Long jobs get a plan and a time estimate up front and a short update at each milestone. Findings that need Adam's call stop the work.
*House* (memories `feedback-stay-focused`, `feedback-no-blind-stretches`, voice rules).

---

## B. Learning, and how the tool asks students to work

How Exegetica's surfaces support learning. Study notes: `docs/design-study/07-learning-science.md`, plus `09` for the AI side.

**Adam's decision (2026-11-08):**
- Chat may quiz and coach, with a Socratic element, so students master the material instead of only looking answers up.
- The full experience gets designed with Adam as its own project.
- B3 sets the limits that hold until then.
- A textbook or workbook has activities, guides and quizzes and is still no teacher. Commitment 1 in the brief draws that line.

**B1. Chat sends the student to the text.**
- After the answer, the most prominent things in a reply are the passages and library sources it drew on.
- Every Scripture reference opens the passage in its context. Every quoted source is named. The whole chapter is one step away.
- Reading the passage is the student's own work, and it's the part that teaches.

*Required* (position statement, decision 0016). *Evidence* (generation and the doer effect, `07`).

**B2. The student's thinking stays the student's.**
- No control, suggestion or shortcut offers to produce a student's work: no "write my paragraph", no "summarize this for my assignment".
- Shortcuts are study moves:
  - show the passage
  - cross-references
  - compare translations
  - define a word
  - show where the passage is discussed
  - quiz me on this

*Required* (the student brief in `webapp/app.py`, which leaves the first draft of graded work to the student, the school's AI policy).

**B3. Chat may quiz and coach, Socratically, inside a study.** Coaching has to pass the seven tests in commitment 1. Until the full experience is designed with Adam, these limits also hold:
- **Questions before answers when the student is learning.**
  - Ask the student to read, recall or explain first.
  - Then give hints in steps.
  - Then give the answer with its source.
  - The source passage is always one tap away.
  - The evidence: high-school students given open chatbot access did better on practice but worse on the exam once access was removed. A tutor version that gave hints in steps and withheld answers largely avoided that harm (Bastani et al., PNAS 2025: about 1,000 students in Turkey, an exam drop of 17 percent with open access). A structured AI tutor built on these methods beat an active-learning class (Kestin et al., Scientific Reports 2025). That study covered 194 Harvard physics undergraduates, two topics and short-term tests, with the tutor as a complement to class. Self-explanation, retrieval and step-level feedback are the methods behind both (`07`).
- **The student or the teacher chooses it.** Coaching is something a student starts for a study or a teacher sets as the purpose. Plain reference lookup stays available and is never turned into a quiz uninvited.
- **Inside one study only.**
  - The model sees the current study and nothing else about the student.
  - No record of mastery carries from one study to the next.
  - Nothing a student did comes back to the model later.
  - Decision 0002 says only a change to the position statement can lift this.
- **Coaching is about the text and the student's answer, never about feelings.** Questions, hints and feedback concern the passage and what the student wrote. The model never asks how the student feels and never speaks of feelings of its own (commitment 1, memory `feedback-student-chat-context`).
- **Through the gate.** Any change to chat behaviour gets a decision record and Adam's probe before students see it (0014).

*House* (Adam, 2026-11-08). *Evidence* (`07`, Bastani et al. 2025, Kestin et al. 2025). *Required* (0002, 0014).

**The position statement.** Under commitment 1, a quizzing, coaching study is a tool, as a workbook is. The statement's student section says AI is used "only as a reference work". When the feature is built, its decision record adds "and a practice tool" there, so `/position` stays true to what the app does.

**B4. Practice tools make students recall, and bring verses back.**
- Scripture Memory's eight steps move from reading to recall with the text hidden. Keep that ladder.
- Mastered verses come back for review on a growing schedule, after days and then weeks. The page shows which verses are due. Memory fades unless retrieval is repeated over growing intervals.
- Due verses appear only inside Scripture Memory, never as a notification, email or badge elsewhere (commitment 4).
- Progress is shown as what the student can recall. No streaks, points or levels.
- The verses and their history belong to the student and never reach the model (0002).

*Evidence* (retrieval practice and spacing, Dunlosky et al. 2013, `07`). *House* (Adam approved spaced review, 2026-11-08, as a feature to build). *Required* (Quiet Standards, 0002).

**B5. The bot's feedback is about the work, and the page's own copy can be warm.**
- The model's replies:
  - say what was right or wrong and where in the text to look
  - never praise the student
  - never bond with the student
  - never speak as though a relationship exists
- Copy we write for the page (empty states, labels, step instructions, encouragement) can be expressive and warm. "Keep going." is fine. Don't be pedantic about it.

*House* (Adam, 2026-11-08). *Evidence* (feedback about the task works better than feedback about the self, Hattie and Timperley 2007, `07`). *Required* (position statement, "never a companion").

**B6. Prep Room resources are built backward.**
1. Start from the objective, written with an observable verb.
2. Then decide what would show the student has learned it.
3. Then plan the activities that get them there.

Formats ask for that order and show it in the teacher version: objectives, the assessment that matches them, practice before assessment, and a key that explains its answers. New skills get worked examples first, with support withdrawn over later items.

*Evidence* (backward design, constructive alignment, the worked-example effect, `07`).

**B7. Quiz items follow your quiz rules and the item-writing rules.** This applies in the Prep Room and in any quiz that chat gives.
- Every item maps to an objective that was taught.
- Open-Bible items ask what the text says.
- A wrong answer is never a defensible reading of the text.
- Distractors come from the misreadings the lesson guards against.
- Views students sincerely hold, which the lesson doesn't take up, stay out of the quiz entirely.
- One best answer, a clear stem, no "all of the above", no grammatical cues.

*House* (memory `john-chapter-quizzes`). *Evidence* (item writing, `07`).

**B8. Teacher tools hand over material for the teacher to judge.**
- Everything the Prep Room makes can be edited before it reaches students.
- It shows its sources and keeps the teacher version apart from the student version.
- Nothing goes to students without passing through the teacher.
- Prayers and devotions stay placeholders for a person to lead (0010).

*Required* (position statement, 0007, 0010).

**B9. Keep the effort that teaches, and remove the effort that doesn't.**
- Recalling, reading the passage, answering a Socratic question, and writing in one's own words are the effort the position statement calls formation. Keep them.
- Hunting for a control, losing one's place, unreadable type and unexplained limits teach nothing. Remove them wherever they appear.

*Evidence* (desirable difficulties, Bjork 1994, `07`). *Required* (position statement).

**B10. Cut what competes with the material.**
- Study surfaces carry no decorative images, sounds or motion.
- Explanations sit next to what they explain: a gloss beside its word, a reference beside its quotation.
- Long material comes in sections the reader controls.
- Headings signal structure, and conversational surfaces use them sparingly.

*Evidence* (Mayer's coherence, contiguity, segmenting and signaling principles, `07`). *House* (memory `feedback-book-formatting-tells` for long documents).

**B11. Default to the support the reader needs, and let readers turn it down.** On student surfaces that means a ninth-grader. Prep Room documents fit the grade band the teacher picks, down to grade 6.
- Terms are defined the first time they appear, and Greek and Hebrew get glossed.
- Readers can hide supports they no longer need.
- Every such change is the reader's own setting, never inferred from their behaviour (0002).

*Evidence* (expertise reversal, `07`). *Required* (0002).

**B12. Motivate through competence and choice, never through the bot as a relationship.**
- Give students real choices (passage, translation, coaching or lookup, type settings), a clear view of what they can now do, and the use of what they're learning.
- Belonging comes from teachers, parents and classmates.
- The bot offers no mascot, rewards, praise or companionship. The page's own copy may encourage (B5).

*Evidence* (self-determination theory, expectancy-value, `07`, and the social-agent research, `09`). *Required* (position statement, "never a companion").

**B13. Every learning design works for every learner.**
- Material works on screen and on paper, at the three screen sizes, through a screen reader, and with the reader's own type settings.
- Students can show what they know in more than one form where the teacher allows it.

*Evidence* (Universal Design for Learning, `07`). *Required* (WCAG 2.2 AA, `08`).

**B14. Judge learning designs by learning.**
- Evidence that a design works is what students can recall or do later, and what the teacher sees in their work.
- Time spent, messages sent and visits never count as evidence of learning. Measuring them would also run against the Quiet Standards and 0002.

*Evidence* (evaluation levels, `07`). *Required* (0002, Quiet Standards).

---

## C. Human-AI: sources, trust, errors, limits, never a person

How the interface presents what the model does. Study note: `docs/design-study/09-human-ai-interaction.md`, especially Microsoft's 18 guidelines and Google's People + AI Guidebook, plus `06` on trust in automation. Changes to what the model says go through decision records and Adam's probe (0014). These rules govern how it appears.

**C1. Say what it can do and what it won't, where the student starts.**
- The empty chat names what Exegetica is for: studying a passage with the library, and practising with it once the Socratic study exists.
- It names what the library holds.
- It names what Exegetica won't do: discuss itself, write prayers or devotions, or write graded work.
- The FAQ under the ⓘ icon covers the rest.

People form their picture of an AI system from the first screens, and a wrong picture leads to misuse or abandonment.
*Evidence* (Microsoft guidelines 1 and 2, the PAIR "mental models" chapter, `09`). *Required* (0001, 0010).

**C2. Show the work as it happens, in plain words.**
- The status line names the real stage, which the server sends (studying, looking it up, reading, writing, checking).
- Tool chips show what is being consulted.
- Progress is never faked, and the reply never narrates as a person ("let me think", "I'm looking").

Visible system status is the first usability heuristic.
*Evidence* (Nielsen, `02`). *Required* (0001, 0019). *House* (the shared status line in `shell.js`).

**C3. Every claim leads back to something checkable.**
- References open the passage.
- Quotations name their source.
- The note under a reply says what it drew on, including "No library resource was consulted for this response."
- The Prep Room's source check lists what it found and what it couldn't.
- Nothing is labelled "verified", because the checks only say what was found where.

Trust should rest on the text the student can open.
*Required* (0016). *Evidence* (calibrated trust, `09`).

**C4. Confidence in the words, matched to the evidence.**
- Where Scripture or the creeds speak plainly, the reply says so plainly.
- Where something is uncertain (a textual variant, a disputed reading, a gap in the library), the reply says so in words. Never with percentages or scores.
- The interface adds no confidence meters.

People over-trust confident systems and stop trusting systems that hedge everything. The goal is trust that matches how good the answer really is.
*House* (memory `feedback-answer-philosophy`, decision 0022). *Evidence* (Lee and See 2004, the PAIR "explainability and trust" chapter, `09`).

**C5. Make checking and correcting cheap.**
- A student can always ask where a claim comes from, open the source, compare translations, or start a new study.
- In the Prep Room, a teacher can edit any line, revise by instruction, and see the source check before using anything.

- A way to report a wrong or troubling reply is approved to explore (Adam, 2026-11-08). It sends the flagged reply to Adam, who can already read saved studies (0009), and adds no new knowledge about the student.

Efficient correction is how people recover from AI mistakes, and AI makes mistakes.
*Evidence* (Microsoft guidelines 7 to 9, `09`). *Required* (0007, 0016).

**C6. Failures say what happened and what to do, with no model names.**
When the model or the library fails, a reply is refused, or a step limit is reached, the reader sees:
- one plain line about what happened
- what they can do next (try again in a minute, ask a narrower question, start a new study)
- the study still intact

Messages never name a model and never blame the reader. Student chat already falls back silently and shows fixed text.

Fixed on 2026-11-08: the Prep Room's fallback notice now reads "The first model couldn't answer, so a backup wrote this draft." (`FALLBACK_NOTICE` in `webapp/providers.py`, covered by `tests/test_policy_and_loop.py`).
*Evidence* (PAIR "errors and graceful failure", Nielsen heuristic 9, `02` and `09`). *Required* (memory `project-exegetica-identity`: the model is never named, plus the voice rules).

**C7. The interface never presents a person.**
- Replies are labelled "Exegetica".
- Fixed copy refers to Exegetica in the third person.
- No avatar, face, name, or animated dots that imitate someone typing. The status line says what is happening instead.
- No "I" in any fixed text the app writes for the bot.

People apply social rules to anything with human cues, so the cues are left out on purpose.
*Required* (commitment 1, decisions 0001, 0006, 0019). *Evidence* (the media equation, Reeves and Nass 1996, `09`).

**C8. Rules are published on pages. Chat never explains them.**
- Questions about Exegetica itself get the fixed reply that points to the FAQ.
- Reasons live on the FAQ, privacy and position pages, linked where the question comes up.
- Every rule explained in chat becomes the next thing a prober pushes on.
*Required* (0001). *House* (memory `feedback-student-chat-context`).

**C9. Limits are fixed text, the same every time.**
- A closed study, a daily cap, a rate limit or a drifted study each gets one fixed, plainly worded line from code, saying what happened and what the student can do next.
- The same wording every time. Never improvised by the model.
*Required* (0011, 0015). *House* (commitment 9).

**C10. The help window is never in the way of help.**
- It opens on top, takes focus, and reads first to a screen reader.
- It lists verified resources and closes easily.
- It is reachable again from the rail's help link.
- It looks like help. Never like an ad, a scold or an error.
*Required* (0018). *Evidence* (accessibility, `08`).

**C11. When a request is out of scope, narrow it and hand it to a person.**
- A request beyond what the library supports, or one that belongs to a person (personal advice, counsel, a crisis), gets a narrowed answer and a pointer to a teacher, parent, pastor or the help window.
- The interface shows that hand-off plainly.
*Evidence* (Microsoft guideline 10, "scope services when in doubt", `09`). *Required* (commitment 1, test 7).

**C12. Teachers get raw material for their own judgment.**
- Prep Room output is shown as a draft for the teacher to vet: editable, with its source check beside it, and with the teacher and student versions apart.
- Nothing is presented as reviewed or approved.
*Required* (position statement, 0007, 0016). *House* (rule B8).

**C13. Design the wrong path first.** For any AI feature, design and screenshot these before the happy path:
- the wrong answer
- the low-confidence answer
- the refusal
- the probing student

Adam probes the student-facing path before it ships.
*Evidence* (prototyping AI with realistic errors, `04`, Microsoft's "when wrong" guidelines, `09`). *Required* (0014). *House* (rule A5).

---

## D. Accessibility and the three screens

Exegetica serves every student at the school, on Chromebooks, tablets and phones, in class and at home. Study note: `docs/design-study/08-accessibility.md`. WCAG references are to version 2.2.

The 2026-11-08 audit and its fixes are recorded under "Known gaps" in the brief. The garden decision is under "The look that exists today".

**D1. WCAG 2.2 AA is the floor for everything Exegetica makes.** That covers the app, the public pages, the course pages, and the PDFs and documents it produces. Where this group asks for more, it says so.
*Required* (WCAG 2.2, the Quiet Standards self-audit).

**D2. Measure contrast against the real background.**
- Text needs 4.5:1, and large text 3:1.
- Control edges, focus rings and meaningful graphics need 3:1.
- Both themes.
- Measure against what is actually behind the text, which is the garden at its worst point wherever text sits on it.
- A test computes the token pairs, so a colour change can't quietly break contrast.
*Required* (1.4.3, 1.4.11). *House* (rule A9).

**D3. Everything works by keyboard.**
- Every action is reachable with Tab and works with Enter or Space.
- The order follows the page.
- Focus is always visible, and sticky bars never hide it (2.4.11).
- No traps.
- Rows and cards that open something are real buttons or links.
- Dialogs take focus in and give it back on close.
*Required* (2.1.1, 2.1.2, 2.4.3, 2.4.7, 2.4.11).

**D4. Names, roles and states come from real HTML first.**
- Use native buttons, links, inputs, headings and landmarks.
- Icon-only controls get an accessible name.
- State is exposed (pressed, expanded, selected, current).
- Each page has one main heading and a sensible heading outline.
- ARIA is used only where HTML has no element for the job.
*Required* (1.3.1, 4.1.2). *Evidence* (WebAIM Million: pages with ARIA average more errors, `08`).

**D5. What changes on screen is announced without moving focus.**
- Streamed replies, notes under replies, limit messages, toasts and status lines are announced politely to screen readers.
- The help window is a dialog that takes focus at once (0018).
- Only the status line's stage is announced, never every word as it arrives. That much is already built.
*Required* (4.1.3, 0018).

**D6. Every target meets the minimum.**
- Every control is at least 24 by 24 CSS pixels, or spaced as WCAG allows (2.5.8).
- Above that, size is a design choice made for the surface and its look.
- Touch screens are still in mind: Apple and Google suggest 44 to 48 pixels for comfortable tapping (`05`), which is worth weighing on surfaces students use mostly by touch.
*Required* (2.5.8). *House* (Adam, 2026-11-08). *Convention* (Apple, Material).

**D7. Three screens, both orientations, any zoom.**
- Every surface is designed and checked at about 1366 by 768, 820 by 1180 and 1180 by 820, and 390 by 844 (A6).
- Content reflows at 320 CSS pixels wide without sideways scrolling.
- Text enlarges to 200 percent.
- Layouts survive the text-spacing override.
- Zoom is never disabled.
- When the on-screen keyboard opens, the composer stays visible.
- Phone layouts respect the screen's safe areas.
*Required* (1.4.4, 1.4.10, 1.4.12, 1.3.4). *Convention.*

**D8. Touch never hides an action.**
- Nothing works only on hover.
- Every swipe, long press or drag has a visible button that does the same thing.
- Dragging always has a single-tap alternative.
*Required* (1.4.13, 2.5.1, 2.5.7). *Evidence* (gesture discoverability, `05`).

**D9. Motion and sound are opt-in and calm.**
- Honour reduced-motion settings.
- Nothing flashes more than three times a second.
- No sound plays by itself.
- Motion explains a change and never decorates.
*Required* (2.3.1, 2.2.2). *House* (the Quiet Standards).

**D10. Text is readable and the reader controls it.**
- Body text on screens is at least 16 CSS pixels.
- Sizes are set in rem, so the device's text size setting works.
- The Reading Room keeps its type settings.
- Line length and spacing follow Group G when it's locked.
*Required* (1.4.4). *Evidence* (Butterick 15 to 25 pixels, `13`).

**D11. Forms explain themselves.**
- Labels are visible.
- Errors appear in text next to the field and say how to fix it.
- Inputs carry autocomplete attributes where they apply.
- Nothing asks people to re-enter what they already gave.
- Sign-in stays on Google, with no puzzles or tests of memory.
*Required* (3.3.1 to 3.3.3, 3.3.7, 3.3.8, 1.3.5).

**D12. Easy to understand for every mind.**
- Plain language in all student-facing copy.
- The same navigation and the same help link in the same place on every page.
- One primary action per screen.
- Nothing depends on memorizing something from an earlier screen.
- No surprise changes of context.
*Required* (3.2.3, 3.2.6). *Evidence* (W3C's Making Content Usable, `08`).

**D13. Images and media carry text alternatives.**
- Informative images say what they show. Functional images say what they do. Decorative images are silent.
- A book cover's alternative gives its title and author.
- Video and audio made for students get captions and a transcript.
- Text is never set as an image.
*Required* (1.1.1, 1.2.2, 1.4.5).

**D14. Documents and PDFs are accessible too.**
- Prep Room documents and PDFs are tagged, with real headings, a reading order, real text, the document language set, and contrast that holds in print.
- The PDF pipeline already exports tagged PDFs (memory `pdf-design`).
*Required* (WCAG applies to documents. The ADA Title II rule covers public schools' documents, and it sets the standard families expect).

**D15. Light enough for old devices and managed Chromebooks.**
- Pages load and respond quickly on a slow home device:
  - Largest Contentful Paint within 2.5 seconds
  - response to input within 200 milliseconds
  - no layout shift
- Images load lazily and at the right size, and JavaScript stays small.
- Check on a throttled connection and processor.
*Convention* (Core Web Vitals, `19`). *House* (the brief: home devices can be old or slow).

**D16. Test the way students meet it.** Test with:
- ChromeVox and the keyboard on a Chromebook
- VoiceOver on an iPad and an iPhone
- TalkBack on Android
- browser zoom, forced colours and reduced motion
- automated checks (axe) as a first sweep

Automated checks find only a minority of issues, so every manual pass in A9 still runs. When a design needs evidence from students with disabilities, Adam arranges it (A10).
*Required* (A9). *Evidence* (`08`).

---

## E. Attention, ethics and privacy for minors

Exegetica's student logins are for grades 9 to 12 inside the school, so every student user is a minor and none is under 13. Teachers of grades 6 to 12 use it too. Every student's words go to an outside model provider. Opening student logins below grade 9 would bring in children under 13 and COPPA, and needs a decision first. Study notes: `docs/design-study/10-persuasion-ethics-privacy.md`, with the self-audit in `docs/qsf-scorecard-exegetica-2026-11-02.md` and the Quiet Standards statement.

**E1. Ask for the least attention the task needs.**
- A student comes to study a passage or practise a verse, and the app is done when that is done.
- No endless lists: more items load when the reader asks, as the Reading Room's "Show more" now does. The self-audit's ATT-09 is fixed.
- No autoplay.
- No "you might also like".
- No pull back into the app beyond the reader's own saved place.

*Required* (Quiet Standards, attention). *Evidence* (the attention economy, `10`).

**E2. No engagement machinery.**
- No notifications.
- No streaks, points, badges, levels, leaderboards or rewards.
- No unread counts.
- No emails that call students back.
- No celebration effects that turn study into a score.

Progress is shown as what a student can now do (B4). Research finds gamification gives small effects that fade, and leaderboards discourage the students at the bottom.
*Required* (Quiet Standards). *Evidence* (Deterding et al. and the gamification meta-analyses, `10`).

**E3. No dark patterns.** The interface never nags, obstructs, sneaks, interferes or forces (Gray et al.'s five strategies):
- Leaving is as easy as joining. Download, delete and clear are reachable from Settings in a few steps.
- Choices that cost the user something are shown with the same weight as the ones that don't.
- No pre-ticked boxes.
- No guilt-trip wording on a refusal button.
- Cancel is always visible.
- Nothing extra is added on the way through a task.

*Required* (Quiet Standards, departure and honesty, decision 0013). *Evidence* (Gray et al. 2018, Mathur et al. 2019, `10`).

**E4. Every sentence about the app is true today.**
- Copy about storage, privacy, sources, models, money and limits matches what the code does.
- When behaviour changes, the copy changes in the same piece of work. Decision 0025 changed the privacy page, the FAQ and Settings together.
- The self-audit's HON-03 ("in this browser only" said to signed-in users) shows what a stale line costs.

*Required* (0013, Quiet Standards honesty). *House* (memory `project-exegetica-identity`).

**E5. Collect only what a feature needs, and record why.**
- No analytics on students.
- Metrics are totals with no account in them (0012).
- Cap counters are keyed by a hashed account and deleted after two days (0011).
- No profile photo (0013).
- Anything new a feature would collect, store or send needs a decision record first, saying what is kept, for how long, and who can read it.

*Required* (0002, 0011, 0012, 0013). *Evidence* (data minimization, privacy by design, `10`).

**E6. Information goes only where a family would expect.**
- Every flow is named on `/privacy`: who receives what (the model providers, Google sign-in), and why.
- Typefaces and scripts are served from Exegetica's own server.
- Student pages load no third-party trackers, embeds or advertising code.
- A new flow is judged by whether a parent would expect it in a school setting.

*Required* (0013). *Evidence* (contextual integrity, Nissenbaum, `10`). *Required* (FERPA where it applies).

**E7. Say plainly who can read what, and for how long.**
- `/privacy` states, in plain words that work for a parent who has never used the app:
  - the maker can read saved studies, and he is a mandated reporter
  - the server keeps each chat until June 1 of its school year, whatever the student removes
  - what each outside service receives
- The chat page links to it from where students start.
- The app never implies more privacy than exists.

*Required* (0009, 0013, 0025).

**E8. High-privacy defaults for minors.**
- Nothing a student does is public or visible to other students.
- No profiles, sharing, comments or messaging between students.
- No location.
- No contact from outside the school.
- Any feature that lets students see each other's work, or lets teachers see more of students' work, needs a decision record first (Adam, 2026-11-08). The teacher project in the tracker is where that gets worked out.

*Evidence* (the UK Age Appropriate Design Code, which covers everyone under 18, `10`). *Required* (0002, 0009).

**E9. Encouragement serves the student's own goal, by honest means.**
- Encouraging copy (B5) supports a goal the student or teacher set, and the student would endorse it on reflection.
- Never encourage more use for its own sake.
- Never use scarcity, fear of missing out, or comparison between students.
- The test: never persuade a student of something you wouldn't consent to be persuaded of yourself.

*Evidence* (Berdichevsky and Neuenschwander 1999, manipulation per Susser et al., `10`). *House* (rule B5).

**E10. Safety comes before keeping anyone in the app.**
- Anything that suggests a student is in danger opens the help window (0018), and the bot hands the student to people (commitment 1, test 7).
- Nothing is designed to keep a distressed student talking to the bot.

*Required* (0018, position statement, "never a companion").

**E11. Design for the student who wants to break it.**
- Assume some students will push every boundary for an audience.
- Nothing a student types is shown to other students.
- Spoken input shown back is masked for profanity, as Scripture Memory already does.
- Limits are fixed text (C9).
- No feature hands a prober a way to embarrass a classmate, such as a name in a prompt reaching a public place.

*House* (memory `feedback-student-chat-context`). *Required* (0011).

**E12. Say how it is paid for, and keep it that way.** The privacy page states that the maker pays the running costs, and that there is no advertising, no payment and no data sale. A change to that is a decision, and the page changes with it.
*Required* (0013, Quiet Standards honesty).

**E13. Fail gracefully, and say what's missing.**
- When the database, the library or a model is down, the app keeps what still works.
- It says in one plain line what isn't available.
- It never loses the student's work.
- The internet requirement is stated.

*Required* (Quiet Standards durability, 0013). *House* (rule C6).

---

## F. Interface craft: states, feedback, forms, navigation

The everyday craft of every Exegetica screen. Study notes: `docs/design-study/03-interaction-design-principles.md`, `19-interface-and-web.md`, and `05-ui-software-and-interaction-techniques.md`. Rule A3 (start from the familiar pattern) and A5 (list every state) come first. These rules say what good looks like once you're there.

**What exists** (built 2026-11-08):
- **`Shell.ask(question)`** is the page's question dialog: a native `<dialog>` with a title, a body, verb buttons, an optional text field with validation, and a danger style.
- **`Shell.toast(text, {undo})`** is the one toast.
- **Undo** covers removing a study, deleting a verse or folder, and moving a verse back to Learning.
- **The test** `test_pages_ask_and_confirm_through_the_shell` in `tests/test_rail.py` keeps the browser's built-in boxes and page-made toasts out.

**F1. Every state has a designed screen, and each one says what to do next.**
- **Empty states** name the one useful first action, for example "Add a verse" or "Pick a book".
- **Loading** uses the shared status line or a placeholder shaped like the content. No bare spinner.
- **Errors** say what happened in plain words and offer the next step (try again, go back).
- **"Didn't load" notices** keep the student's work and say what won't be saved.
- **Closed or capped states** use fixed text (C9).

*Evidence* (visibility of status and error recovery, `03`). *House* (A5).

**F2. Feedback arrives on time.**
- A press or tap shows a pressed state at once (within about 0.1 second).
- Work that takes longer than about a second shows progress in words through the status line.
- Work longer than about 10 seconds says what is happening and lets the person leave and come back, as the Studio does for video.
- Interface responses that don't need the network should land within about 400 milliseconds.

*Evidence* (response-time limits and the Doherty threshold, `03`).

**F3. Undo beats confirm.**
- An action that can be reversed happens at once, followed by a toast with **Undo**. This applies to removing a study, deleting a verse or folder, and moving or renaming something.
- A confirmation dialog is only for what can't be reversed or is large: deleting the account (typed confirmation, decision 0013), or applying a batch of covers.
- Confirm buttons name the action ("Delete verse"), never "OK".
- Focus starts on the safe choice.
- Never use the browser's built-in `confirm()`, `alert()` or `prompt()`. Use the in-app dialog, `Shell.ask`. Built-in dialogs can't be styled or themed, they are hard to read on phones, and they train people to click through.

*Evidence* (Cooper and Raskin on confirmation and habituation, `03`). *House* (memory `feedback-ux-craft`: toasts with Undo, in-app dialogs, safe default focus).

**F4. Toasts confirm and never block.**
- One line that says what happened, plus Undo where it applies.
- Announced politely to screen readers.
- Long enough to read and act on: about 5 seconds when it carries Undo.
- One at a time.
- A problem that needs the person to act stays on screen until it's handled. That kind of message isn't a toast.
- One shared toast lives in the shell (`Shell.toast`), so every page behaves the same way.
- **Its look (Adam, 2026-11-08):**
  - a paper card like the site's notices: the surface colour, a thin rule, a soft shadow, ink text, and Undo in the rose accent
  - never a reversed dark or light slab
  - it sits just above whatever the page marks with `data-toast-above` (chat's composer), and never covers the place a student types
  - on phones it runs nearly full width above the bottom bar, with Undo on the right

*Convention.* *Required* (4.1.3, D5). *House* (A7).

**F5. Navigation always shows where you are and how to get back.**
- The rail lists each role's places, marks the current one, and becomes a bottom bar on phones.
- The wordmark returns to chat.
- Prose pages offer "Back to chat".
- Deeper places show the path: shelf to book to chapter, course to unit to day.
- Anything worth returning to has its own address, such as a book and chapter, or a course day, so the browser's back button and links work.

*Evidence* (information scent and wayfinding, `03` and `18`). *House* (the shared shell).

**F6. Each job uses the pattern people already know.**
- **Chat:**
  - the composer sits at the bottom
  - Enter sends and Shift+Enter starts a new line
  - the send button becomes Stop while a reply streams
  - the list of studies sits to the side
- **Collections** (Scripture Memory, the Living Library, the Studio), modelled on Google Photos and Finder:
  - folders as cards
  - a path header
  - selection with check circles
  - a contextual action bar
  - a menu for moving things
  - drag and drop with a non-drag alternative (D8)
- **The reader:** the position is kept, "Aa" holds the type settings, and contents are one step away.
- **Settings:** grouped, labelled, with each change explained where it's made.

*House* (A3, memory `feedback-ux-craft`). *Convention.*

**F7. One primary action per screen.**
- The primary action is a filled accent button.
- Secondary actions are quieter (outlined or text).
- Destructive actions use the danger style and sit apart from the primary.
- Two filled accent buttons on one screen means the hierarchy has gone wrong (Quiet Standards ATT-20).

*Evidence* (hierarchy, Fitts's law for the main target, `03` and `05`). *Required* (D12).

**F8. Forms ask little and explain themselves.**
- One column, labels above fields, sensible defaults.
- Only the fields the task needs.
- Check each field after the person leaves it, with the error beside the field and a fix.
- Enter submits.
- Autocomplete attributes where they apply.
- Long builders (the Prep Room, the Studio) reveal steps in order and keep a short summary of each finished step visible.

*Evidence* (Wroblewski, progressive disclosure, `03`). *Required* (D11).

**F9. Menus and dialogs behave like the platform's.**
- **Per-item menus** (the kebab) carry an accessible name, open with click, Enter or Space, move with the arrow keys, and close with Escape or a click outside.
- **Dialogs** have a title, take focus and return it (D3), close with Escape, and name their actions with verbs.
- On touch screens, menu rows are comfortably tappable.

*Convention* (the ARIA Authoring Practices patterns, `08`). *Required* (D3, D4).

**F10. The same thing looks and is named the same everywhere.**
- Shared components (the status line, tool chips, toasts, dialogs, buttons, menus) come from the shell and the tokens.
- One word for one thing across pages: study, verse, folder, shelf, book, resource.
- One icon for one action.

*Evidence* (Nielsen's consistency and standards, `02`). *House* (A7).

**F11. Words on controls are verbs, and words in the interface are plain.**
- Buttons say what they do ("Add verse", "Start practice", "Draft resource").
- Sentence case.
- No machinery words on student surfaces: no "model", "token", "API" or "prompt".
- Copy follows the voice rules, and error copy follows C6.

*House* (voice rules, `docs/voice-and-copy.md`). *Evidence* (match between system and the real world, `02`).

**F12. Motion shows where things went, briefly.**
- Use motion for continuity: a verse moving into a folder, a panel opening, a reply arriving.
- Entering motion eases out. Most transitions finish within about 200 to 300 milliseconds.
- Nothing moves for decoration.
- Reduced-motion settings are honoured (D9).

*Evidence* (motion principles, `20`). *Required* (D9).

**F13. The page keeps up with the person.**
- Saves feel immediate: show the result, then reconcile with the server.
- Typing is never blocked by work in the background.
- Lists load in pieces the person asks for (E1).
- Nothing jumps as content arrives: reserve space for images and replies.

*Evidence* (perceived performance, `05`). *Convention* (Core Web Vitals, D15).

**F14. House layout rules from 2026-11-08.**
- Every page sits on the garden.
- The wordmark sits at the top of each page's own column, never in a banner.
- Bars that stay put while the page scrolls are clear at rest and frosted only while content passes under them.

*House* (Adam, 2026-11-08).

**F15. Keyboard shortcuts help, and never surprise.**
- Frequent actions in the teacher tools and the Studio get shortcuts, shown beside the action in menus and tooltips.
- No single-key shortcut fires while the person is typing.
- Single-key shortcuts can be turned off.

*Required* (WCAG 2.1.4, character key shortcuts). *Convention.*

---

## G. Reading and screen typography

How text reads on Exegetica's screens: chat replies, Scripture, the Reading Room, and long pages. Study notes: `docs/design-study/13-typography.md`, `14-type-design-and-lettering.md`, `06` (reading and perception). Printed documents and books are Group H.

**State on 2026-11-08** (measured, then fixed at Adam's request):

1. **One type system.**
   - The built pages now draw their faces from the tokens (`prose.css`, `ops.css`, `formats.css`, `standards.css`).
   - `--display` and `--caps` moved into `tokens.css`.
   - Spectral's regular weight is self-hosted for long reading.
   - Font choices themselves stay open for a later design pass. Adam: consistency now.
2. **Line length.** Chat replies are at about 69 characters per line (`max-width: 54ch`) and the corpus page at about 71.
3. **Greek and Hebrew.**
   - **Fonts.** `webapp/static/fonts/orig.css` self-hosts EB Garamond's Greek as "Exegetica Greek" and Noto Serif Hebrew as "Exegetica Hebrew" (SIL OFL), through `scripts/fetch_fonts.py --orig`. Every page loads it, and their unicode ranges mean the files download only when a Greek or Hebrew character appears.
   - **Fallback.** Both faces sit in `--sans` and `--serif`, so untagged text still finds them.
   - **Tagging.** `Shell.tagLanguages` tags Greek (`lang="grc"`) and Hebrew (`lang="he"`, right to left, isolated) on load and as content arrives: streaming replies, Prep Room documents and their PDFs, and the reader, which tags each chapter before it measures the pages.
   - **Size.** Greek is set 1.1 times larger beside the interface faces, and Hebrew 1.15 times.
   - **Checked.** `tests/test_typography.py` guards all of this. A browser check confirmed tagging, direction, fonts loading from Exegetica's server, no double tagging on repaint, and the line lengths.
   - **Not yet covered.** The offline PDF builders (`scripts/course_pdf.py` and `scripts/book_pdf.py`) embed their own Latin fonts and don't tag Greek or Hebrew.

**G1. One face per role, drawn from the tokens.**
- Interface and chat answers: Public Sans (`--sans`).
- Scripture and quoted sources on screen: Spectral (`--serif`).
- Headings and display: Fraunces (`--display`).
- Tracked capitals on books and covers: Libre Baskerville (`--caps`).
- Labels, eyebrows and code: IBM Plex Mono (`--mono`).
- Book text: EB Garamond, with Literata as the reader's choice (`--book`).
- The course pages keep the school's own Inter and Fraunces. That's the Yorkville palette, a deliberate exception.
- Greek and Hebrew get faces that hold their scripts (G6).
- No other page stylesheet names a face directly.

*House* (the brief, A7). *Evidence* (limit families and give each a role, `13`). *Convention* (fewer font files, D15).

**G2. Reading text is sized, spaced and measured for long reading.**
- Body text is at least 16px. Text meant for long reading is 17 to 19px.
- Leading is 1.5 to 1.7.
- Lines run 45 to 75 characters, aiming near 66 on a laptop and at least about 35 on a phone. Set the measure on the text column in `ch` or `em`.
- Sizes stay in rem, so the device's text size setting works.

*Evidence* (Bringhurst and Butterick, `13`). *Required* (1.4.4, 1.4.12, D10).

**G3. One paragraph method per surface.**
- Books: first-line indents, no space between paragraphs, the first paragraph after a heading flush, justified only with hyphenation. The reader already does this.
- Screens and chat: space between paragraphs, flush left and ragged right, no justification.

*Evidence* (`13`). *House* (the book interior, memory `project-exegetica-interior`).

**G4. Hierarchy stays shallow.**
- Chat replies use at most two heading levels, styled modestly, and often none.
- Lists only for real sequences or sets.
- No bold run-in labels in long-form text.
- On long pages, each heading says what follows.
- A step between levels changes one or two things (size, weight, face), never everything.

*Evidence* (`13`). *House* (memory `feedback-book-formatting-tells`, rule B10).

**G5. Scripture is set as Scripture.**
- Quotations are set in the serif.
- The reference follows the text and opens the passage (B1). The translation is named where more than one could be meant.
- Verse numbers are small superscripts.
- Poetry keeps its lines.
- A long quotation is a block quotation.
- References stay together on one line, with non-breaking spaces in "1 John" and "John 3:16".
- Ranges take an en dash ("John 3:16–18").

*Evidence* (`13`). *House* (rule B1, decision 0016).

**G6. Greek and Hebrew are set properly.**
- Self-hosted faces cover polytonic Greek and pointed Hebrew, including the vowel points.
- Every Greek or Hebrew word or passage is tagged with its language (`lang="grc"`, `lang="he"`).
- Hebrew runs right to left. Inside an English line it is isolated, so punctuation lands correctly.
- Hebrew is set a little larger than the surrounding text (about 1.15 to 1.25 times), so the points stay legible.
- Transliterations are in italics.
- Strong's numbers are small and quiet.

*Required* (3.1.2, language of parts). *Evidence* (`13`, `14`). **A gap today.**

**G7. The characters are right.**
- Curly quotes and apostrophes, en dashes for ranges, the ellipsis character, and real multiplication and minus signs.
- Oldstyle figures in running book text. Tabular figures in tables and counts that line up.
- Copy written for Exegetica uses no em dashes (the voice rules). Public-domain books keep their authors' punctuation.

*Evidence* (Butterick's key rules, `13`). *House* (voice rules).

**G8. The reader controls the page.**
- The Reading Room keeps its size steps, its face choice and the theme.
- The reading position is kept.
- Settings belong to the reader's device.
- Nothing overrides the browser's own zoom or text size.

*Required* (1.4.4, D10). *House* (memory `project-exegetica-interior`).

**G9. Dark reading is gentle.**
- Off-white text on a near-black page, never pure white on pure black. The tokens already do this.
- No thin weights in dark mode.
- Book pages use the reader's own page colour.

*Evidence* (halation and dark-mode practice, `16`). *Required* (D2).

**G10. Long pages can be scanned and navigated.**
- A page with more than about five sections opens with a short contents list linked to the sections.
- Sections have their own addresses.
- Headings say what follows.

*Evidence* (information scent, `03`). *Required* (2.4.6).

**G11. Fonts load without shifting the text.**
- Self-hosted subsets with `font-display: swap`.
- The body face is preloaded on pages where reading starts at once.
- Fallback fonts are sized to match, so the text doesn't jump when the real font arrives.

*Convention* (Core Web Vitals, D15). *Required* (0013, fonts served from Exegetica's own server).

**G12. A streaming reply never pulls the page away from the reader.**
- While a reply streams, the page follows it only while the reader is at the bottom.
- A reader who scrolls up to read stays where they are.
- A "jump to the latest" control appears instead.

*Convention* (chat practice). *Evidence* (reader control, `03`).

---

## H. Documents, PDFs and books

Everything Exegetica produces to be printed, downloaded or read as a book:
- Prep Room documents and their PDFs
- the John course PDFs (`scripts/course_pdf.py`)
- house books (`scripts/book_pdf.py`)
- the Reading Room's book interiors (`webapp/typeset.py`)

Study notes: `docs/design-study/13-typography.md`, `15-grids-layout-editorial.md`, `20-print-motion-history-critique.md`. Locked rules already in memory: `pdf-design`, `project-exegetica-interior`, `feedback-book-formatting-tells`, `feedback-page-length-loose`, `john-chapter-quizzes`.

**State on 2026-11-08** (fixed at Adam's request):

1. **The Prep Room PDF.** It now prints by H2:
   - EB Garamond text at 12pt (13.5pt for grades 6 to 8), Fraunces headings, Public Sans tables with hairline rules
   - 2-inch side margins, so lines run 69 to 73 characters
   - the title and "Teacher copy" or "Student copy" at the head of every page after the first, and a page number at the foot
   - headings kept with their text, and nothing tinted

   The faces load as soon as a document shows, and the PDF button waits for them before opening the print dialog. A browser check printed a sample to PDF and confirmed the line length, running heads, page numbers and fonts (no fallback font). The on-screen preview is still set in the sans.
2. **The course and book PDFs.** `scripts/print_fonts.py` gives both builders Exegetica's own fonts as embedded data, plus "Exegetica Greek" and "Exegetica Hebrew", and tags Greek and Hebrew as the pages do. `book_pdf.py` no longer fetches Google Fonts. `course_pdf.py` already embedded its faces and now adds Greek and Hebrew. A course PDF rendered with no network requests. None of the 350 course documents contains Greek or Hebrew characters yet.
3. **The credit line.** It's an option at download, a "Credit line" checkbox beside Copy:
   - it ends the PDF and the `.md` file with "Drafted with Exegetica from its library's sources and reviewed by the teacher."
   - it shows at the foot of the document while it's on
   - it's on by default, and the teacher's choice is remembered in their browser
   - Copy stays the document alone

Tests: `tests/test_documents.py`.

**H1. Content and design stay apart.** A generated document is structured content: headings, paragraphs, lists, tables, quotations. One fixed print stylesheet per kind of document carries all the design, and the model never writes styling. This keeps every document consistent, and it guards against output that looks machine-made.
*House* (memory `pdf-design`).

**H2. Print typography follows the locked PDF rules.**
- The page margins hold the measure to 45 to 75 characters, aiming near 66. On Letter paper the side margins are about 1.5 to 1.75 inches, and the bottom margin is a little deeper than the top.
- Body text is a serif at about 10.5 to 11pt with 130 to 140 percent leading. EB Garamond runs small for its size, so it takes 12pt (13.5pt for grades 6 to 8) to read like an 11pt text face. With 2-inch side margins that lands near 70 characters a line.
- Headings use the display face. Tables and labels use a functional sans.
- One paragraph method per document: indents or space, never both.
- Tables use hairline horizontal rules only: no vertical lines, no zebra stripes, no fills. Numerals are right-aligned in tabular figures.
- No tinted call-out boxes. A rule and white space do the job.
- Orphans and widows are at least two lines. Headings never sit alone at the foot of a page.
- Every page carries a running head (the document's title) and a page number.

*House* (memory `pdf-design`). *Evidence* (`13`, `15`, `20`).

**H3. Long documents read like books, not chat.**
- No bold labels opening paragraphs.
- Few subheadings, and never one template repeated in every chapter.
- No parts that hold only one chapter.
- No announcing a count before the content ("three reasons").
- No summary tables or listicles inside narrative.
- No bold key terms in running text, and no question headings.
- A requested page count guides the first draft only. Content is never cut later just to hold it.

*House* (memories `feedback-book-formatting-tells`, `feedback-page-length-loose`).

**H4. Teacher and student versions never mix.**
- Answer keys, teacher notes and rubrics live only in the teacher version.
- The student file is generated without them, so it can't leak them.
- File names and the running head say which version it is.

*Required* (0007). *House* (`course_pdf.py`'s separate folders).

**H5. Assessments follow rules B6 and B7.** Items map to taught objectives. Distractors come from the misreadings the lesson guards against. No wrong answer is a defensible reading. Views students sincerely hold, which the lesson doesn't take up, stay out.
*House* (memory `john-chapter-quizzes`).

**H6. Scripture in documents is exact and credited.**
- References are checked against the bundled Bible by the source check (0016).
- The translation is named.
- ESV quotations follow Crossway's terms: in classroom handouts and other materials that aren't sold, the initials "(ESV)" follow each quotation. A published book carries Crossway's full copyright notice. These terms are from training knowledge and should be checked on Crossway's permissions page before relying on them.
- Greek and Hebrew are set and tagged per G6.

*Required* (0016, the translation's licence). *House* (G5, G6).

**H7. No AI-written worship in any document.** Where a format calls for a prayer or devotion, the document shows a plain placeholder, "[Prayer: led by the teacher]", set so it reads as a gap for a person to fill.
*Required* (0010).

**H8. Documents fit their readers and the school's printers.**
- The grade band sets size and density: larger type for grades 6 to 8 than for high school (13.5pt and 12pt in EB Garamond).
- Documents print well in black and white on Letter paper. Meaning never rides on colour alone, and tints that turn to grey mud are avoided.
- Margins leave room for hole punching.

*Evidence* (`07`, `13`). *Required* (D2's rule on colour alone, carried to print). *House* (teachers of grades 6 to 12, from the brief).

**H9. PDFs are accessible documents.**
- Tagged PDF, with real headings, a sensible reading order and the document language set.
- Real text, never text as pictures.
- Alt text for images.
- Links whose words say where they go.
- Embedded fonts, including Greek and Hebrew.

*Required* (D14, WCAG for documents). *House* (memory `pdf-design`: the pipeline exports tagged PDFs).

**H10. Books keep the house interior.**
- No provenance and no translator or editor credit inside a book. The colophon claims only "set, corrected and designed".
- EB Garamond for the text, with Literata as the reader's choice. Fraunces for headings, Libre Baskerville for tracked capitals.
- The interior follows the book's cover theme and motif.
- Each Part gets its own title page, with no running head or page number. Every chapter, front and back matter included, starts on a new page.
- Never turn on markdown's "replacements" option, which turns "(C)" into ©.

*House* (memories `project-exegetica-interior`, `pdf-design`, `project-house-covers`).

**H11. One pipeline, self-hosted fonts.**
- Documents render through Chromium with a dedicated print stylesheet and native page margin boxes. Add Paged.js only when cross-references or footnotes need it.
- Fonts come from Exegetica's own copies and are embedded, never fetched from Google at render time.
- Wait for the fonts to load before exporting.

*House* (memory `pdf-design`, decision 0013 for self-hosted fonts).

---

## I. Marks, covers, imagery and colour

How Exegetica looks as a whole: its marks, its colour, the garden, its icons, the house covers, and any image it makes. Study notes: `docs/design-study/16-color.md`, `17-identity-branding-systems.md`, `18` (icons and pictograms), `20` (photography and history). Locked rules already in memory and the skill: `project-house-covers`, the colour tokens and the garden (the brief, Group D).

**What exists** (2026-11-08):

- **The marks:**
  - the wordmark: "Exegetica" in a serif over a rose brushstroke, black for light pages (`wordmark-black.png`) and white for dark (`wordmark.png`)
  - the E icon: a serif E on the same brushstroke over near-black, in every favicon size, the touch icon, and the 192 and 512 app icons
- **The wordmark's placement:** once per page, at the top of the page's own column, linking to chat, and never in a banner (`partials/masthead.html`, decided 2026-11-08).
- **Colour:** the tokens in `tokens.css`, tested pair by pair (`tests/test_contrast.py`). The course pages keep the school's navy and gold.
- **The garden:** behind every page. Light mode uses the more colourful copy, dark mode the original, both under the paper colour at 86 percent.
- **Icons:** one stroke family on a 24-unit grid, 1.7 stroke, round ends, no fill, drawn in the current text colour (`shell.py`, `shell.css`).
- **Covers:** the locked house cloth design, plus the per-reader cover picker.
- **Images Exegetica makes:** only in the Media Studio, which is the maker's alone and keeps its images private (0017).
- **The home-screen manifest** uses the dark paper colour (`#14151a`) for its background and theme colour (fixed 2026-11-08).

**I1. One mark, used as drawn.**
- The wordmark and the E icon are images. They're never re-set in live type, stretched, recoloured, outlined or given effects.
- The black wordmark goes on light grounds and the white one on dark.
- The wordmark appears once per page, at the top of the page's column, links to chat (except on chat itself), and is never in a banner. It's left off print.
- It keeps clear space of at least the height of its capital E on every side, and is never placed on busy imagery.
- The E icon stands for Exegetica wherever a small square mark is needed: the browser tab, the home screen, and app icons.

*House* (Adam, 2026-11-08, and the E icon). *Evidence* (identity systems keep their marks exact, `17`).

**I2. Colour comes from the tokens, each in its role.**
- Paper and surfaces are the ground. The three ink levels set the text hierarchy.
- The rose accent marks the brand and the one primary action on a screen (F7).
- Iron marks links and information. Brass is decoration only: icons, rings, borders, never small text.
- Success, warning and error colours mean only that, and never stand in for the brand.
- Dark mode is its own palette, not an inversion.
- No page invents a colour. A new colour is a new token, tested against every ground.
- Colour never carries meaning alone (D2).

*House* (the tokens, `tests/test_contrast.py`). *Evidence* (Itten's contrast of extension: the accent stays small to keep its strength, `16`). *Required* (1.4.1, 1.4.3, 1.4.11).

**I3. The garden is the ground, and nothing else is.**
- Every page sits on the garden: the colourful copy in light mode, the original in dark, under the paper colour at 86 percent, with paper beneath as the fallback.
- No page adds another background image, texture or pattern.
- The garden stays off documents and print.
- Text sits on it only in colours tested against its worst point.

*House* (Adam, 2026-11-08). *Required* (D2).

**I4. Icons are one family.**
- Drawn on the 24-unit grid with the same stroke weight, round ends, no fill, and the current text colour.
- One icon for one meaning across the site (F10).
- On student surfaces an icon carries a visible label, except the few nobody misreads (close, theme, menu).
- The drawing is hidden from screen readers, and the button carries the name.
- A new icon is drawn to the family, never borrowed from another set.

*Evidence* (icons alone are ambiguous, pictogram systems hold one grammar, `18`). *Required* (D4).

**I5. House covers keep the locked design.**
- The board is always the house cloth: parchment `#f0e8dc` or ink `#1e2026`.
- A theme colours only the pattern and the thick recessed outer border.
- Titles are engraved in the theme's lettering colour, never in gold.
- No inner frame, title box or band rules. The title sits in a flat gap in the pattern.
- Fraunces titles and Libre Baskerville capitals.
- Motifs are ornamental and characterful (a fleuron, a winged key, a sea serpent), never everyday objects drawn as clip art.
- Cover text follows the `cover_text` rules and the hand-written short titles.

*House* (memory `project-house-covers`, "That is our design").

**I6. Images Exegetica makes are honest about what they are.**
- Images from the Media Studio stay private to the maker until a decision says otherwise (0017).
- When an AI-made image is ever shown to students, it is labelled as made with AI.
- It is never presented as a photograph, a historical record, or evidence of how a place, object or person looked.
- No image of a real student or staff member is ever generated.
- Every image used in a page or document carries alt text (D13).

*Required* (0017, D13, and the school handbook, which forbids pictures of students or staff without their consent). *House* (the Quiet Standards on honesty). *Evidence* (critical approaches to images as arguments, `18`, `20`).

**I7. Illustration and photography share one register.**
- Where Exegetica uses illustration, it speaks the covers' language: ornamental, engraved or woodcut in feel, a limited palette from the tokens.
- No glossy 3D, stock-photo clichés or clip art.
- Photographs are real, credited and licensed.
- A set of images (a unit, a series of documents) holds one style throughout.

*House* (the covers' motif rule). *Evidence* (identity coherence, art direction, `17`).

**I8. The school's marks stay the school's.**
- Course pages and course PDFs wear Yorkville's navy and gold and the course's own marks.
- Exegetica's wordmark appears on course pages as on every page. Exegetica's colours aren't mixed into the school's palette.

*House* (the course palette, `course.css`).

**I9. Exegetica makes no image of Christ.**
- Exegetica never makes or depicts an image of Christ, in any surface, document or generated image.
- It may display existing images of Christ that come with the sources in its library, such as a public-domain book's own cover art or illustrations. Those belong to the source, not to Exegetica.
- Nothing is searched for or removed because of this rule.
- House covers use ornament, not figures.
*House* (Adam, 2026-11-08). In line with the Reformed confessions on images (Westminster Larger Catechism 109, Heidelberg Catechism 96 to 98).

---

## J. Information design: tables, maps, timelines, charts

How Exegetica shows information that has structure: tables, the course calendar, and any map, timeline, family tree, diagram or chart it draws later. Study notes: `docs/design-study/12-data-visualization.md`, `18-information-and-exhibit-design.md`, `15` (grids). Printed tables follow H2.

**What exists** (2026-11-09):

- **Tables** appear in chat replies, Prep Room documents, `/ops` and the corpus page. Chat and the Prep Room build theirs with one shared function (`Shell.table` in `shell.js`, styled in `shell.css`), guarded by `tests/test_documents.py`:
  - header cells tied to their columns, and numbers and references right-aligned in tabular figures
  - references and ranges kept whole on one line
  - on phones (560px and under, screen only), tables of five columns or more become a card per row
  - a narrower table wider than the screen scrolls in its own labelled region, with a soft shade at the edge where columns are hidden
  - cells open to the garden, with no solid background
- **No maps, timelines, family trees or charts are drawn anywhere yet.** The library holds what they would need: place coordinates, event and birth years, genealogies, and the people and places graph. The tools return all of it to the model as text. Maps and timelines are on the list of approved work to design with Adam.
- **The course calendar** (`/calendar`, `/course`) shows the school year by month, week and day.
- **Years in the library's output** read "c. 30 AD" and "c. 1000 BC".

**J1. Start from the reader's question.** Before drawing anything, name three things:
- the data
- the task: look something up, compare, follow a change over time, find a place, trace a relationship
- who reads it: a student or a teacher, on which screen

Then choose the plainest form that answers. Often that's a sentence or a short table. A graphic earns its place only when it answers faster or more truly than words.
*Evidence* (Munzner's what, why and how, `12`, Wurman's five ways to organize, `18`).

**J2. Tables are built for lookup.**
- Header cells name each column.
- Text is left-aligned. Numbers and references are right-aligned in tabular figures.
- Use as few columns as the question needs.
- Light rules. Print uses hairlines only (H2).
- References and ranges ("4:46-54") never break across lines. A list of them wraps between items.
- On phones, a table of five columns or more becomes a card per row: the row's name heads the card, and each line carries its column's label.
- A narrower table wider than the screen scrolls inside its own labelled region, which the keyboard can reach and scroll. A soft shade at an edge shows more columns are out of sight. The page itself never scrolls sideways.
- The cells stay open to the garden behind them.

*Required* (1.3.1, 1.4.10, 2.1.1). *Evidence* (`12`, `15`). *House* (Adam, 2026-11-09).

**J3. Maps show a period, honestly.** When Exegetica draws a map:
- It names its period, because borders, cities and roads changed across Scripture's centuries.
- It uses a quiet base, with modern borders absent or faint and the regions of that period labelled.
- It has a scale bar and north.
- A place whose identification is disputed is marked as uncertain, with its source named.
- Every map has a text alternative: the places and how they relate.
- Maps are drawn from Exegetica's own data and images. No third-party map tiles or embeds, which would send a student's activity elsewhere (E6).

*Evidence* (cartographic generalization and maps as arguments, Monmonier, `18`). *Required* (E6, D13).

**J4. Timelines show uncertainty and their chronology.**
- One scale per timeline. Any break in a long span is marked plainly.
- Approximate dates read as approximate ("c. 1000 BC") or as ranges. Nothing gets false precision.
- Where chronologies truly differ (an early or late date for the Exodus, for example), the timeline says which one it follows, in a brief attributed note.
- Dates use BC and AD, as the library already does.

*Evidence* (Priestley and the cartography of time, `18`). *House* (memory `feedback-answer-philosophy`: a brief attributed note where scholars truly divide, and the library's year format).

**J5. Family trees and relationships stay readable.**
- Descent is drawn as a tree. A network only for a small set.
- Relationship types are labelled (father, son, wife, brother), and disputed links are marked.
- A long genealogy is shown a few generations at a time, with the way forward and back always visible.
- Every tree is also readable as a nested list, for screen readers.

*Evidence* (`12`, `18`). *Required* (1.3.1).

**J6. Charts tell the truth at a glance.**
- The chart type follows the task:
  - bars on a zero baseline to compare
  - lines for change over time
  - position on a shared scale before area or angle
- Label the data directly, and the takeaway in the title.
- No 3D, dual axes or decoration.
- Colours by their roles (I2), each tested for contrast. Never colour alone.
- Every chart comes with a text alternative and its data as a table.
- No chart is ever made of a student's own behaviour, topics or moods (0002, E5). `/ops` shows totals only.

*Evidence* (Cleveland and McGill, Tufte's lie factor, Lundgard and Satyanarayan's levels of description, `12`). *Required* (0002, 0012, D13).

**J7. Calendars show the school's rhythm.**
- Today is marked.
- School days, breaks and assessment days are told apart by more than colour.
- Units and lessons are labelled.
- Each day links to its plan.
- Every view prints cleanly.

*Evidence* (`18`). *Required* (1.4.1).

**J8. Diagrams in documents are structure, not drawing.**
- When a Prep Room document needs an outline, a passage's structure (a chiasm, a sequence of signs), or a comparison, the model writes it as indented text, a list or a table.
- The document's stylesheet sets it. No ASCII art.
- A drawn diagram is the teacher's to make or approve.

*House* (H1, content and design kept apart).

**J9. Exploration stays simple, and never profiles students.**
- Any interactive map, timeline or tree starts from an overview. The reader zooms and filters, and details appear on demand.
- Every control works by keyboard and touch.
- Animated changes are brief and staged, and respect reduced motion.
- Teacher views show what a class worked on in totals and never build a profile of a student. Any teacher view needs the decision the teacher project will make (0009).

*Evidence* (Shneiderman's information-seeking mantra, `12`). *Required* (0002, D8, D9).

---

## K. Pre-ship checklist and the tests that enforce it

The last gate before Claude hands back any change to something Exegetica shows or prints. It gathers the checks from Groups A to J into one list, says how each one is checked, and says which checks a test or script keeps from slipping. Study notes: `docs/design-study/02` (evaluation methods), `08` (accessibility testing), `19` (performance).

**What exists** (2026-11-09):

- **The free checks** (`python -m pytest`: no network, no API spend, about 35 seconds). Among them:
  - colour: every token on every ground, the garden's worst point in both themes, the course palette (`test_contrast.py`)
  - type: no page names a typeface, the roles are tokens, Greek and Hebrew self-hosted and tagged, reading lines near 66 characters (`test_typography.py`)
  - the shell: one rail by role, teacher places turning others away with a page, every page on the base layout and the garden, the wordmark in its column, dialogs and toasts through the shell, the docked verse list (`test_rail.py`)
  - documents and tables (`test_documents.py`), icons and the manifest (`test_icons.py`), cache headers (`test_cache_headers.py`)
  - every word people see against the voice rules, and the approved crisis wording (`test_copy_voice.py`), the student prompts (`test_student_prompts.py`)
  - the browser check's own safety and page list (`test_design_check.py`)
- **The browser check** (`scripts/design_check.py`, run from PowerShell). Its own local server blanks production data and every model key, signs in as each role through a header only that server reads, and checks all 16 pages. It uses the vendored axe-core 4.11.1 in `scripts/vendor/axe-core/` (MPL-2.0). Its first full run, on 2026-11-09, found faults on the standards page, `/ops`, the covers review, the Prep Room and Scripture Memory, all fixed the same night.
- **The free checks run when Claude runs them,** before every hand-back. Adam chose to keep them manual for now (2026-11-09).

**K1. Every change to a surface ends with this checklist.** Before handing back a change to anything Exegetica shows or prints:
- Run the free checks, always.
- Run the browser check when a page, stylesheet or script changed.
- Work through the checklist items (K5) the change touches. A one-line copy fix touches few, and a new page touches all.
- Report what ran and what each found, what couldn't be checked, and what is left for Adam (A12).

*House* (CLAUDE.md, A8, A9, A12).

**K2. The free checks hold every rule a test can read.**
- A test reads the source or renders in-process: no network, no browser, no model, no production data. That keeps it free to run on every change.
- When a pass finds a mechanical fault, the fix ships with a test that would have caught it.
- Each test is named for what it keeps, in plain words, and its file names the rule group.
- A test is never loosened to let a change pass. When a rule changes, Adam locks the rule first, and the test follows it.

*House* (A9, CLAUDE.md). *Evidence* (regression tests keep fixed faults fixed, `02`).

**K3. The browser check lives in the repo and runs on demand.** `scripts/design_check.py`:
- It starts a local preview with the database, the file store and every model key blanked, so nothing reaches production and nothing costs money.
- It loads every page as a student, a teacher and the admin, in both themes, at phone, tablet and laptop sizes.
- It runs:
  - axe-core with the WCAG 2.2 A and AA rules
  - a Tab walk at laptop size: every stop visible, none hidden under a sticky bar, nothing clickable that the keyboard can't reach
  - target sizes at phone size: 24px at least, 44px on touch controls
  - reflow at 320px: the page never scrolls sideways
  - reduced motion: nothing animates
- It saves a screenshot of every page and state for the eye pass (A8), lists what failed, and exits non-zero on any failure.
- It stays out of `python -m pytest` because it needs Chromium and a running server. A free test keeps it safe and its page list complete.

*Required* (D1, D3, D6, D7, D9). *Evidence* (automated checks find a minority of accessibility faults, so they come first and never alone, `08`).

**K4. Some checks need eyes or people.** Claude does the first three, and hands the rest to Adam as a short list of what to try and what to listen or look for:
- reading every screenshot of every state (A5, A8)
- reading every printed page of a document as a PDF (H2, H9)
- the heuristic pass and reading the copy at a ninth-grade level (A9, B11)
- screen readers on the devices students use: ChromeVox, VoiceOver, TalkBack (D16)
- real students or teachers trying a task (A10)
- the bot's behaviour, which only Adam probes

*House* (memory `feedback-manual-probing`). *Required* (D16).

**K5. The checklist.** Each item names its rule and how it's checked: **test** (the free checks), **browser** (K3), **eye** (Claude reads it), **Adam** (K4).

The person and the job
- One line: who uses it, the job, what could go wrong, and how a student would misuse it (A1, E11). *eye*
- Every state designed and screenshotted: empty, loading, partial, error, offline, long content, each role, signed out (A5, F1). *browser, eye*

Learning and AI, on student surfaces
- It sends the student to the text, and the thinking stays theirs (B1, B2). *eye*
- It never presents a person, and limits are fixed text (C7, C9). *eye*
- Every claim leads to something checkable (C3). *eye*
- Failures say what happened and what to do, with no model names (C6). *test*
- Help is one tap away and never in the way (C10). *test, eye*

Accessibility
- axe finds nothing, in both themes at three sizes (D1). *browser*
- Every colour pair is a token, tested on every ground and on the garden's worst point (D2, I2). *test*
- Keyboard walk, visible focus, nothing hidden under a bar (D3). *browser*
- Targets, reflow at 320px, zoom to 200 percent, both orientations (D6, D7). *browser*
- Changes announced without moving focus (D5). *eye, Adam*
- Reduced motion respected (D9). *browser*
- Greek and Hebrew tagged and self-hosted (G6). *test*

Attention and privacy
- No engagement machinery and no dark patterns (E2, E3). *eye*
- Every sentence about the app is true today (E4). *eye, Adam*
- New data has a recorded reason, and no page requests anything from a third party (E5, E6). *test, to add*

Craft, type, documents, marks, information
- Built from the shell: rail, dialogs, toasts, chips, status line, tables (A7, F4, F9, J2). *test*
- One primary action per screen, and undo before confirm (F3, F7). *eye*
- Faces from the role tokens, reading lines near 66 characters (G1, G2). *test*
- No layout shift as fonts arrive (G11). *browser, to add*
- Print follows the locked rules, and the PDF is read page by page (H2). *test, eye*
- The wordmark once per page, the garden behind every page, icons from the family (I1, I3, I4). *test*

Voice
- Every word people see passes the voice rules, outside quotations (A9). *test*
- Crisis copy changes only with Adam's approval. *test, Adam*

*House* (Groups A to J).

**K6. A full audit runs at the turning points.**
- The whole browser check, every page and role, plus the eye pass, runs before Claude calls a change ready to deploy, and after any change to the shell, the tokens or the type.
- The brief's known gaps are rewritten from what the audit finds.
- A check that couldn't run is named in the report, never left out.

*House* (the 2026-11-08 audit that replaced the brief's known gaps, A12).
