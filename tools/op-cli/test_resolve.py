#!/usr/bin/env python3
"""Tests for path -> owner routing.

These are the cheapest tests in the repo and the most load-bearing: if routing
is wrong, an agent writes somewhere it should not, and every other guarantee
in the constitution rests on it holding.

Run: python tools/op-cli/test_resolve.py
"""
from __future__ import annotations

import sys

from owners import HUMAN, UNOWNED, resolve, route

# (path, expected owner, why this case is here)
CASES: list[tuple[str, str, str]] = [
    ("OWNERS.yml", HUMAN, "an agent that could edit this could widen its own boundary"),
    (".specify/memory/constitution.md", HUMAN, "the rules are not agent-editable"),
    (".env.local", HUMAN, "secrets"),
    ("infra/docker-compose.yml", HUMAN, "container + network config is human-owned"),
    ("infra/keycloak/realm/fun-world.json", "auth-agent", "the one carve-out inside infra/"),

    ("apps/api/catalog/views.py", "api-agent", "plain app code"),
    ("apps/api/catalog/tests/test_titles.py", "qa-agent",
     "CONFLICT CASE: matches api-agent's dir AND qa's **/tests/** — qa must win"),
    ("apps/api/core/models.py", "data-agent", "only data-agent writes models"),
    ("apps/api/core/migrations/0001_initial.py", "data-agent", "only data-agent writes migrations"),
    ("apps/api/oauth/device.py", "auth-agent", "RFC 8628 device grant lives here"),

    ("apps/mobile/src/screens/Home.tsx", "mobile-agent", "phone screen"),
    ("apps/mobile/src/tv/Rail.tsx", "tv-agent",
     "CONFLICT CASE: inside apps/mobile/** but TV is a different interaction model"),

    ("apps/web/app/browse/page.tsx", "web-agent", "next.js route"),
    ("packages/contracts/index.ts", "contract-keeper", "generated types have one writer"),
    ("packages/tokens/base.json", "design-system", "the only source of colour"),
    ("tools/media/ladder.sh", "media-agent", "ffmpeg pipeline"),
    ("tools/op-cli/main.py", "op-agent", "op-cli owns itself"),
    ("e2e/playback.spec.ts", "qa-agent", "e2e is qa's"),

    ("README.md", UNOWNED, "no rule covers it — a claim must be REFUSED, not allowed"),

    # Newly protected after the guard found these unowned:
    (".claude/agents/web-agent.md", HUMAN,
     "an agent rewriting its own definition would drift from what OWNERS enforces"),
    ("specs/004-identity/spec.md", HUMAN, "an agent that edits the spec approves its own work"),
    ("package.json", HUMAN, "build config"),
    ("turbo.json", HUMAN, "build config"),
]


def main() -> int:
    width = max(len(c[0]) for c in CASES)
    failures = []

    for path, expected, why in CASES:
        got = resolve(path)
        ok = got.owner == expected
        if not ok:
            failures.append((path, expected, got.owner, why))
        print(f"{'ok  ' if ok else 'FAIL'} {path:<{width}}  {got.owner:<16} {got.rule}")
        if not ok:
            print(f"       expected {expected} — {why}")

    # A ticket spanning two owners must be reported as splittable, not assigned.
    spanning = ["apps/api/catalog/views.py", "apps/web/app/browse/page.tsx"]
    grouped = route(spanning)
    print(f"\nrouting a 2-owner ticket -> {sorted(grouped)}")
    if len(grouped) != 2:
        failures.append(("split detection", "2 owners", str(sorted(grouped)), "must force a split"))
        print("FAIL  a ticket spanning two owners must split, not assign")
    else:
        print("ok    correctly requires a split")

    print(f"\n{len(CASES) + 1 - len(failures)}/{len(CASES) + 1} passed")
    if failures:
        print(f"\n{len(failures)} FAILURE(S) — fix OWNERS.yml before any agent runs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
