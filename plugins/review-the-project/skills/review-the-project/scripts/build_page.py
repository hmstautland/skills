#!/usr/bin/env python3
"""Build the review page from a review.json data file.

    python3 build_page.py <review.json> <out.html>

The page is rendered client-side from the embedded data, so this script only
validates the data, embeds it safely and fills in the <title>. See
references/data-format.md for the schema. Exits non-zero (and builds nothing)
when the data is inconsistent - e.g. a finding marked fixed that no change-log
entry mentions - because the page would then misreport the project's state.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "page_template.html"

KINDS = {"bug", "security", "risk", "unfinished", "improvement", "dead-code"}
SEVERITIES = {"high", "medium", "low"}
STATUSES = {"open", "partly", "fixed"}
VERIFICATIONS = {"verified", "corrected", "accepted"}
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

    for fid, f in by_id.items():
        if f.get("status") == "fixed" and fid not in referenced_fixed:
            errors.append(f"finding {fid} is fixed but no changelog entry lists it under 'fixes'")
        if f.get("status") == "partly" and fid not in referenced_partly:
            errors.append(f"finding {fid} is partly fixed but no changelog entry lists it under 'partly'")

    for i, p in enumerate(data.get("priorities", [])):
        for fid in p.get("findings", []):
            if fid not in by_id:
                errors.append(f"priority {i} ({p.get('title', '?')}) refers to unknown finding {fid}")

    return errors


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
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("%%TITLE%%", title.replace("&", "&amp;").replace("<", "&lt;"), 1)
    html = html.replace("%%DATA%%", payload, 1)
    Path(sys.argv[2]).write_text(html, encoding="utf-8")

    findings = data["findings"]
    open_findings = [f for f in findings if f["status"] != "fixed"]
    print(f"Built {sys.argv[2]} ({len(html) // 1024} KB)")
    print(f"  open: {len(open_findings)} ({dict(Counter(f['severity'] for f in open_findings))}), "
          f"partly fixed: {sum(f['status'] == 'partly' for f in findings)}, "
          f"fixed: {len(findings) - len(open_findings)}")


if __name__ == "__main__":
    main()
