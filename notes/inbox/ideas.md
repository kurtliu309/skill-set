---
name: ideas
description: The user's ideas and to-do list, each with a date, status, and content
status: active
updated: 2026-11-12
---

# Idea log

Format:

```
## [date] Title
- Status: undecided / planning / done / abandoned
- Content: one or two sentences
- Notes: (optional)
```

---

## [2026-11-10] Agent dispatch logic: hand to Opus for design once quota recovers
- Status: in progress
- Content: Continue finishing the agent engineering dispatch logic (who does what, when to upgrade to Opus, quota-mode switching). Once quota recovers, have Opus design it.
- Notes: 2026-11-12 Opus produced a v2 draft, pending testing. Entry point `global\agent-ops\engineering-paradigm-brief.md`.

## [2026-11-10] Engineering paradigm: how loops and iteration run
- Status: undecided
- Content: Settle "how to run loops and iterate each time you do an engineering task". Split into two layers:
  1. the agent's own loop mode (how to execute and self-check within a single task)
  2. the whole project's iteration mode (how to advance, accept, and review across multiple tasks)
- Notes: Do it together with the dispatch logic above. 2026-11-12: the v2 draft already has the per-round engineering order and the single-task loop; refine after testing.

## [2026-11-10] Servers and self-built websites: research how to use them and how to publish
- Status: undecided
- Content: Research how to use a server, how to build your own website, and how to publish the website online.
- Notes: Research first, then decide which server and deployment method to use.

## [2026-11-10] Bilibili / other site video crawler + video content summarization
- Status: planning (merged into [002 news push pipeline](002-news-pipeline.md) on 2026-11-13)
- Content: Build a crawler that can pull videos from Bilibili or other sites. Core idea: you do not necessarily need the images; summarize the video content by analyzing only the audio and subtitles, hand that summarization capability to AI, and make it a tool that can be called repeatedly.
- Notes: See whether it can combine with existing video downloaders.

## [2026-11-10] Daily scheduled task: AI monetization ideas (3 per day)
- Status: undecided
- Content: Produce 3 ideas per day, on a schedule, that can be monetized or built with AI.
- Notes: Split out of "daily scheduled tasks"; can run independently.

## [2026-11-10] Daily scheduled task: frontier tech content (5 per day)
- Status: planning (merged into [002 news push pipeline](002-news-pipeline.md) on 2026-11-13, as the first task)
- Content: Every day, on a schedule, find 5 tech-related videos or articles from GitHub, Bilibili, and X, focusing on the most cutting-edge content.
- Notes: Split out of "daily scheduled tasks"; can run independently.

## [2026-11-10] Daily scheduled task: AI finance monitoring
- Status: undecided
- Content: Scan the finance sections once a day on a schedule, see whether there are relatively big opportunities, and do analysis in the finance direction.
- Notes: Split out of "daily scheduled tasks"; can run independently.

## [2026-11-10] Daily scheduled task: the scheduling framework itself
- Status: planning (on 2026-11-13 decided as "Task Scheduler starts a DeepSeek subagent", see [002 news push pipeline](002-news-pipeline.md); monetization ideas and finance monitoring will be plugged in later as tasks)
- Content: Build a framework that triggers once a day on a schedule, so the three tasks above can each run on time, output results, and be recorded in ideas.
- Notes: Settle the framework first, then plug the three tasks in.

## [2026-11-10] Web game: profit and monetization methods
- Status: undecided
- Content: Make an online game (web game), focusing on how to profit and how to monetize. Need to think through:
  1. Monetization model: ads, in-app purchases (items/skins/battle pass), membership subscription — which to choose or how to combine them
  2. What ad monetization requires: ad network or platform accounts, integration of ad slots such as rewarded video/interstitial, traffic and retention data, ad review compliance
  3. How to choose publishing channels: web (H5/web game portals), WeChat mini programs, Douyin mini games — each has different traffic, revenue share, and review rules, so they need comparing
- Notes: Compare the three channels and several monetization models first, then decide what game to make.

## [2026-11-11] Blender MCP: integrate an existing solution and make it one with kpipe
- Status: undecided
- Content: Use an existing Blender MCP solution, do not build one from scratch.
  1. Test first to verify it works
  2. Follow the existing pipeline's conventions and integrate it with the pipeline on the houdini-kpipe side
- Notes: Reminder: remember to come back and do this.

## [2026-11-11] Quota recovery reminder
- Status: undecided
- Content: When quota recovers, remind the user, then start the "Agent dispatch logic" item (designed by Opus).
- Notes: Reminder: remember to speak up proactively when quota recovers.

## [2026-11-11] Note organization framework: unified storage location and protocol
- Status: done
- Content: Organize all notes and MD files into one definite place, and turn it into a framework protocol, so new notes go into fixed locations per the protocol and are no longer lost every time. The current problem is that note files and MD files are scattered.
- Notes: 2026-11-12 first round complete: created `<HUB>` (protocol, index, check script, write skill hub-write, hierarchy diagram). See the hub's HANDOFF.md for what follows.

---


## [2026-11-12] Claude and DeepSeek quota display script
- Status: in progress (the user raised its priority on 2026-11-12)
- Content: Make a script that outputs Claude (5-hour, weekly) and DeepSeek (balance/usage) quota in one line, for the user to see and for models and hooks to read.
- Notes: Cheaper than the model calling `get_usage` (that returns a big blob of JSON; the script only needs one line); hooks cannot call MCP tools, so with the script, the "plan first line" hook could verify whether the percentages are real. Related to agent-ops' dispatch-architecture-v2.
- Already clarified (2026-11-12):
  - Claude: the only documented source is the status line script's stdin `rate_limits.five_hour/seven_day.used_percentage`, `resets_at` (Unix seconds), available only to subscription users and only after the session's first API response; hook stdin has no quota; neither `/usage` nor the CLI has machine-readable output. Docs: https://code.claude.com/docs/en/statusline.md#rate-limit-usage
  - DeepSeek: `GET https://api.deepseek.com/user/balance` verified working (¥11.63 at the time); the official API does not give usage history, so you have to record the balance before and after a dispatch yourself and compute the difference.
  - Direction: write our own, following approaches found online, without third-party packages (some only support macOS/Linux, some use login credentials to call the API). The status line script writes `rate_limits` into a cache file on each refresh; the model and hooks read the cache.
- Survey of existing tools (2026-11-12, the user asked to look at Bilibili/GitHub/X):
  - The mainstream status line tools claude-hud (jarrodwatts, about 18K★, needs Node) and ccstatusline (about 7K★) also read `rate_limits` from stdin, the same source as our plan; they only draw to the terminal status bar, do not write cache files, and do not serve hooks or models. Bilibili videos are basically all promoting these two.
  - Another category calls Anthropic's undocumented OAuth usage API, which requires login credentials; not used.
  - Known pitfalls: `rate_limits` only has `five_hour` and `seven_day` (no per-model weekly quota); the window may be missing entirely rather than null, so the script must be tolerant.
  - The DeepSeek side is all small projects (dsbc, pi-deepseek-balance, etc.), basically calling `/user/balance` plus local consumption-rate computation; a few lines of our own is enough.
  - Conclusion (inferred): nothing existing directly satisfies "write a cache for hooks to read"; still recommend writing our own, and we can reference the output format of jtbr's gist.
- To do (in order):
  1. ~~Confirm the direction~~: on 2026-11-12 the user decided "write our own".
  2. Small test result (2026-11-12, tested): the CLI `claude` (v2.1.302) does run the status line script; after sending the first message, `rate_limits` has `five_hour` and `seven_day`, and `cache.json` was written correctly (5h 82%, weekly 11%, matching get_usage). The desktop app's Code tab, when using `py -I ...`, did not call it at all in a new session; after changing to the full path of python.exe and retesting in a new session, it still did not call it → **conclusion: the desktop app does not run the status line script**. The cache only updates when using the CLI. Design should consider: the cache carries a write time and reports "unknown" when expired; in the desktop app, the model writes the same `cache.json` after calling `get_usage`. The following is the old record: installed `~/.claude/quota/statusline.py` (writes `cache.json`, logs one line per call to `calls.log`), added `statusLine` to `settings.json`, backed up at `settings.json.bak-20261112-quota`. In the session where it was installed, the app did not call it; you need to send a message in a new session and check whether it appears in `calls.log` and whether `rate_limits` is yes or no. Original plan: whether the desktop app's Code tab runs the status line script (install a cache-only status line script, back up `~/.claude/settings.json` before changing it, then restore or keep it after testing).
  3. ~~Enter plan mode + grill~~: on 2026-11-12 first settled on a modular cache plan, then changed to the simplified version (only get_usage + hooks, DeepSeek deferred), see `global/agent-ops/quota-script-plan.md`. Originally planned: settle the design: cache file location and format, one-line output format, how often to check DeepSeek balance, how to view it on the phone.
  4. Implement it and wire it into the first line of the dispatch script and the plan first-line hook.
