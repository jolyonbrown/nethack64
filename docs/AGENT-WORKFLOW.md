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

OpenAI's Codex plugin for Claude Code (`openai/codex-plugin-cc`) is enabled
for this repo in `.claude/settings.json`; Claude Code offers to install it the
first time it starts here. It drives `codex app-server` and adds
`/codex:review` (Codex's built-in reviewer on the working tree or branch),
`/codex:adversarial-review` (a review you can steer with focus text),
`/codex:rescue` (hand Codex a task), and `/codex:status`, `/codex:result`,
`/codex:cancel`, `/codex:setup`. These are typed by you; Claude Code's own
review step uses `codex exec` (below). The plugin needs the Codex CLI on PATH
and logged in, which `/codex:setup` checks.

The old `.mcp.json` entry (`codex mcp-server`) is gone: Codex CLI 0.154.0
(2026-09) removed that subcommand.

**Sandbox.** Codex runs every command inside bubblewrap (`bwrap` from PATH;
Codex 0.167 ships its own copy in `codex-resources/`, but strace shows it runs
`/usr/bin/bwrap`, 2026-11-13).
Ubuntu 24.04 sets `kernel.apparmor_restrict_unprivileged_userns=1`, so bwrap
cannot create its user namespace ("setting up uid map: Permission denied",
"loopback: Failed RTM_NEWADDR"). Then even a read-only Codex cannot run
`git diff` or open a file, and `/codex:review` reports that it could not
complete (seen 2026-11-12). No Codex setting gets round it (checked 2026-11-13,
Codex 0.167): `sandbox_mode`, writable roots and permission profiles change what
the sandbox allows once it starts, `danger-full-access` turns it off, and the
deprecated `use_legacy_landlock` flag stops with "filesystem-restricted execution
requires bubblewrap to isolate app-server sockets". The fix OpenAI documents for
24.04 (learn.chatgpt.com/docs/sandboxing) needs root: Ubuntu's own profile, which
lets bwrap create the namespace and denies capabilities to what runs inside it.
Not applied (2026-11-13): nothing needs it while the workarounds below cover every
use; only the plugin's `/codex:review` and `/codex:adversarial-review` stay broken.

```sh
sudo apt install apparmor-profiles apparmor-utils
sudo install -m 0644 /usr/share/apparmor/extra-profiles/bwrap-userns-restrict \
  /etc/apparmor.d/bwrap-userns-restrict
sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict
bwrap --ro-bind / / --dev /dev --proc /proc --unshare-net true && echo ok
```

Instead, `/codex-review` gives Codex everything inline: one
self-contained packet (task, doc excerpts, full diff) piped into
`codex exec -s read-only`, so Codex needs no commands. A Codex that writes
(`--dangerously-bypass-approvals-and-sandbox`) runs only in its own worktree,
and only on projects where you have allowed it (this one: 2026-11-09).

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
