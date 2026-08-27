# Architecture Decision Records

Why the system is the way it is. Numbered, immutable once accepted;
a reversal adds a new record and marks the old one **Superseded**.

New decisions use [`template.md`](template.md).

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-run-entirely-on-the-home-network.md) | Run entirely on the home network | Accepted |
| [0003](0003-nextjs-for-the-web-client-not-astro.md) | Next.js for the web client, not Astro | Accepted |
| [0004](0004-django-and-django-ninja-for-the-api.md) | Django and django-ninja for the API | Accepted |
| [0005](0005-two-frontends-not-one-universal-expo-app.md) | Two frontends, not one universal Expo app | Accepted |
| [0006](0006-generate-the-client-contract-from-openapi.md) | Generate the client contract from OpenAPI | Accepted |
| [0007](0007-path-ownership-resolved-first-match-wins.md) | Path ownership, resolved first-match-wins | Accepted |
| [0008](0008-op-cli-is-the-only-door-to-the-board.md) | op-cli is the only door to the board | Accepted |
| [0009](0009-self-hosted-openproject-for-coordination.md) | Self-hosted OpenProject for coordination | Accepted |
| [0010](0010-build-oauth-21-before-adopting-keycloak.md) | Build OAuth 2.1 before adopting Keycloak | Accepted |
| [0011](0011-device-authorization-grant-for-televisions.md) | Device Authorization Grant for televisions | Accepted |
| [0012](0012-self-host-hls-instead-of-a-managed-video-api.md) | Self-host HLS instead of a managed video API | Accepted |
| [0013](0013-tailscale-for-remote-access-not-a-public-tunnel.md) | Tailscale for remote access, not a public tunnel | Accepted |
| [0014](0014-bound-concurrency-by-review-capacity.md) | Bound concurrency by review capacity | Accepted |
| [0015](0015-skeletons-for-loading-lottie-for-error-and-empty-states.md) | skeletons for loading lottie for error and empty states | Accepted |

## When to write one

Write an ADR when a choice is **hard to reverse**, **surprising**, or
**was reversed** -- not for routine implementation detail. The test:
would someone six months from now ask *why is it like this?*
