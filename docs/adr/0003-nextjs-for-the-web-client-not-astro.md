# 0003. Next.js for the web client, not Astro

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Astro was the original choice. Its value is SEO, cold-visitor TTFB and
shipping zero JavaScript on content pages. Running local-only behind a
login, **all three are worth nothing here**.

It also costs something real: Astro is multi-page by architecture, so client
state is lost on navigation. For a persistent player, playback position,
audio-track selection and a mini-player that survives browsing, that is
close to fatal. Every route in this app is authenticated.

## Decision

Use **Next.js 16** (App Router, RSC) for web. It doubles as the LG webOS
television client, since webOS is an HTML/JS platform.

## Consequences

- Client state survives navigation, which the player requires.
- One React model across web and native, so patterns transfer.
- webOS gets a client for free.
- **Cost:** ships far more JavaScript than Astro would have. Nobody here is
  on 3G, so this is an acceptable trade.
- **Cost:** RSC plus a separate API server needs a deliberate token handoff.
  Get it wrong and pages work on client navigation but 401 on hard refresh.
