from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
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
        ('teacher', 'Тест от учителя'),
    ]

    GRADE_CHOICES = [
        (5, '5'),
        (4, '4'),
        (3, '3'),
        (2, '2'),
        (0, 'Незачет'),
    ]

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
    teacher_test = models.ForeignKey(
        'TeacherTest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results',
        verbose_name='Тест учителя'
    )

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('result_detail', args=[str(self.id)])
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



class LabWork(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкая'),
        ('medium', 'Средняя'),
        ('hard', 'Сложная'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    pptx_file = models.FileField(upload_to='media/pptx_files/', blank=True, null=True)
    theme = models.CharField(max_length=100, verbose_name="Тема")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_labs')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    docx_file = models.FileField(upload_to=lab_file_path, verbose_name="Файл.docx")

    def get_file_name(self):
        """Получить имя файла без пути"""
        return os.path.basename(self.file.name)
    def __str__(self):
        return self.title
class LabSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Сдано'),
        ('under_review', 'На проверке'),
        ('graded', 'Проверено'),
        ('rejected', 'Отклонено'),
    ]
    checked = models.BooleanField(default=False)
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


class TestCategory(models.Model):
    """Категории тестов (Графы, Логика, Множества и т.д.)"""
    name = models.CharField(max_length=100, verbose_name="Название")
    code = models.CharField(max_length=50, unique=True, verbose_name="Код")  # graphs, logic, plenty, final
    description = models.TextField(blank=True, verbose_name="Описание")
    order = models.IntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return self.name


class TestQuestion(models.Model):
    """Вопрос теста"""
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField(verbose_name="Текст вопроса")
    is_imported = models.BooleanField(default=False, verbose_name="Импортирован из БД")
    option_a = models.TextField(verbose_name="Вариант A")
    option_b = models.TextField(verbose_name="Вариант B")
    option_c = models.TextField(verbose_name="Вариант C")
    option_d = models.TextField(verbose_name="Вариант D")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_questions')
    correct_option = models.CharField(
        max_length=1,
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        verbose_name="Правильный вариант"
    )
    difficulty = models.CharField(
        max_length=10,
        choices=[('easy', 'Легкий'), ('medium', 'Средний'), ('hard', 'Сложный')],
        default='medium',
        verbose_name="Сложность"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ['category', 'id']

    def __str__(self):
        return f"{self.category.name}: {self.question_text[:50]}..."


class TestKindConfig(models.Model):
    """Конфигурация типов тестов (хранится в БД)"""
    TEST_KIND_CHOICES = [
        ('start', 'Входное тестирование'),
        ('final', 'Итоговое тестирование'),
    ]

    code = models.CharField(
        max_length=10,
        choices=TEST_KIND_CHOICES,
        unique=True,
        verbose_name="Код типа теста"
    )
    title = models.CharField(max_length=200, verbose_name="Название теста")
    template = models.CharField(max_length=100, verbose_name="Шаблон теста")
    result_template = models.CharField(max_length=100, verbose_name="Шаблон результатов")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    order = models.IntegerField(default=0, verbose_name="Порядок")

    # Связь с категориями тестов
    categories = models.ManyToManyField(
        TestCategory,
        through='TestKindCategory',
        related_name='test_kinds',
        verbose_name="Категории теста"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Конфигурация теста"
        verbose_name_plural = "Конфигурации тестов"
        ordering = ['order', 'code']

    def __str__(self):
        return f"{self.title} ({self.code})"


class TestKindCategory(models.Model):
    """Связь между типом теста и категориями с указанием количества вопросов"""
    test_kind = models.ForeignKey(TestKindConfig, on_delete=models.CASCADE)
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE)
    questions_count = models.IntegerField(
        default=5,
        verbose_name="Количество вопросов",
        help_text="0 - все вопросы категории"
    )
    order = models.IntegerField(default=0, verbose_name="Порядок")

    class Meta:
        unique_together = ['test_kind', 'category']
        ordering = ['order']

    def __str__(self):
        return f"{self.test_kind.code} → {self.category.name} ({self.questions_count} вопросов)"


class TeacherTest(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    title = models.CharField(max_length=200, verbose_name="Название теста")
    description = models.TextField(blank=True, verbose_name="Описание")
    questions = models.ManyToManyField(TestQuestion, through='TeacherTestQuestion', related_name='teacher_tests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    # Изменяем: если assigned_to пусто, тест доступен ВСЕМ ученикам учителя
    assigned_to = models.ManyToManyField(
        User,
        related_name='assigned_tests',
        blank=True,
        limit_choices_to={'profile__role': 'student'},
        verbose_name="Конкретные ученики (оставьте пустым для всех)"
    )

    # Новое поле: назначать автоматически новым ученикам
    auto_assign_new_students = models.BooleanField(
        default=True,
        verbose_name="Автоматически назначать новым ученикам"
    )
class TeacherTestQuestion(models.Model):
    test = models.ForeignKey(TeacherTest, on_delete=models.CASCADE)
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['test', 'question']


# Добавьте в models.py после существующих моделей

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_lab', 'Новая лабораторная работа'),
        ('new_test', 'Новый тест'),
        ('lab_submitted', 'Сдана лабораторная работа'),
        ('test_completed', 'Пройден тест'),
        ('lab_graded', 'Проверена лабораторная работа'),
        ('test_graded', 'Проверен тест'),
        ('lab_comment', 'Добавлен комментарий к лабораторной'),
        ('new_student', 'Новый ученик'),
        ('new_message', 'Новое сообщение'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} для {self.recipient.username}"


# Добавьте эту модель в конец файла models.py

class Message(models.Model):
    """Модель для сообщений между студентами"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(verbose_name="Текст сообщения")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message #{self.id}"


# Замените существующий сигнал на этот:
# Добавьте в models.py после класса Message

class TeacherStudentMessage(models.Model):
    """Модель для сообщений между учителем и студентом"""
    MESSAGE_TYPES = [
        ('text', 'Текст'),
        ('voice', 'Голосовое сообщение'),
        ('file', 'Файл'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_teacher_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_teacher_messages')
    content = models.TextField(verbose_name="Текст сообщения", blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    file_attachment = models.FileField(upload_to='chat_files/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    voice_message = models.FileField(upload_to='voice_messages/', blank=True, null=True)
    voice_duration = models.IntegerField(default=0, help_text="Длительность в секундах")
    reactions = models.JSONField(default=dict, blank=True)  # {user_id: '👍'}
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Сообщение #{self.id} от {self.sender.username} к {self.recipient.username}"
@receiver(post_save, sender=UserProfile)
def assign_tests_to_new_student(sender, instance, created, **kwargs):
    """При создании нового ученика: уведомление учителю + назначение тестов + уведомление одногруппникам"""
    if created and instance.role == 'student' and instance.teacher:
        from .utils import notify_teacher_about_new_student, notify_groupmates_about_new_student, \
            notify_student_about_new_test

        # ===== 1. УВЕДОМЛЕНИЕ УЧИТЕЛЮ =====
        notify_teacher_about_new_student(instance.teacher, instance.user)

        # ===== 2. УВЕДОМЛЕНИЕ ОДНОГРУППНИКАМ =====
        notify_groupmates_about_new_student(instance.user)

        # ===== 3. НАЗНАЧЕНИЕ ТЕСТОВ =====
        tests = TeacherTest.objects.filter(
            teacher=instance.teacher,
            is_active=True
        ).filter(
            Q(assigned_to__isnull=True) | Q(auto_assign_new_students=True)
        ).distinct()

        for test in tests:
            test.assigned_to.add(instance.user)
            notify_student_about_new_test(instance.teacher, instance.user, test)