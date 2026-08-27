# Fun World

A private, self-hosted streaming app. Runs on one laptop, watched on phones
and televisions in one house. Never deployed anywhere public.

Built by agents working inside hard filesystem boundaries, driven by
spec-driven development, coordinated through self-hosted OpenProject.

| | |
|---|---|
| **API** | Django 6 + django-ninja (Python 3.13, uv) |
| **Web** | Next.js 16 |
| **Phone / TV** | Expo 57 — Android TV, Fire TV, Google TV |
| **Board** | OpenProject 17 at http://localhost:8080/projects/fun-world |
| **Content** | Blender Foundation open movies (CC-BY) |

## Start here

- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — five diagrams: where
  things run, how the code fits together, a playback request end to end, how
  work reaches an agent, and the content model. Renders on GitHub and in
  VS Code's Markdown preview.
- **[`docs/adr/`](docs/adr/)** — Architecture Decision Records. *Why* the
  system is like this, including the choices that were reversed and what
  changed. Read before proposing a different approach.
- **[`docs/build-plan.html`](docs/build-plan.html)** — the full plan: every
  decision, what it replaced and why, constraints, and build order. Open it in
  a browser; it is self-contained and needs no network.

## The rules

- [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — the
  non-negotiable principles. Read before planning anything.
- [`OWNERS.yml`](OWNERS.yml) — the routing table. Which agent may write where.
  Human-owned; no agent may modify it.

## Boundaries

Every agent writes only inside its allowlist. Assignment is *derived* from
paths, never chosen by an agent — which is why handoff loops cannot form.

```bash
pnpm owners:test     # 24 routing cases — run after any OWNERS.yml change
pnpm agents:gen      # regenerate .claude/agents/*.md from OWNERS.yml
pnpm agents:check    # fail if they have drifted
```

Boundaries are enforced in three layers (ADR-0007). Agents commit with
`FW_AGENT` set; human commits are unrestricted.

```bash
FW_AGENT=web-agent git commit -m "..."   # checked against OWNERS.yml
git commit -m "..."                       # human, unrestricted
```

| layer | where | catches |
|---|---|---|
| 1 | the agent's own definition | honest mistakes |
| 2 | pre-commit hook | everything else on this machine |
| 3 | `boundaries` job in CI | a layer-2 bypass — `--no-verify`, or a clone without hooks |

`FW_AGENT` is recorded as an `FW-Agent:` commit trailer by a
`prepare-commit-msg` hook, which is what lets layer 3 check a commit after the
fact. Without it the acting agent is unrecoverable: every agent commits as the
same GitHub account, so authorship separates agent from human and nothing
finer. Install the hooks with:

```bash
python tools/op-cli/check_boundaries.py --install
```

`.github/CODEOWNERS` is generated from `OWNERS.yml` (`gen_codeowners.py`) and
puts a human reviewer on paths no agent may write. It requests review; it does
not block a merge — there is no branch protection on a private repo on the
free tier. The CI job is the half that fails the build.

## Local stack

```bash
docker compose -f infra/docker-compose.yml up -d   # postgres :5433, media :8090
```

OpenProject lives separately in `../openproject-selfhost` and is not part of
this compose project.
