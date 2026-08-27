"""Use case: list the catalog.

The application layer. It depends on the domain and on an interface it defines
itself. `.importlinter` forbids **`django`, `ninja` and `core`** here — the
whole framework and the ORM app, not merely HTTP.

That is stricter than it first looked, and the reversal is worth knowing.
The original rule was "forbid `django.http` and `django.shortcuts`, allow the
ORM", on the reasoning that Django models leak through repository return types
and pretending otherwise produces mapping code nobody maintains.

import-linter rejected it: subpackages of external packages cannot be
forbidden, only whole packages. That forced a decision instead of a compromise,
and the stricter answer turned out to be correct — the *concrete* repository
belongs in `catalog.infrastructure`, which may import `django` and `core`
freely. So this layer never needs either, and the leak the compromise was
designed around does not exist.
"""

from __future__ import annotations

from typing import Protocol

from catalog.domain.title import Title


class TitleRepository(Protocol):
    """What this use case needs from storage.

    Declared *here*, in the layer that consumes it, rather than in the layer
    that implements it. That is the dependency inversion the onion is for: the
    concrete repository in `infrastructure` depends on this Protocol, so
    storage can be replaced without the use case knowing.

    A Protocol rather than an ABC because nothing needs to inherit from it —
    any object with a matching `list_all()` satisfies it, including a plain
    list wrapper in a test, with no import of this module at all.

    Named `list_all()` rather than `all()` on purpose. `all()` is what
    `Model.objects` calls it, and borrowing that name from the very thing this
    Protocol exists to invert invites an implementer to assume a QuerySet is
    on the other side.
    """

    def list_all(self) -> list[Title]: ...


def list_titles(repository: TitleRepository) -> list[Title]:
    """Every title in the catalog.

    No pagination, filtering or ordering — vertical 003 concerns, and the
    contract (`contracts/titles.md`) explicitly promises nothing about order.

    Returning an empty list for an empty catalog is the whole reason FR-008 is
    satisfiable: "no titles" is a successful result, distinguishable by the
    client from "the server could not be reached". A use case that raised on an
    empty catalog would collapse those two states into one failure path.
    """
    return repository.list_all()
