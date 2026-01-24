from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
# urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import account_page,account_delete, signup_page
from .views import CustomLoginView  # If you have a custom login view
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Authentication
    path("login/", CustomLoginView.as_view(), name="login"),
    path("signup/", signup_page, name="signup_page"),
    
    # Account page
    path("account/", account_page, name="account"),

    # urls.py (add this line)
    path("account/delete/", account_delete, name="account_delete"),


    # Password change
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="users/password_change.html",
            success_url="/accounts/password-change/done/"
        ),
        name="password_change"
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="users/password_change_done.html"
        ),
        name="password_change_done"
    ),

    # Logout
    path("logout/", LogoutView.as_view(next_page="/login/"), name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )