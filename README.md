# skills

Claude Code plugins.

## review-the-project

A verified code review of any repository, published as a review page that stays current:
a short abstract first, then open bugs, known and calculated risks, and shortcomings, with
the change log last. Every finding is re-checked by an independent agent before it is
listed. When issues are fixed, the skill marks them, moves them to the change log and
republishes the page.

Ask Claude Code to "review the project", or "update the review" after fixes.

### Install

```
/plugin marketplace add hmstautland/skills
/plugin install review-the-project@hms-skills
```

Requires Python 3 (for the page builder) and Claude Code's Artifact tool for publishing.
The review data is kept in the reviewed project at `.review/review.json`.
