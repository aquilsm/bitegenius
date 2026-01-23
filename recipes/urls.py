from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet
from django.urls import path
from .views import PantryView, RecommendationView
from django.urls import path
from .views import *
from . import views

urlpatterns = [
    # HTML pages
    path("", home_page, name="home"),
    path("pantry/", pantry_page, name="pantry-page"),
    path("recommendations/", recommendations_page, name="recommendations-page"),
    path("recipe-clicked/<int:recipe_id>/",views.recipe_clicked,name="recipe-clicked"),
    path("add-recipe/",add_recipe,name="add-recipe"),
    path("recipe/<int:recipe_id>/", views.recipe_detail_page, name="recipe-detail"),
    path("edit-recipe/<int:recipe_id>/",views.edit_recipe,name="edit-recipe"),
    path("delete-recipe/<int:recipe_id>/",views.delete_recipe,name="delete-recipe"),
    path("favorite/<int:recipe_id>/",views.toggle_favorite,name="toggle-favorite"),
    path("favorites/",views.favorites_page,name="favorites-page"),
    path("weekly-plan/",views.weekly_plan_page,name="weekly-plan"),
    path("weekly-plan/add/<int:recipe_id>/<int:day>/",views.add_to_weekly_plan,name="add-to-weekly-plan"),
    path("weekly-plan/remove/<int:planned_id>/",views.remove_from_weekly_plan,name="remove-from-weekly-plan"),
    path("weekly-plan/select-day/<int:recipe_id>/",views.select_day_for_week,name="select-day-for-week"),
    path("weekly-plan/move/<int:planned_id>/",views.move_weekly_plan,name="move-weekly-plan"),
    path("weekly-plan/pick/",views.recipe_picker,name="recipe-picker"),
    

    # API endpoints
    path("api/pantry/", PantryView.as_view(), name="pantry"),
    path("api/recommendations/", RecommendationView.as_view(), name="recommendations"),
    path("api/ingredient-suggestions/",ingredient_suggestions,name="ingredient-suggestions"),
]

