"""Thin OpenProject API v3 client.

Deliberately small and deliberately not an MCP server. An MCP server mirrors
the API, which hands every agent raw work-package access -- and a mirror
cannot refuse an invalid transition. Every rule in OWNERS.yml would degrade
into a suggestion. This client is the only door, so the rules can live in
front of it (see main.py).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

from owners import ROOT, board

# Status ids on this instance. OpenProject's defaults turned out to fit the
# agent workflow better than the six I would have invented -- "Test failed"
# in particular is exactly the qa -> implementer bug state.
STATUS = {
    "backlog": 1,       # New
    "ready": 4,         # Confirmed
    "claimed": 7,       # In progress
    "review": 9,        # In testing  — PR open, qa checking
    "failed": 11,       # Test failed — the bug loop
    "blocked": 13,      # On hold     — escalated to a human
    "done": 12,         # Closed
    "rejected": 14,     # Rejected
}
TYPE = {"task": 1, "milestone": 2, "feature": 4, "epic": 5, "bug": 7}


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, details: list[str] | None = None):
        self.status, self.message, self.details = status, message, details or []
        super().__init__(f"HTTP {status}: {message}")

    def render(self) -> str:
        out = [f"OpenProject rejected the request (HTTP {self.status}): {self.message}"]
        out += [f"  - {d}" for d in self.details]
        return "\n".join(out)


def _load_env() -> tuple[str, str]:
    url = os.environ.get("OPENPROJECT_URL")
    key = os.environ.get("OPENPROJECT_API_KEY")
    if url and key:
        return url.rstrip("/"), key
    envfile = ROOT / ".env.local"
    if envfile.exists():
        for line in envfile.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "OPENPROJECT_URL" and not url:
                url = v.strip()
            elif k.strip() == "OPENPROJECT_API_KEY" and not key:
                key = v.strip()
    if not url or not key:
        raise SystemExit(
            "No OpenProject credentials.\n"
            "  Expected OPENPROJECT_URL and OPENPROJECT_API_KEY in the environment\n"
            f"  or in {envfile}\n"
            "  Get a key: OpenProject -> My account -> Access tokens -> API -> Generate"
        )
    return url.rstrip("/"), key


class Client:
    def __init__(self) -> None:
        self.base, key = _load_env()
        self.auth = base64.b64encode(f"apikey:{key}".encode()).decode()
        self.project = board().get("project", "fun-world")

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Basic {self.auth}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r) if r.status != 204 else {}
        except urllib.error.HTTPError as e:
            try:
                payload = json.load(e)
            except Exception:
                raise ApiError(e.code, e.reason or "unknown")
            details = [
                d.get("message", "")
                for d in (payload.get("_embedded", {}).get("errors") or [])
            ]
            raise ApiError(e.code, payload.get("message", e.reason or "unknown"), details)
        except urllib.error.URLError as e:
            raise SystemExit(
                f"Cannot reach OpenProject at {self.base} ({e.reason}).\n"
                "  Is it running?  docker compose -f ../openproject-selfhost/docker-compose.yml ps"
            )

    # --- schema discovery -------------------------------------------------
    # List custom fields take an option href, not a plain string, and the ids
    # are instance-specific. Discover them once rather than hardcoding.
    @lru_cache(maxsize=8)
    def _form_schema(self, type_id: int) -> dict:
        form = self.call(
            "POST",
            f"/api/v3/projects/{self.project}/work_packages/form",
            {"_links": {"type": {"href": f"/api/v3/types/{type_id}"}}},
        )
        return form["_embedded"]["schema"]

    def option_href(self, field: str, value: str, type_id: int = TYPE["task"]) -> str | None:
        allowed = self._form_schema(type_id).get(field, {}).get("_embedded", {}).get("allowedValues") or []
        for o in allowed:
            if o.get("value") == value:
                return o["_links"]["self"]["href"]
        return None

    def allowed_values(self, field: str, type_id: int = TYPE["task"]) -> list[str]:
        allowed = self._form_schema(type_id).get(field, {}).get("_embedded", {}).get("allowedValues") or []
        return [o.get("value") for o in allowed if o.get("value")]

    # --- work packages ----------------------------------------------------
    def get_wp(self, wp_id: int) -> dict:
        return self.call("GET", f"/api/v3/work_packages/{wp_id}")

    def patch_wp(self, wp_id: int, changes: dict) -> dict:
        """PATCH with the current lockVersion -- OpenProject rejects a stale one,
        which is what stops two agents clobbering each other's update."""
        current = self.get_wp(wp_id)
        body = dict(changes)
        body["lockVersion"] = current["lockVersion"]
        return self.call("PATCH", f"/api/v3/work_packages/{wp_id}", body)

    def allowed_transitions(self, wp_id: int, lock_version: int | None = None) -> list[str]:
        """Statuses this work package may legally move to right now.

        OpenProject enforces a per-type, per-role workflow, so a status change
        that looks obviously correct can still be rejected. Asking first turns
        an opaque 422 into a sentence that says what to do instead.

        The form endpoint needs the current lockVersion in its body -- omit it
        and it answers 409 Conflict, which reads like a concurrent-edit problem
        and is really just a malformed request.
        """
        if lock_version is None:
            lock_version = self.get_wp(wp_id)["lockVersion"]
        form = self.call(
            "POST", f"/api/v3/work_packages/{wp_id}/form", {"lockVersion": lock_version}
        )
        allowed = form["_embedded"]["schema"].get("status", {}).get("_embedded", {}).get(
            "allowedValues", []
        )
        return [o.get("name") for o in allowed if o.get("name")]

    def set_status(self, wp_id: int, key: str, extra: dict | None = None) -> dict:
        """Move to a named status from STATUS, refusing clearly if the workflow
        does not permit it.

        Reads the work package exactly once and reuses that lockVersion for the
        write. Fetching it twice invites a 409 for no reason, and a spurious
        conflict is far more confusing than a real one.
        """
        target_id = STATUS[key]
        target_name = self._status_name(target_id)

        current = self.get_wp(wp_id)
        allowed = self.allowed_transitions(wp_id, current["lockVersion"])
        if allowed and target_name not in allowed:
            now = current["_links"]["status"]["title"]
            raise ApiError(
                422,
                f"the workflow does not allow '{now}' -> '{target_name}' for this type",
                [f"legal from here: {', '.join(allowed)}"],
            )

        body = dict(extra or {})
        links = dict(body.get("_links") or {})
        links["status"] = {"href": f"/api/v3/statuses/{target_id}"}
        body["_links"] = links
        body["lockVersion"] = current["lockVersion"]
        return self.call("PATCH", f"/api/v3/work_packages/{wp_id}", body)

    @lru_cache(maxsize=32)
    def _status_name(self, status_id: int) -> str:
        return self.call("GET", f"/api/v3/statuses/{status_id}")["name"]

    def create_wp(self, body: dict) -> dict:
        return self.call("POST", f"/api/v3/projects/{self.project}/work_packages", body)

    def comment(self, wp_id: int, text: str) -> dict:
        return self.call(
            "POST",
            f"/api/v3/work_packages/{wp_id}/activities",
            {"comment": {"format": "markdown", "raw": text}},
        )

    def query(self, filters: list[dict], page_size: int = 100) -> list[dict]:
        q = urllib.parse.quote(json.dumps(filters))
        path = f"/api/v3/projects/{self.project}/work_packages?pageSize={page_size}&filters={q}"
        return self.call("GET", path).get("_embedded", {}).get("elements", [])


import urllib.parse  # noqa: E402  (needed by query, imported late to keep the header tidy)
