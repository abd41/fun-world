# Feature Specification: Platform Walking Skeleton

**Feature Branch**: `001-platform-walking-skeleton`

**Created**: 2026-08-27

**Status**: Draft

**Input**: Vertical 001 — the thinnest possible slice through every layer, existing to prove the architecture rather than to deliver a feature.

## Why this exists

This feature delivers almost no user value on purpose. Its job is to prove four
assumptions that every later vertical depends on, while they are still cheap to
disprove:

1. The server and the two clients can exchange data through generated types.
2. A device that is not the development machine can reach the system.
3. Work can be built inside the ownership boundaries without deadlocking.
4. A change can travel spec → ticket → branch → review → merge.

If any of those is wrong, it is far cheaper to learn it here than during
playback. **A finished skeleton that looks unimpressive is the correct outcome.**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a title on the laptop (Priority: P1)

Someone at home opens the web app on their laptop and sees the name of one
title stored in the system.

**Why this priority**: It is the shortest path that still touches every layer —
storage, server, generated contract, and a client. Without it nothing else can
be built on top.

**Independent Test**: Open the web app on the development machine. The title's
name is on screen, and it came from the database rather than from hardcoded
text — provable by changing the stored value and reloading.

**Acceptance Scenarios**:

1. **Given** one title exists in storage, **When** someone opens the web app,
   **Then** that title's name is displayed.
2. **Given** the stored name is changed, **When** the page is reloaded,
   **Then** the new name is displayed without any code change.
3. **Given** storage is unreachable, **When** someone opens the web app,
   **Then** they see a plain message saying the catalog is unavailable, not a
   blank page or a stack trace.

---

### User Story 2 - See the same title on a phone (Priority: P1)

Someone opens the mobile app on a physical phone connected to the same home
network and sees the same title.

**Why this priority**: Equal to P1 because it proves the assumption most likely
to be wrong. The development machine can always reach itself; a phone cannot.
Every address that works on the laptop and fails on a phone is a defect that
would otherwise surface much later, in front of a television.

**Independent Test**: Open the mobile app on a real handset — not a simulator
sharing the host's network stack — and see the same name as the laptop shows.

**Acceptance Scenarios**:

1. **Given** the phone is on the home network, **When** the mobile app opens,
   **Then** the same title name is displayed as on the laptop.
2. **Given** the phone is on mobile data instead of home Wi-Fi, **When** the app
   opens, **Then** it shows a message explaining it cannot reach the home
   server, rather than hanging indefinitely.

---

### User Story 3 - The pipeline proves itself (Priority: P2)

A maintainer changes the shape of the data the server returns, and the clients
fail to build until they are updated.

**Why this priority**: Lower because no end user sees it, but it is the property
that keeps the two clients honest for the rest of the project. It must be
demonstrated once, deliberately, rather than assumed.

**Independent Test**: Rename a field on the server, regenerate, and confirm the
client build fails with a type error naming that field.

**Acceptance Scenarios**:

1. **Given** the server's response shape changes, **When** the shared contract
   is regenerated, **Then** the change appears in the contract.
2. **Given** a client still uses the old field, **When** the client is built,
   **Then** the build fails and names the field.
3. **Given** nothing has changed, **When** the contract is regenerated,
   **Then** there is no difference to commit.

### Edge Cases

- **The database is empty.** Both clients show "no titles yet", not an error and
  not a crash. An empty catalog is a normal state, not a failure.
- **The server is not running.** Both clients say so plainly and stop. Neither
  retries forever nor shows a spinner with no end.
- **The phone is on the wrong network.** Distinguishable from "server is down" in
  the message, because the fix is different.
- **The title name contains non-Latin characters or an apostrophe.** Displayed
  correctly on both clients — encoding assumptions are cheaper to find now.
- **The stored name is very long.** It wraps or truncates visibly; it does not
  break the layout or get silently cut off.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store at least one title, with a name, that
  survives a restart of the machine.
- **FR-002**: The system MUST expose the stored titles to client applications
  over the home network.
- **FR-003**: The web client MUST display the name of the stored title.
- **FR-004**: The mobile client MUST display the name of the same stored title
  when running on a physical device on the home network.
- **FR-005**: Both clients MUST obtain the data shape from a single shared
  definition derived from the server, rather than each declaring their own.
- **FR-006**: The shared definition MUST be derived automatically. A hand-written
  change to it MUST fail the build.
- **FR-007**: Client applications MUST NOT contain a hardcoded network address.
  The address MUST come from configuration, because the correct value differs
  between the development machine and every other device.
- **FR-008**: Each client MUST distinguish, in what it shows, between "there are
  no titles" and "the server could not be reached".
- **FR-009**: A maintainer MUST be able to add or edit a title without writing
  code.
- **FR-010**: The system MUST run entirely on the home network, reachable from a
  laptop and a phone, and MUST NOT be reachable from the public internet.
- **FR-011**: The automated checks that guard ownership boundaries, path routing
  and layering MUST pass, and MUST run against real application code for the
  first time.
- **FR-012**: A single documented command MUST bring the whole system up from a
  clean checkout, and MUST fail with an actionable message when a prerequisite
  is missing rather than part-way through with an obscure one.

### Key Entities

- **Title**: One item of watchable content. For this feature it needs only an
  identity and a display name. Everything else a title will eventually
  need — seasons, artwork, licence, duration — is deliberately excluded so
  that the shape of the pipeline is what gets tested, not the shape of the
  catalog.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The same title name is visible simultaneously on a laptop browser
  and a physical phone, both on the home network.
- **SC-002**: Changing the stored name and reloading shows the new name on both
  clients, with no code change and no redeployment.
- **SC-003**: Regenerating the shared definition when nothing has changed
  produces no difference to commit.
- **SC-004**: Renaming a server field causes a client build to fail, naming that
  field — demonstrated once, deliberately.
- **SC-005a**: A single documented command brings the whole system up from a
  clean checkout, and an automated check proves it works on a machine that has
  nothing installed. The command reports how long it took.
- **SC-005b**: A person who has not seen the project brings it up on their own
  machine without asking a question. *Judgement, not automation — see the note
  below.*
- **SC-006**: Every automated guard on the pull request passes.
- **SC-007**: The work travels spec → ticket → branch → review → merge, with at
  least one review comment raised and resolved on the way.

**A note on SC-005.** This was originally one criterion — *"a stranger can start
it in 15 minutes"* — which reads well and cannot be tested. Prose in a README is
not executed, so it drifts the moment a step changes, and the author never
notices because their machine already has everything.

Splitting it separates what a machine can settle from what it cannot. **005a is
mechanical**: one command, proven on a runner that starts with nothing. **005b
is a judgement call** and stays deliberately unautomated, because an automated
check can prove the commands work but never that a person understood them. The
platform-specific parts — container runtime, the home-network address, the
firewall rule — will not be covered by a clean Linux runner at all.

Recording it this way stops 005b being quietly marked done because 005a passed.
They are different claims and only one of them has a test.

## Assumptions

- **A single title is enough.** Lists, ordering and pagination are catalog
  concerns belonging to vertical 003. Proving one record moves end to end is the
  entire point here.
- **No styling.** Unstyled text is sufficient and preferable — styling would
  invite judgement about appearance when the question being asked is whether the
  wiring works. The design system arrives in vertical 002.
- **No authentication.** Everything is open on the home network for this
  vertical. Identity is vertical 004, and adding it here would make a failure
  ambiguous between "auth is wrong" and "the pipeline is wrong".
- **The phone is a real device on home Wi-Fi.** A simulator on the development
  machine shares the host's network stack and would pass while the real case
  fails, which would defeat the purpose of User Story 2.
- **Content is placeholder.** The name used need not be a real title; licensing
  and attribution belong to vertical 003.
- **The maintainer edits titles through an administrative interface**, not by
  writing SQL, satisfying FR-009 without building a product surface.

## Out of Scope

Stated explicitly, because the temptation to add these is what turns a skeleton
into a half-built product:

authentication and profiles · video playback of any kind · more than one title ·
seasons, episodes or artwork · search · styling, theming or design tokens ·
television clients · offline behaviour · caching · pagination · error retry
logic beyond a single clear message.
