from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from notes.models import Deattribution


class Command(BaseCommand):
    help = "Delete deattribution data older than the specified number of days."

    def add_arguments(self, parser):
        parser.add_argument("num_days", type=int)

    def handle(self, *args, **options):
        if (num_days := options["num_days"]) < 1:
            raise CommandError("num_days should be positive.")
        deleted = Deattribution.objects.filter(
            created__lte=timezone.now() - timezone.timedelta(days=num_days)
        ).delete()
        deleted = deleted[0]
        self.stdout.write(
            "%s record(s) older than %s day(s) deleted." % (deleted, num_days)
        )
