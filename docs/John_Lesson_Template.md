# John — Daily Lesson Template
## The shape every lesson follows

This is the reusable form of a single lesson. It is built to do three things at once, on every ordinary day: reach the three-tier room, govern the teacher's voice, and treat the Word as living rather than as a textbook.

Under Approach B this template is also the data model. Each field below is a slot the generator fills for a specific lesson, drawn from the Scope & Sequence, the paired sermon in `john-sermons/`, and the [External Resource Map](John_External_Resource_Map.md). Short-day and insert-day differences are flags on the record.

---

## 1. Lesson header

| Field | What goes here |
|---|---|
| Unit / Lesson | Unit name; lesson n of 150 |
| Date / Day type | Regular (50 min) · Thursday (36) · Half-day (26) |
| Passage | The verses taught today |
| Big idea | One sentence. The spine of the lesson. |
| Christ connection | Where the passage lands on Christ (the christotelic point) |
| Memory verse | The verse planted or reviewed today, if any |
| Content objectives | 2 to 4 things every student must know by the bell. This is the floor, and it is what the quizzes and finals later assess. |
| Reach / Hold / Stretch | The zero-knowledge entry and honest on-ramp for the searching student (S); the background this lesson supplies (B); the high-ceiling thread for the disciple (D) |
| Resources to pull | Sermon number; resource-map entries |

**Talk budget (write it at the top and mean it):** your sustained voice stays under about 18 to 20 of the 43 working minutes, and no single stretch of teacher talk runs past 8 to 10 minutes. The time map below keeps you honest; when you look up, the plan has already told you to hand off.

---

## 2. The five moves (regular 50-minute day)

### Move 1 — Quiet time with the Lord · 7 min · ungraded (credit for doing it)
- **Host:** you, or a rotating student host once the room has learned the rhythm. Closing in prayer is opt-in, so a shy or not-yet-believing student can host by reading the verse and keeping time.
- **Shape:** one minute to settle and hear a short centering verse or prompt; five minutes to journal, pray, and sit; one minute to gather.
- **Students:** write in the **Quiet-Time Journal**. Personal. Not collected for content.
- **On-ramp:** phrase the prompt so a doubter can honestly write his questions to God. Phones away.
- **Tier note:** gentle for (S), who is asked nothing aloud; a lasting habit for all.

### Move 2 — Hear the Word · 3 to 5 min
- **Students** read the passage aloud, slowly. Rotate readers. Optional fast round: one line each on what stood out.
- **You** are nearly silent, and you give navigation help (where we are in the story, the page number) so the searching student is never lost or embarrassed.

### Move 3 — Work the text · about 25 min · the governed block, no lecture here
- Run a **prepared question sequence** written in advance. You ask; they discover.
  - **Entry question** any student can answer with no prior knowledge.
  - **Core question** on the passage's main point, worked first in **John groups** and think-pair-share, with observation written in the **Reading Journal**.
  - **Deeper question** with a high ceiling (an Old Testament echo, a cross-reference, a hard question, a Greek word) for the disciple, feeding journals and projects.
- **Cold-call comprehension checks**, named rather than volunteers, so participation is assigned and not optional.
- **You** circulate among the groups and probe in short turns. Governor cue: if you have been talking more than two or three minutes straight in this block, turn the next thing you were going to say into a question.
- **Tier note:** the Entry and Core serve (S) and (B); the Deeper serves (D); everyone speaks to a partner before the room.

### Move 4 — Land and minister · 5 to 7 min · your protected pulpit
- Bring the passage to Christ, and speak its truth over the class, plainly, instructing the believer and inviting the outsider.
- This is also where you gently **correct or deepen any theology** that surfaced today, including anything a student got wrong while leading. Grace on the grade, truth in the room.
- Time-boxed on purpose, so it lands with weight.

### Move 5 — Respond · 3 to 5 min · graded participation
- An in-room written response in the **Reading Journal** to an existential prompt, not an academic one: "John wrote this so that you may believe. What is this passage asking of you?"
- On short days this can be a spoken one-sentence round instead.
- Give the Word room to press; trust the Spirit for what only He does.

---

## 3. Short-day variants

| Day | Quiet time | Hear | Work | Land | Respond |
|---|---|---|---|---|---|
| **Thursday (36 min)** | 7 | 3 | ~17 (one question, not a full sequence) | 4 | 3-5 |
| **Half-day (26 min)** | 3-4 | 3 | ~12 (one focused question or a single verse) | 4 | 3 |

Thursdays are a good home for a memory-verse plant or a student devotional. On a half-day, the quiet time plus one verse can be the whole lesson.

---

## 4. Periodic inserts (scheduled in the Scope & Sequence, not every day)

- **Student-led devotional · 10 to 15 min · participation grade.** A John group leads the class in a miniature of this arc: read the passage, give the one big idea, show how it points to Christ, ask the class one good question and facilitate a short discussion, and close with one application or a truth spoken over the room. Graded for preparation, engagement, and serving the class, with tiered speaking roles inside the group. **Theology is coached live, not scored.** Listening groups owe one written affirmation and one honest question. (Full rubric comes with the assessment menu.)
- **Memory-verse work:** plant, or oral recitation to a partner who checks and initials.
- **Checkpoint quiz, seminar, or project milestone** on its scheduled day.

---

## 5. What each lesson feeds the gradebook

- **Participation** draws from the Work-block engagement, the cold-call and think-pair-share, the Respond entry, quiet-time hosting, and devotional leads.
- **Content mastery**, the "ensure they know it" floor, is carried by the **memory verses, checkpoint quizzes, and semester finals**, so the devotionals and the quiet time stay about formation.
- **Homework** stays near zero, only the reading itself, which keeps homework-alone under the 20 percent cap while participation may run higher.

## 6. The two journals

- **Quiet-Time Journal:** personal and devotional, ungraded or credit-for-doing, used in Move 1.
- **Reading Journal:** observation and response, used in Moves 3 and 5, graded inside Participation.

---

## 7. Data-model note (Approach B)

The header fields and the contents of the five moves are the per-lesson record. The generator produces each record from the Scope & Sequence (passage, big idea, memory verse, objectives), the paired sermon (framing, illustrations, the emphasis worth borrowing), and the resource map (which outside piece serves this passage and which tier it helps). Day type and any insert are flags that reshape the time map. Nothing in a generated lesson is invented against the text; the exegetical spine comes from the Study Bible tools.
