# Quickstart — proving vertical 001 works

How to verify the walking skeleton, and what each step is actually testing.
Every success criterion in the spec maps to something here.

## Prerequisites

```bash
uv run python tools/op-cli/check_toolchain.py --phase 1
```

Must report **phase 1 toolchain complete**. `ffmpeg`, `java` and `adb` will show
as missing — correct, they belong to phase 3.

Also needed: Docker Desktop running, and a phone on the same Wi-Fi.

## Bring it up

```bash
./scripts/setup
```

One command (FR-012). Expect it to print, at the end:

```
Fun World is up.
  API      http://192.168.0.106:8000
  Web      http://192.168.0.106:3000
  Media    http://192.168.0.106:8090
  FW_HOST  192.168.0.106      <- the address your phone needs
  elapsed  4m12s
```

`FW_HOST` is **configurable, and only auto-detected as a fallback** (R2). Setup
reports which source it used and never overwrites a value you have set.

To pin it — recommended once a VPN is in place, and the end state this design
exists for:

```bash
echo 'FW_HOST=funworld.tailnet.ts.net' >> .env
./scripts/setup                        # reports "from .env — not overwritten"
```

Nothing parses `FW_HOST` as an IP address, so a MagicDNS name, an mDNS name and
a bare address are all valid. Swapping to the VPN later is this one line — no
code change, nothing in `apps/` aware anything moved.

While it is auto-detected, DHCP can move the laptop and the phone will stop
working until setup is re-run. Pinning it removes that failure entirely.

## Proving each criterion

### SC-001 — the same title on laptop and phone

**Laptop**: open `http://localhost:3000`. Expect "Big Buck Bunny".

**Phone**: same Wi-Fi, open the Expo app. Expect the same text.

> **This is the criterion most likely to fail, and the reason the vertical
> exists.** A simulator on this machine is not a valid test — it shares the
> host's network stack and would pass while a real handset fails. Use a real
> phone.
>
> If the laptop works and the phone does not, the cause is almost always an
> address: something resolved `localhost` on a device where that means the
> device itself.

### SC-002 — the data is real, not hardcoded

```bash
# change the stored name without touching code
open http://localhost:8000/admin/     # log in, edit the Title, save
```

Reload both clients. Both show the new name. If either still shows the old one,
it is rendering a constant and FR-003/FR-004 are not met.

### SC-003 — regeneration is a no-op

```bash
pnpm --filter @fun-world/contracts generate
git diff --exit-code packages/contracts
```

Must exit `0`. A non-empty diff means the committed contract does not match what
the API currently describes — the drift CI gate would catch this on a PR, and
catching it locally first is cheaper.

### SC-004 — the contract actually bites

Demonstrate once, deliberately, then revert:

```bash
# in apps/api/catalog/api.py, rename the response field name -> title
pnpm --filter @fun-world/contracts generate
pnpm --filter web typecheck
```

The web build **must fail**, naming the field. If it compiles, the clients are
not really using the generated types and FR-005 is not met — which would mean
the whole seam is decorative.

Revert the rename and regenerate.

### SC-005a — setup works on a machine with nothing

Not verifiable here — this machine is not clean. The CI job
`setup (clean runner)` runs `scripts/setup` on `ubuntu-latest` and asserts the
API answers.

### SC-005b — a person can do it unaided

Deliberately not automated (see the spec's note). The honest test is handing the
README to someone who has not seen the project. **CI passing is not evidence for
this criterion**, and marking it done because CI is green is the specific
mistake the spec split SC-005 to prevent.

### SC-006 — guards pass

```bash
uv run --with pyyaml python tools/op-cli/check_drift.py
uv run --with pyyaml python tools/op-cli/test_resolve.py
uv run --with import-linter lint-imports --config .importlinter
```

The third one matters most here: it is the **first time it runs against real
code**. Until now it passed because `app` did not exist, which proves nothing.

### FR-008 — the two failure states are distinguishable

```bash
docker compose -f infra/docker-compose.yml stop db
```

Both clients must say they cannot reach the server. Then:

```bash
docker compose -f infra/docker-compose.yml start db
# delete the seeded title via /admin/
```

Both must now say there are no titles. **Two different messages.** If they look
the same, the states have been collapsed and FR-008 is not met — a user cannot
tell "nothing here yet" from "something is broken", and those need different
reactions.

## Teardown

```bash
docker compose -f infra/docker-compose.yml down        # keeps the data
docker compose -f infra/docker-compose.yml down -v     # discards it
```

`down -v` then `./scripts/setup` is the closest local approximation of the clean
run, and worth doing once before opening the PR.
