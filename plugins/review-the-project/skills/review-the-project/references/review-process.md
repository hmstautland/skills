# Running the review

Use this when doing a new review (not when updating an existing one).

## 1. Scout (yourself, inline)

Cheap facts the reviewers need, so they don't each rediscover them:
- `git status`, `git log --oneline -5`, current commit hash, remote URL.
- Tracked files with line counts (`git ls-files | xargs wc -l`), excluding vendored code, models, binaries.
- Test baseline: run the suite the way the project documents it and record pass/fail counts.
  If the documented command fails but another works, that is itself a finding.
- Static analysis that is already available (pyflakes/vulture, eslint, `go vet`, `cargo clippy` …).
  Record which hits are false positives (e.g. route handlers registered by decorators,
  functions referenced by string in a registry).
- Project instructions (CLAUDE.md, README, CONTRIBUTING) — the reviewers get CLAUDE.md
  automatically; name any rule a reviewer specifically needs.

Then split the code into 4–7 **areas** of similar size along real boundaries (feature
folders, layers). Always add two cross-cutting reviewers: an **unused-code sweep** and,
after the first round, a **completeness critic**.

## 2. Fan out

In Claude Code: if the user opted into multi-agent orchestration (or ultracode is on), use
the Workflow tool: `pipeline(areas, review, verifyEachFinding)` then a critic agent whose
findings are verified too. Otherwise use parallel Agent calls — one per area — and then one
verifier agent per batch of findings.

In other agents: use subagents the same way if the agent has them. If it doesn't, review
the areas one after another, then verify the findings in a separate pass using the
verifier prompt below, taking the verifier's side: try to disprove each finding from the
code rather than re-reading your own reasoning.

Either way: reviewers are read-only and must not edit files.

### Shared preamble (prepend to every reviewer and verifier prompt)

```
You are reviewing the <project> repo at <path>. READ-ONLY: do not edit, create or delete
files, and do not commit. You may run read-only commands (grep, imports, the test suite).
<how to activate the environment>.

Baseline already established: <test result>. Static analysis: <hits, with known false positives>.

Rule for "unused" findings: if something looks unused but has clear intent (a config
table, a feature flag, a registry entry, a stub), classify it as UNFINISHED (decide:
implement or remove), not as dead code. Only truly dead code is "dead-code".

Report only what you verified by reading the code. Give repo-relative paths and line
numbers. For a bug, give a concrete failure scenario (input/state → wrong behaviour).
No style nits; fewer, real findings. Mark design=true if the fix changes a contract used
across files (endpoint, event shape, registry, config, storage).
```

### Reviewer output schema

```json
{"type": "object", "properties": {
  "summary": {"type": "string", "description": "3-8 sentence assessment of the area"},
  "findings": {"type": "array", "items": {"type": "object", "properties": {
    "kind": {"type": "string", "enum": ["bug", "security", "dead-code", "unfinished", "improvement"]},
    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
    "file": {"type": "string"}, "line": {"type": "integer"},
    "title": {"type": "string"},
    "detail": {"type": "string", "description": "what is wrong + concrete failure scenario"},
    "suggestion": {"type": "string"},
    "design": {"type": "boolean"}},
    "required": ["kind", "severity", "file", "line", "title", "detail", "suggestion", "design"]}}},
 "required": ["summary", "findings"]}
```

### Area prompt

Name the files, then list what to look for in *that* area — the risks specific to it
(auth and session handling for a web layer, path traversal for file tools, parsing edge
cases for date handling, blocking calls in async handlers, injection in subprocess calls,
XSS where text reaches `innerHTML`, races on shared state …). The more specific the
checklist, the better the findings.

The **unused-code sweep** checks every function, module, config value, template, static
file and dependency for real usage (imports, string references, decorators, template
includes, script tags, tests, CI, docs), and for each registered plugin/tool/command
whether it is reachable and working, with a keep / finish / remove recommendation.

### Verifier prompt (one per finding)

```
You are an adversarial verifier. A reviewer of the "<area>" area reported:
kind / severity / location / title / detail / suggestion: <…>

<lens>
Default to "refuted" if after genuine investigation you cannot substantiate it. Use
"partially" if the core issue is real but details (severity, location, mechanism) are
wrong — then give the corrected statement.
```

Lens by kind:
- bug: trace the actual path; can the triggering state occur; does a guard elsewhere
  prevent it; is it tested? Demonstrate with a read-only snippet where possible.
- security: is it reachable by an attacker or by an automated component, given auth and
  permission rules? Be concrete about the exploit path or why none exists.
- dead-code: search exhaustively for usages, including string references and templates;
  could it be an unfinished feature?
- unfinished: is it actually wired up and working?
- improvement: is the premise about current behaviour true; would the suggestion break anything?

Verifier schema: `{"verdict": "confirmed|partially|refuted", "reason": "...", "corrected": "..."}`.

### Completeness critic

After the first round, give one agent the list of surviving finding titles and ask what
was missed: cross-file contract mismatches (payloads vs the code consuming them), files
nobody looked at closely, test gaps on the riskiest paths, docs that no longer match the
code. Verify its findings the same way.

## 3. Propose tasks

After verification, one more agent (or pass) proposes improvement tasks for the board:
work the project would benefit from that isn't a defect in existing code. Give it the
scout facts, the reviewers' summaries and the surviving finding titles. Ask for 4–10
tasks, each with a concrete reason in *this* code, for example:
- rate limiting or request size limits on an endpoint that can be abused,
- a context, token or memory budget where input can grow without bound,
- security hardening (auth on an admin route, secrets out of the repo, dependency pinning),
- tests for the riskiest untested path, backups, logging or monitoring that is missing.

Drop generic advice that would apply to any project. Where a task would also resolve
findings, list their ids in `findings`. Tasks are suggestions, so they are not verified
like findings, but each must name the files or behaviour it is about.

Task schema: `{"title", "text", "area", "files": [], "effort": "small|medium|large", "findings": []}`.

## 4. Synthesize into review.json

- Drop refuted findings entirely. `confirmed` → `verification: "verified"`;
  `partially` → `"corrected"` with the corrected statement in `corrected`.
- Merge duplicates (same root cause found by several reviewers) into one finding; keep
  the clearest write-up and list the other areas in `also_reported_by`.
- Number findings with stable integer ids. Never renumber later — ids are the links.
- Add `risk` findings for trade-offs you know were made deliberately (from docs, code
  comments or the conversation), with `verification: "accepted"`.
- Write the abstract and priorities yourself, from the verified findings. Include an
  answer to any specific question the user asked (e.g. "is X as good as it could be?").
- `method`: areas covered, how many agents, baseline test result, severity context
  (e.g. "judged for a single-user local app"), anything not covered.
- `summaries`: each reviewer's `summary`, so readers can see the overall conclusions.
- `tasks`: the proposed tasks with stable integer ids, `column: "backlog"` and
  `source: "review"`.
