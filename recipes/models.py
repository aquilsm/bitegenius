from django.db import models
from django.conf import settings
from django.db.models import Q

class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class Recipe(models.Model):
    name = models.CharField(max_length=200, blank=True)
    prep_time_minutes = models.IntegerField()
    is_user_submitted = models.BooleanField(default=False)
    steps = models.TextField(
        help_text="One step per line",
        blank=True
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes"
    )

    def __str__(self):
        return self.name or "Unnamed recipe"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes"
    )

    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"

class PantryItem(models.Model):
    session_id = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.session_id} - {self.ingredient.name}"


class WeeklyPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    session_id = models.CharField(
        max_length=100,
        null=True,        # ✅ REQUIRED
        blank=True
    )
    week_start = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "week_start"],
                condition=Q(user__isnull=False),
                name="unique_weekly_plan_per_user"
            ),
            models.UniqueConstraint(
                fields=["session_id", "week_start"],
                condition=Q(session_id__isnull=False),
                name="unique_weekly_plan_per_session"
            ),
        ]

    def __str__(self):
        return f"WeeklyPlan {self.week_start}"


class PlannedRecipe(models.Model):
    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="planned_recipes"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )
    day_of_week = models.IntegerField(
        choices=[
            (0, "Monday"),
            (1, "Tuesday"),
            (2, "Wednesday"),
            (3, "Thursday"),
            (4, "Friday"),
            (5, "Saturday"),
            (6, "Sunday"),
        ]
    )

    def __str__(self):
        return f"{self.recipe.name} on {self.get_day_of_week_display()}"

def get_user_or_session_pantry(request):
    if request.user.is_authenticated:
        return PantryItem.objects.filter(user=request.user)
    return PantryItem.objects.filter(
        session_id=request.session.session_key
    )

class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("user", "recipe")
