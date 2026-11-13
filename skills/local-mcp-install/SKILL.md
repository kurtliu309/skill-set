---
name: "local-mcp-install"
description: "Use when installing, registering, uninstalling or troubleshooting a local MCP server on the user's Windows computer: choosing one, how to run commands on their machine, where the Store version of Claude keeps its config, and verification."
---

# Installing a local MCP on the user's computer

## Choosing one
- Compare GitHub stars/forks, the date of the latest commit, whether it supports the current version of the target software, and whether it has a PyPI/npm package with a built-in install command. Do not recommend new repositories that hardly anyone uses.
- Give the user the recommendation together with the reasons and source links.

## The computer's environment
- Windows; Python 3.13 at `<python>`, and `py -3` on the command line. Install packages with `py -3 -m pip install --upgrade <package>`. Whether Node is installed is unconfirmed — check `node -v` before relying on it.
- "Documents" is redirected by OneDrive to `%USERPROFILE%\OneDrive\Documents`; software preference folders live there, not in `%USERPROFILE%\Documents`.
- Claude Desktop is the **Microsoft Store version**. The config it actually reads:
  `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`
  It does not read `%APPDATA%\Claude\claude_desktop_config.json`, which is what installers write by default.

## Registering it with Claude
- **Merge** `mcpServers.<name>` into that real config file: back up the original first (`.bak-<timestamp>`), read it with json, add only this one entry, keep every other key, write a temporary file and then replace. Do not overwrite the whole file.
- Write an absolute path in `command` (Claude does not inherit the shell PATH when it launches an MCP server).
- Afterwards, have the user **quit Claude completely** from the tray and reopen it; closing the window is not enough. The restart drops the current connection, which is normal.

## How to run commands on their computer
1. If `device_bash` is available, use it directly.
2. If not: write the command as a `.bat` (or a `.bat` plus a `.py`), put it in an authorised folder with the device file tools, and have the user double-click it in File Explorer; the bat writes its output to a log file, which you then fetch back and read.
   - Computer use only grants click-level permission for terminals, PowerShell and File Explorer, not typing; do not try to work around that.
   - Logs may be GBK-encoded; decode them as GBK first.
   - Do not put "generate the file" and "upload to the computer" in the same batch of parallel calls, or old content gets uploaded; do it in two steps, or use a new file name each time.
   - Computer use must be switched on by the user in Claude desktop under Settings → This computer → Computer use (the Chinese UI wording is uncertain; switch the UI to English temporarily if you cannot find it). "Enabled" on the phone does not mean it is enabled on the computer — trust what the tool returns.
3. For scripts downloaded from the internet and for steps that change config, explain exactly what will change first and wait for the user to confirm.

## Verification
- After the restart, the MCP's tools appear in the session (in a remote session the names are `mcp__remote-devices__<name>__*`).
- Call a read-only tool (status / version / listing type) to confirm it is really connected, then tell the user it is installed.

## Uninstalling
- Use the package's own uninstall first (if it has one), then `pip uninstall` / `npm uninstall`; delete the entry from the Store version's config by hand (back it up first as well).

## Troubleshooting
- No tools in Claude: the config was written to the `%APPDATA%` copy, Claude was not fully quit, `command` is not an absolute path, or the JSON is malformed.
- The plugin inside the target software does not load: it was most likely installed to `%USERPROFILE%\Documents` instead of the preference folder under OneDrive's Documents.
