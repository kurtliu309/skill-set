---
name: delegate-coding
description: Must be loaded before every conversation that touches engineering or a project. When the main conversation is Opus: delegate to DeepSeek whenever possible, then check the result yourself. When the main conversation is Haiku: only chat, hand engineering work to DeepSeek verbatim, and relay its reply unchanged.
---

# Delegation rules

Version 2.1.0. For the lessons behind these rules, see `CHANGELOG.md`.

First check what model you are: **Haiku uses the lightweight mode, every other model uses the standard mode.**

## Command to dispatch DeepSeek

Write the task into a `.md` file in your scratchpad, then run this in the background:

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File "$USERPROFILE/.claude/skills/delegate-coding/deepseek-agent.ps1" -Cwd '<project dir>' -PromptFile '<task file>' < /dev/null
```

- Flash is the default. For Pro, add `-Model claude-opus-5-5`. For read-only tasks, add `-Access strict`.
- When it finishes it prints `== DEEPSEEK ok=... turns=...`, followed by the agent's final reply. It stops after 80 turns at most (`-MaxTurns`).
- Wait for the completion notification; do not poll.

## Standard mode (Opus)

- Delegate to DeepSeek whenever you can (not a hard rule, but consider it first by default). In the task file, state the working directory, what to change, what not to touch, and which command to test with.
- Keep for yourself only: small jobs that take one or two steps, work that needs MCP / a browser / artifacts, and design decisions that need back-and-forth with the user.
- Check the result yourself when it finishes: look at `git diff` and the test output. If it is not good enough, fix it yourself or dispatch again.

## Lightweight mode (Haiku)

You only chat, run the command above, and relay results. Do not read code yourself, do not edit files, do not evaluate the result.

- When the user wants to change a project or asks about something in a project: copy their exact words into the task file, start it with a line `Working directory is <dir>`, then run the command. For questions that change nothing, add `-Access strict`. Relay the reply to the user unchanged.
- If you don't know which project directory it is, ask the user.
- Everything else (small talk, questions about you) answer directly.
- If the user says "hand it to Opus", tell them to switch the model to Opus in the app.

## Exceptions

- If the user names a specific model or agent, use that one.
- Houdini: state in the task that it must run `<python> <HOUDINI>/pipeline/tools/hou_exec.py <script.py>`, must not modify the original project, and must not move nodes. For work that needs the fxhoudini MCP, do it yourself in standard mode, or dispatch the `houdini-coder` agent.
- DeepSeek can spawn subagents (Agent tool). The subagents also run on DeepSeek with the same permissions. There is no MCP, browser or network access.
