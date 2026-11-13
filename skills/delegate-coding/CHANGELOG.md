# delegate-coding changelog

Newest first. The full text of older versions is kept in `<HUB>/.trash/` (`delegate-coding-0.4.1-*`, `-0.5.0-*`, `-1.0.0-*`); the reasoning behind each change is in the retrospectives.

- **2.1.0 (2026-11-12)**: Standard mode became "delegate to DeepSeek whenever you can". The script dropped `--bare` (it cuts the tool set down to Bash/Read/Edit, and `--tools` cannot add them back, so subagents can't be spawned), and now isolates with `--strict-mcp-config` + a separate `CLAUDE_CONFIG_DIR`, while allowing the Agent tool; strict mode explicitly denies Edit/Write (acceptEdits would auto-approve them). Measured: a strict subagent succeeded and writes were rejected; a dev subagent wrote files successfully.
- 2.0.0 (2026-11-12): Major simplification. Only `SKILL.md` and `deepseek-agent.ps1` remained; the script only starts DeepSeek, caps at 80 turns and prints the reply. Removed the gate, acceptance commands, multi-round rework, write-card step, ledger, templates and tests.
- 1.0.0 (2026-11-12): Split by main-conversation model; added `dispatch.ps1` (write card, gate, up to 3 rounds). In practice, acceptance commands and the allow list contradicted each other and tasks could not be completed; the user found it too heavy, and it was replaced by 2.0.0 the same day.
- 0.5.0 (2026-11-12): The main conversation only relayed messages and handed everything to an Opus supervisor. Failed: Haiku could not tell when to answer itself and when to forward.
- 0.4.x (2026-11-12): V2 pipeline (quota tiers, summary → spec → execution → first review → final review).
- 0.3.0 and earlier: Haiku main conversation, three-mode table, 60% threshold.
