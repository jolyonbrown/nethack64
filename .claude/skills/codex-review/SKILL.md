---
description: Ask Codex (via the codex MCP server) for an independent, read-only review of the current branch diff or a design question, then weigh its findings.
argument-hint: "[what to review]"
disable-model-invocation: true
---

# Codex review

1. Collect context: `git diff main...HEAD --stat`, the task id from `docs/TASKS.md`,
   and any ADR touched.
2. Call the `codex` MCP tool with `sandbox: "read-only"`, `approval-policy: "never"`,
   `cwd` = repo root, and a prompt like:

   > Review branch <name> for task <id> in this repo. Follow AGENTS.md. Check the
   > review checklist in docs/AGENT-WORKFLOW.md. Run the read-only checks you can
   > (git diff, reading files). List concrete problems with file:line, ranked by
   > severity; say explicitly if you found none. Focus: $ARGUMENTS

3. Verify each finding yourself (read the code, run the command). Fix the real ones;
   for ones you reject, write one line why in the session note.
4. Follow-ups in the same conversation use `codex-reply` with the returned `threadId`.

If the MCP server is unavailable, say so and suggest Jolyon run `codex` in a terminal
on the branch with the same prompt.
