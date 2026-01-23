from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render
from django.utils.timezone import now

from analytics.models import AnalyticsEvent


@staff_member_required
def analytics_dashboard(request):
    today = now().date()

    from_date = request.GET.get("from") or (today - timedelta(days=7))
    to_date = request.GET.get("to") or today

    events = AnalyticsEvent.objects.filter(
        created_at__date__range=[from_date, to_date]
    )

    total_events = events.count()
    authenticated_events = events.filter(user__isnull=False).count()
    anonymous_events = events.filter(user__isnull=True).count()

    # 📈 Events per day
    daily = (
        events.extra(select={"day": "DATE(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    day_labels = [str(d["day"]) for d in daily]
    day_counts = [d["count"] for d in daily]

    # 🔥 Top events
    top_events = (
        events.values("event_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # 🧪 Funnel
    funnel_steps = [
        ("view_recipe", "Viewed recipe"),
        ("add_to_weekly_plan", "Added to weekly plan"),
        ("cook_recipe", "Cooked recipe"),
    ]

    funnel_counts = []
    previous_count = None

    for idx, (step, label) in enumerate(funnel_steps):
        count = events.filter(event_type=step).values("session_id").distinct().count()

        if previous_count:
            conversion = round((count / previous_count) * 100, 1)
            dropoff = round(100 - conversion, 1)
        else:
            conversion = 100
            dropoff = 0

        funnel_counts.append({
            "step": step,
            "label": label,
            "count": count,
            "conversion": conversion,
            "dropoff": dropoff,
            "next_step": funnel_steps[idx + 1][0] if idx + 1 < len(funnel_steps) else None,
        })

        previous_count = count

    return render(request, "analytics/analytics_dashboard.html", {
        "from_date": from_date,
        "to_date": to_date,
        "total_events": total_events,
        "authenticated_events": authenticated_events,
        "anonymous_events": anonymous_events,
        "day_labels": day_labels,
        "day_counts": day_counts,
        "top_events": top_events,
        "funnel_counts": funnel_counts,
    })
