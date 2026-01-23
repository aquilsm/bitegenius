from .models import Recipe, RecipeIngredient
from functools import wraps
from analytics.utils import track_event
from django.shortcuts import redirect
from django.urls import reverse

STAPLE_INGREDIENTS = {
    "salt",
    "oil",
    "water",
    "pepper",
    "sugar",
    "butter",
}

def get_recommendations(pantry_ingredients, limit=3):
    """
    Given a list of pantry ingredient names,
    return up to `limit` recipe recommendations.
    """

    pantry_set = set(pantry_ingredients)
    results = []

    recipes = Recipe.objects.prefetch_related("recipe_ingredients__ingredient")

    for recipe in recipes:
        recipe_ingredients = recipe.recipe_ingredients.all()
        ingredient_names = [ri.ingredient.name for ri in recipe_ingredients]

        used = [name for name in ingredient_names if name in pantry_set]
        missing = [name for name in ingredient_names if name not in pantry_set]

        if not used:
            continue  # no overlap, skip

        results.append({
            "recipe_id": recipe.id,
            "name": recipe.name,
            "used_ingredients": used,
            "missing_ingredients": missing,
            "prep_time_minutes": recipe.prep_time_minutes,
            "score": len(used),  # simple scoring
        })

    # Sort by best match (most used ingredients first)
    results.sort(key=lambda r: r["score"], reverse=True)

    # Remove internal score before returning
    for r in results:
        r.pop("score", None)

    return results[:limit]

def filter_staples(ingredients):
    """
    Remove common staple ingredients from matching logic.
    """
    return [
        i for i in ingredients
        if i not in STAPLE_INGREDIENTS
    ]

def login_gate(event_name):
    """
    Decorator to require login and track analytics
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                track_event(
                    event_name=f"{event_name}_login_required",
                    request=request,
                    metadata={
                        "path": request.path
                    }
                )
                return redirect(
                    f"{reverse('login')}?next={request.path}"
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator