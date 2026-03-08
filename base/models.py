from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import migrations, models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, verbose_name="ФИО")
    group = models.CharField(max_length=20, verbose_name="Группа")
    course = models.PositiveSmallIntegerField(verbose_name="Курс")

    def __str__(self):
        return f"{self.full_name} ({self.group})"


class TestResult(models.Model):
    TEST_TYPES = [
        ('start', 'Входное тестирование'),
        ('final', 'Итоговое тестирование'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=10, choices=TEST_TYPES)
    score = models.IntegerField()  # количество правильных ответов
    total_questions = models.IntegerField()
    percent = models.FloatField()
    date_completed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_test_type_display()} ({self.score}/{self.total_questions})"

