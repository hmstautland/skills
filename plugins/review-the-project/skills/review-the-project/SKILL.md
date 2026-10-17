---
name: review-the-project
description: Verified code review of a whole repository, published as a living review page (abstract, bugs, known and calculated risks, shortcomings, change log) with a task board, kept up to date as fixes land. Use whenever the user asks to review, audit or health-check a project or codebase, look for bugs or unused code across a repo, asks "is this as good as it could be", wants an existing review page updated after fixes ("update the review", "mark that as fixed", "refresh the review artifact"), or pastes task board changes ("apply these task board changes to the review"). Also use after fixing issues from an earlier review in the same project, to keep its status current.
---

# Review the project

Produce a review the owner can act on and share: a short abstract first, then the open
bugs, the known and calculated risks, and the shortcomings, with the change log last. The
page always reflects the **current** state — fixed issues leave the issue lists and appear
only in the change log, and every count is a count of what is still open. A second page,
the task board, turns the findings and suggested improvements into cards in Backlog,
To do, In progress and Done.

Three modes:
- **New review** — no `.review/review.json` in the project yet (or the user wants a fresh one).
- **Update** — the file exists: fixes landed, the user asks to refresh the page, or you just
  fixed something a review listed. Updating is the common case; do it without being asked
  after you fix a reviewed issue, and say that you did.
- **Board changes** — the user pastes text from the task board's "Copy my changes" button.
  Apply it as described in `references/data-format.md` (Board changes), then rebuild and
  publish as in Update.

## Works in any coding agent

These instructions name tools by what they do. Use whatever your agent has:

| Need | Claude Code | Other agents (e.g. GitHub Copilot) |
|---|---|---|
| Ask the user a question | AskUserQuestion | Ask in chat |
| Parallel reviewers and verifiers | Agent (or Workflow, if the user opted in) | Subagents if available; otherwise one area at a time, and verify each finding in a separate pass that tries to disprove it |
| Publish the pages | Artifact tool | No hosting: build into the project (see below) and give the user the path |

## Files in this skill

- `scripts/build_page.py <review.json> <out.html>` — validates the data and builds the
  review page plus `tasks.html` (the task board) next to it.
- `assets/page_template.html`, `assets/tasks_template.html` — the two pages, rendered from
  the data. Don't hand-edit the built HTML: change the data and rebuild, so the next
  update doesn't lose your edit.
- `references/data-format.md` — the review.json schema, including tasks and board changes.
  Read before writing or editing the file.
- `references/review-process.md` — scouting, reviewer/verifier prompts and schemas, and how
  to turn results into review.json. Read for a new review.

## New review

1. Read `references/review-process.md` and follow it: scout, split into areas, fan out
   reviewers, verify every finding independently, run a completeness critic, then propose
   tasks.
   Scale to the ask: "quick look" → 2–3 reviewers; "full review/audit" → 5–7 plus the sweep
   and critic.
2. Write `.review/review.json` (see `references/data-format.md`). Mention the location to
   the user in one line; if they want it elsewhere (or gitignored), move it.
3. Build and publish (below).
4. In chat, keep it short: the abstract, the top priorities, decisions the user needs to
   make, and the link. The pages hold the detail.

## Update

1. Read `.review/review.json` and `git diff`/`git log` since the last update (or the fixes
   you just made). Re-read the code behind each finding you are about to change — a status
   is a claim about the code, so check it rather than trusting memory.
2. For each affected finding set `status` (`fixed` / `partly`), `status_note` (what was done;
   for partly, what is still open) and `status_date`. For `partly`, also rewrite the title
   and severity to the part that is still open (see `references/data-format.md`).
3. Add one `changelog` entry per coherent change, listing those findings under `fixes` /
   `partly`, with the files touched.
4. New problems you introduced or noticed (including deliberate trade-offs) become new
   findings with fresh ids — `kind: "risk"` with `verification: "accepted"` for trade-offs.
5. Update `tasks`: move finished ones to `done` with a `done_note`, drop the `findings` ids
   that are now fixed, and add new suggestions the changes made relevant.
6. Rewrite `abstract` and `priorities` for the new state, and set `updated` to today.
   Stale summaries are the main way a review page starts lying; the counts update
   themselves, but the prose doesn't. The abstract describes only the current state —
   don't recount the fixes there; that history lives in the change log.
7. Build and publish again (to the same `artifact_url`, where there is one).

## Build and publish

Build into a folder of its own, with the review page named `index.html`, so the task
board's "Back to the review" link and the review's "Tasks" link find each other:

```
python3 <skill-dir>/scripts/build_page.py .review/review.json <dir>/index.html
```

If it reports inconsistencies, fix the data (don't bypass the check): a fixed finding with
no change-log entry means the reader can't see what happened to it.

**With the Artifact tool** (Claude Code): `<dir>` is a folder in the scratchpad. Publish
`<dir>/index.html` with `files: {"tasks.html": "<dir>/tasks.html"}` so the board is
published with it. First publish: pass `icon: "code"` and save the returned URL as
`artifact_url` in review.json. Later: publish to that `url`, again with `files`. When the
change is small, say in one line what changed on the page. The page starts private; remind
the user once that others can open it only after it is shared from its Share menu.

**Without it**: build to `.review/site/` and give the user the path to
`.review/site/index.html` to open in a browser. Both pages are self-contained HTML, so
the folder can also be hosted anywhere static files can be served.

## Writing guidance

- Write for someone who hasn't seen the conversation: plain words, what fails and how,
  file:line for every claim.
- Severity reflects the real deployment (single-user local tool vs public service). Say
  which in `method`.
- "Verified" must mean something: every finding on the page was re-checked by an
  independent reviewer; findings that didn't survive are simply left out. Don't publish
  counts of rejected findings — they mean nothing to a reader.
- Tasks are specific to this project. "Add rate limiting" belongs only when there is an
  endpoint that can be abused; say which one and why.
- Line numbers refer to `commit`. After fixes, files move; that's expected and noted in
  the footer. When you do a fresh review later, update `commit`.
- Respect the project's own rules (CLAUDE.md, AGENTS.md, copilot-instructions.md etc.): a
  review never edits code unless the user asks for fixes, and anything that changes a
  cross-file contract is presented as a decision with options and a recommendation, not
  done silently.
