from django.apps import AppConfig


class CoreConfig(AppConfig):
    """The catalog's persistence layer.

    Named `core` rather than `catalog` deliberately: `catalog/` is api-agent's
    Django-free domain and application code (ADR-0016). Keeping the ORM here
    and the rules there is what `import-linter` enforces.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Catalog"
