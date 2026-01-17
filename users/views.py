from django.contrib.auth.views import LoginView
from recipes.models import PantryItem
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from recipes.models import WeeklyPlan

class CustomLoginView(LoginView):
    template_name = "auth/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        session_id = self.request.session.session_key
        if session_id:
            WeeklyPlan.objects.filter(
                session_id=session_id,
                user__isnull=True
            ).update(user=self.request.user)

        return response

def login_page(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:
            login(request, user)
            return redirect("recommendations-page")
        else:
            error = "Invalid username or password"

    return render(
        request,
        "auth/login.html",
        {"error": error}
    )

def signup_page(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            error = "Username already exists"
        else:
            user = User.objects.create_user(
                username=username,
                password=password
            )
            login(request, user)
            return redirect("recommendations-page")

    return render(
        request,
        "auth/signup.html",
        {"error": error}
    )

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("recommendations-page")
    else:
        form = UserCreationForm()

    return render(request, "auth/signup.html", {"form": form})