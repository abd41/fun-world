import { defineConfig } from "@hey-api/openapi-ts";

/**
 * Step two: `openapi.json` -> `src/`. Step one is `scripts/export-schema.mjs`.
 *
 * `input` is the committed file, never a URL. See that script for why.
 */
export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src",
    // No prettier, no eslint. The generator's own output is deterministic;
    // adding a formatter means a second tool whose version also has to be
    // pinned, or the empty-diff gate fails on a machine with a different
    // one -- a false failure that trains people to bypass it.
    postProcess: [],
  },
  // No log file at all. hey-api writes one by default, and a log appearing
  // under a generated directory would show up as contract drift on the very
  // next run of the gate.
  logs: { file: false },
  plugins: [
    "@hey-api/typescript",
    "@hey-api/sdk",
    // fetch, because it is the one HTTP client both targets already have:
    // the browser natively, and React Native through its polyfill. A client
    // per platform would mean the generated seam differs by platform, which
    // is the thing generating it was meant to prevent.
    "@hey-api/client-fetch",
  ],
});
