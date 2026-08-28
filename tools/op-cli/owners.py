"""Path -> owner resolution. The single implementation of the routing rule.

Everything that needs to answer "who owns this file?" imports from here:
the pre-commit guard, the test suite, and op-cli itself. Two implementations
of this logic would eventually disagree, and the disagreement would show up
as an agent being allowed to write somewhere it should not.

Resolution is TOP-DOWN, FIRST MATCH WINS -- see the comment in OWNERS.yml for
why that beats "most specific wins".
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OWNERS_FILE = ROOT / "OWNERS.yml"

HUMAN = "HUMAN"
UNOWNED = "UNOWNED"
# Any agent may write these — see `shared_generated` in OWNERS.yml.
SHARED = "SHARED"


@dataclass(frozen=True)
class Resolution:
    owner: str
    rule: str

    @property
    def writable_by_agent(self) -> bool:
        if self.owner == SHARED:
            return True
        return self.owner not in (HUMAN, UNOWNED) and not self.owner.startswith("AMBIGUOUS")


@lru_cache(maxsize=1)
def load(path: str | None = None) -> dict:
    return yaml.safe_load(Path(path or OWNERS_FILE).read_text(encoding="utf-8"))


def _match(path: str, pattern: str) -> bool:
    """Glob match with `**` semantics fnmatch doesn't give us on its own."""
    # NB: lstrip("./") would strip *characters*, turning ".env.local" into
    # "env.local" and silently dropping every dotfile out of its protection
    # rule. Strip the "./" prefix only.
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    if fnmatch.fnmatch(path, pattern):
        return True
    # `dir/**` should match `dir/` and everything beneath it
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if path == prefix or path.startswith(prefix + "/"):
            return True
    # `**/x` should match at any depth
    if pattern.startswith("**/"):
        rest = pattern[3:]
        parts = path.split("/")
        for i in range(len(parts)):
            tail = "/".join(parts[i:])
            if fnmatch.fnmatch(tail, rest):
                return True
            if rest.endswith("/**") and tail.startswith(rest[:-2]):
                return True
    return False


def resolve(path: str, cfg: dict | None = None) -> Resolution:
    """Return who may write `path`.

    UNOWNED is a refusal, not a permission -- a path no rule covers cannot be
    claimed. Silence is never authorisation.
    """
    cfg = cfg or load()

    # Shared generated artifacts are checked before anything else: they are
    # outputs, so ownership does not apply to them at all.
    for pattern in cfg.get("shared_generated", []) or []:
        if _match(path, pattern):
            return Resolution(SHARED, f"shared_generated[{pattern}]")

    for rule in cfg.get("precedence", []):
        for pattern in rule["paths"]:
            if _match(path, pattern):
                return Resolution(rule["owner"], f"precedence[{pattern}]")

    hits = [
        (agent, pattern)
        for agent, spec in cfg["owners"].items()
        for pattern in (spec.get("writes") or [])
        if _match(path, pattern)
    ]
    if not hits:
        return Resolution(UNOWNED, "no rule")

    # Several patterns matching is fine as long as they agree. An agent may
    # legitimately own a directory AND a cross-cutting pattern inside it --
    # data-agent owns `apps/api/core/**` and also `apps/api/**/migrations/**`,
    # so `core/migrations/0001.py` matches twice and is not ambiguous.
    # Ambiguity is about *disagreement*, not about the number of matches.
    agents = {h[0] for h in hits}
    if len(agents) == 1:
        matched = hits[0][1] if len(hits) == 1 else f"{len(hits)} patterns, all {hits[0][0]}"
        return Resolution(hits[0][0], f"owners[{matched}]")

    return Resolution(
        "AMBIGUOUS:" + ",".join(sorted(agents)),
        "CONFLICT — two agents claim this; add a precedence rule",
    )


def route(paths: list[str], cfg: dict | None = None) -> dict[str, list[str]]:
    """Group paths by owning agent. More than one key means the ticket splits."""
    cfg = cfg or load()
    out: dict[str, list[str]] = {}
    for p in paths:
        out.setdefault(resolve(p, cfg).owner, []).append(p)
    return out


def limits(cfg: dict | None = None) -> dict:
    return (cfg or load()).get("limits", {})


def board(cfg: dict | None = None) -> dict:
    return (cfg or load()).get("board", {})


def accounts(cfg: dict | None = None) -> dict:
    """The GitHub logins for the agent account and the reviewing human.

    Read from OWNERS.yml rather than .env.local so it is available in CI. The
    guard that needs it must fail loudly when it is missing, never quietly
    decide that no agent is acting -- see check_boundaries.py.
    """
    return (cfg or load()).get("accounts", {})
