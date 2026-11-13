# Hub protocol

Rules for managing AI knowledge and skills. Every model and every tool reads and writes by this page.

## How to find things

1. Start at [INDEX.md](INDEX.md).
2. Use the "when to read" column: open only the next level that matters for the current task.
3. Keep going down until you reach a note or a skill. Never read a whole directory top to bottom.

## Four roles

| Role | File | Purpose |
|---|---|---|
| Entry | `~/.claude/CLAUDE.md`, a project's `AGENTS.md` | Loaded automatically by the tool. Only hard rules and "which index to read next" |
| Index | `INDEX.md` in every folder | Lists what is in this folder and when to read it |
| Note | Any other `.md` | One topic per page: facts, rules, reasons, pitfalls |
| Skill | `SKILL.md` and its companion files | Executable procedure |

There is no depth limit. The only requirement: every level down must be pointed to by one line in the index above it.

## Two scopes

- **Global**: `<HUB>/global/<domain>/`. Content useful across projects.
- **Project**: stays in the project folder (`AGENTS.md` + `docs/INDEX.md` + `docs/notes/`), with one line in [projects/INDEX.md](projects/INDEX.md). Project-only skills go in the project's `.claude/skills/`.

Not sure where it belongs: put it in the project by default. Promote it to global when a second project needs it. Ideas that belong to no project go in `global/inbox/`.

## Writing rules

- **Links may only point downward.** An index points to the next level; a note does not link to another domain. If two domains need the same fact, promote it one level up.
- **Every fact has exactly one home.** Link from elsewhere; never copy the content.
- **One topic per page.** Do not pile unrelated facts into one file.
- **Only record what cannot be read from the environment**: rules, reasons, conclusions, pitfalls. Do not record what the code or file listing already shows.
- File and folder names: lowercase English with hyphens, for example `bilibili-567.md`. Note bodies may be written in any language.
- To add, edit or move anything in the hub or a project hub, use the `hub-write` skill. It picks the location, applies the template, updates the index and runs the checks.
- Anything that does not follow the main rules must be listed in [EXCEPTIONS.md](EXCEPTIONS.md).

## Templates

### Index `INDEX.md`

```markdown
# <folder name>

<one sentence: what goes here>

| Content | When to read |
|---|---|
| [Title](file.md) | one-sentence condition |
| [Subfolder](sub/INDEX.md) | one-sentence condition |
| `skill:name` | one-sentence condition (for a skill that is not in the hub) |
```

### Note

```markdown
---
name: <same as the file name>
description: <one sentence, enough to decide whether to read it>
status: active | draft | stale
updated: YYYY-MM-DD
---

# Title

Conclusion first. Then the reason, how to use it, and pitfalls.
```

### Project entry `AGENTS.md`

```markdown
# <project name>

<one sentence: what this project is>

- General rules: `<HUB>/PROTOCOL.md`.
- Project notes index: [docs/INDEX.md](docs/INDEX.md)
- <hard rules specific to this project, one per line>
```

## Checks and tidy-up

- After every write run: `py <HUB>/tools/check.py --root <hub or project path>`. It must report zero errors.
- Hierarchy map: `py <HUB>/tools/build_map.py` generates `map.html`.
- Tidy up once a week: file loose notes and the inbox, merge duplicates, fix broken links, mark stale pages as stale. A tidy-up produces suggestions only; change nothing until the user confirms.
- Every checked root has a `hub.json` that declares the scope.
