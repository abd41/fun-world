#!/usr/bin/env python3
"""Reject a staged changeset that writes outside the acting agent's boundary.

This is enforcement layer 2 of 3 (see the build plan, §05):
  1. the agent's own definition tells it where it may write   -- catches honesty
  2. THIS, at commit time                                     -- catches the rest
  3. CODEOWNERS + a required check on the PR                  -- catches layer 2 bypass

Who is acting is read from FW_AGENT. With no FW_AGENT set, the commit is
treated as a human commit and allowed -- a person may write anywhere. That is
deliberate: this guard constrains agents, not you.

    FW_AGENT=web-agent git commit -m "..."      # checked against the allowlist
    git commit -m "..."                          # human, unrestricted

ONE EXCEPTION. If the commit is authored as the agent account (GH_AGENT_USER)
and FW_AGENT is unset, it is REFUSED rather than treated as human -- that is an
agent that forgot the variable, and waving it through would let it write
anywhere. Committing under your own identity is unaffected.

Install:  python tools/op-cli/check_boundaries.py --install
Manual:   FW_AGENT=web-agent python tools/op-cli/check_boundaries.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import HUMAN, ROOT, SHARED, UNOWNED, accounts, load, resolve  # noqa: E402

HOOK = """#!/bin/sh
# Fun World pre-commit -- generated, do not edit by hand.
# Three guards, each catching a class of silent failure:
#   1. drift        -- OWNERS.yml vs agent definitions vs routing vs the board
#   2. bounds       -- did the acting agent write outside its allowlist
#   3. constitution -- mechanically checkable rules, over staged files
set -e
ROOT="$(git rev-parse --show-toplevel)"
uv run --with pyyaml python "$ROOT/tools/op-cli/check_drift.py" --offline
uv run --with pyyaml python "$ROOT/tools/op-cli/check_boundaries.py"
uv run python "$ROOT/tools/op-cli/check_constitution.py" --staged
"""


def agent_identity() -> str:
    """The account agents commit as.

    OWNERS.yml first, .env.local only as a fallback. The order matters and was
    the wrong way round: .env.local is gitignored, so it does not exist in CI.
    Read from there alone, this returned "" on every CI run -- and "" means
    `pending_author_is_agent()` says False, which means every agent commit
    would have been waved through as human work by a check whose entire job is
    to tell them apart. Silently, and reporting success.

    A username is not a secret, so it belongs in the committed routing table.
    The token stays in .env.local.
    """
    if name := accounts().get("agent", "").strip():
        return name
    envfile = ROOT / ".env.local"
    if envfile.exists():
        for line in envfile.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GH_AGENT_USER="):
                return line.split("=", 1)[1].strip()
    return ""


def pending_author_is_agent() -> bool:
    """Is this commit being authored as the agent account?

    Reads the author git will actually record, which is what `-c user.name`
    sets -- so it reflects the commit about to be made rather than the repo's
    default config.
    """
    identity = agent_identity()
    if not identity:
        return False

    # GIT_AUTHOR_IDENT is "Name <email> <timestamp> <tz>". Compare the NAME
    # exactly -- a substring match over the whole string is wrong here, because
    # the human's email (abdulrawoofali24@gmail.com) contains the agent's
    # username (abdulRaw), so every human commit matched. Caught by testing the
    # human-on-an-agent-branch case, which is exactly the false positive this
    # check was chosen to avoid.
    out = subprocess.run(
        ["git", "var", "GIT_AUTHOR_IDENT"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    name = out.split("<", 1)[0].strip() if "<" in out else out
    return name.casefold() == identity.casefold()


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True, text=True, cwd=ROOT,
    )
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


TRAILER_HOOK = """#!/bin/sh
# Fun World prepare-commit-msg -- generated, do not edit by hand.
#
# Records WHICH agent is committing, as a trailer, so a boundary claim can be
# checked after the fact instead of argued about.
#
# FW_AGENT is the identity the boundary guard validates, and it used to live
# only in this shell's environment -- gone the instant the commit finished. On
# PR #15 that produced a dispute nobody could settle: a reviewer inferred an
# agent from git authorship, the author answered that the hook had passed, and
# neither could be checked. Every agent shares one GitHub account, so
# authorship separates agent from human and nothing finer.
#
# $2 is the commit source. Skip merges and squashes: their message is assembled
# from commits that already carry their own trailer, and appending another
# would attribute someone else's work to whoever ran the merge.
[ -n "$FW_AGENT" ] || exit 0
case "$2" in
  merge|squash) exit 0 ;;
esac
git interpret-trailers --in-place --if-exists replace --trailer "FW-Agent: $FW_AGENT" "$1"
"""


PUSH_HOOK = """#!/bin/sh
# Fun World pre-push -- generated, do not edit by hand.
exec uv run --with pyyaml python "$(git rev-parse --show-toplevel)/tools/op-cli/check_push.py"
"""


def install() -> int:
    hooks = Path(
        subprocess.run(["git", "rev-parse", "--git-path", "hooks"],
                       capture_output=True, text=True, cwd=ROOT).stdout.strip()
    )
    if not hooks.is_absolute():
        hooks = ROOT / hooks
    hooks.mkdir(parents=True, exist_ok=True)
    for name, body in (("pre-commit", HOOK), ("prepare-commit-msg", TRAILER_HOOK),
                       ("pre-push", PUSH_HOOK)):
        path = hooks / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        print(f"installed {path}")
    print("commit: agents must set FW_AGENT; human commits are unrestricted")
    print("msg:    FW_AGENT is recorded as an FW-Agent trailer, so CI can check it")
    print("push:   direct pushes to main are refused -- use a PR")
    return 0


class GitFailed(RuntimeError):
    """A git command this check depends on did not succeed."""


def _git(*args: str) -> str:
    """Run git, and REFUSE to treat a failure as an empty answer.

    This used to discard the return code and stderr, which made a `rev-list`
    that failed indistinguishable from a range containing no commits -- so a
    bad or unreachable BASE (a force-push, a shallow clone, a deleted ref)
    produced "no commits in <range>" and exit 0. A guard that reports success
    because its input was broken is the failure this whole job exists to catch.
    """
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise GitFailed("git " + " ".join(args) + " failed: " + r.stderr.strip())
    return r.stdout.strip()


def violations_for(agent: str, files: list[str], cfg: dict) -> list[tuple[str, str, str]]:
    """Every file in `files` that `agent` is not allowed to write."""
    out = []
    for f in files:
        r = resolve(f, cfg)
        if r.owner in (agent, SHARED):
            continue
        if r.owner == HUMAN:
            reason = "human-owned — an agent may never write this"
        elif r.owner == UNOWNED:
            reason = "no OWNERS.yml rule covers it — add one, or this path has no owner"
        elif r.owner.startswith("AMBIGUOUS"):
            reason = f"two owners claim it ({r.owner.split(':', 1)[1]}) — add a precedence rule"
        else:
            reason = f"owned by {r.owner}"
        out.append((f, reason, r.rule))
    return out


def check_range(rev_range: str) -> int:
    """Enforcement layer 3: re-check every commit in a PR, where --no-verify cannot reach.

    Layers 1 and 2 -- the agent's own definition, and the pre-commit hook --
    are both local, and both are one `--no-verify` away from not existing.
    This is the layer that survives that, which ADR-0007 has claimed all along
    and nothing implemented.

    Identity comes from the FW-Agent trailer, not from authorship. Authorship
    cannot carry it: every agent commits as one account, so it separates agent
    from human and nothing finer. An agent-authored commit with NO trailer is a
    failure rather than a pass -- otherwise stripping the trailer would be a
    way to opt out of the check, which is the same hole as a guard that skips
    when its config is missing.
    """
    cfg = load()
    identity = agent_identity()
    if not identity:
        # Refuse rather than pass. With no identity every commit looks human
        # and this job would report success having checked nothing -- the exact
        # failure it exists to catch.
        print("REFUSING to run: no agent account is configured.", file=sys.stderr)
        print("  Set `accounts.agent` in OWNERS.yml.", file=sys.stderr)
        return 1

    try:
        shas = [ln for ln in _git("rev-list", "--no-merges", rev_range).splitlines() if ln]
    except GitFailed as why:
        # Fail, do not skip. "I could not read the range" is not "the range is
        # clean", and only one of those two should let a merge proceed.
        print(f"REFUSING to run: {why}", file=sys.stderr)
        print(f"  The range {rev_range!r} could not be read, so nothing was checked.",
              file=sys.stderr)
        print("  In CI this usually means a shallow clone — set fetch-depth: 0.",
              file=sys.stderr)
        return 1

    if not shas:
        print(f"boundary guard: no commits in {rev_range}")
        return 0

    known = set(cfg["owners"])
    failures: list[str] = []
    for sha in shas:
        author = _git("log", "-1", "--format=%an", sha)
        subject = _git("log", "-1", "--format=%s", sha)
        short = sha[:9]

        if author.casefold() != identity.casefold():
            print(f"  human   {short}  {subject}")
            continue

        trailer = _git("log", "-1", "--format=%(trailers:key=FW-Agent,valueonly)", sha).strip()
        if not trailer:
            failures.append(chr(10).join([
                f"{short} {subject}",
                "      Authored by the agent account with no FW-Agent trailer, so",
                "      which agent wrote it cannot be determined and its boundary",
                "      cannot be checked. Reinstall the hooks:",
                "        uv run --with pyyaml python tools/op-cli/check_boundaries.py --install",
            ]))
            print(f"  FAIL    {short}  {subject}  (no FW-Agent trailer)")
            continue

        if trailer not in known:
            failures.append(chr(10).join([
                f"{short} {subject}",
                f"      FW-Agent: {trailer!r} is not an agent in OWNERS.yml",
            ]))
            print(f"  FAIL    {short}  {subject}  (unknown agent {trailer!r})")
            continue

        files = [ln for ln in _git("show", "--pretty=format:", "--name-only",
                                   "--diff-filter=ACMRT", sha).splitlines() if ln.strip()]
        bad = violations_for(trailer, files, cfg)
        if bad:
            lines = [f"{short} {subject}",
                     f"      {trailer} wrote {len(bad)} file(s) it does not own:"]
            lines += [f"        {f}  — {why}  (via {rule})" for f, why, rule in bad]
            failures.append(chr(10).join(lines))
            print(f"  FAIL    {short}  {subject}  ({trailer}, {len(bad)} violation(s))")
        else:
            print(f"  ok      {short}  {subject}  ({trailer}, {len(files)} file(s))")

    if failures:
        print(file=sys.stderr)
        print(f"BOUNDARY VIOLATION in {len(failures)} commit(s):", file=sys.stderr)
        print(file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
            print(file=sys.stderr)
        print("Do not widen OWNERS.yml to fix this — it is human-owned.", file=sys.stderr)
        print("Split the work package so each child routes to its real owner:", file=sys.stderr)
        print("    op-cli split --wp <id> --by-paths", file=sys.stderr)
        return 1

    print()
    print(f"boundary guard: {len(shas)} commit(s) checked, all inside their agent's boundary")
    return 0


def main() -> int:
    if "--install" in sys.argv:
        return install()

    for i, arg in enumerate(sys.argv):
        if arg == "--range":
            return check_range(sys.argv[i + 1])

    agent = os.environ.get("FW_AGENT", "").strip()
    files = staged_files()

    if not files:
        return 0

    if not agent:
        # An agent that forgets FW_AGENT would get an unrestricted human
        # commit, which is the one way left to write outside a boundary by
        # accident. Authorship is the precise signal: agents commit as the
        # agent account, humans as themselves.
        #
        # Branch name was the other candidate and is wrong -- a human
        # legitimately commits on an agent's branch (registering an app in
        # settings.py, fixing a guard), and blocking that would train people
        # to bypass the hook.
        if pending_author_is_agent():
            print(
                f"\nREFUSED: committing as the agent account with no FW_AGENT set.\n\n"
                f"  Author is '{agent_identity()}', so this is agent work — but the\n"
                "  boundary guard was about to wave it through as a human commit,\n"
                "  which would let it write anywhere.\n\n"
                "  Set the agent explicitly:\n"
                "      FW_AGENT=<agent> git commit ...\n\n"
                "  If you are a person, commit under your own identity instead.\n",
                file=sys.stderr,
            )
            return 1
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
        if r.owner in (agent, SHARED):
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
