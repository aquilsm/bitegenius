from django.core.management.base import BaseCommand
from analytics.retention import detect_cook_today_users

class Command(BaseCommand):
    help = "Detect users eligible for retention reminders"

    def handle(self, *args, **kwargs):
        detect_cook_today_users()
        self.stdout.write("Retention detection complete")
