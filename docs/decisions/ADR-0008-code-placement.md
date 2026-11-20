# ADR-0008: Code placement: the busiest banks on the EasyFlash, the rest from the REU

- Status: accepted (Jolyon, 2026-11-17: "accept ADR-0008, 1 MB REU minimum is fine");
  amended 2026-11-20: the REU minimum is 2 MB (Jolyon: "A bigger REU requirement is OK - if
  we need 2MB so be it"), below
- Date: 2026-11-16
- Deciders: Jolyon (+ Claude, who proposes it)

## Context
ADR-0003 chose EasyFlash + REU and left open where the code goes (ARCHITECTURE.md, "Code:
banking", options A-C). Measured since (BANKING-SPIKE.md):

- The whole game, built by Oscar64 with the pin of 80 commits from the bank plan of 2026-11-15
  (`tools/bank/build_c64.py --linker-stubs`), is 103 banks of up to 16 KB (1-103): 1,569,516
  bytes of code and literals, plus 17 KB of resident code. An EasyFlash holds 64 banks, one of
  them the boot bank, so 63 can hold banked code: 40 banks (about 600 KB) do not fit.
- A call into another bank costs 34 cycles through a resident stub (`tests/spikes/bankcall.c`);
  the pin's linker stubs make every such call (commit 72). An REU transfer costs about 1,090
  cycles a KB (the same spike), so a 16 KB bank is about 18 ms.
- How often play needs which bank (`tools/measure/bankplace.py`, `docs/data/bankplace-2026-11-17.txt`):
  in the host game's profile with the old bot (run, walk, stairs; 9,273 turns) 39 of the 103
  banks are never entered. That profile hides the cold code, so the bot gained `--wide`: it also
  picks up, quaffs, reads, zaps, eats, applies, wears, wields, throws, casts, kicks, engraves,
  opens doors and prays, in a game for each of the 13 roles (4,222 turns merged). Then 1,246
  functions are called and only 3 banks are never entered. Keeping the banks entered most on
  the cartridge, the others are entered:

  | Banks on the EasyFlash | Off it | Entries a turn into those (wide profile) |
  |---|---|---|
  | 63 | 40 | 0.9 |
  | 56 | 47 | 1.6 |
  | 48 | 55 | 2.8 |
  | 32 | 71 | 9.5 |
  | 24 | 79 | 20.8 |

  An entry is an upper bound on a load: the counts do not give the calls' order, and a bank
  already in the window needs none.
- The code and literals compress about 1.85:1 (deflate, per bank) to 2:1 (lzma). Keeping the
  overflow on the cartridge packed would leave room for only about 14-20 unpacked banks, so play
  would enter packed banks some 20 times a turn, each an unpacking of a fraction of a second on a
  6502: too slow.
- RAM: with the cartridge switched off, `$8000-$BFFF` is RAM. While banked code runs from the
  EasyFlash, data cannot live there anyway, so a 16 KB window there costs no data RAM.

## Decision
1. **The 63 banks entered most execute in place from the EasyFlash; the other banks (40
   today) live in the REU** and run in a 16 KB RAM window at `$8000-$BFFF`, with the cartridge
   switched off while they run. A call into such a bank goes through the same resident bank call
   routine: it loads the bank into the window by REU DMA if another one is there, switches the
   cartridge off, and on return switches back to the caller's bank. The routine keeps the rules
   of the linker stubs (A, X, Y, the zero page and the stack as it found them, both ways).
2. **The REU needs at least 1 MB, 2 MB recommended**: the overflow code (about 600 KB) beside
   far data (ADR-0009: `mons[]`, `objects[]`, the heap, about 60 KB plus its page cache), the
   RAM disk for levels and saves (T2.4) and room to grow. The 512 KB REU of `make run` stops
   being enough for the whole game. VICE and the Ultimate family offer up to 16 MB.
3. **The REU's code arrives as an image**: in VICE as an REU image file beside the `.crt`
   (`x64sc -reuimage`); on real hardware loaded from disk at start (about 600 KB) until a
   faster path is checked (the Ultimate's documentation reached on 2026-11-16 does not say
   whether it preloads an REU image; to be tested).
4. **The bank plan is made from the wide profile** (hot code together, rarely used code in the
   REU banks), and re-made as the code changes.

## Consequences
- Easier: everything the game needs fits, with no packing, and the cost is small: about one
  window load a turn at about 18 ms in this profile, against about 1 s a turn of game code.
- Harder: the bank call routine grows (a bank number past the cartridge means the REU, a check
  of what the window holds, the cartridge switched off and on); a function in an REU bank may
  not hand out a pointer into its own code or literals that outlives its call (the window can
  change: the same rule as for literals in EasyFlash banks today, BANKING-SPIKE.md); interrupt
  code must not run from the window. Real hardware needs the REU-aware EasyFlash (HARDWARE.md,
  the `$DF00` problem) and a way to fill the REU at start.
- Watch: the profile is a bot's, levels 1-4 at most; special levels, shops, the quest and the
  endgame are barely in it. If they enter REU banks often, the remedy is the plan (move hot
  functions to the cartridge), not the design. A stock C64 is outside this plan (as in
  ADR-0003, a stretch).

## Corrections and progress
- 2026-11-17: the counts above were first written as 104 banks, 62 kept and 42 (670 KB) off
  the cartridge: `bankplace.py` counted the plan's empty bank 0 as a bank. Corrected, with
  the boot bank kept apart: 63 banks for code (1-63), 40 off. Same decision.
- 2026-11-17: the bank call routine with REU banks, checked in VICE
  (`tests/spikes/bankreu.c`, `run_bankreu.py`; 14 checks: recursion through two REU banks
  and through an REU and an EasyFlash bank, A/X/Y kept, function pointers, tail calls, long
  results, the cartridge on again afterwards). A call into an EasyFlash bank is 300 cycles
  for an int (int, int) function there; into an REU bank already in the window, 361; with a
  16 KB fetch, 16,832 (17.1 ms). `tools/bank/crt_split.py` moves banks 64 and up from the
  .crt into the REU image; `bankgen.py --linker-stubs` writes the routine; the renumbered
  plan is `docs/data/bankplan-2026-11-17-reu.json` (`bankplace.py --write`). The REU size
  probe (`sys_reu_banks()`) now leaves the REU as it found it.
- 2026-11-17: the whole game from the renumbered plan passes every listing check
  (`docs/data/wholegame-reu-2026-11-17.txt`); its resident code is 828 B smaller than before,
  the string trampolines now ending in one call that copies and switches back.

## Evidence / how to re-check
`python3 tools/profile_play.py --wide --role R --merge -o build/profile-arcs-wide.json` for each
role (`tools/host-build.sh --profile` first); `python3 tools/measure/bankplace.py --profile
build/profile-arcs-wide.json`; the whole game's bank sizes from `tools/bank/build_c64.py
--check-only` (BANKING-SPIKE.md); `tests/spikes/bankcall.c` for the call and REU costs.
- 2026-11-20: **the REU minimum is 2 MB** (Jolyon). The far build's banked code grew with the
  bank call glue moved out of resident memory (T2.12, `docs/data/wholegame-far-2026-11-19b.txt`):
  1.79 MB of code and literals, about 110 banks, against the 121 a 1 MB EasyFlash and a 1 MB REU
  leave beside the far data, with the far heap spaces still to come. Banks 128-191 are the
  second megabyte; `nh_map` and `crt_split.py` needed no change (bank b at (b - 64) * 16 KB),
  and `crt_split.py` now pads the image to 2 MB. Checked in VICE: `tests/spikes/run_bankreu.py
  --second-bank 191` (the last 16 KB of a 2 MB REU), 14/14.
