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


class UserUpdateForm(forms.ModelForm):
    """Форма редактирования профиля пользователя"""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class PasswordChangeForm(forms.Form):
    """Форма смены пароля"""
    old_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )
    new_password2 = forms.CharField(
        label="Подтвердите новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")
        return password2