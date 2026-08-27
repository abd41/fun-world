# 0004. Django and django-ninja for the API

- **Status:** Accepted
- **Date:** 2026-08-27
- **Supersedes:** an earlier choice of FastAPI, and before it Hono.

## Context

The owner is comfortable in JavaScript and wants to learn Python, so the
backend is where the learning budget belongs. Three candidates: Hono
(TypeScript, abandoned once Python became the goal), FastAPI (async-native,
minimal), and Django with django-ninja layered on.

The historical objection to Django was that it is synchronous. **Django 6.0
shipped a genuine async ORM** -- `aget()`, `aall()`, async views with no
`sync_to_async` boilerplate -- which removes it.

## Decision

Use **Django 6.0 + django-ninja**, Python 3.13, managed by uv.

The decisive factor is **Django admin**. This app needs catalog management:
titles, seasons, episodes, artwork. Django admin provides that for the cost
of registering models. FastAPI equivalents cover roughly 60% of it, and
building the rest is most of a feature vertical.

## Consequences

- Vertical 012 shrinks to an admin action that shells out to ffmpeg.
- ORM, migrations, auth scaffolding and admin arrive together.
- django-ninja keeps Pydantic v2 and auto-generated OpenAPI, so ADR-0006
  works unchanged.
- **Cost:** more framework opinion to learn than FastAPI would impose.
- **Cost:** Django 6 async is real but the third-party ecosystem is patchy.
  Keep the async boundary explicit and shallow.
