# hub-system

A file-based knowledge base for AI assistants: notes, rules and skills, with an index at
every level and a small checker that keeps the tree honest.

The idea is simple. An assistant should never have to read a whole directory to find one
fact. It starts at the entry file, reads one index, opens one more level, and lands on the
page it needs. Notes are one topic per page, every fact has exactly one home, and indexes
only point downward. The protocol in [PROTOCOL.md](PROTOCOL.md) defines the rules; the
`hub-write` skill (in the `skills/` folder of this pack) defines the procedure for writing.

## What is here

| Path | What it is |
|---|---|
| `INDEX.md` | The root index of this starter hub |
| `PROTOCOL.md` | The rules: roles, scopes, writing rules, templates |
| `EXCEPTIONS.md` | Things that deliberately live outside the hub |
| `global/` | Cross-project domains (`global/<domain>/`) |
| `projects/` | Registry of project hubs |
| `hub.json` | Checker configuration for this root |
| `tools/check.py` | Structure checker: links, naming, frontmatter, orphan pages, skill junctions |
| `tools/link_skills.py` | Creates the junctions that expose hub skills in `~/.claude/skills` |
| `tools/build_map.py` | Generates an interactive `map.html` of the whole tree |
| `tools/tests/` | Unit tests for the tools |

## Quick start

1. Copy this folder somewhere, for example `~/hub`. It is already a valid hub.
2. Run the checker and the map builder:

   ```
   py tools/check.py --root .
   py tools/build_map.py
   ```

3. Read [PROTOCOL.md](PROTOCOL.md), then start adding notes and domains.
4. To expose a global skill, put it in `global/<domain>/skills/<name>/` and run
   `py tools/link_skills.py`. On Windows this creates a directory junction in
   `~/.claude/skills`; on other platforms, create a symlink instead or skip this step.

Python 3.11 or newer is enough; the tools use only the standard library. `check.py` is
cross-platform. `link_skills.py` uses `mklink /J` and is Windows-only.

## How the checker thinks

- Everything reachable from `INDEX.md` through links is in scope.
- A file that no index points to is an orphan (E1).
- Broken links are E2; over-long indexes E3; bad frontmatter E4; bad names E5;
  a folder with no `INDEX.md` E6; an unregistered external link E7; a broken skill
  junction E8.
- Every folder that holds notes needs an `INDEX.md`.
- A folder containing `SKILL.md` is a skill unit and is checked as one object.

The exact codes and messages are in `tools/check.py`.
