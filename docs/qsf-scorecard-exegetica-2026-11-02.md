# QSF Audit Scorecard: Exegetica

## Audit Information

| Field | Value |
|---|---|
| **Product** | Exegetica (web app in `webapp/`, MCP servers in `src/`) |
| **URL** | https://exegetica.app |
| **Audit Date** | 2026-11-02 |
| **Audit Mode** | Source Code, plus limited runtime inspection. Attestation answers not yet supplied, so this is not yet a Full audit. |
| **Auditor** | LLM-assisted (Claude Opus 5.5), self-audit for Hi Low Studio. Auditor has final authority on all scores. |
| **QSF Version** | 1.0 |

### Evidence basis

- **Tree audited:** commit `1a5ad5d` plus uncommitted changes, as they stood at 19:33 CST on 2026-11-02. Line numbers in this file were verified against that state.
- **The tree moved during the audit.** `webapp/app.py` and `webapp/static/index.html` changed at 19:09, and `docs/position-statement-christian-school.md` appeared at the same minute. Earlier line numbers were discarded and re-collected.
- **The working tree differs from production.** Live `/` is 46,637 bytes, last modified 2026-10-21. The working-tree `index.html` is 50,857 bytes. `ABOUT_EXEGETICA` (`webapp/app.py:146`) and the tools info bubble are not deployed.
- **Runtime method:** headless Chromium with Puppeteer and axe-core. Working-tree HTML and static files were served by request interception. No app process was started. All non-GET requests were aborted. Data calls were GETs to the live site.
- **Blocked request:** one anonymous `PUT /api/reading/position` from opening a book was aborted in the browser and never reached the server. No POST was sent to any `/api` route and no model call was made.
- **Not done, by instruction:** no app start, no production database query, no fly logs, no `.env` values (names only).
- **Not done, by tooling:** no screen reader session, no Firefox or Safari run, no real device test, no signed-in session.

---

## Result Summary

| | Result |
|---|---|
| **Must-Pass Gate** | **FAIL, 14 of 27 passed** (6 of those are N/A, treated as PASS by the kit) |
| **Total Scored Points** | **69 of 143** (48%), with 13 points pending attestation |
| **Domain Minimums Met** | **No.** Failing: Data Sovereignty 22%, Departure 33%, Durability 6%, Governance 25% |
| **Certification Tier** | **Not Certified** |

69 points clears the 57-point Verified line, but the gate fails first, so the point total does not produce a tier.

### Where the 69 points came from

| Source | Points |
|---|---|
| Earned on observed evidence | 40 |
| Awarded as N/A (feature absent) | 29 |
| **Scored total** | **69** |
| Failed | 61 |
| Pending attestation, not counted | 13 |
| **Available** | **143** |

The 40 evidenced points sit below the 57-point line. N/A accounts for 42% of the score.

### Failed must-pass gates

| ID | Confidence | Finding | Evidence |
|---|---|---|---|
| ATT-09 | High | Reading Room catalog auto-loads on scroll | `webapp/static/reader.html:1449-1451`; measured 48→96→144 tiles with no click |
| DAT-01 | High | No data export | `webapp/static/settings.js:98-100` |
| DAT-02 | High | No complete export of any user store | `scripts/schema.sql:7,43,51,57,65,180,208` |
| DAT-03 | High | No export path to count clicks on | `webapp/static/settings.js:98-100` |
| DAT-07 | Medium | Profile picture collected, stored, never displayed | `webapp/auth.py:116,136`; `scripts/schema.sql:12` |
| DAT-08 | Medium | No ad connections found; no policy exists to confirm it | `webapp/app.py:921-993` (no policy route) |
| HON-02 | High | Sign-up is self-service, account deletion has no path at all | `webapp/app.py:921-993`; `webapp/static/settings.js:178` |
| HON-03 | Medium | UI says "in this browser only" to signed-in users whose studies go to Neon | `webapp/static/index.html:553` |
| HON-13 | High | No statement of how the product is paid for | `webapp/static/reader.html:1695` is the only related text |
| DEP-09 | Medium | Internet requirement never stated, no offline mode | `webapp/static/index.html:373` |
| DUR-01 | High | Contrast and naming failures on primary flows | `webapp/static/index.html:18-19,182`; `webapp/static/memory.html:563` |
| DUR-02 | High | 17 of 21 visible chat controls under 44px; study list not keyboard reachable | `webapp/static/index.html:86,98,243,556` |
| GOV-01 | High | No privacy policy | `webapp/app.py:921-993`; live `/privacy` returns 404 |

---

## Domain Summary

| Domain | Must-Pass | Scored | Available | % | Min Met? |
|---|---|---|---|---|---|
| 01 Attention | 5/6 | 22 | 27 | 81% | Y |
| 02 Data Sovereignty | 0/5 | 6 | 27 | 22% | N |
| 03 Honesty | 2/5 | 13 | 22 | 59% | Y |
| 04 Departure | 3/4 | 5 | 15 | 33% | N |
| 05 Respect | 3/3 | 18 | 19 | 95% | Y |
| 06 Durability | 1/3 | 1 | 17 | 6% | N |
| 07 Governance | 0/1 | 4 | 16 | 25% | N |
| **Total** | **14/27** | **69** | **143** | **48%** | |

If all 13 pending points were attested as passes, the total would be 82, with Data Sovereignty at 41%, Departure at 53% and Governance at 44%. Durability would still miss the minimum, and the gate would still fail.

---

## Detailed Findings

Result key: N/A means the feature does not exist and no plan for it was found. The kit treats N/A as PASS on must-pass criteria and as full points on scored criteria. Points shown after the result are points awarded.

### Domain 01: Attention

#### 1A. Notification Architecture

**ATT-01** Must-Pass
- **Result:** PASS
- **Confidence:** High
- **Evidence:** No `Notification`, `PushManager` or `serviceWorker` usage anywhere in `webapp/`. Live `/sw.js` and `/manifest.json` return 404. No mail library or send path in `webapp/` or `src/`.
- **Notes:** None.

**ATT-02** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** No notifications exist. No notification plan found in `docs/`.
- **Notes:** None.

**ATT-03** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** Same as ATT-02. `webapp/static/settings.js:98-100` has no notification settings.
- **Notes:** None.

**ATT-04** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No notifications exist.
- **Notes:** None.

**ATT-05** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No notifications exist.
- **Notes:** None.

**ATT-06** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No notifications exist.
- **Notes:** None.

**ATT-07** 1 pt
- **Result:** N/A (1)
- **Confidence:** High
- **Evidence:** No notifications exist.
- **Notes:** None.

**ATT-08** 1 pt
- **Result:** N/A (1)
- **Confidence:** High
- **Evidence:** No notifications exist.
- **Notes:** None.

#### 1B. Engagement Pattern Prohibition

**ATT-09** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** `webapp/static/reader.html:1449` reads "infinite scroll: auto-reveal more as the sentinel nears the viewport". `webapp/static/reader.html:1451` runs an IntersectionObserver with a 600px margin that calls `render(false)`. Measured in Chromium: grid held 48 tiles, then 96, then 144 after scrolling, with no click.
- **Notes:** The catalog is finite (14,978 items) and the tiles come from memory. The kit fails any automatic load that lacks an explicit action. A "Show more" button already exists at `webapp/static/reader.html:630`.

**ATT-10** Must-Pass
- **Result:** PASS
- **Confidence:** High
- **Evidence:** Repository search for streak, consecutive and daily-login logic finds none. `lastPracticedAt` (`webapp/static/memory.html:395`) is stored and nothing penalizes its age. Mastery refresh starts only from a user click (`webapp/static/memory.html:617`).
- **Notes:** None.

**ATT-11** Must-Pass
- **Result:** PASS
- **Confidence:** Medium
- **Evidence:** No points, XP, levels, leaderboards or collectible badges. Scripture Memory has an eight-step flow with a "Mastered" state: class `.badge` (`webapp/static/memory.html:132`), a count on the Mastered tab (`webapp/static/memory.html:516`), and the toast "Mastered <reference> 🎉" (`webapp/static/memory.html:1009`).
- **Notes:** Flagged. Progress is tied to task completion, so this passes. A stricter reader could call the toast a reward signal and the state an achievement display.

**ATT-12** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** `webapp/static/memory.html:904` uses `<audio controls preload="none">`. No `autoplay` attribute or `.play()` call in `webapp/`.
- **Notes:** None.

**ATT-13** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No pull-to-refresh, random rewards or surprise reveals found.
- **Notes:** Assisted criterion, pending auditor confirmation.

**ATT-14** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No timer, session summary or check-in in any page. No session duration logic in `webapp/`.
- **Notes:** None.

**ATT-15** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** No follower, like or view counts. Tab counts at `webapp/static/memory.html:515-516` show the person's own verses and are private.
- **Notes:** None.

#### 1C. Interface Restraint

**ATT-16** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** Primary task is asking a question. `/` (`webapp/app.py:921`) opens directly on the composer (`webapp/static/index.html:370`), with no account. One screen.
- **Notes:** Primary task identification needs auditor confirmation.

**ATT-17** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No splash screen or interstitial in any page.
- **Notes:** `fly.toml:30` allows scale to zero, so cold starts can delay the first load. That is load time, with no timed animation.

**ATT-18** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** Modals found: Settings and Sources (user-opened), crisis help (`webapp/static/index.html:497`), verse and folder forms, and native confirms for destructive or data decisions (`webapp/static/index.html:739`). No promotional modal. No scroll or timer trigger.
- **Notes:** None.

**ATT-19** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Four pages carry a global rule (`webapp/static/index.html:47`). The reader's rules cover cover images only. With reduced motion emulated in Chromium these still reported live durations: `.cover` transform (`webapp/static/reader.html:123`), `.toc` slide (`webapp/static/reader.html:375`), `.stage` margin (`webapp/static/reader.html:390`), `.pb-fill` width (`webapp/static/reader.html:566`).
- **Notes:** Fail indicator: only some animations respect the preference.

**ATT-20** 1 pt
- **Result:** PASS (1)
- **Confidence:** Medium
- **Evidence:** Send is the single solid action on the chat screen (`webapp/static/index.html:180`). Example prompts are neutral outlined buttons.
- **Notes:** Flagged. Assisted criterion. The solid New study button competes with Send when the panel is open.

**ATT-21** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** Empty states are informational: `webapp/static/index.html:553`, `webapp/static/memory.html:632`. No upsell or urgency.
- **Notes:** The copy at `webapp/static/index.html:553` is calm and also inaccurate. See HON-03.

**ATT-22** 1 pt
- **Result:** PASS (1)
- **Confidence:** Medium
- **Evidence:** No urgency copy found in pages or Python. Pulsing is limited to a running tool and the streaming caret (`webapp/static/index.html:162`), both true status.
- **Notes:** Flagged. The brand accent `#c05a64` (`webapp/static/index.html:19`) is a muted red used on primary buttons. It creates no false urgency, but a literal reading of "red only for errors" would fail.

**ATT-23** 1 pt
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** `.prose{max-width:68ch}` (`webapp/static/index.html:141`) rendered 666px wide at 16px and at least 86 characters per line, measured at a 1280px viewport with a seeded English paragraph. Reader measured 47 characters per line, in range.
- **Notes:** The `ch` unit is the width of a zero, wider than average text in Public Sans, so 68ch overshoots.

---

### Domain 02: Data Sovereignty

#### 2A. Data Portability

**DAT-01** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** Settings has three tabs and no export (`webapp/static/settings.js:98-100`). The only download is one generated document as `.md` (`webapp/static/generate.html:323`). Anonymous studies sit in localStorage with no download control.
- **Notes:** `GET /api/chats` (`webapp/store.py:61`) returns JSON to a signed-in session. It has no UI and no documentation, so it does not count as an export feature.

**DAT-02** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** Per-user stores with no combined export: `users`, `memory_state`, `cover_prefs`, `chat_state`, `reading_state`, `library_source_texts`, `library_items` (`scripts/schema.sql:7,43,51,57,65,180,208`).
- **Notes:** None.

**DAT-03** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** No export control exists to reach (`webapp/static/settings.js:98-100`).
- **Notes:** None.

**DAT-04** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Endpoints in `webapp/app.py:921-993` are internal, session-cookie only and undocumented. No webhook or token path.
- **Notes:** None.

**DAT-05** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No export exists, so no format documentation exists.
- **Notes:** None.

**DAT-06** 2 pts
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** Library accepts EPUB, PDF, TXT and MD uploads (`webapp/static/library.html:565`), a teacher-facing route for source books. Browser-to-account import (`webapp/static/index.html:739`) handles only Exegetica's own format. Studies, verses and reading positions cannot be imported from another product.
- **Notes:** Flagged. A literal reader could pass the book upload. The criterion's intent, moving a person's data in, is unmet.

#### 2B. Data Collection Minimalism

**DAT-07** Must-Pass
- **Result:** FAIL
- **Confidence:** Medium
- **Evidence:** Google `picture` is read (`webapp/auth.py:116`), stored in Neon (`scripts/schema.sql:12`) and placed in the session (`webapp/auth.py:136`). No live UI renders it; only leftover CSS refers to it (`webapp/static/index.html:59`). Every page also sends visitors' IP and page URL to Google Fonts (`webapp/static/index.html:13`; hosts measured on `/`, `/memory`, `/read`, `/corpus`), though a self-hosted font path exists (`webapp/course_views.py:73`).
- **Notes:** Flagged. Assisted criterion, proportionality is the auditor's call. Fail indicator: data fields not tied to a current feature.

**DAT-08** Must-Pass
- **Result:** FAIL
- **Confidence:** Medium
- **Evidence:** Technical half is clean: the only third-party hosts on `/`, `/memory`, `/read` and `/corpus` were `fonts.googleapis.com` and `fonts.gstatic.com`, and no ad SDK appears in `pyproject.toml` or page source. Documentary half is absent: the pass condition requires a privacy policy confirming this and none exists.
- **Notes:** Flagged. No sharing with advertisers was found. This cures with GOV-01.

**DAT-09** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Settings shows name, email and role only (`webapp/static/settings.js:175-177`).
- **Notes:** None.

**DAT-10** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No analytics or telemetry in code. Measured hosts contain no analytics endpoint.
- **Notes:** A schema comment mentions possible future "teacher analytics". No plan for it was found.

**DAT-11** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** Chat, Memory and Reading Room work signed out (`webapp/auth.py:2`; `webapp/app.py:357` has no user check). No nag screens.
- **Notes:** None.

**DAT-12** 1 pt
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No retention statement exists. No purge job in `webapp/` or `.github/workflows/`. `chat_state` has no expiry (`scripts/schema.sql:57`).
- **Notes:** None.

#### 2C. Data Security & Deletion

**DAT-13** 3 pts
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** Observed: teacher source texts use AES-GCM at application level (`webapp/extraction.py:118`). `chat_state` and `memory_state` are plain jsonb at application level (`scripts/schema.sql:43,57`). Neon storage encryption is a vendor claim that needs attesting.
- **Notes:** See questionnaire.

**DAT-14** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No route, button or SQL deletes a user. Repository search for `delete from users` and account-deletion logic finds none. Foreign keys cascade (`scripts/schema.sql:44`), so the database side is ready.
- **Notes:** Individual studies can be deleted. The account row, email and name cannot.

**DAT-15** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Neither deactivation nor deletion exists.
- **Notes:** None.

**DAT-16** 2 pts
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** No deletion flow exists, so no deletion request can start a purge clock today.
- **Notes:** See questionnaire.

**DAT-17** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** Google OAuth with `openid email profile` scope (`webapp/auth.py:41`). No phone field.
- **Notes:** None.

**DAT-18** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** Live handshakes at TLS 1.0 and 1.1 refused, 1.2 and 1.3 accepted. HTTP returns 301 to HTTPS (`fly.toml:27`). Zero `http://` URLs in `/api/catalog`. Database uses a verifying TLS context (`webapp/db.py:53`).
- **Notes:** The live response carries no HSTS header. The criterion does not require one.

---

### Domain 03: Honesty

#### 3A. Dark Pattern Prohibition

**HON-01** Must-Pass
- **Result:** PASS
- **Confidence:** Medium
- **Evidence:** No guilt-laden decline copy. Confirms are neutral (`webapp/static/index.html:739`).
- **Notes:** Flagged. "I need practice 😓" (`webapp/static/memory.html:847`) pairs a first-person label with an anxious face. It is a self-assessment and declines no offer.

**HON-02** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** Sign-up: Settings, Sign in with Google (`webapp/static/settings.js:183`), Google consent. Deletion: no route in `webapp/app.py:921-993`, no control in Settings (`webapp/static/settings.js:178` offers only Sign out), and no support address anywhere in the product.
- **Notes:** No evidence of deliberate design, and the criterion headline says "deliberately". The pass condition does not depend on intent: deletion must be no harder than sign-up through the same channel.

**HON-03** Must-Pass
- **Result:** FAIL
- **Confidence:** Medium
- **Evidence:** `webapp/static/index.html:553` shows "Your studies are saved here, in this browser only." with no signed-in check, while signed-in studies go to Neon (`webapp/static/index.html:544`; `webapp/store.py:73`). `webapp/static/index.html:303,330` claim "Every answer is drawn from" the library or primary sources; `webapp/providers.py` sets no `tool_choice`, so tool use is requested by prompt and enforced by nothing.
- **Notes:** Flagged. The storage copy is a false statement in the product. The "every answer" claim is unenforced; no uncited answer was observed because no model call was allowed. The BYOK claim at `webapp/static/settings.js:104` matched the code path read.

**HON-04** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** No paid tier or subscription exists to cancel or downgrade.
- **Notes:** The account exit failure is scored once, under HON-02.

**HON-05** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No newsletter or marketing consent. The one checkbox, upload attestation, defaults unchecked (`webapp/static/library.html:572`).
- **Notes:** None.

**HON-06** 2 pts
- **Result:** N/A (2)
- **Confidence:** Medium
- **Evidence:** No price exists in the product.
- **Notes:** Flagged. `docs/go-to-market-plan.md:151` lists KDP in the build order and `docs/go-to-market-plan.md:186` notes a $0.99 minimum, so a priced channel is an open item.

**HON-07** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No timers, scarcity counts or urgency copy in pages or Python.
- **Notes:** None.

**HON-08** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** No consent or plan choice exists to weight. The import confirm uses the native dialog (`webapp/static/index.html:739`).
- **Notes:** None.

#### 3B. Algorithmic Transparency

**HON-09** 3 pts
- **Result:** N/A (3)
- **Confidence:** Medium
- **Evidence:** Reading Room is alphabetical (`webapp/reader.py:170`). No feed exists.
- **Notes:** Flagged. Teacher YouTube search is re-ranked by embeddings with no disclosure (`webapp/library.py:210`). That is search relevance on a query, so it was treated as outside "content feed".

**HON-10** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** Sort options: Author A–Z, Title A–Z, Longest, Shortest (`webapp/static/reader.html:871-873`).
- **Notes:** None.

**HON-11** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Generated replies are headed with a job title: `who.textContent=role==="user"?"You":personaName(persona)` (`webapp/static/index.html:646`), giving Professor, Historian, Aide or Researcher (`webapp/static/index.html:470`). The composer note (`webapp/static/index.html:373`) never says the answer is machine-generated. A search of the static pages finds no "AI", "language model" or "generated by". Generated student course materials (`docs/John_Pipeline.md:71`) are served at `/course` with no label.
- **Notes:** `ABOUT_EXEGETICA` tells the model what it is, and `webapp/app.py:150` tells it not to volunteer that. The draft position statement says "AI Must Never Be the Teacher" (`docs/position-statement-christian-school.md:33`), while the label reads Professor to students as young as 11.

**HON-12** 1 pt
- **Result:** N/A (1)
- **Confidence:** Medium
- **Evidence:** No pricing exists.
- **Notes:** Same KDP condition as HON-06.

#### 3C. Business Model Transparency

**HON-13** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** No statement of how Exegetica is paid for on any page. The closest text is a book colophon, "Free to read; never for sale." (`webapp/static/reader.html:1695`), which covers the Reading Room and names no funding. Exegetica has no marketing site, and live hilowstudio.dev `/about`, `/work`, `/philosophy`, `/contact`, `/privacy` and `/changelog` do not mention it.
- **Notes:** `ABOUT_EXEGETICA` states the maker on request and does not state funding.

**HON-14** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Free product, no funding explanation anywhere in the app.
- **Notes:** None.

**HON-15** 2 pts
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** No paywall exists in the code audited.
- **Notes:** See questionnaire.

**HON-16** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No terms of service exist. Live `/terms` and `/tos` return 404.
- **Notes:** None.

---

### Domain 04: Departure

#### 4A. Session Closure

**DEP-01** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No `beforeunload` handler in `webapp/`. Sign out redirects immediately (`webapp/auth.py:142-144`).
- **Notes:** None.

**DEP-02** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:**
  - Studies persist only after the reply ends (`webapp/static/index.html:708,713`), so closing mid-reply loses the turn, including the person's own question.
  - Composer drafts are never saved (`webapp/static/index.html:370`).
  - Generator output is never saved; localStorage on that page holds only the theme (`webapp/static/generate.html:241`).
  - Storage and save failures are swallowed silently (`webapp/static/index.html:545`, `:540`; `webapp/static/memory.html:343`).
  - A failed `GET /api/chats` at boot leaves an empty list (`webapp/static/index.html:733-741`), and the next save replaces the whole account blob (`webapp/store.py:73-83`).
  - A failed `GET /api/memory` is treated as an empty account (`webapp/static/memory.html:371`), which re-seeds and immediately PUTs (`webapp/static/memory.html:383`) with no user action, replacing that person's verses and progress.
- **Notes:** The two overwrite paths come from reading the code. They were not triggered.

**DEP-03** 1 pt
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** No mail path in code. `docs/go-to-market-plan.md:149` plans an email service for Send to Kindle.
- **Notes:** See questionnaire.

**DEP-04** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** Sign out redirects with no survey or promotion (`webapp/auth.py:142-144`).
- **Notes:** None.

#### 4B. Account Offboarding

**DEP-05** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** No subscriptions exist.
- **Notes:** None.

**DEP-06** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** No paid data exists.
- **Notes:** None.

**DEP-07** Must-Pass
- **Result:** N/A (PASS)
- **Confidence:** High
- **Evidence:** No cancellation exists.
- **Notes:** None.

**DEP-08** 2 pts
- **Result:** N/A (2)
- **Confidence:** Medium
- **Evidence:** No shared or team feature in code. `classes` and `enrollments` tables exist (`scripts/schema.sql:19,27`) with zero code references.
- **Notes:** Flagged. If the tables reflect a live plan, N/A no longer holds. `teacher_id` cascades on delete (`scripts/schema.sql:21`), so a departing teacher would erase a class.

#### 4C. Graceful Degradation

**DEP-09** Must-Pass
- **Result:** FAIL
- **Confidence:** Medium
- **Evidence:** No statement of the internet requirement in any page, and no offline mode (see DEP-10). The composer note (`webapp/static/index.html:373`) and sign-in prompt (`webapp/static/settings.js:182`) omit it. No marketing site exists to carry it.
- **Notes:** Flagged. A site reached by URL makes the requirement evident, and a reasonable auditor could waive this. The pass condition is literal: disclosed, or works offline.

**DEP-10** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No service worker, no manifest, no offline caching (live `/sw.js` and `/manifest.json` return 404).
- **Notes:** None.

**DEP-11** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No terms of service and no shutdown plan.
- **Notes:** None.

**DEP-12** 2 pts
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** All users receive each deploy with no choice, as with any hosted site. Legacy persona ids are preserved for saved chats (`webapp/static/index.html:460`).
- **Notes:** See questionnaire.

---

### Domain 05: Respect

#### 5A. Temporal Respect

**RES-01** 3 pts
- **Result:** N/A (3)
- **Confidence:** Medium
- **Evidence:** No notifications, scheduled sync or client background work exists. Sync runs only on user actions (`webapp/static/index.html:537`).
- **Notes:** The criterion lists no explicit N/A condition. Applied because every governed activity is absent.

**RES-02** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No notifications are sent.
- **Notes:** None.

**RES-03** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No time-based urgency copy found in pages or Python.
- **Notes:** None.

**RES-04** 1 pt
- **Result:** N/A (1)
- **Confidence:** High
- **Evidence:** No recurring actions exist.
- **Notes:** None.

**RES-05** 1 pt
- **Result:** N/A (1)
- **Confidence:** High
- **Evidence:** No milestone notifications exist.
- **Notes:** None.

#### 5B. Contextual Intelligence

**RES-06** Must-Pass
- **Result:** PASS
- **Confidence:** High
- **Evidence:** The microphone is the only sensor used. `recognition.start()` runs only inside `toggleMic` (`webapp/static/memory.html:983-986`), from a tap. Permission denial leaves a manual path (`webapp/static/memory.html:946-947`). No camera, location or contacts use.
- **Notes:** None.

**RES-07** Must-Pass
- **Result:** PASS
- **Confidence:** Medium
- **Evidence:** Microphone maps to the recitation steps. The transcript stays in page memory for comparison and display (`webapp/static/memory.html:789-792`).
- **Notes:** In Chrome, Web Speech recognition sends audio to a vendor speech service. Nothing in the app says so. That gap is scored under GOV-04.

**RES-08** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No notifications or background activity to adjust.
- **Notes:** None.

**RES-09** 2 pts
- **Result:** N/A (2)
- **Confidence:** High
- **Evidence:** No location use.
- **Notes:** None.

**RES-10** 1 pt
- **Result:** PASS (1)
- **Confidence:** High
- **Evidence:** The only permission prompt follows a tap on the microphone (`webapp/static/memory.html:986`). Nothing prompts at load.
- **Notes:** None.

#### 5C. Resource Respect

**RES-11** Must-Pass
- **Result:** PASS
- **Confidence:** High
- **Evidence:** No WebAssembly, mining or distributed compute in `webapp/static/` or `pyproject.toml`. Idle Chromium measurement below shows no activity.
- **Notes:** None.

**RES-12** 2 pts
- **Result:** PASS (2)
- **Confidence:** Medium
- **Evidence:** Measured in Chromium over 20 idle seconds: `/` used 0.001s of task time with 0 requests and a 1.4MB heap; `/read` used 0.002s with 0 requests and a 9.2MB heap.
- **Notes:** Each Reading Room visit loads the whole catalog (`webapp/static/reader.html:1457`): 4.67MB raw, 1.16MB compressed. That is a foreground cost, noted for the auditor. Measured on desktop, no battery test.

**RES-13** 2 pts
- **Result:** PASS (2)
- **Confidence:** High
- **Evidence:** No wake lock, WebSocket or background fetch. The event stream exists only during a reply. Zero requests during the idle window.
- **Notes:** The keep-warm job runs on GitHub (`.github/workflows/keep-warm.yml`) and touches no user device.

**RES-14** 1 pt
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** Nothing documents browser storage use. Studies accumulate in localStorage, including capped tool output, with no storage readout.
- **Notes:** Flagged. There is no install to size. Storage use exists and is undocumented, so the criterion was applied instead of N/A.

---

### Domain 06: Durability

#### 6A. Accessibility

**DUR-01** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:**
  - axe (WCAG 2.1 A and AA): `/` 3 contrast failures in each theme; `/memory` 16 critical `button-name` failures plus 9 contrast; `/read` 36 light and 33 dark contrast; `/corpus` 188 light and 157 dark contrast.
  - White on accent, used by Send and active toggles, measures 4.29:1 in light and 2.79:1 in dark (`webapp/static/index.html:19,99,180`). Normal text needs 4.5:1.
  - The composer note, the chat's only reliability warning, is 11.5px `--ink-faint` (`webapp/static/index.html:182`), computed at 2.90:1 in light.
  - The composer has a placeholder and no label (`webapp/static/index.html:370`).
  - At 320px wide `#p-researcher` is clipped, reaching 346px (WCAG 1.4.10).
- **Notes:** axe could not rate text over the garden background, so token ratios fill that gap. Teacher pages were not run through axe. `webapp/static/generate.html:282` shows labels with no `for` association.

**DUR-02** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** Measured at 375px: `/` 17 of 21 visible controls under 44px, including toggles at 26px high (`webapp/static/index.html:98`), the rail at 40px (`webapp/static/index.html:243`) and delete at 19x19px (`webapp/static/index.html:86`). `/memory` 16 of 22. `/read` 35 of 41. Desktop: `.chat-item` is a plain div with a click handler (`webapp/static/index.html:556,561`), and `.del` takes focus at opacity 0 (`webapp/static/index.html:86`), so focus is invisible.
- **Notes:** None.

**DUR-03** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** A 45-step Tab walk on `/` reached the delete button and never the study itself (`tabindex` and `role` both null), so a keyboard user can delete a study and cannot open one. On `/memory`, 16 verse rows had 0 focusable, and selecting a row (`webapp/static/memory.html:559,601`) is the route to Practice.
- **Notes:** None.

**DUR-04** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No `aria-live` or `role="status"` in `webapp/static/index.html`, so streamed replies are not announced. The crisis panel opens from a server event (`webapp/static/index.html:698`) without moving focus (`webapp/static/index.html:497`); at runtime focus stayed on a background button. Settings also leaves focus behind (`webapp/static/settings.js:120`). 16 kebab buttons have no name (`webapp/static/memory.html:563`).
- **Notes:** Code and axe review only. No screen reader session was run.

**DUR-05** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Tool result status is a colored 7px dot with no text or icon: `.tool .ic` and `.tool.error .ic` (`webapp/static/index.html:161,164`). A failed tool looks like a finished one in grayscale.
- **Notes:** Fail indicator: status conveyed only by a color dot.

**DUR-06** 1 pt
- **Result:** PASS (1)
- **Confidence:** Medium
- **Evidence:** At 640x400 (1280x800 at 200%) `/`, `/memory`, `/read` and `/course` showed no horizontal page overflow. Off-screen controls were the closed drawer button and the swipeable filter strip (`webapp/static/reader.html:341`).
- **Notes:** The chat thread pane shrinks to 105px tall at that size and stays scrollable. Chromium emulation only.

#### 6B. Standards & Interoperability

**DUR-07** Must-Pass
- **Result:** PASS
- **Confidence:** Medium
- **Evidence:** No plugins and no "best viewed in" copy. Web Speech is feature-detected (`webapp/static/memory.html:784`), and unsupported browsers keep a manual path (`webapp/static/memory.html:946-947`).
- **Notes:** Flagged. The kit asks for two browsers. Only Chromium was available, so Firefox and Safari need a manual check.

**DUR-08** 2 pts
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** OPDS is planned and unbuilt (`docs/go-to-market-plan.md:97,151`; live `/opds` returns 404). MCP is used internally; live `/mcp` returns 404 and `webapp/README.md:18` confirms no public MCP URL. The repository is private.
- **Notes:** Flagged. Assisted criterion. The Generator `.md` download is an open format and offers no protocol.

**DUR-09** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No export format exists to document.
- **Notes:** None.

#### 6C. Longevity

**DUR-10** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** Live `/changelog` returns 404. The GitHub repository returns 404 to anonymous visitors. The studio changelog covers hilowstudio.dev only and never mentions Exegetica.
- **Notes:** None.

**DUR-11** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No support, security update or end-of-life statement found. Live `/support` and `/security` return 404.
- **Notes:** None.

**DUR-12** 1 pt
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** No stated system requirements, which is a listed fail indicator.
- **Notes:** Flagged. The code has no OS dependency and likely runs widely. The kit's rule fails any present indicator.

---

### Domain 07: Governance

#### 7A. Privacy & Legal Clarity

**GOV-01** Must-Pass
- **Result:** FAIL
- **Confidence:** High
- **Evidence:** No privacy route in `webapp/app.py:921-993`. Live `/privacy` and `/privacy-policy` return 404. No page links to one. The hilowstudio.dev privacy policy does not mention Exegetica.
- **Notes:** Users include minors whose conversations go to a model provider. `webapp/app.py:155-157` states that only when asked, and the block is not deployed.

**GOV-02** 3 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No policy, so no summary.
- **Notes:** None.

**GOV-03** 2 pts
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** No policy exists to version.
- **Notes:** See questionnaire.

**GOV-04** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No disclosure of any of these, found in code: Anthropic, OpenAI, xAI and Google as model providers (`webapp/providers.py:330`); Google OAuth (`webapp/auth.py:40`); Google Fonts (`webapp/static/index.html:13`); ESV API (`webapp/memory.py:24-25`); Neon (`webapp/db.py:2`); Fly.io (`fly.toml`); Cloudflare R2 and Inngest (`pyproject.toml`); the browser speech service (RES-07).
- **Notes:** None.

#### 7B. User Communication

**GOV-05** 2 pts
- **Result:** FAIL (0)
- **Confidence:** Medium
- **Evidence:** No feedback link, form or address on any page. The hilowstudio.dev contact form exists, but the product does not name the studio and the studio site does not name the product.
- **Notes:** Flagged. A single link would change this result.

**GOV-06** 2 pts
- **Result:** FAIL (0)
- **Confidence:** High
- **Evidence:** No help pages (live `/help`, `/docs`, `/faq` return 404). `/corpus` inventories sources and teaches no tasks. `webapp/README.md` is developer documentation.
- **Notes:** None.

**GOV-07** 1 pt
- **Result:** Pending Attestation (not counted)
- **Confidence:** Low
- **Evidence:** No stated response time found.
- **Notes:** See questionnaire.

#### 7C. Ethical Commitments

**GOV-08** 2 pts
- **Result:** PASS (2)
- **Confidence:** Medium
- **Evidence:** Live hilowstudio.dev `/about` (source `C:\Users\adam\hi-low\components\about\about-honesty.tsx:24`): "Hi Low Studio is bootstrapped. It is funded entirely by consulting services and product sales." No investors, no ads, no data sales.
- **Notes:** Flagged. Passed at company level, as the kit instructs. The disclosure never names Exegetica, and the brief says the creator pays model bills personally, which the published sentence does not describe.

**GOV-09** 2 pts
- **Result:** PASS (2)
- **Confidence:** Medium
- **Evidence:** Live hilowstudio.dev `/philosophy`, in the studio repository since 2026-04-08, and the commitments in `C:\Users\adam\hi-low\components\how-we-build.tsx` from 2026-03-28.
- **Notes:** Flagged. Written by the framework's author, so its independence from QSF is limited. `docs/position-statement-christian-school.md:3` was not counted: it is an untracked draft created during this audit. The studio commitment "You own your records and can always take your digital life with you" (`how-we-build.tsx:24`) is unmet by this product (DAT-01, DAT-14).

---

## Attestation Questionnaire

*For criteria with automationLevel: "manual". To be completed by the product team.*

| # | Criterion | Question | Response |
|---|---|---|---|
| 1 | DAT-13 | Is sensitive user data encrypted at rest, including `chat_state` and `memory_state`? What algorithm and key length? What counts as sensitive? How are keys managed? | [Pending] |
| 2 | DAT-16 | What is the backup and point-in-time retention on Neon and the Fly volume? What is the maximum number of days from a deletion request to full purge? Is the purge automated? | [Pending] |
| 3 | DEP-03 | Does the application send re-engagement email? What is the minimum delay after last activity? Can users turn it off? | [Pending] |
| 4 | DEP-12 | Have any updates in the last 12 months removed features or substantially changed the interface? Were users given a choice or a migration period? | [Pending] |
| 5 | GOV-03 | How will users be told of material policy changes? Before the effective date? With a summary of changes? | [Pending] |
| 6 | GOV-07 | What is the stated support response time, where is it published, and what share of requests meet it? | [Pending] |
| 7 | HON-15 | Have any previously free features been moved behind a paywall in the last 24 months? If yes, was notice and export offered? | [Pending] |

*False attestation voids certification. Answers are cross-referenced against observable evidence.*

Points at stake: DAT-13 3, DAT-16 2, DEP-03 1, DEP-12 2, GOV-03 2, GOV-07 1, HON-15 2. Total 13.

---

## Attestation Cross-Reference

The questionnaire is unanswered, so this table tests the audit brief and the product's own claims.

| Attestation | Observable Evidence | Consistent? | Notes |
|---|---|---|---|
| Chat works without an account | `webapp/app.py:357` has no user check | Yes | None |
| Google sign-in is optional | `webapp/auth.py:2`; Settings offers it | Yes | None |
| Anonymous studies stay in the browser, signed-in studies go to Neon | `webapp/static/index.html:544-545`; `webapp/store.py:73` | Yes | The UI says otherwise for signed-in users (`webapp/static/index.html:553`) |
| No subscriptions | No billing code | Yes | None |
| Non-commercial and free | Live product charges nothing | Partly | `docs/go-to-market-plan.md:151,186` lists KDP with a $0.99 minimum, against the colophon "never for sale" (`webapp/static/reader.html:1695`) |
| Creator pays the model bills personally | Not observable | Unable to verify | The studio's public sentence names consulting and product sales |
| "No ads, analytics, notifications, streaks, or gamification" (`webapp/app.py:159-161`) | Ads, analytics, notifications, streaks: none found | Yes, with one flag | Gamification is the open judgment at ATT-11 |
| "Exegetica has no accounts and stores nothing" (`webapp/safety.py:4`) | Accounts and Neon storage exist | **No** | Internal docstring, stale. Same at `webapp/memory.py:5` |

---

## Flagged for Auditor Review

Every `assisted` criterion needs auditor confirmation under the kit. This table lists the ones with a live judgment call.

| Criterion | Finding | Confidence | Reason for Flag |
|---|---|---|---|
| ATT-11 | PASS | Medium | "Mastered" state, count and 🎉 toast could read as an achievement display |
| ATT-20 | PASS | Medium | Two solid accent buttons when the studies panel is open |
| ATT-22 | PASS | Medium | Brand accent is a muted red on primary actions |
| DAT-06 | FAIL | Medium | Teacher book upload could satisfy a literal reading |
| DAT-07 | FAIL | Medium | Proportionality of `picture` and Google Fonts |
| DAT-08 | FAIL | Medium | Fails only on the missing policy confirmation |
| HON-01 | PASS | Medium | "I need practice 😓" |
| HON-03 | FAIL | Medium | False storage copy is small in reach; "every answer" was not observed failing |
| HON-06, HON-12 | N/A | Medium | KDP remains open in the go-to-market plan |
| HON-09 | N/A | Medium | Undisclosed embedding re-rank in teacher search |
| DEP-08 | N/A | Medium | Dormant `classes` and `enrollments` tables |
| DEP-09 | FAIL | Medium | Evident for a website, undisclosed by the letter |
| RES-14 | FAIL | Medium | No install exists; storage is undocumented |
| DUR-07 | PASS | Medium | Firefox and Safari untested |
| DUR-08 | FAIL | Medium | Choice of which protocols are relevant |
| DUR-12 | FAIL | Medium | Fails on a documentation indicator alone |
| GOV-05 | FAIL | Medium | Studio contact form exists, unconnected to the product |
| GOV-08 | PASS | Medium | Company-level disclosure that never names the product |
| GOV-09 | PASS | Medium | Same author as the framework |

---

## Recommendations

### Must-Fix (Blocks Certification)

These five changes cover all 13 failed gates.

1. **Publish a privacy policy, plain terms and an About page, and link them from every page.** State the funding, the internet requirement, the outside providers and a contact address. Clears GOV-01, HON-13, DEP-09 and DAT-08. Adds HON-14 (3), GOV-02 (3), HON-16 (2), DEP-11 (2), GOV-04 (2), DUR-11 (2), GOV-05 (2): 16 points.
2. **Add Download my data and Delete my account to Settings.** Export every per-user table as documented JSON, plus a localStorage export for anonymous users. `on delete cascade` already exists, so the database side is one route and one confirm. Clears DAT-01, DAT-02, DAT-03 and HON-02. Adds DAT-14 (3), DAT-05 (2), DUR-09 (2): 7 points.
3. **Run an accessibility pass.** Darken `--ink-faint` and the accent behind white text, make `.chat-item` and `.vrow` real buttons, name the kebab buttons, add a live region, move focus into the crisis panel, raise targets to 44px, and add text to tool status. Clears DUR-01 and DUR-02. Adds DUR-03 (3), DUR-04 (2), DUR-05 (2): 7 points.
4. **Remove the IntersectionObserver and use the existing Show more button,** which is already wired (`webapp/static/reader.html:1308`). Clears ATT-09. Same pass: extend reduced motion to the reader (ATT-19, 2) and tighten `.prose` to about 60ch (ATT-23, 1): 3 points.
5. **Say what the thing is and keep less.** Label replies as AI-generated, fix the "in this browser only" copy, soften "every answer", drop `picture`, and self-host fonts. Clears HON-03 and DAT-07. Adds HON-11 (2): 2 points.

If all five land as scoped, the projection is about 104 of 143 with every gate and domain minimum met, which reaches the QSF Certified line before attestation. Each change still needs re-audit.

### High Priority (High-Value Points)

1. **DEP-10 (3 pts):** service worker that caches the shell, opened chapters and saved studies. Medium effort.
2. **DAT-09 (3 pts):** a My data view in Settings. Low effort once export exists.
3. **DAT-15 (2 pts):** a deactivate option beside delete, with plain consequences. Low effort.
4. **DEP-02 (2 pts):** save the question before streaming, save drafts, surface save failures, and stop treating a failed GET as an empty account. Fix the Scripture Memory path first, since it overwrites without user action. Medium effort.
5. **ATT-14 (2 pts):** a quiet session length line in the Studies panel. Low effort.

### Quick Wins (Low Effort)

1. **DUR-10:** a public changelog page.
2. **GOV-06:** a short how-to page for Chat, Memory and Reading Room.
3. **DAT-12:** state retention periods, then add the purge job that makes them true.
4. **RES-14, DUR-12:** one line each in the About page.
5. **ATT-11, HON-01:** remove the 🎉 and the 😓.

### Outside the framework

QSF does not score these. They came up during evidence collection.

- `/api/chat`, `/api/generate`, `/api/generate/book` and `/api/revise` (`webapp/app.py:985,991-993`) have no auth or rate limit and fall through to the server's Anthropic key (`webapp/providers.py:330`), so anyone with the URL can spend the creator's money. Live `/generate` and `/library` return 200 to anonymous visitors.
- `?view=teacher` selects the teacher view with no authentication (`webapp/app.py:460-461`). `webapp/course_views.py:7-9` says it must sit behind real authentication before hosting for students. It is now hosted.
- The live site sends no HSTS or Content-Security-Policy header.

### Notes on the kit

- `qsf-criteria.json` nests all 104 criteria under one domain object, and its declared `availablePoints` of 26 for Attention disagrees with the computed 27. Domain totals here were computed by ID prefix and match the template.
- `qsf.md:6` says 134 points. The criteria, rules and template all say 143.
- `qsf.md:195` still uses the tier names Silver and Gold.

---

*Audit conducted using the Quiet Standards Framework v1.0, published by Hi Low Studio LLC.*
*Full specification: https://hilowstudio.dev/standards/spec*
