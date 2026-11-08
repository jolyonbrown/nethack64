# Working with Claude Code and Codex

## Roles

- **You (Jolyon)**: direction, priorities, real-hardware testing, final say on
  ADRs that change the game's behaviour.
- **Claude Code — lead implementer.** Works through `docs/TASKS.md`, keeps
  `make test` green, writes ADRs and session notes. Instructions: `CLAUDE.md`
  (which imports `AGENTS.md`).
- **Codex — independent reviewer and second pair of hands.** Reviews diffs and
  ADRs, attacks hard bugs in parallel on a separate branch/worktree, and
  double-checks claims (sizes, "it works in VICE") by re-running commands.
  Instructions: `AGENTS.md` (read directly).

Both agents share one source of truth: the repo. Nothing important lives only
in a chat transcript.

## The loop

1. Pick a task from `docs/TASKS.md`; put your name/date on it.
2. Branch: `task/T1.3-else-macro` (one task per branch).
3. Do it; run the verification loop in `AGENTS.md`.
4. Review: Claude Code calls `/codex-review` (or you run `codex` yourself on
   the branch). Codex reads the diff + task, runs the checks, reports
   problems. Disagreements go into the PR/session note, not silently dropped.
5. Merge when checks pass; tick the task; write the session note.

## Wiring Codex into Claude Code

`.mcp.json` registers Codex as an MCP server:

```json
{ "mcpServers": { "codex": { "command": "codex", "args": ["mcp-server"] } } }
```

It exposes `codex` (start a session: `prompt`, `cwd`, `sandbox`,
`approval-policy`, ...) and `codex-reply` (continue one by `threadId`).
Needs the Rust Codex CLI on PATH and logged in. Known gotchas: very old
versions don't return the `threadId` from `codex` (multi-turn breaks) — keep
Codex CLI current; reviews should use `sandbox: "read-only"`.

Without MCP: run Codex in its own terminal in the same repo (or a git
worktree), point it at the branch, and ask for a review against `AGENTS.md`.

## Parallel work without collisions

- Separate git worktrees per agent (`git worktree add ../nh-codex task/...`).
- Separate VICE ports: `VICE_PORT=6503 tools/vice.py launch ...` in the second tree.
- `build/` is per-worktree; nothing global except installed tools.

## Handoff notes

`docs/sessions/YYYY-MM-DD-<agent>.md`, five headings: **Changed**,
**Verified** (commands + results), **Measured** (any sizes/timings),
**Next**, **Questions for Jolyon**. Short. The next session (either agent)
starts by reading the latest note and `docs/TASKS.md`.

## Review checklist (for whichever agent reviews)

- Does it build for both targets (`make`, `make prg`) and keep `make test` green?
- If `port/` changed: `tools/check_ansi.sh`, host build, `tests/host_smoke.py`?
- Any change to game behaviour has an ADR?
- New compiler workaround has a repro in `tests/oscar64-repros/` and a row in
  `docs/OSCAR64-COMPAT.md`?
- Memory: did the resident region grow (`make memmap`)? Is it justified?
- No reads of `$DF00-$DFFF`; no EasyFlash RAM use?
- Claims in docs dated and reproducible?
