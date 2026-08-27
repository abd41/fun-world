/**
 * The one way to build a client, with `baseUrl` genuinely required.
 *
 * AUTHORED, not generated -- which is why it lives outside `src/`. Constitution
 * §12 governs the generated output (`src/`, `openapi.json`); this package has
 * always also held authored files (`package.json`, the hey-api config, the
 * export script). Nothing here is machine-written, and the generator never
 * touches this directory.
 *
 * ## Why it exists
 *
 * The README used to claim `baseUrl` was required and that §7 was "enforced by
 * absence" because the document declares `servers: []`. Review checked, and it
 * was false: hey-api types `baseUrl` as optional, so `createClient()` and
 * `createClient({})` both compile. `getUrl` then does `(baseUrl ?? "") + path`
 * and issues a **same-origin** request.
 *
 * That is not a type error anyone would notice. It is a phone that renders
 * "cannot reach the server" while the server is perfectly healthy, because the
 * request went to the phone's own origin -- the precise FR-007/FR-008 pair this
 * vertical exists to prove cannot happen.
 *
 * So the requirement is imposed here, where TypeScript can hold it, instead of
 * in prose that a reviewer has to remember.
 */
import { createClient, createConfig } from "../src/client";
import type { Client } from "../src/client";
import type { ClientOptions } from "../src/types.gen";

/** Everything `createConfig` accepts, with `baseUrl` promoted to required.
 *  Derived from the generated signature rather than restated, so a hey-api
 *  upgrade that changes the options cannot leave this type quietly stale. */
type GeneratedConfig = NonNullable<Parameters<typeof createConfig<ClientOptions>>[0]>;

export type ApiClientOptions = Omit<GeneratedConfig, "baseUrl"> & {
  /** Where the API lives. No default, deliberately: §7 forbids a hardcoded
   *  host, and a fallback is how "works on the laptop" ships. */
  baseUrl: string;
};

export function createApiClient({ baseUrl, ...rest }: ApiClientOptions): Client {
  // Empty and whitespace-only both slip past a `string` type and both produce
  // the silent same-origin request this module exists to prevent.
  if (!baseUrl?.trim()) {
    throw new Error(
      "createApiClient needs a baseUrl. Pass the API's address from the " +
        "environment (NEXT_PUBLIC_API_URL, EXPO_PUBLIC_API_URL) — never a literal host.",
    );
  }
  return createClient(createConfig<ClientOptions>({ baseUrl, ...rest }));
}
