#!/usr/bin/env python3
"""op-cli -- the only door between an agent and the board.

Agents never call the OpenProject API directly. Everything goes through here,
because this is where the rules can actually be enforced:

  * claim   refuses paths the agent does not own
  * split   derives children from OWNERS.yml -- an agent never picks a recipient
  * handoff increments a counter and escalates to a human past the limit
  * bug     reopens rather than re-files, and demands an acceptance criterion

A limit an agent is merely asked to respect is not a limit (constitution §26).

Usage:
  op-cli show   --wp 42
  op-cli ls     [--agent web-agent] [--status claimed]
  op-cli claim  --wp 42 --agent api-agent
  op-cli split  --wp 42
  op-cli done   --wp 42 --pr 17
  op-cli bug    --paths apps/web/app/page.tsx --test e2e/browse.spec.ts:14 \\
                --criterion "004-identity AC-3" --title "..." [--reproduced 2]
  op-cli sync   specs/004-identity/tasks.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from client import STATUS, TYPE, ApiError, Client  # noqa: E402
from owners import HUMAN, UNOWNED, board, limits, load, resolve, route  # noqa: E402

F = board().get("fields", {})
AGENT, PATHS, SPEC, HANDOFF, LAYER, VERTICAL = (
    F.get("agent", "customField1"), F.get("paths", "customField2"),
    F.get("spec", "customField3"), F.get("handoff_count", "customField4"),
    F.get("layer", "customField5"), F.get("vertical", "customField6"),
)


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def text_field(value: str) -> dict:
    """Formattable custom fields take {format, raw}. Passing a bare string is
    accepted by the API and silently stores an empty value -- a data-loss trap
    worth having exactly one helper for."""
    return {"format": "markdown", "raw": value}


def wp_paths(wp: dict) -> list[str]:
    raw = wp.get(PATHS)
    raw = raw.get("raw") if isinstance(raw, dict) else raw
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[\n,]+", raw) if p.strip()]


def fmt(wp: dict) -> str:
    links = wp.get("_links", {})
    agent = (links.get(AGENT) or {}).get("title") or "-"
    return (f"#{wp['id']:<5} {(links.get('type') or {}).get('title',''):<8} "
            f"{(links.get('status') or {}).get('title',''):<14} {agent:<16} {wp['subject']}")


# --------------------------------------------------------------------------
def cmd_show(c: Client, a) -> int:
    wp = c.get_wp(a.wp)
    L = wp.get("_links", {})
    print(fmt(wp))
    for label, key in (("spec", SPEC), ("handoff", HANDOFF)):
        print(f"  {label:<9} {wp.get(key) if wp.get(key) is not None else '-'}")
    for label, key in (("layer", LAYER), ("vertical", VERTICAL)):
        print(f"  {label:<9} {(L.get(key) or {}).get('title') or '-'}")
    paths = wp_paths(wp)
    print(f"  paths     {paths or '- (unset: cannot be claimed)'}")
    if paths:
        for owner, group in route(paths).items():
            print(f"    -> {owner:<16} {', '.join(group)}")
    return 0


def cmd_ls(c: Client, a) -> int:
    filters = []
    if a.status:
        if a.status not in STATUS:
            die(f"unknown status '{a.status}'. Known: {', '.join(STATUS)}")
        filters.append({"status": {"operator": "=", "values": [str(STATUS[a.status])]}})
    rows = c.query(filters)
    if a.agent:
        rows = [w for w in rows if (w.get("_links", {}).get(AGENT) or {}).get("title") == a.agent]
    for w in sorted(rows, key=lambda w: w["id"]):
        print(fmt(w))
    print(f"\n{len(rows)} work package(s)")
    return 0


def cmd_claim(c: Client, a) -> int:
    cfg = load()
    if a.agent not in cfg["owners"]:
        die(f"'{a.agent}' is not an agent in OWNERS.yml. Known: {', '.join(sorted(cfg['owners']))}")

    wp = c.get_wp(a.wp)
    paths = wp_paths(wp)
    if not paths:
        die(f"#{a.wp} has no Paths set.\n"
            "  Routing is a function of paths; a ticket without them cannot be claimed.\n"
            "  Set the Paths field on the work package first.")

    grouped = route(paths, cfg)
    foreign = {o: p for o, p in grouped.items() if o != a.agent}
    if foreign:
        lines = [f"#{a.wp} is not {a.agent}'s to claim.\n"]
        for owner, ps in foreign.items():
            why = {HUMAN: "human-owned", UNOWNED: "no OWNERS.yml rule — unowned paths are refused"}.get(
                owner, f"owned by {owner}")
            lines.append(f"  {why}:")
            lines += [f"    {p}" for p in ps]
        if len(grouped) > 1:
            lines.append(f"\n  It spans {len(grouped)} owners. Split it instead:\n"
                         f"    op-cli split --wp {a.wp}")
        die("\n".join(lines))

    href = c.option_href(AGENT, a.agent, TYPE["task"])
    if not href:
        die(f"'{a.agent}' is not an allowed value of the board's Agent field.\n"
            f"  Board offers: {', '.join(c.allowed_values(AGENT, TYPE['task']))}")

    c.set_status(a.wp, "claimed", {"_links": {AGENT: {"href": href}}})
    print(f"claimed #{a.wp} -> {a.agent} (In progress)")
    for p in paths:
        print(f"  {p}")
    return 0


def cmd_split(c: Client, a) -> int:
    cfg, lim = load(), limits()
    wp = c.get_wp(a.wp)
    paths = wp_paths(wp)
    if not paths:
        die(f"#{a.wp} has no Paths set — nothing to split by.")

    depth = int(wp.get(HANDOFF) or 0)
    if depth >= lim.get("max_split_depth", 2):
        die(f"#{a.wp} is at split depth {depth}; the limit is {lim.get('max_split_depth', 2)}.\n"
            "  Escalating to a human instead of fanning out further.\n"
            f"  op-cli block --wp {a.wp} --why 'split depth exceeded'")

    grouped = {o: p for o, p in route(paths, cfg).items()}
    if len(grouped) < 2:
        only = next(iter(grouped))
        die(f"#{a.wp} resolves to a single owner ({only}) — there is nothing to split.\n"
            f"  op-cli claim --wp {a.wp} --agent {only}")

    cap = lim.get("max_children_per_split", 5)
    if len(grouped) > cap:
        die(f"#{a.wp} would fan out to {len(grouped)} children; the cap is {cap}.\n"
            "  Narrow the ticket's Paths, or break it up by hand.")

    L = wp.get("_links", {})
    made = []
    for owner, group in sorted(grouped.items()):
        if owner in (HUMAN, UNOWNED) or owner.startswith("AMBIGUOUS"):
            print(f"  skipped {owner}: {', '.join(group)}  (needs a human, not an agent)")
            continue
        body = {
            "subject": f"{wp['subject']} [{owner}]",
            "description": {"format": "markdown",
                            "raw": f"Split from #{a.wp} by path ownership.\n\nPaths:\n"
                                   + "\n".join(f"- `{p}`" for p in group)},
            PATHS: text_field("\n".join(group)),
            SPEC: wp.get(SPEC),
            HANDOFF: depth + 1,
            "_links": {"type": {"href": f"/api/v3/types/{TYPE['task']}"},
                       "parent": {"href": f"/api/v3/work_packages/{a.wp}"}},
        }
        if href := c.option_href(AGENT, owner, TYPE["task"]):
            body["_links"][AGENT] = {"href": href}
        for key in (LAYER, VERTICAL):
            if (v := L.get(key)) and v.get("href"):
                body["_links"][key] = {"href": v["href"]}
        child = c.create_wp(body)
        made.append((child["id"], owner))
        print(f"  #{child['id']} -> {owner}: {', '.join(group)}")

    c.comment(a.wp, "Split by path ownership:\n"
              + "\n".join(f"- #{i} → `{o}`" for i, o in made))
    print(f"\nsplit #{a.wp} into {len(made)} child work package(s)")
    print("Routing was derived from OWNERS.yml — no agent chose a recipient.")
    return 0


def cmd_done(c: Client, a) -> int:
    c.set_status(a.wp, "review")
    if a.pr:
        c.comment(a.wp, f"Pull request ready for review: #{a.pr}\n\n"
                        f"Put `OP#{a.wp}` in the PR description so OpenProject links them.")
    print(f"#{a.wp} -> In testing" + (f", PR #{a.pr} noted" if a.pr else ""))
    return 0


def cmd_block(c: Client, a) -> int:
    c.set_status(a.wp, "blocked")
    c.comment(a.wp, f"**Escalated to a human.** {a.why}")
    print(f"#{a.wp} -> On hold (needs a human): {a.why}")
    return 0


def cmd_bug(c: Client, a) -> int:
    """File a bug, routed by the path of the failing code.

    Two constitution rules are enforced here rather than trusted:
      §21 a bug names the acceptance criterion it violates, or it is a spec
          question and goes to a human -- otherwise an implementer will
          dutifully break correct code to satisfy a wrong test.
      §22 a failure is reproduced twice before filing, or one flaky test
          generates bugs forever.
    """
    lim = limits()
    if a.reproduced < 2:
        die(f"Reproduced {a.reproduced}x. A failure is filed only after 2 (constitution §22).\n"
            "  Re-run it; a flaky test would otherwise generate bugs indefinitely.")

    paths = [p.strip() for p in re.split(r"[\n,]+", a.paths) if p.strip()]
    grouped = route(paths)
    if len(grouped) != 1:
        die(f"The failing paths span {len(grouped)} owners: {', '.join(sorted(grouped))}.\n"
            "  Narrow the bug to one owner's code, or file it against the spec instead.")
    owner = next(iter(grouped))
    if owner in (HUMAN, UNOWNED):
        die(f"Failing paths resolve to {owner} — this is not an agent's bug.\n"
            "  It goes to a human.")

    # Reopen rather than re-file, so the handoff counter stays a real loop detector.
    existing = [w for w in c.query([{"status": {"operator": "!", "values": [str(STATUS["done"])]}}])
                if a.test in str(w.get("description", {}).get("raw", ""))]
    if existing:
        wp = existing[0]
        n = int(wp.get(HANDOFF) or 0) + 1
        if n > lim.get("max_handoff_count", 3):
            c.set_status(wp["id"], "blocked", {HANDOFF: n})
            c.comment(wp["id"], f"**Escalated.** `{a.test}` has failed {n} times. "
                                "The loop is not converging — a human should look.")
            print(f"#{wp['id']} failed {n}x -> On hold, escalated to a human")
            return 0
        c.set_status(wp["id"], "failed", {HANDOFF: n})
        c.comment(wp["id"], f"Still failing after the fix (attempt {n}).\n\n{a.detail or ''}")
        print(f"reopened #{wp['id']} -> Test failed (attempt {n}/{lim.get('max_handoff_count', 3)})")
        return 0

    body = {
        "subject": a.title,
        "description": {"format": "markdown",
                        "raw": f"**Failing test** `{a.test}`\n\n"
                               f"**Violates** {a.criterion}\n\n"
                               f"**Paths** {', '.join(f'`{p}`' for p in paths)}\n\n"
                               f"Reproduced {a.reproduced}x.\n\n{a.detail or ''}"},
        PATHS: text_field("\n".join(paths)), SPEC: a.criterion, HANDOFF: 1,
        "_links": {"type": {"href": f"/api/v3/types/{TYPE['bug']}"},
                   "status": {"href": f"/api/v3/statuses/{STATUS['failed']}"}},
    }
    if href := c.option_href(AGENT, owner, TYPE["bug"]):
        body["_links"][AGENT] = {"href": href}
    bug = c.create_wp(body)
    print(f"filed bug #{bug['id']} -> {owner} (derived from the failing path, not chosen)")
    return 0


def cmd_sync(c: Client, a) -> int:
    """Read a Spec Kit tasks.md into work packages. One source of truth: no
    GitHub Issues mirror, because two ticket systems drift apart."""
    md = Path(a.tasks)
    if not md.exists():
        die(f"no such file: {md}")
    spec_dir = md.parent.name
    existing = {w["subject"] for w in c.query([])}
    made = skipped = 0
    for line in md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*[-*]\s*\[([ xX])\]\s*(.+?)\s*$", line)
        if not m:
            continue
        subject = re.sub(r"\s+", " ", m.group(2))
        if subject in existing:
            skipped += 1
            continue
        body = {"subject": subject, SPEC: f"specs/{spec_dir}/spec.md",
                "_links": {"type": {"href": f"/api/v3/types/{TYPE['task']}"}}}
        if pm := re.search(r"`([^`]+)`", subject):
            body[PATHS] = text_field(pm.group(1))
        wp = c.create_wp(body)
        made += 1
        print(f"  #{wp['id']} {subject}")
    print(f"\nsynced {md}: {made} created, {skipped} already present")
    if made:
        print("Set Paths on any ticket that lacks them — without paths they cannot be claimed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="op-cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show"); s.add_argument("--wp", type=int, required=True); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("ls"); s.add_argument("--agent"); s.add_argument("--status"); s.set_defaults(fn=cmd_ls)
    s = sub.add_parser("claim"); s.add_argument("--wp", type=int, required=True)
    s.add_argument("--agent", required=True); s.set_defaults(fn=cmd_claim)
    s = sub.add_parser("split"); s.add_argument("--wp", type=int, required=True)
    s.add_argument("--by-paths", action="store_true", help="(default; accepted for readability)")
    s.set_defaults(fn=cmd_split)
    s = sub.add_parser("done"); s.add_argument("--wp", type=int, required=True)
    s.add_argument("--pr"); s.set_defaults(fn=cmd_done)
    s = sub.add_parser("block"); s.add_argument("--wp", type=int, required=True)
    s.add_argument("--why", required=True); s.set_defaults(fn=cmd_block)
    s = sub.add_parser("bug")
    s.add_argument("--paths", required=True); s.add_argument("--test", required=True)
    s.add_argument("--criterion", required=True); s.add_argument("--title", required=True)
    s.add_argument("--detail"); s.add_argument("--reproduced", type=int, default=1)
    s.set_defaults(fn=cmd_bug)
    s = sub.add_parser("sync"); s.add_argument("tasks"); s.set_defaults(fn=cmd_sync)
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.fn(Client(), args)
    except ApiError as e:
        die(e.render())


if __name__ == "__main__":
    raise SystemExit(main())
