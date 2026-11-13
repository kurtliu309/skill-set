# Third-party content

## mattpocock-skills

- Upstream: https://github.com/mattpocock/skills
- Version: 1.3.1
- License: MIT — see `mattpocock-skills/LICENSE` (Copyright (c) 2026 Matt Pocock)

`mattpocock-skills/` is an unmodified copy of the upstream plugin: `LICENSE`, `README.md`
and the `skills/engineering`, `skills/productivity` and `skills/misc` folders. The upstream
`deprecated/` and `in-progress/` skill folders are not included. Nothing here has been
translated or edited; it is kept for reference only.

**The recommended install is the Claude Code plugin from the official marketplace**, which
updates itself:

```bash
claude plugin install mattpocock-skills@claude-plugins-official
```

Copying these files into `~/.claude/skills/` by hand also works, but you then maintain them
yourself and lose plugin updates.

These skills expect the "Agent skills" section in `global/CLAUDE.md` (issue tracker, triage
labels, domain docs) and the files it points to under `global/docs/agents/`. If a project has
its own `docs/agents/*.md` or an `## Agent skills` block, those take precedence.
