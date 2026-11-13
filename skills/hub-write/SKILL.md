---
name: hub-write
description: Use when writing, editing or moving notes, indexes, domains or skills in the hub (`<HUB>`) or in a project hub. This covers jotting down an idea, saving a pitfall or conclusion, relocating memories, creating a domain or registering a project, creating or moving a skill, and the weekly tidy-up. Whenever a piece of knowledge you will need again has to be written down, load this skill first instead of picking a location yourself.
---

# hub-write

The full rules live in `<HUB>/PROTOCOL.md` (the templates are there too). This skill is the fixed procedure for writing.

## Procedure

1. **Decide the scope**
   - Relevant to only one project → the project hub: `<project>\docs\notes\`, with skills in `<project>\.claude\skills\`.
   - Useful to two or more projects, or a general practice unrelated to any project → global: `<HUB>/global/<domain>\`.
   - Ideas and to-dos that are not thought through yet → append one entry to the end of `<HUB>/global/inbox/ideas.md`.
   - Not sure → put it in the project. Do not put it in global "in case it is useful later".

2. **Look for an existing home first**
   Read the `INDEX.md` at the target location. If a page on the same topic already exists, edit that page rather than creating a new one. Never write the same fact in two places; link to it instead.

3. **Write the content**
   - Notes: use the note template in PROTOCOL. One topic per page: conclusion first, then why, how to use it, and pitfalls. File names are lowercase English with hyphens, and `name` matches the file name.
   - Skills: load `skill-creator` first and follow its conventions; the location follows step 1. The real files for a global skill go in `<HUB>/global/<domain>/skills/<name>/` and are registered in that domain's `INDEX.md`. Once in place, run `py <HUB>/tools/link_skills.py` to create the links (run it again after changing computers; see `<HUB>/EXCEPTIONS.md`).
   - Third-party skills (loose folders downloaded from the internet): place them like your own, in `<HUB>/global/<domain>/skills/<name>/`. Read every file before installing (other people's skills are untrusted) and do not change their content; write the source URL in that line of the domain's `INDEX.md`. If the name does not follow the conventions, register it in `<HUB>/EXCEPTIONS.md`. App-synced skills (`skills\synced\`) and plugin skills do not go into the hub; write `skill:<name>` in the index instead.
   - New domain: create a folder and an `INDEX.md` under `<HUB>/global/`. Create it only when there is already content to put there; do not pre-create empty domains.
   - New project: add a line to `<HUB>/projects/INDEX.md`; when tidying it, create `AGENTS.md`, `docs\INDEX.md` and `hub.json` following the project-entry template in PROTOCOL.

4. **Register in the index**
   Add a line to the `INDEX.md` of the containing folder: link + "when to read this". New folders also need a line in the parent index. Skills that are not in the hub are written as `` `skill:<name>` ``.

5. **Check**
   ```
   py <HUB>\tools\check.py --root <hub root or project path>
   ```
   It must report zero errors; look at warnings and keep one only if you can explain why.

6. **Commit**
   - Hub: `git -C <HUB> add -A` and then commit, with a message saying what was added. Push only during the weekly tidy-up or when the user asks.
   - Project: commit only the documents you added or changed this time; do not include other people's uncommitted changes in the project.

7. **Tell the user** where it was put and why it went there.

## Do not

- Do not write keys, cookies or tokens into the hub (it syncs to GitHub).
- Do not edit app-synced skills or plugin skills; the changes will be overwritten.
- Do not place anything outside the main rules. If an exception is genuinely needed, add a line to `<HUB>/EXCEPTIONS.md` explaining why.
- Do not record things that can be read directly from the environment (code structure, file lists, git history).

## Weekly tidy-up

Produce suggestions only; change nothing until the user confirms:

1. Run `check.py` on the hub and on every organized project.
2. Read `global\inbox\ideas.md` and each project's memory directory (`~/.claude/projects/*/memory/`): decide what should become a note and what should change status.
3. Look for duplicates, stale content, and content that should be promoted from a project to global.
4. List the suggestions for the user, each written as "from where → to where / what to change / why".
5. After the user confirms, execute using the procedure above, regenerate the hierarchy map with `py <HUB>\tools\build_map.py`, commit and push.
