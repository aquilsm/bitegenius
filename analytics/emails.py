from django.core.mail import send_mail
from django.conf import settings
from analytics.models import AnalyticsEvent
from analytics.retention import users_who_planned_but_didnt_cook
from django.contrib.auth import get_user_model
from analytics.utils import track_event
from datetime import timedelta
from django.utils.timezone import now
from analytics.models import AnalyticsEvent
from analytics.utils import track_event

User = get_user_model()


def send_cook_reminder_emails():
    user_ids = users_who_planned_but_didnt_cook(days=1)

    users = User.objects.filter(
        id__in=user_ids,
        email__isnull=False
    ).exclude(email="")

    for user in users:
        # ❌ Prevent duplicate emails
        already_sent = AnalyticsEvent.objects.filter(
            user=user,
            event_type="cook_reminder_email_sent"
        ).exists()

        if already_sent:
            continue

        subject = "🍳 Your meal plan is waiting!"
        message = f"""
Hi {user.first_name or "there"},

You planned a recipe on BiteGenius but haven’t cooked it yet.

Open your plan and cook something delicious today 👇
http://127.0.0.1:8000/weekly-plan/

Happy cooking,
BiteGenius 🍽️
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        # 📊 Track email sent
        track_event(
            event_name="cook_reminder_email_sent",
            user=user,
            metadata={"type": "planned_but_not_cooked"}
        )

def send_weekly_summary_emails():
    one_week_ago = now() - timedelta(days=7)

    # Users who interacted this week
    user_ids = AnalyticsEvent.objects.filter(
        created_at__gte=one_week_ago,
        user__isnull=False
    ).values_list("user_id", flat=True).distinct()

    from django.contrib.auth import get_user_model
    User = get_user_model()

    users = User.objects.filter(id__in=user_ids).exclude(email="")

    for user in users:
        already_sent = AnalyticsEvent.objects.filter(
            user=user,
            event_type="weekly_summary_email_sent",
            created_at__gte=one_week_ago
        ).exists()

        if already_sent:
            continue

        planned_count = AnalyticsEvent.objects.filter(
            user=user,
            event_type="recipe_added_to_weekly_plan",
            created_at__gte=one_week_ago
        ).count()

        cooked_count = AnalyticsEvent.objects.filter(
            user=user,
            event_type="recipe_cooked",
            created_at__gte=one_week_ago
        ).count()

        subject = "📅 Your BiteGenius weekly summary"
        message = f"""
Hi {user.first_name or "there"},

Here’s your BiteGenius week 🍽️

📌 Recipes planned: {planned_count}
🔥 Recipes cooked: {cooked_count}

Open BiteGenius to plan your next meals 👇
http://127.0.0.1:8000/

See you next week,
BiteGenius
"""

        from django.core.mail import send_mail
        from django.conf import settings

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

        track_event(
            event_name="weekly_summary_email_sent",
            user=user,
            metadata={
                "planned": planned_count,
                "cooked": cooked_count
            }
        )

def send_reengagement_emails(days_inactive=7):
    cutoff = now() - timedelta(days=days_inactive)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    inactive_users = User.objects.exclude(
        id__in=AnalyticsEvent.objects.filter(
            created_at__gte=cutoff
        ).values_list("user_id", flat=True)
    ).exclude(email="")

    for user in inactive_users:
        already_sent = AnalyticsEvent.objects.filter(
            user=user,
            event_type="reengagement_email_sent"
        ).exists()

        if already_sent:
            continue

        subject = "👋 We saved some recipes for you"
        message = f"""
Hi {user.first_name or "there"},

It’s been a while since you last cooked with BiteGenius.

Jump back in and get fresh recipe ideas 👇
http://127.0.0.1:8000/

Happy cooking,
BiteGenius 🍳
"""

        from django.core.mail import send_mail
        from django.conf import settings

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )

        track_event(
            event_name="reengagement_email_sent",
            user=user,
            metadata={"inactive_days": days_inactive}
        )
