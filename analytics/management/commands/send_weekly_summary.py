from django.core.management.base import BaseCommand
from analytics.emails import send_weekly_summary_emails


class Command(BaseCommand):
    help = "Send weekly summary emails"

    def handle(self, *args, **options):
        self.stdout.write("📅 Sending weekly summary emails...")
        send_weekly_summary_emails()
        self.stdout.write(self.style.SUCCESS("✅ Weekly summaries sent"))
