#!/usr/bin/env node
/**
 * The Expo CLI, with telemetry off.
 *
 * Constitution §6: "Framework telemetry is explicitly disabled, not merely
 * left at its default." Expo's default is ON — verified, not assumed:
 * `@expo/cli@57.0.19`, `build/bin/cli` line 272, reads
 *
 *     if (!boolish('EXPO_NO_TELEMETRY', false)) { ...report the command... }
 *
 * The second argument is the default, so an unset variable means telemetry.
 *
 * ## Why a wrapper and not an env file
 *
 * The root `.env` holds `NEXT_TELEMETRY_DISABLED=1`, but nothing exports that
 * file into the shell — Django reads it itself, and a pnpm script does not.
 * An `apps/mobile/.env` would work locally and could never be committed: the
 * repo-root `.gitignore` ignores `.env` at any depth.
 *
 * So the switch lives where it is guaranteed to run: in front of the CLI. This
 * only covers invocations that go through the package scripts. Running
 * `npx expo start` by hand bypasses it — which is a limitation worth stating
 * rather than papering over. Putting `EXPO_NO_TELEMETRY=1` in the repo-root
 * `.env.example` alongside `NEXT_TELEMETRY_DISABLED=1` would close that gap,
 * and that file is human-owned.
 *
 * The CLI is loaded in-process rather than spawned so that Ctrl-C reaches
 * `expo start`'s own signal handling unchanged.
 */
if (!process.env.EXPO_NO_TELEMETRY) {
  process.env.EXPO_NO_TELEMETRY = "1";
}

process.stderr.write("[fun-world] EXPO_NO_TELEMETRY=1 (constitution §6)\n");

require("expo/bin/cli");
