#!/usr/bin/env python3
"""Generate .github/CODEOWNERS from OWNERS.yml.

Generated, never hand-written. A second hand-maintained ownership table drifts
from the first within a few weeks, and then two files disagree about who owns
what -- which is the failure `check_drift.py` already exists to catch. So this
derives from the same source and `check_drift.py` verifies it still matches.

BE HONEST ABOUT WHAT THIS FILE BUYS. On a private repo on the free tier there
is no branch protection and no required review (the same limitation
`check_push.py` documents), so a CODEOWNERS entry requests a reviewer -- it
does not compel one. That makes it useful and insufficient at the same time.

The enforcing half of layer 3 is the `boundaries` job in guards.yml, which
re-checks every commit in the PR against OWNERS.yml where `--no-verify`
cannot reach. This file is the part that puts a human's name in front of a
change; that job is the part that fails the build.

Only HUMAN-owned paths get an entry. Agents have no GitHub identity of their
own -- they share one account -- so there is nobody to assign an agent-owned
path to, and inventing a mapping would state something untrue.

Run:    python tools/op-cli/gen_codeowners.py
Check:  python tools/op-cli/gen_codeowners.py --check
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


def human_paths(cfg: dict) -> list[str]:
    out: list[str] = []
    for rule in cfg.get("precedence", []):
        if rule.get("owner") == HUMAN:
            out.extend(rule.get("paths", []))
    return out


def render(cfg: dict) -> str:
    human = accounts(cfg).get("human", "").strip()
    if not human:
        raise SystemExit("OWNERS.yml has no accounts.human — cannot generate CODEOWNERS")
    at = "@" + human.lstrip("@")

    lines = [
        "# CODEOWNERS -- GENERATED from OWNERS.yml. Do not edit by hand.",
        "#   regenerate:  python tools/op-cli/gen_codeowners.py",
        "#   verified by: check_drift.py, which fails if this drifts",
        "#",
        "# Enforcement layer 3 of 3 (ADR-0007). Layers 1 and 2 -- the agent's own",
        "# definition and the pre-commit hook -- are both local and both one",
        "# `--no-verify` away from not existing.",
        "#",
        "# What this file does: puts a human reviewer on the PR.",
        "# What it does NOT do: block the merge. There is no branch protection on a",
        "# private repo on the free tier, so a review request here is advisory.",
        "# The half that fails the build is the `boundaries` job in guards.yml.",
        "#",
        "# NOTE ON ORDER: CODEOWNERS is LAST match wins -- the opposite of",
        "# OWNERS.yml, which is first match wins. The catch-all is therefore first",
        "# and the specific paths follow it, which is the reverse of how OWNERS.yml",
        "# reads. Do not sort this file.",
        "",
        "# Every pull request gets a human reviewer. The PR template already",
        "# requires \"a human approved\"; this is that requirement, mechanised as far",
        "# as the platform allows.",
        f"*   {at}",
        "",
        "# Paths NO AGENT MAY EVER WRITE. These are the ones worth a person's eyes:",
        "# a spec is what a human approves, and an agent that could edit OWNERS.yml",
        "# could widen its own boundary from the inside.",
    ]

    seen: set[str] = set()
    for glob in human_paths(cfg):
        pat = to_codeowners_pattern(glob)
        if pat in seen:
            continue
        seen.add(pat)
        lines.append(f"{pat:<28}{at}")

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
            print(f"{OUT.relative_to(ROOT)} does not exist — run gen_codeowners.py", file=sys.stderr)
        else:
            print(f"{OUT.relative_to(ROOT)} does not match OWNERS.yml — regenerate it", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
