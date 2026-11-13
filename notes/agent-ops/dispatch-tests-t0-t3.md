---
name: dispatch-tests-t0-t3
description: T0–T3 test conclusions for dispatch plan v2: DeepSeek without --bare can spawn subagents, and PreToolUse/SubagentStop hooks, the ledger, and the completion gate all work; includes three Windows pitfalls
status: active
updated: 2026-11-12
---

# T0–T3 test conclusions (2026-11-12, Claude Code 2.1.302, DeepSeek Flash)

**Conclusion**: all four passed. In v2, "structured Router, ledger, completion gate, subagent-stop hook bounce-back" are all technically feasible. The evidence is the real tool calls and hook records in the logs, spot-checked in the main conversation. Full report and hook scripts: `<WORKSPACE>\.scratch\dispatch-tests-20261112\`.

| Item | Conclusion | Key evidence |
|---|---|---|
| T0 spawning subagents without `--bare` | pass | main-process `Agent` call; subagent messages carry `parent_tool_use_id`; tool call ids are DeepSeek-style `call_00_...`; the environment only has DeepSeek's key |
| T1 PreToolUse as Router | pass | main-process Write blocked with exit code 2; a subagent call's stdin carries `agent_id` and is allowed; the dispatch script is allowed |
| T2 ledger + completion gate | pass | one line each at the start and end of `ledger.jsonl`; when acceptance fails, `status=failed` and the script exits with code 1 |
| T3 SubagentStop exit code 2 | pass | first time blocked (`stop_hook_active=false`), **the subagent itself** then wrote DONE.txt, second time allowed |

## Pitfalls (must-read when writing hooks and starting DeepSeek in the future)

1. **`CLAUDE_CODE_SIMPLE=1` is inherited**, cutting tools down to only Bash/Edit/Read, which looks like "cannot spawn subagents". Before starting a child process without `--bare`, run `env -u CLAUDE_CODE_SIMPLE`.
2. **SubagentStop must specify `"matcher": "*"`**; without it, it never fires (Stop fires without it).
3. **Hooks crash when reading Chinese stdin**: Windows Python decodes as cp936. Use `sys.stdin.buffer.read().decode("utf-8", errors="replace")`. When it crashes the CLI only says "hook error occurred", easily mistaken for the hook not firing.
4. On Windows, hooks are executed by **Git Bash**, not cmd.
5. With exit code 2, stderr enters the model context as system feedback, so Chinese is delivered in full.

## Limitations (inferred)

- T1's Bash allowlist is prefix matching; `ls; echo x > f` can bypass it. The model did not bypass it this time, but it is not a hard security boundary; the production version must reject `; && | >` and the like.
- T0's proof that subagents run on DeepSeek relies on "only DeepSeek credentials in the environment + the call id format"; the `model` field in the log is just the request alias `claude-sonnet-5-5`.
- Only Flash, a single subagent, and short tasks were tested; concurrency, long tasks, and Watchdog were not tested.

Related: dispatch-architecture-v2 (archived on 2026-11-12 to `<HUB>\.trash\dispatch-consolidate-20261112\dispatch-architecture-v2.md.bak`), [deepseek-bare-mode-limits](deepseek-bare-mode-limits.md).
