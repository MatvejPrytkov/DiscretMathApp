from django.contrib.auth.models import User

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

def notify_teacher_about_submission(teacher, student, lab_work, submission_id, request=None):
    """Уведомление учителя о сдаче лабораторной работы (с проверкой нахождения на странице)"""
    return create_notification_smart(
        recipient=teacher,
        sender=student,
        notification_type='lab_submitted',
        title='📝 Новая сдача лабораторной работы',
        message=f'Студент {student.profile.full_name} сдал лабораторную работу "{lab_work.title}".',
        link=f'/teacher/lab/submission/{submission_id}/',
        request=request,
        current_object_type='submission',
        current_object_id=submission_id
    )


def notify_teacher_about_test_completion(teacher, student, test_result, request=None):
    """Уведомление учителя о прохождении теста (с проверкой)"""
    test_name = test_result.get_test_type_display()

    # Определяем тип объекта для проверки
    obj_type = 'teacher_result' if test_result.test_type == 'teacher' else 'result'

    return create_notification_smart(
        recipient=teacher,
        sender=student,
        notification_type='test_completed',
        title='📊 Пройден новый тест',
        message=f'Студент {student.profile.full_name} прошел тест "{test_name}". Результат: {test_result.score}/{test_result.total_questions} ({test_result.percent}%).',
        link=f'/teacher/result/{test_result.id}/' if test_result.test_type == 'teacher' else f'/teacher/result/{test_result.id}/',
        request=request,
        current_object_type=obj_type,
        current_object_id=test_result.id
    )

def notify_student_about_new_lab(teacher, student, lab_work):
    """Уведомление студента о новой лабораторной работе"""
    create_notification(
        recipient=student,
        sender=teacher,
        notification_type='new_lab',
        title='🧪 Новая лабораторная работа',
        message=f'Преподаватель добавил новую лабораторную работу "{lab_work.title}".',
        link=f'/students/labs/lab/{lab_work.id}/'
    )

def notify_student_about_new_test(teacher, student, teacher_test, request=None):
    """Уведомление студента о новом тесте (с проверкой)"""
    return create_notification_smart(
        recipient=student,
        sender=teacher,
        notification_type='new_test',
        title=f'📝 Новый тест: {teacher_test.title}',
        message=f'Преподаватель добавил новый тест "{teacher_test.title}".\n\n'
                f'Количество вопросов: {teacher_test.questions.count()}',
        link=f'/student/teacher-tests/{teacher_test.id}/',
        request=request,
        current_object_type='test',
        current_object_id=teacher_test.id
    )

def notify_student_about_lab_grade(teacher, student, submission, request=None):
    """Уведомление студента о проверке лабораторной работы (с проверкой)"""
    return create_notification_smart(
        recipient=student,
        sender=teacher,
        notification_type='lab_graded',
        title='✅ Лабораторная работа проверена',
        message=f'Преподаватель проверил вашу работу "{submission.lab_work.title}". Оценка: {submission.grade or "не указана"}.',
        link=f'/student/labs/lab/{submission.lab_work.id}/',
        request=request,
        current_object_type='lab',
        current_object_id=submission.lab_work.id
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
        link=f'/student/result/{test_result.id}/'  # ✅ ИСПРАВЛЕНО - ведет на страницу результата студента
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
        link=f'/teacher/result/{test_result.id}/'
    )

def notify_teacher_about_new_student(teacher, student):
    """Уведомление учителя о новом ученике"""
    create_notification(
        recipient=teacher,
        sender=student,
        notification_type='new_student',
        title='🎓 Новый ученик',
        message=f'К вам прикрепился новый ученик: {student.profile.full_name or student.username}.\n'
                f'Группа: {student.profile.group or "—"}\n'
                f'Курс: {student.profile.course or "—"}',
        link=f'/teacher/students/student/{student.id}/'
    )
# Добавьте эти функции в конец файла utils.py

def notify_student_about_new_groupmate(student, new_groupmate):
    """Уведомление студента о новом одногруппнике"""
    create_notification(
        recipient=student,
        sender=new_groupmate,
        notification_type='new_student',
        title='👥 Новый одногруппник',
        message=f'В вашей группе появился новый студент: {new_groupmate.profile.full_name or new_groupmate.username}.\n'
                f'Группа: {new_groupmate.profile.group}\n'
                f'Курс: {new_groupmate.profile.course}',
        link=f'/student/chat/{new_groupmate.id}/'
    )

def notify_about_new_message(recipient, sender, message_content):
    """Уведомление о новом сообщении"""
    create_notification(
        recipient=recipient,
        sender=sender,
        notification_type='new_message',
        title='💬 Новое сообщение',
        message=f'{sender.profile.full_name or sender.username}: {message_content[:100]}',
        link=f'/student/chat/{sender.id}/'
    )


# Обновите функцию notify_teacher_about_new_student и добавьте уведомление одногруппникам:

def notify_groupmates_about_new_student(student):
    """Уведомление одногруппников о новом студенте"""
    # Находим всех одногруппников (такая же группа и курс, но не включая самого студента)
    groupmates = User.objects.filter(
        profile__role='student',
        profile__group=student.profile.group,
        profile__course=student.profile.course,
        profile__teacher=student.profile.teacher
    ).exclude(id=student.id)

    for groupmate in groupmates:
        create_notification(
            recipient=groupmate,
            sender=student,
            notification_type='new_student',
            title='👥 Новый одногруппник',
            message=f'В вашей группе появился новый студент: {student.profile.full_name or student.username}.\n'
                    f'Группа: {student.profile.group}\n'
                    f'Курс: {student.profile.course}',
            link=f'/student/chat/{student.id}/'
        )


# Добавьте в конец utils.py

def notify_about_teacher_message(recipient, sender, content):
    """Уведомление о новом сообщении от учителя/студента"""
    if hasattr(sender, 'profile') and sender.profile.role == 'teacher':
        # Учитель пишет ученику
        title = '👩‍🏫 Новое сообщение от учителя'
        link = f'/student/chat/teacher/detail/{sender.id}/'
    else:
        # Ученик пишет учителю
        title = '👨‍🎓 Новое сообщение от ученика'
        link = f'/teacher/chat/student/detail/{sender.id}/'

    create_notification(
        recipient=recipient,
        sender=sender,
        notification_type='new_message',
        title=title,
        message=f'{sender.profile.full_name or sender.username}: {content[:100]}',
        link=link
    )


def notify_about_teacher_message_with_file(recipient, sender, file_name, message_type='file'):
    """Уведомление о новом сообщении с файлом от учителя/студента"""
    if hasattr(sender, 'profile') and sender.profile.role == 'teacher':
        title = '📎 Новый файл от учителя'
        link = f'/student/chat/teacher/detail/{sender.id}/'
    else:
        title = '📎 Новый файл от ученика'
        link = f'/teacher/chat/student/detail/{sender.id}/'

    create_notification(
        recipient=recipient,
        sender=sender,
        notification_type='new_message',
        title=title,
        message=f'{sender.profile.full_name or sender.username} отправил файл: {file_name}',
        link=link
    )


# utils.py

def is_user_on_page(request, object_type, object_id):
    """
    Проверяет, находится ли пользователь на странице указанного объекта.

    object_type: 'lab', 'test', 'submission', 'result'
    object_id: ID объекта
    """
    if not request:
        return False

    # Получаем текущий URL
    current_path = request.path
    referer = request.META.get('HTTP_REFERER', '')

    # Словарь путей для разных типов объектов
    path_patterns = {
        'lab': f'/student/labs/lab/{object_id}/',
        'submission': f'/teacher/lab/submission/{object_id}/',
        'test': f'/student/teacher-tests/{object_id}/',
        'result': f'/student/result/{object_id}/',
        'teacher_result': f'/teacher/result/{object_id}/',
    }

    # Проверяем текущий путь и referer
    pattern = path_patterns.get(object_type)
    if not pattern:
        return False

    return pattern in current_path or pattern in referer


def create_notification_smart(recipient, sender, notification_type, title, message, link='', request=None,
                              current_object_type=None, current_object_id=None):
    """
    Умное создание уведомления — не отправляет, если пользователь уже на этой странице.
    """
    # Проверяем, нужно ли пропустить уведомление
    if request and current_object_type and current_object_id:
        if is_user_on_page(request, current_object_type, current_object_id):
            # Пользователь уже на странице — не отправляем уведомление
            return None

    # Стандартное создание уведомления
    if recipient and recipient != sender:
        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
    return None