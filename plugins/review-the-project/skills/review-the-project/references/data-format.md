# review.json format

One file holds the whole review and its history. The page is generated from it
(`scripts/build_page.py`), so the file — not the page — is what you edit when
something changes. Keep it in the project at `.review/review.json` unless the
user picked another place.

```json
{
  "project": "my-app",
  "title": "my-app Code Review",
  "repo_url": "https://github.com/owner/my-app",
  "commit": "<full commit hash the line numbers refer to>",
  "reviewed": "2026-01-10",
  "updated": "2026-01-14",
  "artifact_url": "<URL returned by the first publish>",

  "abstract": ["Paragraph 1 …", "Paragraph 2 …"],

  "priorities": [
    {"title": "Uploads can overwrite other users' files", "text": "One or two sentences on impact.", "findings": [7]}
  ],

  "findings": [
    {
      "id": 7,
      "kind": "bug",
      "severity": "high",
      "area": "Uploads",
      "file": "src/uploads/save.py",
      "line": 48,
      "title": "Uploaded file names are used unchanged, so same-named uploads overwrite each other",
      "detail": "What is wrong, with the concrete failure scenario.",
      "suggestion": "How to fix it.",
      "design": false,
      "verification": "verified",
      "verification_note": "What the second reviewer checked and found.",
      "corrected": "",
      "also_reported_by": ["Unused-code sweep"],
      "status": "open",
      "status_note": "",
      "status_date": "",
      "column": "backlog"
    }
  ],

  "tasks": [
    {
      "id": 1,
      "title": "Add rate limiting to the login endpoint",
      "text": "Why it matters and where to start.",
      "area": "API",
      "files": ["src/api/auth.py"],
      "effort": "small",
      "findings": [7],
      "column": "backlog",
      "source": "review",
      "done_note": ""
    }
  ],

  "decisions": [
    {"title": "Where uploads are stored", "options": "A: … B: …", "recommendation": "A, because …", "status": "open"}
  ],

  "method": ["Five reviewers covered …", "Baseline: 240 tests passed …"],
  "summaries": [{"area": "uploads", "text": "Reviewer's overall conclusion …"}],

  "changelog": [
    {
      "date": "2026-01-14",
      "title": "Uploads get unique names",
      "detail": "What changed, in a sentence or three.",
      "files": ["src/uploads/save.py"],
      "fixes": [7],
      "partly": [12]
    }
  ]
}
```

## Fields

**Top level**
- `reviewed`: date of the review itself. `updated`: date of the last change to
  the file. Both `YYYY-MM-DD`. Set `updated` every time you edit the file.
- `commit`: the commit the line numbers refer to. Source links point there.
  Leave `repo_url` empty for a repo without a browsable remote; links are then omitted.
- `artifact_url`: the published page. Republish to it instead of creating a new page.
- `abstract`: 1–3 short paragraphs on the *current* state: what the project is,
  overall health, the biggest open problems. Rewrite it whenever fixes change the
  picture — it must never describe problems that are already fixed. Keep history out
  of it: no "since the last review", "N issues fixed" or "X was resolved"; what changed
  and when belongs in `changelog`. Read it as if the project were being reviewed for
  the first time today.
- `priorities`: the 3–6 open problems to fix first, ranked. A priority whose
  findings are all fixed is hidden automatically; remove it from the file when you
  next touch it, and promote the next open problem.

**Findings** — one per distinct issue (merge duplicates; list the other
reviewers in `also_reported_by`).
- `kind` decides the section:
  - `bug` → **Bugs**
  - `security` → **Known and calculated risks**
  - `risk` → **Known and calculated risks**, labelled *Accepted risk*: a trade-off made
    on purpose (in-memory state lost on restart, a broad approval that was chosen…).
    These have `verification: "accepted"` and say in `detail` why it was accepted.
  - `unfinished`, `improvement`, `dead-code` → **Shortcomings**
- `severity`: `high` / `medium` / `low`, judged for how the project is actually deployed.
- `design`: true when the fix changes a contract used across files.
- `verification`: `verified` (the second reviewer confirmed it) or `corrected`
  (confirmed, with details corrected — put the corrected statement in
  `corrected`). Findings the second reviewer disproved are not added at all.
- `status`: `open`, `partly` or `fixed`. For `partly` and `fixed`, `status_note`
  is required: what was done, and for `partly`, what is still open. `status_date`
  is the date of that change.
- When a finding becomes `partly`, rewrite its `title` and `severity` to describe
  only what is still open, and end `status_note` with
  "Originally reported as: <old title>". A partly fixed finding titled after the
  part that was fixed makes the page report problems that no longer exist.
- Don't merge two reports as duplicates if fixing one leaves part of the other
  open; keep them separate so each can carry its own status.
- Never delete a fixed finding: the change log shows it.

- `column` (optional): where the finding sits on the task board — `backlog` (default),
  `todo` or `doing`. Fixed findings are always in Done and partly fixed ones default to
  `doing`, so set it only when the owner planned or started work. A finding is never put
  in Done by `column`; only `status: "fixed"` does that.

**Tasks** — the task board (`tasks.html`) shows every finding except accepted risks as a
card, plus these tasks. They are improvements that aren't findings: hardening and
capacity work the code doesn't have yet (rate limiting, request size limits, a context
or token budget, backups, monitoring), missing tests on risky paths, and tasks the owner
added. Each needs a concrete reason grounded in this project, not generic best practice.
- `id`: stable integer, never reused. `title`, `text` required (`text` says why and
  where to start). `area`, `files` and `effort` (`small` / `medium` / `large`) optional.
- `findings`: related finding ids, when the task would also address them.
- `column`: `backlog` (default), `todo`, `doing` or `done`. When a task is done, set
  `done_note` to what was done; don't delete it.
- `source`: `review` (proposed by the review) or `owner` (added by a person).

**Board changes** — the board saves moves and added tasks only in the viewer's browser.
Its "Copy my changes" button gives text starting "Apply these task board changes to the
review", with `board_changes.moves` (`finding` or `task` id, `from`, `to`) and
`board_changes.added` (`title`, `text`, `column`). To apply it: set `column` on each
moved finding or task; add each added task with a fresh id and `source: "owner"`. A
finding moved to Done is a claim that it is fixed: check the code, then mark it
`fixed` (with a change-log entry) or leave it in `doing` and say why.

**Change log** — one entry per coherent change. `fixes` lists findings that are
now `fixed`, `partly` those now `partly`. The builder refuses to build when a
fixed or partly-fixed finding is not listed in some entry, or an entry lists a
finding whose status doesn't match.

## Text formatting

Text fields support `` `code` `` spans, `**bold**`, blank-line paragraphs and
`- ` bullet lists. Everything is rendered as text, never as HTML.
