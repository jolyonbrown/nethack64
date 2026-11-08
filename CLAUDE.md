# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Skills in `.claude/skills/` (invoke as `/name`):
  - `/c64-run` — build, boot in headless VICE, drive it with keys, read the 80-column screen as text
  - `/port-file <file.c>` — take one NetHack source file through Oscar64 (measure, fix, record)
  - `/oscar64-repro` — reduce a compiler problem to a repro + workaround + doc entry
  - `/codex-review` — ask Codex for an independent review of the current diff or a design question
  - `/session-handoff` — write the end-of-session note in `docs/sessions/`
- Codex is wired in as an MCP server in `.mcp.json` (`codex mcp-server`, tools `codex` / `codex-reply`).
  Always call it with `sandbox: "read-only"` for reviews; it must not edit the tree while you are working.
- `.claude/settings.json` pre-approves the build/test/VICE commands; anything that deletes
  `port/` or rewrites history still asks.
- Long VICE sessions: launch with `--headless`, and always `tools/vice.py quit` afterwards so
  no emulator is left holding port 6502.
