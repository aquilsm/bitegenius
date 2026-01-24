from django import forms
from .models import User
from django_countries.widgets import CountrySelectWidget

class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "avatar",
            "gender",
            "date_of_birth",
            "city",
            "country",
            "phone_number",
            "show_email",
            "show_phone",
        ]

        widgets = {
            "country": CountrySelectWidget(attrs={"class": "country-select"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            phone = phone.replace(" ", "")
            if not phone.replace('+', '').isdigit():
                raise forms.ValidationError("Enter a valid phone number")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip()
        return email
