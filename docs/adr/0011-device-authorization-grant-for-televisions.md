# 0011. Device Authorization Grant for televisions

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

A television has no keyboard. Typing a password with a D-pad is miserable;
typing a passkey is impossible. This is not a UX inconvenience -- it makes
the standard authorization-code flow unusable on three of four TV clients.

## Decision

Implement **RFC 8628** for television clients. The TV displays a short
`user_code` and a `verification_uri`; the user approves on a phone; the TV
polls `/token` at the server-dictated `interval` until authorised.

The server's interval is authoritative. `slow_down` means back off, not
retry harder.

## Consequences

- The television never handles a credential -- only a device code, then
  tokens.
- This is exactly what Netflix, YouTube and Disney+ do, so it is directly
  transferable.
- The auth server needs three grants (code+PKCE, device, refresh), each
  driven by a client that actually exists.
- **Cost:** a third flow to implement and test, plus an `/activate` page.
