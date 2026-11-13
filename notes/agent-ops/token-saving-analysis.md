---
name: token-saving-analysis
description: Where subscription quota goes, whether compressing via Haiku then handing to Opus saves, whether the caveman / ponytail plugins are worth installing, token-saving measures ranked by effect
status: active
updated: 2026-11-12
---

# Saving Claude quota: analysis and trade-offs

**Conclusion**: cost per turn ≈ the entire context carried in that turn × model unit price. The biggest waste is fixed overhead such as tool definitions, not chat content. Compressing via Haiku and then handing to Opus does save, provided Opus only makes short-lived calls; design discussions are not suitable for compress-and-hand-off. Neither caveman nor ponytail gets installed; only borrow ponytail's "ladder" rule for DeepSeek.

## Real bill (2026-11-12, one Opus main session)

- Pro plan; context about 200k tokens: tool definitions about 100k (MCP 60k + system tools 40k), chat 76k, system prompt 11k, skills 8k.
- Every sentence in the main conversation recomputes all 200k (caching is cheaper but still counts toward quota).
- How to check: `mcp__ccd_session_mgmt__get_usage` (quota percentage + context breakdown).

## Compressing via Haiku then handing to Opus

- The saving is twofold: routine back-and-forth is handled by Haiku at a low unit price; each new Opus session carries only a 10k-20k task description and ends after a few rounds, instead of carrying 200k of history. Compression is just the means.
- Failure modes:
  - Design discussions: compression loses subtle considerations, Opus gets it wrong or keeps coming back to ask, and each question costs another Opus call. **(2026-11-12, the user revised the decision: the main conversation only converses, and all engineering requests are compressed and handed to the supervisor; the problem of compression losing details in design discussions is pending the user's decision.)**
  - Haiku also carries 100k of tool definitions; with a small window it auto-compacts quickly and paraphrase quality drops (Haiku's window size not checked, pending real testing).
  - Back-and-forth paraphrasing distorts things: let Opus decide what it can decide, and list in one go the things that need the user's call.

## The two plugins

**caveman** (https://github.com/juliusbrussee/caveman): makes replies shorter + compresses logs/JSON/test output + auto-selects models (requires signup) + cloud tracking.
- Author's own measurements: most of the output savings came from one sentence, "answer more concisely"; `/caveman` only saved about 3% more (median), the rule itself adds about 1,160 input tokens per turn; session-wide input was 33% lower.
- Not very useful for us: the bulk of agent work is input; input compression is already covered by "paste only the last line of tests" and "hand long logs to DeepSeek to read".
- Risks: telemetry on by default; auto model selection sends the prompt and CLAUDE.md to its cloud; once installed, every session and subagent loads it.

**ponytail** (https://github.com/dietrichgebert/ponytail): makes agents write less code, not a dedicated token-saving tool. Before writing, go through the ladder: is it really needed → does the codebase already have it → can the standard library/platform do it → can an installed dependency do it → only then write the minimal implementation; risky logic gets a small test; the reply states what was skipped.
- Author's own measurements (Opus 5.5, 39 tasks × 5 runs): code -53%, output tokens -45%, cost -26%, higher test coverage.
- For us: the smaller the DeepSeek change, the less Opus has to read during review, which saves Claude quota. Do not install the plugin (it collects session data locally and has a status panel); just copy the ladder rule into `delegate-coding\coder-system.md`.

## Measures ranked by effect

1. Cut fixed overhead: turn off connectors like fxhoudini, computer-use, Chrome when not doing Houdini work (only the user can turn these off in the desktop app's input box + menu).
2. Keep sessions short and stitch them together with HANDOFF.
3. Expensive models only make short-lived calls; hand large files to cheap models to read and write summaries.
4. CLAUDE.md and resident skills should be as short as possible; they are carried every turn.
5. Concise replies: one sentence of prompting is enough, no plugin needed.
6. Compress input: paste only the last line of tests, hand long logs to DeepSeek.

Related: dispatch-architecture-v2 (archived on 2026-11-12 to `<HUB>\.trash\dispatch-consolidate-20261112\dispatch-architecture-v2.md.bak`).
