from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from .models import AnalyticsEvent

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("event_type", "user__email")


class AnalyticsDashboardAdmin(admin.AdminSite):
    site_header = "📊 BiteGenius Analytics"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "dashboard/",
                self.admin_view(self.dashboard),
                name="analytics-dashboard",
            ),
        ]
        return custom_urls + urls

    def dashboard(self, request):
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)

        events = AnalyticsEvent.objects.filter(
            created_at__date__gte=last_7_days
        )

        def count(event):
            return events.filter(event_type=event).count()

        context = {
            "total_events": events.count(),
            "recipes_planned": count("recipe_added_to_weekly_plan"),
            "recipes_cooked": count("recipe_cooked"),
            "favorites": count("toggle_favorite"),
            "recommendations_viewed": count("recommendations_viewed"),
            "daily_active_users": (
                events.exclude(user=None)
                .values("user")
                .distinct()
                .count()
            ),
        }

        return render(
            request,
            "admin/analytics_dashboard.html",
            context,
        )
