#!/usr/bin/env python3
"""Post review-agent's findings on a pull request -- as comments, never approval.

The prompt in `.claude/agents/review-agent.md` says the agent cannot approve.
That is worth nothing on its own: an agent with a shell and your ambient `gh`
session is authenticated as YOU, so `gh pr review --approve` would simply work.
A rule that lives only in a prompt is a suggestion.

This makes it structural. Every GitHub call here is forced through
GH_AGENT_TOKEN, so the agent acts as the agent account -- which is also the
account that opened the pull request. GitHub refuses self-approval, so approval
is not merely discouraged, it is impossible. The same asymmetry that lets a
human approve an agent's work is what stops the agent approving its own.

    FW_AGENT=review-agent python tools/op-cli/agent_review.py --pr 3 \\
        --finding "apps/web/page.tsx:14  literal hex #E50914 — constitution §14" \\
        --note "Is the rail abstraction earning its keep at one caller?"
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import ROOT  # noqa: E402


def env() -> dict[str, str]:
    out = dict(os.environ)
    f = ROOT / ".env.local"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip())
    return out


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--finding", action="append", default=[],
                    help="mechanical violation: file:line and the rule it breaks. Repeatable.")
    ap.add_argument("--note", action="append", default=[],
                    help="judgement call to flag, not resolve. Repeatable.")
    ap.add_argument("--clean", action="store_true",
                    help="say explicitly that nothing mechanical was found")
    a = ap.parse_args()

    e = env()
    if e.get("FW_AGENT", "").strip() != "review-agent":
        die("FW_AGENT must be review-agent to post a review.")
    token = e.get("GH_AGENT_TOKEN", "").strip()
    if not token:
        die("GH_AGENT_TOKEN missing. Without it this would fall back to your own\n"
            "gh session, and the agent would be able to approve — which is the\n"
            "one thing it must not be able to do.")

    if not (a.finding or a.note or a.clean):
        die("Nothing to say. Pass --finding, --note, or --clean.")

    parts = ["## review-agent", ""]
    if a.finding:
        parts += ["**Mechanical — these break a stated rule:**", ""]
        parts += [f"- {f}" for f in a.finding] + [""]
    elif a.clean:
        parts += ["No mechanical violations found: no literal hex outside `packages/tokens`,",
                  "no hardcoded hosts, no hand-edited contracts, no runtime asset fetches.", ""]
    if a.note:
        parts += ["**Judgement — flagged, not resolved. Your call:**", ""]
        parts += [f"- {n}" for n in a.note] + [""]
    parts += ["---",
              "_Comments only. This agent cannot approve — a human has to read this "
              "and decide. Unresolved threads block the merge._"]
    body = "\n".join(parts)

    # --comment, never --approve. And even if that flag were passed, the token
    # below belongs to the account that opened the PR, so GitHub would refuse.
    r = subprocess.run(
        ["gh", "pr", "review", str(a.pr), "--comment", "--body", body],
        capture_output=True, text=True, cwd=ROOT,
        env={**os.environ, "GH_TOKEN": token},
    )
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        die("posting the review failed:\n" + out.replace(token, "<REDACTED>"))

    print(f"posted review on PR #{a.pr}: {len(a.finding)} finding(s), {len(a.note)} note(s)")
    print("A human still has to approve. That is the gate, not a formality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
