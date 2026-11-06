# 0018: Three checks can open the help window, and /ops counts how often it opens

Decided by A. James Vega, 2026-11-04. It closes the crisis gap the 2026-10-31 safety review ranked first: the old word check caught 3 of 25 crisis messages in its probe.

**Decision.** Any of three checks opens the "Need help now?" window, which lists verified crisis resources. It opens at most once per reply. A flag does only that: the reply is unchanged, no one is notified, and nothing about the person or the message is kept.

1. **The local check** (`precheck`) reads the person's latest message before anything else, on the server with no network, so its window opens before the reply starts. It has two parts, and either opens the window.
   - A word list. It reads teenagers' spelling ("im", "w/o", "gonna") as the full words and covers kinds of phrasing rather than single phrases: self-harm in any tense, warning signs such as goodbye letters, a topic made personal ("for my essay on suicide... i think about it"), someone else about to hurt themselves, emotional abuse, silence an adult demands, grooming, weapons brought to school, and a body in danger. A negation clears only the phrase it belongs to, so "I'd never hurt anyone, I just want to die" fires. School words such as "class" or "project" no longer clear a first-person statement. Its match also picks which resources the window lists first.
   - A classifier that reads the gist of a message: a logistic regression over the message's embedding (the model2vec model the libraries already load, baked into the image) and its words and word pairs. It takes under a millisecond. `scripts/train_crisis_check.py` trains it on 600 messages an agent wrote for training, the first evaluation set, and Bible verses, including the 2,000 a first model scored most like a crisis, so that the lament psalms and Job, which sound like first-person distress, stay quiet. It ignores negation, so "I don't want to kill myself" opens the window.
2. **The reply.** The model is told to send a person in trouble to the window (`safeguarding_note`). When its reply does, the window opens.
3. **The model check** (`check`). Claude Haiku 5.5 reads the person's last three messages for meaning and answers yes or no with a category. It runs alongside the reply, so the window opens a second or two in. A finished reply waits up to five seconds for it. It runs on every student chat, whichever model writes the reply (0024), on a teacher's chat that goes to Anthropic, and on fixed replies other than a bare greeting, so a capped or drifted student in crisis is still checked. If it fails or gives no answer, the local check's answer stands. It costs about a hundredth of a cent a message, counted in the chat's metrics row when it answers before the run ends.

`/ops` shows, for each UTC day, how many times the window opened and which check opened it, and how many times the model check gave no answer. These are totals in `ops_daily`: no account, message, category, or time of day. This settles open decision H in the harness proposal.

**Why.** The word list missed slang, abuse words, and any message with a negation or a school word in it. A missed message got a reply that pointed to a window that never opened. A list cannot keep up with how teenagers write, and the maker judged 20 of 50 not good enough for the check that answers before the reply, so the classifier joined it on 2026-11-05. The model check sends a student's last three messages to Anthropic. Until 2026-11-06 Anthropic already received them for the reply, and since then DeepInfra writes the reply (0024). The classifier sends nothing anywhere.

Measured on two sets written by agents that never saw the checks (`evals/crisis/`). The first set's misses were studied to widen the word list and then trained the classifier, so only the second scores them fairly. It was scored with the word list frozen, and with two versions of the classifier; the second version changed for Bible verses, not for anything in the set.

| Set 2 | Crisis messages caught | Quiet messages opened wrongly |
|---|---|---|
| Word list before this decision | 5 of 50 | 6 of 50 |
| Word list now | 20 of 50 | 7 of 50 |
| Classifier | 48 of 50 | 3 of 50 |
| Local check (either) | 49 of 50 | 10 of 50 |
| Model check (sets 1 and 2) | 100 of 100 | 0 of 95 |

Set 2 showed the word list adding one catch and seven wrong opens, most from two broad patterns (a bare mention of suicide, and killing said in the same breath as the school). Those two now name the category only and never open the window themselves. The rest of the list stays because it catches plain statements the classifier can miss ("i was sexually abused", "I'm going to kill him after class"). A third blind set, written after that change and scored once with everything frozen (2026-11-05):

| Set 3 | Crisis messages caught | Quiet messages opened wrongly |
|---|---|---|
| Word list alone | 29 of 60 | 1 of 60 |
| Classifier alone | 56 of 60 | 4 of 60 |
| Local check (either) | 56 of 60 | 5 of 60 |
| Model check | 60 of 60 | 1 of 60 |
| All layers | 60 of 60 | 6 of 60 |

No layer opened on any of the 30 study questions. The local check's wrong opens were three jokes and two plain doctrine questions, and the quiet messages were written to sit close to the line. Bible verses a student may paste: the local check opens on 129 of the WEB's 37,677 verses, a translation the classifier never trained on, mostly commands that begin "Don't". The model check took a median 1.2 seconds (longest 3.8).

**Enforced in.** `webapp/safety.py` (`precheck`, `_similar`, `points_to_help`, `check`), `webapp/crisis_classifier.json` (the trained weights, from `scripts/train_crisis_check.py` and `scripts/crisis_train.json`), `chat()`, `_fixed_reply` and the startup load in `webapp/app.py`, `metrics.count` and `COUNTERS` in `webapp/metrics.py`, and `webapp/ops.py`. Covered by `tests/test_crisis_check.py` and `tests/test_chat_route.py`. Measured by `evals/crisis/run.py` (free for the local check, about a cent with `--model`).

**Reverse when.** The window should do more than open, such as replacing the reply or notifying an adult. That needs the school's procedure under decision 0009 first. After any change to the word list, the training data, or the model check's prompt, score a new blind set: sets 1 and 2 are spent, and set 3 has been scored once.
