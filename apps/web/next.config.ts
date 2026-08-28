import type { NextConfig } from "next";

import { resolveWebEnv } from "./env.config";

/**
 * The two API URLs, resolved once at config load from the single `FW_HOST`
 * in the repository-root `.env`. See `env.config.ts` for why they are read
 * there rather than copied into `apps/web/.env`.
 */
const webEnv = resolveWebEnv();

// Printed, not silent. `scripts/setup` reports where FW_HOST came from for the
// same reason: an address that is wrong and invisible costs an afternoon.
console.log(
  [
    "",
    "  fun-world web — API addresses",
    `    API_URL_INTERNAL     ${webEnv.API_URL_INTERNAL}   (${webEnv.sources.API_URL_INTERNAL})`,
    `    NEXT_PUBLIC_API_URL  ${webEnv.NEXT_PUBLIC_API_URL}   (${webEnv.sources.NEXT_PUBLIC_API_URL})`,
    "",
  ].join("\n"),
);

const nextConfig: NextConfig = {
  /**
   * `@fun-world/contracts` publishes TypeScript source, not compiled JS — its
   * `main` and `exports` both point at `./src/index.ts`. Without this, Next
   * hands `.ts` from node_modules to the runtime unparsed and the import fails
   * at build. It is a consequence of §12: the package is generated from
   * `openapi.json`, and adding a build step to it would add a second artefact
   * that can go stale.
   */
  transpilePackages: ["@fun-world/contracts"],

  /**
   * Why `env` and not just `process.env`.
   *
   * `NEXT_PUBLIC_*` is inlined into the browser bundle from the environment
   * Next sees at build start. `FW_HOST` lives in the repository-root `.env`,
   * which Next does not load, so at build start `NEXT_PUBLIC_API_URL` is
   * usually unset and the browser would get `undefined`. Listing it here makes
   * the inlining explicit and independent of load ordering.
   *
   * Both keys are listed deliberately. They are two variables because a server
   * component and a browser fetch are two different network positions
   * (research R2); collapsing them is what produces "works in the browser,
   * 500s on hard refresh". Today both resolve to the same LAN address, and
   * they remain separately overridable so that a container network or a proxy
   * changes configuration rather than code.
   */
  env: {
    API_URL_INTERNAL: webEnv.API_URL_INTERNAL,
    NEXT_PUBLIC_API_URL: webEnv.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
