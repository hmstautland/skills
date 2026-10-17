#!/usr/bin/env python3
"""UserPromptSubmit hook: offer the review-the-project skill on review and fix prompts.

Adds context only; it never blocks a prompt. Any error exits quietly so a broken
hook can't get in the way of the user's request.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = "review-the-project"

REVIEW_WORDS = re.compile(
    r"\b(review|reviews|reviewing|audit|auditing|health[- ]?check|code[- ]?quality"
    r"|gjennomgang|gjennomg[åa]|revider|revisjon)\b",
    re.IGNORECASE,
)
FIX_WORDS = re.compile(
    r"\b(fix|fixes|fixed|fixing|bugfix|patch|resolve|resolved|repair"
    r"|fiks|fikse|fikset|rett(?:e|et)? opp)\b",
    re.IGNORECASE,
)

ASK = (
    "Ask the user with AskUserQuestion; ask at most once per conversation, and not again "
    "if they already answered or the request is clearly unrelated to code quality."
)


def find_review(cwd: Path) -> Path | None:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, timeout=3,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = ""
    for base in [Path(top)] if top else [cwd, *cwd.parents]:
        candidate = base / ".review" / "review.json"
        if candidate.is_file():
            return candidate
    return None


def context_for(prompt: str, review: Path | None) -> str | None:
    wants_review = bool(REVIEW_WORDS.search(prompt))
    wants_fix = bool(FIX_WORDS.search(prompt))

    if review and wants_review:
        return (
            f"This project has an existing review at {review}. Before acting, ask whether "
            f"they want the {SKILL} skill to update that review page. {ASK}"
        )
    if review and wants_fix:
        return (
            f"This project has an existing review at {review}. Do the requested fix; then, "
            f"if it touched anything the review lists, ask whether they want the {SKILL} "
            f"skill to update the review page. {ASK}"
        )
    if wants_review:
        return (
            f"The user asked for a review. If they mean the whole project or codebase (not "
            f"just a diff, PR or single file), ask before starting whether they want the "
            f"{SKILL} skill: a verified multi-agent review published as a living review "
            f"page, or a quicker inline answer. {ASK}"
        )
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
        prompt = str(data.get("prompt", "")).strip()
        # Explicit slash commands and direct mentions of the skill need no nudge.
        if not prompt or prompt.startswith("/") or SKILL in prompt:
            return 0
        context = context_for(prompt, find_review(Path(data.get("cwd") or ".")))
    except Exception:
        return 0
    if context:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
