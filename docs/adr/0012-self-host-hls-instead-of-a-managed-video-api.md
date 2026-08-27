# 0012. Self-host HLS instead of a managed video API

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Mux, Cloudflare Stream and Bunny Stream all cost money at rest. A managed
API would also hide the parts most worth understanding: the encoding ladder,
the manifest, and signed playback.

## Decision

Transcode Blender Foundation open movies (CC-BY) with **ffmpeg** into a
four-rung HLS ladder -- 1080/720/480/360, H.264 + AAC-LC, CMAF fMP4, 6s
segments, keyframes every 2s. Serve from local disk via **Caddy**.

Django issues short-lived HMAC-signed playback tokens bound to
`(profile_id, title_id, expiry)`; Caddy validates before serving the
manifest.

## Consequences

- Zero cost, and real multi-bitrate video with genuine subtitle tracks.
- The signed-URL mechanism gets built rather than bought -- roughly what
  Cloudflare Stream offers anyway, since it has no studio DRM either.
- **Cost:** no ABR analytics, no automatic re-encoding, no CDN.
- **Cost:** transcoding is manual and slow on a laptop.
