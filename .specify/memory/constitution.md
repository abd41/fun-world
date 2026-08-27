# Fun World — Constitution

Non-negotiable principles for this project. Every `/speckit.plan` is checked
against this document. A plan that violates a principle is rejected at plan
time, not at review time.

This file is **human-owned**. No agent may modify it. Amending it is a
deliberate act by a person, and amendments are dated below.

---

## I. Scope and legality

1. **This is a private home streaming app.** It runs on one laptop and is
   reached from devices in one house. It is never deployed to a public host.

2. **No Netflix intellectual property, ever.** Not the name, the wordmark, the
   logo, the brand red, nor any asset derived from them. The product is
   "Fun World". A UI of poster rails is a generic pattern — that is fine. The
   branding is not.

3. **Only content there is a right to stream.** The catalog is Blender
   Foundation open movies (CC-BY) and material of equivalent licence.
   Attribution is carried in the UI, not just in a code comment.

4. **No scraping of third-party services.** External metadata is fetched once,
   under its own terms, and committed as a fixture.

## II. Network posture

5. **No public exposure.** The app binds `0.0.0.0` and is reachable on the LAN
   and the tailnet. It is never reachable from the open internet. No tunnel
   service, no port forward, no public hostname.

6. **No third-party telemetry.** Nothing reports usage anywhere. Framework
   telemetry is explicitly disabled, not merely left at its default.

7. **No hardcoded hosts.** Every URL comes from environment configuration.
   A hardcoded `localhost` breaks the phone and both TVs, and it will not be
   caught until someone is standing in front of a television.

## III. Agent boundaries

8. **Path ownership is absolute.** An agent writes only inside its `OWNERS.yml`
   allowlist. There is no exception, no "just this once", and no emergency
   that justifies crossing a boundary.

9. **Assignment is derived, never chosen.** No agent selects which agent
   receives work. The owner of a path is looked up in `OWNERS.yml`, which is
   why hand-off loops cannot form. An agent that cannot complete a ticket
   splits it into path-scoped children; it does not pass it on.

10. **A cross-boundary need is a spec amendment.** When a client needs the API
    to behave differently, it does not edit the API. It amends the spec, the
    owning agent changes the server, and contracts regenerate.

11. **`OWNERS.yml` and this file are human-owned.** An agent that could edit
    either could widen its own authority, which would make every principle
    above advisory.

## IV. Contracts

12. **`packages/contracts` is generated, never authored.** It is produced from
    the API's OpenAPI 3.1 document. Hand-editing it is a build failure, not a
    code review comment.

13. **CI regenerates and diffs.** A stale client fails the build. Drift between
    server and clients is made structurally impossible rather than discouraged.

## V. Design

14. **Tokens are the only source of colour.** A literal hex value outside
    `packages/tokens` fails the build on every platform. Without this, colour
    leaks into components within a week.

15. **Web and mobile implement the same `ui-spec` entry, or neither ships.**
    Platform parity is a gate, not an aspiration.

16. **Television is exempt from parity, and deliberately so.** The TV is a
    different interaction model — D-pad focus, 10-foot type, overscan-safe
    margins, no hover. Pretending it is the phone UI at a larger size produces
    something unusable with a remote.

## VI. Authentication

17. **RFC 9700 is the floor.** PKCE on every client without exception.
    Refresh tokens are single-use, rotated on every exchange, and tracked as a
    family — a replayed token revokes the entire family.

18. **Devices without keyboards use the device grant.** Televisions authorise
    through RFC 8628, never by typing a password with a remote control. The
    server-dictated polling interval is respected; `slow_down` means back off.

19. **Secrets never enter the repository.** They live in gitignored
    environment files. A secret that reaches a commit is rotated, not deleted.

## VII. Quality

20. **`qa-agent` writes tests and only tests.** It holds no write access to
    application source, so it cannot make a failing test pass by changing the
    code under test.

21. **A bug ticket cites the acceptance criterion it violates.** If it cannot
    name one, it is not a bug — it is a spec ambiguity, and it routes to a
    human. The specification has authority over correctness, never the test.

22. **A failure is reproduced twice before it is filed.** One flaky test would
    otherwise generate bugs indefinitely.

23. **Reopen, never re-file.** A bug is keyed to its failing test. A
    fix-and-retest cycle reopens the same work package so that the handoff
    counter remains a meaningful loop detector.

## VIII. Autonomy

24. **Agents work between two human gates: spec approval and merge.**
    Everything in between is theirs. An unattended loop with no gate does not
    produce a finished feature; it produces a large volume of plausible code
    that still has to be read.

25. **A pull request, never a direct push.** Every change arrives as a
    reviewable diff.

26. **Limits are enforced by tooling, not by instruction.** Fan-out caps,
    split depth and handoff counts live in `op-cli`, because a limit an agent
    is merely asked to respect is not a limit.

27. **Concurrency is bounded by review capacity, not by the number of
    boundaries.** Eleven agents are *defined*; three or four *run*. The
    constraint on this project is not how many agents can work in parallel —
    it is how many pull requests one person can read carefully in a sitting.
    Beyond that, additional agents do not add throughput; they add an
    unreviewed queue, which is exactly how plausible-looking wrong code gets
    merged. Measure review throughput, not agent utilisation.

28. **Conceptual integrity lives in the spec, because no agent holds it.**
    Brooks argued that the most important property of a system is conceptual
    integrity, and that it comes from few minds, ideally one. Eleven agents
    have none. The specification and this constitution are the substitute —
    which is a genuine bet, and worth naming as one. If the system starts
    producing work that is individually correct and collectively incoherent,
    that bet has failed, and the answer is fewer agents and a stronger spec,
    not more agents and more process.

## IX. Cost

27. **No paid services.** A dependency that requires a credit card is rejected
    at plan time. This is a learning project and it stays free to run.

---

*Ratified 2026-08-27. Amendments are appended below with a date and a reason.*

---

## Amendments

### 2026-08-27 — assets and motion

Prompted by considering Lottie animations for error and loading states. The
discussion exposed three gaps that have nothing to do with Lottie specifically
and apply equally to fonts, icon sets and imagery.

**29. Third-party assets are vendored, never fetched at runtime.**
Fonts, icons, animations and imagery are committed to the repository and served
from this machine. No CDN, no asset host, no exception.

*Why this was missing:* §6 forbids third-party **telemetry** — data about us
going out. §4 forbids **scraping** metadata. A request *for content* from an
asset CDN is neither, so a component pulling a Lottie file from a third-party
host would have violated nothing. It does now.

**30. Third-party assets carry their licence and attribution.**
Every vendored asset records its licence and, where required, is credited in
the UI. The same discipline §3 applies to the catalog, applied to the assets
around it.

*Why this was missing:* §3 governs **content** — the films. A CC-BY animation
or an icon set is not content, and fell outside it.

**31. Motion respects `prefers-reduced-motion`.**
Every animated component has a still fallback and honours the user's setting.
The reduced-motion state is part of its `ui-spec` entry, so §15's parity gate
covers it on both platforms. Animation that cannot be stopped does not ship.

*Why this was missing:* the constitution said nothing about motion or
accessibility at all. This is the first of what will probably become a fuller
accessibility section — the TV work in particular will need focus-visibility
rules that do not exist yet.
