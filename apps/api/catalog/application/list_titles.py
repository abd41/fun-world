"""Use case: list the catalog.

The application layer. It depends on the domain and on an interface it defines
itself — never on Django, never on HTTP. `.importlinter` forbids
`django.http`, `django.shortcuts` and `ninja` here.

The ORM is *not* forbidden at this layer, which is a deliberate compromise
recorded in `.importlinter`: Django models leak through repository return types
in practice, and pretending otherwise produces mapping code nobody maintains.
The line drawn is that HTTP has no business this far in.
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
    any object with a matching `all()` satisfies it, including a plain list
    wrapper in a test, with no import of this module at all.
    """

    def all(self) -> list[Title]: ...


def list_titles(repository: TitleRepository) -> list[Title]:
    """Every title in the catalog.

    No pagination, filtering or ordering — vertical 003 concerns, and the
    contract (`contracts/titles.md`) explicitly promises nothing about order.

    Returning an empty list for an empty catalog is the whole reason FR-008 is
    satisfiable: "no titles" is a successful result, distinguishable by the
    client from "the server could not be reached". A use case that raised on an
    empty catalog would collapse those two states into one failure path.
    """
    return repository.all()
