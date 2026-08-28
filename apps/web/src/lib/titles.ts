/**
 * Fetching the catalogue, and the three outcomes a caller must tell apart.
 *
 * Isomorphic on purpose: the same function serves the server component (given
 * `API_URL_INTERNAL`) and the client island (given `NEXT_PUBLIC_API_URL`).
 * Neither URL is read here — the caller passes the one that is correct for its
 * network position, so `API_URL_INTERNAL` is never referenced from a client
 * component and therefore never inlined into a browser bundle.
 *
 * Every request goes through the GENERATED client. `listTitles` and `TitleOut`
 * come from `packages/contracts`, which is derived from the API's OpenAPI
 * document (§12, FR-005). A hand-written `fetch` with a hand-written response
 * type would compile identically today and would silently stop matching the
 * server the first time a field changed — which is the entire property this
 * vertical exists to prove.
 */
import { listTitles, type TitleOut } from "@fun-world/contracts";
import { createApiClient } from "@fun-world/contracts/runtime";

/**
 * The three states FR-008 requires be distinguishable.
 *
 * `empty` and `unreachable` are separate members rather than one "nothing to
 * show" case because they need different reactions from the person reading
 * the screen: add a title, versus start the server. The API makes the
 * distinction possible by answering an empty catalogue with `200 []` rather
 * than `404` — see the `listTitles` docstring in the generated SDK.
 */
export type TitlesResult =
  | { state: "ok"; titles: TitleOut[] }
  | { state: "empty" }
  | { state: "unreachable"; detail: string };

/** How long to wait before calling the server unreachable. The spec's edge
 *  cases forbid a spinner with no end; a refused connection fails instantly,
 *  but a host that is simply absent from the network black-holes the packet
 *  and would otherwise hang until the platform's default timeout. */
const TIMEOUT_MS = 5_000;

function describe(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string" && error) return error;
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

export async function loadTitles(baseUrl: string): Promise<TitlesResult> {
  const client = createApiClient({ baseUrl });

  // `throwOnError` is left at its default of false, so a refused connection,
  // a DNS failure or a 500 all arrive as `error` rather than as an exception.
  // The try/catch covers what that does not: an abort, and `createApiClient`
  // rejecting a blank baseUrl.
  try {
    const { data, error } = await listTitles({
      client,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });

    if (error !== undefined || data === undefined) {
      return { state: "unreachable", detail: describe(error) };
    }
    return data.length === 0 ? { state: "empty" } : { state: "ok", titles: data };
  } catch (error) {
    return { state: "unreachable", detail: describe(error) };
  }
}
