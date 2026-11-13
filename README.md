# skill-set

A small, sanitized export of a personal Claude Code setup: skills, subagent
definitions, global instructions, and the file-based knowledge system used to manage
them.

Everything here is plain text and independent of any private project. Paths that would
identify a machine or a person have been replaced with placeholders (`<HUB>`, `<HOUDINI>`,
`<WORKSPACE>`, `<VENV>`, `<python>`, `VIDEODOWNLOADER_DIR`); they are explained below.

## Contents

| Path | What it is |
|---|---|
| `skills/` | Source files for the skills below |
| `agents/` | Subagent definitions for Claude Code |
| `global/` | A global `CLAUDE.md` and the default engineering docs it references |
| `hub-system/` | The knowledge / skill management system: protocol, starter tree and tools |
| `third-party/` | Unmodified third-party skills, kept for reference (see below) |
| `dist/` | Ready-to-install archives built from the folders above |

### Skills

| Skill | What it does |
|---|---|
| `delegate-coding` | Dispatch a scoped coding task to a cheaper model (DeepSeek by default) from the main conversation, then verify the result. Includes the PowerShell dispatcher and a changelog explaining the design. |
| `hub-write` | The write procedure for the hub: where a note or skill belongs, the template, index registration and checks. |
| `fetch-and-summarize` | Turn a video (Bilibili, YouTube, anything yt-dlp supports) or a web page into timestamped text, then summarize it. Subtitles first, local Whisper transcription as a fallback. |
| `houdini-kpipe` | Usage of `kpipe`, a Houdini pipeline toolkit: projects, shots, assets, caching, wedges and the scene manager. |
| `houdini-mcp-conventions` | Stable working rules for driving Houdini through its MCP server: token-saving practices, hard rules, delivery of flipbooks, wrap-up. Paths and naming defer to `houdini-kpipe`. |
| `houdini-td-expert` | How to answer Houdini knowledge and troubleshooting questions: conclusion first, exact names, numbers, pitfalls, performance. |
| `device-reconnect-retry` | When the cloud session loses the connection to the user's computer: ask how often and how long to check, resume the task automatically once the device is back. |
| `local-mcp-install` | Installing, registering, verifying and troubleshooting a local MCP server on Windows, including where the Microsoft Store build of Claude Desktop reads its config. |

### Placeholders

Machine- and person-specific paths are replaced throughout:

- `<HUB>` — the root of the personal knowledge hub, the folder containing `INDEX.md` and `PROTOCOL.md`.
- `<HOUDINI>` — the Houdini working directory holding the `pipeline/` toolkit, `projects/` and `tools/hou_exec.py`.
- `<WORKSPACE>` — a scratch workspace folder used as the working directory for one-off scripts and test runs.
- `<VENV>` — a Python virtual environment with the packages from `requirements.txt`.
- `<python>` — the Python interpreter that runs scripts; for Houdini code, one that can import `hou`.
- `VIDEODOWNLOADER_DIR` — optional environment variable naming a folder that contains `ffmpeg.exe` (see `fetch-and-summarize`).

### Subagents

| Agent | What it does |
|---|---|
| `coder` | Lean coding agent with file tools and a shell only: make a scoped change and run the tests. |
| `houdini-coder` | The same, restricted to a Houdini pipeline directory. |

### Hub system

`hub-system/` is a starter knowledge base. It contains:

- `PROTOCOL.md` — how the tree works: four roles (entry, index, note, skill), global
  versus project scope, writing rules and templates.
- `INDEX.md`, `global/`, `projects/` — a valid, nearly empty hub to copy and fill in.
- `EXCEPTIONS.md` — things that deliberately live outside the hub, and why.
- `tools/check.py` — validates links, names, frontmatter, orphan pages and skill
  junctions. Exit code 1 on error.
- `tools/link_skills.py` — exposes global skills in `~/.claude/skills` as directory
  junctions (Windows).
- `tools/build_map.py` — renders the whole hierarchy as an interactive `map.html`.
- `tools/tests/` — unit tests for the tools (26 tests).

See `hub-system/README.md` for the quick start.

## Third-party

`third-party/mattpocock-skills/` is an unmodified, MIT-licensed copy of Matt Pocock's skills
(upstream: https://github.com/mattpocock/skills, version 1.3.1). The recommended install is
the Claude Code plugin from the official marketplace
(`claude plugin install mattpocock-skills@claude-plugins-official`); this copy is for
reference. The "Agent skills" section of `global/CLAUDE.md` configures these skills (issue
tracker, triage labels, domain docs). See `third-party/README.md`.

## Install

Claude Code reads skills, agents and global instructions from fixed locations:

| Pack folder | Copy to |
|---|---|
| `skills/<name>/` | `~/.claude/skills/<name>/` (or install the matching `.skill` archive) |
| `agents/*.md` | `~/.claude/agents/` |
| `global/CLAUDE.md` | merge into `~/.claude/CLAUDE.md` |
| `global/docs/agents/` | `~/.claude/docs/agents/` |

`hub-write` and `delegate-coding` refer to the hub and to a local dispatcher script;
adjust the `<HUB>` placeholder and the model/CLI settings to your own setup before use.

`fetch-and-summarize` needs the packages in `skills/fetch-and-summarize/requirements.txt`
(the scripts only fetch and transcribe; summarizing is the assistant's job).

Python 3.11+ is required for the hub tools. They use only the standard library.

## What is deliberately not included

- Personal notes, research notes, ideas and pitfall logs.
- Assistant memory files.
- Private project code or data.
- Credentials, cookies, tokens.

## Source

Shared from a personal Claude Code workspace. Repository:
https://github.com/kurtliu309/skill-set
