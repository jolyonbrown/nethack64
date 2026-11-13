# Development diary

The story of porting NetHack 3.4.3 to the Commodore 64, told as we go. Each
entry is written to stand alone as a blog post for three kinds of reader: C64
fans and demosceners, NetHack players, and people curious about how a project
run largely by AI agents works in practice.

The diary is not the project record. Measured facts live in
`docs/NETHACK-SURVEY.md` and `docs/OSCAR64-COMPAT.md`, decisions in
`docs/decisions/`, and session handoffs in `docs/sessions/`. The diary tells
the story and points at those for the evidence.

## Entries

| # | Date | Title | Status |
|---|---|---|---|
| 1 | 2026-11-12 | NetHack on the C64, part 1: a 64 KB machine and a compiler that wanted 10 GB | Draft, awaiting Jolyon's review (not yet in the public repository) |

## Who writes it, and when

- **When.** At a milestone (a phase finished, the first time something runs),
  or after a discovery that surprised us, or a fix that was hard to get. Not
  on a schedule, and not once per session.
- **Who.** The lead agent drafts the entry, in the first person plural, with
  "I" kept for its own calls and mistakes.
- **Review.** Jolyon reviews every entry before anything is published. An
  entry stays `draft: true` until Jolyon approves it. Agents do not publish,
  post or link entries anywhere outside this repository.
- **The repository is public.** Anything pushed to GitHub can be read by
  anyone, and `draft: true` does not hide it. A draft entry therefore stays
  uncommitted, or on a branch that has not been pushed, until Jolyon approves
  it. Pushing it is Jolyon's decision.

## Conventions

**Files.** One Markdown file per entry, named `NNNN-slug.md`: a four-digit
number, then a short lower-case slug. Numbers are never reused, and the file
name stays the same if the title changes. Images go in `docs/diary/img/`,
named after what they show, with alt text that describes the picture for
someone who cannot see it.

**Front matter.** Every entry starts with YAML front matter, so a static-site
generator can pick it up unchanged:

| Field | Meaning |
|---|---|
| `title` | The post title. The body has no top-level heading; the title comes from here |
| `date` | The date the entry describes up to, `YYYY-MM-DD` |
| `entry` | The entry number, matching the file name |
| `author` | Who drafted it |
| `summary` | Two or three sentences, usable as the post's teaser |
| `tags` | A short list, lower-case |
| `draft` | `true` until Jolyon approves the entry |
| `reviewed_by` | Added only when Jolyon approves the entry; absent until then |

**Writing.**

- British spelling.
- Open with something that happened, not a status line.
- Give each of the three readers at least one thing that is theirs.
- Explain a term the first time it appears (REU, EasyFlash, KERNAL, banking,
  ADR, fork, pull request, upstream, subagent, run-length coding). A NetHack
  player should not need to know the C64, nor the reverse, and neither should
  need to know GitHub.
- Short paragraphs. At most two tables and one or two short code blocks. The
  "Numbers so far" table counts as one of the two.
- Failures are told as well as wins: what broke, what we got wrong, what is
  still not right.
- No time estimates and no promised dates.
- Say plainly what does and does not run. Never claim something works on the
  C64 unless it has been run in VICE, and say when it has only been run there.
- Say who did what. Agents ran the tests and wrote the code; Jolyon directed
  and decided. Quote Jolyon only in Jolyon's exact words.
- Be fair to other projects and their maintainers.

**Facts.** Every number and claim must be checkable. Each entry ends with a
"Numbers so far" table and a "Notes and sources" section giving the file,
commit id, test or URL behind what it says. Links into the repository are
relative paths (`../PLAN.md`, `../../tests/...`), so they work wherever the
repository is read. If a source is outside the repository (a session
transcript, a system log), or is not committed yet, the notes say so.

**Never include.** Email addresses, tokens, session links, the build
machine's hostname, links to private pages, or personal details about anyone
beyond what they have chosen to say for publication.

## Adding an entry

1. Copy the front matter from the latest entry and take the next number.
2. Gather the facts first, from the repository and recorded results, and check
   each one against its source.
3. Write the entry, then add its row to the table above: the title as plain
   text while the entry is unpublished, as a link once it is pushed.
4. Leave `draft: true`, do not commit to a pushed branch, and tell Jolyon it
   is ready for review.
