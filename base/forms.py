from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
class RegistrationForm(UserCreationForm):
    name = forms.CharField(max_length=100, label="ФИО")
    group = forms.CharField(max_length=20, label="Группа")
    course = forms.IntegerField(min_value=1, max_value=6, label="Курс")
    email = forms.EmailField(required=True)
    class Meta:
        model = User
        fields = ("name", "email", "password1", "password2", "course", "username")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            # Создаем профиль с дополнительными полями
            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["name"],
                group=self.cleaned_data["group"],
                course=self.cleaned_data["course"]
            )
        return user
