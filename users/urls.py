from django.urls import path
from .views import CustomLoginView
from .views import signup

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("signup/", signup, name="signup"),
]