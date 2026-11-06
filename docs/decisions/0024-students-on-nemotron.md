# 0024: Students' replies come from Nemotron 3.5 Super on DeepInfra, and from GLM-5.3-Flash when Nemotron can't be reached

Decided by A. James Vega, 2026-11-06. Replaces the model and the no-fallback rule of docs/decisions/0004.

**Decision.**

- Every student chat runs on `nvidia/NVIDIA-Nemotron-3.5-Super-VL`, NVIDIA's open-weights model, on DeepInfra, with the server's DeepInfra key and reasoning effort at medium. The provider, model, and key a browser sends are still ignored for students, and Settings doesn't offer DeepInfra to teachers.
- When Nemotron can't be reached, the reply comes from `zai-org/GLM-5.3-Flash`, Z.ai's open-weights model, on the same host. "Can't be reached" means the run ended in an error before any text was shown: a host or connection error, a minute with no data from the host, or an empty reply after its one retry. The student sees one reply and no notice, and the metrics row names the model that answered. Once text has been shown, no other model takes over, and a refusal never passes to the fallback.
- Both models run on the OpenAI-compatible loop with the student limits (0008), narration held back (0019), and the library first (0020). Neither host reports a refusal, so a model's own decline reaches the student through the reply check like any other sentence. `REFUSAL_TEXT` stays for the Anthropic path.
- The crisis model check (0018) still runs on Claude Haiku for every student chat. A student's last three messages go to Anthropic for it, though Anthropic no longer writes the reply.
- Teachers keep Claude for chat and the Prep Room.

**Why.** The maker wants an open-weights model he can control and later fine-tune, one Christian parents can trust more than a large AI company's model, at a cost he can carry. In the bake-off of 2026-11-06 (six open models, 41 questions, blind review, `DIRECT_RUNS` in `evals/bakeoff/run.py`), Nemotron gave the plainest answers (4.54 of 5) and the most accurate (4.83), with the fewest "Christians differ" passages on settled points (1), at about half a cent an answer and a median of 22 seconds. DeepSeek V4.1 Flash ranked slightly higher overall, but it was much less plain, surveyed settled points five times, and took twice as long. GLM-5.3-Flash is the maker's choice for the fallback. In the same bake-off it once wrote a prayer for a student and once sent raw tool-call text, so it answers only while Nemotron is down. DeepInfra's terms of service (section 7(b), "Zero Data Retention") keep no prompt or reply beyond the time needed to answer and train no model on them.

**Enforced in.** `STUDENT_PROVIDER`, `STUDENT_MODEL`, `STUDENT_FALLBACK_MODEL`, and `STUDENT_CHAT` in `webapp/policy.py`. The `deepinfra` entry in `PROVIDERS`, `run`, and `_run_openai` in `webapp/providers.py`. `chat()` in `webapp/app.py`, where the model check now runs on every student chat. The probe record in `scripts/predeploy.py` names both models. Covered by `tests/test_policy_and_loop.py` and `tests/test_chat_route.py`.

**Reverse when.** The maker changes the student model or its fallback. Either one serves students only after he has probed it himself (0004).
