from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Recipe
from .serializers import RecipeSerializer
from rest_framework.permissions import IsAuthenticated

class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# Create your views here.
