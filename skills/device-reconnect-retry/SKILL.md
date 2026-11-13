---
name: "device-reconnect-retry"
description: "Use when the connection to the user's computer drops (the remote-devices / fxhoudini tools disappear or report not connected): first ask the user how often to check and for how long, then check automatically with the chosen settings, and notify them and resume the original task once it reconnects."
---

# Automatic reconnection when the computer drops offline

The user's network is unstable, and the connection between the cloud session and their computer (through the Claude desktop app's device bridge) drops from time to time.

## 1. Work out which layer dropped
- **The whole connection is gone**: every `mcp__remote-devices__*` tool disappears at once, or they return "device is not connected to the bridge". Houdini is probably still open → follow the flow below.
- **Only Houdini is unresponsive**: the device tools are still there, but `fxhoudini__get_houdini_connection_status` says not connected, or execute_python keeps timing out → do not use this flow: first check whether the output files are still being updated, and once you have confirmed it is stuck or closed, ask the user to reopen Houdini manually and start the MCP service (start_houdini is not available).

## 2. Ask for the check interval and duration
1. If the user already said so in this conversation, reuse it and do not ask again.
2. Otherwise use AskUserQuestion to ask both questions in a single call:
   - Check interval: every 15 minutes (recommended, uses the least quota) / every 5 minutes / every 2 minutes (fastest recovery, most quota) / no automatic checks, wait for me to come back and message
   - Maximum duration: 30 minutes / 1 hour / 2 hours / 4 hours
   Explain each in one sentence in the question text: every check is a full round of conversation, roughly re-reading the entire current context (about 1/10 of the price through the cache), so the longer the conversation the more each check costs; total checks = duration ÷ interval. When the conversation is already long, recommend "no automatic checks". The user can pick "Other" and write their own.
3. If AskUserQuestion is unavailable (a scheduled / unattended session): ask the same two questions in plain text, end the round and wait for the reply; do not pick settings and start polling on your own.
4. If "no automatic checks" is chosen (ignore the second question in that case): tell the user to send a message once reconnected and you will continue, then stop and schedule nothing.

## 3. Schedule checks with the chosen settings
1. Number of checks M = duration ÷ interval (round up). Tell the user in one sentence: checks have started every X minutes, M in total, and you will notify them once it reconnects; they can also resume immediately by opening this conversation in the desktop app and sending a message.
2. Use `mcp__claude-code-remote__send_later` (delay_minutes = interval, initiation = human_request) to schedule the next check. The message must be self-contained:
   - which check out of how many, the interval, the total duration;
   - how to check: ToolSearch `select:mcp__remote-devices__get_device_info,mcp__remote-devices__fxhoudini__get_houdini_connection_status` and call them; failing to load them or a not connected reply counts as not reconnected;
   - not reconnected: do not message the user, do nothing else, do not narrate; just schedule the next check at the same interval (number +1);
   - reconnected: a summary of the task to resume (what to do, the constraints, how far it got).
3. If still not connected when the limit is reached: stop scheduling and use SendUserMessage to tell the user in one sentence that you tried for Y and it did not reconnect, and that sending a message once it is back will let you continue. Do not consume any more quota after that.
4. If the user changes the interval or duration part-way through: use `mcp__claude-code-remote__delete_trigger` to cancel checks that have not fired yet, and reschedule from 1 with the new settings.
5. Do not switch to checking with a new session via create_trigger: a scheduled task bound to the computer is suspended while the computer is offline (suspension_reason = device_absent) and never runs at all (measured 2026-10-30).

## 4. Once reconnected
1. SendUserMessage to tell the user it has reconnected; if a PushNotification tool is available, also push it to their phone.
2. If the user messaged first and recovery happened early: use delete_trigger to cancel checks that have not fired yet.
3. Check the state before continuing: whether Houdini is connected, which hip is open, whether there are unsaved changes; clean up leftover mplay.exe / hffmpeg.exe (without popping up windows).
4. Do not simply resend operations that were issued before the drop but whose results never arrived (cache, flipbook, save and so on): first look at the output files or logs to confirm whether they had already finished.
5. Continue the work from the task summary.
