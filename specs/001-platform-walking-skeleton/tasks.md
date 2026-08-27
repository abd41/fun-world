---

description: "Task list for vertical 001 — platform walking skeleton"
---

# Tasks: Platform Walking Skeleton

**Input**: Design documents from `specs/001-platform-walking-skeleton/`

**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/titles.md

**Tests**: Included. The spec's SC-004 requires demonstrating that a contract
change breaks the client build, and FR-008 requires two failure states to be
distinguishable — neither is credible without a test.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelisable — different paths, different owners, no dependency
- **[Story]**: US1, US2, US3 from spec.md
- Every task names its **owner** and the **paths** it touches, because `op-cli`
  routes on paths and refuses a claim that spans owners

## Ownership is the scheduling constraint

Unusually for a task list, **who can do a task is determined by the paths it
touches**, not by who is free. `op-cli claim` refuses a ticket whose paths are
unowned or resolve to more than one agent, so a task that spans a boundary is
not "harder" — it is unclaimable, and must be split.

This is why T001 exists and why nothing can start before it.

---

## Phase 1: Setup — all HUMAN-owned, and blocking

**Purpose**: Create the structure agents will work inside. Every task here
touches human-owned paths by design (constitution §8, ADR-0007).

- [ ] T001 **[BLOCKS EVERYTHING]** Close 8 ownership gaps in `OWNERS.yml` — owner: **HUMAN** — paths: `OWNERS.yml`
  - Add to the HUMAN precedence block: `scripts/**`, `apps/api/pyproject.toml`, `apps/api/manage.py`, `apps/api/config/**`
  - Change `data-agent` from three specific files to the whole Django app: `apps/api/core/**`
  - **Why the second change matters**: `data-agent` currently owns `core/models.py` and `core/admin.py` by name, so `core/apps.py`, `core/__init__.py` and `core/management/commands/seed.py` are unowned — its own app is full of files it cannot write. Listing files instead of the directory was the modelling error.
  - Regenerate agents (`pnpm agents:gen`), extend `test_resolve.py` with the 8 paths, confirm 0 gaps
  - **Verify**: every path in T002–T021 resolves to exactly one owner

- [ ] T002 Django project scaffold — owner: **HUMAN** — paths: `apps/api/pyproject.toml`, `apps/api/manage.py`, `apps/api/config/settings.py`, `apps/api/config/urls.py`
  - `uv init`, add `django~=6.0`, `django-ninja`, `psycopg[binary]`, `django-environ`
  - `settings.py`: database from env, `ALLOWED_HOSTS` from `FW_HOST`, bind `0.0.0.0`
  - **No secrets and no addresses in the file** — both come from env (FR-007)

- [ ] T003 `scripts/setup` — owner: **HUMAN** — paths: `scripts/setup`
  - Order per research R3: toolchain check → resolve `FW_HOST` → compose `--wait` → `uv sync` → migrate → seed → `pnpm install` → generate contracts → print URLs + elapsed
  - `FW_HOST` resolution: environment → `.env` → auto-detect. **Never overwrite a set value** (research R2); report which source was used
  - Idempotent: running twice must not duplicate the seed or clobber `.env`

- [ ] T004 [P] Document `FW_HOST` — owner: **HUMAN** — paths: `.env.example`
  - Show all three valid forms: LAN IP, mDNS name, Tailscale MagicDNS name
  - State that pinning it is the recommended end state, not the fallback

**Checkpoint**: `./scripts/setup` runs to completion on this machine. Agents can now claim work.

---

## Phase 2: Foundational — the data, before any client

**Purpose**: A `Title` must exist and be editable before anything can display it.

- [ ] T005 Django `core` app with the Title model — owner: **data-agent** — paths: `apps/api/core/apps.py`, `apps/api/core/models.py`, `apps/api/core/migrations/`
  - Fields exactly per data-model.md: `id` (UUID pk), `name` (≤200, required, non-empty after trim), `created_at`
  - **Nothing else.** `kind`, `year`, `licence` and artwork belong to vertical 003; adding them makes the data model the subject of review instead of the pipeline

- [ ] T006 [P] Register Title in Django admin — owner: **data-agent** — paths: `apps/api/core/admin.py`
  - Satisfies FR-009: a maintainer edits a title without writing code
  - List display and search on `name`, so SC-002 is one click rather than a query

- [ ] T007 Idempotent seed command — owner: **data-agent** — paths: `apps/api/core/management/commands/seed.py`
  - Inserts one Title, `name="Big Buck Bunny"` (CC-BY, so vertical 003 can keep it)
  - **Idempotent by `name`** — `scripts/setup` runs it every time and must not accumulate duplicates

- [ ] T008 [P] CI job: setup on a clean runner — owner: **op-agent** — paths: `.github/workflows/setup.yml`
  - `ubuntu-latest`, checkout, run `./scripts/setup`, assert the API answers
  - Satisfies **SC-005a only**. Add a comment saying so explicitly: this job cannot cover Docker Desktop, LAN detection against WSL/Hyper-V adapters, or the firewall rule, and **must not be treated as evidence for SC-005b**

**Checkpoint**: A title exists in Postgres and is editable in the admin.

---

## Phase 3: User Story 1 — see a title on the laptop (P1) 🎯 MVP

**Goal**: The stored title's name renders in a browser on the development machine.

**Independent Test**: Open the web app; the name appears; change it in the admin and reload; the new name appears.

- [ ] T009 [US1] Domain and application layers — owner: **api-agent** — paths: `apps/api/catalog/domain/title.py`, `apps/api/catalog/application/list_titles.py`
  - `domain/title.py`: plain dataclass, **no Django import, no Pydantic** (§32, `.importlinter`)
  - `application/list_titles.py`: the use case, depending only on domain
  - This is the first code `import-linter` will actually check — until now it passed because the package was empty, which proved nothing

- [ ] T010 [US1] `GET /api/titles` — owner: **api-agent** — paths: `apps/api/catalog/api.py`
  - Response exactly per contracts/titles.md: array of `{id, name}`, `created_at` **not** exposed
  - **Empty catalog returns `[]` with 200, never 404** — a 404 collapses "no titles" into "cannot reach server" and makes FR-008 unsatisfiable in the client

- [ ] T011 [US1] Generate `packages/contracts` — owner: **contract-keeper** — paths: `packages/contracts/**`
  - `@hey-api/openapi-ts` against the running API's `openapi.json`
  - Commit the generated output; add the `generate` script
  - **Never hand-edit** (§12)

- [ ] T012 [US1] Next.js app rendering the title — owner: **web-agent** — paths: `apps/web/**`
  - Consume the generated client from `packages/contracts` — **not** a hand-written `fetch` type, or FR-005 is unmet and the whole seam is decorative
  - `API_URL_INTERNAL` for server components, `NEXT_PUBLIC_API_URL` for the browser (research R2 — collapsing these produces "works in browser, 500s on hard refresh")
  - `NEXT_TELEMETRY_DISABLED=1` (§6)

- [ ] T013 [US1] Empty and unreachable states on web — owner: **web-agent** — paths: `apps/web/**`
  - **Two visibly different messages** (FR-008). If they read the same, a user cannot tell "nothing here yet" from "something is broken", and those need different reactions
  - Unstyled text is correct — styling arrives in vertical 002

**Checkpoint**: SC-001 (laptop half) and SC-002 pass.

---

## Phase 4: User Story 2 — see the same title on a phone (P1)

**Goal**: The same name renders on a physical handset on the home network.

**Independent Test**: Open the Expo app on a real phone on the same Wi-Fi.

> **The highest-risk story in this vertical.** The development machine can always
> reach itself; a phone cannot. A simulator shares the host's network stack and
> would pass while a real device fails — so a simulator is not a valid test.

- [ ] T014 [US2] Expo app rendering the title — owner: **mobile-agent** — paths: `apps/mobile/**`
  - Same generated client from `packages/contracts`
  - `EXPO_PUBLIC_API_URL` from `FW_HOST` — **never `localhost`**, which resolves to the phone itself (FR-007)

- [ ] T015 [US2] Empty and unreachable states on mobile — owner: **mobile-agent** — paths: `apps/mobile/**`
  - Same two states as T013 (FR-008)
  - Additionally distinguish "phone is not on the home network" — the fix differs from "server is down", and the spec's edge cases call this out

**Checkpoint**: SC-001 passes in full — same title, laptop and phone, simultaneously.

---

## Phase 5: User Story 3 — the pipeline proves itself (P2)

**Goal**: A server-side shape change breaks the client build, loudly.

**Independent Test**: Rename a response field, regenerate, watch the client fail with that field named.

- [ ] T016 [US3] Contract drift gate in CI — owner: **op-agent** — paths: `.github/workflows/guards.yml`
  - Regenerate contracts, `git diff --exit-code`
  - Satisfies SC-003: regeneration with no change produces nothing to commit
  - **Delivered early, inside PR #15 (T011/OP#65), not by op-agent.** The
    `contracts` job in `guards.yml` is this task. Recorded here so the next
    reader does not implement it twice. The board carries the same note on
    OP#70. `git diff --exit-code` alone turned out to be insufficient — it
    says nothing about a *newly emitted* file, so the job stages first.

- [ ] T017 [US3] Prove the contract bites — owner: **qa-agent** — paths: `apps/api/tests/`, `e2e/`
  - A test asserting the response shape matches the contract, so a rename fails a test rather than only failing a typecheck someone might skip
  - Record the manual SC-004 demonstration (rename → regenerate → build fails → revert) in the quickstart run log

**Checkpoint**: All three stories functional; SC-003 and SC-004 demonstrated.

---

## Phase 6: Polish

- [ ] T018 [P] API tests — owner: **qa-agent** — paths: `apps/api/tests/`
  - `GET /api/titles` returns the seeded title; empty database returns `[]` and not 404
  - **Assert the two `MAX_NAME_LENGTH` declarations agree.** `catalog.domain.title.MAX_NAME_LENGTH` and `core.models.Title.name.max_length` are deliberately duplicated — the domain states a rule, the ORM builds a column — and they live in two different agents' files. The comment says the domain wins if they diverge; nothing enforces it. One line closes that:
    ```python
    from catalog.domain import title as domain_title
    from core.models import Title as ORMTitle
    assert domain_title.MAX_NAME_LENGTH == ORMTitle._meta.get_field("name").max_length
    ```
  - **Assert ordering is not promised.** `core.models.Title.Meta.ordering` is set for the admin, while `contracts/titles.md` says ordering is unspecified. A client could observe stable ordering and come to depend on it. The test should assert the *contract's* silence, not the model's default
  - qa-agent cannot write `src` (§20), so it cannot make a failing test pass by changing the code under test

- [ ] T019 [P] End-to-end check — owner: **qa-agent** — paths: `e2e/`
  - Uses `browser-test-agent` — note its `inspect` needs the DOM-settle behaviour fixed earlier, or it snapshots an unrendered shell
  - `.browser-test-agent.json` already points at `localhost:3000`

- [ ] T020 README — owner: **HUMAN** — paths: `README.md`
  - One command, the `FW_HOST` explanation, and how to point a phone at it
  - **This is what SC-005b tests.** CI passing is not evidence for it

- [ ] T021 Run quickstart.md end to end — owner: **HUMAN** — paths: none (verification only)
  - Every SC in order, including `down -v` then `setup` as the closest local approximation of a clean run
  - **SC-005b is a judgement call and stays one** — do not tick it because T008 is green

---

## Dependencies & Execution Order

```
T001  OWNERS.yml            <- blocks literally everything
  |
T002  django scaffold  ->  T003 scripts/setup  ->  T004 [P] .env.example
  |
T005  Title model  ->  T006 [P] admin      T008 [P] clean-runner CI
  |                    T007 seed
  |
T009  domain+application  ->  T010 GET /api/titles  ->  T011 contracts
                                                          |
                            +-----------------------------+
                            |                             |
                     T012/T013 web (US1)          T014/T015 mobile (US2)   [P]
                            |                             |
                            +-----------------------------+
                                          |
                              T016/T017 pipeline proof (US3)
                                          |
                              T018-T021 polish
```

### What is genuinely parallel

Only where paths **and** owners are disjoint:

- **T006 ∥ T007** — no. Both `data-agent`, same owner, sequential.
- **T006 ∥ T008** — yes. `data-agent` (`apps/api/core/`) and `op-agent` (`.github/`).
- **T012/T013 ∥ T014/T015** — yes, and this is the payoff of ADR-0005: `web-agent` and `mobile-agent` never touch the same path and both read a frozen contract, so they need no coordination at all.
- **T018 ∥ T019** — same owner (`qa-agent`), so sequential despite different paths.

**Do not run more than 3–4 agents at once** (constitution §27). The limit is
review throughput, not agent availability, and this vertical is the first time
the loop runs unassisted.

---

## Implementation Strategy

**Start with one agent, not four.** The loop has never executed end to end
without a human driving each step. `data-agent` should take T005–T007 alone,
all the way to a merged PR. If that is clean, add `web-agent` and `mobile-agent`
in parallel for Phase 3–4.

Finding a flaw on "render one title" is much cheaper than finding it with four
agents interleaving.

### MVP

T001–T013 delivers User Story 1: a title on a laptop, from a real database,
through generated types. That is a legitimate stopping point — US2 adds the
phone, which is where the real risk is, but US1 alone proves the seam.

### Notes

- Commit per task or logical group; every commit runs the boundary guard
- Agents open PRs via `agent_pr.py` so `abdulRaw` proposes and a human approves
- A task that turns out to span owners is **split** (`op-cli split`), never
  handed to another agent — routing is derived, never chosen (ADR-0007)
