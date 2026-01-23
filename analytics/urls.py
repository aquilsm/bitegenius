from django.urls import path
from .admin_views import (
    analytics_dashboard,
    analytics_export_csv,
    funnel_drilldown,
    session_timeline,
)

app_name = "analytics"

urlpatterns = [
    path("dashboard/", analytics_dashboard, name="dashboard"),
    path("export/", analytics_export_csv, name="export_csv"),
    path("funnel-drilldown/", funnel_drilldown, name="funnel_drilldown"),
    path(
        "session/<str:session_id>/",
        session_timeline,
        name="session_timeline",
    ),
]
