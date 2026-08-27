# 0014. Bound concurrency by review capacity

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

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

## Decision

Define all eleven boundaries -- the map is cheap and is what makes routing
work -- but **run three or four agents concurrently**.

The right number is "how many pull requests can one person read carefully in
a sitting", not "how many boundaries exist". Measure **review throughput**,
not agent utilisation.

## Consequences

- Agents beyond the review limit add queue, not throughput -- and an
  unreviewed queue is exactly how plausible-looking wrong code gets merged.
- Concurrency becomes a dial to turn up once the loop has proven itself.
- **Open bet:** Brooks argued conceptual integrity is a system's most
  important property and comes from few minds, ideally one. Eleven agents
  have none; the spec and constitution are the substitute. If the system
  starts producing work that is individually correct and collectively
  incoherent, that bet has failed -- and the answer is fewer agents and a
  stronger spec, not more process.
