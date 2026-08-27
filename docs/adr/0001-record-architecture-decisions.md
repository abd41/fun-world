# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

This project makes consequential choices quickly, and several have already
reversed an earlier one. Without a record the *reasoning* is lost and only
the outcome survives, so a later reader cannot tell a deliberate choice from
an accident, nor know which constraint would have to change for the choice
to change.

## Decision

Record each significant architectural decision here in Michael Nygard's
format. Numbered, immutable once accepted. A reversal never edits the old
record: it adds a new one and marks the old **Superseded**.

## Consequences

- The *why* survives, which is the part that decays first.
- Superseded records stay readable, so a reversal shows its own reasoning.
- Costs a few minutes per decision. Worth it the first time someone asks
  "why isn't this Astro?" and the answer is a link rather than a memory.
