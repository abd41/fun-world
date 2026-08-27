# 0015. Skeletons for loading, Lottie for error and empty states

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Every screen needs a loading state and an error state, and the two are usually
solved with the same component -- a spinner -- because that is the least
thought. The question raised was whether to use Lottie animations for both, or
skeleton placeholders, or one of each.

They are not the same problem.

**Loading a known shape.** Rails, poster grids and title detail all have a
structure that is known before the data arrives. A skeleton communicates that
structure: the viewer sees where things will land. This measurably reduces
perceived wait and eliminates layout shift when content resolves. A spinner in
the middle of a grid conveys nothing about what is coming -- the shape *is* the
information, and a spinner discards it.

**An error or an empty result.** There is no structure to preview, because
there is nothing to come. These states are rare, so asset weight is
irrelevant. They are also negative moments, where a little character genuinely
helps rather than decorates.

**A cold start.** Especially on television, where boot is slow and a blank
screen reads as a broken device.

## Decision

Three states, three treatments.

| State | Treatment |
|---|---|
| Content loading with known shape | **Skeleton** — mirrors the real layout |
| Error (404, 500, offline) and empty (no results, empty My List) | **Lottie** |
| Cold start / splash, television especially | **Lottie**, capped at ~1.5s |

Implementation: **dotLottie (`.lottie`)** rather than raw JSON — substantially
smaller. `@lottiefiles/dotlottie-web` on Next.js, `lottie-react-native` on Expo.

Assets are **vendored** (constitution §29), carry their **licence and
attribution** (§30), and honour **`prefers-reduced-motion`** (§31). The
reduced-motion still frame is part of each component's `ui-spec` entry, so the
§15 parity gate covers it on both platforms.

`design-system` owns the `ui-spec` entries; `web-agent` and `mobile-agent`
implement them natively.

## Consequences

- Loading feels faster without being faster, because the skeleton previews the
  layout instead of hiding it.
- No layout shift on data arrival, which is the actual defect a spinner causes.
- Error and empty screens get personality in the one place where personality
  is worth its cost.
- **Cost:** two mechanisms to build and maintain rather than one spinner.
- **Cost:** `lottie-react-native` is another native dependency on Expo. It
  should be fine on Android TV, but that is an assumption — **verify it early,
  at vertical 002, not at 006 when the error screens get built.**
- **Cost:** skeletons must be kept in step with the real layout. A skeleton
  that no longer matches its component is worse than none, because it promises
  a shape that does not arrive.
- Prompted three constitution amendments (§29–31) that generalise well beyond
  this decision — the same rules now govern fonts, icons and imagery.
