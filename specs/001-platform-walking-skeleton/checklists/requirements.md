# Specification Quality Checklist: Platform Walking Skeleton

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Two iterations were needed.** The first draft failed *"no implementation
details"* badly — it named Django, django-ninja, Next.js, Expo, hey-api,
Postgres, `GET /api/titles`, `openapi.json`, `import-linter` and the IP address
`192.168.0.106`, all of which came from the feature description. Those are the
right decisions but they belong in `plan.md`; a spec that names them cannot be
validated against anything except itself.

Rewritten in terms of observable behaviour:

| Was | Became |
|---|---|
| `GET /api/titles` returns a Title | The system exposes stored titles to clients (FR-002) |
| hey-api generates from openapi.json | Both clients obtain the shape from one shared definition derived from the server (FR-005) |
| Expo app reaches `192.168.0.106` | Clients contain no hardcoded address; it comes from configuration (FR-007) |
| import-linter passes | Automated guards pass against real code for the first time (FR-011) |

**FR-007 and FR-008 were not in the original description.** They were added
because the edge-case pass surfaced them: the phone-cannot-reach-localhost
problem is the single most likely failure in this vertical, and "no titles" vs
"cannot reach the server" are different states with different fixes that a
naive implementation would collapse into one blank screen.

**SC-005 was split after review, and FR-012 added.** It began as one criterion —
*"a stranger can start it in 15 minutes"* — which reads well and fails the
"measurable" test. Prose in a README is not executed: it drifts the moment a
step changes, and the author never notices because their machine already has
everything installed.

Now **005a** is mechanical (one command, proven on a runner that starts with
nothing) and **005b** is explicitly a judgement call that stays unautomated. The
point of separating them is that 005b cannot be quietly marked done because 005a
passed — they are different claims and only one has a test. FR-012 is the
requirement that makes 005a buildable.

**SC-006 said "all four automated guards" — there are three** (drift, routing,
layering). Corrected to not name a number, since the count will change and a
spec that has to be updated when a CI job is added is a spec that will go stale.

No [NEEDS CLARIFICATION] markers were needed. The description was unusually
specific, and where it was silent — how a maintainer edits a title, what a
client shows when storage is empty — reasonable defaults existed and are
recorded under Assumptions.
