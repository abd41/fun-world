# 0002. Run entirely on the home network

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

The brief was a Netflix clone. That raises two worries which are easy to
conflate: a **legal** one (do not publish something that looks like Netflix)
and a **networking** one (what is reachable from where). Conflating them
produces an airgap, which would break the televisions entirely.

## Decision

The app binds `0.0.0.0` and is reachable across the LAN and the tailnet. It
is **never** reachable from the public internet. No tunnel, no port forward,
no public hostname. Setup may use the network; the running system makes no
third-party calls.

What we are building is Jellyfin: a self-hosted media server streaming
content we have rights to, to our own devices. The two rules that matter are
never ship Netflix branding, and only stream content we have rights to
(Blender Foundation open movies, CC-BY).

## Consequences

- No hosting cost, no deployment target, no edge-runtime constraints.
- Removed a real risk: the Cloudflare Tunnel found in the compose override
  would have published this box with OpenProject's default `admin`/`admin`
  credentials live on it.
- Every outbound call is now a defect. Gravatar, telemetry and version
  checks are disabled and **verified** off, not merely configured off.
- **Cost:** no CDN, no managed TLS; remote access needs a VPN (ADR-0013).
- **Cost:** "works on my machine" is the entire quality bar.
