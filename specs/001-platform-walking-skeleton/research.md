# Phase 0 — Research

Three questions this vertical cannot proceed without. The stack itself needed no
research: it was decided in ADRs 0002–0016 and is cited, not revisited.

---

## R1. Five paths no agent can claim

**Question**: `OWNERS.yml` does not cover the Django project scaffold or the
setup script. Who owns them?

Verified by resolving the paths this vertical creates:

```
scripts/setup                UNOWNED   <-- gap
apps/api/pyproject.toml      UNOWNED   <-- gap
apps/api/manage.py           UNOWNED   <-- gap
apps/api/config/settings.py  UNOWNED   <-- gap
apps/api/config/urls.py      UNOWNED   <-- gap
apps/api/core/models.py      data-agent
apps/api/catalog/api.py      api-agent
```

Unowned is a *refusal*, not permission (`op-cli` will not let a ticket be
claimed), so five tasks would deadlock.

**Decision**: Both become **HUMAN**-owned.

**Rationale**: `config/settings.py` holds `INSTALLED_APPS`, the database
connection and middleware — project structure, not feature work. Adding a Django
app is a structural decision that happens roughly once per vertical, and is
precisely the kind of change worth a person noticing. This matches root
`package.json` already being human-owned for the same reason (ADR-0007).

`scripts/setup` is the project's front door and the thing SC-005a tests. It
would otherwise attract edits from every agent whose layer it touches — the same
shape of problem as `pnpm-lock.yaml`, but with the opposite answer: the lockfile
is *regenerated* incidentally, whereas the setup script is *authored*
deliberately, so `shared_generated` does not apply.

**Alternatives considered**:

- *Give `config/**` to `data-agent`.* Rejected: it owns models and migrations,
  and settings is neither. It would also mean one agent gatekeeping every other
  agent's ability to register an app.
- *Auto-discover `INSTALLED_APPS` by convention* so settings never changes.
  Rejected: it fights Django idiom, and hiding app registration to satisfy an
  ownership rule is the tail wagging the dog.
- *A new `platform-agent`.* Rejected: agent sprawl is a named failure mode
  (ADR-0014), and this would be an agent whose entire job is ~6 files that
  change once per vertical.

**Cost accepted**: adding a Django app in later verticals needs a human commit.
Roughly eleven more times over the project. Worth it.

---

## R2. One host value, three clients, no hardcoding (FR-007)

**Question**: The phone cannot reach `localhost` — that resolves to the phone.
How does one address reach a Django server, a Next.js app (which fetches from
*both* server and browser) and an Expo app, without being written down three
times and drifting?

**The trap**: Next.js has two fetch contexts. A React Server Component fetches
from *inside* the container/host, where `localhost` is correct. The browser
fetches from the user's machine, where it is correct only by coincidence. The
phone needs the LAN IP in both cases. Three contexts, three correct answers,
one wrong value away from a bug that appears only on the device.

**Decision**: A single detected `FW_HOST`, written once by `scripts/setup`, fanned
out to per-client variables that are *derived*, never typed by hand.

```
scripts/setup detects the LAN IPv4 (excluding loopback, link-local,
and virtual adapters such as WSL/Hyper-V) and writes .env:

  FW_HOST=192.168.0.106          <- the only place an address is written

then derives, into each client's env file:
  apps/api    ALLOWED_HOSTS=localhost,127.0.0.1,${FW_HOST}
              (Django binds 0.0.0.0 so it accepts on every interface)
  apps/web    API_URL_INTERNAL=http://localhost:8000      server components
              NEXT_PUBLIC_API_URL=http://${FW_HOST}:8000  browser
  apps/mobile EXPO_PUBLIC_API_URL=http://${FW_HOST}:8000  always the LAN IP
```

**Rationale**: The value is detected rather than configured, so it is correct on
first run and cannot be forgotten. It is written in exactly one place, so a
DHCP change is fixed by re-running setup rather than by finding three files.
The Next.js split is explicit rather than implicit, because collapsing it is the
specific mistake that produces "works in the browser, 500s on hard refresh".

**Alternatives considered**:

- *`localhost` everywhere.* Rejected: fails on the phone, which is FR-004.
- *A hostname via mDNS (`funworld.local`).* Genuinely attractive — survives DHCP
  changes. Rejected for this vertical: Android's mDNS support is inconsistent
  and debugging a name-resolution failure on a handset would dominate a vertical
  whose purpose is proving the pipeline. Revisit at vertical 006.
- *Tailscale MagicDNS.* The eventual answer (ADR-0013) and immune to DHCP. Not
  yet installed, and adding a VPN to the critical path of the first vertical
  couples "does the pipeline work" to "does the VPN work".
- *Hardcode and document it.* Rejected outright by FR-007.

**Known limitation, accepted**: DHCP can reassign the laptop's address, breaking
the phone until `scripts/setup` is re-run. `setup` will detect and report a
changed `FW_HOST` rather than failing obscurely.

---

## R3. A setup command provable on a machine with nothing (FR-012 / SC-005a)

**Question**: How is "works from a clean checkout" verified, given the author's
machine can never answer that question?

**Decision**: `scripts/setup` — one idempotent bash script — plus a CI job on a
clean `ubuntu-latest` runner that executes it and asserts the API answers.

Order matters, and is chosen so failures are actionable:

```
1. check_toolchain.py --phase 1     fail early, with install hints
2. detect FW_HOST, write .env       before anything reads it
3. docker compose up -d --wait      --wait, so migrations cannot race a
                                    database that is still starting
4. uv sync && manage.py migrate     schema before seed
5. seed one Title (idempotent)      re-running must not duplicate
6. pnpm install
7. generate packages/contracts      needs the API running
8. print URLs, FW_HOST, elapsed     elapsed makes SC-005a's 15 minutes
                                    a number rather than a feeling
```

**Rationale**: A toolchain check first means a missing `ffmpeg` reports itself
in three seconds with a `winget` line, instead of thirty seconds later as a
`command not found` inside a subprocess. `--wait` removes the flakiest possible
failure. Idempotence matters because the second run is the common case and a
setup script that only works once teaches people not to trust it.

**Alternatives considered**:

- *A `Makefile`.* Rejected: `make` is absent on this Windows machine (verified),
  and adding a dependency to run the script that checks dependencies is circular.
- *`docker compose` alone.* Rejected: cannot install the JS toolchain, cannot
  generate contracts, cannot detect the LAN IP.
- *A README list of steps.* Rejected by FR-012 — it is what SC-005 was split to
  stop relying on.

**Known limitation, and it is real**: `ubuntu-latest` proves the commands work.
It cannot prove the Windows path — Docker Desktop, the LAN IP detection against
WSL and Hyper-V virtual adapters, or the firewall rule. `PowerShell` adapter
enumeration on this machine returned three IPv4 addresses, only one of which is
correct, so LAN detection is the part most likely to behave differently on CI
than in reality.

This is exactly the gap SC-005b exists to name. **CI settles the mechanical
half; a person trying it settles the rest**, and the plan does not pretend
otherwise.
