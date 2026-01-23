from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("signup/", signup, name="signup"),
    path("account/", account_page, name="account"),
    path("password-change/",auth_views.PasswordChangeView.as_view(template_name="users/password_change.html",success_url="/accounts/password-change/done/"),
    name="password_change"
    ),
    path("password-change/done/",auth_views.PasswordChangeDoneView.as_view(template_name="users/password_change_done.html"),
    name="password_change_done"
    ),
]