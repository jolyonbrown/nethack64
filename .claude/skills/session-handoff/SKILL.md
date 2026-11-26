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

Then bring the status documents up to date with what landed (AGENTS.md, "Recording what
you learn"):
- `docs/TASKS.md`: tick finished items, and add a dated note to the ones that moved;
- `docs/PLAN.md`: its "Where we are" line, and the phase checkboxes;
- `README.md`: "Where it stands" (what plays, the figures table, what is still to come);
- `docs/TO-DECIDE.md`: new questions, and decisions moved to Decided.

Make sure `make test` was the last thing run and is green.
Keep the note under ~40 lines.
