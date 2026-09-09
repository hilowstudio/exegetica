# Theologian framing consult (per unit)

How we frame each John unit going forward. The Theologian persona is the theological
advisor. The builder (Claude) holds the whole task and has the final call: the builder
gives the Theologian full context, reads its brief, checks it against the master plan,
reconciles what doesn't fit, and only then generates. The Theologian advises. It does
not decide, and its brief is never passed straight through to generation.

## 1. The consult (what the Theologian gets)

Spawn a Theologian subagent (opus) and have it:
- Adopt `src/studybible_mcp/prompts/theologian.md` fully, and use the study-bible MCP
  tools (word study, cross-references, study notes, ESV via get_passage) to ground.
- Read the course design: `docs/John_Build_Spec.md` and `docs/John_Voice_Guide.md`.
- Read the prior units' framing in `docs/john-framing/U*.md` for continuity. Build on
  what earlier units established (the signs, the "I am" sayings, the Baptist's witness,
  the memory-verse arc); do not re-explain or contradict it.
- Receive, for THIS unit: the passage, the calendar (lessons, day types, half-days,
  checkpoints), the memory-verse status (plants a verse, or review-only), and the
  paired sermon text if one exists. Where a sermon exists, build on Adam's own
  preaching rather than cut against it.

Standing questions (adapt to the passage):
1. Christotelic center in one or two sentences; where it lands on Christ.
2. The contested exegetical points for this passage, with a ruling on each (not a survey).
3. The christological / covenantal connections worth teaching (types, OT echoes).
4. How to reach the three-tier room (searching / churched-passive / disciple) on this text.
5. How to teach the memory verse freshly, if the unit plants one.
6. Pitfalls to avoid with teenagers on this passage.
7. Anything to emphasize that wasn't asked.
8. A recommended split across the unit's lessons, on scene or thought seams, each lesson
   landing on Christ.

Hard rule for the brief: no em dashes, no contrastive negation, plain positives.

## 2. The vet (what the builder checks before using it)

Before writing `docs/john-framing/<unit>.md` and generating, reconcile the Theologian's
brief against the master context:
- **Calendar:** does the split match the lesson count and day types? Do half-days and
  checkpoints fit? (Recut the split to fit the calendar, not the reverse.)
- **Build Spec:** consistent with the locked design (three-tier, grace-first, ESV, the
  5-move template, the assessment model)?
- **Continuity:** consistent with how prior units framed shared threads? No contradiction
  of what students have already been taught.
- **Memory:** matches the 16-verse plan (plant vs review-only)?
- **Sermon:** where a sermon exists, does the brief build on it, not against it?
- **Voice:** free of machine tells; will translate cleanly to the teenage register.
- **Theology:** sound and consistent with the Build Spec's positions; flag anything worth
  pushing back on rather than adopting silently.

Reconcile, edit the framing file to the vetted version, then generate and review the
output against the brief.

## 3. Grain

Frame per unit, with the brief speaking to each lesson (as U4 did). If one lesson is
especially hard, run a focused follow-up consult on that lesson alone. Do not consult
per lesson by default; the unit-level brief that lands each lesson is the right grain.
