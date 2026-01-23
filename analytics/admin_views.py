from django.shortcuts import render
from django.utils.timezone import now
from datetime import timedelta, datetime
from django.db.models import Count
from .models import AnalyticsEvent
import csv
from django.http import HttpResponse
from django.db.models.functions import TruncDate
from django.contrib.admin.views.decorators import staff_member_required

def analytics_dashboard(request):
    # ----------------------------
    # Date range (safe parsing)
    # ----------------------------
    from_str = request.GET.get("from")
    to_str = request.GET.get("to")

    try:
        from_date = datetime.strptime(from_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        from_date = (now() - timedelta(days=7)).date()

    try:
        to_date = datetime.strptime(to_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        to_date = now().date()

    events = AnalyticsEvent.objects.filter(
        created_at__date__gte=from_date,
        created_at__date__lte=to_date,
    )

    # ----------------------------
    # Overview metrics
    # ----------------------------
    total_events = events.count()
    authenticated_events = events.filter(user__isnull=False).count()
    anonymous_events = events.filter(user__isnull=True).count()

    events_by_day = (
    events
    .annotate(day=TruncDate("created_at"))
    .values("day")
    .annotate(count=Count("id"))
    .order_by("day")
    )

    day_labels = [e["day"].strftime("%b %d") for e in events_by_day]
    day_counts = [e["count"] for e in events_by_day]

    # ----------------------------
    # Top events (safe aggregation)
    # ----------------------------
    top_events = (
        events
        .values("event_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    top_event_labels = [e["event_type"] for e in top_events]
    top_event_counts = [e["count"] for e in top_events]

    # ----------------------------
    # Funnel (session-based)
    # ----------------------------
    FUNNEL_STEPS = [
        "recommendations_viewed",
        "recipe_clicked",
        "added_to_weekly_plan",
    ]

    funnel_counts = []
    previous_count = None

    for i, step in enumerate(FUNNEL_STEPS):
        step_sessions = (
            events
            .filter(event_type=step)
            .values_list("session_id", flat=True)
            .distinct()
            .count()
        )

        if previous_count:
            conversion = round((step_sessions / previous_count) * 100, 1)
            dropoff = round(100 - conversion, 1)
        else:
            conversion = 100.0
            dropoff = 0.0

        next_step = FUNNEL_STEPS[i + 1] if i + 1 < len(FUNNEL_STEPS) else None

        funnel_counts.append({
            "step": step,                       # raw value (URL-safe)
            "label": step.replace("_", " ").title(),
            "count": step_sessions,
            "conversion": conversion,
            "dropoff": dropoff,
            "next_step": next_step,             # 👈 explicit
        })

        previous_count = step_sessions

    return render(
        request,
        "admin/analytics_dashboard.html",
        {
            "from_date": from_date,
            "to_date": to_date,
            "total_events": total_events,
            "authenticated_events": authenticated_events,
            "anonymous_events": anonymous_events,
            "events_by_day": events_by_day,
            "day_labels": day_labels,
            "day_counts": day_counts,
            "top_event_labels": top_event_labels,
            "top_event_counts": top_event_counts,
            "funnel_counts": funnel_counts,
        }
    )

def analytics_export_csv(request):
    from_str = request.GET.get("from")
    to_str = request.GET.get("to")

    try:
        from_date = (
            datetime.strptime(from_str, "%Y-%m-%d")
            if from_str else now() - timedelta(days=7)
        )
    except ValueError:
        from_date = now() - timedelta(days=7)

    try:
        to_date = (
            datetime.strptime(to_str, "%Y-%m-%d")
            if to_str else now()
        )
    except ValueError:
        to_date = now()

    events = AnalyticsEvent.objects.filter(
        created_at__date__gte=from_date.date(),
        created_at__date__lte=to_date.date(),
    ).select_related("user")

    filename = (
        f"bitegenius_analytics_"
        f"{from_date.date()}_to_{to_date.date()}.csv"
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Event Type",
        "User",
        "Authenticated",
        "Session ID",
        "Created At",
        "Metadata",
    ])

    for event in events:
        writer.writerow([
            event.event_type,
            event.user.username if event.user else "",
            "Yes" if event.user else "No",
            event.session_id,
            event.created_at.isoformat(),
            event.metadata,
        ])

    return response

@staff_member_required
def funnel_drilldown(request):
    step = request.GET.get("step")
    next_step = request.GET.get("next")

    if not step or not next_step:
        return render(request, "admin/funnel_drilldown.html", {
            "error": "Invalid funnel steps"
        })

    # Sessions that reached current step
    step_sessions = set(
        AnalyticsEvent.objects
        .filter(event_type=step)
        .values_list("session_id", flat=True)
    )

    # Sessions that reached next step
    next_sessions = set(
        AnalyticsEvent.objects
        .filter(event_type=next_step)
        .values_list("session_id", flat=True)
    )

    # Drop-off sessions
    dropped_sessions = step_sessions - next_sessions

    events = (
        AnalyticsEvent.objects
        .filter(session_id__in=dropped_sessions)
        .order_by("-created_at")
    )

    return render(request, "admin/funnel_drilldown.html", {
        "step": step,
        "next_step": next_step,
        "events": events,
        "count": len(dropped_sessions),
    })

@staff_member_required
def session_timeline(request, session_id):
    events = (
        AnalyticsEvent.objects
        .filter(session_id=session_id)
        .select_related("user")
        .order_by("created_at")
    )

    return render(request, "admin/session_timeline.html", {
        "session_id": session_id,
        "events": events,
    })