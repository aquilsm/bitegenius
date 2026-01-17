from rest_framework import serializers
from .models import Recipe
from .models import Ingredient, PantryItem, RecipeIngredient

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name"]

class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = ["id", "name", "prep_time_minutes", "ingredients"]

class PantryInputSerializer(serializers.Serializer):
    ingredients = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

class RecommendationSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField()
    name = serializers.CharField()
    used_ingredients = serializers.ListField(
        child=serializers.CharField()
    )
    missing_ingredients = serializers.ListField(
        child=serializers.CharField()
    )
    prep_time_minutes = serializers.IntegerField(allow_null=True)

