/**
 * One call to `GET /api/titles`, turned into exactly one of the states the
 * screen knows how to render.
 *
 * The data and the types both come from `packages/contracts`, which is
 * generated from the API's OpenAPI document (FR-005, ADR-0006). Nothing here
 * declares the shape of a title; `TitleOut` is imported, so renaming `name` on
 * the server breaks this file at compile time instead of at runtime on a
 * handset (SC-004).
 *
 * ## Why the states are separate values and not booleans
 *
 * FR-008 requires "no titles" and "cannot reach the server" to be told apart,
 * and the spec's edge cases add a third: "the phone is on the wrong network".
 * The three need different reactions from whoever is holding the phone —
 * nothing, start the server, change Wi-Fi — so they are three distinct results
 * here and three distinct sentences on screen. Collapsing any two of them
 * loses the only information the message carries.
 *
 * An empty catalog is a SUCCESS. The API returns `200 []`, never a 404; the
 * generated `listTitles` docstring in `sdk.gen.ts` says the same thing and for
 * the same reason.
 *
 * This module deliberately imports nothing from Expo or React Native — only
 * `@fun-world/contracts` and a TYPE from `../net/connection`, which erases at
 * compile time. The connection probe arrives as a parameter instead. That is
 * what makes the decision table runnable against real sockets on a laptop, so
 * all five branches below can be observed rather than argued about; the run is
 * quoted in the commit that added this file.
 */
import { listTitles, type TitleOut } from "@fun-world/contracts";
import { createApiClient } from "@fun-world/contracts/runtime";

import type { Reachability } from "../net/connection";

/**
 * There has to be a deadline at all: acceptance scenario US2-2 says the app
 * shows a message "rather than hanging indefinitely", and a TCP connection to
 * an address with nothing on it can sit unanswered for far longer than anyone
 * will wait. Eight seconds is a judgement call, not a measurement — long
 * enough not to punish a slow first request, short enough to be worth waiting
 * out.
 */
export const REQUEST_TIMEOUT_MS = 8000;

export type CatalogState =
  /** `200` with rows. */
  | { kind: "titles"; titles: TitleOut[] }
  /** `200 []`. A normal, successful, empty catalog. */
  | { kind: "empty" }
  /** The server answered, and said no. Reachable, so not a network problem. */
  | { kind: "server-error"; status: number }
  /** The request never got an answer, and the phone believes it is on Wi-Fi. */
  | { kind: "server-unreachable"; detail: string }
  /** The request never got an answer, and the phone is not on the house network. */
  | { kind: "off-home-network" };

export type LoadCatalogOptions = {
  /** Absolute API address. Comes from `apiBaseUrl()`; never a literal. */
  baseUrl: string;
  /** Injected so the decision table can be exercised off-device. */
  probeConnection: () => Promise<Reachability>;
  timeoutMs?: number;
};

export async function loadCatalog({
  baseUrl,
  probeConnection,
  timeoutMs = REQUEST_TIMEOUT_MS,
}: LoadCatalogOptions): Promise<CatalogState> {
  const client = createApiClient({ baseUrl });

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // `typeof listTitles<false>` pins ThrowOnError to false — errors come back as
  // values, not exceptions. Without the explicit `false`, TypeScript resolves
  // the generic to its constraint (`boolean`), the conditional return type
  // stays unresolved, and `result.error` does not exist on the union.
  let result: Awaited<ReturnType<typeof listTitles<false>>>;
  try {
    result = await listTitles({ client, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }

  const { data, error } = result;

  // The generated result type declares `response: Response`, not optional —
  // but `packages/contracts/src/client/client.gen.ts` returns
  // `{ error, request, response: undefined as any }` when `fetch` itself
  // threw. So a missing response is precisely "the request never reached a
  // server", which is the distinction this whole function turns on. Widening
  // the type here is what lets TypeScript compare it to undefined at all.
  const response: Response | undefined = result.response;

  if (data) {
    return data.length === 0 ? { kind: "empty" } : { kind: "titles", titles: data };
  }

  if (response) {
    return { kind: "server-error", status: response.status };
  }

  return (await probeConnection()) === "off-home-network"
    ? { kind: "off-home-network" }
    : { kind: "server-unreachable", detail: describeTransportError(error, timeoutMs) };
}

/**
 * A short, human-sized description of why the request gave up.
 *
 * React Native's `fetch` is `whatwg-fetch` over `XMLHttpRequest` — confirmed by
 * reading the bundle Expo Go actually downloads, where `xhr.onerror` rejects
 * with `new TypeError('Network request failed')` and `xhr.onabort` with
 * `new DOMException('Aborted', 'AbortError')`.
 *
 * The check below is on `.name`, not `instanceof Error`, on purpose. That same
 * bundle uses the platform's `DOMException` when one exists and only falls back
 * to a polyfill whose prototype chain includes `Error` when it does not — so
 * `instanceof Error` is not guaranteed for the abort case, and getting it wrong
 * would silently downgrade the timeout message to the generic one.
 *
 * `timeoutMs` is the effective value used for THIS request, not the module
 * default, so the sentence cannot claim a deadline the caller did not set.
 */
function describeTransportError(error: unknown, timeoutMs: number): string {
  const thrown = error as { name?: unknown; message?: unknown } | null | undefined;

  if (thrown?.name === "AbortError") {
    return `No answer within ${Math.round(timeoutMs / 1000)} seconds.`;
  }
  if (typeof thrown?.message === "string" && thrown.message.length > 0) {
    return thrown.message;
  }
  if (typeof error === "string" && error.length > 0) return error;
  return "The request did not reach a server.";
}
