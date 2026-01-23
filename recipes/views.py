from rest_framework.viewsets import ModelViewSet
from .serializers import RecipeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import (
    PantryInputSerializer,
    RecommendationSerializer
)
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import filter_staples
from .utils import STAPLE_INGREDIENTS
from django.http import HttpResponseRedirect
from datetime import date, timedelta
from collections import Counter
from datetime import date
from analytics.utils import track_event
from .pantry_utils import normalize_ingredient,fuzzy_match_ingredient
from users.decorators import login_required_or_redirect
from rest_framework.test import APIRequestFactory
import random
from django.contrib import messages
from django.urls import reverse
from datetime import date
from recipes.utils import login_gate

def home_page(request):
    """
    Public landing page.
    No login required.
    Shows pantry form + recipe of the day + browse recipes.
    """

    recipes = Recipe.objects.prefetch_related("ingredients").all()

    recipe_of_the_day = random.choice(recipes) if recipes else None

    categories = {
        "Quick & Easy": recipes.filter(prep_time_minutes__lte=15),
        "Dinner Ideas": recipes.filter(prep_time_minutes__gt=15),
    }

    return render(
        request,
        "recipes/home.html",
        {
            "recipe_of_the_day": recipe_of_the_day,
            "categories": categories,
            "ingredients": "",     # 🟢 needed for form re-render
            "error": None,         # 🟢 needed for form errors
            "user": request.user,
        }
    )

class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class PantryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PantryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key

        PantryItem.objects.filter(session_id=session_id).delete()

        ingredient_names = serializer.validated_data["ingredients"]

        known_ingredients = list(
            Ingredient.objects.values_list("name", flat=True)
        )

        matched_ingredients = []
        fuzzy_used_count = 0

        for name in ingredient_names:
            normalized = normalize_ingredient(name)
            matched = fuzzy_match_ingredient(
                normalized,
                known_ingredients
            )

            ingredient, _ = Ingredient.objects.get_or_create(name=matched)

            if normalized != matched:
                fuzzy_used_count += 1

            PantryItem.objects.get_or_create(
                session_id=session_id,
                ingredient=ingredient
            )

            matched_ingredients.append(matched)

        # ✅ Analytics
        track_event(
            event_name="pantry_submitted",
            request=request,
            metadata={
                "ingredient_count": len(matched_ingredients),
            }
        )

        track_event(
            event_name="pantry_fuzzy_matching",
            request=request,
            metadata={
                "fuzzy_matches": fuzzy_used_count,
                "total_ingredients": len(ingredient_names)
            }
        )

        # ✅ RETURN matched ingredients
        return Response(
            {"matched_ingredients": matched_ingredients},
            status=status.HTTP_201_CREATED
        )

class RecommendationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.session.session_key
        if not session_id:
            return Response([], status=status.HTTP_200_OK)

        # ----------------------------
        # Pantry ingredients
        # ----------------------------
        pantry_items = PantryItem.objects.filter(
            session_id=session_id
        ).select_related("ingredient")

        pantry_ingredients = {
            item.ingredient.name for item in pantry_items
        }

        # ----------------------------
        # Favorites (session-based)
        # ----------------------------
        favorites = request.session.get("favorites", [])

        recommendations = []

        for recipe in Recipe.objects.prefetch_related("ingredients"):

            recipe_ingredients = {
                ing.name
                for ing in recipe.ingredients.all()
                if ing.name not in STAPLE_INGREDIENTS
            }

            # 🔑 CRITICAL FIX
            if not recipe_ingredients:
                continue

            used = recipe_ingredients & pantry_ingredients
            if not used:
                continue

            missing = recipe_ingredients - pantry_ingredients

            score = len(used)

            if recipe.id in favorites:
                score += 2
                print(
                    f"USER_EVENT recommendation_boosted "
                    f"recipe_id={recipe.id}"
                )

            recommendations.append({
                "recipe_id": recipe.id,
                "name": recipe.name,
                "used_ingredients": list(used),
                "missing_ingredients": list(missing),
                "prep_time_minutes": recipe.prep_time_minutes,
                "is_user_submitted": recipe.is_user_submitted,
                "is_favorited": recipe.id in favorites,
                "score": score,
            })

        recommendations.sort(
            key=lambda x: (-x["score"], len(x["missing_ingredients"]))
        )

        top_results = recommendations[:3]

        serializer = RecommendationSerializer(top_results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

def pantry_page(request):
    if request.method == "POST":
        ingredients = request.POST.get("ingredients", "")

        ingredient_list = [
            i.strip().lower()
            for i in ingredients.split(",")
            if i.strip()
        ]

        if not ingredient_list:
            return render(
                request,
                "recipes/pantry.html",
                {
                    "error": "Please enter at least one ingredient.",
                    "ingredients": ingredients,
                }
            )

        factory = APIRequestFactory()
        api_request = factory.post(
            "/api/pantry/",
            {"ingredients": ingredient_list},
            format="json"
        )

        api_request.session = request.session
        api_request.user = request.user

        response = PantryView.as_view()(api_request)

        # ✅ CRITICAL FIX
        matched = response.data.get("matched_ingredients", [])
        request.session["pantry"] = matched
        request.session.modified = True

        return redirect("/recommendations/")

    return render(request, "recipes/pantry.html")

def recommendations_page(request):
    MAX_ANON_RECOMMENDATIONS = 3

    pantry = request.session.get("pantry", [])
    favorites = request.session.get("favorites", [])

    recommendations = []

    recipes = Recipe.objects.prefetch_related("ingredients")

    for recipe in recipes:
        recipe_ingredients = [
            ing.name
            for ing in recipe.ingredients.all()
            if ing.name not in STAPLE_INGREDIENTS
        ]

        if not recipe_ingredients:
            continue

        used_ingredients = [
            ing for ing in recipe_ingredients if ing in pantry
        ]

        if not used_ingredients:
            continue

        missing_ingredients = [
            ing for ing in recipe_ingredients if ing not in pantry
        ]

        score = len(used_ingredients)

        if recipe.id in favorites:
            score += 2

        recommendations.append({
            "recipe_id": recipe.id,
            "name": recipe.name,
            "used_ingredients": used_ingredients,
            "missing_ingredients": missing_ingredients,
            "prep_time_minutes": recipe.prep_time_minutes,
            "is_user_submitted": recipe.is_user_submitted,
            "is_favorited": recipe.id in favorites,
            "score": score,
        })

    recommendations.sort(
        key=lambda x: (-x["score"], len(x["missing_ingredients"]))
    )

    total_recommendations = len(recommendations)
    is_anonymous = not request.user.is_authenticated

    # 🔐 SOFT GATE
    if is_anonymous:
        recommendations = recommendations[:MAX_ANON_RECOMMENDATIONS]

        if total_recommendations > MAX_ANON_RECOMMENDATIONS:
            track_event(
                event_name="recommendation_login_gate_shown",
                request=request,
                metadata={
                    "total_available": total_recommendations,
                    "shown": MAX_ANON_RECOMMENDATIONS,
                }
            )

    # 📊 Analytics — page viewed
    track_event(
        event_name="recommendations_viewed",
        request=request,
        user=request.user,
        metadata={
            "shown": len(recommendations),
            "total_available": total_recommendations,
        }
    )

    # ----------------------------
    # Weekly plan helpers
    # ----------------------------
    planned_recipe_ids = set(
        PlannedRecipe.objects.filter(
            weekly_plan__session_id=request.session.session_key,
            weekly_plan__week_start=get_week_start(),
        ).values_list("recipe_id", flat=True)
    )

    today_plan = None
    today_index = date.today().weekday()

    if request.session.session_key:
        week_start = get_week_start()
        session_id = request.session.session_key

        weekly_plan = WeeklyPlan.objects.filter(
            user=request.user if request.user.is_authenticated else None,
            session_id=None if request.user.is_authenticated else session_id,
            week_start=week_start,
        ).first()

        if weekly_plan:
            today_plan = weekly_plan.planned_recipes.select_related(
                "recipe"
            ).filter(day_of_week=today_index).first()

    return render(
        request,
        "recipes/recommendations.html",
        {
            "recommendations": recommendations,
            "pantry": pantry,
            "planned_recipe_ids": planned_recipe_ids,
            "today_plan": today_plan,
            "show_login_cta": (
                is_anonymous and
                total_recommendations > MAX_ANON_RECOMMENDATIONS
            ),
            "hidden_count": max(
                0,
                total_recommendations - MAX_ANON_RECOMMENDATIONS
            ),
        }
    )

def recipe_clicked(request, recipe_id):
    favorites = request.session.get("favorites", [])

    if recipe_id not in favorites:
        favorites.append(recipe_id)
        request.session["favorites"] = favorites

    # ✅ Analytics — recipe clicked
    track_event(
        event_name="recipe_clicked",
        request=request,
        user=request.user,
        metadata={"recipe_id": recipe_id}
    )

    return redirect("/recommendations/")


def ingredient_suggestions(request):
    query = request.GET.get("q", "").strip().lower()

    if not query:
        return JsonResponse([], safe=False)

    ingredients = (
        Ingredient.objects
        .filter(name__icontains=query)
        .order_by("name")[:10]
    )

    results = [ingredient.name for ingredient in ingredients]

    return JsonResponse(results, safe=False)

def add_recipe(request):
    if request.method == "POST":
        name = request.POST.get("name")
        ingredients_raw = request.POST.get("ingredients")
        prep_time = request.POST.get("prep_time_minutes")
        steps = request.POST.get("steps", "").strip()

        recipe = Recipe.objects.create(
            name=name,
            prep_time_minutes=prep_time,
            is_user_submitted=True,
            steps=steps
        )

        ingredient_names = [
            i.strip().lower()
            for i in ingredients_raw.split(",")
            if i.strip()
        ]

        for ing_name in ingredient_names:
            ingredient, _ = Ingredient.objects.get_or_create(
                name=ing_name
            )
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient
            )

        print(
            f"USER_EVENT recipe_submitted "
            f"id={recipe.id} name={recipe.name}"
        )

        return redirect("/recommendations/")

    return render(request, "recipes/add_recipe.html")

def recipe_detail_page(request, recipe_id):
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related("ingredients"),
        id=recipe_id
    )

    pantry = request.session.get("pantry", [])

    recipe_ingredients = [
        ing.name for ing in recipe.ingredients.all()
        if ing.name not in STAPLE_INGREDIENTS
    ]

    used_ingredients = [
        ing for ing in recipe_ingredients if ing in pantry
    ]

    missing_ingredients = [
        ing for ing in recipe_ingredients if ing not in pantry
    ]

    # 🧠 WHY explanation
    if not missing_ingredients:
        why = (
            "You already have all the main ingredients, "
            "so you can cook this without buying anything extra."
        )
    elif len(missing_ingredients) == 1:
        why = (
            f"You have most of what you need — "
            f"you’re only missing {missing_ingredients[0]}."
        )
    elif recipe.prep_time_minutes <= 10:
        why = (
            "This is a quick recipe that fits well "
            "with the ingredients you already have."
        )
    elif len(used_ingredients) >= 2:
        why = (
            "This recipe uses several ingredients from your pantry, "
            "making it a good match."
        )
    else:
        why = (
            "This recipe shares at least one ingredient "
            "with what you have at home."
        )

    print(
        f"USER_EVENT recipe_viewed "
        f"id={recipe.id} name={recipe.name}"
    )

    steps = []

    if recipe.steps:
        steps = [
            step.strip()
            for step in recipe.steps.split("\n")
            if step.strip()
        ]

    return render(
        request,
        "recipes/recipe_detail.html",
        {
            "recipe": recipe,
            "used_ingredients": used_ingredients,
            "missing_ingredients": missing_ingredients,
            "why": why,
            "steps": steps,
        }
    )

def edit_recipe(request, recipe_id):
    recipe = get_object_or_404(
        Recipe,
        id=recipe_id,
        is_user_submitted=True
    )

    if request.method == "POST":
        recipe.name = request.POST.get("name")
        recipe.prep_time_minutes = request.POST.get("prep_time_minutes")
        recipe.steps = request.POST.get("steps", "").strip()
        recipe.save()

        ingredients_raw = request.POST.get("ingredients", "")

        ingredient_names = [
            i.strip().lower()
            for i in ingredients_raw.split(",")
            if i.strip()
        ]

        # Clear old ingredients
        recipe.recipe_ingredients.all().delete()

        for ing_name in ingredient_names:
            ingredient, _ = Ingredient.objects.get_or_create(
                name=ing_name
            )
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient
            )

        print(
            f"USER_EVENT recipe_edited "
            f"id={recipe.id} name={recipe.name}"
        )

        return redirect("recipe-detail", recipe_id=recipe.id)

    # Pre-fill ingredients
    existing_ingredients = ", ".join(
        ing.name for ing in recipe.ingredients.all()
    )

    return render(
        request,
        "recipes/edit_recipe.html",
        {
            "recipe": recipe,
            "ingredients": existing_ingredients,
        }
    )

def delete_recipe(request, recipe_id):
    recipe = get_object_or_404(
        Recipe,
        id=recipe_id,
        is_user_submitted=True
    )

    if request.method == "POST":
        recipe_name = recipe.name
        recipe.delete()

        print(
            f"USER_EVENT recipe_deleted "
            f"id={recipe_id} name={recipe_name}"
        )

        return redirect("/recommendations/")

    return render(
        request,
        "recipes/delete_recipe_confirm.html",
        {
            "recipe": recipe
        }
    )

@login_gate("toggle_favorite")
def toggle_favorite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)

    favorite, created = FavoriteRecipe.objects.get_or_create(
        user=request.user,
        recipe=recipe
    )

    if not created:
        favorite.delete()
        action = "removed"
    else:
        action = "added"

    # 📊 Analytics — success
    track_event(
        event_name="recipe_favorite_toggled",
        request=request,
        user=request.user,
        metadata={
            "recipe_id": recipe.id,
            "action": action
        }
    )

    return redirect(request.META.get("HTTP_REFERER", "/"))

@login_required_or_redirect
def favorites_page(request):
    favorite_ids = request.session.get("favorites", [])

    recipes = Recipe.objects.filter(id__in=favorite_ids)

    # ✅ Analytics — favorites viewed
    track_event(
        event_name="favorites_viewed",
        request=request,
        user=request.user,
        metadata={"count": recipes.count()}
    )

    return render(
        request,
        "recipes/favorites.html",
        {
            "recipes": recipes
        }
    )


def get_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())

@login_required_or_redirect
def weekly_plan_page(request):
    # ----------------------------
    # Session
    # ----------------------------
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key

    week_start = get_week_start()

    # ----------------------------
    # Weekly plan
    # ----------------------------
    if request.user.is_authenticated:
        weekly_plan, _ = WeeklyPlan.objects.get_or_create(
        user=request.user,
        week_start=week_start
    )
    else:
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key

        weekly_plan, _ = WeeklyPlan.objects.get_or_create(
            session_id=session_id,
            week_start=week_start
        )

    # Dictionary: day_of_week -> PlannedRecipe
    planned = {
        p.day_of_week: p
        for p in weekly_plan.planned_recipes.select_related("recipe")
    }

    # ----------------------------
    # Pantry (DB-backed, single source of truth)
    # ----------------------------
    pantry_ingredients = set(
        PantryItem.objects.filter(
            session_id=session_id
        ).values_list("ingredient__name", flat=True)
    )

    # ----------------------------
    # Grocery preview
    # ----------------------------
    grocery_items = Counter()

    planned_recipes = (
        weekly_plan.planned_recipes
        .select_related("recipe")
        .prefetch_related("recipe__ingredients")
    )

    for planned_recipe in planned_recipes:
        for ing in planned_recipe.recipe.ingredients.all():
            if ing.name in STAPLE_INGREDIENTS:
                continue
            if ing.name not in pantry_ingredients:
                grocery_items[ing.name] += 1

    grocery_list = grocery_items.items()

    # ----------------------------
    # Days
    # ----------------------------
    days = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    today_index = date.today().weekday()

    track_event(
    event_name="weekly_plan_viewed",
    request=request,
    user=request.user
    )
    
    track_event(
    event_name="weekly_plan_created",
    request=request,
    user=request.user,
    metadata={"week_start": str(week_start)}
    )

    return render(
        request,
        "recipes/weekly_plan.html",
        {
            "week_start": week_start,
            "days": days,
            "planned": planned,
            "grocery_list": grocery_list,
            "today_index" : today_index,
        }
    )

@login_gate("add_to_weekly_plan")
def add_to_weekly_plan(request, recipe_id, day):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    week_start = get_week_start()

    if request.user.is_authenticated:
        # ✅ Logged-in user: user-based plan, NO session_id
        weekly_plan, created = WeeklyPlan.objects.get_or_create(
            user=request.user,
            session_id=None,
            week_start=week_start,
        )
    else:
        # 🔐 Anonymous user: session-based plan
        if not request.session.session_key:
            request.session.create()

        weekly_plan, created = WeeklyPlan.objects.get_or_create(
            user=None,
            session_id=request.session.session_key,
            week_start=week_start,
        )

    planned_recipe, replaced = PlannedRecipe.objects.update_or_create(
        weekly_plan=weekly_plan,
        day_of_week=day,
        defaults={"recipe": recipe}
    )

    # 📊 Analytics
    track_event(
        event_name="recipe_added_to_weekly_plan",
        request=request,
        user=request.user if request.user.is_authenticated else None,
        metadata={
            "recipe_id": recipe.id,
            "day": day,
            "week_start": str(week_start),
            "replaced_existing": not replaced
        }
    )

    return redirect("weekly-plan")

def remove_from_weekly_plan(request, planned_id):
    planned = get_object_or_404(PlannedRecipe, id=planned_id)
    planned.delete()

    # ✅ Analytics — recipe removed from weekly plan
    track_event(
        event_name="recipe_removed_from_plan",
        request=request,
        user=request.user,
        metadata={"planned_id": planned_id}
    )

    return redirect("weekly-plan")


def select_day_for_week(request, recipe_id):
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key

    recipe = get_object_or_404(Recipe, id=recipe_id)

    week_start = get_week_start()

    weekly_plan, _ = WeeklyPlan.objects.get_or_create(
        session_id=session_id,
        week_start=week_start
    )

    planned_recipes = weekly_plan.planned_recipes.select_related("recipe")

    planned_days = {
        p.day_of_week: p for p in planned_recipes
    }

    days = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    today_index = date.today().weekday()
    suggested_day = None

    # 1️⃣ Prefer today if empty
    if today_index not in planned_days:
        suggested_day = today_index

    # 2️⃣ Otherwise first empty day
    if suggested_day is None:
        for day, _ in days:
            if day not in planned_days:
                suggested_day = day
                break

    # 3️⃣ Otherwise shortest recipe day
    if suggested_day is None:
        shortest = None
        for p in planned_recipes:
            if shortest is None or p.recipe.prep_time_minutes < shortest.recipe.prep_time_minutes:
                shortest = p
        if shortest:
            suggested_day = shortest.day_of_week

    print(
        f"USER_EVENT weekly_day_suggested "
        f"recipe_id={recipe.id} day={suggested_day}"
    )

    return render(
        request,
        "recipes/select_day.html",
        {
            "recipe": recipe,
            "days": days,
            "suggested_day": suggested_day,
        }
    )

def move_weekly_plan(request, planned_id):
    planned = get_object_or_404(PlannedRecipe, id=planned_id)

    if request.method == "POST":
        new_day = int(request.POST.get("new_day"))
        planned.day_of_week = new_day
        planned.save()

        print(
            f"USER_EVENT weekly_plan_moved "
            f"id={planned_id} new_day={new_day}"
        )

    return redirect("weekly-plan")

def recipe_picker(request):
    """
    Shows ALL recipes.
    Used by Weekly Planner → Add One
    """

    day = request.GET.get("day")

    recipes = (
        Recipe.objects
        .prefetch_related("ingredients")
        .all()
        .order_by("name")
    )

    # Favorite mapping (only if logged in)
    favorite_ids = set()

    if request.user.is_authenticated:
        favorite_ids = set(
            FavoriteRecipe.objects.filter(
                user=request.user
            ).values_list("recipe_id", flat=True)
        )

    recipe_data = []
    for recipe in recipes:
        recipe_data.append({
            "id": recipe.id,
            "name": recipe.name,
            "prep_time": recipe.prep_time_minutes,
            "is_favorited": recipe.id in favorite_ids
        })

    # 📊 Analytics
    track_event(
        event_name="recipe_picker_viewed",
        request=request,
        user=request.user,
        metadata={
            "day": day,
            "recipe_count": len(recipe_data)
        }
    )

    return render(
        request,
        "recipes/recipe_picker.html",
        {
            "recipes": recipe_data,
            "day": day,
            "login_required": not request.user.is_authenticated
        }
    )

