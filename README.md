# skills

Claude Code plugins.

## Development setup

Enable the repository's pre-commit hook once after cloning:

```sh
git config core.hooksPath .githooks
```

The hook increments the patch version in the affected plugin's `.claude-plugin/plugin.json`
whenever a staged change touches `plugins/`, and stages the updated manifest automatically.

## review-the-project

A verified code review of any repository, published as a review page that stays current:
a short abstract first, then open bugs, known and calculated risks, and shortcomings, with
the change log last. Every finding is re-checked by an independent agent before it is
listed. When issues are fixed, the skill marks them, moves them to the change log and
republishes the page.

Ask Claude Code to "review the project", or "update the review" after fixes.

The plugin also installs a prompt hook. When a prompt asks for a review or audit, Claude
asks whether to run this skill or give a quicker inline answer. If the project already has a
`.review/review.json`, review prompts offer to update that page instead, and fix prompts
offer it once the fix is done. Prompts in Norwegian ("gjennomgang", "fiks") are matched too.

### Install

```
/plugin marketplace add hmstautland/skills
/plugin install review-the-project@hms-skills
```

Requires Python 3 (for the page builder) and Claude Code's Artifact tool for publishing.
The review data is kept in the reviewed project at `.review/review.json`.
