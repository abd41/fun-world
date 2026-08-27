# 0007. Path ownership, resolved first-match-wins

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Multiple agents writing one repository collide. Assigning work by feature
leaks immediately: two agents both "own" playback and both edit the API.

A subtler problem: **agents choosing who to hand work to** is the number one
documented failure mode in multi-agent systems. A hands to B, B to C, C back
to A, context lost at every hop, nobody owning the outcome.

## Decision

Boundaries are **directory paths** in `OWNERS.yml`. Exactly one agent may
write each path. Assignment is **derived** from the paths a ticket declares,
never chosen by an agent.

Resolution is **top-down, first-match-wins** (firewall semantics),
deliberately not "most specific wins" -- which is undefined when globs
overlap. `apps/api/catalog/tests/x.py` matches both `apps/api/catalog/**`
and `**/tests/**`, and neither is obviously more specific. An ordered list
has exactly one answer, always.

`OWNERS.yml` is **human-owned**: an agent that could edit it could widen its
own boundary.

## Consequences

- Hand-off loops cannot form. Routing is a pure function of paths.
- Web and mobile can work the same feature in parallel without negotiating.
- An agent that cannot finish a ticket **splits** it rather than passing it.
- Enforced in three layers: agent definition, pre-commit guard, CODEOWNERS.
- **Cost:** cross-boundary changes route through a spec amendment rather
  than a quick edit. That slowness is the feature.
- **Cost:** unowned paths refuse claims, so the map must be kept current.
  Running the guard found `.claude/**`, `specs/**` and the root build config
  sitting unowned.
