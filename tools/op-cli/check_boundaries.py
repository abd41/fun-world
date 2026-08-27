#!/usr/bin/env python3
"""Reject a staged changeset that writes outside the acting agent's boundary.

This is enforcement layer 2 of 3 (see the build plan, §05):
  1. the agent's own definition tells it where it may write   -- catches honesty
  2. THIS, at commit time                                     -- catches the rest
  3. CODEOWNERS + a required check on the PR                  -- catches layer 2 bypass

Who is acting is read from FW_AGENT. With no FW_AGENT set, the commit is
treated as a human commit and allowed -- a person may write anywhere. That is
deliberate: this guard constrains agents, not you.

    FW_AGENT=web-agent git commit -m "..."      # checked
    git commit -m "..."                          # human, unrestricted

Install:  python tools/op-cli/check_boundaries.py --install
Manual:   FW_AGENT=web-agent python tools/op-cli/check_boundaries.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import HUMAN, ROOT, UNOWNED, load, resolve  # noqa: E402

HOOK = """#!/bin/sh
# Fun World pre-commit -- generated, do not edit by hand.
# Two guards, both cheap, each catching a class of silent failure:
#   1. drift  -- OWNERS.yml vs what agents believe and what routing enforces
#   2. bounds -- did the acting agent write outside its allowlist
set -e
ROOT="$(git rev-parse --show-toplevel)"
uv run --with pyyaml python "$ROOT/tools/op-cli/check_drift.py" --offline
uv run --with pyyaml python "$ROOT/tools/op-cli/check_boundaries.py"
"""


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True, text=True, cwd=ROOT,
    )
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def install() -> int:
    hooks = Path(
        subprocess.run(["git", "rev-parse", "--git-path", "hooks"],
                       capture_output=True, text=True, cwd=ROOT).stdout.strip()
    )
    if not hooks.is_absolute():
        hooks = ROOT / hooks
    hooks.mkdir(parents=True, exist_ok=True)
    path = hooks / "pre-commit"
    path.write_text(HOOK, encoding="utf-8")
    path.chmod(0o755)
    print(f"installed {path}")
    print("agents must commit with FW_AGENT set; human commits are unrestricted")
    return 0


def main() -> int:
    if "--install" in sys.argv:
        return install()

    agent = os.environ.get("FW_AGENT", "").strip()
    files = staged_files()

    if not files:
        return 0

    if not agent:
        print(f"boundary guard: human commit ({len(files)} file(s)) — unrestricted")
        return 0

    cfg = load()
    if agent not in cfg["owners"]:
        print(f"boundary guard: FW_AGENT='{agent}' is not in OWNERS.yml", file=sys.stderr)
        print(f"  known agents: {', '.join(sorted(cfg['owners']))}", file=sys.stderr)
        return 1

    violations: list[tuple[str, str, str]] = []
    for f in files:
        r = resolve(f, cfg)
        if r.owner == agent:
            continue
        if r.owner == HUMAN:
            reason = "human-owned — an agent may never write this"
        elif r.owner == UNOWNED:
            reason = "no OWNERS.yml rule covers it — add one, or this path has no owner"
        elif r.owner.startswith("AMBIGUOUS"):
            reason = f"two owners claim it ({r.owner.split(':', 1)[1]}) — add a precedence rule"
        else:
            reason = f"owned by {r.owner}"
        violations.append((f, reason, r.rule))

    if not violations:
        print(f"boundary guard: ok — {len(files)} file(s), all within {agent}")
        return 0

    print(f"\nBOUNDARY VIOLATION — {agent} tried to write {len(violations)} file(s) it does not own:\n",
          file=sys.stderr)
    width = max(len(v[0]) for v in violations)
    for path, reason, rule in violations:
        print(f"  {path:<{width}}  {reason}", file=sys.stderr)
        print(f"  {'':<{width}}  via {rule}", file=sys.stderr)

    print(
        "\nDo not work around this by widening OWNERS.yml — it is human-owned.\n"
        "Split the work package instead, so each child routes to its real owner:\n"
        f"    op-cli split --wp <id> --by-paths\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
