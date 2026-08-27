#!/usr/bin/env python3
"""Generate .claude/agents/*.md from OWNERS.yml.

The agent definitions are DERIVED, never hand-written. OWNERS.yml is the one
source of truth for boundaries; if these two ever disagree, the boundary an
agent believes in is not the boundary that gets enforced -- which is the
failure this generator exists to make impossible.

Re-run after any OWNERS.yml change:   python tools/op-cli/gen_agents.py
Check for drift in CI:                python tools/op-cli/gen_agents.py --check
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OWNERS = ROOT / "OWNERS.yml"
OUT_DIR = ROOT / ".claude" / "agents"

# Every agent gets the same tools. The boundary is enforced by op-cli and the
# pre-commit guard, not by withholding an editor -- an agent that cannot read
# widely makes worse decisions, and one that cannot write at all cannot work.
TOOLS = "Read, Write, Edit, Glob, Grep, Bash"

TEMPLATE = """---
name: {name}
description: {description}
tools: {tools}
model: {model}
---

You are `{name}` on the Fun World project: a private, self-hosted streaming
app. Django 6 + django-ninja API, Next.js 16 web, Expo 57 phone and Android TV.

## Your job

{job}

## Your boundary — this is not advisory

You may write **only** to these paths:

{writes_block}

You may read:

{reads_block}

Writing outside your allowlist is rejected by the pre-commit guard and by
`op-cli`. There is no exception and no emergency that justifies it.

**If you need a change outside your boundary**, you do not make it and you do
not ask another agent to make it. You split the work package by path
(`op-cli split --wp <id> --by-paths`), which routes each child to whichever
agent owns those paths. You never choose a recipient; routing is a lookup in
`OWNERS.yml`, and that is precisely why hand-off loops cannot form here.

## Working a ticket

```
op-cli claim   --wp <id> --agent {name}   # refuses if the paths are not yours
#   ... do the work, inside your boundary ...
op-cli done    --wp <id> --pr <n>         # links the PR, moves to In testing
```

Open a pull request. Never push directly to the default branch.

## Rules that bind you

Read `.specify/memory/constitution.md` before planning anything. The ones that
catch people out most often:

- **`packages/contracts` is generated**, never authored by hand.
- **No literal hex colours** outside `packages/tokens`.
- **No hardcoded hosts** — every URL comes from env, or the phone and both
  televisions break in a way nobody notices until they are standing in front
  of one.
- **No public exposure, no third-party telemetry, no paid services.**
- **Never edit `OWNERS.yml` or the constitution.** They are human-owned.
"""


def block(items: list[str], empty: str) -> str:
    if not items:
        return f"- _{empty}_"
    return "\n".join(f"- `{i}`" for i in items)


def render(name: str, spec: dict) -> str:
    job = " ".join(str(spec.get("job", "")).split())
    reads = spec.get("reads") or []
    reads_rendered = (
        "- everything in the repo" if reads == ["**"] else block(reads, "nothing outside your own paths")
    )
    return TEMPLATE.format(
        name=name,
        description=job.rstrip(".") + ".",
        tools=TOOLS,
        model="sonnet" if name in {"contract-keeper", "op-agent"} else "opus",
        job=job,
        writes_block=block(spec.get("writes") or [], "no write access"),
        reads_block=reads_rendered,
    )


def main() -> int:
    check = "--check" in sys.argv
    owners = yaml.safe_load(OWNERS.read_text(encoding="utf-8"))["owners"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    drift: list[str] = []
    for name, spec in owners.items():
        path = OUT_DIR / f"{name}.md"
        new = render(name, spec)
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if new == old:
            print(f"  unchanged  {path.relative_to(ROOT)}")
            continue
        if check:
            drift.append(str(path.relative_to(ROOT)))
            continue
        path.write_text(new, encoding="utf-8")
        print(f"  {'updated' if old else 'created'}    {path.relative_to(ROOT)}")

    # An agent file with no OWNERS entry would be a boundary nobody enforces.
    known = {f"{n}.md" for n in owners}
    for stray in sorted(p for p in OUT_DIR.glob("*.md") if p.name not in known):
        print(f"  ORPHAN     {stray.relative_to(ROOT)} — no OWNERS.yml entry", file=sys.stderr)
        drift.append(str(stray.relative_to(ROOT)))

    if check and drift:
        print(f"\nDRIFT: {len(drift)} file(s) out of sync with OWNERS.yml", file=sys.stderr)
        print("Run: python tools/op-cli/gen_agents.py", file=sys.stderr)
        return 1
    print(f"\n{len(owners)} agent definitions in sync with OWNERS.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
