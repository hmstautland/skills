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

Four modes:
- **New review** — no `.review/review.json` in the project yet.
- **Update** — the file exists: fixes landed, the user asks to refresh the page, or you just
  fixed something a review listed. Updating is the common case; do it without being asked
  after you fix a reviewed issue, and say that you did. An update checks the changes since
  the last update; it doesn't re-scan the whole project.
- **Re-review** — the file exists and the user asks for a full review again ("review the
  project again", "a fresh review"). Run the whole review and merge it into the existing
  file and page (below), so the change log shows what was fixed and what is new since the
  last review. Start over from an empty file only if the user explicitly asks to discard
  the history, and even then publish to the same page.
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
- `scripts/sync_github.py <review.json>` — mirrors the task board to a GitHub project with
  one issue per card (see GitHub project below). `--dry-run` prints the plan.
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
5. Offer the GitHub project (below) if the repo is on GitHub.

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
8. If review.json has a `tracker`, sync it (below).

## Re-review

1. Read `references/review-process.md` and run it as for a new review, against the current
   commit. Give the reviewers the titles of the open findings so they report each one again
   if it still holds, rather than treating it as new.
2. Merge, as described in `references/review-process.md` (Merging a re-review): a result that
   matches an existing finding keeps its id; an open finding that no reviewer reproduced is
   re-checked and marked `fixed` if it is gone; everything else is new, with a fresh id.
3. Add one `changelog` entry for the re-review, e.g. "Re-review at `<short commit>`", with the
   fixed findings under `fixes` and the new ones under `found`.
4. Set `commit` and `reviewed` to the new review, `updated` to today, then continue from
   Update step 5 (tasks, abstract and priorities, build and publish, tracker sync). The
   tracker stays the same GitHub project: fixed findings close their issues and new ones
   get issues.

## One page per project

A project has one review page, at `artifact_url`, and its change log is the history. Always
publish to that URL. If you can't (the page was deleted, or the user can't edit it) or you
find an earlier review page for the same project (an older `artifact_url` the user mentions,
or one listed among the user's artifacts with the same project's review title), then once
the current page is published, ask the user whether to delete the older page, saying that
its findings are covered by the change log. Delete it only when they confirm; deleting
can't be undone and breaks the link for anyone it was shared with. Without the Artifact
tool there is nothing to delete: the build always replaces `.review/site/`.

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

## GitHub project

After the first review is published, if `origin` is a GitHub repo, ask the user whether
to create a GitHub project for it, named after the review date (e.g. "Review 17 October
2026"), with one issue per open finding and suggested task, placed in the same columns as
the task board. Creating issues is visible to everyone with access to the repo, so ask
first and say how many issues it would create (`--dry-run` tells you). Offer:
- all open findings and tasks,
- only high and medium findings plus tasks (`--min-severity medium`), or
- no project.

Then run, from the project root:

```
python3 <skill-dir>/scripts/sync_github.py .review/review.json [--min-severity medium] [--no-tasks]
```

It needs the GitHub CLI logged in with project access (`gh auth login`, then
`gh auth refresh -s project`); if it stops on missing access, tell the user that command.
It writes the project and the issue numbers into review.json, so rebuild and republish
the pages afterwards: both then link to the project and to each issue. If it stops part
way, run it again; it continues without creating duplicates.

**On later updates**, when review.json has a `tracker`: run it with `--dry-run`, tell the
user in one line what it will do (new issues, issues to close, cards to move) and run it
when they agree. It closes the issues of fixed findings and done tasks with a comment,
creates issues for new ones, and only moves a card on GitHub when the review's column
changed, so moves made on GitHub are kept. It reports issues someone closed on GitHub
that the review still lists as open: check the code for each, then mark the finding fixed
(with a change-log entry) or tell the user it is still open.

For a repo hosted elsewhere (GitLab, Azure DevOps, Bitbucket), say that only GitHub is
supported for now; don't improvise issue creation with another tool unless the user asks.

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
