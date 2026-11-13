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
- `.claude/settings.json` pre-approves the build/test/VICE commands; anything that deletes
  `port/` or rewrites history still asks.
- Long VICE sessions: launch with `--headless`, and always `tools/vice.py quit` afterwards so
  no emulator is left holding port 6502.
