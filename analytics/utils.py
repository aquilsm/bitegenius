from .models import AnalyticsEvent
from django.utils.timezone import now, timedelta

def track_event(
    event_name,
    request=None,
    user=None,
    metadata=None
):
    if request:
        session_id = request.session.session_key
        if not session_id:
            request.session.save()
            session_id = request.session.session_key
    else:
        session_id = None

    AnalyticsEvent.objects.create(
        event_type=event_name,   # 🔑 matches model
        user=user if user and user.is_authenticated else None,
        session_id=session_id,
        metadata={
            **(metadata or {}),
            "schema_version": 1
        }
    )
    if session_id and is_duplicate_event(event_name, session_id):
        return


def is_duplicate_event(event_type, session_id, seconds=30):
    cutoff = now() - timedelta(seconds=seconds)
    return AnalyticsEvent.objects.filter(
        event_type=event_type,
        session_id=session_id,
        created_at__gte=cutoff
    ).exists()