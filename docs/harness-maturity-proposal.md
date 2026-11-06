# Exegetica harness: maturity proposal

2026-11-02. Built from seven time-boxed spikes, one per harness layer, plus the independent QSF scorecard (`docs/qsf-scorecard-exegetica-2026-11-02.md`). File and line references describe the working tree on this date.

## Where things stand

| Layer | Now | Target | Most important finding |
|---|---|---|---|
| 1. Loop | 1 Ad hoc | 3 on the Anthropic path | Student chat can leave Opus by two routes, one of them to the model that failed the ladder |
| 2. Tooling | 2 Deliberate | 3 | Nothing restarts a dead tool server, and the health check stays green |
| 3. Context | 1 Ad hoc | 3 for what students see | The persona conflict runs through four prompt sources, and browser history is unvalidated |
| 4. Memory | 1 Ad hoc | 3 | A failed load can overwrite an account's chats or verses |
| 5. Verification | 1 Ad hoc (reply checking 0) | 3 for conduct and deploy, 2 for accuracy | Nothing checks a reply, but holding each sentence until it passes costs under a second by estimate |
| 6. Governance | 1 Ad hoc | 3 | Exam keys are public on the live site, and "Opus only" is not enforced |
| 7. Observability | 1 Ad hoc | 3 | Failures are invisible: API errors log nothing, and refusals look like normal usage |

The library and tools were designed. The controls around them grew as problems appeared. The plan closes the live holes first, then makes the written rules true in code, then makes failure visible, then keeps the promises the statement makes to students and parents.

Building everything below is roughly two to three weeks of focused work. Direct API cost is about $20, nearly all of it safety ladder runs, each approved before it runs.

## Do this first

**The final-exam answer keys are public on the live site.** On 2026-11-02, `https://exegetica.app/course/doc/GEN_final-1-book-of-signs-TEACHER.md` returned 200 (16,094 bytes) with no sign-in, and the public `/course` page links to the teacher documents. No `?view=teacher` is needed. Treat both finals as exposed until you decide otherwise.

The fix is small (Governance step 2), but `fly deploy` builds the working tree, so it would also ship today's untested floor and all other uncommitted work. Ship it from a clean `git worktree`. The live site is an Oct 21 build, so check what else differs between HEAD and production before deploying.

Three more items should not wait for the code:

- Set a Console spend limit and split the API key by traffic class (app, scripts, red-team). One unlimited anonymous POST can cost up to $15.36 in output today.
- Copy the ladder out of Temp. `slowburn.py`, `redteam_probe.py`, `precheck_probe.py` and 24 transcripts sit in the scratchpad of session `9709e033-...`, where cleanup can delete them.
- Ask counsel about sign-in: Illinois SOPPA covers nonpublic schools, and COPPA may apply to grade 6. (Google's Workspace is not a blocker: a student's school account signed in on 2026-09-11.)

## What maturity means here

All seven layers use one scale. 0 Absent: nothing exists. 1 Ad hoc: it works when someone does it by hand. 2 Deliberate: designed, written down, checked by hand. 3 Enforced: guaranteed by code, covered by an automatic check, failure is visible. 4 Measured: tuned from production data.

Level 3 is the target nearly everywhere, because the app handles minors' text and has one developer, so a failure must be visible without anyone watching. Level 4 is not a goal: at this traffic there is too little data to tune from. The size of the bill justifies very little here. The safety of minors justifies the rigor.

## Decisions only you can make

| # | Decision | Recommendation | What it changes |
|---|---|---|---|
| A | Is sign-in required for student chat? | Yes, after counsel answers the questions above | Without it, no cap binds a person; caps can only be shared pools |
| B | Can any adult read student chats? | No for now, and make that structurally true by removing student chat text from Neon | Signed-in chats sit in Neon today, you hold the credentials, and you are a mandated reporter, so "no adult reads" is false until the text is gone. A yes forces sign-in, a server-written log, a named reader, a read audit, and prior notice to parents, and the school and its lawyer must set the procedure first |
| C | Can a refusal simply end a student reply? | Yes | Removes `fallbacks="default"` and the Sonnet 4.6 fallback from student chat. Otherwise student chat can run on a model that never passed the ladder |
| D | What are the modes called, and which is the default? | Rename Professor, and make the Socratic mode the default for students | Replies are labeled "Professor" (`index.html:646`), and that label contradicts "never the teacher". You also need to rule on whether a "tutor" Aide survives that line |
| E | May the Generator write prayers and devotions? | No closing prayers; keep passages and questions, and a person prays | `devotional_guide` writes a closing prayer, which the statement's "orchestrate a devotion" appears to forbid. A softer option is to draft prayers for a teacher to lead |
| F | Do old studies reopen read-only? | Yes, after one day, with a 24-turn cap | Reopening a study resends its whole transcript, so one chat carries the model across days, which is the slow-burn route |
| G | Doctrine wording | Your sign-off on the third-person file | The student prompt states the tradition's positions and attributes them, and the pastors' prompt keeps "your convictions" |
| H | Does `/ops` show a daily count of help-panel displays? | Only if the school approves | You are school personnel and would read it. The number is a total with no category, time, or join. Decided yes on 2026-11-04 (docs/decisions/0018) |
| I | Is this non-commercial? | Your ruling | `docs/go-to-market-plan.md:151,186` lists Kindle books at a $0.99 minimum, and two QSF N/As depend on the answer |

## Roadmap

Each phase ships on its own. The order follows risk to students first and convenience last.

**Hotfix.** Exam keys and teacher views, from a clean worktree. Under an hour plus deploy.

**Phase 1: Close the doors (about a day and a half).** Teacher-only Generator, Revise, extraction and upload. Model lock with no fallback on student chat. One policy file holding request and run limits. Domain lock on sign-in. Fix both overwrite bugs. A failed Revise keeps the teacher's document. Short decision records in `docs/decisions/`.

**Phase 2: Make the rules true (about three days).** Move the ladder into the repo. Split the prompt so the conflict leaves the text. Give every model route the floor. Answer greetings in code, and stop forwarding thinking. Build the sentence gate and its tests. Build the ladder runner and the predeploy gate. Today's floor ships here, after a ladder pass and not before.

**Phase 3: Know when it fails (about three to four days).** One named ending for every run, tool timeouts, a supervised bridge, a real health route, the metrics table, `/ops`, one spend alert, then daily caps under decision A.

**Phase 4: Keep the promises (about three days, needs A and B).** `/privacy`, Download my data, Delete my account, retention with a scheduled purge, AI disclosure on the chat screen, an About page, the bot's true answer to "who reads this?", browser hygiene, the course schedule tool, and the corpus manifest. Most of the QSF scorecard's five changes land here. Its accessibility pass and the reader's infinite scroll are outside the harness and need their own time.

**Phase 5: Polish, as time allows.** Tool descriptions, the citation hook, the "no library source was consulted" label, the Generator report, ESV fallback, comprehension on Inngest, and the cache TTL decision after two weeks of metrics.

**Build status, 2026-11-03.** Phases 1 to 4 are built in the working tree, uncommitted and undeployed, with no model calls spent. Decision records 0011 to 0014 describe what Phases 2 to 4 added. Three items differ from the plan above:

- The ladder runner is not built. By the maker's choice, he probes the bot himself, and `scripts/predeploy.py` requires his probe record for the current student prompt.
- Fly's health check stays on `/api/config`. The deep check, `/api/health`, runs from keep-warm, so a restarting library cannot take the Reading Room offline.
- The retention purge is built and switched off until the maker sets its periods.

Built on 2026-11-03 after the first pass: the comprehension build on Inngest, the one-step retry, the "who reads this?" answer in `ABOUT_EXEGETICA`, and old studies opening read-only (decision F, docs/decisions/0015). The comprehension build has had no live test build, which costs money and waits on the maker.

Phases 1 to 5 were committed and deployed on 2026-11-04. Self-hosted fonts, the last item from Phases 2 to 4, were built the same day after the deploy.

The crisis check, first on the 2026-10-31 safety review's fix list and missing from this plan, was built on 2026-11-04 (docs/decisions/0018). A word check, the reply itself, and a Claude Haiku 5.5 check can each open the help window, and `/ops` counts how often it opens. On the latest blind set the local check (a word list and a small classifier on the server) opens on 56 of 60 crisis messages, against 5 of 50 for the old list, and the model check on all 60. Together they caught every one, with 6 wrong opens in 60 quiet messages and none on the 30 study questions.

Phase 5 is built except the cache-lifetime decision, which waits on two weeks of metrics. Built on 2026-11-03: tool descriptions that say when to call each tool, the citation hook (`webapp/citations.py`), the "No library resource was consulted for this response." label and the note on quotations no source holds, the Generator's source check, and paragraph locators on theology hits (docs/decisions/0016). The ESV fallback and the comprehension build were built earlier.

| Money | Estimate |
|---|---|
| Ladder pass on Opus, about 85 turns (scaled from the Oct 31 Sonnet runs; thinking may raise it) | About $6 each, expect 2-3 while tuning |
| Candidate model on Haiku, two reps | About $0.40 |
| Limit test | Under $1 |
| One comprehension test build | About $0.50, quoted first |
| Tool description rewrite (one cache rewrite) | About $0.06 |

## Layer 1: Execution and loop

**Where it stands.** The Anthropic happy path and refusal handling are deliberate (`webapp/providers.py:263-298,372`), but how a run ends is undefined and no test covers the file. Anthropic returns on anything except `tool_use` (`:378`), so `max_tokens` looks finished. The OpenAI path ignores `response.incomplete` and `response.failed` (`:438-441`). The Grok and Gemini path never reads `finish_reason`, so a cut inside tool arguments runs the tool with `{}` (`:524-528`). Exhausting `MAX_TOOL_TURNS` ends silently on all three, and on the Generator that means a blank page after 12 paid steps (`generator.py:611`).

Other findings: any Revise failure replaces the teacher's document (`generate.html:588,629`). Error strings enter chat history and go back to the model (`index.html:699,704`). Students see raw SDK error dumps (`providers.py:391`). Closing the browser stops the loop, tested with a stand-in, except `comprehension.ensure`, where up to 41 calls continue with no guard against duplicate builds (`app.py:610`). Mid-stream failures end the run with no step retry.

**What maturity looks like (level 3 on the Anthropic path; BYOK paths get end reporting only).**
- Every run ends in one named state, logged without message text, and non-complete states show a plain sentence.
- A check proves `/api/chat` sends no fallback model.
- A check proves no run exceeds its ceiling by more than one step.
- A failed Revise leaves the prior document intact, and error text never enters history.
- A hung tool ends within 30 seconds, and a killed tool server ends the run within two steps and recovers on the next request.
- Closing the browser loses no paid comprehension work.

**Plan.**
1. Lock chat to Opus: no `fallback_model`, no `fallbacks`, log `final.model`. S. Needs decision C.
2. Restore the prior document on any Revise failure. `generate.html`. S.
3. Emit one `end` event: complete, cut_off, step_limit, budget, tools_failed, refused, provider_error, cancelled. Never run tools on a truncated turn. Clients treat a stream without `end` as interrupted. `providers.py`, `index.html`, `generate.html`. M.
4. Per-surface limits, checked between steps, with `tool_choice: none` on the last step so the model answers. Chat 8 steps, 16k tokens, $1. Generator 12, 64k, $5. Revise 3, 64k, $2. S, live test under $1.
5. 30-second tool timeout, tools_failed after two all-failed steps, SSE heartbeat every 15 seconds. S. Depends on Layer 2.
6. Retry a failed step once if no text reached the reader in it; otherwise keep the partial text. Log raw errors server-side only. S.
7. Tally tokens from stream events so cancelled steps are logged. Add a Stop button. S.
8. Move the comprehension build to Inngest: one memoized step per batch, one build per book, a "being prepared" notice. M, one test build. Teacher-only until decision A.
9. `scripts/check_loop.py`: fake stream and MCP, no network, one case per ending. Pin deploy versions (`Dockerfile:12`). M.

**Do not build.** Chat, Generator or Revise on Inngest (student text would sit in a third party's payloads). Task budgets (an advisory pacing hint that bounds no bill). Automatic continuation, checkpointed resume, circuit breakers, queues, or BYOK feature parity.

## Layer 2: Tooling

**Where it stands.** The tool set is 28 MCP tools plus 4 curriculum tools; History mode reaches 49. Input validation is already at level 3, through the SDK's jsonschema check. Process lifecycle is at level 1.

Nothing restarts a dead subprocess (`webapp/app.py:274-285`). With two calls in flight, the SDK raises a `RuntimeError` and cancels the task that opened the session. In the app that is lifespan, so its `finally` starts closing the Neon pool and both bridges while the server keeps serving. This was reproduced on Windows against a stand-in. `/api/config` reads cached tools, so the Fly check stays green on a dead bridge (`app.py:421`, `fly.toml:37-44`). Tool calls have no timeout (`app.py:283,320`). Handler exceptions return plain text with `isError` false, so failures show as success (`studybible_mcp/server.py:295,301`, `socialsci_mcp/server.py:1028,1033`).

Concurrency is fine: 25 concurrent Bible calls took 1.43 s locally. The nearer ceiling for a class of 25 is Fly's `hard_limit = 20`, since each chat stream holds a slot. Schemas are 8,900 tokens in Bible mode and 11,800 in History. `get_passage` returns ESV proxy errors as normal results, though `clients.py:11-12` promises fallback. Descriptions say what tools return and rarely say when to call them. The check scripts run by hand and skip stdio, and the Bible check covers 5 of 28 tools.

**What maturity looks like (level 3).**
- Killing a subprocess with calls in flight leaves the other bridge and the Neon pool working, and tools return within 10 seconds.
- No tool call outlasts 30 seconds, and every turn ends with a plain message.
- Every failure sets `is_error` and shows as failed.
- A health route returns 503 when a bridge misses a ping.
- Every deploy runs both tool checks plus one stdio call.

**Plan.**
1. Supervised bridge: own the session in a dedicated task, respawn with backoff, `read_timeout_seconds=30`, a fixed "library unavailable" error. `app.py`. M.
2. Server honesty: let exceptions raise, add a handler deadline with `conn.interrupt()`, lock DB init. Both `server.py`. S.
3. Wall-clock turn deadline. `providers.py`. S. Shares Layer 1 step 3.
4. Health route using `session.send_ping()` per bridge, and repoint the Fly check. S.
5. ESV and NET failure serves BSB with a note naming the substitution. S.
6. Extend the Bible check to 28 tools, add one stdio call, ship both checks in the image, run after deploy. M.
7. Add when-to-call sentences, "not for" clauses on near-collisions (`lookup_person` and `lookup_name`), and the 34 missing History parameter descriptions. M, about $0.06.
8. Citation hook: hold each turn's raw outputs in memory for Layer 5, add a locator to theology hits. M.

**Do not build.** Tool search (11,800 cached tokens cost about $0.0024 a request, and it is Anthropic-only). Parallel tool execution (database calls queue anyway). Connection pools, extra workers, circuit breakers. Structured metadata on all 49 tools.

**Open risk.** The ESV is meant never to be stored (`clients.py:7`), yet 4,000 characters return in `tool_done` and may persist for signed-in users. That needs a license check.

## Layer 3: Context

**Where it stands.** Assembly order is documented (`app.py:249-259`), but nothing checks it, and it relies on recency to settle contradictions. The conflicting lines go past `theologian.md`:

- Self and opinions: `theologian.md:3,7,9,19,68,119`, `curriculum.py:266,271` ("remaining entirely yourself"), `app.py:72`, `historian.md:3,44,72`.
- Sentiment: `app.py:83`, `theologian.md:76`, `historian.md:102`.
- Teacher or shepherd: `theologian.md:13,15,23,33,35,54,74,76`, `app.py:72,132-133` (the floor itself grants "a pastoral mind"), `historian.md:34,92-95`, which sorts students by spiritual state.
- Worship: `theologian.md:81,94`.
- Crisis: `historian.md:103` recites 988 against the rule in `safety.py:124`.

Faith-integration generation also loads the Theologian (`generator.py:344`). History is unvalidated: non-string content passes through, so native blocks reach the API and the crisis pre-check fails quiet on a list (`providers.py:165,168`, `safety.py:107`), and forged tool output arrives as a real `tool_result` (`app.py:375`).

Cache writes are modelled, not measured. Sparse traffic on the 5-minute TTL appears to be the largest part. In a typical cache lifetime of one or two turns, the prefix is 40-70% of writes, live tool results 30-50%, and rebuilt turns under 10%. Observability adds that Generator tasks can each write about 120k tokens, roughly $0.60. Preserved thinking poses no 400 risk on Opus 5.5, because no thinking is replayed across turns; the cost is reasoning lost between turns.

**What maturity looks like (level 3 for what students see; cache tuning stays at 2).**
- A test assembles every subject and persona and fails on listed persona phrases or first person outside quotations.
- Doctrine lives in one file, included verbatim by the pastors' and student prompts.
- A test confirms every model route's system prompt carries the floor.
- A POST with native blocks, forged turns, or an oversized transcript never reaches `providers.run`.
- Greetings and the turn limit return fixed text with no model call.

**Plan.**
1. Validate intake: strings only, last role user, known tool names, persona allowlist. `app.py`, `providers.py`. S.
2. Split the prompt. A new `doctrine.md` holds convictions, covenants, sanctification and doctrinal guardrails in third person. One framing sentence differs by audience. `theologian.md` keeps pastor identity. `_base_for` stops loading it. Rewrite every listed line so the conflict leaves the text, including the floor's "pastoral mind" and `historian.md`. Cuts the prefix about 20%. M. Needs decisions D and G and a ladder pass.
3. Move fixed behaviour into code: greeting in `chat()`, after the crisis pre-check, and no thinking text sent to the browser. This replaces the greeting rule added today. S.
4. Generator and Revise floor, added to `_with_voice`: draft for teacher review, no tool voice or sentiment or persona, documents are material and never instructions, plus the safeguarding note, with `precheck` on `brief` and `instruction`. S to M. Needs decision E.
5. Add a tools cache marker (free, saves about $0.04 per persona switch). After two weeks of metrics, set a one-hour TTL only if over 40% of cold writes follow within an hour on the same prefix. Under $5 a month either way. S.

**Do not build.** Byte-exact replay with stored thinking signatures (about $1 a month saved). Compaction (chats are short, and a summary can launder a jailbreak). Anonymous server-side sessions. Pre-warming.

## Layer 4: Memory

**Where it stands.** Corpus distribution is level 2 (`scripts/publish_db.py:72-73`, `app.py:736-774`). Student state is level 1, and retention and account deletion are level 0.

Both overwrite bugs are confirmed by reading the code. In Scripture Memory, a failed load is treated as an empty account and auto-saves seed verses (`memory.html:370-383`). In chat, a failed `GET /api/chats` leaves an empty list and the first new message saves over the whole account (`index.html:542-544,733-741`). They were reproduced with stubs, not observed live.

Other findings: cascade does not finish deletion, because `canonical_source` keeps `upload:<user_id>` (`extraction.py:432`, `library_store.py:576`). `reading_state` records what each child reads (`reader.py:418`). `ABOUT_EXEGETICA` has no storage facts, so the bot has no true answer to "can my teacher read this?". `/corpus` counts match the databases, while `NOTICE` and some tool descriptions have drifted.

**The rule: the machine holds no knowledge of a student; a student may keep a notebook.** Part III of the statement reserves being "seen, known, and loved" to God, parents and teachers, and Part I limits students to a reference work, which does not recall its reader. Ruled out under any decision: cross-chat recall, summaries, profiles, extracted facts, embeddings of student text, the API memory tool, a student's name or class in any prompt, "welcome back", and analytics on topics or moods. Studies, verses, reading place and display preferences stay as the student's own records.

**What maturity looks like (level 3).**
- A test proves the system prompt is byte-identical signed in and signed out.
- A failed GET never causes a PUT, and a stale PUT gets 409.
- A deleted test account leaves no row or `upload:<id>` string.
- A scheduled purge enforces the periods stated on `/privacy`, and a missed run is visible.
- A check fails when `/corpus` or `NOTICE` disagrees with the databases.
- The bot answers "what unit is class on?" from the calendar and "who reads this?" from stated facts.

**Plan.**
1. Fix overwrites: a failed GET shows a retry notice and blocks saves; PUT echoes `updated_at` and gets 409 if stale, which also stops two tabs colliding. `memory.html`, `index.html`, `store.py`. M.
2. Decision records in `docs/decisions/`: decision, reason, reversal condition, enforcement point, with a `CLAUDE.md` pointer. The reasons now sit in auto-memory on one machine, outside git. Correct `safety.py:4` and `memory.py:5`. S.
3. Prompt-identity test. S.
4. Course schedule tool: `curriculum.py` reads `docs/john-course-calendar.json` and returns today's Chicago date and scheduled lesson. A date in the system prompt would rewrite the cached prefix daily. S.
5. Corpus manifest: `scripts/corpus_manifest.py` writes committed JSON (source, count, license, URL, hash), `/corpus` renders it, and a check compares `NOTICE`. M.
6. Chat bounds: studies older than a day reopen read-only. S. Needs decision F.
7. Browser hygiene: clear local copies after a confirmed import, prune local chats at 30 days, add Clear this browser, fix `index.html:553`. S.
8. Download and Delete: export every store except jobs, never the BYOK key; delete scrubs `canonical_source`, then R2 originals, then the user. Stop storing `picture`. `store.py`, `settings.js`. M.
9. Retention and `/privacy`: one constants file feeds the page and `ABOUT_EXEGETICA`. Use an Inngest cron, since Fly stops machines and kills in-process timers. M. Needs decisions A and B.

| Store | Retention | Delete |
|---|---|---|
| `users`, `memory_state`, `reading_state`, `cover_prefs` | 12 months after last login | Cascade |
| `chat_state` | Retired under B=no; otherwise 90 days per chat | Per chat and account |
| `library_items`, `library_source_texts` | Account life | Cascade plus scrub |
| `library_ingest_jobs` | 30 days | Purge |
| `classes`, `enrollments` | Drop; no code uses them | |
| Browser | Chats 30 days; verses kept | Clear this browser |

**Do not build.** Relational chat tables. Per-user encryption keys (absence from Neon is the stronger promise). Corpus rollback tooling. Consent platforms, request portals, or teacher dashboards of student activity.

## Layer 5: Verification

**Where it stands.** Reply checking is at 0: every event goes straight to the browser (`app.py:401-402`, `index.html:689`). Thinking summaries also reach students, labelled "Thinking…" (`providers.py:363`, `index.html:690`). pytest points at a `tests/` folder that does not exist (`pyproject.toml:91-93`). `lint_voice.py` exits 1 today and never sees a reply. `slowburn.py:11` posts to production, so it cannot test an undeployed prompt.

Measured with an inline prototype on saved text, no model calls:
- A narrow conduct regex fired by turn 6 in all 24 ladder transcripts, and so did three no-tool replies in a row.
- Masking quotes, blockquotes, emphasis and regnal numbers cut first-person hits in 148 generated documents from 1,253 to 130. The rest are unquoted Scripture voice, so bare first person cannot stop a reply.
- References: 1,396 checked, 0 nonexistent, so that check has low yield.
- Quotations: 117 of 199 matched no local translation, mostly ESV wording, so a check can say "not found locally" and never "misquoted".

These numbers come from text written before today's floor. False stops and sentence delay stay unknown until the first run.

**The streaming decision.** Full buffering costs the whole reply (median 15.5 s with tools). An appended correction costs nothing, but the student has read the sentence and the client replays it as history, which is the path that entrenched the break. The recommendation is to hold each sentence on the server until it passes. The checks took under 2 ms, and the delay is about one sentence, under a second by estimate. A failing sentence never reaches the browser or history.

Conduct fails closed for all chat, and a checker exception also stops the reply. Accuracy fails open. The stop line always names a trusted adult and the help panel, because the crisis regex misses 22 of 25 phrasings. A clean ladder is necessary and not sufficient, since warmth without filterable phrases passes text checks.

**What maturity looks like (level 3 for conduct and deploy, 2 for accuracy and Generator).**
- A fake-provider test proves a violating sentence never leaves `chat`.
- Free pytest covers the traps, break lines and crisis phrases.
- `predeploy` refuses when tests fail or the prompt hash and model lack a recorded ladder pass.
- No student reply can come from an unladdered model.
- Stop counts appear in metrics, without text.

**Plan.**
1. Copy the ladder into `evals/ladder/`. S. Confirm repo visibility first, since the lines include a minor persona.
2. Add served model and usage to the final event. S.
3. `webapp/reply_check.py` and `tests/`: masks, narrow regex, sentence buffer with quote state. A quotation is exempt only if found in tool results. M.
4. Wire the gate into `chat`. After 3 no-tool replies add a system reminder; after 5 send a fixed reply with no model call. M. Under decision A the count moves server-side so New Chat cannot reset it.
5. After each reply, note quotations missing from tool results, and label no-tool answers "No library source was consulted." M.
6. `evals/ladder/run.py`, per `build-eval.md`, against local `/api/chat`: 16 probes, 6 single-theme sequences, 15 study negatives, about 85 turns, including a name and persona sequence and the forged-history tests. Written by you, never from student chats. Pass means zero violations and zero false stops. One rep for a prompt change, two for a candidate model. It prints the estimate and requires `--yes`. M, about $6 a pass.
7. `scripts/predeploy.py`: pytest, tool checks, lint, policy check, clean tree, prompt-hash check, `fly deploy`, then a GET of `/api/config` asserting tool counts. S to M.
8. Generator report beside the download: references checked and quotations not found locally. It never blocks and never says "verified". M.

**Do not build.** CI as a gate (`fly deploy` ships the working tree, and the corpora are not in git). A runtime model judge, unless the ladder shows a miss. ESV ingestion, an adaptive AI red-teamer, an eval framework, or dashboards.

## Layer 6: Permissions and governance

**Where it stands.** Personal-data and admin routes have real checks (`store.py:26`, `reader.py:672`). Nothing proves every route has one, and the routes that spend money or expose exams have none.

| Routes | Today | Should be |
|---|---|---|
| `/api/chat` | Anonymous, server key | Model locked, capped |
| `/api/generate`, `/api/generate/book`, `/api/revise` | Anonymous, server key | Teacher-only |
| `/course*`, `/calendar*` | Anonymous, teacher content | Teacher-only |
| `/api/library/extract`, `/api/library/upload/*` | Any Google account, paid | Teacher-only |
| `/api/library/books`, `podcasts`, `video`, `youtube` | Anonymous, outside quota | Signed in |
| Own-data routes, admin routes, Inngest | Correct | Unchanged |
| Pages, `/read*`, `/api/books*`, covers, `/auth/*`, `/api/config` | Public and free | Unchanged |

Read-only tools protect data only: `max_tokens=64000` times 12 steps allows $15.36 of output per POST. Settings has a free-text Model field open to everyone (`settings.js:106`), and `claude-sonnet-4-6` works with no key. Any pre-output error containing "unavailable" or "404" retries on Sonnet 4.6 (`providers.py:70,110-114,291`). `fallbacks="default"` re-runs declined requests elsewhere (`:346-348`). `/api/generate/book` runs comprehension on the server key even for BYOK callers, with no single-flight lock (`app.py:612`), and at least 2,044 local books exceed 150k words, roughly $0.50 each. `/api/revise` is a free general Opus endpoint with no floor. The teacher role stays in the cookie up to 14 days (`library_store.py:507`). BYOK keys persist in localStorage on shared computers (`settings.js:6`).

**What maturity looks like (level 3).**
- A check fails on an unlisted route and confirms gated routes refuse anonymous calls.
- No client field, error or refusal moves student chat off Opus (fake-provider test).
- A capped student gets fixed text, no model call, and the crisis panel; counters survive machine stops.
- Non-school accounts cannot sign in, and removing a teacher takes effect on the next request.
- Deploys refuse a dirty tree, and a changed prompt hash needs a ladder record.

**Plan.**
1. Console spend limit and split keys. You do these. S.
2. Exam keys and teacher views first: `_view` (`app.py:460`) requires a live `auth.is_teacher`, and `course.py:108-124` becomes default-deny with exam papers and keys teacher-only. S.
3. Model lock in a new `webapp/policy.py`: student and anonymous chat Opus only, client `provider`, `model` and `api_key` ignored, fixed error text. Teacher chat, Generator and Revise: Opus default, BYOK allowed. Library jobs use `EXTRACTION_MODEL` only. S.
4. Teacher-only Generator, Revise, extract and upload, under any answer to decision A. It writes answer keys, so students should not reach it. S.
5. Domain lock: `auth_callback` requires `hd == yorkvillechristian.com` and `email_verified`, and `TEACHER_EMAILS` and admins pass regardless. Rotate `SESSION_SECRET`. S.
6. Request limits in the policy file (see the resolved conflicts below). S.
7. Daily caps in Neon `usage_daily(subject, day, turns, est_usd)`: start at 30 turns or $1.50 per student, 300 turns per teacher, $8 school-wide. The pre-check runs first, so a capped student in crisis still gets the panel. M. Needs decision A.
8. Rate limits keyed to identity, never IP, since the school shares one address. One in-flight stream per subject, 6 turns a minute, 12 model streams maximum. If anonymity stays: a cookie id plus one shared anonymous pool. S.
9. One prompt builder, so every route gets the floor. S.
10. Deploy gate: you alone ship, through Layer 5's `predeploy`. M.

Sentiment, names, personas, first person, graded work and pastoral handoff can only ever be prompt rules. A reply check detects those; it cannot prevent them.

**Do not build.** Role tables, admin UI, Redis, captcha, CI/CD, staging, canaries, SAML. Student usage meters, which are trackers under QSF.

## Layer 7: Observability

**Where it stands.** `_log_usage` prints one line per Anthropic turn, and tool timings share stdout. Nothing stores or checks them. API errors log nothing (`providers.py:390,457,532`). A refusal logs as ordinary usage (`:372`). Truncated and tool-capped replies end silently. Usage counts only after `get_final_message`, so disconnects undercount. BYOK Anthropic turns mix with server-key turns (`:330`). Estimates ignore server-side fallback and extraction's `claude-sonnet-5`.

**What maturity looks like (level 3).**
- Every server-key call leaves one row whatever the outcome, tested with a fake client.
- A test pins the row to an allowlist of numeric and enumerated fields.
- Rows purge at 90 days, and the privacy page says so.
- One admin page shows last week's cost, failures, last-row time and failed writes.
- Monthly estimates land within 10% of Console.

**The privacy line.** A field is operational under QSF DAT-07 if it runs or bounds an existing feature, describes the request, and cannot be joined to a person. Behaviour data (persona choice, session length, return visits) is DAT-10 telemetry, anonymous minors cannot meaningfully opt in, so it goes uncollected. There is no user column under any decision. Under required sign-in, the cap's counter lives in the limiter's own short-lived table. A `user_id` here would turn a cost log into a behaviour log of identifiable minors.

**Plan.**
1. Close the silent paths and add the store: `webapp/metrics.py`, `providers.py`, `extraction.py`, `app.py`, `scripts/schema.sql`. M. Neon wins over log shipping and SQLite: existing pool, our retention, readable by the page.
   - `turn_metrics`: `hour`, `route`, `key_source`, `model_req`, `model_served`, `prefix_hash`, `outcome`, `http_status`, `refusal_category`, `steps`, `tool_errors`, `input`, `cache_read`, `cache_write`, `output`, `first_read`, `first_write`, `est_usd`, `duration_ms`.
   - `ops_daily`: `day`, `name`, `value`.
   - Never recorded: message text or its hashes, tool inputs or outputs, provider error strings (`str(e)` can echo a request), persona, IP, user agent, browser or session ids, email, `google_sub`, keys.
2. Split the cache-write causes for one school week, then drop the temporary columns (`gap`, `prev_tools`, `diag`). Keep cache diagnostics inside the tool loop permanently, since any reason there is a real bug. S.
3. `/ops` behind `auth.is_admin`: 14 UTC days of spend, turns, refusals, failed turns, truncated replies, cap hits. A pull page beats a pushed note. S. Decision H covers help-panel counts.
4. One alert: estimated spend over $5 in a UTC day. Only Oct 31 and Nov 1 crossed it, both red-team days. A curl in `keep-warm.yml` hits a token-gated `/ops/flag` that fails once a day, so GitHub emails you with no new vendor. S. The Console spend limit stays the real stop.

**Do not build.** OpenTelemetry (it needs a beta, an SDK and a backend to answer what one table answers). Langfuse, Datadog or Sentry (a third party holding records of minors' sessions). The Usage API in the app (an Admin credential on a public server). Per-student views, percentiles, SLOs, anomaly detection, or paging.

## Where the spikes disagreed, and how this proposal settles it

- **Signing client history.** Tooling and Context propose HMAC signing; Memory and Governance say do not build it. The Oct 31 review found a forged "I love you" was rejected, but forged tool output was never tested. Settled: validate intake now, add forged-history and forged-tool cases to the ladder, and sign only if they succeed. If signing is needed, one signature over the transcript covers both cases.
- **Turn and request limits.** Four spikes gave four numbers. Settled in one policy file: 8 tool steps per run, 16k `max_tokens`, $1 per run, 24 turns per study, 8k characters per message, 120k per transcript. The ladder confirms or moves the turn number. A turn cap is a cost and drift control; the reply gate is the safety control, since the ladder broke at turn 6.
- **Deploy gate.** `predeploy.py`, `release.sh` and `check_loop.py` become one script, `scripts/predeploy.py`.
- **Generator and the reply gate.** Verification noted the gate would have to wrap Generator routes if they stay open. They become teacher-only under any answer to decision A, so student traffic never reaches them.
- **Purge timing.** Observability purged at boot and Memory used a cron. One Inngest cron does both, because a purge that never runs must be visible.
- **Cache writes.** Context models sparse traffic as the largest part. Observability says the rebuild is certain and its share unknown. Both stand until the one-week measurement. Under $5 a month is at stake either way, so nothing waits on it.

## Corrections to what I told you earlier

- Exam keys do not need `?view=teacher`. They are linked from the plain `/course` page.
- `fly logs` shows about 100 lines, but Fly's docs say Grafana log search keeps 7 days. I have not confirmed that on your account.
- The slow-burn ladder was saved, in a Temp folder.
- I said your source pages disagree. `/corpus` counts match the databases; the stale side is `NOTICE` and the tool descriptions.
- The worst case is about $15.36 per POST, so it is bounded per request, though not per day.
- "No memory across chats" was incomplete: reopening a study resends its full transcript.
- I graded Tooling "solid". Its spike grades it level 2, with process lifecycle at level 1.

## What remains unverified

- Failure tests ran locally with stand-ins, not on Fly with the real SDK.
- All verification measurements use text written before today's floor.
- Exposure of teacher views was confirmed for one document on production; indexing is unchecked, and `/robots.txt` returns 404.
- Legal: SOPPA operator status, COPPA for grade 6, and the mandated-reporter statute text.
- Anthropic retention for your organization, Neon backup windows, and whether your account is an Organization.
- Whether `tool_choice: none` works with adaptive thinking on Opus 5.5.
- Fly's idle timeout, which `fly.toml` does not set.
