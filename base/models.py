from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import migrations, models
from django.contrib.auth.models import User
import uuid
import os
def lab_file_path(instance, filename):
    # Сохраняем с английским именем
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('lab_works', filename)

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Ученик'),
        ('teacher', 'Учитель'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, verbose_name="ФИО")
    group = models.CharField(max_length=20, verbose_name="Группа", blank=True, null=True)
    course = models.PositiveSmallIntegerField(verbose_name="Курс", blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student', verbose_name="Роль")

    # Добавляем связь ученик-учитель
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="Преподаватель",
        limit_choices_to={'profile__role': 'teacher'}  # только учителя
    )

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class TestResult(models.Model):
    TEST_TYPES = [
        ('start', 'Входное тестирование'),
        ('final', 'Итоговое тестирование'),
    ]

    GRADE_CHOICES = [
        (5, '5'),
        (4, '4'),
        (3, '3'),
        (2, '2'),
        (0, 'Незачет'),
    ]
    grade = models.IntegerField(choices=GRADE_CHOICES, blank=True, null=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=10, choices=TEST_TYPES)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percent = models.FloatField()
    date_completed = models.DateTimeField(auto_now_add=True)
    correct_answers = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    category_results = models.JSONField(default=dict, blank=True)

    # Поля для оценки
    grade = models.IntegerField(
        choices=GRADE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Оценка'
    )
    teacher_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий учителя'
    )
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_results',
        verbose_name='Оценку выставил'
    )
    graded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата оценки'
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_test_type_display()} ({self.score}/{self.total_questions})"

class TestAnswer(models.Model):
    result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='answers')
    question_id = models.IntegerField()
    question_text = models.TextField()

    user_answer = models.CharField(max_length=1, blank=True, null=True)  # a/b/c/d
    correct_answer = models.CharField(max_length=1)  # a/b/c/d

    user_answer_text = models.TextField(blank=True, null=True)
    correct_answer_text = models.TextField(blank=True, null=True)

    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Result#{self.result_id} Q{self.question_id} ({'OK' if self.is_correct else 'NO'})"


# 🆕 НОВАЯ МОДЕЛЬ ЛАБОРАТОРНЫХ РАБОТ
class LabWork(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкая'),
        ('medium', 'Средняя'),
        ('hard', 'Сложная'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    docx_file = models.FileField(upload_to='lab_works/', verbose_name="Файл .docx")
    theme = models.CharField(max_length=100, verbose_name="Тема")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_labs')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    docx_file = models.FileField(upload_to=lab_file_path, verbose_name="Файл.docx")
    def __str__(self):
        return self.title
class LabSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Сдано'),
        ('under_review', 'На проверке'),
        ('graded', 'Проверено'),
        ('rejected', 'Отклонено'),
    ]

    lab_work = models.ForeignKey(LabWork, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lab_submissions')
    submitted_file = models.FileField(upload_to='lab_submissions/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    grade = models.CharField(max_length=10, blank=True, null=True)  # 2,3,4,5 или "н"
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='graded_labs')

    def __str__(self):
        return f"{self.student.profile.full_name} - {self.lab_work.title}"