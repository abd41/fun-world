"""HTTP surface for the catalog — the outermost layer.

This is where serialisation lives, which is why Pydantic is forbidden in the
domain and belongs here instead (`.importlinter`). It is also the layer that
`openapi.json` is derived from, and therefore what `packages/contracts` is
generated from: the shape declared below is the shape both clients compile
against.

Contract: `specs/001-platform-walking-skeleton/contracts/titles.md`.
If this file and that document disagree, the generated artefact wins and the
document is wrong — but they should not disagree, and T017 tests that.
"""

from __future__ import annotations

from uuid import UUID

from ninja import Router, Schema

from catalog.application.list_titles import list_titles
from catalog.infrastructure.django_repository import DjangoTitleRepository

router = Router(tags=["catalog"])


class TitleOut(Schema):
    """One title, as clients see it.

    `created_at` is deliberately absent. It exists on the model for provenance,
    and no client needs it — a field in the contract is
    a field two clients can come to depend on, and removing it later is a
    breaking change made for no reason.
    """

    id: UUID
    name: str


@router.get(
    "",
    response=list[TitleOut],
    summary="List every title",
    # Pinned, not derived. django-ninja defaults operation_id to the Python
    # path -- this one was `catalog_api_list_all`, which hey-api turned into a
    # client function named `catalogApiListAll`. That makes the module layout
    # part of the published contract: renaming this file or moving the function
    # would rename the function both clients call, so a pure refactor becomes a
    # breaking change with no diff in behaviour to explain it.
    operation_id="listTitles",
)
def list_all(request) -> list[TitleOut]:
    """Every title in the catalog.

    No pagination or filtering — vertical 003 concerns.

    Rows do arrive ordered, because `core.models.Title.Meta.ordering` is set for
    the admin's benefit, so the SQL carries `ORDER BY created_at DESC`. The
    contract still promises nothing about order, and that is deliberate: a
    client must not come to depend on an ordering that exists as a side effect
    of an admin convenience. T018 tests the contract's silence, not this
    default.

    An empty catalog returns `[]` with 200, never 404. That is what makes FR-008
    satisfiable: "no titles" has to be a *success* so a client can distinguish
    it from "could not reach the server". A 404 would collapse both into one
    failure path, and the two need different messages because they need
    different reactions from the person reading them.
    """
    titles = list_titles(DjangoTitleRepository())
    return [TitleOut(id=t.id, name=t.display_name) for t in titles]
