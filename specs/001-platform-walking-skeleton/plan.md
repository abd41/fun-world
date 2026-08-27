# Implementation Plan: Platform Walking Skeleton

**Branch**: `001-platform-walking-skeleton` | **Date**: 2026-08-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-platform-walking-skeleton/spec.md`

## Summary

One `Title` record travels from Postgres, through a Django API, into a generated
TypeScript contract, and onto two screens — a laptop browser and a physical
phone. Nothing else.

The spec deliberately names no technology. This plan does, because the stack was
settled in ADRs 0002–0016 and re-deciding it per feature is how a project loses
its shape.

The three things most likely to go wrong, and where each is handled:

| Risk | Handled by |
|---|---|
| The phone cannot reach the API (`localhost` resolves to the phone) | One **configurable** `FW_HOST` flowing to all three clients; auto-detected only as a fallback, never overwriting a set value, so swapping to a VPN hostname later is a one-line edit (§FR-007) |
| Setup works only on this machine | `scripts/setup`, proven on a runner that starts with nothing (§FR-012) |
| Five paths no agent can claim, so tasks deadlock | `OWNERS.yml` amendment, **before any other task** |

## Technical Context

**Language/Version**: Python 3.13 (API, managed by uv) · TypeScript 5.x on Node 22 (clients)

**Primary Dependencies**: Django 6.0 + django-ninja (API) · Next.js 16 App Router (web) · Expo SDK 57 (phone) · `@hey-api/openapi-ts` (contract generation)

**Storage**: PostgreSQL 17 in Docker, published on `:5433` to avoid colliding with any host Postgres

**Testing**: pytest (API) · Vitest (clients) · `import-linter` (layering) · existing `test_resolve.py` (routing)

**Target Platform**: One laptop as server; clients are a desktop browser and a physical Android/iOS handset on the same Wi-Fi. No public exposure (constitution §5).

**Project Type**: Polyglot monorepo — one Python service, two TypeScript clients, one generated package between them

**Performance Goals**: None. This vertical is about correctness of wiring; any performance target here would be measuring the wrong thing and would invite premature optimisation.

**Constraints**: No runtime egress (§29) · no hardcoded hosts (FR-007) · dependencies point inward (§32) · no paid services (§27)

**Scale/Scope**: One title, one endpoint, two screens. Roughly 15 files of application code.

## Constitution Check

*GATE: Must pass before Phase 0. Re-checked after Phase 1.*

| Principle | Applies how | Status |
|---|---|---|
| §5 No public exposure | Compose publishes to the LAN; no tunnel, no port forward | PASS |
| §6 No third-party telemetry | `NEXT_TELEMETRY_DISABLED=1`; Expo telemetry off | PASS |
| §7 No hardcoded hosts | The central design problem of this vertical — see Phase 0 | PASS by design |
| §8 Path ownership absolute | **5 paths currently unowned — blocks work until amended** | ⚠ PREREQUISITE |
| §12 Contracts generated | `packages/contracts` from `openapi.json`; CI diff gate | PASS |
| §14 Tokens only source of colour | No colour at all this vertical — unstyled text | N/A |
| §15 Web and mobile implement same `ui-spec` | No `ui-spec` entries yet; both render the same field | PASS |
| §17–18 Auth | Out of scope; vertical 004 | N/A |
| §20 qa-agent writes only tests | Tests live under paths qa-agent owns | PASS |
| §29 Assets vendored | No assets this vertical | N/A |
| §32 Dependencies point inward | `import-linter` runs against real code for the first time | PASS by design |

**One gate fails.** §8 is not satisfiable today: `scripts/setup`, `apps/api/pyproject.toml`, `apps/api/manage.py`, `apps/api/config/settings.py` and `apps/api/config/urls.py` resolve to `UNOWNED`, and unowned refuses a claim. Every task touching them would deadlock.

Resolution is in Phase 0 and is task T001 — it must land before anything else.

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-walking-skeleton/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0 — the three hard decisions
├── data-model.md        # Phase 1 — the Title entity
├── contracts/
│   └── titles.md        # Phase 1 — the one endpoint's contract
├── quickstart.md        # Phase 1 — how to prove it works
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
scripts/
└── setup                       HUMAN — the front door; SC-005a tests this

infra/                          HUMAN
├── docker-compose.yml          postgres :5433, caddy :8090
└── Caddyfile

apps/api/                       Python 3.13, uv
├── pyproject.toml              HUMAN — project scaffold
├── manage.py                   HUMAN
├── config/                     HUMAN — settings, urls, INSTALLED_APPS
│   ├── settings.py
│   └── urls.py
├── core/                       data-agent
│   ├── models.py               Title ORM model
│   ├── admin.py                registers Title (satisfies FR-009)
│   └── migrations/
└── catalog/                    api-agent
    ├── domain/title.py         plain dataclass — no Django import (§32)
    ├── application/list_titles.py
    └── api.py                  django-ninja router

packages/contracts/             contract-keeper — GENERATED, never authored

apps/web/                       web-agent — Next.js 16
└── app/page.tsx                renders the title

apps/mobile/                    mobile-agent — Expo 57
└── app/index.tsx               renders the same title
```

**Structure Decision**: The monorepo layout from ADR-0005 and ADR-0006, filled
in for the first time. `apps/api` follows ADR-0016's onion layering **only in
`catalog/`**, where a rule exists worth isolating. `core/` holds the ORM model
and admin registration with no layering, because a `Title` with a name has no
business rule to protect and four layers around it would be ceremony.

That asymmetry is deliberate and is the first live test of §32's "applied where
business rules are non-trivial, not uniformly".

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `catalog/` has domain + application layers for one read | ADR-0016 must be exercised against real code before verticals with actual rules depend on it | Deferring layering to vertical 003 means retrofitting it into an existing `api.py` — the exact expensive path the ADR exists to avoid |
| Two clients rendering identical text | FR-004 and SC-001 require the phone specifically; the laptop cannot prove the phone case | One client would leave the highest-risk assumption (a device that is not this machine can reach the API) untested until vertical 006 |
| A `scripts/setup` for a project with three commands | FR-012 and SC-005a; prose in a README is not executed and drifts silently | A documented list of steps cannot be verified by CI, so "works from a clean checkout" would remain an assertion |
