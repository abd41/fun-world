/**
 * Export the API's OpenAPI 3.1 document to `openapi.json`.
 *
 * This is step one of two. `openapi.json` is produced from the Django routers
 * here; `src/` is then produced from `openapi.json` by hey-api. Both are
 * generated, neither is authored (constitution §12).
 *
 * ## Why a file and not a URL
 *
 * hey-api can read a live URL, and that was the obvious first design. It is
 * the wrong one: it makes the drift gate depend on a running server, so CI
 * cannot regenerate without standing up Postgres and binding a port. A guard
 * that needs that much scaffolding to run is a guard that gets a conditional
 * wrapped around it, and this repo has already shipped three checks that went
 * green while enforcing nothing for exactly that reason.
 *
 * `export_openapi_schema` reads the router definitions through Django's app
 * registry. It touches no database and opens no socket -- verified against a
 * DATABASE_URL pointing at a dead port. So regeneration is a pure function of
 * the committed source, which is what makes SC-005's empty-diff check mean
 * something.
 *
 * ## Determinism
 *
 * `--sorted` and `--indent 2` are what make the output diffable. Without
 * sorted keys the ordering follows dict insertion, so an unrelated edit can
 * reshuffle the file and produce a diff that says nothing. A drift gate whose
 * output is unstable teaches people to ignore it.
 */
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(PACKAGE_DIR, "..", "..");
const API_DIR = join(REPO_ROOT, "apps", "api");
const OUTPUT = join(PACKAGE_DIR, "openapi.json");

const result = spawnSync(
  "uv",
  [
    "run",
    "python",
    "manage.py",
    "export_openapi_schema",
    // Named explicitly rather than letting django-ninja resolve("/api/") find
    // it. The lookup version depends on URL routing being importable *and*
    // matching, and fails with "No NinjaAPI instance found" -- which reads
    // like the API is broken when the real cause is a changed prefix.
    "--api",
    "config.urls.api",
    "--sorted",
    "--indent",
    "2",
    "--output",
    OUTPUT,
  ],
  { cwd: API_DIR, stdio: ["ignore", "inherit", "inherit"] },
);

if (result.error?.code === "ENOENT") {
  console.error(
    "uv not found on PATH. The schema is exported by Django, so generating\n" +
      "contracts needs the Python toolchain: https://docs.astral.sh/uv/",
  );
  process.exit(1);
}
if (result.status !== 0) {
  console.error(`\nSchema export failed (exit ${result.status}).`);
  process.exit(result.status ?? 1);
}

// django-ninja writes the JSON without a trailing newline. Add one, so the
// file is POSIX-clean and git stops reporting "\ No newline at end of file"
// on a file that is supposed to be boringly stable.
const schema = readFileSync(OUTPUT, "utf8");
if (!schema.endsWith("\n")) {
  writeFileSync(OUTPUT, `${schema}\n`, "utf8");
}

// A schema with no paths means the routers did not load. Django exits 0 in
// that case and writes a valid, empty document, which would then generate a
// valid, empty client -- and every downstream check would pass while the
// clients had nothing to call.
const { paths } = JSON.parse(schema);
const count = Object.keys(paths ?? {}).length;
if (count === 0) {
  console.error("Exported schema contains no paths. Refusing to write an empty contract.");
  process.exit(1);
}

console.log(`openapi.json — ${count} path${count === 1 ? "" : "s"}`);
