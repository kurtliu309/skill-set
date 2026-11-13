---
name: deepseek-bare-mode-limits
description: deepseek-agent.ps1 runs with --bare, which gives only three tools (Bash, read, edit), cannot spawn subagents, hooks do not run, no background; the cause is --bare, not DeepSeek
status: active
updated: 2026-11-12
---

# The DeepSeek process cannot spawn subagents: the cause is `--bare`

**Conclusion**: `delegate-coding\deepseek-agent.ps1` starts DeepSeek with `claude --bare -p`. The official documentation states that bare mode provides only three tools: Bash, file read, and file edit, so even if `Agent` is listed in `--allowedTools` it is unavailable. This is not a capability limitation of DeepSeek.

## Evidence

- Probe (2026-11-09, `<WORKSPACE>\.scratch\team-bench-20261109\probe\REPORT.md`): 7 tools were explicitly allowed including Agent, and the model only saw Bash, Edit, Read. At the time the report noted "7 allowed, only 3 visible" without explanation.
- Official docs https://code.claude.com/docs/en/headless: "In bare mode Claude has access to the Bash, file read, and file edit tools."

## Other limitations of bare mode (same document)

- Does not auto-load custom subagents, skills, MCP, or CLAUDE.md; to use them you must pass them explicitly via `--agents`, `--mcp-config`, `--append-system-prompt-file`.
- Hooks do not run, even when passed in via `--settings`.
- Cannot run background commands or background subagents.

## Two more limitations we added ourselves

- The script's dev permissions forbid `Bash(claude *)` and `Bash(powershell*)`, so DeepSeek also cannot start another DeepSeek from the command line. Nesting has to go through the `py` dispatch script on the allowlist.

## How to use

- Keep using `--bare` for normal execution tasks: fast startup, unaffected by global configuration.
- When DeepSeek needs to spawn subagents, or you need to test hooks: use a copy of the script without `--bare`, with a separate `CLAUDE_CONFIG_DIR` and `--settings`, to avoid reading the user's global hooks and MCP. T0 test on 2026-11-12: it can spawn, and subagents also run on DeepSeek; but you must first unset the inherited `CLAUDE_CODE_SIMPLE`, otherwise the tools are likewise cut down to three. See [dispatch-tests-t0-t3](dispatch-tests-t0-t3.md).
- When a large task needs to be dispatched further down, you do not have to rely on DeepSeek nesting: have the Opus supervisor (a Claude coder subagent with Bash) run the dispatch script directly.
