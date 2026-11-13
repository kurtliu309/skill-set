---
name: 001-multi-person-collab-agent
description: "Idea: an agent aimed at small groups, weighting and summarizing opinions and running timed brainstorming"
status: active
updated: 2026-11-12
---

# Idea 001: Multi-person collaboration agent (weighted opinion summary + timed brainstorming)

- Date recorded: 2026-11-07
- Status: original idea (not refined)

## In one sentence

An agent aimed at small groups: synthesizes everyone's opinions by each person's weight; it can also run a timed brainstorming session, and after the deadline automatically summarizes and proposes plans.

## Feature 1: Weighted opinion summary

- Each member has a weight (e.g. the lead has a high weight, an observer a low one).
- On a given topic, everyone gives their own opinion.
- The agent summarizes the opinions by weight: which are consensus, which are disputed, and which side the high-weight people lean toward.

## Feature 2: Timed brainstorming

- The initiator opens a brainstorming session and sets a deadline (e.g. "before 18:00 today").
- Before the deadline, all members can submit ideas / thoughts / opinions in that session without limit on times or quantity.
- When time is up, the session closes automatically and the agent:
  1. Summarizes (deduplicates, categorizes)
  2. Proposes several candidate plans

## Questions to work out

- Who sets the weights? Fixed, or varying by topic (e.g. by area of expertise)?
- During brainstorming, can people see others' ideas? (Seeing them enables mutual inspiration; not seeing them avoids herd behavior)
- Do weights matter in brainstorming? Or is everyone equal during brainstorming, with weighting only when choosing the final plan?
- Anonymous or real-name?
- Where to run it: Feishu / DingTalk / WeChat group bot / Slack / standalone web page?
- What happens after the summary: a vote? The agent recommends one? Export to a document?
