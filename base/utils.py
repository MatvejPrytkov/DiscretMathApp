# utils.py
from .models import Notification

def create_notification(recipient, sender, notification_type, title, message, link=''):
    """Создает уведомление для пользователя"""
    if recipient and recipient != sender:  # Не отправляем уведомление самому себе
        Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )

def notify_teacher_about_submission(teacher, student, lab_work, submission_id):
    """Уведомление учителя о сдаче лабораторной работы"""
    create_notification(
        recipient=teacher,
        sender=student,
        notification_type='lab_submitted',
        title='📝 Новая сдача лабораторной работы',
        message=f'Студент {student.profile.full_name} сдал лабораторную работу "{lab_work.title}".',
        link=f'/teacher/lab/submission/{submission_id}/'  # Теперь подставляется реальный ID
    )

def notify_teacher_about_test_completion(teacher, student, test_result):
    """Уведомление учителя о прохождении теста"""
    test_name = test_result.get_test_type_display()
    create_notification(
        recipient=teacher,
        sender=student,
        notification_type='test_completed',
        title='📊 Пройден новый тест',
        message=f'Студент {student.profile.full_name} прошел тест "{test_name}". Результат: {test_result.score}/{test_result.total_questions} ({test_result.percent}%).',
        link=f'/result/{test_result.id}/'
    )

def notify_student_about_new_lab(teacher, student, lab_work):
    """Уведомление студента о новой лабораторной работе"""
    create_notification(
        recipient=student,
        sender=teacher,
        notification_type='new_lab',
        title='🧪 Новая лабораторная работа',
        message=f'Преподаватель добавил новую лабораторную работу "{lab_work.title}".',
        link=f'/lab/{lab_work.id}/'
    )

def notify_student_about_new_test(teacher, student, teacher_test):
    """Уведомление студента о новом тесте"""
    create_notification(
        recipient=student,
        sender=teacher,
        notification_type='new_test',
        title='📝 Новый тест',
        message=f'Преподаватель добавил новый тест "{teacher_test.title}".',
        link=f'/student/teacher-test/{teacher_test.id}/'
    )

def notify_student_about_lab_grade(teacher, student, submission):
    """Уведомление студента о проверке лабораторной работы"""
    create_notification(
        recipient=student,
        sender=teacher,
        notification_type='lab_graded',
        title='✅ Лабораторная работа проверена',
        message=f'Преподаватель проверил вашу работу "{submission.lab_work.title}". Оценка: {submission.grade or "не указана"}.',
        link=f'/lab/{submission.lab_work.id}/'
    )

def notify_student_about_test_grade(teacher, student, test_result):
    """Уведомление студента о проверке теста"""
    test_name = test_result.get_test_type_display()
    create_notification(
        recipient=student,
        sender=teacher,
        notification_type='test_graded',
        title='📊 Тест проверен',
        message=f'Преподаватель проверил ваш тест "{test_name}". Оценка: {test_result.get_grade_display()}.',
        link=f'/result/{test_result.id}/'
    )

def notify_students_about_new_lab(teacher, students, lab_work):
    """Уведомление всех студентов о новой лабораторной работе"""
    for student in students:
        if student != teacher:
            notify_student_about_new_lab(teacher, student, lab_work)

def notify_students_about_new_test(teacher, students, teacher_test):
    """Уведомление всех студентов о новом тесте"""
    for student in students:
        if student != teacher:
            notify_student_about_new_test(teacher, student, teacher_test)

def notify_teacher_about_any_test_completion(teacher, student, test_result, test_name):
    """Уведомление учителя о прохождении любого теста"""
    create_notification(
        recipient=teacher,
        sender=student,
        notification_type='test_completed',
        title=f'📊 Пройден тест: {test_name}',
        message=f'Студент {student.profile.full_name} прошел {test_name}. Результат: {test_result.score}/{test_result.total_questions} ({test_result.percent}%).',
        link=f'/result/{test_result.id}/'
    )