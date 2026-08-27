# 0006. Generate the client contract from OpenAPI

- **Status:** Accepted
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
