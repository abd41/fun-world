# `@fun-world/web` — the Next.js client

Next.js 16, App Router, TypeScript. Also the target for the LG webOS television,
which runs this app in the TV's browser rather than the Expo build.

Vertical 001 scope: **one page that lists every title's name**, and nothing else.
There is no styling and no stylesheet — `packages/tokens` does not exist yet and §14 fails
the build on a literal colour, so unstyled text is the correct output here, not a
shortcut. The design system arrives in vertical 002.

## Running it

```sh
pnpm install                       # from the repository root
pnpm --dir apps/web run dev        # http://<FW_HOST>:3000
```

Use `--dir`, not `--filter`. `pnpm --filter <name>` **exits 0 when it matches
nothing**, so a filter string that drifts from the package name turns a check
into a no-op that reports success. `--dir` fails loudly on a missing directory
and `pnpm run` fails on a missing script.

The API must be running for the page to show titles; if it is not, the page
still renders and says so (see *Three states* below).

## Addresses

There is exactly one host value in this project: `FW_HOST` in the
**repository-root** `.env`, written by `scripts/setup`. Everything else is
derived from it. This app never contains a literal address (§7).

| variable | used by | value |
|---|---|---|
| `API_URL_INTERNAL` | the server component, running on the machine that runs Next | `http://${FW_HOST}:8000` |
| `NEXT_PUBLIC_API_URL` | the browser, inlined into the client bundle at build | `http://${FW_HOST}:8000` |

They are two variables on purpose. A React Server Component and a browser fetch
are two different network positions, and research R2 records that collapsing
them is what produces "works in the browser, 500s on hard refresh". Both happen
to resolve to the same LAN address today; each is independently overridable, so
a container network or a reverse proxy later is a configuration change rather
than a code change.

**Next.js does not read the repository-root `.env`** — it only auto-loads
`.env` files from the app directory. Rather than keep a second copy of the host
in `apps/web/.env` (a copy DHCP will move out from under you), `env.config.ts`
reads the root file at config load and `next.config.ts` publishes the two
derived values through Next's `env` key. This mirrors what `apps/api` already
does: `config/settings.py` calls `environ.Env.read_env(BASE_DIR.parent.parent /
".env")` for the same reason.

Resolution order, first match wins:

1. `API_URL_INTERNAL` / `NEXT_PUBLIC_API_URL` already set in the environment
2. derived from `FW_HOST` in the environment
3. derived from `FW_HOST` in the repository-root `.env`
4. nothing matched → **throws**, naming `scripts/setup`

There is deliberately no default. A blank base URL makes the generated client
issue a same-origin request, which renders "cannot reach the server" while the
server is perfectly healthy — see the comment in
`packages/contracts/runtime/client.ts`.

`NEXT_TELEMETRY_DISABLED=1` is set by every `next` script in `package.json`
via `cross-env`, so it applies on Windows and POSIX alike (§6). Confirm with
`pnpm --dir apps/web run telemetry:status`, which prints `Status: Disabled`.

## The contract

Every request goes through the generated client, never a hand-written `fetch`:

```ts
import { listTitles, type TitleOut } from "@fun-world/contracts";
import { createApiClient } from "@fun-world/contracts/runtime";
```

`@fun-world/contracts` ships TypeScript **source** — its `exports` point at
`./src/index.ts` — so `next.config.ts` lists it in `transpilePackages`.

This is FR-005, and it is what makes the seam load-bearing. Verified rather than
assumed: changing `title.name` to `title.nayme` in `TitlesView.tsx` fails
`pnpm --dir apps/web run typecheck` with

```
error TS2551: Property 'nayme' does not exist on type 'TitleOut'.
```

so a field this client reads and the server stops sending is a build failure,
not a page that renders `undefined`. The full SC-004 loop — rename it on the
server, regenerate, watch this break — is T017 and is not demonstrated here.

## Three states, three messages

`src/lib/titles.ts` returns a discriminated union and `src/components/TitlesView.tsx`
is the single place it becomes words, so the two fetch contexts cannot word the
same state differently.

| state | when | container |
|---|---|---|
| `ok` | `200` with at least one title | `<div data-state="ok">` |
| `empty` | `200 []` | `<div data-state="empty">` — "No titles yet…" |
| `unreachable` | connection refused, timeout, or a non-2xx | `<div data-state="unreachable">` — "Cannot reach the server…" |

`empty` and `unreachable` read differently on purpose (FR-008). They need
different reactions — add a title, versus start the server — and the API makes
the distinction possible by answering an empty catalogue with `200 []` rather
than `404`.

`data-state` is the stable hook for end-to-end tests, which belong to `qa-agent`
under `e2e/`. Assert on that rather than on the prose.

## Known gap: the browser half cannot reach the API yet

The "From this browser" button fetches with `NEXT_PUBLIC_API_URL` and currently
always reports `unreachable`. Verified 2026-08-28 by driving headless Chrome
against a production build:

```
Access to fetch at 'http://<FW_HOST>:8000/api/titles' from origin
'http://<FW_HOST>:3002' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

The API sends no CORS headers and answers a preflight `OPTIONS` with `405`.
Web and API are always different origins here — same host, different ports — so
this affects every browser-side call, including the webOS television. The fix is
in `apps/api`, which `web-agent` may not write (§8), so it is reported rather
than worked around. A proxy route in this app would "fix" it only by turning the
browser call back into a server-side one, which would hide the gap instead of
closing it.

Server-side rendering is unaffected: the page itself lists titles correctly.
