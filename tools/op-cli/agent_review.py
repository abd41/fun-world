#!/usr/bin/env python3
"""Post review-agent's findings as INLINE comments on the diff.

Two things this gets right that a plain review body does not.

**Inline comments create resolvable threads.** The ruleset on `main` requires
review threads to be resolved before merge -- but that rule only acts on real
conversation threads, and only inline comments anchored to a diff line create
one. A review body creates no thread, so it blocks nothing. Posting findings as
a body was the difference between review-agent having teeth and having none.

**A finding anchored to a line is actionable.** "literal hex in page.tsx" sends
someone hunting; a comment on the line does not.

Approval remains impossible: every call is forced through GH_AGENT_TOKEN, and
that account opened the pull request, so GitHub refuses self-approval. The rule
is structural rather than a promise in a prompt.

    FW_AGENT=review-agent python tools/op-cli/agent_review.py --pr 5 \\
        --finding "apps/web/app/page.tsx:14:literal hex #E50914 — constitution §14" \\
        --note "Does the rail abstraction earn its keep at one caller?"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from owners import ROOT  # noqa: E402

REPO = "abd41/fun-world"


def env() -> dict[str, str]:
    out = dict(os.environ)
    f = ROOT / ".env.local"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip())
    return out


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def gh_api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    cmd = ["gh", "api", "-X", method, path]
    if body is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(
        cmd, input=json.dumps(body) if body is not None else None,
        capture_output=True, text=True, cwd=ROOT,
        env={**os.environ, "GH_TOKEN": token},
    )
    raw = (r.stdout or r.stderr or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"message": raw.replace(token, "<REDACTED>") or "no response"}


def parse_finding(s: str) -> tuple[str, int, str]:
    """`path:line:message` -> (path, line, message)."""
    parts = s.split(":", 2)
    if len(parts) < 3 or not parts[1].strip().isdigit():
        die(f"--finding must be path:line:message, got:\n  {s}\n"
            "  A finding without a line cannot become a thread, and a comment\n"
            "  that is not a thread does not block the merge. Use --note for\n"
            "  something that genuinely has no location.")
    return parts[0].strip(), int(parts[1]), parts[2].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--finding", action="append", default=[],
                    help="path:line:message — becomes a blocking inline thread. Repeatable.")
    ap.add_argument("--note", action="append", default=[],
                    help="judgement call with no single location. Non-blocking. Repeatable.")
    ap.add_argument("--clean", action="store_true", help="explicitly report nothing mechanical found")
    a = ap.parse_args()

    e = env()
    if e.get("FW_AGENT", "").strip() != "review-agent":
        die("FW_AGENT must be review-agent to post a review.")
    token = e.get("GH_AGENT_TOKEN", "").strip()
    if not token:
        die("GH_AGENT_TOKEN missing. Without it this falls back to your own gh\n"
            "session, and the agent could approve — the one thing it must not do.")
    if not (a.finding or a.note or a.clean):
        die("Nothing to say. Pass --finding, --note, or --clean.")

    pr = gh_api("GET", f"repos/{REPO}/pulls/{a.pr}", token)
    if "head" not in pr:
        die(f"could not read PR #{a.pr}: {pr.get('message')}")
    commit_id = pr["head"]["sha"]

    changed = {f["filename"] for f in gh_api("GET", f"repos/{REPO}/pulls/{a.pr}/files", token)} \
        if isinstance(gh_api("GET", f"repos/{REPO}/pulls/{a.pr}/files", token), list) else set()
    files = gh_api("GET", f"repos/{REPO}/pulls/{a.pr}/files", token)
    changed = {f["filename"] for f in files} if isinstance(files, list) else set()

    comments = []
    for raw in a.finding:
        path, line, msg = parse_finding(raw)
        if changed and path not in changed:
            die(f"'{path}' is not in this pull request's diff.\n"
                "  GitHub can only anchor a comment to a changed line.\n"
                f"  Changed here: {', '.join(sorted(changed)[:6])}"
                + (" ..." if len(changed) > 6 else ""))
        comments.append({"path": path, "line": line, "side": "RIGHT", "body": msg})

    body_parts = ["## review-agent", ""]
    if a.clean and not a.finding:
        body_parts += ["No mechanical violations found: no literal hex outside `packages/tokens`,",
                       "no hardcoded hosts, no hand-edited contracts, no runtime asset fetches.", ""]
    elif a.finding:
        body_parts += [f"{len(comments)} mechanical finding(s) left inline. "
                       "Each is a thread, and unresolved threads block the merge.", ""]
    if a.note:
        body_parts += ["**Judgement — flagged, not resolved. Your call:**", ""]
        body_parts += [f"- {n}" for n in a.note] + [""]
    body_parts += ["---",
                   "_Comments only. This agent cannot approve — that is structural, "
                   "not a promise._"]

    payload = {"commit_id": commit_id, "event": "COMMENT", "body": "\n".join(body_parts)}
    if comments:
        payload["comments"] = comments

    res = gh_api("POST", f"repos/{REPO}/pulls/{a.pr}/reviews", token, payload)
    if "id" not in res:
        die("posting the review failed:\n  " + str(res.get("message")))

    print(f"posted review on PR #{a.pr}")
    print(f"  {len(comments)} inline thread(s) — these block the merge until resolved")
    print(f"  {len(a.note)} note(s) — flagged for a human, non-blocking")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
