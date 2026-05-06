from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, TestResult, LabWork, TestQuestion, TeacherTest, LabSubmission, TeacherPersonalQuestion


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

    teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='teacher'),
        required=False,
        label="Преподаватель",
        empty_label="-- Выберите преподавателя --",
        widget=forms.Select(attrs={'class': 'form-control'}),
        # ДОБАВЬТЕ ЭТО — разрешаем пустое значение
        to_field_name='id',
    )

    class Meta:
        model = User
        fields = ("name", "email", "password1", "password2", "username", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(profile__role='teacher')
        self.fields['teacher'].required = False
        # Добавьте эти атрибуты для скрытого поля
        self.fields['teacher'].widget = forms.HiddenInput()

    def clean_teacher(self):
        teacher = self.cleaned_data.get('teacher')
        if not teacher or teacher == '':
            return None
        return teacher

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
            if not teacher:
                self.add_error('teacher', 'Для ученика необходимо выбрать преподавателя')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["username"]

        if commit:
            user.save()

            teacher_value = self.cleaned_data.get("teacher")
            # teacher_value уже прошёл через clean_teacher, но на всякий случай
            if isinstance(teacher_value, User):
                teacher_obj = teacher_value
            else:
                teacher_obj = None

            UserProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["name"],
                role=self.cleaned_data["role"],
                group=self.cleaned_data.get("group"),
                course=self.cleaned_data.get("course"),
                teacher=teacher_obj
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


# Добавьте после существующих форм

class ProfileEditForm(forms.ModelForm):
    """Форма для редактирования профиля ученика (группа, курс, преподаватель)"""

    group = forms.CharField(max_length=20, label="Группа", required=False)
    course = forms.IntegerField(min_value=1, max_value=6, label="Курс", required=False)
    teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='teacher'),
        required=False,
        label="Преподаватель",
        empty_label="-- Выберите преподавателя --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)

        # Если есть профиль, заполняем поля
        if self.user_profile:
            self.fields['group'].initial = self.user_profile.group
            self.fields['course'].initial = self.user_profile.course
            self.fields['teacher'].initial = self.user_profile.teacher if self.user_profile.teacher else None

        # Настройка queryset для преподавателей
        self.fields['teacher'].queryset = User.objects.filter(profile__role='teacher')

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.user_profile:
            # Обновляем профиль
            self.user_profile.group = self.cleaned_data.get('group')
            self.user_profile.course = self.cleaned_data.get('course')
            self.user_profile.teacher = self.cleaned_data.get('teacher')
            self.user_profile.save()
        return user
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
class LabWorkForm(forms.ModelForm):
    class Meta:
        model = LabWork
        fields = ['title', 'description', 'pptx_file']  # Включите pptx_file
        widgets = {
            'pptx_file': forms.FileInput(attrs={'accept': '.pptx'}),
        }

class AddQuestionForm(forms.ModelForm):
    class Meta:
        model = TestQuestion
        fields = ['category', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'difficulty']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
            'option_a': forms.Textarea(attrs={'rows': 2}),
            'option_b': forms.Textarea(attrs={'rows': 2}),
            'option_c': forms.Textarea(attrs={'rows': 2}),
            'option_d': forms.Textarea(attrs={'rows': 2}),
        }

class CreateTeacherTestForm(forms.ModelForm):
    questions = forms.ModelMultipleChoiceField(
        queryset=TestQuestion.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    assigned_to = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Назначить ученикам"
    )

    class Meta:
        model = TeacherTest
        fields = ['title', 'description', 'questions', 'assigned_to']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # ИЗМЕНЕНИЕ: показываем все вопросы вместо фильтрации по created_by
            self.fields['questions'].queryset = TestQuestion.objects.all()

            # Ограничиваем учеников только привязанными к этому учителю
            self.fields['assigned_to'].queryset = User.objects.filter(
                profile__role='student',
                profile__teacher=user
            )
            # Показываем полное имя ученика в чекбоксах
            self.fields['assigned_to'].label_from_instance = (
                lambda obj: obj.profile.full_name
                if hasattr(obj, 'profile') and obj.profile.full_name
                else obj.username
            )

class TestQuestionForm(forms.ModelForm):
    class Meta:
        model = TestQuestion
        fields = ['question_text','option_a', 'option_b', 'option_c', 'option_d', 'correct_option']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control question-text', 'rows': 2, 'placeholder': 'Текст вопроса'}),
            'option_a': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант ответа 1'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант ответа 2'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант ответа 3'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант ответа 4'}),
            'correct_option': forms.Select(attrs={'class': 'form-control'}, choices=[
                (1, 'Вариант 1'), (2, 'Вариант 2'), (3, 'Вариант 3'), (4, 'Вариант 4')
            ]),
        }

class TeacherTestForm(forms.ModelForm):
    class Meta:
        model = TeacherTest
        fields = ['title', 'description']  # Убрали 'course' и 'group'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название теста'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание теста'}),
        }

    # Поле для выбора существующих вопросов остается
    existing_questions = forms.ModelMultipleChoiceField(
        queryset=TestQuestion.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Выбрать вопросы из базы данных"
    )


class GradeLabForm(forms.ModelForm):
    class Meta:
        model = LabSubmission
        fields = ['grade', 'comment', 'checked']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'grade': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'checked': forms.HiddenInput(),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.checked = True  # При сохранении оценки автоматически отмечаем как проверенное
        if commit:
            instance.save()
        return instance


# forms.py - добавьте новую форму

class TeacherPersonalQuestionForm(forms.ModelForm):
    """Форма для создания личного вопроса учителя"""

    class Meta:
        model = TeacherPersonalQuestion
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'category']
        widgets = {
            'question_text': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Введите текст вопроса'}),
            'option_a': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант А'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант Б'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант В'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Вариант Г'}),
            'correct_option': forms.Select(attrs={'class': 'form-control'},
                                           choices=[('a', 'А'), ('b', 'Б'), ('c', 'В'), ('d', 'Г')]),
            'category': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Например: Алгебра, Геометрия, Программирование...'}),
        }


class TeacherTestWithPersonalForm(forms.ModelForm):
    """Обновленная форма создания теста с личными вопросами"""
    existing_questions = forms.ModelMultipleChoiceField(
        queryset=TestQuestion.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Выбрать вопросы из общей базы"
    )
    personal_questions = forms.ModelMultipleChoiceField(
        queryset=TeacherPersonalQuestion.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Мои личные вопросы"
    )

    class Meta:
        model = TeacherTest
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название теста'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание теста'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['personal_questions'].queryset = TeacherPersonalQuestion.objects.filter(teacher=user)