from django.core.management.base import BaseCommand
from analytics.emails import send_cook_reminder_emails


class Command(BaseCommand):
    help = "Send cook reminder emails to users who planned but didn’t cook"

    def handle(self, *args, **options):
        self.stdout.write("⏳ Sending cook reminder emails...")
        send_cook_reminder_emails()
        self.stdout.write(self.style.SUCCESS("✅ Cook reminders sent"))
