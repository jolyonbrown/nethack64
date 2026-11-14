# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Skills in `.claude/skills/` (invoke as `/name`):
  - `/c64-run` — build, boot in headless VICE, drive it with keys, read the 80-column screen as text
  - `/port-file <file.c>` — take one NetHack source file through Oscar64 (measure, fix, record)
  - `/oscar64-repro` — reduce a compiler problem to a repro + workaround + doc entry
  - `/codex-review` — ask Codex for an independent review of the current diff or a design question
  - `/session-handoff` — write the end-of-session note in `docs/sessions/`
- Codex comes in through OpenAI's Claude Code plugin (`codex@openai-codex`, enabled in
  `.claude/settings.json`); its `/codex:review` and `/codex:adversarial-review` are for Jolyon to run.
  Your own Codex reviews follow `/codex-review`: a packet piped into `codex exec -s read-only`.
  Codex must not edit the tree while you are working. There is no Codex MCP server any more
  (`codex mcp-server` was removed in Codex CLI 0.154); see `docs/AGENT-WORKFLOW.md`.
- `.claude/settings.json` pre-approves the build/test/VICE commands; `git push`, `git reset
  --hard` and deleting `port/` still prompt (settings are Jolyon's to change: the auto-mode
  classifier blocks agents from editing permission rules). Jolyon, 2026-11-14: "You do not
  need my permission to use git", so do not stop to ask before git operations.
- Long VICE sessions: launch with `--headless`, and always `tools/vice.py quit` afterwards so
  no emulator is left holding port 6502.
- Commit messages end with the `Co-Authored-By: Claude ...` line and no `Claude-Session:`
  link, even where Claude Code's own attribution adds one (Jolyon, 2026-11-13: the repo is
  public and the link is no use to its readers). Commits meant for upstream Oscar64 follow
  `docs/OSCAR64-UPSTREAM.md` instead.
