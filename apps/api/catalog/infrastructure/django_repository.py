"""The concrete repository: Django ORM on one side, domain objects on the other.

This is the layer that pays for the boundary. `catalog.application` declares
`TitleRepository` as a Protocol and never imports Django; something has to turn
rows into domain objects, and it is this module. `.importlinter` allows `django`
and `core` here and nowhere further in.

Dependency direction, stated correctly: this module depends inward on the
domain, and `catalog.application` also depends on the domain. Nothing depends
outward on this module — the application layer knows only its own Protocol, and
is wired to this implementation at the edge, in `catalog.api`.

Whether the mapping earns its keep is the open question in ADR-0016, which says
to watch for the layering becoming ceremonial. Right now it is two fields and a
loop. It will be worth revisiting at vertical 003, when a Title has a licence, a
kind, seasons and artwork, and the mapping either starts carrying real rules or
is still just copying attributes.
"""

from __future__ import annotations

import logging

from catalog.domain.title import InvalidTitle, Title
from core.models import Title as TitleRow

log = logging.getLogger(__name__)


class DjangoTitleRepository:
    """Reads titles out of Postgres and hands back domain objects.

    Structurally satisfies `catalog.application.list_titles.TitleRepository`
    without importing it — that is the point of a Protocol.
    """

    def list_all(self) -> list[Title]:
        # `.only()` because the domain type has two fields and the table will
        # grow many more in vertical 003. Selecting columns nobody reads is the
        # kind of thing that is free now and quietly expensive later.
        rows = TitleRow.objects.only("id", "name")

        titles: list[Title] = []
        for row in rows:
            try:
                titles.append(Title(id=row.id, name=row.name))
            except InvalidTitle:
                # A read path must not fail on data it did not create.
                #
                # `Title.__post_init__` rejects a blank name, and `Title.save()`
                # enforces the same rule — but `bulk_create`, `QuerySet.update`,
                # `loaddata` and data migrations all bypass `save()`, so a row
                # violating the invariant can exist. Before this, exactly one
                # such row turned the whole endpoint into a 500.
                #
                # That matters more than it looks: contracts/titles.md says
                # clients treat any non-200 as "cannot reach the server", so a
                # healthy server with one bad row became indistinguishable from
                # an unreachable one — the FR-008 collapse the empty-catalog
                # rule exists to prevent.
                #
                # Skipping keeps the catalog readable and makes the bad row
                # visible in the log rather than silent. The real fix is a
                # database CheckConstraint so the row cannot exist at all;
                # that belongs to data-agent, on core/models.py, and is noted
                # on the work package.
                log.warning(
                    "Skipping title %s: stored name fails the domain rule. "
                    "It was probably written by a path that bypasses save().",
                    row.id,
                )
        return titles
