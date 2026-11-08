# References

## Compiler and emulator
- Oscar64 — https://github.com/drmortalwombat/oscar64 (manual: `oscar64.md` in the repo;
  EasyFlash samples: `samples/memmap/easyflash*.c`; overlays: `samples/memmap/overlay.c`)
- cc65 — https://github.com/cc65/cc65
- VICE — https://vice-emu.sourceforge.io/ (binary monitor: manual chapter "Binary monitor";
  GitHub mirror with ROMs and docs: https://github.com/VICE-Team/svn-mirror)

## Hardware
- EasyFlash — https://www.c64-wiki.com/wiki/EasyFlash
- Ultimate cartridge emulation & REU-aware EasyFlash sub-type —
  https://1541u-documentation.readthedocs.io/en/latest/howto/cartridges.html
- Kung Fu Flash + REU discussion — https://github.com/KimJorgensen/KungFuFlash/issues/48
- EasyFlash and REU conflict — https://groups.google.com/g/easyflash-users/c/8b0NtZ3EGTQ
- Commodore 64 Ultimate (built on the Ultimate 64) —
  https://www.hackster.io/news/the-commodore-64-returns-as-the-fpga-powered-commodore-64-ultimate-4a8ea04e9dab
- CRT file format — VICE manual, "The CRT cartridge image format"

## NetHack
- NetHack 3.4.3 — https://www.nethack.org/v343/ (source also in `upstream/`)
- NetHack General Public License — `upstream/nethack-3.4.3/dat/license`
- MS-DOS overlay build (historic precedent): `upstream/nethack-3.4.3/sys/msdos/`
  (`Makefile.BC`, `schema*.BC`, `ovlinit.c`) and `include/trampoli.h`

## Agents
- Claude Code memory files and `@AGENTS.md` imports — https://code.claude.com/docs/en/memory
- Claude Code project files (`.claude/`, skills, `.mcp.json`) — https://code.claude.com/docs/en/claude-directory
- Codex CLI as an MCP server (`codex mcp-server`, tools `codex`/`codex-reply`) —
  https://codex.danielvaughan.com/2026/03/30/codex-cli-as-mcp-server/
