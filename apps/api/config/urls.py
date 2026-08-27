"""URL routing.

Two surfaces, and the split matters:

  /admin/  Django admin — a developer tool. It binds directly to ORM models
           and deliberately skips the onion layers (ADR-0016). That shortcut
           is what makes FR-009 free: a maintainer edits a title without
           writing code.

  /api/    django-ninja — the product surface the clients consume, and what
           `openapi.json` describes. Everything here goes through the
           application layer.

## Registering a router is a human step, and that is a known cost

This file is HUMAN-owned (`apps/api/config/**`), so `api-agent` cannot add its
own router here. Each new router therefore needs a human commit — the same cost
as `INSTALLED_APPS`, accepted deliberately in research R1 because both are
project structure rather than feature work.

It is written down here because the alternative is worse in a specific way: if
this file imported a router before the agent had written it, the scaffold would
not boot at all, and T002 would ship broken waiting on T010. A bootable
scaffold with an explicit registration step beats a broken one with a
convenient import.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from ninja import NinjaAPI

from catalog.api import router as catalog_router

api = NinjaAPI(
    title="Fun World",
    version="0.1.0",
    description="Private home streaming. Not reachable from the public internet.",
)

api.add_router("/titles", catalog_router)


@api.get("/health", tags=["meta"], operation_id="health")
def health(request) -> dict:
    """Cheapest possible proof the API is up and reachable.

    Gives a client a way to distinguish "cannot reach the server" from "server
    is up but has no titles" — the two states FR-008 requires be told apart.

    This docstring is published: django-ninja puts it in `openapi.json`, which
    puts it in `sdk.gen.ts`, which both clients read. It previously claimed
    `scripts/setup` and the clean-runner CI job "both poll this". Neither does
    — setup makes no HTTP call at all, and the workflow polls `/healthz` below.
    The line was wrong when written and this change is the first thing that
    would have shipped it to a client.
    """
    return {"status": "ok"}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    # Kept outside the ninja app so it answers even if the API fails to build.
    path("healthz", lambda r: JsonResponse({"status": "ok"})),
]
