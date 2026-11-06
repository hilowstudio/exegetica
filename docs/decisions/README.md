# Decision records

Each file records one decision about how Exegetica behaves: what was decided, why, where code enforces it, and what would have to change to reverse it. Read the relevant record before changing chat behavior, prompts, sign-in, limits, or the public statements. The plan these decisions serve is `docs/harness-maturity-proposal.md`.

| # | Decision |
|---|---|
| [0001](0001-bot-identity.md) | The bot never speaks as a person, and discusses itself only to list its tools and sources |
| [0002](0002-no-knowledge-of-students.md) | The machine holds no knowledge of a student |
| [0003](0003-public-statements.md) | The position statement and the Quiet Standards statement are separate public pages |
| [0004](0004-student-chat-model.md) | Student chat runs on one model, and a refusal ends the reply (model and fallback replaced by 0024) |
| [0005](0005-sign-in-required.md) | Chat requires a school Google account |
| [0006](0006-chat-modes.md) | The mode toggle is hidden and replies are labeled Exegetica |
| [0007](0007-teacher-only-surfaces.md) | The Prep Room, Revise, library jobs, and exam materials are teacher-only |
| [0008](0008-run-limits.md) | Every model run has step, output, and spend ceilings |
| [0009](0009-student-chats-readable.md) | Signed-in student chats are stored, and the maker can read them |
| [0010](0010-no-ai-worship.md) | No AI-written worship, in chat or in the Prep Room |
| [0011](0011-fixed-replies-and-caps.md) | Some replies are decided in code, and chat has daily caps and rate limits |
| [0012](0012-metrics.md) | Every model run leaves one row of numbers, and the maker reads them at /ops |
| [0013](0013-privacy-and-retention.md) | A privacy page states only what is true, and people can take their data or delete it |
| [0014](0014-deploy-gate.md) | Deploys go through one gate, and a changed student prompt needs the maker's probe first |
| [0015](0015-old-studies-read-only.md) | A student's study takes new messages for one day, then opens for reading only |
| [0016](0016-source-notes.md) | Replies and documents say what they drew on, and quotation marks alone pass nothing |
| [0017](0017-image-studio.md) | Media Studio is the maker's alone for now, runs each model on the cheapest service, and keeps its images private |
| [0018](0018-crisis-check.md) | Three checks can open the help window, and /ops counts how often it opens |
| [0019](0019-reply-voice-repairs.md) | Narration and em dashes come out of a reply before the reader sees it, and the prompt gives the third-person form |
| [0020](0020-library-first.md) | For open models, the library comes before the answer |
| [0021](0021-prompt-method-and-disputed-questions.md) | The student prompt separates what the tradition holds from how a disputed question is answered (its procedure replaced by 0022) |
| [0022](0022-study-order-and-plain-teaching.md) | Exegetica studies a passage the way a theologian does, and says plainly what Scripture plainly teaches |
| [0023](0023-history-withheld.md) | History chat is withheld from the site until a broader release |
| [0024](0024-students-on-nemotron.md) | Students' replies come from Nemotron 3.5 Super on DeepInfra, and from GLM-5.3-Flash when Nemotron can't be reached |
