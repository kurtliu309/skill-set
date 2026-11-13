# agent-ops

How to make AI do work: dispatch, engineering process, writing skills, tool-use tips.

| Content | When to read |
|---|---|
| [delegate-coding](../../skills/delegate-coding/SKILL.md) | Before a conversation that involves engineering or a project; Opus does it itself or dispatches to DeepSeek, Haiku just hands the engineering work verbatim to DeepSeek |
| [hub-write](../../skills/hub-write/SKILL.md) | Adding, changing, or moving notes, indexes, or skills in the hub or a project hub |
| [Quota display simplified plan](quota-script-plan.md) | When you want the plan's first line to show the tier and Claude quota, or you are writing the ExitPlanMode hook |
| [T6 grill route results](t6-grill-route-result.md) | When deciding whether grill question generation goes to an Opus subagent or DeepSeek, scoring the T6 plan, or before retesting T6 |
| [T0–T3 test conclusions](dispatch-tests-t0-t3.md) | When writing hooks, starting DeepSeek without --bare, or finalizing v2 |
| [DeepSeek's --bare limits](deepseek-bare-mode-limits.md) | When a DeepSeek process needs to spawn subagents, run hooks, or run background tasks |
| [Token-saving analysis](token-saving-analysis.md) | When you want to save Claude quota, evaluate token-saving plugins, or decide on handing off from Haiku to Opus |
| [Wide screenshots with headless Edge](wide-screenshot-edge-headless.md) | When the built-in browser screenshot is wrong, or the pane is hidden |
| `skill:skill-creator` | Creating or modifying the content of a skill (official) |
| `skill:mattpocock-skills:writing-for-agents` | When writing docs for agents to read |
| `skill:mattpocock-skills:grilling` | Confirming design decisions round by round before implementation |
| `skill:mattpocock-skills:*` the rest | Diagnostics, TDD, prototyping, research, code review, and other engineering steps |
| `skill:device-reconnect-retry` | When the connection to the user's computer drops |
| `skill:local-mcp-install` | Installing, removing, or troubleshooting local MCP servers on the user's computer |
