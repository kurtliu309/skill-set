# Dispatch plan lessons (retrospective)

Maintained since 2026-11-12; append here after every major change. The current rules are only in `<HUB>\global\agent-ops\skills\delegate-coding\SKILL.md`; where this page conflicts, SKILL.md wins. This page keeps each version's design, why it failed, and the test evidence, so the lessons are not lost after old files are deleted.

## Round 6 (2026-11-12, 2.0.0): cut the gate and multi-round, keep only one skill

**1.0.0 failed in a real run**: on a real order (adding a `sub` function), the Flash writing the task card copied `discover -s tests -t .`, a command that needs `tests/__init__.py`, but the card also said "do not add `__init__.py`", and it was not on the allowlist either. Result: round 1 acceptance failed; in round 2 the executor added the file and acceptance passed, but the gate judged it out of scope; round 3 stalled and was stopped manually. **Once the acceptance command and the allowlist contradict each other, the executor cannot resolve it and can only burn through the rounds.**

**The user's judgment**: the acceptance command and gate setup are too redundant; simplify everything into one skill.

**What 2.0.0 keeps**: `SKILL.md` plus a `deepseek-agent.ps1` (starts DeepSeek, caps at `--max-turns 80`, prints the final reply). Checking goes back to the main conversation: Opus looks at the diff and tests itself; Haiku relays verbatim and the user judges. The same task was tested in 7 rounds, finished in 11 seconds, tests OK.

**What was cut**: `dispatch.ps1`, the `-Gate`/`GATE-*` gate lines, `-Accept`, multi-round rework, the card-writing step, the ledger, `ds_result.py`, `coder-system.md` (content merged into the script), all templates, and the 30 tests. Full text at `<HUB>\.trash\delegate-coding-1.0.0-20261112\`.

**What this round taught**
- Every extra machine check adds one more failure point where "checks conflict with each other". The more checks there are, the more someone has to write the config correctly — and the one writing the config is the weakest model.
- DeepSeek cannot stop on its own; one `--max-turns` is enough, with no need for the whole rounds, gate, and rework system.
- Run one real order before adding mechanisms: all 30 fake-claude tests of 1.0.0 passed, and the very first real order failed.

## Round 5 (2026-11-12, 1.0.0): the relay layer failed, switched to tiers by main-conversation model

**The failed design (0.4.1–0.5.0)**: the main conversation (Haiku) only relays; all engineering requests are compressed and handed to a newly started Opus supervisor.

**Why it failed**
- Haiku cannot tell whether the user is talking to it or asking it to forward to Opus. "Should this sentence be forwarded" is itself a judgment, and the rules forbade the main conversation from judging — a contradiction at both ends. In actual use the user considered Haiku "too poor".
- The rules relied only on the model's self-discipline, with no mechanism to enforce them. Hooks can block "doing it yourself", but not "should have forwarded and did not" or "lost information while compressing".
- It did not save either: every newly started supervisor re-reads the context, and each relay layer adds another layer of loss; when the main conversation is Opus, starting another Opus supervisor is pure duplication.
- Corroborating evidence: in the previous round the main conversation violated the rules and edited files directly.

**The new design (1.0.0, decided by the user)**
- The tier depends only on the main-conversation model. Opus is the stable tier: do it itself; for big tasks write a card and dispatch DeepSeek Flash to execute, with the main-conversation Opus doing the final review in person. Haiku is the thrifty tier: only chat; to change code, run one fixed command that first has Flash write the card, then has Flash execute; to ask about the project, run another command and relay the result verbatim.
- Haiku only needs to make a three-way classification (change code / ask about the project / small talk), and no longer judges "who to hand it to".
- Cards are written by Flash, not Pro. The user recalls testing that Flash was better; T4's conclusion was also that the model writing the spec makes little difference. Use `-PlannerModel` to switch to Pro.
- Stopping condition per the user's choice A: stop when acceptance passes, at most N rounds (default 3), enforced by the script, not relying on the model to say stop. In addition, each round has a `--max-turns` cap (aimed at the T6 case where DeepSeek cannot stop).
- Removed: tier switching at 80%/70% quota, Flash code summaries, Flash first review, short-lived Opus supervisor, at most one rework, `make_copy` copy isolation, loop mode. Original text at `<HUB>\.trash\delegate-coding-0.5.0-20261112\pipeline.md.bak`.

**What this round taught**
- Making a weak model the router: the problem lies in the "routing" step. Either let it do only classifications it can make at a glance, or do not let it route at all.
- Rules that can be given to a script (stopping, rounds, scope creep) should not be written as words for the model to read.
- Each round's gate only sees that round's changes. With multiple rounds, earlier out-of-scope changes become "invisible" in later rounds, so a final check across the whole order is needed (`dispatch.ps1` did this, with tests).
- Copy isolation was designed to keep the experiment from "seeing the old answer"; it is not needed for everyday work and requires porting back into the original project, so it was removed.

**Not yet verified**: whether the thrifty tier's Haiku can reliably execute the three-way classification; the user needs to switch to Haiku and test it. The thrifty tier currently has no final review, only the gate.

## Plan evolution

1. **Original delegate-coding (0.3.0 and earlier)**
   - The main conversation is fixed to Haiku 5.5: only converse, relay, summarize, and do lightweight acceptance.
   - Switches between normal / thrifty at a 60% quota threshold; plus a "full mode" the user turns on manually, giving a three-mode table.
   - Acceptance relies on the main conversation looking at the git diff itself or dispatching Haiku to check; when needed it marks "recommend upgrading to Opus" and pops up a question to the user.
   - Rework continues on the same agent via SendMessage.
2. **V2 (finalized, merged into SKILL.md 0.4.0)**
   - The main conversation is whatever model the user picked in the app; it only converses and dispatches, and does not act as supervisor itself.
   - Two tiers: 5-hour quota ≥80% or weekly quota ≥70% goes to the thrifty tier, otherwise stable; the tiers only change the supervisor.
   - Stable-tier supervisor = short-lived Opus calls (writing the spec reads only the Flash-written code summary; final review reads only the requirement + spec + first review); thrifty-tier supervisor = DeepSeek Pro.
   - Execution and first review are DeepSeek Flash in both tiers; `-Gate` is the only completion check; at most one rework, sent back to the same copy in a new process.
   - Execution and rework both happen in the copy made by `make_copy.sh` (the original repo history and .scratch contain old answers).
3. **Most-simplified discussion (not adopted)**
   - Discussed further cutting the supervisor / first-review layers and keeping only "execute + gate"; not adopted because final review proved the most valuable in testing (see below).

## Test evidence

- **T4**: the same task had its spec written by DeepSeek and by Opus respectively, and both outputs were ultimately bounced for rework by final review. This shows the model writing the spec is not the key; final review is the layer that catches things. Because of this the tier division is marked "tentative (T4 tested only one task)".
- **T5**: 12 DeepSeek runs, 0 false blocks by the acceptance command; 1 false block came from the scaffolding (gate config / copy environment), not the acceptance itself.
- **T6**: DeepSeek cannot stop — it keeps working past the point where it should stop. So completion cannot rely on the executor saying "done"; it must rely on an external gate and background task completion notifications.

## Key conclusions

- Final review is the most valuable: no matter how good the spec, rework happens; the last independent final review catches the most problems.
- The gate (`-Gate`) currently only has test data, **no real dispatch block / false-block data yet**.
- Failure escalation (confirmed by the user on 2026-11-12): if the gate fails twice in a row — the stable tier switches to Opus directly without stopping to ask the user; the thrifty tier follows the V2 original text: switch to Pro first, and if that still fails, stop and ask the user.
- The gate only sees changes within `-Cwd`; changes across directories (e.g. the hub's HANDOFF.md, .trash backups) rely on manual checking in final review.
- In a task card, any line starting with `GATE-ACCEPT:` / `GATE-ALLOW:` is parsed; before pasting the original spec into a rework card, remove the gate lines first, otherwise the gate reports a config error (exit code 6).

## Old files moved away

Location: `<HUB>\.trash\dispatch-consolidate-20261112\`; file names are the original name + `.bak` (e.g. `dispatch-architecture-v2.md.bak`), and the old path -> new path mapping is in `MANIFEST.txt` in the same directory. Includes:

- `dispatch-architecture-v2.md` (V2 draft)
- `V2-DRAFT.md`, `V2-SUMMARY.md`, `DESIGN-INVENTORY.md` (V2 final draft, summary, 37-item design inventory)
- `HANDOFF-DRAFT.md` (handoff draft)
- `engineering-paradigm-brief.md` (old handoff page, describing full mode)
- Also pre-rewrite backups `SKILL.md.bak`, `HANDOFF.md.bak`, `INDEX.md.bak`

Experimental data (T0–T6 directories, T4-TABLE.md, dispatch-tests-t0-t3.md, t6-grill-route-result.md, etc.) was not moved and is still in place.

## Open items

- The gate's block rate and false-block rate in real dispatch: the user will decide when to test.
- The tier division (only one task tested), loop-mode rework, and how to store manual tier overrides: tentative or undecided, see the "not implemented / tentative" section of SKILL.md.

## Change in the number of unit tests

- Original delegate-coding tests: HANDOFF recorded 9 at the time (written before the gate work).
- Item 2 (generic gate: -Gate, GATE-ACCEPT / GATE-ALLOW, exit codes 5 and 6, ledger gate and out_of_scope fields) added 10, totaling 19, all passing.
- Plan B (treat a non-zero claude exit as a gate failure) added 1, totaling 20, all passing.
- So the "Ran 9 tests" line in HANDOFF is outdated; it is 20 now. The user decided not to update HANDOFF and to keep it as is.
- The added tests all target gate decisions, exit codes, ledger fields, and out-of-scope checks, not the quality of the code produced by the model.
