/**
 * Where the API is, as far as the running app is concerned.
 *
 * ONE runtime lookup, deliberately: `Constants.expoConfig.extra.apiUrl`, put
 * there by `app.config.ts`, which is the only place that knows how to derive
 * an address from `FW_HOST` (constitution §7). Reading an env var here as well
 * would create a second answer to the same question and a class of bug where
 * the laptop and the phone disagree about which one won.
 *
 * `null` is a real possible answer — `extra` is absent when the app is loaded
 * from a manifest that was built without it — and callers must render it as a
 * configuration problem rather than as "the server is down". Those are again
 * different fixes.
 */
import Constants from "expo-constants";

export function apiBaseUrl(): string | null {
  const extra = Constants.expoConfig?.extra as { apiUrl?: unknown } | undefined;
  const value = typeof extra?.apiUrl === "string" ? extra.apiUrl.trim() : "";
  return value.length > 0 ? value : null;
}

/** Shown verbatim when {@link apiBaseUrl} returns null. */
export const MISSING_BASE_URL_MESSAGE =
  "This build has no API address. Run ./scripts/setup at the repo root so " +
  "FW_HOST is set, then restart the Expo server.";
