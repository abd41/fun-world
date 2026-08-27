"""The concrete repository: Django ORM on one side, domain objects on the other.

This is the layer that pays for the boundary. `catalog.application` declares
`TitleRepository` as a Protocol and never imports Django; something has to turn
rows into domain objects, and it is this module. `.importlinter` allows `django`
and `core` here and nowhere further in.

Whether that mapping earns its keep is the open question in ADR-0016, which
says to watch for the layering becoming ceremonial. Right now it is two fields
and a loop. It will be worth revisiting at vertical 003, when a Title has a
licence, a kind, seasons and artwork, and the mapping either starts carrying
real rules or is still just copying attributes.
"""

from __future__ import annotations

from catalog.domain.title import Title
from core.models import Title as TitleRow


class DjangoTitleRepository:
    """Reads titles out of Postgres and hands back domain objects.

    Structurally satisfies `catalog.application.list_titles.TitleRepository`
    without importing it — that is the point of a Protocol. This module depends
    inward on the domain; the application layer depends on neither.
    """

    def list_all(self) -> list[Title]:
        # `.only()` because the domain type has two fields and the table will
        # grow many more in vertical 003. Selecting columns nobody reads is the
        # kind of thing that is free now and quietly expensive later.
        rows = TitleRow.objects.only("id", "name")
        return [Title(id=row.id, name=row.name) for row in rows]
