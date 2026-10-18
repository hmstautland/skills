#!/usr/bin/env python3
"""Build the review page and its task board from a review.json data file.

    python3 build_page.py <review.json> <out.html>

Writes <out.html> and, next to it, tasks.html (the task board, linked from the
review page). Both pages are rendered client-side from the embedded data, so this
script only validates the data, embeds it safely and fills in the titles. See
references/data-format.md for the schema. Exits non-zero (and builds nothing)
when the data is inconsistent - e.g. a finding marked fixed that no change-log
entry mentions - because the page would then misreport the project's state.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE = ASSETS / "page_template.html"
TASKS_TEMPLATE = ASSETS / "tasks_template.html"
TASKS_PAGE = "tasks.html"

KINDS = {"bug", "security", "risk", "unfinished", "improvement", "dead-code"}
SEVERITIES = {"high", "medium", "low"}
STATUSES = {"open", "partly", "fixed"}
VERIFICATIONS = {"verified", "corrected", "accepted"}
COLUMNS = {"backlog", "todo", "doing", "done"}
EFFORTS = {"small", "medium", "large"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(data):
    errors = []

    for key in ("project", "findings"):
        if key not in data:
            errors.append(f"missing top-level '{key}'")
    for key in ("reviewed", "updated"):
        if data.get(key) and not DATE.match(data[key]):
            errors.append(f"'{key}' must be YYYY-MM-DD, got {data[key]!r}")

    ids = Counter(f.get("id") for f in data.get("findings", []))
    for fid, n in ids.items():
        if n > 1:
            errors.append(f"finding id {fid} is used {n} times")

    by_id = {f.get("id"): f for f in data.get("findings", [])}
    for f in data.get("findings", []):
        where = f"finding {f.get('id')}"
        for key in ("id", "kind", "severity", "title", "detail", "status"):
            if key not in f:
                errors.append(f"{where}: missing '{key}'")
        if f.get("kind") not in KINDS:
            errors.append(f"{where}: kind {f.get('kind')!r} not in {sorted(KINDS)}")
        if f.get("severity") not in SEVERITIES:
            errors.append(f"{where}: severity {f.get('severity')!r} not in {sorted(SEVERITIES)}")
        if f.get("status") not in STATUSES:
            errors.append(f"{where}: status {f.get('status')!r} not in {sorted(STATUSES)}")
        if f.get("verification", "verified") not in VERIFICATIONS:
            errors.append(f"{where}: verification {f.get('verification')!r} not in {sorted(VERIFICATIONS)}")
        if f.get("status") in ("partly", "fixed") and not f.get("status_note"):
            errors.append(f"{where}: status '{f['status']}' needs a status_note saying what changed (and, if partly, what is still open)")
        if "column" in f and f["column"] not in COLUMNS - {"done"}:
            errors.append(f"{where}: column {f['column']!r} must be backlog, todo or doing (a finding is done only when its status is fixed)")

    referenced_fixed, referenced_partly = set(), set()
    for i, entry in enumerate(data.get("changelog", [])):
        where = f"changelog entry {i} ({entry.get('title', '?')})"
        if not DATE.match(entry.get("date", "")):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        for key, bucket, want in (("fixes", referenced_fixed, "fixed"), ("partly", referenced_partly, "partly")):
            for fid in entry.get(key, []):
                if fid not in by_id:
                    errors.append(f"{where}: {key} refers to unknown finding {fid}")
                elif by_id[fid]["status"] != want:
                    errors.append(f"{where}: lists finding {fid} under '{key}' but its status is '{by_id[fid]['status']}'")
                bucket.add(fid)
        for fid in entry.get("found", []):
            if fid not in by_id:
                errors.append(f"{where}: found refers to unknown finding {fid}")

    for fid, f in by_id.items():
        if f.get("status") == "fixed" and fid not in referenced_fixed:
            errors.append(f"finding {fid} is fixed but no changelog entry lists it under 'fixes'")
        if f.get("status") == "partly" and fid not in referenced_partly:
            errors.append(f"finding {fid} is partly fixed but no changelog entry lists it under 'partly'")

    for i, p in enumerate(data.get("priorities", [])):
        for fid in p.get("findings", []):
            if fid not in by_id:
                errors.append(f"priority {i} ({p.get('title', '?')}) refers to unknown finding {fid}")

    task_ids = Counter(t.get("id") for t in data.get("tasks", []))
    for tid, n in task_ids.items():
        if n > 1:
            errors.append(f"task id {tid} is used {n} times")
    for t in data.get("tasks", []):
        where = f"task {t.get('id')} ({t.get('title', '?')})"
        for key in ("id", "title", "text"):
            if not t.get(key):
                errors.append(f"{where}: missing '{key}'")
        if t.get("column", "backlog") not in COLUMNS:
            errors.append(f"{where}: column {t.get('column')!r} not in {sorted(COLUMNS)}")
        if t.get("source", "review") not in ("review", "owner"):
            errors.append(f"{where}: source {t.get('source')!r} must be review or owner")
        if t.get("effort") and t["effort"] not in EFFORTS:
            errors.append(f"{where}: effort {t['effort']!r} not in {sorted(EFFORTS)}")
        for fid in t.get("findings", []):
            if fid not in by_id:
                errors.append(f"{where}: refers to unknown finding {fid}")

    return errors


def fill(template, title, payload, **extra):
    html = template.read_text(encoding="utf-8")
    html = html.replace("%%TITLE%%", title.replace("&", "&amp;").replace("<", "&lt;"), 1)
    for key, value in extra.items():
        html = html.replace(f"%%{key}%%", value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;"))
    return html.replace("%%DATA%%", payload, 1)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("review.json is inconsistent, page not built:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    # "<" escaped so text quoting <script> or <!-- can't end the data block
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    title = data.get("title") or f"{data['project']} Code Review"
    out = Path(sys.argv[2])
    if out.name == TASKS_PAGE:
        sys.exit(f"the review page can't be named {TASKS_PAGE}; that name is used by the task board")
    html = fill(TEMPLATE, title, payload, TASKS_HREF=TASKS_PAGE)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    tasks_out = out.with_name(TASKS_PAGE)
    tasks_out.write_text(fill(TASKS_TEMPLATE, f"{data['project']} Tasks", payload, REVIEW_HREF=out.name), encoding="utf-8")

    findings = data["findings"]
    open_findings = [f for f in findings if f["status"] != "fixed"]
    print(f"Built {out} ({len(html) // 1024} KB) and {tasks_out}")
    print(f"  open: {len(open_findings)} ({dict(Counter(f['severity'] for f in open_findings))}), "
          f"partly fixed: {sum(f['status'] == 'partly' for f in findings)}, "
          f"fixed: {len(findings) - len(open_findings)}, suggested tasks: {len(data.get('tasks', []))}")


if __name__ == "__main__":
    main()
