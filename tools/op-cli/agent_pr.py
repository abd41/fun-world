#!/usr/bin/env python3
"""Push an agent's branch and open its pull request AS THE AGENT ACCOUNT.

Why this exists at all: GitHub refuses to let anyone approve their own pull
request. With one identity, "require an approval" is a rule that can only be
satisfied by bypassing it -- and a gate you always bypass is worse than no gate,
because it teaches you the gesture. Opening the PR as a second identity makes
the approval real: `abdulRaw` proposes, `abd41` approves.

The distinction that matters: GitHub's self-approval rule keys on **who opened
the pull request**, not who authored the commits. Commit authorship is
attribution; the PR author is what unblocks approval. This sets both, but only
the second one is load-bearing.

    FW_AGENT=web-agent python tools/op-cli/agent_pr.py --wp 42 --title "..."
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import ROOT, load  # noqa: E402

PROTECTED = {"main", "master"}


def env() -> dict[str, str]:
    """Read .env.local without importing a dependency for four keys."""
    out = dict(os.environ)
    f = ROOT / ".env.local"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip())
    return out


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wp", type=int, required=True, help="work package id — goes in the PR body as OP#<id>")
    ap.add_argument("--title", help="PR title (defaults to the last commit subject)")
    ap.add_argument("--body", default="", help="extra PR body text")
    args = ap.parse_args()

    e = env()
    agent = e.get("FW_AGENT", "").strip()
    user, token = e.get("GH_AGENT_USER", "").strip(), e.get("GH_AGENT_TOKEN", "").strip()

    if not agent:
        die("FW_AGENT is not set. An agent opens its own pull requests:\n"
            "    FW_AGENT=web-agent python tools/op-cli/agent_pr.py --wp 42")
    if agent not in load()["owners"]:
        die(f"'{agent}' is not an agent in OWNERS.yml")
    if not user or not token:
        die("GH_AGENT_USER and GH_AGENT_TOKEN must be in .env.local.\n"
            "  Without a second identity, GitHub will not let anyone approve the PR.")

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if branch in PROTECTED:
        die(f"You are on '{branch}'. Agents work on a branch:\n"
            f"    git switch -c {agent}/wp-{args.wp}")

    if run(["git", "status", "--porcelain"]).stdout.strip():
        die("Working tree is dirty. Commit your work first — the pre-commit guard\n"
            "checks it against your boundary, and skipping that defeats the point.")

    # Ephemeral push URL: never written to .git/config, so the token does not
    # persist in the repo. It is still visible to `ps` for the moment the push
    # runs -- acceptable on a single-user laptop, and the reason this is not
    # how you would do it on a shared machine.
    push_url = f"https://x-access-token:{token}@github.com/abd41/fun-world.git"
    print(f"pushing {branch} as {user} ...")
    p = run(["git", "push", push_url, f"HEAD:refs/heads/{branch}", "--force-with-lease"])
    if p.returncode != 0:
        die("push failed:\n" + (p.stderr.replace(token, "<REDACTED>") if token else p.stderr))
    print(f"  pushed {branch}")

    title = args.title or run(["git", "log", "-1", "--pretty=%s"]).stdout.strip()
    body = (
        f"{args.body}\n\n" if args.body else ""
    ) + (
        f"Work package **OP#{args.wp}** — http://localhost:8080/work_packages/{args.wp}\n\n"
        f"Opened by `{agent}`, working inside its `OWNERS.yml` boundary.\n\n"
        "---\n"
        "- [ ] `review-agent` has commented\n"
        "- [ ] mechanical findings addressed or answered\n"
        "- [ ] a human approved\n"
    )

    # gh honours GH_TOKEN, so the PR is authored by the agent account. This is
    # the load-bearing line: it is what makes the human's approval possible.
    envv = {**os.environ, "GH_TOKEN": token}
    p = subprocess.run(
        ["gh", "pr", "create", "--base", "main", "--head", branch,
         "--title", title, "--body", body],
        capture_output=True, text=True, cwd=ROOT, env=envv,
    )
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        if "already exists" in out:
            print("  PR already open for this branch — pushed the new commits to it")
        else:
            die("gh pr create failed:\n" + out.replace(token, "<REDACTED>"))
    else:
        print(f"  {out.splitlines()[-1]}")

    print(f"\nNext: op-cli done --wp {args.wp} --pr <number>")
    print(f"Then a human reviews. {user} cannot approve its own PR — that is the point.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
