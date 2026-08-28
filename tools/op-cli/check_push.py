#!/usr/bin/env python3
"""Refuse a direct push to the protected branch.

GitHub's free tier gives no branch protection or rulesets on a private repo, so
the "nothing reaches main without review" rule has to be enforced somewhere
else. This is that somewhere.

Be clear about what this is worth. A local hook is skippable with --no-verify
and only exists on this machine. It is not a security control; it is a
guardrail against the honest mistake -- an agent, or a tired human, pushing a
branch straight to main out of habit. Given the only actors here are agents
running under the owner's own control, the threat model is carelessness rather
than malice, and a guardrail is the right shape of answer.

If the repository ever goes public, real server-side rules become available for
free and should replace this.

Install: python tools/op-cli/check_boundaries.py --install
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROTECTED = {"main", "master"}


def current_branch() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout.strip()


def main() -> int:
    # git passes "<local ref> <local sha> <remote ref> <remote sha>" on stdin,
    # one line per ref being pushed. Empty stdin means nothing to check.
    refs = [ln.split() for ln in sys.stdin.read().splitlines() if ln.strip()]

    blocked = []
    for parts in refs:
        if len(parts) < 3:
            continue
        remote_ref = parts[2]
        branch = remote_ref.rsplit("/", 1)[-1]
        if branch in PROTECTED:
            blocked.append(branch)

    if not blocked:
        return 0

    branch = current_branch()
    print(
        f"\nREFUSED: direct push to '{blocked[0]}'.\n\n"
        "  Everything reaches the default branch through a reviewed pull\n"
        "  request (constitution §25). Nothing merges without a human\n"
        "  approving it -- that gate is the point, not a formality.\n\n"
        f"  You are on: {branch}\n\n"
        "  Instead:\n"
        f"    git switch -c <feature-branch>       # if you are on {blocked[0]}\n"
        "    git push -u origin <feature-branch>\n"
        "    gh pr create --fill\n\n"
        "  A pull request body should carry OP#<id> so OpenProject links it.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
