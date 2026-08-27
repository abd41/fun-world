# 0009. Self-hosted OpenProject for coordination

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Agents need durable, queryable shared state that survives an agent dying
mid-task and lets a human see what is happening. GitHub Projects was the
initial assumption; the owner already had OpenProject cloned.

## Decision

Use **self-hosted OpenProject 17** at `localhost:8080`, bound to loopback.
Git and GitHub keep code and pull requests; OpenProject keeps tickets and
state, joined by putting `OP#<id>` in a pull request description.

OpenProject owns tickets and state. Git owns code and truth. They are never
allowed to disagree.

## Consequences

- Local, free, consistent with ADR-0002.
- Richer model than GitHub Projects: types, parent/child, relations, custom
  fields.
- Its **default types map onto the plan for free**: Epic per vertical,
  Feature, Task, and **Bug for the qa loop**.
- Its **default statuses beat the six we specced** -- `Test failed` is
  exactly the qa-to-implementer state.
- **Cost:** custom fields cannot be created through API v3; that needs
  `rails runner`. One-time setup only.
- **Cost:** Spec Kit's `/speckit.taskstoissues` targets GitHub Issues and is
  therefore redundant. `op-cli sync` reads `tasks.md` directly, because
  mirroring two ticket systems is how they drift apart.
- **Cost:** OIDC is an Enterprise add-on, so single sign-on across
  OpenProject and Fun World is unavailable. Agents use an API key and need
  no SSO.
