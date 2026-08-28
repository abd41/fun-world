#!/usr/bin/env python3
"""Assemble everything review-agent needs to actually review a pull request.

The gap this closes: `agent_review.py` posts findings it is handed. It reads
nothing. For thirteen pull requests "posted review" meant a message was
published, not that anything was examined.

The findings that were missed had one thing in common -- every one was a
CROSS-REFERENCE between two artefacts:

    a docstring        vs  the config it claimed to describe
    a comment          vs  the package names that actually exist
    a domain constant  vs  the ORM column it must agree with
    a method name      vs  the purpose the same file states

None is visible in a single file, and none is greppable. They need a reader
holding several things at once. So this brief does not hand over a diff -- it
hands over the diff PLUS the material the diff makes claims about.

    python tools/op-cli/review_brief.py --pr 13 > brief.md

The brief is then given to review-agent, which decides the findings and calls
agent_review.py with what IT found -- rather than with what someone passed in.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import ROOT, resolve  # noqa: E402

REPO = "abd41/fun-world"
MAX_DIFF_CHARS = 60_000


def gh(args: list[str]) -> str:
    # encoding="utf-8" explicitly. `text=True` alone decodes with the LOCALE
    # codec, which on this machine is cp1252 -- so any diff containing a
    # character outside Latin-1 killed this script with UnicodeDecodeError.
    #
    # It went unnoticed because em-dashes ARE in cp1252, so every earlier brief
    # worked. It first failed on a PR whose tests used Japanese text, and it
    # failed in the worst available way: the caller redirects stdout to a file,
    # so the traceback landed IN the brief. A 26-line "brief" containing a
    # Python stack trace would have been handed to review-agent, which would
    # have reviewed the traceback and reported on a diff it never saw.
    #
    # errors="replace" so one undecodable byte degrades a character rather than
    # losing the whole review.
    r = subprocess.run(
        ["gh", *args], capture_output=True, cwd=ROOT,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        print(f"gh {' '.join(args)} failed:\n{r.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return r.stdout


def referenced_docs(diff: str, changed: list[str]) -> list[Path]:
    """Files the diff makes claims ABOUT, which must be read alongside it.

    This is the whole point. A docstring describing `.importlinter` is only
    checkable if `.importlinter` is in front of the reader too.
    """
    out: set[Path] = set()

    # Anything the diff names by path or backtick.
    for m in re.finditer(r"[`\s(]([\w./-]+\.(?:py|ts|tsx|yml|yaml|json|md|importlinter))", diff):
        p = ROOT / m.group(1).lstrip("./")
        if p.is_file() and p.as_posix() not in changed:
            out.add(p)

    # Config files that rules live in are always relevant.
    for always in (".importlinter", "OWNERS.yml"):
        p = ROOT / always
        if p.is_file():
            out.add(p)

    # ADRs the diff cites by number.
    for m in re.finditer(r"ADR-(\d{4})", diff):
        for p in (ROOT / "docs" / "adr").glob(f"{m.group(1)}-*.md"):
            out.add(p)

    return sorted(out)[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", type=int, required=True)
    a = ap.parse_args()

    # The brief is written to a FILE by the caller (`> brief.md`), so anything
    # this script prints becomes the brief. stdout must therefore be UTF-8
    # regardless of the console codepage -- otherwise a Japanese test fixture
    # in the diff crashes print() and the traceback becomes the review.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    meta = json.loads(gh(["pr", "view", str(a.pr), "--json",
                          "title,body,headRefName,author,files"]))
    diff = gh(["pr", "diff", str(a.pr)])

    # An empty diff means the brief would contain no code to review, and a
    # reviewer handed it would report "nothing wrong" having seen nothing.
    # Refuse loudly instead: this script's output IS the review's input, so a
    # silent degradation here is a review that never happened.
    if not diff.strip():
        print(f"REFUSING: `gh pr diff {a.pr}` returned nothing. "
              "A brief with no diff produces a review of nothing.", file=sys.stderr)
        return 1
    truncated = len(diff) > MAX_DIFF_CHARS
    if truncated:
        diff = diff[:MAX_DIFF_CHARS]

    changed = [f["path"] for f in meta.get("files", [])]

    print(f"# Review brief — PR #{a.pr}: {meta['title']}\n")
    print(f"Opened by `{meta['author']['login']}` on `{meta['headRefName']}`.\n")

    print("## Files changed, and who owns them\n")
    for path in changed:
        r = resolve(path)
        print(f"- `{path}` — **{r.owner}**")
    print()

    # The spec the ticket cites, if the body names one.
    if m := re.search(r"OP#(\d+)", meta.get("body") or ""):
        print(f"Work package **OP#{m.group(1)}**. "
              "Check the change against the acceptance criteria it claims to satisfy.\n")

    print("## What to look for\n")
    print("""Two kinds of finding, and do not blur them.

**Mechanical** — state flatly, with `path:line`. But note that the greppable
subset (literal colour, hardcoded hosts, runtime assets, hand-edited contracts)
is already enforced by `check_constitution.py` in CI. Do not re-report those;
look for what a grep cannot see.

**Cross-reference** — this is where the value is, and where every previously
missed finding lived:

- Does a docstring or comment still describe the config it claims to? Compare
  against the actual file, included below.
- Does a comment name a package, module or layer that exists?
- Are two declarations of the same constant kept in step by anything, or only
  by a comment saying they should be?
- Does a name match what the surrounding code says it is for?
- Does the change contradict an ADR it cites? Cite the ADR number if so.

**Judgement** — flag, do not resolve. Whether an abstraction earns its keep,
whether the spec was read correctly. Say what you noticed and stop.

Report with:

    FW_AGENT=review-agent python tools/op-cli/agent_review.py --pr {pr} \\
        --finding "path:line:what is wrong and which rule it breaks" \\
        --note "a judgement call for the human"

`--finding` needs `path:line` and becomes a blocking thread. Use `--note` only
when there is genuinely no single location. If nothing is wrong, pass `--clean`
and say so — a review that invents findings to look useful is worse than none.
""".replace("{pr}", str(a.pr)))

    print("## The diff\n")
    print("```diff")
    print(diff)
    if truncated:
        print(f"\n... truncated at {MAX_DIFF_CHARS} chars — review what is shown")
    print("```\n")

    print("## Files this diff makes claims about\n")
    print("*Included so cross-references can actually be checked rather than assumed.*\n")
    for p in referenced_docs(diff, changed):
        rel = p.relative_to(ROOT).as_posix()
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(body) > 6000:
            body = body[:6000] + "\n... truncated"
        print(f"### `{rel}`\n")
        print("```")
        print(body)
        print("```\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
