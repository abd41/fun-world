# apps/mobile — the phone client

Expo SDK 57 + Expo Router. Vertical 001 (T014, T015): one screen that renders
every title's name from `GET /api/titles`, on a real handset on the home
network.

The TV build is a different interaction model and a different owner — see
`src/tv/` and `tv-agent` in `OWNERS.yml`. Nothing here should assume a remote
control.

## Running it

```
./scripts/setup                     # once, from the repo root — writes FW_HOST
cd apps/api && uv run python manage.py runserver 0.0.0.0:8000
pnpm --dir apps/mobile run start    # then scan the QR with Expo Go
```

`--dir`, not `--filter`. `pnpm --filter <name>` exits 0 when it matches no
project at all, so a drifted package name would report success having run
nothing.

The phone and the laptop must be on the same network, and the laptop's firewall
must allow inbound 8000 and 8081. Neither is something this app can check.

## The address, and why there is only one of it

Constitution §7 forbids a hardcoded host, and on a phone that is not a style
rule: `localhost` inside the app is *the phone*, so a hardcoded default reaches
the wrong machine and then reports "cannot reach the server" while the server is
perfectly healthy.

There is exactly one host value in this project — `FW_HOST` in the repo-root
`.env`, written by `scripts/setup`. `app.config.ts` reads it at config time and
publishes `extra.apiUrl`; `src/api/config.ts` reads that back at runtime. One
resolver, one runtime lookup, no second copy to drift.

Resolution order, first match wins:

| | source | use |
|---|---|---|
| 1 | `EXPO_PUBLIC_API_URL` in the environment | full override, port included |
| 2 | `FW_HOST` in the environment | matches `scripts/setup` step 2/9 |
| 3 | `FW_HOST=` in the repo-root `.env` | the normal case |
| 4 | nothing | **throws**, with the fix in the message |

Case 4 is deliberate. A fallback here is how "works on the laptop" ships.

## The five states on screen

`src/api/titles.ts` returns one of five results and `src/app/index.tsx` gives
each a different sentence, because each needs a different reaction:

| result | what the reader should do |
|---|---|
| `titles` | watch something, eventually |
| `empty` (`200 []`) | nothing — an empty catalog is a success, not an error |
| `off-home-network` | join the home Wi-Fi |
| `server-unreachable` | start the server on the laptop |
| `server-error` | read the server's log |

FR-008 requires the first three to be distinguishable. The spec's edge cases
require `off-home-network` to be distinguishable from `server-unreachable`
separately, *because the fix is different* — one is Wi-Fi, the other is the
laptop. A single "cannot connect" message sends the reader to the wrong one
half the time.

The two are told apart by asking the handset what transport it is on
(`src/net/connection.ts`), because the `fetch` failure itself is identical.
That probe knows the transport, **not** which Wi-Fi network — a phone on a
neighbour's Wi-Fi is told the server is unreachable. Reading the SSID needs a
location permission, which is a large ask for a slightly better message.

## Things that are deliberately absent

**No styling and no colour.** Spec 001 assumes unstyled text; §14 makes
`packages/tokens` the only source of colour and it is still empty. The only
style rules here are padding and spacing.

**No `metro.config.js`.** The usual monorepo advice is to set `watchFolders`
and `resolver.nodeModulesPaths` by hand. On SDK 57.0.17 that is no longer
needed and doing it is worse: `expo/metro-config`'s `getDefaultConfig` already
reads `pnpm-workspace.yaml` and produces

```
watchFolders:      <root>/node_modules, <root>/apps/mobile, <root>/packages/contracts
nodeModulesPaths:  <root>/apps/mobile/node_modules, <root>/node_modules
```

A hand-written `watchFolders = [workspaceRoot]` *replaces* that precise list
with the whole tree. This was measured, not assumed — removing a hand-written
config changed nothing, and the bundle contains
`packages/contracts/src/sdk.gen.ts` either way. If a future SDK stops doing it,
add the file back.

**No tests.** `**/__tests__/**` belongs to `qa-agent` (`OWNERS.yml`), which is
what stops an implementer making a red test green by editing the test.

## Telemetry

`scripts/expo.cjs` sets `EXPO_NO_TELEMETRY=1` before loading the CLI, because
§6 requires framework telemetry be *explicitly* disabled and Expo's default is
on (`@expo/cli@57.0.19`, `build/bin/cli` line 272 reads
`boolish('EXPO_NO_TELEMETRY', false)`).

This covers the package scripts only. `npx expo start` by hand bypasses it. The
gap closes if `EXPO_NO_TELEMETRY=1` joins `NEXT_TELEMETRY_DISABLED=1` in the
repo-root `.env.example`, which is a human-owned file.
