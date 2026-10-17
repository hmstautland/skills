---
name: review-the-project
description: Verified code review of a whole repository, published as a living review page (abstract, bugs, known and calculated risks, shortcomings, change log) that is kept up to date as fixes land. Use whenever the user asks to review, audit or health-check a project or codebase, look for bugs or unused code across a repo, asks "is this as good as it could be", or wants an existing review page updated after fixes ("update the review", "mark that as fixed", "refresh the review artifact"). Also use after fixing issues from an earlier review in the same project, to keep its status current.
---

# Review the project

Produce a review the owner can act on and share: a short abstract first, then the open
bugs, the known and calculated risks, and the shortcomings, with the change log last. The
page always reflects the **current** state — fixed issues leave the issue lists and appear
only in the change log, and every count is a count of what is still open.

Two modes:
- **New review** — no `.review/review.json` in the project yet (or the user wants a fresh one).
- **Update** — the file exists: fixes landed, the user asks to refresh the page, or you just
  fixed something a review listed. Updating is the common case; do it without being asked
  after you fix a reviewed issue, and say that you did.

## Files in this skill

- `scripts/build_page.py <review.json> <out.html>` — validates the data and builds the page.
- `assets/page_template.html` — the page; generic, rendered from the data. Don't hand-edit
  the built HTML: change the data and rebuild, so the next update doesn't lose your edit.
- `references/data-format.md` — the review.json schema. Read before writing or editing the file.
- `references/review-process.md` — scouting, reviewer/verifier prompts and schemas, and how
  to turn results into review.json. Read for a new review.

## New review

1. Read `references/review-process.md` and follow it: scout, split into areas, fan out
   reviewers, verify every finding independently, run a completeness critic.
   Scale to the ask: "quick look" → 2–3 reviewers; "full review/audit" → 5–7 plus the sweep
   and critic. Use the Workflow tool only when the user opted into multi-agent orchestration;
   otherwise parallel Agent calls.
2. Write `.review/review.json` (see `references/data-format.md`). Mention the location to
   the user in one line; if they want it elsewhere (or gitignored), move it.
3. Build and publish (below).
4. In chat, keep it short: the abstract, the top priorities, decisions the user needs to
   make, and the link. The page holds the detail.

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
5. Rewrite `abstract` and `priorities` for the new state, and set `updated` to today.
   Stale summaries are the main way a review page starts lying; the counts update
   themselves, but the prose doesn't. The abstract describes only the current state —
   don't recount the fixes there; that history lives in the change log.
6. Build and publish to the same `artifact_url`.

## Build and publish

```
python3 <skill-dir>/scripts/build_page.py .review/review.json <scratchpad>/review.html
```

If it reports inconsistencies, fix the data (don't bypass the check): a fixed finding with
no change-log entry means the reader can't see what happened to it.

Publish the built file with the Artifact tool. First publish: pass `icon: "code"` and save the
returned URL as `artifact_url` in review.json. Later: publish to that `url`. When the
change is small, say in one line what changed on the page. The page starts private; remind
the user once that others can open it only after it is shared from its Share menu.

## Writing guidance

- Write for someone who hasn't seen the conversation: plain words, what fails and how,
  file:line for every claim.
- Severity reflects the real deployment (single-user local tool vs public service). Say
  which in `method`.
- "Verified" must mean something: every finding on the page was re-checked by an
  independent agent; findings that didn't survive are simply left out. Don't publish
  counts of rejected findings — they mean nothing to a reader.
- Line numbers refer to `commit`. After fixes, files move; that's expected and noted in
  the footer. When you do a fresh review later, update `commit`.
- Respect the project's own rules (CLAUDE.md etc.): a review never edits code unless the
  user asks for fixes, and anything that changes a cross-file contract is presented as a
  decision with options and a recommendation, not done silently.
