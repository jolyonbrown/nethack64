# Brainstorm, 2026-11-15: making NetHack fit and run fast enough on a C64

After the speed and working-set measurements (docs/RAM-PLAN.md), Jolyon asked for alternative
approaches before deciding where to fix the hot spots. Four models worked independently from
one brief (`brief.md`), each with a focus of its own:

| File | Model | Focus | Means |
|---|---|---|---|
| `fable.md` | Claude Fable | the compiler and the code | read the repository, ran experiments in Oscar64's emulator |
| `gpt-6-astra.md` | GPT-6 Astra (Codex) | hardware, memory architecture, prior art | web search |
| `gpt-6.1-sol.md` | GPT-6.1 Sol (Codex) | 6502 and scene techniques | web search |
| `gemini.md` | Gemini (agy) | the widest list | the brief only |

These are model outputs, kept as they came (one scratch path removed). What was checked,
corrected or rejected, and the direction Jolyon chose, are in RAM-PLAN.md, "The brainstorm
and the direction". Two corrections apply to the brief itself: the static frames take 3.2 KB,
not 11.5 KB (Oscar64 overlays them), and 103 banks of 16 KB do not fit a 1 MB EasyFlash plus a
512 KB REU, so 39 of them have to be copied from the REU into RAM to run.
