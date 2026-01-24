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
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from datetime import date, timedelta  # Add timedelta
from django.utils import timezone
from datetime import date, timedelta
from .forms import UserChangeForm
from django.contrib.auth.hashers import check_password
from django import forms
#from .forms import CustomLoginForm

User = get_user_model()

# Add this helper function (or import the correct one)
def get_week_start(today=None):
    if today is None:
        today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday

class CustomLoginView(LoginView):
    template_name = "auth/login.html"
    
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "This account is disabled.",
                code="inactive",
            )
    #authentication_form = CustomLoginForm

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Oops! That username or password didn’t match.”"
        )
        return super().form_invalid(form)
    
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



@login_required
def account_page(request):
    user = request.user
    edit_mode = request.GET.get("edit") == "1"

    if request.method == "POST":
        form = UserChangeForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect("account")
    else:
        form = UserChangeForm(instance=user)

    favorites = request.session.get("favorites", [])
    favorites_count = len(favorites)

    session_id = request.session.session_key
    week_start = get_week_start()
    weekly_plan = WeeklyPlan.objects.filter(session_id=session_id, week_start=week_start).first()

    planned_count = 0
    today_recipe = None
    if weekly_plan:
        planned_recipes = weekly_plan.planned_recipes.select_related("recipe")
        planned_count = planned_recipes.count()
        today_index = date.today().weekday()
        today_plan = planned_recipes.filter(day_of_week=today_index).first()
        if today_plan:
            today_recipe = today_plan.recipe

    context = {
        "user": user,
        "form": form,
        "edit_mode": edit_mode,
        "favorites_count": favorites_count,
        "planned_count": planned_count,
        "today_recipe": today_recipe,
    }
    return render(request, "users/account.html", context)


def signup_view(request):
    if request.method == "POST":
        # Get form data
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        
        # Validation
        errors = []
        
        # Check required fields
        if not username or not email or not password1 or not password2:
            errors.append("All fields are required")
        
        # Check password match
        if password1 and password2 and password1 != password2:
            errors.append("Passwords do not match")
        
        # Check password strength (optional)
        if password1 and len(password1) < 8:
            errors.append("Password must be at least 8 characters")
        
        # Check if username exists
        if username and User.objects.filter(username=username).exists():
            errors.append("Username already exists")
        
        # Check if email exists
        if email and User.objects.filter(email=email).exists():
            errors.append("Email already registered")
        
        # If there are errors, show them
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "auth/signup.html", {
                "username_value": username,
                "email_value": email
            })
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            
            # Log the user in
            login(request, user)
            
            # Analytics — signup success
            track_event(
                event_name="user_signed_up",
                request=request,
                user=user,
                metadata={"source": "email"}
            )
            
            # Success message
            messages.success(request, "Welcome to BiteGenius! Your account has been created.")
            
            return redirect("recommendations-page")
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, "auth/signup.html", {
                "username_value": username,
                "email_value": email
            })
    
    # GET request - show signup form
    return render(request, "auth/signup.html")

@login_required
def account_delete(request):
    if request.method != "POST":
        return redirect("account")

    password = request.POST.get("password")

    if not password:
        messages.error(request, "Password is required.")
        return redirect("account")

    if not check_password(password, request.user.password):
        messages.error(request, "Incorrect password. Account not deleted.")
        return redirect("account")

    # 🔐 IMPORTANT ORDER
    user = request.user
    logout(request)          # ← kill session first
    user.delete()            # ← then delete user

    messages.success(request, "Your account has been permanently deleted.")
    return redirect("login")  # or homepage

