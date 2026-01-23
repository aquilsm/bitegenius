from django.contrib.auth.views import LoginView
from recipes.models import PantryItem
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from recipes.models import WeeklyPlan
from django.contrib.auth.decorators import login_required
from recipes.models import PlannedRecipe
from recipes.models import Recipe
from datetime import date
from recipes.models import WeeklyPlan, PlannedRecipe, FavoriteRecipe
from recipes.views import get_week_start
from analytics.utils import track_event

User = get_user_model()

class CustomLoginView(LoginView):
    template_name = "auth/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        session_id = self.request.session.session_key
        user = self.request.user

        if session_id:
            PantryItem.objects.filter(
                session_id=session_id,
                user__isnull=True
            ).update(user=user)

            WeeklyPlan.objects.filter(
                session_id=session_id,
                user__isnull=True
            ).update(user=user)

        # Merge favorites
        favorites = self.request.session.get("favorites", [])
        for recipe_id in favorites:
            FavoriteRecipe.objects.get_or_create(
                user=user,
                recipe_id=recipe_id
            )
        self.request.session.pop("favorites", None)

        # ✅ Analytics — successful login
        track_event(
            event_name="user_logged_in",
            request=self.request,
            user=user
        )

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

            # ✅ Analytics — successful login
            track_event(
                event_name="user_logged_in",
                request=request,
                user=user
            )

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

            # ✅ Analytics — signup success
            track_event(
                event_name="user_signed_up",
                request=request,
                user=user,
                metadata={"source": "email"}
            )

            return redirect("recommendations-page")

    return render(
        request,
        "auth/signup.html",
        {"error": error}
    )


def signup(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email or not password:
            return render(
                request,
                "users/signup.html",
                {"error": "Email and password are required"}
            )

        if User.objects.filter(email=email).exists():
            return render(
                request,
                "users/signup.html",
                {"error": "User already exists"}
            )

        user = User.objects.create_user(
            username=email,   # ✅ REQUIRED
            email=email,
            password=password
        )

        login(request, user)
        return redirect("/")

    return render(request, "users/signup.html")


@login_required
def account_page(request):
    user = request.user

    favorites = request.session.get("favorites", [])
    favorites_count = len(favorites)

    session_id = request.session.session_key
    week_start = get_week_start()

    weekly_plan = WeeklyPlan.objects.filter(
        session_id=session_id,
        week_start=week_start
    ).first()

    planned_count = 0
    today_recipe = None

    if weekly_plan:
        planned_recipes = weekly_plan.planned_recipes.select_related("recipe")
        planned_count = planned_recipes.count()

        today_index = date.today().weekday()
        today_plan = planned_recipes.filter(day_of_week=today_index).first()
        if today_plan:
            today_recipe = today_plan.recipe

    return render(
        request,
        "users/account.html",
        {
            "user": user,
            "favorites_count": favorites_count,
            "planned_count": planned_count,
            "today_recipe": today_recipe,
        }
    )
