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


@dataclass(frozen=True)
class Resolution:
    owner: str
    rule: str

    @property
    def writable_by_agent(self) -> bool:
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
    if len(hits) == 1:
        return Resolution(hits[0][0], f"owners[{hits[0][1]}]")
    if len(hits) > 1:
        agents = ",".join(sorted({h[0] for h in hits}))
        # Two owners for one path means OWNERS.yml needs a precedence rule.
        return Resolution(f"AMBIGUOUS:{agents}", "CONFLICT — add a precedence rule")
    return Resolution(UNOWNED, "no rule")


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
