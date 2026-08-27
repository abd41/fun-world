"""Seed the catalog. Safe to run on every setup.

`scripts/setup` calls this every time, so it must be idempotent — a seed that
only works once teaches people not to re-run setup, which defeats the point of
setup being the single command.

Idempotence is by `name` rather than by id: the id is a random UUID, so
get_or_create on it would insert a new row every run. That is the specific bug
this docstring exists to stop someone reintroducing.
"""

from django.core.management.base import BaseCommand

from core.models import Title

# Blender Foundation open movies, CC-BY. Placeholder content that vertical 003
# can keep rather than throw away, and legal to stream (constitution §3).
#
# There is no licence or attribution column yet — those arrive with 003, and §3
# only bites once content is actually served to a viewer. Recorded here so the
# provenance is not lost in the meantime.
SEED_TITLES = [
    "Big Buck Bunny",
]


class Command(BaseCommand):
    help = "Insert the placeholder catalog. Idempotent — safe to re-run."

    def handle(self, *args, **options):
        created = existing = 0

        for name in SEED_TITLES:
            _, was_created = Title.objects.get_or_create(name=name)
            if was_created:
                created += 1
                self.stdout.write(f"  created  {name}")
            else:
                existing += 1

        total = Title.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"seed: {created} created, {existing} already present, {total} total"
            )
        )
