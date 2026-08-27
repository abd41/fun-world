# 0005. Two frontends, not one universal Expo app

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Expo Router v7 can target web, iOS and Android from a single codebase. That
would have halved the frontend work, removed `packages/ui-spec` entirely,
and made "same UI, only colours change" structural rather than policed --
it would be one component tree.

## Decision

Build **two frontends**: Next.js for web, Expo for phone and television.
Chosen for learning breadth, with the owner explicitly making that trade.

## Consequences

- Two frontend paradigms learned rather than one.
- **Unplanned dividend:** this covers both television families. Android TVs
  take the Expo build; LG webOS takes the Next.js app. A universal-Expo-only
  stack would have left webOS with nothing good.
- **Cost:** roughly twice the frontend work, and eleven agents not eight.
- **Cost:** `packages/ui-spec` exists solely to keep two implementations in
  lockstep -- overhead a single codebase would not have.
- **Revisit this** the moment scope starts to hurt. It is the largest
  discretionary cost in the project.
