from django.db import models
from django.conf import settings

class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    prep_time = models.IntegerField(help_text="Minutes")
    cook_time = models.IntegerField(help_text="Minutes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
