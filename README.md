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

Boundaries are enforced in layers (ADR-0007). Agents commit with `FW_AGENT`
set; human commits are unrestricted.

```bash
FW_AGENT=web-agent git commit -m "..."   # checked against OWNERS.yml
git commit -m "..."                       # human, unrestricted
```

| layer | where | catches | blocking? |
|---|---|---|---|
| 1 | the agent's own definition | honest mistakes | no |
| 2 | pre-commit hook | everything else on this machine | yes, locally |
| 3 | `.github/CODEOWNERS` | puts a human on human-owned paths | **not yet** — see below |
| 3 | `Agent boundaries` job in CI | a layer-2 bypass: `--no-verify`, or a clone without hooks | **not yet** — see below |

`FW_AGENT` is recorded as an `FW-Agent:` commit trailer by a
`prepare-commit-msg` hook, which is what lets the CI job check a commit after
the fact. Without it the acting agent is unrecoverable: every agent commits as
the same GitHub account, so authorship separates agent from human and nothing
finer. `./scripts/setup` installs the hooks; to do it by hand:

```bash
uv run --with pyyaml python tools/op-cli/check_boundaries.py --install
```

**What is and is not blocking today.** Ruleset 21628724 is active on `main`
with one required approval, required thread resolution, dismiss-stale-on-push
and squash-only merges. Two gaps remain, both repository settings rather than
files, so neither can be closed from this repo:

- `require_code_owner_review` is `false`, so CODEOWNERS *requests* a reviewer
  and does not compel one.
- The required status checks are `OWNERS.yml drift`, `Path routing` and
  `Onion layers`. `Agent boundaries (layer 3)` is **not** among them, so a red
  boundaries run still merges.

Until both are set, layer 3 is evidence rather than a gate. That is stated
here rather than glossed, because a check believed to block and silently not
blocking is worse than one nobody trusts.

The CI job runs on pull requests only. On `push: main` a squash commit is
authored by whoever opened the pull request and flattens a whole branch into
one message, so the question it asks cannot be answered honestly there.

## Local stack

```bash
docker compose -f infra/docker-compose.yml up -d   # postgres :5433, media :8090
```

OpenProject lives separately in `../openproject-selfhost` and is not part of
this compose project.
