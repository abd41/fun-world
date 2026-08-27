# Contract — Titles

One endpoint. This document describes what the API promises; the machine-readable
form is `openapi.json`, emitted by django-ninja, and `packages/contracts` is
generated from that.

**This file is documentation. `openapi.json` is the contract.** If they disagree,
the generated artefact wins and this file is wrong.

## `GET /api/titles`

Returns every title. No pagination, no filtering, no ordering guarantees —
all three are vertical 003 concerns and adding them here would mean the clients
exercise code this vertical is not testing.

### Response `200`

```json
[
  {
    "id": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f607",
    "name": "Big Buck Bunny"
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Stable identifier |
| `name` | string | Display name |

`created_at` is **not** exposed. It exists for provenance and idempotent
seeding; no client needs it, and a field in the contract is a field two clients
can come to depend on.

### Empty catalog

```json
[]
```

An empty array, **not** `404` and not an error object. FR-008 requires clients
to distinguish "no titles" from "cannot reach the server", and that distinction
is only possible if the empty case is a successful response. A `404` here would
collapse both states into one failure path — the exact bug FR-008 exists to
prevent.

### Errors

This vertical defines no error responses. If the database is unreachable, Django
returns `500` and the clients treat any non-`200` as "cannot reach the server"
(FR-008). Structured error bodies arrive when there is something worth
structuring — a client cannot act differently on a well-formed 500 than on a
malformed one.

## What the clients may assume

- The response is an array, possibly empty.
- `id` and `name` are always present on every element.
- Nothing about ordering. A client that depends on the first element being
  stable is relying on Postgres's physical row order, which is not a promise.

## What generation guarantees

`packages/contracts` is produced by `@hey-api/openapi-ts` from `openapi.json`
and is never hand-edited (constitution §12). CI regenerates and fails on a
non-empty diff.

The consequence worth stating plainly, because it is the property SC-004 exists
to demonstrate: **renaming `name` on the server breaks the client build**, with
an error naming the field. That failure is the feature. A pipeline where the
server can change shape and the clients keep compiling is a pipeline that will
fail at runtime instead, in front of a television.
