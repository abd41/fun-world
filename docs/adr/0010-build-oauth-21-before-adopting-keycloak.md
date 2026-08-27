# 0010. Build OAuth 2.1 before adopting Keycloak

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

The owner explicitly wants to learn authentication. Adopting an identity
provider immediately would deliver working auth and teach nothing about why
any of its parts exist.

## Decision

Two phases.

**Phase 1:** implement `/authorize`, `/token`, `/jwks.json` and `/revoke` in
Django. RS256 JWTs, refresh tokens hashed and tracked as a family, reuse
detection. Target RFC 9700: PKCE on every client, single-use rotating
refresh tokens, a replayed token revoking the whole family.

**Phase 2:** swap the issuer for Keycloak. Django stops issuing tokens and
becomes a pure resource server validating against a remote JWKS.

Keycloak over Authentik or Zitadel: Apache 2.0 (Zitadel v3 moved to
AGPL-3.0), widest protocol coverage, most transferable to know.

## Consequences

- The mechanics are understood before they are abstracted away.
- Phase 2 shows how little application code changes when the issuer moves.
- **Cost:** roughly two weeks a managed provider would have saved.
- **Cost:** hand-rolled auth is a genuinely bad idea in production. This is
  a learning exercise on a private network, the only context where it is
  defensible.
- Social login is out; external identity providers need egress (ADR-0002).
