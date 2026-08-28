/**
 * Build-time resolution of the two API URLs this app needs.
 *
 * Imported by `next.config.ts` ONLY. Nothing under `src/` may import it: it
 * reads the filesystem, which would fail in the browser bundle and would put
 * the repository layout into a client chunk.
 *
 * ## The problem it solves
 *
 * Constitution §7 says every URL comes from environment configuration, and
 * research R2 says there is exactly one host value in this project — `FW_HOST`
 * in the repository-root `.env`, written by `scripts/setup`. Next.js, however,
 * only auto-loads `.env` files from the app directory (`apps/web/.env`), so
 * `FW_HOST` is invisible to this app by default.
 *
 * The three ways to close that gap and why this one:
 *
 *   - copy the host into `apps/web/.env`  — a second copy of the one value
 *     that must never have two copies; DHCP moves one and not the other
 *   - symlink `apps/web/.env` to the root — `.env*` is gitignored, so nothing
 *     would carry the link to another checkout at all; and this machine has
 *     `core.symlinks=false`, where git materialises a symlink as a text file
 *     containing its target rather than as a link
 *   - read the root `.env` here, at config load  — no second copy, no
 *     platform assumption. This.
 *
 * ## Resolution order — first match wins, exactly as research R2 specifies
 *
 *   1. `API_URL_INTERNAL` / `NEXT_PUBLIC_API_URL` already in the environment
 *   2. derived from `FW_HOST` in the environment
 *   3. derived from `FW_HOST` in the repository-root `.env`
 *   4. no match: throw. There is deliberately no default — see below.
 *
 * ## Why there is no fallback
 *
 * `packages/contracts/runtime/client.ts` refuses a blank `baseUrl` because an
 * empty one produces a silent same-origin request: the page renders "cannot
 * reach the server" while the server is perfectly healthy. Defaulting the host
 * here would reintroduce that at one remove — the build would succeed and the
 * failure would surface on a television. A missing host is a setup problem and
 * says so, with the command that fixes it.
 *
 * ## A note on research R2
 *
 * R2's table suggests `API_URL_INTERNAL=http://localhost:8000` for server
 * components. That literal is not used here, for two reasons. It is a second
 * host value, which is the thing R2 itself argues against; and
 * `check_constitution.py` greps `apps/**` for `http://localhost` and fails the
 * build on it (§7). Both URLs therefore derive from `FW_HOST`, which the
 * server machine can reach as readily as the browser can. They stay two
 * separate variables because the contexts are genuinely different and each is
 * independently overridable — see `next.config.ts`.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

/** Marker that identifies the monorepo root. Chosen over `.git` because a
 *  checkout used as a submodule has no `.git` directory, and over `.env`
 *  because `.env` is exactly the file that may be missing. */
const ROOT_MARKER = "pnpm-workspace.yaml";

const SETUP_HINT =
  "Run ./scripts/setup from the repository root, or set FW_HOST in the " +
  "repository-root .env (see .env.example).";

function findRepoRoot(startDir: string): string {
  let dir = resolve(startDir);
  // Walk up until `dirname` stops changing, which is the filesystem root on
  // both POSIX and Windows.
  for (;;) {
    if (existsSync(join(dir, ROOT_MARKER))) return dir;
    const parent = dirname(dir);
    if (parent === dir) {
      throw new Error(
        `apps/web: could not find ${ROOT_MARKER} above ${startDir}, so the ` +
          `repository-root .env cannot be located. ${SETUP_HINT}`,
      );
    }
    dir = parent;
  }
}

/**
 * Minimal `KEY=VALUE` reader for the repository-root `.env`.
 *
 * Deliberately not `@next/env`'s `loadEnvConfig`. Checked against the shipped
 * source rather than assumed — `@next/env@16.3.3`, `dist/index.js`:
 *
 *     function loadEnvConfig(t,n,o=console,s=false,i){
 *       if(!a){a=Object.assign({},process.env)}
 *       if(l&&!s){return{combinedEnv:l,parsedEnv:p,loadedEnvFiles:u}}
 *       replaceProcessEnv(a); ...
 *
 * `l` is module-level state and `s` is `forceReload`, so once any call has
 * populated the cache a later call returns it — the directory argument is not
 * consulted at all. Were Next to load env for `apps/web` before this config is
 * evaluated, a call here for the repository root would read nothing and report
 * success: a silent no-op of exactly the shape this repository keeps shipping.
 * Passing `forceReload` skips the cache but then reaches `replaceProcessEnv`,
 * which resets `process.env` to a snapshot — a much larger side effect than
 * reading one file.
 *
 * NOT verified: whether Next does in fact call it for `apps/web` first. That
 * ordering is what the risk turns on and it was not observed; only the cache
 * behaviour above was. Reading the file directly makes the ordering moot,
 * which is why this does not depend on settling it.
 *
 * Handles comments, blank lines, `export ` prefixes and surrounding quotes.
 * It does not do variable interpolation, and nothing in this project needs it.
 */
function readEnvFile(path: string): Record<string, string> {
  if (!existsSync(path)) return {};
  const out: Record<string, string> = {};
  for (const raw of readFileSync(path, "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq < 0) continue;
    const key = line.slice(0, eq).replace(/^export\s+/, "").trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"') && value.length > 1) ||
      (value.startsWith("'") && value.endsWith("'") && value.length > 1)
    ) {
      value = value.slice(1, -1);
    }
    if (key) out[key] = value;
  }
  return out;
}

/** The port Django is served on. A port is not a host, so §7 does not reach
 *  it; it is the same number `scripts/setup` prints and `apps/api` binds. */
const API_PORT = 8000;

export type WebEnv = {
  /** Used by server components. Never referenced from a client component, so
   *  it is never inlined into a browser bundle. */
  API_URL_INTERNAL: string;
  /** Inlined into the browser bundle at build time by Next's `env` config. */
  NEXT_PUBLIC_API_URL: string;
  /** Where each value came from, one line each, so `next.config.ts` can print
   *  it and neither URL is ever a mystery — the same courtesy `scripts/setup`
   *  extends to `FW_HOST` itself. */
  sources: { API_URL_INTERNAL: string; NEXT_PUBLIC_API_URL: string };
};

export function resolveWebEnv(cwd: string = process.cwd()): WebEnv {
  const rootEnv = readEnvFile(join(findRepoRoot(cwd), ".env"));

  let host = process.env.FW_HOST?.trim();
  let hostSource = "derived from FW_HOST in the environment";
  if (!host) {
    host = rootEnv.FW_HOST?.trim();
    hostSource = "derived from FW_HOST in the repository-root .env";
  }

  const derived = host ? `http://${host}:${API_PORT}` : "";

  const overrideInternal = process.env.API_URL_INTERNAL?.trim();
  const overrideBrowser = process.env.NEXT_PUBLIC_API_URL?.trim();

  const internal = overrideInternal || derived;
  const browser = overrideBrowser || derived;

  if (!internal || !browser) {
    throw new Error(
      "apps/web: FW_HOST is not set, so the API address cannot be derived " +
        "and there is no default (constitution §7 — a hardcoded host breaks " +
        `the phone and both televisions). ${SETUP_HINT}`,
    );
  }

  return {
    API_URL_INTERNAL: internal,
    NEXT_PUBLIC_API_URL: browser,
    sources: {
      API_URL_INTERNAL: overrideInternal ? "set explicitly in the environment" : hostSource,
      NEXT_PUBLIC_API_URL: overrideBrowser ? "set explicitly in the environment" : hostSource,
    },
  };
}
