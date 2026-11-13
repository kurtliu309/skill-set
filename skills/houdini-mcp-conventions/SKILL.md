---
name: "houdini-mcp-conventions"
description: "The working rules for Houdini MCP: token-saving practices, hard rules, paths and naming (governed by houdini-kpipe), flipbook delivery, and wrap-up. Load it before doing any Houdini operation through fxhoudini (opening or creating a scene, creating nodes, simulating, caching, flipbooks, rendering)."
---

# Houdini MCP working rules

This skill is how to work (stable rules). Things that change do not live here: verified pitfalls and practices are in the project doc `claude/houdini_kb.md` (new entries go into `claude/houdini_kb_inbox.md` first), project state is in `claude/projects/<project>.md`, and mid-task handoffs are in `claude/handoff_<project>.md`. If any of these docs are already visible in context, do not project_read them again; if this skill has already been loaded in this conversation, do not load it again.

## 1. Opening (once per conversation)
1. Load the core tools with a single ToolSearch: `select:mcp__remote-devices__fxhoudini__execute_python,mcp__remote-devices__fxhoudini__get_houdini_connection_status,mcp__remote-devices__fxhoudini__connect_houdini`. Load the other fxhoudini tools only when execute_python cannot do the job, and load as many as you need in one go: every tool definition that is loaded stays in context for the rest of the conversation.
2. Ports start at 8100 and go up by one per extra instance; one conversation sticks to one port. If Houdini is not responding: ask the user to open Houdini and start the MCP service (start_houdini is not available). If the whole computer connection has dropped: use the device-reconnect-retry skill.
3. Get the state with a single execute_python call: hip path, hou.hipFile.hasUnsavedChanges(), frame range and FPS, and the node names under /obj (names only).

## 2. Save tokens (do all of these)
- **Prefer execute_python**: use it for queries, building networks, setting parameters and running caches, and do a whole group of related operations in one script (including naming, network boxes and sticky notes). Every tool call resends the entire context, so fewer calls cost less. Wrap the script in try/except and return only the last ~15 lines of the traceback on failure.
- **Keep returns short**: no more than about 40 lines per return; print only the values you need, round floats to 3 decimals, give a count plus the first few items for lists; do not dump every parameter, attribute, point or node tree. Avoid large-output tools such as get_parameters, get_network_overview, get_scene_summary, get_node_info and capture_network_editor.
- **Checking parameters**: inside execute_python, use hou.nodeType(cat, name).parmTemplateGroup() to filter parameter names and default values by keyword; use search_help / get_help_page only when you need the underlying explanation, and quote only the paragraphs you need.
- **Long tasks** (expected > 50 s): estimate the time and disk space first; write a log (under kpipe that is var_scenes/logs, `cache.log_dir()`); after an MCP timeout do not poll — use send_later to check once at the expected completion time, reading only the last ~20 log lines and the count/size of the output files.
- **Images**: images you have looked at stay in context. Look at at most one keyframe sheet per iteration (≤ 1280 px wide, 6–8 tiles); if numbers can settle it (bbox, density statistics, projection error, frame count), do not look at images. Send files meant for the user with SendUserFile directly; you do not need to Read them yourself.
- **Do not open subagents**: there is only one Houdini instance and all its state is in the main conversation. Use a subagent only for work unrelated to Houdini whose output is long and can be thrown away once read (for example paging through a very long crash log), and have it report only the conclusion; such work can be assigned to haiku or sonnet.
- **Keep replies short**: the user often reads on a phone. One or two sentences of intent before starting; do not narrate every step in the middle; a few lines of result plus file locations when done.
- **One task per conversation**: when the task is finished, or the context is already long (after looking at several images and iterating many rounds), write `claude/handoff_<project>.md` (≤ 20 lines: goal, constraints, the user's direction, current state, next step, hip and key node paths, suggested model) and ask the user to start a new conversation. A new conversation carries only a few K of base context, whereas a long conversation re-reads everything before it on every round.
- **Do not switch models mid-task**: switching model or effort invalidates the entire cache, so only choose at the start of a new conversation. Write the "suggested model" line in the handoff according to the nature of the task: mechanical work (re-rendering a flipbook, encoding mp4, tidying files, batch-changing already-decided parameters, tidying the KB) uses Sonnet; new effect design, debugging and judging image quality use Opus.

## 3. Hard rules
- Never overwrite or rename the user's working files: to change one, first save it as a new version with Save Version (artist=mcp), then change the new version (see section 4); pure analysis is read-only. When there are unsaved changes, do not clear or save them on your own — ask first.
- Heavy simulations / large caches: run 10–20 frames first to estimate time and disk space, and get consent before running. During the test phase, cache ≤ 2 GB per shot and a single Pyro run ≤ 10–15 minutes. Disk space on D: is limited, so check the free space before a large cache.
- During the test phase, produce viewport flipbooks only; do not render.
- Put adjustable parameters in a spare folder on a control node and reference them from a wrangle with ch("../x"). Keep the network clean: node names, network boxes, sticky notes.
- When unsure about a parameter name or behaviour, look it up; do not make it up.
- Look at results with a VFX supervisor's eye: proactively point out problems with proportion, speed, detail, silhouette and timing, and give the fix.

## 4. Paths and naming (governed by kpipe)
- **Project, shot, asset, hip naming, folder structure and cache / flipbook / render paths are all governed by the `houdini-kpipe` skill** — load it first; they are not repeated here so they cannot go stale. When kpipe changes, change only houdini-kpipe; this section does not need to follow.
- Key points (see houdini-kpipe for details): create new projects and shots with kpipe (the Create window / `project.new_project`, `new_shot`, `new_asset`); save versions from MCP with artist=`mcp` (`project.save_version(artist=config.MCP_ARTIST)`); take paths from the Scene Manager variables (var_scenes, var_cache, var_playblast, var_render…) instead of hard-coding them. Test projects go in playground (`new_project(..., playground=True)`).
- Changing the user's working files: do not overwrite or rename the original; save a new version with Save Version (artist=mcp) and change that. Pure analysis does not need a save.
- Old hips without a Scene Manager (projects from before kpipe, such as the old ones with the mcp_ prefix): analyse read-only; to continue working, first ask the user whether to convert it into a kpipe project.
- Caching: use kpipe's `cache.create_cache()` (Labs File Cache, latest version); do not hand-write paths.
- Use variables in parameters (chs("/obj/scene_manager/var_cache"), $OS, $F4); do not hard-code absolute paths.

## 5. Flipbooks and delivery
- Before shooting: sv.setPwd(hou.node('/obj')) (when you are sitting inside a geo, the other objects are ghosted, and the flipbook captures that too); make sure the display flag is on the final node; outputToMPlay(False).
- Use kpipe's `flipbook.deliver()`: sequence → hffmpeg (h264_nvenc, yuv420p, scene FPS) → mp4 + keyframe sheet, output to var_playblast (paths governed by houdini-kpipe). Split long sequences into segments of about 150 frames.
- subprocess: creationflags=0x08000000 (no pop-up windows), decode output as gbk. Clean up mplay, hffmpeg and terminal processes when done.
- Delivery = keyframe sheet + mp4. To send to the user: device_request_folder_access `<HOUDINI>` → only after access is granted can ToolSearch find device_stage_files → stage → SendUserFile. For sheets that fail to stage, extract frames from the mp4 instead.
- When reporting, state clearly where the hip, cache, flipbook and render each live.

## 6. Environment and known limitations
- Windows with a Chinese locale; 16C/32T, 32 GB, RTX 5070 Laptop; Houdini 21.0.512 Commercial. Houdini's Python has numpy and PIL, but not scipy or cv2 (do OpenCV-style processing by sending images back to the container).
- Crash logs: `%LOCALAPPDATA%\Temp\houdini_temp\crash.*_log.txt`
- A single MCP call times out at 60 s, but Houdini keeps running to completion: for long tasks write a log, read it after the timeout to confirm, and do not resend.
- Showing connected but always timing out = possibly stuck: check whether the output files are still being updated, and if it is stuck ask the user to reopen.
- Second instance: start it from the existing Houdini with subprocess, then connect_houdini.
- render_sheet is not available; use SceneViewer.flipbook instead. A flipbook written directly to mp4 does not work.
- Capturing a long sequence with MPlay open crashes/hangs.
- return_expression must be a string; viewport settings reset after load_scene; a folder cannot be renamed while it is open and in use.

## 7. Wrap-up (when the task is done)
1. Overwrite `claude/projects/<project>.md` entirely (≤ 40 lines, only what is needed to continue the project: current version, key nodes, caches, the user's feedback, to-dos). When the project ends, fold the reusable practices into the KB and delete this file.
2. New cross-project pitfalls or practices: append one line each to `claude/houdini_kb_inbox.md`; when the inbox reaches about 10 entries, merge it into `claude/houdini_kb.md` (merging duplicates and dropping stale entries as you go, keeping the KB at about 150 lines) and empty the inbox. Do not rewrite the whole KB just to add one line.
3. Delete `claude/handoff_<project>.md` (if it exists).
4. Clean up mplay, hffmpeg and terminal processes.
5. If the task is unfinished and a new conversation is needed, write the "suggested model" line in the handoff (see section 2).
- When writing a project doc, write it to a local file first, then upload it with project_write's local_path.
