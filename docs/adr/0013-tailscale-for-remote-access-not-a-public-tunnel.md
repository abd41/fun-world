# 0013. Tailscale for remote access, not a public tunnel

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

The owner wants to reach the server from their own devices when away from
home. The compose override already contained a Cloudflare Tunnel with a live
token, which would have published this box -- with OpenProject's default
`admin`/`admin` credentials on it.

Cloudflare Tunnel exposes a service *to the public* for *other people*. That
is not the requirement.

## Decision

Use **Tailscale**: a private WireGuard mesh where only enrolled devices
connect, peer-to-peer, nothing publicly exposed, no router ports opened. The
`cloudflared` service was removed from the compose override and its token
stripped from `.env`.

## Consequences

- Consistent with ADR-0002: private by construction, not by configuration.
- Traffic does not route through a third party.
- **MagicDNS retires the hardcoded-LAN-IP problem** -- one stable hostname
  resolves identically at home and away.
- **Cost:** LG webOS cannot join a tailnet, so that television is LAN-only.
  Acceptable, since it never leaves the house.
- The tunnel token should still be revoked in Cloudflare; deleting it
  locally does not invalidate it.
