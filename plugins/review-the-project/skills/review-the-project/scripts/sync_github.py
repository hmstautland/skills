#!/usr/bin/env python3
"""Mirror the review's task board to a GitHub project with one issue per card.

    python3 sync_github.py <review.json> [--repo owner/name] [--title "Review 17 October 2026"]
                           [--min-severity low|medium|high] [--no-tasks] [--dry-run]

First run (no "tracker" in review.json): creates a GitHub project, links it to the
repo, sets its Status column to Backlog / To do / In progress / Done, and creates one
issue per open finding (accepted risks excluded) and per task that isn't done.

Later runs: creates issues for new findings and tasks, closes the issues of fixed
findings and done tasks with a comment, and moves an issue's Status only when the
review's column changed since the last sync, so moves made on GitHub are kept. Issues
closed on GitHub while the review still lists them as open are reported, not reopened.

The review is the source of truth and nothing is ever deleted on GitHub. Issue numbers
are written back into review.json after each issue, so a failed run can be re-run
without creating duplicates. --dry-run prints the plan and changes nothing.

Needs the GitHub CLI (gh), logged in with the "project" scope:
    gh auth login && gh auth refresh -s project
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

COLUMNS = ["backlog", "todo", "doing", "done"]
COLUMN_NAMES = {"backlog": "Backlog", "todo": "To do", "doing": "In progress", "done": "Done"}
# GitHub's default Status options, used if the Status field can't be changed.
DEFAULT_STATUS = {"backlog": None, "todo": "Todo", "doing": "In Progress", "done": "Done"}
SEV_RANK = {"high": 0, "medium": 1, "low": 2}
KIND_LABEL = {"bug": "bug", "security": "security", "unfinished": "shortcoming",
              "improvement": "shortcoming", "dead-code": "shortcoming"}
LABELS = {
    "review": ("1d5f8a", "From the code review"),
    "severity: high": ("b42318", "Review severity"),
    "severity: medium": ("a64b00", "Review severity"),
    "severity: low": ("5d6878", "Review severity"),
    "bug": ("d73a4a", "Something isn't working"),
    "security": ("b60205", "Security exposure"),
    "shortcoming": ("c5def5", "Unfinished, dead code or design gap"),
    "suggestion": ("0e8a16", "Improvement suggested by the review"),
}
STATUS_OPTIONS_MUTATION = """
mutation($field: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
  updateProjectV2Field(input: {fieldId: $field, singleSelectOptions: $options}) {
    projectV2Field { ... on ProjectV2SingleSelectField { id options { id name } } }
  }
}"""


class GhError(RuntimeError):
    pass


def gh(*args: str, parse: bool = True, stdin: str | None = None):
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, input=stdin)
    if proc.returncode:
        raise GhError(f"gh {' '.join(args[:3])} … failed: {proc.stderr.strip() or proc.stdout.strip()}")
    out = proc.stdout.strip()
    return json.loads(out) if parse and out else out


def repo_from_remote(cwd: Path) -> str | None:
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=cwd,
                             capture_output=True, text=True).stdout.strip()
    except OSError:
        return None
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def default_title(data: dict) -> str:
    try:
        d = date.fromisoformat(data.get("reviewed") or "")
    except ValueError:
        d = date.today()
    return f"Review {d.day} {d.strftime('%B')} {d.year}"


def finding_column(f: dict) -> str:
    if f.get("status") == "fixed":
        return "done"
    return f.get("column") or ("doing" if f.get("status") == "partly" else "backlog")


def cards(data: dict, min_sev: str, with_tasks: bool):
    """(key, record, column, is_closed, title, body, labels) for every card the tracker covers."""
    review_url = data.get("artifact_url") or ""
    for f in data.get("findings", []):
        if f.get("kind") == "risk":
            continue
        closed = f.get("status") == "fixed"
        if not f.get("issue") and (closed or SEV_RANK.get(f.get("severity"), 2) > SEV_RANK[min_sev]):
            continue
        yield (f"finding {f['id']}", f, finding_column(f), closed, f["title"], finding_body(f, data, review_url),
               ["review", f"severity: {f['severity']}", KIND_LABEL.get(f["kind"], "shortcoming")])
    if not with_tasks:
        return
    for t in data.get("tasks", []):
        col = t.get("column") or "backlog"
        closed = col == "done"
        if not t.get("issue") and closed:
            continue
        yield (f"task {t['id']}", t, col, closed, t["title"], task_body(t, data, review_url), ["review", "suggestion"])


def source_link(data: dict, file: str, line) -> str:
    loc = f"{file}:{line}" if line and line > 0 else file
    if data.get("repo_url") and data.get("commit"):
        url = f"{data['repo_url'].rstrip('/')}/blob/{data['commit']}/{file.split(':')[0]}" + (f"#L{line}" if line and line > 0 else "")
        return f"[`{loc}`]({url})"
    return f"`{loc}`"


def footer(data: dict, what: str, anchor: str, review_url: str) -> str:
    link = review_url + (f"#{anchor}" if anchor else "")
    src = f"[the code review]({link})" if review_url else "the code review"
    return f"\n\n---\n{what} from {src} of {data.get('project', 'this project')} ({data.get('reviewed', '')})."


def finding_body(f: dict, data: dict, review_url: str) -> str:
    head = [f"**Severity:** {f['severity'].capitalize()}", f"**Kind:** {f['kind']}"]
    if f.get("area"):
        head.append(f"**Area:** {f['area']}")
    parts = [" · ".join(head)]
    if f.get("file"):
        parts.append(f"**Where:** {source_link(data, f['file'], f.get('line'))}")
    if f.get("status") == "partly" and f.get("status_note"):
        parts.append(f"> **Partly fixed.** {f['status_note']}")
    parts.append(f.get("corrected") or f["detail"])
    if f.get("suggestion"):
        parts.append(f"### Suggested fix\n{f['suggestion']}")
    return "\n\n".join(parts) + footer(data, f"Finding {f['id']}", f"f{f['id']}", review_url)


def task_body(t: dict, data: dict, review_url: str) -> str:
    head = ["**Suggested improvement**"]
    if t.get("effort"):
        head.append(f"**Effort:** {t['effort']}")
    if t.get("area"):
        head.append(f"**Area:** {t['area']}")
    parts = [" · ".join(head), t["text"]]
    if t.get("files"):
        parts.append("**Files:** " + ", ".join(f"`{x}`" for x in t["files"]))
    if t.get("findings"):
        parts.append("**Related findings:** " + ", ".join(str(i) for i in t["findings"]))
    return "\n\n".join(parts) + footer(data, f"Task {t['id']}", "", review_url)


def close_comment(rec: dict) -> str:
    note = rec.get("status_note") or rec.get("done_note") or ""
    return ("Fixed according to the code review." if "status_note" in rec else "Done according to the code review.") + (f"\n\n{note}" if note else "")


class Project:
    """The GitHub project: its node id, Status field and column → option id map."""

    def __init__(self, owner: str, number: int):
        self.owner, self.number = owner, number
        self.id = self.field = None
        self.options: dict[str, str | None] = {}

    def load(self, set_columns: bool) -> list[str]:
        notes = []
        self.id = gh("project", "view", str(self.number), "--owner", self.owner, "--format", "json")["id"]
        fields = gh("project", "field-list", str(self.number), "--owner", self.owner, "--format", "json")["fields"]
        status = next((f for f in fields if f.get("name") == "Status"), None)
        if not status:
            raise GhError("the project has no Status field")
        self.field = status["id"]
        by_name = {o["name"]: o["id"] for o in status.get("options", [])}
        if not all(COLUMN_NAMES[c] in by_name for c in COLUMNS) and set_columns:
            try:
                body = {"query": STATUS_OPTIONS_MUTATION, "variables": {"field": self.field, "options": [
                    {"name": COLUMN_NAMES[c], "color": "GRAY", "description": ""} for c in COLUMNS]}}
                res = gh("api", "graphql", "--input", "-", stdin=json.dumps(body))
                by_name = {o["name"]: o["id"] for o in res["data"]["updateProjectV2Field"]["projectV2Field"]["options"]}
            except (GhError, KeyError, TypeError) as e:
                notes.append(f"could not set the Status columns ({e}); using GitHub's defaults, with Backlog as 'No Status'")
        if all(COLUMN_NAMES[c] in by_name for c in COLUMNS):
            self.options = {c: by_name[COLUMN_NAMES[c]] for c in COLUMNS}
        else:
            self.options = {c: by_name.get(DEFAULT_STATUS[c]) if DEFAULT_STATUS[c] else None for c in COLUMNS}
        return notes

    def set_column(self, item_id: str, column: str):
        option = self.options.get(column)
        if option:
            gh("project", "item-edit", "--id", item_id, "--project-id", self.id, "--field-id", self.field,
               "--single-select-option-id", option, parse=False)
        else:
            gh("project", "item-edit", "--id", item_id, "--project-id", self.id, "--field-id", self.field, "--clear", parse=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("review_json", type=Path)
    ap.add_argument("--repo", help="owner/name; default: the GitHub remote 'origin', or the tracker's repo")
    ap.add_argument("--title", help="project title on first run; default 'Review <reviewed date>'")
    ap.add_argument("--min-severity", choices=["low", "medium", "high"],
                    help="create issues only for findings at least this severe (first run default: low)")
    ap.add_argument("--no-tasks", action="store_true", help="don't create issues for suggested tasks")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args()

    path = args.review_json
    data = json.loads(path.read_text(encoding="utf-8"))
    tracker = data.get("tracker") or {}
    first = not tracker
    if tracker and tracker.get("type") != "github":
        sys.exit(f"review.json tracks {tracker.get('type')!r}, not GitHub")

    repo = args.repo or tracker.get("repo") or repo_from_remote(path.resolve().parent)
    if not repo:
        sys.exit("can't tell which GitHub repo this is; pass --repo owner/name")
    owner = repo.split("/")[0]
    min_sev = args.min_severity or tracker.get("min_severity") or "low"
    with_tasks = not (args.no_tasks or tracker.get("tasks") is False)
    title = tracker.get("project_title") or args.title or default_title(data)

    # Plan
    plan_new, plan_close, plan_move, report = [], [], [], []
    items = list(cards(data, min_sev, with_tasks))
    for key, rec, col, closed, ttl, body, labels in items:
        issue = rec.get("issue")
        if not issue:
            plan_new.append((key, rec, col, ttl, body, labels))
            continue
        if closed and issue.get("state") != "closed":
            plan_close.append((key, rec))
        if issue.get("column") != col or not issue.get("item_id"):
            plan_move.append((key, rec, col))

    print(f"{'Create' if first else 'Update'} GitHub project “{title}” for {repo}")
    if first:
        print(f"  issues for open findings with severity ≥ {min_sev}" + ("" if with_tasks else ", no tasks"))
    print(f"  {len(plan_new)} new issues, {len(plan_close)} to close, {len(plan_move)} to move on the board")
    for key, rec, col, ttl, *_ in plan_new[:12]:
        print(f"    + {key}: {ttl[:80]}  [{COLUMN_NAMES[col]}]")
    if len(plan_new) > 12:
        print(f"    … and {len(plan_new) - 12} more")
    for key, rec in plan_close:
        print(f"    ✓ close #{rec['issue']['number']} ({key})")
    if args.dry_run:
        print("Dry run: nothing changed.")
        return 0
    if not shutil.which("gh"):
        sys.exit("the GitHub CLI (gh) is not installed: https://cli.github.com")

    def save():
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    try:
        gh("auth", "status", parse=False)
        if first:
            created = gh("project", "create", "--owner", owner, "--title", title, "--format", "json")
            data["tracker"] = tracker = {
                "type": "github", "repo": repo, "owner": owner, "project_number": created["number"],
                "project_url": created["url"], "project_title": title, "min_severity": min_sev,
                "tasks": with_tasks, "created": date.today().isoformat(),
            }
            save()
            try:
                gh("project", "link", str(created["number"]), "--owner", owner, "--repo", repo, parse=False)
            except GhError as e:
                report.append(f"project created but not linked to {repo}: {e}")
        project = Project(owner, tracker["project_number"])

        def ensure_item(rec: dict):
            if not rec["issue"].get("item_id"):
                item = gh("project", "item-add", str(project.number), "--owner", owner, "--url", rec["issue"]["url"], "--format", "json")
                rec["issue"]["item_id"] = item["id"]
                save()
        report += project.load(set_columns=first)

        for name, (color, desc) in LABELS.items():
            gh("label", "create", name, "--repo", repo, "--color", color, "--description", desc, "--force", parse=False)

        for key, rec, col, ttl, body, labels in plan_new:
            url = gh("issue", "create", "--repo", repo, "--title", ttl, "--body", body,
                     *[a for l in labels for a in ("--label", l)], parse=False).splitlines()[-1]
            number = int(url.rstrip("/").rsplit("/", 1)[-1])
            # Saved before adding to the project, so a re-run never creates the issue twice.
            rec["issue"] = {"number": number, "url": url, "item_id": None, "column": None, "state": "open"}
            save()
            ensure_item(rec)
            plan_move.append((key, rec, col))
            print(f"  created #{number} ({key})")

        for key, rec, col in plan_move:
            ensure_item(rec)
            project.set_column(rec["issue"]["item_id"], col)
            rec["issue"]["column"] = col
            save()

        for key, rec in plan_close:
            gh("issue", "close", str(rec["issue"]["number"]), "--repo", repo, "--comment", close_comment(rec), parse=False)
            rec["issue"]["state"] = "closed"
            save()
            print(f"  closed #{rec['issue']['number']} ({key})")

        # Closed on GitHub but still open in the review: someone thinks it's done.
        closed_on_gh = {i["number"] for i in gh("issue", "list", "--repo", repo, "--label", "review", "--state", "closed",
                                                "--limit", "1000", "--json", "number")}
        for key, rec, col, closed, *_ in items:
            issue = rec.get("issue")
            if issue and not closed and issue["number"] in closed_on_gh:
                report.append(f"#{issue['number']} ({key}) is closed on GitHub but open in the review: check the code, then mark it fixed or reopen the issue")
    except GhError as e:
        save()
        print(f"Stopped: {e}", file=sys.stderr)
        if "project" in str(e) and ("scope" in str(e) or "INSUFFICIENT_SCOPES" in str(e)):
            print("Give gh access to projects with: gh auth refresh -s project", file=sys.stderr)
        print("Progress so far is saved in review.json; run again to continue.", file=sys.stderr)
        return 1

    print(f"Project: {tracker['project_url']}")
    for line in report:
        print(f"  note: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
