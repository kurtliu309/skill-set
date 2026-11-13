---
name: t6-grill-route-result
description: T6 grill route test: rounds, usage, paraphrase issues, and finalized points for T6b (Opus subagent) and T6c (DeepSeek Flash); scoring pending, no conclusion yet
status: draft
updated: 2026-11-12
---

# T6 grill route test conclusions

**Conclusion**: for now, do not judge which route is better. The rounds on the two sides are not symmetric (Opus 3 rounds, DeepSeek 6 rounds), and the user has not scored them yet. This records only the facts and the unfinished scoring. The requirement used for the questions is the simplified quota display (`quota-script-plan.md`).

## Data

| Item | T6b (Opus subagent) | T6c (DeepSeek Flash) |
|---|---|---|
| Rounds | 3 rounds | 6 rounds |
| Questions | 7 questions (4 in round 1, 3 in round 2), round 3 finalized | answered 16 questions (4 each in rounds 1-4); the 4 in round 5 were rejected because the user accidentally triggered a popup, so they went unanswered, and it finalized directly afterwards |
| tokens | about 49k total for the subagent | about 19k input + about 22k output (not counted against Claude quota) |
| Duration | about 46 seconds | about 143 seconds |
| Final test checklist items | 9 | 13 |
| Plan quality | pending the user's score (1-5) | pending the user's score (1-5) |

Main conversation quota (`get_usage`, integer percentages): 3% at the start of the 5-hour window, 4% after T6b, 5% after T6c; weekly quota 14% throughout. The return values are integers only, so changes below 1% are not visible.

## Paraphrasing

- When Haiku paraphrased T6c round 1 question 3, the title was written wrong, adding "what causes all the quota limit tests to be blocked?"; the options were unchanged.
- The rest was largely paraphrased as-is.

## Why the two sides are not symmetric

- DeepSeek's prompt had no round limit and no clear stopping criterion. It interpreted "at most 4" as having to ask all 4, and treated every gap it found as a must-ask.
- So the two sides' "question quality" and "usage" cannot be compared directly.

## T6b finalized points (Opus)

1. First-line format: `Tier: <stable|thrifty> · Claude 5h N% (HH:MM reset) · Week N%`.
2. Hook: in the global `~/.claude/settings.json` under `PreToolUse`, matching `ExitPlanMode`, effective for all projects; the script is `<HUB>\tools\plan_header_hook.py`, standard library only.
3. Wrong first-line format: exit 2, stderr states the required format.
4. `get_usage` return not found in the transcript: check the format only, then allow, without distinguishing the desktop app from the CLI.
5. Found but older than 10 minutes: bounce, prompting a new `get_usage` call.
6. The two percentages must exactly match the return; if not, bounce, with the raw numbers in stderr.
7. The reset time is only checked for HH:MM format, not the value.
8. The tier is computed strictly from the percentages (5h ≥80% or weekly ≥70% means thrifty), manual override unsupported; a mismatch is bounced.
9. After 3 consecutive bounces in the same conversation, allow, with a warning added to stderr. The "3 times" was chosen by the user in the T6b round 2 popup (option "allow after 3 consecutive bounces in the same conversation"). The counting method (first count from the transcript, and if that fails use a counter file named by `session_id` in the temp directory) was added by Opus at finalization and never confirmed by the user.
10. The hook erroring itself: exit 0 and allow, leaving a warning in stderr.
11. Tests must cover: wrong format, `get_usage` not found (check the format only, then allow), older than 10 minutes, percentage mismatch, wrong tier computation, wrong HH:MM format, allow after 3 consecutive bounces, allow after an internal hook error, normal pass — 9 in total.
12. Test order, implementation steps, CLI sync, and cleaning up the old status bar all follow the original plan.

## DeepSeek finalized points

**One point the user never confirmed**: "weekly quota present in the record but omitted in the line → exit 2" (see "missing-field comparison" and test checklist 2 below). DeepSeek derived this itself; it was not the user's answer.

**Bounce counts cannot be compared directly**: on the Opus side the user chose allow after 3 times; on the DeepSeek side the user chose allow after 2 times (on the 3rd). The two sides asked different questions, so these two numbers cannot be compared directly.

The following is the T6c finalization text (taken from the reply output by `ds_result.py`, unmodified):

> **T6c simplified quota display · final design points (finalized)**
>
> - First-line format A (record includes weekly quota): `Tier: {tier literal} · 5h {P5}% · Week {PW}% · Reset {HH:MM}`; format B (record has no weekly quota): `Tier: {tier literal} · 5h {P5}% · Reset {HH:MM}`; separators, spaces, and punctuation are fixed character by character.
> - The first line must start with the literal `Tier: ` prefix; no blank line, heading, comment, or any prefix is allowed before it; use `^` to anchor the line start and compare the whole line character by character; no trailing spaces at line end, only a single newline is allowed.
> - Percentages are displayed rounded (round-half-up, 0.5 rounds up); the tier is not normalized, comparing the raw value character by character for equality.
> - The reset time is always local-timezone `HH:MM`; only validate legality (`^([01]\d|2[0-3]):[0-5]\d$`), and **do not** compare it with the recorded value.
> - Hook decision flow: parse the stdin JSON for session_id and tool input → take the most recent `get_usage` call record → no record goes to the fallback → with a record, first judge freshness → then judge field completeness → then compare the whole line character by character → exit 0 or exit 2 and write back the count.
> - The hook erroring itself (invalid stdin JSON, unreadable record/state files, internal exception) → always **exit 0 and allow**, with just one diagnostic line in stderr, never blocking the task.
> - Fallback: no `get_usage` in the record (the CLI lacks that tool) → do not check percentages or the tier value, only validate the format against the full template; the tier segment only needs to be non-empty and contain no template separators, and `HH:MM` must still be a valid 24-hour time; bad format → exit 2.
> - Expired: the record exists but the timestamp is **> 10 minutes** ago → exit 2 bounce, with stderr explicitly requiring "please call get_usage again before writing the first line"; exactly 10 minutes counts as not expired.
> - Field completeness: the record has a weekly quota but no 5-hour limit → exit 2 bounce, likewise requiring a `get_usage` re-call, with no fallback and no guessing.
> - Missing-field comparison: record has no weekly quota → the line must omit the `· Week N%` segment (no 0% placeholder); record has a weekly quota but the line omits it → exit 2; a field missing on the hook side means that field is skipped in the comparison.
> - Consecutive-bounce count: state stored in `%TEMP%\plan_header_hook\<session_id>.json` (`{count, last_ts}`); count+1 before each exit 2; any pass clears it; within the same session, after 2 bounces, the 3rd bounce **exits 0 and allows with a warning**; failing to read or write the counter file is handled as a hook error (allow).
> - Warning delivery: on the 3rd allow, exit 0, and stdout outputs JSON: `{"systemMessage":"the quota line has failed the template 2 times in a row, allowing this time; please correct the first line to Tier: ... · 5h N% · Week M% · Reset HH:MM"}`, not written to stderr.
> - delegate-coding rule change: add a new rule to the delegate-coding rules (not scoped only to ExitPlanMode) — for all tasks going through delegate-coding, the first sentence at the start of work must output the quota line, **directly reusing the plan first line's whole-line template and fill rules** (including omitting the weekly quota when absent, rounding, local HH:MM), with no heading or blank line before it, as an explicit contract with the hook.
> - Test checklist 1: exact match (template A) → exit 0; exact match (template B) → exit 0.
> - Test checklist 2: record has a weekly quota, line omits the weekly segment → exit 2; record has no weekly quota, line adds a weekly segment → exit 2.
> - Test checklist 3: rounding semantics — record 42.5 / line 43 → pass; record 42.5 / line 42 → bounce; record 42.4 / line 42 → pass.
> - Test checklist 4: tier literal mismatch (case, alias, empty tier) → exit 2.
> - Test checklist 5: blank line, heading, space, or BOM before the first character → exit 2 (character-anchored).
> - Test checklist 6: invalid `HH:MM` (24:00, 7:5, 07:60, 7:5:00) → exit 2; `HH:MM` value differs from the record but the format is valid → pass.
> - Test checklist 7: no `get_usage` record + correct format → fallback exit 0; no record + bad format → exit 2.
> - Test checklist 8: record exactly 10 minutes → pass; 10 minutes 1 second → exit 2 and prompt a `get_usage` re-call.
> - Test checklist 9: record has a weekly quota but no 5h → exit 2 and prompt a `get_usage` re-call.
> - Test checklist 10: consecutive bounces — 1st and 2nd exit 2, 3rd exit 0 with `systemMessage` in stdout; after a pass in between, the count clears and starts over.
> - Test checklist 11: the hook itself throws (stdin not JSON, record file corrupt, state directory not writable) → exit 0, stderr has exactly one diagnostic line, no traceback.
> - Test checklist 12: cross-session isolation — session A's count does not affect session B; the same session shares the count across tasks.
> - Test checklist 13: delegate-coding first-sentence regression — the first sentence produced by the rule goes through the same template validation as the plan's first line; a consistent format passes.
>
> Finalized, no more questions.

## Next steps

- After the user scores both plans (1-5), decide which route to use, then update the pending test results in `dispatch-architecture-v2.md`.
- If retesting, both sides must first be given the same rules: a round limit and a stopping criterion.
