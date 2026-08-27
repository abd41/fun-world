# `@fun-world/contracts`

Generated API types and client. **Nothing in `src/` or `openapi.json` is written
by hand** — constitution §12 makes hand-editing a build failure, not a review
comment.

```bash
pnpm --filter @fun-world/contracts generate
```

## Two steps, both generated

```
apps/api/catalog/api.py          Python routers — the actual source of truth
        |
        |  manage.py export_openapi_schema      (scripts/export-schema.mjs)
        v
openapi.json                     OpenAPI 3.1, committed
        |
        |  @hey-api/openapi-ts                  (openapi-ts.config.ts)
        v
src/                             TypeScript types + fetch client, committed
```

Both artefacts are committed. That is what lets CI regenerate and diff (§13):
drift between the server and its clients becomes a failed build instead of a
runtime surprise on a television.

## Why the schema comes from a file, not a running server

hey-api can read a live URL, which was the obvious first design and is the
wrong one. It would make the drift gate depend on Postgres being up and a port
being bound — and a guard that needs that much scaffolding is a guard that
eventually gets a conditional wrapped around it. Three checks in this repo have
already gone green while enforcing nothing for exactly that reason.

`export_openapi_schema` reads the routers through Django's app registry. It
opens no socket and touches no database — verified with `DATABASE_URL` pointing
at a dead port. So regeneration is a pure function of committed source, which is
what makes the empty-diff check (SC-005) mean anything.

## Using it

`baseUrl` is required and has no default. The OpenAPI document declares
`servers: []`, so there is nothing for a client to fall back to — §7 enforced by
absence rather than by review.

```ts
import { createClient } from "@fun-world/contracts/client";
import { listTitles } from "@fun-world/contracts";

const client = createClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL! });
const { data, error } = await listTitles({ client });
```

`data` is `TitleOut[]`, `error` is set when the request fails. An empty catalog
is `data === []`, **not** an error — FR-008 needs those two states to stay
distinguishable, and this is the seam where they could quietly collapse.

This package ships TypeScript source, not built JavaScript. Consumers must
transpile it: Next.js needs `transpilePackages: ["@fun-world/contracts"]`, Expo
handles workspace packages already.

## Two things that will surprise you

**A docstring edit is a contract change.** django-ninja publishes each view's
docstring as the OpenAPI `description`, so rewording a comment in `api.py`
changes `openapi.json`, changes `src/`, and fails the drift gate until someone
regenerates. That is working as intended — the docs really are part of the
contract — but the first time it happens it looks like a broken build.

**Operation ids are pinned by hand in `api.py`.** django-ninja derives them from
the Python module path, so `catalog/api.py::list_all` generated a client
function called `catalogApiListAll`. That would make the server's file layout
part of the published contract: moving the function would rename what both
clients call, turning a pure refactor into a breaking change. Every route sets
`operation_id` explicitly. New routes must too.
