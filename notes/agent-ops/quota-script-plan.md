---
name: quota-script-plan
description: Simplified plan for showing the tier and Claude quota on the plan's first line: only get_usage + an ExitPlanMode hook cross-check; DeepSeek balance deferred; finalized 2026-11-12, not implemented
status: active
updated: 2026-11-12
---

# Quota display: simplified plan (pending tests and implementation)

**Conclusion**: do not write a quota cache script. Claude quota uses only `get_usage`; use a `PreToolUse` hook on `ExitPlanMode` to ensure the plan's first line contains the tier and quota, and cross-check the numbers against the transcript. DeepSeek balance is ignored for now. Decided by the user on 2026-11-12.

## Why change to the simplified version

- The original plan (one cache file per source + `quota.py`) goes in circles in the desktop app: the data only comes from `get_usage`, and the model writes it into a cache and reads it back, which adds no information.
- The earlier claim that "hooks cross-check the cache for truth" also does not hold: the cache is written by the model itself, which amounts to checking itself against itself.
- The cache is only useful when the reading side cannot call `get_usage` (dispatch scripts, hooks, other agents); none of those needs is urgent now.
- The research notes are kept: `<WORKSPACE>\.scratch\quota-research-20261112\NOTES.md`. If we later integrate Codex or want DeepSeek balance, we can restart from the original plan's approach: one file per source, uniform format.

## Design

1. **First-line format**: `Tier: <stable|thrifty> · Claude 5h N% (HH:MM reset) · Week N%`.
2. **Data source**: before producing the plan, the model calls `mcp__ccd_session_mgmt__get_usage`, using the `5-hour limit` and `Weekly · all models` items it returns.
3. **Hook**: add `PreToolUse` in `~/.claude/settings.json`, matching `ExitPlanMode`. The script goes at `<HUB>\tools\plan_header_hook.py`, standard library only.
   - Read `tool_input.plan` from stdin and check the first line's format; if wrong, exit 2 with stderr stating the required format.
   - Read the transcript from `transcript_path` in stdin and find the most recent `get_usage` return. If not found, or older than 10 minutes → bounce, prompting "call get_usage first".
   - The two percentages in the first line must match that return; if not, bounce.
   - The tier is computed from the percentages per v2 rules: 5-hour ≥80% or weekly ≥70% → thrifty, otherwise stable (when there is a manual override by the user, the override takes precedence; how to store the override is pending v2).
4. **Phone**: the plan body is in the conversation, so its first line is that line, and it can be seen on the phone (pending real testing).

## To test first (in order)

1. Whether the PreToolUse hook on `ExitPlanMode` fires in the desktop app; after an exit 2 bounce, whether the model revises the first line and resubmits.
2. Whether the `get_usage` return text and timestamp can be found in the transcript pointed to by `transcript_path` (look at the tool_result structure in the JSONL).
3. Whether the plan's first line is visible on the phone.

**Test record (2026-11-12)**: item 2 passed. The `get_usage` return is stored in the transcript JSONL: the `type: user` tool_result line carries a `timestamp`, the `tool_use_id` can be matched to the earlier assistant `tool_use`, and the text is JSON (with `percentUsed` and `label`). The timestamp is UTC, so convert when comparing. Items 1 and 3 are untested.

Implement once all three pass. If item 1 fails, fall back to "rely only on delegate-coding rules to make the model write it", with no enforcement.

## Implementation steps (after the tests pass)

1. At the start of work, call `get_usage` to check quota.
2. Write `plan_header_hook.py` and tests: with fake stdin and a fake transcript, covering five cases: wrong format, get_usage not called, older than 10 minutes, numbers mismatch, pass. Hand the code and tests to the supervisor, dispatch DeepSeek Flash per delegate-coding, and the supervisor does the final review.
3. Main conversation backs up `settings.json`, then adds the hook; produce a plan once in the desktop app and confirm it can bounce and pass.
4. Main conversation edits `delegate-coding`: call `get_usage` before producing a plan and write the first line in the format.
5. **Sync with the CLI terminal version of Claude Code (the user's requirement, must be the last step)**: the desktop app and the CLI `claude` share `~/.claude/settings.json`, so changes take effect on both sides.
   - Remove `statusLine`, move `~/.claude/quota/` into `.trash`, and leave no dangling old scripts.
   - Produce a plan once in the CLI `claude` and confirm the new hook also bounces and passes properly, with no errors and no leftovers in the status bar.
   - Tell the user the result.
6. Run `check.py --root <HUB>` and commit the hub.

## Also to handle

- The status bar script from the old test at `~/.claude/quota/` and the `statusLine` in `settings.json` are no longer needed. When implementing, move them into `.trash` and remove `statusLine` (backed up at `settings.json.bak-20261112-quota`), telling the user first.
