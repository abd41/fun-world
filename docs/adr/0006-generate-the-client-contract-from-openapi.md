# 0006. Generate the client contract from OpenAPI

- **Status:** Accepted, amended 2026-08-27 (see Amendment)
- **Date:** 2026-08-27

## Context

The API is Python; both clients are TypeScript. A hand-written shared types
package cannot span that boundary. It would be maintained twice and drift
silently, surfacing as a runtime error in a client long after the server
changed.

## Decision

django-ninja emits OpenAPI 3.1 from its Pydantic v2 schemas.
`@hey-api/openapi-ts` generates `packages/contracts`: TypeScript types, Zod
schemas and TanStack Query hooks.

`packages/contracts` is **generated, never authored**. Hand-editing it is a
build failure. CI regenerates on every pull request and fails on a non-empty
diff.

## Consequences

- Client/server drift becomes structurally impossible, not discouraged.
- The polyglot split costs about twenty lines of config.
- Contract-first API design is itself worth learning.
- **Cost:** a codegen step in the loop; the API must run to regenerate.
- **Cost:** generated code is noisy in diffs. Acceptable, nobody reads it.

## Amendment — 2026-08-27, on implementing T011

Review of PR #15 found the implementation contradicting this ADR on two points
without saying so. The decision stands; two details in it were wrong.

**"the API must run to regenerate" is reversed.** It does not, and deliberately
so. `manage.py export_openapi_schema` reads the routers through Django's app
registry and writes the document with no socket bound and no database touched
— verified with `DATABASE_URL` pointing at a dead port. `openapi.json` is
committed and hey-api generates from that file.

This matters more than a detail. Generating from a live URL would make the CI
drift gate depend on Postgres being up and a port being bound, and a guard that
needs that much scaffolding is a guard that ends up wrapped in a conditional.
Three checks in this repo went green while enforcing nothing for exactly that
reason. Regeneration is now a pure function of committed source.

**Zod schemas and TanStack Query hooks are not generated.** Only types, the SDK
functions and the fetch client are. Nothing in vertical 001 validates a response
at runtime or caches a query, and generating unused surface would mean two more
plugin versions to pin and more output for the empty-diff gate to be unstable
about. They are worth adding at the vertical that first needs them — Zod when
an endpoint takes untrusted input, TanStack when a client has enough state to
justify it — and this ADR should be amended again rather than the plugins added
quietly.

**One consequence to add:** the OpenAPI `description` of every operation is its
Python docstring, so rewording a comment in `api.py` is a contract change and
fails the drift gate until someone regenerates. That is correct behaviour and
it surprises people the first time.

