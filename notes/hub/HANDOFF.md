# Hub handoff (2026-11-12, after dispatch simplification 2.0.0)

The old full handoff (rounds 1 to 7) is at `_archive\handoff-20261112\HANDOFF-round1-7.md`. For why each version of the dispatch plan failed, see the retrospective `<WORKSPACE>\docs\notes\dispatch-v2-lessons.md`.

## Current dispatch rules

The rules are governed by `<HUB>\global\agent-ops\skills\delegate-coding\SKILL.md` (2.0.0). This skill has only three files: `SKILL.md`, `deepseek-agent.ps1`, `CHANGELOG.md`.

- **Main conversation is Opus (stable tier)**: do what it can itself; write big tasks into a task file and hand them to DeepSeek (Flash by default) with one command; when done, Opus looks at `git diff` and the tests itself.
- **Main conversation is Haiku (thrifty tier)**: only chat. To change the project or ask about things in the project, write the user's exact words into a task file and hand it to DeepSeek, relaying the reply verbatim to the user; for questions only, add `-Access strict`.
- DeepSeek runs at most 80 rounds per order (`--max-turns`). No gates, acceptance commands, or multi-round rework.

## What the next conversation should do: test

1. **Thrifty tier real test (priority)**: have the user switch the main conversation to Haiku in the app. See whether it can:
   - load `delegate-coding` right at the start;
   - distinguish the three cases: change the project, ask about the project, small talk;
   - when changing the project, not read code or edit files itself, only write the exact words into a task file and run the command, relaying the result verbatim;
   - ask the user first when it does not know the project directory.

   Suggest using a small git project that can run tests, testing at least one "change code" order and one "question only" order.
2. **Stable tier**: have Opus dispatch one real big task, and see whether DeepSeek can finish it within 80 rounds and whether Opus catches problems when checking.
3. After testing, write the conclusions into the retrospective document, opening a "Round 7" section.

Already verified: the new script ran one real order (adding `sub` to a temp repo's `calc.py`), 7 rounds, 11 seconds, tests OK.

## Not decided yet

- Whether to keep the "attach a file tree diagram before the plan ends" line in the global `~/.claude/CLAUDE.md`; if deleted, archive the `plan-tree-diagram.md` memory as well.
- Whether to archive the `chinese-code-summary.md` memory.
- Whether to add checks to the thrifty tier: right now Haiku only relays verbatim and nobody checks the code. Decide after the real test.

## Other to-dos (unrelated to dispatch)

- VideoDownloader: the T4 fixes are left in `<WORKSPACE>\.scratch\t4-20261112\A` and `\B`, not ported for now. Known issues: on successful completion, completed overwrites cancelled; `_finish` lacks a `_gen` guard; `resume` does not check `_removed`; in version B, an exception thrown during cleanup swallows the outcome.
- Houdini pipeline and cc_sandbox are only registered, not organized.

## How to verify the hub

```
py <HUB>\tools\check.py --root <HUB>
py -m unittest discover -s <HUB>\tools\tests
```
