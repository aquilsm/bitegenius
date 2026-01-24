"""
URL configuration for bitegenius project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# def home(request):
#      return JsonResponse({"message": "Welcome to BiteGenius API"})


def healthz(request):
    return HttpResponse("ok")

urlpatterns = [
    # path('', home),
    path("healthz/", healthz),

    path('api/', include('recipes.urls')),

    path("", include("recipes.urls")),  # keep your app routes
    
    # ✅ Auth (CUSTOM)
    path("accounts/", include("users.urls")),

    # ✅ Logout only (safe to keep built-in)
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # ✅ CUSTOM ADMIN EXTENSIONS — MUST COME FIRST
    path("admin/analytics/", include(("analytics.urls", "analytics"), namespace="analytics")),
    
    path('admin/', admin.site.urls),

]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )