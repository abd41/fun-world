/**
 * Expo config, evaluated in Node by the Expo CLI before Metro starts.
 *
 * Its one interesting job is turning the project's single host value into the
 * API address the phone will use, and publishing it as `extra.apiUrl` so the
 * running app can read it from `Constants.expoConfig.extra`.
 *
 * ## Why the address is resolved here and not in the app
 *
 * Constitution §7: no hardcoded hosts. On a phone this is not a style rule.
 * `localhost` inside the Expo app resolves to THE PHONE, so a hardcoded
 * default does not fail — it succeeds at reaching the wrong machine and then
 * reports "cannot reach the server" while the server is perfectly healthy.
 *
 * There is exactly ONE host value in this project: `FW_HOST` in the repo-root
 * `.env`, written by `scripts/setup`. This file reads that file rather than
 * keeping a second copy, because two copies drift the first time DHCP moves
 * the laptop.
 *
 * Note `.env` at the repo root is gitignored, so on a fresh clone it does not
 * exist until `./scripts/setup` has run. That is why the failure below is a
 * thrown error with an instruction, not a fallback.
 *
 * ## Resolution order — first match wins
 *
 *   1. `EXPO_PUBLIC_API_URL` in the environment  — full override, port included
 *   2. `FW_HOST` in the environment              — same precedence scripts/setup uses
 *   3. `FW_HOST=` in the repo-root `.env`        — the normal case
 *   4. nothing                                   — throw, with the fix in the message
 *
 * This mirrors `scripts/setup` step 2/9 deliberately: a value you set is never
 * overwritten by something guessed.
 */
import type { ExpoConfig } from "expo/config";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

/** apps/mobile -> apps -> repo root. */
const REPO_ROOT = resolve(__dirname, "..", "..");
const ROOT_ENV = resolve(REPO_ROOT, ".env");

/**
 * The port Django is served on. Fixed across the project — `scripts/setup`
 * prints the same one in its closing summary. It is not a host and §7 does not
 * govern it; `EXPO_PUBLIC_API_URL` overrides the whole URL if it ever moves.
 */
const API_PORT = "8000";

/**
 * Pull `FW_HOST` out of the repo-root `.env`.
 *
 * A deliberately small parser: `KEY=value`, `#` comments, optional surrounding
 * quotes. It is not a dotenv implementation and does not need to be — the file
 * it reads is written by `scripts/setup` and has five plain lines.
 */
function fwHostFromRootEnv(): string | undefined {
  let text: string;
  try {
    text = readFileSync(ROOT_ENV, "utf8");
  } catch {
    return undefined;
  }
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line.length === 0 || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    if (line.slice(0, eq).trim() !== "FW_HOST") continue;
    const value = line
      .slice(eq + 1)
      .trim()
      .replace(/^["']|["']$/g, "");
    if (value.length > 0) return value;
  }
  return undefined;
}

function resolveApiUrl(): string {
  const override = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (override) return override;

  const host = process.env.FW_HOST?.trim() || fwHostFromRootEnv();
  if (!host) {
    throw new Error(
      [
        "FW_HOST is not set, so apps/mobile has no API address to give the phone.",
        "",
        "It is deliberately not defaulted: a default would be this machine's own",
        "address, which on a handset means the handset, and the app would report",
        "'cannot reach the server' with the server running fine.",
        "",
        "Fix it by running the project's setup once, from the repo root:",
        "    ./scripts/setup",
        "or by setting the value yourself, in the repo-root .env:",
        "    FW_HOST=<the address other devices reach this laptop on>",
        "Any host works — a LAN IP, an mDNS name, or a Tailscale MagicDNS name.",
      ].join("\n"),
    );
  }
  return `http://${host}:${API_PORT}`;
}

export default (): ExpoConfig => ({
  name: "Fun World",
  slug: "fun-world",
  version: "0.0.1",
  orientation: "portrait",
  scheme: "funworld",
  userInterfaceStyle: "automatic",
  plugins: ["expo-router"],
  ios: { supportsTablet: true },
  android: { package: "com.funworld.mobile" },
  extra: {
    /**
     * Read at runtime by `src/api/config.ts`. There is one runtime lookup, not
     * two: `process.env.EXPO_PUBLIC_API_URL` is an INPUT to the resolution
     * above, and the resolved answer travels to the device only through here.
     */
    apiUrl: resolveApiUrl(),
  },
});
