# 0014: Deploys go through one gate, and a changed student prompt needs the maker's probe first

Recorded 2026-11-03 from the harness proposal, Layer 5 item 7. It replaces the proposal's ladder run, by the maker's choice: he probes the bot himself.

**Decision.** `scripts/predeploy.py` deploys only with `--deploy`. Before that it refuses unless:

- the git tree is clean, untracked files included, because `fly deploy` ships the working tree;
- pytest passes;
- the Bible and History tool checks pass;
- both servers answer a stdio round trip through the app's own bridge;
- the student prompt has a probe record.

The voice lint is reported and does not block. After deploying, the gate checks the live site: tool counts match this tree, `/api/health` answers, and a signed-out request for a teacher answer key is refused.

A probe record is the maker's note that he probed this exact prompt and model (`--record-probe "what was probed"`), kept in `evals/probe-records.json`. The prompt hash covers both subjects' student prompts and the locked model, so any change to the floor, the briefs, doctrine, the safeguarding note, or the model needs a new record. `--no-probe-record` ships anyway, and the gate prints a warning.

**Why.** Today's floor was written without a model run, and every earlier deploy shipped whatever was in the folder.

**Enforced in.** `scripts/predeploy.py`. Fly's own health check stays on `/api/config`, so a restarting library never takes the Reading Room offline with it. The deep check, `/api/health`, runs every five minutes from keep-warm.

**Reverse when.** A CI pipeline replaces hand deploys. The proposal advises against one while the corpora live outside git.
