"""Django admin registration — this is FR-009.

A maintainer edits a title without writing code, and SC-002 (change the stored
name, reload, see it) becomes one click rather than a SQL statement.

The admin binds directly to ORM models and skips the onion layers entirely.
That is a deliberate exception recorded in ADR-0016: the admin is a developer
tool, not a product surface, and routing it through the application layer would
buy nothing but indirection.
"""

from django.contrib import admin

from .models import Title


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "id")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)
