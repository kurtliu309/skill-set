# notes

Working notes from the setup this repository was exported from. They are English
translations of the originals, with names and machine paths removed.

| Folder | What it holds |
|---|---|
| [`inbox/`](inbox/INDEX.md) | **The idea and to-do system.** One running log of ideas and to-dos, plus longer write-ups for the ones that grow. |
| [`agent-ops/`](agent-ops/INDEX.md) | How work is dispatched between models: the dispatch lessons, test results, token and quota notes. |
| [`hub/`](hub/HANDOFF.md) | Hand-off notes from building the hub system (the starter itself is in `../hub-system/`). |

## The idea / to-do system (`inbox/`)

- **One file to append to**: [`inbox/ideas.md`](inbox/ideas.md). Each entry has a date, a
  title, a status (`undecided` / `planning` / `in progress` / `done` / `abandoned`), the content
  and optional notes. New ideas are appended at the end; the assistant is told "note this down" and
  does not ask where it goes.
- **Never delete an entry.** Update its status as it moves; for abandoned ones, write one line
  saying why.
- **Grow in place**: when an idea reaches "planning" and needs detail, it gets its own page
  (see [`001`](inbox/001-multi-person-collab-agent.md) and
  [`002`](inbox/002-news-pipeline.md)); `ideas.md` keeps only a link.
- The inbox is one domain in the hub (`global/inbox/`), indexed like every other domain, so
  the assistant can find it from `INDEX.md` without scanning the tree.

## Agent dispatch (`agent-ops/`)

Start with [`dispatch-v2-lessons.md`](agent-ops/dispatch-v2-lessons.md) for why the current rule is
as simple as it is (compare the `delegate-coding` skill in `../skills/`). The test notes
([`dispatch-tests-t0-t3.md`](agent-ops/dispatch-tests-t0-t3.md),
[`t6-grill-route-result.md`](agent-ops/t6-grill-route-result.md),
[`deepseek-bare-mode-limits.md`](agent-ops/deepseek-bare-mode-limits.md)) hold the measurements it
rests on.

## Notes on the notes

- Some notes mention files that were later archived or that live only in the original
  workspace (marked with placeholders such as `<HUB>`); they are kept as historical record.
- The hub map (`map.html`) is generated, not stored: run `hub-system/tools/build_map.py`
  on your own hub. The generated map of the original hub is not included because it lists
  private note titles.
