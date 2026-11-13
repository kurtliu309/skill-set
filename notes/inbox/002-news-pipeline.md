---
name: 002-news-pipeline
description: "News push pipeline plan: Task Scheduler starts a DeepSeek subagent on a schedule, scripts fetch (RSSHub/Horizon/BiliNote), the model reads and writes the daily digest and memory, webhook pushes; direction set 2026-11-13, memory design pending a plan-mode discussion"
status: active
updated: 2026-11-13
---

# Idea 002: News push pipeline (video summaries + daily digest)

- Date recorded: 2026-11-13
- Status: planning (direction set, memory design undecided, not tested, project not created)
- Merged ideas (see [ideas.md](ideas.md)): Bilibili video summaries, the daily scheduling framework, frontier tech 5 items; AI monetization ideas and finance monitoring will later be plugged in as two other tasks.

## Conclusion

**The Windows Task Scheduler starts a DeepSeek subagent directly at the scheduled time, and it exits when done.** Scripts do the fetching; the model only reads and writes. No Claude scheduled tasks, no new Discord bot, no agent framework like OpenClaw.

```
Task Scheduler 9:00
  └─ news-agent.ps1 -Job tech -Model <Flash|Pro>
       ├─ DeepSeek runs: py fetch.py tech   ← calls RSSHub / Horizon / BiliNote, outputs plain text
       ├─ DeepSeek reads the material, writes digests\YYYY-MM-DD-tech.md, writes memory
       └─ py push.py   ← Discord webhook pushes to the user's private channel
```

## Why this design

- **A new session every time**: no conversation accumulation, and no re-reading previous tokens each time. "Remembering" relies on files.
- **The model is selectable**: write Flash or Pro in the config per task.
- **No Claude quota spent**: no Claude relaying in between; Claude scheduled tasks charge subscription quota every time, and only Claude's own models can be selected.
- **Scripts fetch, model reads**: the subagent has WebFetch/WebSearch/curl disabled and can only run scripts to get material; all fetch logic lives in code.
- **No all-permissions bot**: we discussed "create a new bot with full internet and local machine permissions". When the model has no tools, large process permissions are not dangerous; but push only needs a webhook, so there is no need to create a bot. If we later want "send a Bilibili link and get a summary back", add it then.
- **The old chat bot stays untouched**: `<WORKSPACE>\discord-deepseek-bot` serves a friends' group; its permissions stay on the allowlist. Its `fetcher.py` and `Memory` approach can be referenced or reused.

## Chosen existing solutions (picked by adoption, November 2026 snapshot)

| Part | Solution | Notes |
|---|---|---|
| Source | [RSSHub](https://github.com/diygod/rsshub) | Bilibili uploaders, X (needs cookie), GitHub Trending (needs token) to RSS; one Docker command to start |
| Digest engine | [Horizon](https://github.com/Thysrael/Horizon) | MIT, Python; fetch → dedupe → LLM scoring and summarization → Markdown; the page mentions DeepSeek, integration not verified |
| Video summary | [BiliNote](https://github.com/JefferyHcool/BiliNote) | MIT; Bilibili subtitles via cookies/player API, falling back to yt-dlp; Fast-Whisper when there are no subtitles; supports DeepSeek |

Researched but not chosen: OpenClaw, Hermes Agent (agent frameworks that let the model go online by itself, the opposite of "scripts fetch, model reads"); n8n (visual workflows, memory has to be wired up yourself); auto-news (needs Airflow + Notion, too heavyweight).

## How to start

- Reuse the approach of `~/.claude/skills/delegate-coding/deepseek-agent.ps1` and write a separate `news-agent.ps1`: swap the system prompt to "read material, write the digest, write memory", round cap about 15. The original dispatch script stays untouched.

## Pending

1. **Memory** (next step: open a plan-mode discussion): how much to store; whether the subagent only writes and never reads, or also reads when writing the digest; the user leans toward "write memory only", undecided.
2. Real testing: two RSSHub routes, Horizon connected to DeepSeek, BiliNote getting subtitles from one Bilibili link.
3. Project location: tentatively `<WORKSPACE>\news-pipeline\`; once created, register it in the project registry and move this page there.
