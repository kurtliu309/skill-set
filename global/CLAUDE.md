## Agent skills

Global defaults for the mattpocock engineering skills. If the current project has its own `docs/agents/*.md` (or an `## Agent skills` block in its CLAUDE.md / AGENTS.md), those override the files below.

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/` in the current project root. See `~/.claude/docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `~/.claude/docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` + `docs/adr/` at the current project root. See `~/.claude/docs/agents/domain.md`.

## Hub (all projects)
- The entry point for notes, ideas, pitfalls and skills is `<HUB>/INDEX.md`; the rules are in `<HUB>/PROTOCOL.md`. To look something up, read the index first, then open only the page you need.
- To save a piece of knowledge you will use again ("note this down", "add an idea"), load the `hub-write` skill first, then follow it to pick the location, register the index entry and run the checks.
- Treat the automatic memory directory as a scratchpad only; long-lived content belongs in the hub or in the project's `docs/notes/`.

## Global preferences
- Write all prose aimed at the user in Chinese; leave code, commands and file names unchanged.
- End every plan with a file-tree diagram.
- Save context: to accept a result, read only the last line of the test output and the key sections — do not print whole diffs. Connectors can only be turned off by the user from the + menu in the desktop app's input box.

## Delegation (all projects)
- Every conversation that touches engineering or a project (whether or not it is just a question) must load the `delegate-coding` skill before it starts; its rules are authoritative and must not be skipped.
