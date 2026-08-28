#!/usr/bin/env python3
"""Generate .github/CODEOWNERS from OWNERS.yml.

Generated, never hand-written. A second hand-maintained ownership table drifts
from the first within a few weeks, and then two files disagree about who owns
what -- which is the failure `check_drift.py` already exists to catch. So this
derives from the same source and `check_drift.py` verifies it still matches.

WHAT THIS FILE IS WORTH, ACCURATELY. An earlier version of this docstring said
the repository was private and had no branch protection, and cited
`check_push.py` for it. Both halves were wrong. The repository is PUBLIC, and
ruleset 21628724 is `active` on the default branch with one required approval,
required review-thread resolution, dismiss-stale-on-push and squash-only
merges. `check_push.py:15-16` actually says the opposite of what it was cited
for -- "if the repository ever goes public, real server-side rules become
available for free and should replace this" -- which has now happened.

What is true is narrower and worth stating exactly: the ruleset has
`require_code_owner_review: false`. So a CODEOWNERS entry requests a reviewer
and does not compel one, and flipping that single flag is what would make this
file blocking. The platform is not the obstacle; a setting is.

ORDERING. OWNERS.yml is FIRST match wins; CODEOWNERS is LAST match wins. The
two are exact opposites, so precedence rules are emitted in REVERSE order and
the catch-all goes first. Getting this wrong is not cosmetic: an earlier
version collected HUMAN paths into an unordered set and dropped the carve-outs
that precede them, which made the generated file assert that
`infra/keycloak/realm/**` was human-only when OWNERS.yml routes it to
auth-agent.

Run:    python tools/op-cli/gen_codeowners.py       (needs pyyaml)
        uv run --with pyyaml python tools/op-cli/gen_codeowners.py
Check:  ... gen_codeowners.py --check
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import HUMAN, ROOT, accounts, load  # noqa: E402

OUT = ROOT / ".github" / "CODEOWNERS"


def to_codeowners_pattern(glob: str) -> str:
    """Translate an OWNERS.yml glob into CODEOWNERS syntax.

    CODEOWNERS uses gitignore-style patterns, which differ from OWNERS.yml's
    globs in two ways that matter:

      `specs/**`  ->  `/specs/`   a trailing slash already means "everything
                                  under here", and `**` is not special
      `OWNERS.yml` -> `/OWNERS.yml`  unanchored patterns match at ANY depth,
                                  so a bare name would also match
                                  `apps/web/OWNERS.yml`. Anchor everything.
    """
    p = glob.strip()
    if p.endswith("/**"):
        p = p[: -len("/**")] + "/"
    elif p.endswith("/*"):
        p = p[: -len("/*")] + "/"
    return "/" + p.lstrip("/")


def _covers(broad: str, narrow: str) -> bool:
    """Does OWNERS.yml glob `broad` contain `narrow`?"""
    if not broad.endswith("/**"):
        return False
    return narrow.startswith(broad[: -len("**")])


def classify(cfg: dict) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Split precedence into human-only paths and agent carve-outs inside them.

    Walks `precedence` IN ORDER, which is the whole point. A non-HUMAN rule
    that appears BEFORE a HUMAN rule covering the same tree is a carve-out:
    first-match-wins means the agent owns it, and the human lock below does not
    apply. OWNERS.yml says so out loud at the auth-agent entry -- "Must precede
    the infra/** lock below".

    Returns (human_paths, carve_outs) where a carve-out is
    (path, real_owner, the_human_path_it_sits_inside).
    """
    rules = cfg.get("precedence", [])
    human_paths: list[str] = []
    carve_outs: list[tuple[str, str, str]] = []

    for i, rule in enumerate(rules):
        if rule.get("owner") != HUMAN:
            continue
        for hp in rule.get("paths", []):
            human_paths.append(hp)
            # Only rules EARLIER in the list can override this one.
            for earlier in rules[:i]:
                owner = earlier.get("owner")
                if owner == HUMAN:
                    continue
                for ap in earlier.get("paths", []):
                    if _covers(hp, ap):
                        carve_outs.append((ap, owner, hp))
    return human_paths, carve_outs


def render(cfg: dict) -> str:
    human = accounts(cfg).get("human", "").strip()
    if not human:
        raise SystemExit("OWNERS.yml has no accounts.human — cannot generate CODEOWNERS")
    at = "@" + human.lstrip("@")

    human_paths, carve_outs = classify(cfg)
    carved = {ap for ap, _, _ in carve_outs}

    lines = [
        "# CODEOWNERS -- GENERATED from OWNERS.yml. Do not edit by hand.",
        "#   regenerate:  uv run --with pyyaml python tools/op-cli/gen_codeowners.py",
        "#   verified by: check_drift.py, which fails if this drifts",
        "#",
        "# Ownership is enforced in layers (ADR-0007). Layers 1 and 2 -- the agent's",
        "# own definition and the pre-commit hook -- are local, and both are one",
        "# `--no-verify` away from not existing.",
        "#",
        "# WHAT THIS FILE DOES: requests a human reviewer on the pull request.",
        "# WHAT IT DOES NOT DO: block the merge -- yet. Ruleset 21628724 is active on",
        "# the default branch (1 approval, thread resolution, squash-only), but it",
        "# sets `require_code_owner_review: false`. Flipping that one flag is what",
        "# makes this file blocking. The repository is public and server-side rules",
        "# are available; the gap is a setting, not the platform.",
        "#",
        "# The `Agent boundaries (layer 3)` job in guards.yml re-checks every commit",
        "# against OWNERS.yml. NOTE: it is not yet in the ruleset's required status",
        "# checks (those are: OWNERS.yml drift, Path routing, Onion layers), so it",
        "# reports but does not yet block either.",
        "#",
        "# ORDER: CODEOWNERS is LAST match wins -- the exact opposite of OWNERS.yml,",
        "# which is FIRST match wins. Precedence is therefore emitted in REVERSE,",
        "# and the catch-all comes first. Do not sort this file.",
        "",
        "# A human is asked to review every pull request. Caveat, because the file",
        "# should not overstate itself: GitHub never requests review from the PR's",
        f"# own author, so a pull request opened by {at} gets no reviewer from this",
        "# line. It covers agent-opened pull requests, which is the case that matters.",
        f"*   {at}",
        "",
        "# Paths NO AGENT MAY EVER WRITE. A spec is what a human approves, and an",
        "# agent that could edit OWNERS.yml could widen its own boundary from inside.",
    ]

    seen: set[str] = set()
    for glob in human_paths:
        if glob in carved:
            continue
        pat = to_codeowners_pattern(glob)
        if pat in seen:
            continue
        seen.add(pat)
        lines.append(f"{pat:<28}{at}")

    if carve_outs:
        lines += [
            "",
            "# Carve-outs: these sit INSIDE a human-owned tree above, but OWNERS.yml",
            "# lists them earlier, and first-match-wins means the agent owns them.",
            "# They are not human-only, so they do not belong in the block above.",
            f"# The reviewer stays {at} because there is only one human here; the",
            "# owner named on each line is the agent that may WRITE it.",
        ]
        for ap, owner, inside in carve_outs:
            pat = to_codeowners_pattern(ap)
            if pat in seen:
                continue
            seen.add(pat)
            lines.append(f"{pat:<28}{at}   # written by {owner}, inside {inside}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    cfg = load()
    new = render(cfg)
    check = "--check" in sys.argv

    old = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if old == new:
        print(f"{OUT.relative_to(ROOT)} unchanged")
        return 0

    if check:
        if old is None:
            print(f"{OUT.relative_to(ROOT)} does not exist — regenerate it:", file=sys.stderr)
        else:
            print(f"{OUT.relative_to(ROOT)} does not match OWNERS.yml — regenerate it:", file=sys.stderr)
        print("    uv run --with pyyaml python tools/op-cli/gen_codeowners.py", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
