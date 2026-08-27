"""The domain's idea of a Title.

This module imports nothing from Django, django-ninja, Pydantic, or anything
that speaks HTTP. That is enforced by `.importlinter`, not merely intended
(constitution §32) — and this file is the first code that contract has ever
actually been run against. Until now it passed because the package was empty,
which proved nothing.

Why Pydantic is excluded specifically: it is the tempting one. It validates
nicely and looks harmless in an entity. But once entities carry `BaseModel`,
the domain starts being shaped by what is convenient to serialise rather than
by the rules it exists to hold. Serialisation belongs in presentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

# The longest name the catalog will accept. Duplicated as max_length on the ORM
# model, which is the usual cost of keeping the domain framework-free: the ORM
# needs it to build a column, the domain needs it to state a rule. If they ever
# disagree, this one is the rule and the column is wrong.
MAX_NAME_LENGTH = 200


class InvalidTitle(ValueError):
    """A Title was constructed that the domain does not consider valid."""


@dataclass(frozen=True)
class Title:
    """One item of watchable content.

    Frozen because a Title is a value here, not a thing being edited. Editing
    happens through Django admin against the ORM model; this type exists to be
    read, passed around, and reasoned about.
    """

    id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            # The same rule the ORM model enforces on save. It lives in both
            # places on purpose: the ORM protects the database, and this
            # protects any code path that builds a Title without touching the
            # database at all -- a fixture, a test, a future import.
            raise InvalidTitle("A title needs a name.")
        if len(self.name) > MAX_NAME_LENGTH:
            raise InvalidTitle(
                f"A title name is at most {MAX_NAME_LENGTH} characters, got {len(self.name)}."
            )

    @property
    def display_name(self) -> str:
        """What a client should show.

        Trivial today. It exists because it is the seam where a rule will go —
        a kids-profile filter, a localised title, a fallback when the name is
        missing in the viewer's language. Putting it here now means those
        arrive in the domain rather than being scattered across two clients.
        """
        return self.name.strip()
