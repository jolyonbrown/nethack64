---
description: Ask Codex for an independent, read-only review of the current branch diff or a design question, then weigh its findings.
argument-hint: "[what to review]"
disable-model-invocation: true
---

# Codex review

1. Collect context: `git diff master...HEAD --stat`, the task id from `docs/TASKS.md`,
   and any ADR touched.
2. Build one self-contained packet in the scratchpad: the task, the review checklist
   from `docs/AGENT-WORKFLOW.md`, excerpts of the ADRs/docs it relies on, and the full
   `git diff master...HEAD`, with bulky generated files left out and listed as left out.
   The packet ends with:

   > Review branch <name> for task <id>. Follow AGENTS.md. List concrete problems
   > with file:line, ranked by severity; say explicitly if you found none. Say which
   > claims you could not check from the packet. Focus: $ARGUMENTS

3. Run `codex exec -s read-only -C "$(git rev-parse --show-toplevel)" - < packet.md`
   (add `-m <model>` to choose one). Never put the prompt on the command line: the
   shell mangles quotes and flag-like text.
4. Verify each finding yourself (read the code, run the command). Fix the real ones;
   for ones you reject, write one line why in the session note.

Why a packet: Codex's sandbox needs bubblewrap, which cannot run on this machine yet
(`docs/AGENT-WORKFLOW.md`, "Sandbox"), so Codex cannot run `git diff` itself. Once
`bwrap --ro-bind / / --dev /dev --proc /proc --unshare-net true` succeeds, Jolyon
can use the plugin directly: `/codex:adversarial-review --base master <focus>`.
