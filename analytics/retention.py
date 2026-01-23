from datetime import date
from recipes.models import WeeklyPlan, PlannedRecipe
from analytics.utils import track_event
from django.utils.timezone import now
from datetime import timedelta
from analytics.models import AnalyticsEvent
from django.contrib.auth import get_user_model

User = get_user_model()

def detect_cook_today_users():
    today = date.today()
    today_index = today.weekday()

    plans = PlannedRecipe.objects.select_related(
        "weekly_plan", "recipe"
    ).filter(
        day_of_week=today_index,
        weekly_plan__user__isnull=False
    )

    for planned in plans:
        track_event(
            event_name="cook_today_reminder_eligible",
            user=planned.weekly_plan.user,
            metadata={
                "recipe": planned.recipe.name,
                "date": str(today)
            }
        )

def detect_inactive_users(days=5):
    cutoff = now() - timedelta(days=days)

    active_users = AnalyticsEvent.objects.filter(
        created_at__gte=cutoff,
        user__isnull=False
    ).values_list("user_id", flat=True)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    inactive_users = User.objects.exclude(id__in=active_users)

    for user in inactive_users:
        track_event(
            event_name="inactive_user_detected",
            user=user,
            metadata={"inactive_days": days}
        )

def users_who_planned_but_didnt_cook(days=1):
    cutoff = now() - timedelta(days=days)

    planned = AnalyticsEvent.objects.filter(
        event_type="recipe_added_to_weekly_plan",
        created_at__gte=cutoff,
        user__isnull=False
    ).values_list("user_id", flat=True)

    cooked = AnalyticsEvent.objects.filter(
        event_type="recipe_cooked",
        created_at__gte=cutoff,
        user__isnull=False
    ).values_list("user_id", flat=True)

    return set(planned) - set(cooked)

def mark_users_for_cook_reminder():
    user_ids = users_who_planned_but_didnt_cook(days=1)

    for user in User.objects.filter(id__in=user_ids):
        already_marked = AnalyticsEvent.objects.filter(
            user=user,
            event_type="cook_reminder_marked"
        ).exists()

        if not already_marked:
            track_event(
                event_name="cook_reminder_marked",
                user=user,
                metadata={"reason": "planned_but_not_cooked"}
            )