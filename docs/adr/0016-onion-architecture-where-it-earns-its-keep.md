# 0016. Onion architecture, where it earns its keep

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

The API needs a structure decided before code exists, because layering is the
one thing that cannot be retrofitted cheaply. Once `views.py` imports the ORM
and the ORM leaks into business rules, unpicking it is a rewrite.

Onion architecture was proposed, via
[this article](https://codefinity.com/blog/Onion-Architecture-in-Software-Development).

**One correction, because it matters.** That article states *"Inner layers
depend only on outer layers."* That is inverted. The rule is:

> **Dependencies point inward. The domain core depends on nothing.**

Implementing it as written would produce exactly the coupling the pattern
exists to prevent, so the source is noted here rather than followed literally.

**The tension worth naming:** Django actively resists this. Its ORM is Active
Record — models *are* the persistence layer — and Django admin needs real ORM
models, which is precisely why Django was chosen (ADR-0004). Pure domain
entities held separately from ORM models means mapping code in both
directions, forever.

## Decision

Adopt Onion in `apps/api`, with dependencies pointing inward:

```
presentation/    django-ninja routers, Pydantic schemas, Django admin
       |         depends on -> application
       v
application/     use cases: StartPlayback, RecordProgress,
       |         ListContinueWatching. Defines the repository interfaces
       v         it needs; depends on -> domain only
domain/          entities and business rules as plain dataclasses.
                 Depends on NOTHING. No Django import, ever.

infrastructure/  ORM models, repository implementations, the HLS signer.
                 Depends inward on application + domain, implementing the
                 interfaces they declare.
```

**Applied where business rules are non-trivial, not everywhere.** Playback
progress, resume logic, entitlement and kids filtering earn four layers. A
`Genre` lookup does not — forcing it there buys boilerplate and nothing else.
The test: *is there a rule here that would survive changing the database?*

**Enforced by `import-linter` in CI**, not by intention. A layering rule that
lives only in a document erodes in about three weeks. The contract fails the
build if `domain/` imports Django, or if any layer reaches outward.

The frontend follows the same discipline under different names:
`packages/player-core` is already a domain layer — progress maths and resume
rules with no I/O. Pure logic in packages, orchestration in feature modules,
React only at the edge.

## Consequences

- Business rules become testable without a database, a request, or Django.
- The rules that matter are in one place instead of smeared across views.
- Swapping the HLS signer, or Django for something else, touches
  `infrastructure/` only.
- **Cost:** mapping between ORM models and domain entities, in both
  directions. This is the real price and it is paid on every model.
- **Cost:** more files and more indirection. On a solo project that is a
  genuine tax, which is why it is scoped to where rules exist rather than
  applied uniformly.
- **Cost:** Django admin binds to ORM models, so the admin is inherently a
  presentation-over-infrastructure shortcut that skips the inner layers. That
  is accepted deliberately — admin is a developer tool, not a product surface.
- **Watch for:** the layering becoming ceremonial — a `domain/` full of
  anaemic dataclasses with no behaviour, and all the logic still in services.
  If that happens the pattern is not paying for itself and should be dropped
  for the areas where it has not landed, rather than defended.
