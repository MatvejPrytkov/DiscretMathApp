from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, TestResult


class RegistrationForm(UserCreationForm):
    name = forms.CharField(max_length=100, label="ФИО")
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[('student', 'Ученик'), ('teacher', 'Учитель')],
        label="Роль",
        widget=forms.RadioSelect
    )
    group = forms.CharField(max_length=20, label="Группа", required=False)
    course = forms.IntegerField(min_value=1, max_value=6, label="Курс", required=False)

    # Добавляем поле выбора преподавателя
    teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='teacher'),
        required=False,
        label="Преподаватель",
        empty_label="-- Выберите преподавателя --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ("name", "email", "password1", "password2", "username", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Обновляем queryset для поля teacher
        self.fields['teacher'].queryset = User.objects.filter(profile__role='teacher')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        group = cleaned_data.get("group")
        course = cleaned_data.get("course")
        teacher = cleaned_data.get("teacher")

        if role == 'student':
            if not group:
                self.add_error('group', 'Для ученика необходимо указать группу')
            if not course:
                self.add_error('course', 'Для ученика необходимо указать курс')
            # Проверяем, что ученик выбрал преподавателя
            if not teacher:
                self.add_error('teacher', 'Для ученика необходимо выбрать преподавателя')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["name"],
                role=self.cleaned_data["role"],
                group=self.cleaned_data.get("group"),
                course=self.cleaned_data.get("course"),
                teacher=self.cleaned_data.get("teacher")  # Сохраняем преподавателя
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
class MyLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Переопределяем стандартную ошибку
        self.error_messages['invalid_login'] = (
            "Пожалуйста, введите правильные имя пользователя и пароль. "
            "Оба поля могут быть чувствительны к регистру."
        )


class GradeTestForm(forms.ModelForm):
    """Форма для выставления оценки за тест"""

    class Meta:
        model = TestResult
        fields = ['grade', 'teacher_comment']
        widgets = {
            'grade': forms.Select(attrs={'class': 'form-control'}),
            'teacher_comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Комментарий учителя...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Настраиваем поле grade
        self.fields['grade'].required = True
        self.fields['grade'].label = 'Оценка'
        self.fields['teacher_comment'].required = False