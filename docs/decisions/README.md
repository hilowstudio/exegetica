# Decision records

Each file records one decision about how Exegetica behaves: what was decided, why, where code enforces it, and what would have to change to reverse it. Read the relevant record before changing chat behavior, prompts, sign-in, limits, or the public statements. The plan these decisions serve is `docs/harness-maturity-proposal.md`.

| # | Decision |
|---|---|
| [0001](0001-bot-identity.md) | The bot is software, says so plainly, and never speaks as a person |
| [0002](0002-no-knowledge-of-students.md) | The machine holds no knowledge of a student |
| [0003](0003-public-statements.md) | The position statement and the Quiet Standards statement are separate public pages |
| [0004](0004-student-chat-model.md) | Student chat runs on one model, and a refusal ends the reply |
| [0005](0005-sign-in-required.md) | Chat requires a school Google account |
| [0006](0006-chat-modes.md) | The mode toggle is hidden and replies are labeled Exegetica |
| [0007](0007-teacher-only-surfaces.md) | Generator, Revise, library jobs, and exam materials are teacher-only |
| [0008](0008-run-limits.md) | Every model run has step, output, and spend ceilings |
| [0009](0009-student-chats-readable.md) | Signed-in student chats are stored, and the maker can read them |
| [0010](0010-no-ai-worship.md) | No AI-written worship, in chat or in the Generator |
| [0011](0011-fixed-replies-and-caps.md) | Some replies are decided in code, and chat has daily caps and rate limits |
| [0012](0012-metrics.md) | Every model run leaves one row of numbers, and the maker reads them at /ops |
| [0013](0013-privacy-and-retention.md) | A privacy page states only what is true, and people can take their data or delete it |
| [0014](0014-deploy-gate.md) | Deploys go through one gate, and a changed student prompt needs the maker's probe first |
| [0015](0015-old-studies-read-only.md) | A student's study takes new messages for one day, then opens for reading only |
| [0016](0016-source-notes.md) | Replies and documents say what they drew on, and quotation marks alone pass nothing |
| [0017](0017-image-studio.md) | Image Studio is the maker's alone for now, runs each model on the cheapest service, and keeps its images private |
