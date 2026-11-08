---
description: Write the end-of-session handoff note in docs/sessions and update TASKS/PLAN so the next agent (Claude Code or Codex) can pick up cleanly.
---

# Session handoff

Create `docs/sessions/<YYYY-MM-DD>-claude.md` (append `-2` etc. if it exists) with:

- **Changed** — files/areas, one line each
- **Verified** — exact commands and their results (pass counts, exit codes)
- **Measured** — sizes/timings with tool versions, if any
- **Next** — the next 1-3 tasks, by TASKS.md id
- **Questions for Jolyon** — decisions only he can make

Then tick finished items in `docs/TASKS.md`, update phase checkboxes in `docs/PLAN.md`
if a phase moved, and make sure `make test` was the last thing run and is green.
Keep the note under ~40 lines.
