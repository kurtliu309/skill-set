# Exceptions

The main rule is: global content lives in `<HUB>/global`, project content lives in the project folder, and both are indexed. The items below deliberately do not follow that rule. Every new exception must be registered here, otherwise the checker reports an error.

| Item | Where it lives | Why it is an exception | Long term |
|---|---|---|---|
| Entry point of a global skill | `~/.claude/skills/<name>` is only a junction; the real files are in `<HUB>/global/<domain>/skills/<name>/` | The tool only scans this directory for global skills | Permanent. Create the skill in the hub, then run `tools/link_skills.py` to make the junction |
| Skills installed inside the app | The app-managed sync folder | The app overwrites local edits | Permanent. Index them only; edit them in the app |
| Official and plugin skills | Plugin directories | Overwritten on update | Permanent. Index them only |
| Global entry file | `~/.claude/CLAUDE.md` | The tool decides the location | Permanent. Keep the content as short as possible |
| Memory directories | `~/.claude/projects/` | The tool writes there and scopes them per project | Scratchpad only. Move long-lived content into the hub during the weekly tidy-up |
| Build artifacts: `.scratch`, `_snapshots` and similar | Inside each project | Process artifacts, not knowledge | Never migrated |
| Third-party skills whose folder name breaks the naming rule | Wherever they were installed | Renaming would break their own references | Register the name here and leave the files untouched |
