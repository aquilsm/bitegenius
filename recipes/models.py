from django.db import models
from django.conf import settings
from django.conf import settings

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
    session_id = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.session_id} - {self.ingredient.name}"


class WeeklyPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=100, blank=True)
    week_start = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session_id", "week_start")

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
