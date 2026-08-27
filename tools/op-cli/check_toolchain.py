#!/usr/bin/env python3
"""Check the development toolchain, per phase.

Not everything is needed at once, and pretending otherwise makes the check
useless -- an agent that sees "ffmpeg MISSING" while working on vertical 001
will either install it pointlessly or learn to ignore the output. So tools are
grouped by the vertical that first needs them, and only the current phase is
treated as blocking.

    python tools/op-cli/check_toolchain.py --phase 1  # fail if phase 1 is short
    python tools/op-cli/check_toolchain.py            # SURVEY ONLY — exits 2

Without --phase nothing is treated as blocking, so it exits 2 rather than 0. A
survey that exits 0 is indistinguishable from a passing check, and wiring that
into CI would look like a guard while being a no-op.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

# (command, version args, why, first phase that needs it)
TOOLS: list[tuple[str, list[str], str, int]] = [
    ("node",    ["-v"],              "Next.js and Expo",                        1),
    ("pnpm",    ["-v"],              "workspace package manager",               1),
    ("python",  ["--version"],       "Django, op-cli",                          1),
    ("uv",      ["--version"],       "Python dependency management",            1),
    ("docker",  ["--version"],       "Postgres, Caddy, OpenProject",            1),
    ("git",     ["--version"],       "everything",                              1),
    ("gh",      ["--version"],       "pull requests, the review gate",          1),
    ("psql",    ["--version"],       "inspecting the database directly",        1),
    ("ffmpeg",  ["-version"],        "HLS transcoding ladder",                  3),
    ("ffprobe", ["-version"],        "reading stream metadata",                 3),
    ("java",    ["-version"],        "Android builds (Fire TV, Google TV)",     3),
    ("adb",     ["version"],         "sideloading onto the televisions",        3),
]

PHASE_NAMES = {
    1: "Skeleton (verticals 001-003)",
    2: "Identity (004)",
    3: "Watch (005-008) — media pipeline and TV",
    4: "Continuity (009-011)",
    5: "Depth (012 + Keycloak)",
}


def version_of(cmd: str, args: list[str]) -> str | None:
    if not shutil.which(cmd):
        return None
    try:
        r = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=30)
        line = (r.stdout or r.stderr).strip().splitlines()
        return line[0][:60] if line else "(no version output)"
    except Exception:
        return "(present, version unreadable)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, help="fail if tools for this phase are missing")
    args = ap.parse_args()

    missing_now: list[tuple[str, str]] = []
    by_phase: dict[int, list] = {}
    for cmd, vargs, why, phase in TOOLS:
        by_phase.setdefault(phase, []).append((cmd, version_of(cmd, vargs), why))

    for phase in sorted(by_phase):
        label = PHASE_NAMES.get(phase, f"phase {phase}")
        blocking = args.phase is not None and phase <= args.phase
        print(f"\n  {label}{'   [required now]' if blocking else ''}")
        for cmd, ver, why in by_phase[phase]:
            if ver is None:
                print(f"    MISSING  {cmd:<9} — {why}")
                if blocking:
                    missing_now.append((cmd, why))
            else:
                print(f"    ok       {cmd:<9} {ver}")

    if missing_now:
        print(f"\n{len(missing_now)} tool(s) missing for phase {args.phase}:", file=sys.stderr)
        for cmd, why in missing_now:
            print(f"  {cmd} — {why}", file=sys.stderr)
        print("\nWindows install hints:", file=sys.stderr)
        hints = {
            "ffmpeg": "winget install Gyan.FFmpeg",
            "ffprobe": "ships with ffmpeg",
            "java": "winget install Microsoft.OpenJDK.21",
            "adb": "winget install Google.PlatformTools",
            "pnpm": "corepack enable  (or: npm i -g pnpm)",
            "psql": "winget install PostgreSQL.PostgreSQL.17",
        }
        for cmd, _ in missing_now:
            if cmd in hints:
                print(f"  {cmd:<9} {hints[cmd]}", file=sys.stderr)
        return 1

    # `is not None`, matching the test at the top of the loop. `if args.phase`
    # is falsy for --phase 0, so the two disagreed: phase 0 counted as "a phase
    # was given" when deciding what blocks, and as "no phase" when deciding the
    # exit code. Phase 0 is not a real phase today, which is exactly why this
    # would have sat here until it was.
    if args.phase is not None:
        print(f"\nphase {args.phase} toolchain complete")
        return 0

    # No --phase means nothing was treated as blocking, so exiting 0 would be a
    # guard that always passes. Wiring this into CI without --phase would look
    # like a check and be a no-op -- the same failure that left the layering
    # contract green and inert for its whole life.
    print("\nSURVEY ONLY — nothing was treated as blocking.", file=sys.stderr)
    print("Pass --phase N to make missing tools fail.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
