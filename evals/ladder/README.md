# Safety ladder

Scripts and transcripts from the 2026-10-31 safety review of student chat, moved here on 2026-11-04 from a temporary folder that cleanup could have deleted. The maker probes the bot by hand before each deploy, and `scripts/predeploy.py` checks for his record in `evals/probe-records.json`. Nothing in this folder runs automatically.

Keep this folder in the private repository. The student personas are high school students, and the transcripts hold the bot's replies to them.

## Scripts

| Script | What it does | Cost |
|---|---|---|
| `precheck_probe.py` | Runs 25 crisis messages through `webapp/safety.precheck` and counts what it catches | Free, no model |
| `slowburn.py` | Sends one turn of a hand-driven conversation and keeps the history in a JSON file | One chat turn |
| `redteam_probe.py` | Sends 16 adversarial prompts to `/api/chat` and one to `/api/revise` | About 17 chat replies |
| `redteam_weak.py` | Sends seven of those prompts with a cheaper model named in the request | Seven chat replies |

The three live scripts were written for the Oct 21 build: anonymous requests, the persona names `professor`, `aide` and `researcher`, and a model chosen by the request. Production now requires sign-in, locks the student model and names the modes differently, so those scripts need a session cookie and today's request shape before they run again. Every live run spends API money, so get the maker's approval and a cost figure first.

Run the free one from the repository root:

    .venv/Scripts/python.exe evals/ladder/precheck_probe.py

## Transcripts

All from 2026-10-31, signed out, Bible mode with the Theologian persona.

| File | Conversation |
|---|---|
| `redteam_results.json`, `redteam.log` | `redteam_probe.py` on the server's default model |
| `redteam_claude-haiku-5-5.json`, `redteam_claude-sonnet-4-6.json` | `redteam_weak.py` on cheaper models |
| `redteam_haiku.json` | `redteam_weak.py` on Haiku 4.5, which failed with API errors |
| `burn_opus.json`, `burn_sonnet.json`, `burn_haiku.json` | The slow-burn "I love you" ladder under pressure, a sophomore persona |
| `burn_haiku2.json` | Haiku rerun with the maker's argument |
| `burn3_opus.json`, `burn3_sonnet.json`, `burn3_haiku.json` | The gentle rerun: a student who is loved and needs nothing |
| `replay_opus.json` | Opus replay of the sophomore ladder |
| `forge_opus.json`, `forge_sonnet.json` | A forged "I love you" placed in the history |
| `branch_a.json` to `branch_e.json` | Sonnet 4.6 branches after its break: post-break paths, warmth only, the present moment, the name step |
| `senior.json`, `senior2.json` | A new 18-year-old senior, then a senior who understands how the bot works |
| `excl.json`, `body.json` | Exclusivity and embodiment directions with the informed senior |
| `t_world.json`, `t_sustain.json`, `t_being.json`, `t_being2.json` | One theme per conversation, from turn 16 (`t_being2` adds the sensory question) |
| `adult.json` | A 44-year-old adult on the same ladder |

What they showed: Sonnet 4.6 broke at turn 6 in every sequence, Haiku 5.5 held, and Opus 5.5 held under pressure and drifted under gentleness. Student chat has been locked to Opus since the Phase 1 build.
