from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField
from PIL import Image

class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    gender = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
    )

    date_of_birth = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)

    # ✅ ISO-2 country code (IN, US, GB, etc.)
    country = CountryField(blank=True, null=True)

    phone_number = models.CharField(max_length=20, blank=True)

    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=False)

    def profile_completion_percent(self):
        fields = [
            self.first_name,
            self.last_name,
            self.avatar,
            self.gender,
            self.date_of_birth,
            self.city,
            self.country,
            self.phone_number,
        ]
        filled = sum(bool(f) for f in fields)
        return int((filled / len(fields)) * 100)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.avatar:
            return

        try:
            img = Image.open(self.avatar.path)
        except Exception:
            return

        size = min(img.width, img.height)
        left = (img.width - size) / 2
        top = (img.height - size) / 2
        right = (img.width + size) / 2
        bottom = (img.height + size) / 2

        img = img.crop((left, top, right, bottom))
        img = img.resize((256, 256), Image.LANCZOS)
        img.save(self.avatar.path, quality=90, optimize=True)
