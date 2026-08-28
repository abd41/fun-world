#!/usr/bin/env python3
"""Fail if anything has drifted away from OWNERS.yml.

OWNERS.yml is the single source of truth for who may write what. Three other
things restate it, and each can silently disagree:

  * .claude/agents/*.md  -- what an agent BELIEVES its boundary is
  * the routing resolver -- what actually gets ENFORCED
  * the board Agent field -- what can be ASSIGNED

A disagreement between the first two is the dangerous one: an agent works to a
boundary nobody enforces, or is refused by one it was never told about. Neither
failure announces itself, so it is checked mechanically rather than remembered.

    python tools/op-cli/check_drift.py          # all checks
    python tools/op-cli/check_drift.py --offline # skip the board check
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from owners import ROOT, load  # noqa: E402

HERE = Path(__file__).resolve().parent
AGENTS_DIR = ROOT / ".claude" / "agents"


def check_agent_roster(cfg: dict) -> list[str]:
    """Every OWNERS entry has a definition file, and vice versa."""
    owners = set(cfg["owners"])
    files = {p.stem for p in AGENTS_DIR.glob("*.md")}
    problems = []
    for missing in sorted(owners - files):
        problems.append(f"OWNERS.yml defines '{missing}' but .claude/agents/{missing}.md is missing")
    for orphan in sorted(files - owners):
        problems.append(f".claude/agents/{orphan}.md exists but '{orphan}' is not in OWNERS.yml")
    return problems


def check_agent_content(cfg: dict) -> list[str]:
    """Each definition states exactly the paths OWNERS.yml grants it.

    Catches the subtle case: the file exists and the name matches, but somebody
    hand-edited the allowlist inside it.
    """
    problems = []
    for name, spec in cfg["owners"].items():
        path = AGENTS_DIR / f"{name}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for write in spec.get("writes") or []:
            if f"`{write}`" not in text:
                problems.append(f"{name}: OWNERS.yml grants '{write}' but its definition does not say so")
    return problems


def check_regenerates_clean() -> list[str]:
    """Regenerating produces no change -- the strongest form of the check."""
    r = subprocess.run(
        [sys.executable, str(HERE / "gen_agents.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if r.returncode == 0:
        return []
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if "unchanged" not in ln]
    return ["agent definitions do not match a fresh generation:"] + [f"  {ln}" for ln in lines if ln.strip()]


def check_codeowners() -> list[str]:
    """.github/CODEOWNERS still matches OWNERS.yml.

    CODEOWNERS is the third enforcement layer and it is generated, so the way
    it fails is by quietly falling behind: a new HUMAN-owned path is added to
    OWNERS.yml, nobody regenerates, and the path a person was meant to review
    is reviewed by nobody. Same shape as the agent definitions above.
    """
    r = subprocess.run(
        [sys.executable, str(HERE / "gen_codeowners.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if r.returncode == 0:
        return []
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip() and "unchanged" not in ln]
    return ["CODEOWNERS does not match OWNERS.yml:"] + [f"  {ln}" for ln in lines]


def check_routing() -> list[str]:
    r = subprocess.run([sys.executable, str(HERE / "test_resolve.py")],
                       capture_output=True, text=True, cwd=HERE)
    if r.returncode == 0:
        return []
    failed = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    return ["routing tests failed:"] + [f"  {ln}" for ln in failed]


class Skipped(Exception):
    """This check could not run. NOT the same as passing."""


def check_board(cfg: dict) -> list[str]:
    """Board Agent options match OWNERS.yml.

    Skipped only when OpenProject is genuinely unreachable -- an unreachable
    board must not block a commit made on a train.

    It is NOT skipped when the board answers and rejects us. A wrong API key is
    a real failure, and the earlier version caught every exception alike, so a
    bad key printed "skipped" and "ok" on the same line. That is the exact shape
    of the import-linter bug: a check reporting success while doing nothing.
    """
    try:
        from client import ApiError, TYPE, Client
        c = Client()
        allowed = set(c.allowed_values("customField1", TYPE["task"]))
    except SystemExit as e:
        # No credentials configured at all, or the host does not resolve.
        raise Skipped(str(e).splitlines()[0]) from e
    except ApiError as e:
        if e.status in (401, 403):
            # The board answered and refused us. That is a broken setup, not an
            # absent one, and it must be loud.
            return [f"OpenProject rejected the credentials (HTTP {e.status}) — "
                    "the board check cannot run, and a bad key is not a skip"]
        raise Skipped(f"HTTP {e.status}") from e
    except Exception as e:  # noqa: BLE001
        raise Skipped(type(e).__name__) from e

    owners = set(cfg["owners"])
    problems = []
    for missing in sorted(owners - allowed):
        problems.append(f"'{missing}' is in OWNERS.yml but is not an option on the board's Agent field")
    for extra in sorted(allowed - owners):
        problems.append(f"'{extra}' is an option on the board but is not in OWNERS.yml")
    if problems:
        problems.append("  fix in OpenProject: Administration -> Custom fields -> Agent")
    return problems


def main() -> int:
    cfg = load()
    offline = "--offline" in sys.argv

    # The board check is ALWAYS in this list. It used to be appended only when
    # `not offline`, which meant --offline removed it entirely: `skipped` stayed
    # empty, the summary block was never reached, and the run printed "no drift
    # — consistent across every surface" having never looked at one of them.
    # Both callers pass --offline, so that was every automated run.
    #
    # An omitted check and a skipped check are the same lie told differently.
    # Now it always runs and always reports; --offline only says the skip is
    # expected, which changes the exit code, not the honesty of the output.
    def board_check() -> list[str]:
        if offline:
            raise Skipped("--offline was passed")
        return check_board(cfg)

    checks = [
        ("agent roster matches OWNERS.yml", lambda: check_agent_roster(cfg)),
        ("agent definitions state their real paths", lambda: check_agent_content(cfg)),
        ("definitions match a fresh generation", check_regenerates_clean),
        ("routing resolves as intended", check_routing),
        ("CODEOWNERS matches OWNERS.yml", check_codeowners),
        ("board Agent field matches OWNERS.yml", board_check),
    ]

    failures: list[str] = []
    skipped: list[str] = []
    for label, fn in checks:
        try:
            problems = fn()
        except Skipped as why:
            # A skip is reported as a skip, never as "ok". Conflating them is
            # how a guard ends up green and inert.
            skipped.append(f"{label} — {why}")
            print(f"  SKIP {label}  ({why})")
            continue
        print(f"  {'ok  ' if not problems else 'FAIL'} {label}")
        failures.extend(problems)

    if failures:
        print("\nDRIFT DETECTED\n", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nOWNERS.yml is the source of truth. Two different things are\n"
            "generated from it, and they have SEPARATE generators -- routing a\n"
            "reader to the wrong one is why this is spelled out:\n\n"
            "    .claude/agents/*.md   ->  pnpm agents:gen\n"
            "    .github/CODEOWNERS    ->  pnpm codeowners:gen\n\n"
            "Fix whichever the failure above names. Never hand-edit either: both\n"
            "are generated, and the next generation would silently undo it.\n",
            file=sys.stderr,
        )
        return 1

    if skipped:
        # Never claim "no drift" when a surface was not examined. The summary
        # states exactly what was checked, so a green run cannot be mistaken for
        # a complete one.
        print(f"\nno drift in {len(checks) - len(skipped)} of {len(checks)} checks — "
              f"{len(skipped)} SKIPPED, so this is not a clean bill of health:")
        for s in skipped:
            print(f"    {s}")
        if not offline:
            # --offline is an explicit statement that the board is unreachable
            # and that is expected. Without it, a skip is a surprise and should
            # not pass silently.
            print("\n  Re-run with --offline if that is expected.", file=sys.stderr)
            return 1
        return 0

    print(f"\nno drift — {len(cfg['owners'])} agents consistent across every surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
