# Phase 1 — Data Model

One entity. The restraint is the point: this vertical tests the pipeline's
shape, not the catalog's.

## Title

A single item of watchable content.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key. UUID rather than a sequential integer because IDs will appear in playback URLs from vertical 005, and a guessable catalog is an avoidable mistake to design in now. |
| `name` | string, max 200 | Displayed by both clients. The one field this vertical actually exercises. |
| `created_at` | timestamp | Set on insert. Present so the seed is idempotent by name and the record has provenance. |

**No other fields.** Everything a `Title` will eventually need — `kind`, `year`,
`licence`, `attribution`, seasons, artwork, renditions — belongs to vertical 003
and is listed in the spec's Out of Scope. Adding any of them here would make the
data model the subject of review rather than the pipeline.

### Validation

- `name` is required and non-empty after trimming. An untitled title is
  meaningless and would render as a blank screen, which FR-008 says must be
  distinguishable from "no titles at all".
- `name` is not unique. Two films can share a name; enforcing uniqueness here
  would encode a rule the domain does not have.

### Where it lives — and the deliberate asymmetry

The same concept appears in two layers, and this is the first live test of
constitution §32 and ADR-0016:

```
apps/api/core/models.py          Title (Django ORM)      data-agent
apps/api/catalog/domain/title.py Title (plain dataclass)  api-agent
```

**Why both.** The ORM model is infrastructure: it knows about columns, indexes
and Django admin. The dataclass is the domain: plain Python, no framework
import, the thing `import-linter` will assert stays clean.

**Why this looks like overkill, and is accepted anyway.** For a two-field entity
with no behaviour, the mapping between them is pure cost. ADR-0016 says onion
applies "where business rules are non-trivial", and by its own test — *would
this rule survive changing the database?* — a `Title` with a name would not
qualify.

It is done here regardless, for one reason: **`import-linter` has never run
against real code.** A contract that only passes because the package is empty
proves nothing. This vertical is where the layering is verified to actually
work, and doing that on the simplest possible entity is cheaper than discovering
a broken contract during vertical 008.

The plan records this under Complexity Tracking rather than leaving it to look
like an accident. If the mapping is still pure ceremony by vertical 003, that is
evidence against the pattern and ADR-0016 should be revisited — not defended.

### Seed data

One row, inserted idempotently by `scripts/setup`:

```
name: "Big Buck Bunny"
```

A Blender Foundation open movie (CC-BY), so the placeholder is already something
vertical 003 can keep rather than throw away. No `licence` or `attribution`
column exists yet to record that — those arrive with 003, and constitution §3
only bites once content is actually served.

Idempotence is by `name`: re-running setup must not produce a second Big Buck
Bunny.

## State transitions

None. A `Title` in this vertical is created by the seed or by an administrator
and then read. Publication states, availability windows and ingest status all
belong to vertical 012.
