from django.core.management.base import BaseCommand
from analytics.emails import send_reengagement_emails


class Command(BaseCommand):
    help = "Send re-engagement emails to inactive users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Days of inactivity before sending email"
        )

    def handle(self, *args, **options):
        days = options["days"]
        self.stdout.write(f"📭 Sending re-engagement emails ({days} days inactive)...")
        send_reengagement_emails(days_inactive=days)
        self.stdout.write(self.style.SUCCESS("✅ Re-engagement emails sent"))
