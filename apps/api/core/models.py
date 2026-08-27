"""Persistence for the catalog.

This is the *infrastructure* layer (ADR-0016): it knows about columns, indexes
and Django admin. The domain equivalent — a plain dataclass with no framework
import — lives in `catalog/domain/title.py` and is written by `api-agent`.

Two models for one concept looks like ceremony at this size, and for a Title
with a name it honestly is. It is done here anyway because `import-linter` has
never run against real code, and a layering contract that passes only because
the package is empty proves nothing. See data-model.md, which records that this
justification expires after vertical 001.
"""

import uuid

from django.db import models


class Title(models.Model):
    """One item of watchable content."""

    # UUID rather than a sequential integer: from vertical 005 these appear in
    # playback URLs, and a catalog whose contents can be enumerated by counting
    # upwards is an avoidable mistake to design in now, while it is free.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=200,
        help_text="Display name. Shown by every client.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest first is a reasonable default for a person opening the admin.
        # It is deliberately NOT a promise to API clients -- contracts/titles.md
        # says ordering is unspecified, and a client that starts depending on
        # this would be relying on something no test enforces.
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """Reject a blank name.

        A title whose name is whitespace renders as an empty row, which is
        indistinguishable from "no titles" — the exact confusion FR-008 exists
        to prevent. `CharField` alone would allow it, since Django treats a
        space as a non-empty string.
        """
        from django.core.exceptions import ValidationError

        if not (self.name or "").strip():
            raise ValidationError({"name": "A title needs a name."})

    def save(self, *args, **kwargs):
        # full_clean() is not called by save() in Django, so validation defined
        # above would apply in the admin and silently not in a management
        # command or a shell. Calling it here means the rule holds everywhere.
        self.full_clean()
        return super().save(*args, **kwargs)
