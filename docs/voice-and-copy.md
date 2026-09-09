# Voice Rules

Governs all user-facing text in this project: page copy, generated resources, and chat answers. Injected into the model via `src/studybible_mcp/prompts/voice.md`; companion to [design-guidance.md](design-guidance.md).

## Length
Verbosity is the primary tic: a second sentence restating the first, a needless qualifier, a recap. Completeness and concision hold together: every required point present, and no word a point didn't need.

Two passes:
1. **Cut.** Delete each sentence; if no fact or beat is lost, leave it gone. If a sentence is predictable from the one before, drop one.
2. **Compress.** Hold each surviving fact in fewer words.

Then confirm every required claim survived. If a cut drops one, find shorter phrasing; don't restore the padding.

## Absolute ban: contrastive negation
Denying one term to assert the next in parallel grammar ("not X, but Y"). The denied half is a straw man; a strong claim stands alone. True antithesis, both halves asserted and neither denied, is allowed.

## Figures to avoid
Isocolon/parison, ascending tricolon, anaphora, epistrophe, hyperbole/intensifier stacking, praeteritio, rhetorical questions (hypophora only), em dash, coined compound, compression close, untranslatable frame, semicolon accumulation, deflating turn.

## Lexical bans
- **Dead metaphor:** cutting-edge, game-changer, supercharge, unlock, at your fingertips, the power of, best-in-class, mission-critical, holistic, synergy, ecosystem, leverage, utilize, delve, enhance, transformative, pivotal, comprehensive, intricacies.
- **Vague nouns:** aspects, factors, elements, solutions, offerings, areas, touchpoints.
- **Summary closers:** "In conclusion", "Overall", "In summary". End on the last real line.
- **Theatre:** no fake scarcity, countdown, confirmshaming, or exclamation reflex. A real constraint stated once is fine.

## Salience markers and flattery
Stock phrases that mark importance without carrying any. Examples:
- **Structural metaphors:** load-bearing, heavy lifting, blast radius, smoking gun, footgun, belt-and-suspenders, ground truth.
- **Salience stamps:** that's real, that's not nothing, that matters, here's why it matters, sit with that, let it land, worth sitting with, resolves it cleanly.
- **Flattery openers:** "You're absolutely right", "good catch"/"sharp catch", "Great question".
- **Honesty framings:** "let me be honest", "honest take", "honestly?".
- **Others:** softened pushback ("I'll gently push back"), cliffhanger offers ("would you like me to continue?"), intensifier crutches ("genuinely", "truly", "deeply"), hedge-jargon ("unfalsifiable as stated", "canonical", "nuance").

**The rule is on the move, not the words.** Ban one metaphor and the writing pivots to the next; they are the same substitution of a vivid stand-in for a concrete claim. The list is examples, not a spec.

**Positive replacement.** When something matters, state what depends on it or what breaks without it, then stop. Correct directly, with no preface and no apology. Delete any sentence that only signals importance.

## Enforcement
`scripts/lint_voice.py` greps user-facing text for the unambiguous tics, em dashes, and contrastive negation. Run it in review or a pre-commit hook. It catches the listed tics and nothing subtler.
