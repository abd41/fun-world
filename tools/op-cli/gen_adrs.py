#!/usr/bin/env python3
"""One-shot generator for the initial ADR set.

These records back-fill decisions already made and reversed during the
bootstrap, while the reasoning is still recoverable. Later ADRs are written by
hand -- this script exists to seed the folder, not to own it.
"""
from __future__ import annotations

import pathlib
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADR = ROOT / "docs" / "adr"

TEMPLATE = """# {num}. {title}

- **Status:** {status}
- **Date:** {date}
{extra}
## Context

{context}

## Decision

{decision}

## Consequences

{consequences}
"""

RECORDS: list[dict] = [
    dict(
        num="0001", title="Record architecture decisions", status="Accepted",
        context="""
        This project makes consequential choices quickly, and several have already
        reversed an earlier one. Without a record the *reasoning* is lost and only
        the outcome survives, so a later reader cannot tell a deliberate choice from
        an accident, nor know which constraint would have to change for the choice
        to change.
        """,
        decision="""
        Record each significant architectural decision here in Michael Nygard's
        format. Numbered, immutable once accepted. A reversal never edits the old
        record: it adds a new one and marks the old **Superseded**.
        """,
        consequences="""
        - The *why* survives, which is the part that decays first.
        - Superseded records stay readable, so a reversal shows its own reasoning.
        - Costs a few minutes per decision. Worth it the first time someone asks
          "why isn't this Astro?" and the answer is a link rather than a memory.
        """),
    dict(
        num="0002", title="Run entirely on the home network", status="Accepted",
        context="""
        The brief was a Netflix clone. That raises two worries which are easy to
        conflate: a **legal** one (do not publish something that looks like Netflix)
        and a **networking** one (what is reachable from where). Conflating them
        produces an airgap, which would break the televisions entirely.
        """,
        decision="""
        The app binds `0.0.0.0` and is reachable across the LAN and the tailnet. It
        is **never** reachable from the public internet. No tunnel, no port forward,
        no public hostname. Setup may use the network; the running system makes no
        third-party calls.

        What we are building is Jellyfin: a self-hosted media server streaming
        content we have rights to, to our own devices. The two rules that matter are
        never ship Netflix branding, and only stream content we have rights to
        (Blender Foundation open movies, CC-BY).
        """,
        consequences="""
        - No hosting cost, no deployment target, no edge-runtime constraints.
        - Removed a real risk: the Cloudflare Tunnel found in the compose override
          would have published this box with OpenProject's default `admin`/`admin`
          credentials live on it.
        - Every outbound call is now a defect. Gravatar, telemetry and version
          checks are disabled and **verified** off, not merely configured off.
        - **Cost:** no CDN, no managed TLS; remote access needs a VPN (ADR-0013).
        - **Cost:** "works on my machine" is the entire quality bar.
        """),
    dict(
        num="0003", title="Next.js for the web client, not Astro", status="Accepted",
        context="""
        Astro was the original choice. Its value is SEO, cold-visitor TTFB and
        shipping zero JavaScript on content pages. Running local-only behind a
        login, **all three are worth nothing here**.

        It also costs something real: Astro is multi-page by architecture, so client
        state is lost on navigation. For a persistent player, playback position,
        audio-track selection and a mini-player that survives browsing, that is
        close to fatal. Every route in this app is authenticated.
        """,
        decision="""
        Use **Next.js 16** (App Router, RSC) for web. It doubles as the LG webOS
        television client, since webOS is an HTML/JS platform.
        """,
        consequences="""
        - Client state survives navigation, which the player requires.
        - One React model across web and native, so patterns transfer.
        - webOS gets a client for free.
        - **Cost:** ships far more JavaScript than Astro would have. Nobody here is
          on 3G, so this is an acceptable trade.
        - **Cost:** RSC plus a separate API server needs a deliberate token handoff.
          Get it wrong and pages work on client navigation but 401 on hard refresh.
        """),
    dict(
        num="0004", title="Django and django-ninja for the API", status="Accepted",
        extra="- **Supersedes:** an earlier choice of FastAPI, and before it Hono.\n",
        context="""
        The owner is comfortable in JavaScript and wants to learn Python, so the
        backend is where the learning budget belongs. Three candidates: Hono
        (TypeScript, abandoned once Python became the goal), FastAPI (async-native,
        minimal), and Django with django-ninja layered on.

        The historical objection to Django was that it is synchronous. **Django 6.0
        shipped a genuine async ORM** -- `aget()`, `aall()`, async views with no
        `sync_to_async` boilerplate -- which removes it.
        """,
        decision="""
        Use **Django 6.0 + django-ninja**, Python 3.13, managed by uv.

        The decisive factor is **Django admin**. This app needs catalog management:
        titles, seasons, episodes, artwork. Django admin provides that for the cost
        of registering models. FastAPI equivalents cover roughly 60% of it, and
        building the rest is most of a feature vertical.
        """,
        consequences="""
        - Vertical 012 shrinks to an admin action that shells out to ffmpeg.
        - ORM, migrations, auth scaffolding and admin arrive together.
        - django-ninja keeps Pydantic v2 and auto-generated OpenAPI, so ADR-0006
          works unchanged.
        - **Cost:** more framework opinion to learn than FastAPI would impose.
        - **Cost:** Django 6 async is real but the third-party ecosystem is patchy.
          Keep the async boundary explicit and shallow.
        """),
    dict(
        num="0005", title="Two frontends, not one universal Expo app", status="Accepted",
        context="""
        Expo Router v7 can target web, iOS and Android from a single codebase. That
        would have halved the frontend work, removed `packages/ui-spec` entirely,
        and made "same UI, only colours change" structural rather than policed --
        it would be one component tree.
        """,
        decision="""
        Build **two frontends**: Next.js for web, Expo for phone and television.
        Chosen for learning breadth, with the owner explicitly making that trade.
        """,
        consequences="""
        - Two frontend paradigms learned rather than one.
        - **Unplanned dividend:** this covers both television families. Android TVs
          take the Expo build; LG webOS takes the Next.js app. A universal-Expo-only
          stack would have left webOS with nothing good.
        - **Cost:** roughly twice the frontend work, and eleven agents not eight.
        - **Cost:** `packages/ui-spec` exists solely to keep two implementations in
          lockstep -- overhead a single codebase would not have.
        - **Revisit this** the moment scope starts to hurt. It is the largest
          discretionary cost in the project.
        """),
    dict(
        num="0006", title="Generate the client contract from OpenAPI", status="Accepted",
        context="""
        The API is Python; both clients are TypeScript. A hand-written shared types
        package cannot span that boundary. It would be maintained twice and drift
        silently, surfacing as a runtime error in a client long after the server
        changed.
        """,
        decision="""
        django-ninja emits OpenAPI 3.1 from its Pydantic v2 schemas.
        `@hey-api/openapi-ts` generates `packages/contracts`: TypeScript types, Zod
        schemas and TanStack Query hooks.

        `packages/contracts` is **generated, never authored**. Hand-editing it is a
        build failure. CI regenerates on every pull request and fails on a non-empty
        diff.
        """,
        consequences="""
        - Client/server drift becomes structurally impossible, not discouraged.
        - The polyglot split costs about twenty lines of config.
        - Contract-first API design is itself worth learning.
        - **Cost:** a codegen step in the loop; the API must run to regenerate.
        - **Cost:** generated code is noisy in diffs. Acceptable, nobody reads it.
        """),
    dict(
        num="0007", title="Path ownership, resolved first-match-wins", status="Accepted",
        context="""
        Multiple agents writing one repository collide. Assigning work by feature
        leaks immediately: two agents both "own" playback and both edit the API.

        A subtler problem: **agents choosing who to hand work to** is the number one
        documented failure mode in multi-agent systems. A hands to B, B to C, C back
        to A, context lost at every hop, nobody owning the outcome.
        """,
        decision="""
        Boundaries are **directory paths** in `OWNERS.yml`. Exactly one agent may
        write each path. Assignment is **derived** from the paths a ticket declares,
        never chosen by an agent.

        Resolution is **top-down, first-match-wins** (firewall semantics),
        deliberately not "most specific wins" -- which is undefined when globs
        overlap. `apps/api/catalog/tests/x.py` matches both `apps/api/catalog/**`
        and `**/tests/**`, and neither is obviously more specific. An ordered list
        has exactly one answer, always.

        `OWNERS.yml` is **human-owned**: an agent that could edit it could widen its
        own boundary.
        """,
        consequences="""
        - Hand-off loops cannot form. Routing is a pure function of paths.
        - Web and mobile can work the same feature in parallel without negotiating.
        - An agent that cannot finish a ticket **splits** it rather than passing it.
        - Enforced in three layers: agent definition, pre-commit guard, CODEOWNERS.
        - **Cost:** cross-boundary changes route through a spec amendment rather
          than a quick edit. That slowness is the feature.
        - **Cost:** unowned paths refuse claims, so the map must be kept current.
          Running the guard found `.claude/**`, `specs/**` and the root build config
          sitting unowned.
        """),
    dict(
        num="0008", title="op-cli is the only door to the board", status="Accepted",
        context="""
        Agents need to read and update work packages. The obvious options are giving
        each agent the REST API, or running an MCP server in front of it.

        An MCP server mirrors the API, and a mirror **cannot refuse an invalid
        transition**. Every rule in `OWNERS.yml` and the constitution would degrade
        into a suggestion an agent is asked to respect.
        """,
        decision="""
        Build **`op-cli`**, a thin Python CLI owning the integration. Agents never
        touch the API directly.

        It enforces what the constitution declares: `claim` refuses paths the agent
        does not own and refuses a ticket with no paths at all; `split` derives
        children from `OWNERS.yml`; `bug` demands two reproductions and a cited
        acceptance criterion, and reopens rather than re-files; `block` escalates
        past the handoff limit.

        This mirrors the existing `browser-test-agent` pattern: a standalone tool,
        outside every repo, knowing nothing about business logic, driven via Bash.
        """,
        consequences="""
        - Rules sit in front of the API, where they can actually refuse.
        - One API key, one place to change behaviour.
        - Written in Python, serving the learning goal.
        - **Cost:** a tool to maintain; agents cannot do board things it has not
          been taught.
        - **Cost:** its error messages *are* the agent's user interface, so they
          must be instructive rather than merely correct.
        """),
    dict(
        num="0009", title="Self-hosted OpenProject for coordination", status="Accepted",
        context="""
        Agents need durable, queryable shared state that survives an agent dying
        mid-task and lets a human see what is happening. GitHub Projects was the
        initial assumption; the owner already had OpenProject cloned.
        """,
        decision="""
        Use **self-hosted OpenProject 17** at `localhost:8080`, bound to loopback.
        Git and GitHub keep code and pull requests; OpenProject keeps tickets and
        state, joined by putting `OP#<id>` in a pull request description.

        OpenProject owns tickets and state. Git owns code and truth. They are never
        allowed to disagree.
        """,
        consequences="""
        - Local, free, consistent with ADR-0002.
        - Richer model than GitHub Projects: types, parent/child, relations, custom
          fields.
        - Its **default types map onto the plan for free**: Epic per vertical,
          Feature, Task, and **Bug for the qa loop**.
        - Its **default statuses beat the six we specced** -- `Test failed` is
          exactly the qa-to-implementer state.
        - **Cost:** custom fields cannot be created through API v3; that needs
          `rails runner`. One-time setup only.
        - **Cost:** Spec Kit's `/speckit.taskstoissues` targets GitHub Issues and is
          therefore redundant. `op-cli sync` reads `tasks.md` directly, because
          mirroring two ticket systems is how they drift apart.
        - **Cost:** OIDC is an Enterprise add-on, so single sign-on across
          OpenProject and Fun World is unavailable. Agents use an API key and need
          no SSO.
        """),
    dict(
        num="0010", title="Build OAuth 2.1 before adopting Keycloak", status="Accepted",
        context="""
        The owner explicitly wants to learn authentication. Adopting an identity
        provider immediately would deliver working auth and teach nothing about why
        any of its parts exist.
        """,
        decision="""
        Two phases.

        **Phase 1:** implement `/authorize`, `/token`, `/jwks.json` and `/revoke` in
        Django. RS256 JWTs, refresh tokens hashed and tracked as a family, reuse
        detection. Target RFC 9700: PKCE on every client, single-use rotating
        refresh tokens, a replayed token revoking the whole family.

        **Phase 2:** swap the issuer for Keycloak. Django stops issuing tokens and
        becomes a pure resource server validating against a remote JWKS.

        Keycloak over Authentik or Zitadel: Apache 2.0 (Zitadel v3 moved to
        AGPL-3.0), widest protocol coverage, most transferable to know.
        """,
        consequences="""
        - The mechanics are understood before they are abstracted away.
        - Phase 2 shows how little application code changes when the issuer moves.
        - **Cost:** roughly two weeks a managed provider would have saved.
        - **Cost:** hand-rolled auth is a genuinely bad idea in production. This is
          a learning exercise on a private network, the only context where it is
          defensible.
        - Social login is out; external identity providers need egress (ADR-0002).
        """),
    dict(
        num="0011", title="Device Authorization Grant for televisions", status="Accepted",
        context="""
        A television has no keyboard. Typing a password with a D-pad is miserable;
        typing a passkey is impossible. This is not a UX inconvenience -- it makes
        the standard authorization-code flow unusable on three of four TV clients.
        """,
        decision="""
        Implement **RFC 8628** for television clients. The TV displays a short
        `user_code` and a `verification_uri`; the user approves on a phone; the TV
        polls `/token` at the server-dictated `interval` until authorised.

        The server's interval is authoritative. `slow_down` means back off, not
        retry harder.
        """,
        consequences="""
        - The television never handles a credential -- only a device code, then
          tokens.
        - This is exactly what Netflix, YouTube and Disney+ do, so it is directly
          transferable.
        - The auth server needs three grants (code+PKCE, device, refresh), each
          driven by a client that actually exists.
        - **Cost:** a third flow to implement and test, plus an `/activate` page.
        """),
    dict(
        num="0012", title="Self-host HLS instead of a managed video API", status="Accepted",
        context="""
        Mux, Cloudflare Stream and Bunny Stream all cost money at rest. A managed
        API would also hide the parts most worth understanding: the encoding ladder,
        the manifest, and signed playback.
        """,
        decision="""
        Transcode Blender Foundation open movies (CC-BY) with **ffmpeg** into a
        four-rung HLS ladder -- 1080/720/480/360, H.264 + AAC-LC, CMAF fMP4, 6s
        segments, keyframes every 2s. Serve from local disk via **Caddy**.

        Django issues short-lived HMAC-signed playback tokens bound to
        `(profile_id, title_id, expiry)`; Caddy validates before serving the
        manifest.
        """,
        consequences="""
        - Zero cost, and real multi-bitrate video with genuine subtitle tracks.
        - The signed-URL mechanism gets built rather than bought -- roughly what
          Cloudflare Stream offers anyway, since it has no studio DRM either.
        - **Cost:** no ABR analytics, no automatic re-encoding, no CDN.
        - **Cost:** transcoding is manual and slow on a laptop.
        """),
    dict(
        num="0013", title="Tailscale for remote access, not a public tunnel", status="Accepted",
        context="""
        The owner wants to reach the server from their own devices when away from
        home. The compose override already contained a Cloudflare Tunnel with a live
        token, which would have published this box -- with OpenProject's default
        `admin`/`admin` credentials on it.

        Cloudflare Tunnel exposes a service *to the public* for *other people*. That
        is not the requirement.
        """,
        decision="""
        Use **Tailscale**: a private WireGuard mesh where only enrolled devices
        connect, peer-to-peer, nothing publicly exposed, no router ports opened. The
        `cloudflared` service was removed from the compose override and its token
        stripped from `.env`.
        """,
        consequences="""
        - Consistent with ADR-0002: private by construction, not by configuration.
        - Traffic does not route through a third party.
        - **MagicDNS retires the hardcoded-LAN-IP problem** -- one stable hostname
          resolves identically at home and away.
        - **Cost:** LG webOS cannot join a tailnet, so that television is LAN-only.
          Acceptable, since it never leaves the house.
        - The tunnel token should still be revoked in Cloudflare; deleting it
          locally does not invalidate it.
        """),
    dict(
        num="0014", title="Bound concurrency by review capacity", status="Accepted",
        context="""
        Eleven agent boundaries are defined. The tempting conclusion is to run
        eleven agents.

        Brooks's Law says adding people to a late project makes it later, driven by
        communication overhead and ramp-up. With agents the mechanism is *worse* in
        one respect -- a human ramps up once, an agent starts cold every session --
        and better in another, since exclusive path ownership suppresses the
        communication term almost entirely.

        But the binding constraint is neither. Every cross-boundary change is a spec
        amendment, and every change lands as a pull request. **Both gates are one
        human.** That is Amdahl's Law, not Brooks's: the sequential fraction bounds
        the speedup regardless of how many agents run.
        """,
        decision="""
        Define all eleven boundaries -- the map is cheap and is what makes routing
        work -- but **run three or four agents concurrently**.

        The right number is "how many pull requests can one person read carefully in
        a sitting", not "how many boundaries exist". Measure **review throughput**,
        not agent utilisation.
        """,
        consequences="""
        - Agents beyond the review limit add queue, not throughput -- and an
          unreviewed queue is exactly how plausible-looking wrong code gets merged.
        - Concurrency becomes a dial to turn up once the loop has proven itself.
        - **Open bet:** Brooks argued conceptual integrity is a system's most
          important property and comes from few minds, ideally one. Eleven agents
          have none; the spec and constitution are the substitute. If the system
          starts producing work that is individually correct and collectively
          incoherent, that bet has failed -- and the answer is fewer agents and a
          stronger spec, not more process.
        """),
]


def slug(title: str) -> str:
    out = title.lower().replace(" ", "-")
    return "".join(c for c in out if c.isalnum() or c == "-")


def main() -> int:
    ADR.mkdir(parents=True, exist_ok=True)
    written = []
    for r in RECORDS:
        path = ADR / f"{r['num']}-{slug(r['title'])}.md"
        path.write_text(
            TEMPLATE.format(
                num=r["num"], title=r["title"], status=r["status"], date="2026-08-27",
                extra=r.get("extra", ""),
                context=textwrap.dedent(r["context"]).strip(),
                decision=textwrap.dedent(r["decision"]).strip(),
                consequences=textwrap.dedent(r["consequences"]).strip(),
            ),
            encoding="utf-8",
        )
        written.append((r["num"], r["title"], r["status"]))

    index = ["# Architecture Decision Records", "",
             "Why the system is the way it is. Numbered, immutable once accepted;",
             "a reversal adds a new record and marks the old one **Superseded**.", "",
             "New decisions use [`template.md`](template.md).", "",
             "| # | Decision | Status |", "|---|---|---|"]
    for num, title, status in written:
        index.append(f"| [{num}]({num}-{slug(title)}.md) | {title} | {status} |")
    index += ["", "## When to write one", "",
              "Write an ADR when a choice is **hard to reverse**, **surprising**, or",
              "**was reversed** -- not for routine implementation detail. The test:",
              "would someone six months from now ask *why is it like this?*"]
    (ADR / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    (ADR / "template.md").write_text(
        TEMPLATE.format(
            num="NNNN", title="Short present-tense title", status="Proposed",
            date="YYYY-MM-DD", extra="",
            context="What forces are at play? What makes this decision necessary?\n"
                    "State the constraints honestly, including the ones that lost.",
            decision="What we are doing, in active voice. \"We will...\"",
            consequences="What becomes easier, and what becomes harder.\n"
                         "**List the costs.** An ADR with only benefits is marketing.",
        ),
        encoding="utf-8",
    )

    print(f"wrote {len(written)} ADRs + README.md + template.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
