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

A **Tasks** link on the review opens a task board with Backlog, To do, In progress and Done
columns. Every open finding is a card, next to improvements the review suggests for this
project (rate limiting on an exposed endpoint, a context size budget, security
hardening). Fixed findings move to Done when the review is updated. Anyone can drag cards
and add their own tasks; those changes stay in their browser until they use "Copy my
changes" and give the text to their agent, which writes them into the review.

If the repository is on GitHub, the agent then offers to create a GitHub project named
after the review date (e.g. "Review 17 October 2026") with one issue per open finding and
suggested task, in the same columns as the board. Later updates close the issues of fixed
findings, open issues for new ones, and leave moves made on GitHub alone. This needs the
GitHub CLI with project access: `gh auth login`, then `gh auth refresh -s project`.

Ask your agent to "review the project", or "update the review" after fixes.

The plugin also installs a prompt hook. When a prompt asks for a review or audit, the agent
asks whether to run this skill or give a quicker inline answer. If the project already has a
`.review/review.json`, review prompts offer to update that page instead, and fix prompts
offer it once the fix is done. Prompts in Norwegian ("gjennomgang", "fiks") are matched too.

### Install in Claude Code

```
/plugin marketplace add hmstautland/skills
/plugin install review-the-project@hms-skills
```

### Install in GitHub Copilot (VS Code)

VS Code installs Claude-format plugins directly, including the hook. Turn on
`chat.plugins.enabled`, add this marketplace in settings, then install
`review-the-project` from the Extensions view (search `@agentPlugins`):

```json
"chat.plugins.enabled": true,
"chat.plugins.marketplaces": ["hmstautland/skills"]
```

To use only the skill, without the hook, copy
`plugins/review-the-project/skills/review-the-project` to `.github/skills/` in a project or
to `~/.copilot/skills/`. VS Code's agent hooks are still in preview.

Copilot has no equivalent of Claude's Artifact tool, so the pages are built into
`.review/site/` in the project; open `.review/site/index.html` in a browser, or host the
folder anywhere that serves static files.

### Requirements

Python 3 (for the page builder), and the GitHub CLI for the optional GitHub project. The
review data is kept in the reviewed project at `.review/review.json`.
