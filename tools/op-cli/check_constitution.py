#!/usr/bin/env python3
"""Check the constitution's mechanically-checkable rules against the code.

This exists because `review-agent` did not. `agent_review.py` posts findings it
is handed; it reads no diff and analyses nothing, so for thirteen pull requests
"posted review on PR #N" meant a message was published, not that anything had
been examined. These are the rules a machine can settle without judgement, so
they belong in CI where they cannot be skipped -- not in a comment someone may
or may not read.

    python tools/op-cli/check_constitution.py            # whole repo
    python tools/op-cli/check_constitution.py --staged   # staged files only

Judgement calls -- does this docstring still describe the config it claims to,
does this abstraction earn its keep -- are NOT here. They need a reader.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Directories that are generated, vendored, or not ours to police.
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", "dist", ".next",
    ".turbo", ".expo", "staticfiles", "media",
}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".yml", ".yaml", ".sh"}


class Finding:
    def __init__(self, rule: str, path: Path, line: int, text: str, why: str):
        self.rule, self.path, self.line, self.text, self.why = rule, path, line, text.strip(), why

    def __str__(self) -> str:
        rel = self.path.relative_to(ROOT).as_posix()
        return f"  {rel}:{self.line}\n      {self.text[:96]}\n      §{self.rule} — {self.why}"


def files_to_check(staged_only: bool) -> list[Path]:
    if staged_only:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT,
        ).stdout
        paths = [ROOT / p.strip() for p in out.splitlines() if p.strip()]
    else:
        paths = [p for p in ROOT.rglob("*") if p.is_file()]
    return [
        p for p in paths
        if p.suffix in CODE_SUFFIXES
        and p.exists()
        and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    ]


# --- §14  tokens are the only source of colour -----------------------------
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# A hex string is only a *colour* in a styling context. `#deadbeef` in a comment
# about a commit sha is not a violation, and flagging it would train people to
# ignore this check.
COLOUR_CONTEXT = re.compile(r"(colou?r|background|border|fill|stroke|shadow|gradient|theme)", re.I)


def check_colour(path: Path, lines: list[str]) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("packages/tokens/") or rel.startswith("docs/") or rel.startswith("specs/"):
        return []
    if rel.startswith("tools/"):
        return []          # the checker's own regexes are not styling
    out = []
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith(("#", "//", "*", "/*")):
            continue       # a hex in prose is not a colour declaration
        if HEX.search(line) and COLOUR_CONTEXT.search(line):
            out.append(Finding("14", path, n, line,
                               "literal colour outside packages/tokens"))
    return out


# --- §7  no hardcoded hosts -------------------------------------------------
HOST = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\d+\.\d+\.\d+\.\d+)(:\d+)?")


def check_hosts(path: Path, lines: list[str]) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix()
    # Config, docs, tooling and infrastructure legitimately name addresses.
    # The rule is about APPLICATION code shipping one.
    if not (rel.startswith("apps/") or rel.startswith("packages/")):
        return []
    if "/tests/" in rel or "__tests__" in rel or rel.endswith((".yml", ".yaml", ".json")):
        return []
    out = []
    for n, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith(("#", "//", "*", '"""')):
            continue
        if HOST.search(line):
            out.append(Finding("7", path, n, line,
                               "hardcoded address in application code — use FW_HOST from env"))
    return out


# --- §29  third-party assets are vendored, never fetched at runtime ---------
ASSET_CDN = re.compile(
    r"https?://[^\s\"')]*\.(?:woff2?|ttf|otf|png|jpe?g|svg|gif|webp|lottie|json)\b", re.I
)
LOCAL_HOST_RE = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\d+\.\d+\.\d+\.\d+)")


def check_assets(path: Path, lines: list[str]) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix()
    if not (rel.startswith("apps/") or rel.startswith("packages/")):
        return []
    out = []
    for n, line in enumerate(lines, 1):
        m = ASSET_CDN.search(line)
        if m and not LOCAL_HOST_RE.search(m.group(0)):
            out.append(Finding("29", path, n, line,
                               "asset fetched from a third-party host at runtime — vendor it"))
    return out


def check_operation_ids(path: Path, lines: list[str]) -> list[Finding]:
    """Every django-ninja route pins an explicit operation_id.

    Not a constitution clause; an invariant T011 established and could only
    state in prose. django-ninja defaults operation_id to the Python module
    path, and hey-api turns that into the client function name -- so
    `catalog/api.py::list_all` published a function called `catalogApiListAll`.
    That puts the server's file layout in the contract: moving a function
    renames what both clients call, making a pure refactor a breaking change.

    A README sentence saying "new routes must set operation_id" is exactly the
    kind of rule that holds until the first person who has not read it. Parsed
    with ast rather than regex because these decorators wrap across lines.
    """
    rel = path.relative_to(ROOT).as_posix()
    if path.suffix != ".py" or not rel.startswith("apps/api/"):
        return []
    try:
        tree = ast.parse(chr(10).join(lines))
    except SyntaxError:
        return []       # not ours to report; the test suite will say so

    verbs = {"get", "post", "put", "patch", "delete", "api_operation"}
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr not in verbs:
                continue
            # Only ninja routers/APIs -- `router.get(...)`, `api.get(...)`.
            base = dec.func.value
            if not isinstance(base, ast.Name) or base.id not in {"router", "api"}:
                continue
            if not any(kw.arg == "operation_id" for kw in dec.keywords):
                out.append(Finding(
                    "T011", path, dec.lineno, lines[dec.lineno - 1],
                    f"route '{node.name}' has no operation_id, so the client "
                    "function name would be derived from this file's path",
                ))
    return out


# §12 (packages/contracts is generated, never authored) is deliberately NOT
# checked here.
#
# The first attempt tested for a `.generated` marker file. That was wrong twice
# over: hand-editing a file leaves the marker untouched, so it passes on exactly
# the case it claimed to catch; and it invented a convention that exists nowhere
# else in the repo and is absent from T011's instructions to contract-keeper.
#
# What actually detects hand-editing is regenerate-and-diff, which is §13 and is
# scheduled as T016. A check that cannot fail for the reason it names is worse
# than no check, because it occupies the space where a real one would go.


CHECKS = [
    ("§14 colour only from tokens", check_colour),
    ("§7  no hardcoded hosts", check_hosts),
    ("§29 assets vendored", check_assets),
    ("T011 routes pin operation_id", check_operation_ids),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true", help="only files staged for commit")
    args = ap.parse_args()

    paths = files_to_check(args.staged)
    findings: list[Finding] = []

    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for _, fn in CHECKS:
            findings.extend(fn(path, lines))

    print(f"  checked {len(paths)} file(s)")
    for label, _ in CHECKS:
        n = sum(1 for f in findings if label.split()[0].lstrip("§") == f.rule)
        print(f"  {'ok  ' if n == 0 else 'FAIL'} {label}" + (f"  ({n})" if n else ""))

    if findings:
        print(f"\nCONSTITUTION VIOLATIONS — {len(findings)}\n", file=sys.stderr)
        for f in findings:
            print(str(f), file=sys.stderr)
            print(file=sys.stderr)
        return 1

    print("\nno mechanical violations")
    print("Judgement calls are NOT covered here — they still need a reader.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
