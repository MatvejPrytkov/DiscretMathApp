from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .decorators import student_required, teacher_required
from .models import User, TeacherStudentMessage, Message
from .utils import create_notification, notify_about_teacher_message
import json
from datetime import datetime, timezone  # импортируем timezone из модуля datetime


@login_required
@student_required
def student_teacher_chat_list(request):
    """Страница со списком чатов студента с учителем"""
    user = request.user

    # Находим учителя студента
    teacher = user.profile.teacher

    if not teacher:
        return render(request, 'student/teacher_chat_list.html', {
            'error': 'У вас не назначен преподаватель. Обратитесь к администратору.',
            'has_teacher': False
        })

    # Получаем все сообщения с учителем
    chat_messages = TeacherStudentMessage.objects.filter(
        sender__in=[user, teacher],
        recipient__in=[user, teacher]
    ).order_by('created_at')

    # Считаем непрочитанные сообщения от учителя
    unread_count = TeacherStudentMessage.objects.filter(
        sender=teacher,
        recipient=user,
        is_read=False
    ).count()

    return render(request, 'student/teacher_chat_list.html', {
        'teacher': teacher,
        'chat_messages': chat_messages,
        'unread_count': unread_count,
        'has_teacher': True,
        'teacher_name': teacher.profile.full_name if teacher.profile else teacher.username
    })



@login_required
@teacher_required
def teacher_student_chat_list(request):
    """Страница со списком чатов учителя со всеми учениками"""
    teacher = request.user

    students = User.objects.filter(
        profile__role='student',
        profile__teacher=teacher
    ).select_related('profile')

    students_data = []
    for student in students:
        last_message = TeacherStudentMessage.objects.filter(
            sender__in=[teacher, student],
            recipient__in=[teacher, student]
        ).order_by('-created_at').first()

        unread_count = TeacherStudentMessage.objects.filter(
            sender=student,
            recipient=teacher,
            is_read=False
        ).count()

        students_data.append({
            'student': student,
            'name': student.profile.full_name or student.username,
            'group': student.profile.group or '—',
            'course': student.profile.course or '—',
            'last_message': last_message,
            'last_message_time': last_message.created_at if last_message else None,
            'unread_count': unread_count
        })

    # ✅ ИСПРАВЛЕННАЯ сортировка — используем datetime.timezone.utc
    def get_sort_key(item):
        time = item.get('last_message_time')
        if time is None:
            return datetime.min.replace(tzinfo=timezone.utc)  # ← исправлено
        return time

    students_data.sort(key=get_sort_key, reverse=True)

    return render(request, 'teacher/student_chat_list.html', {
        'students': students_data,
        'total_students': len(students_data)
    })


@login_required
def teacher_student_chat_detail(request, user_id):
    """Детальная страница чата между учителем и учеником"""
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # Проверяем права доступа
    is_teacher = current_user.profile.role == 'teacher'
    is_student = current_user.profile.role == 'student'

    if is_student:
        # Студент может общаться только со своим учителем
        if other_user != current_user.profile.teacher:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Вы можете общаться только со своим преподавателем")

        other_name = other_user.profile.full_name or other_user.username
        other_role = 'Преподаватель'

    elif is_teacher:
        # Учитель может общаться только со своими учениками
        if other_user.profile.teacher != current_user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Этот ученик не принадлежит вам")

        other_name = other_user.profile.full_name or other_user.username
        other_role = f'Ученик, группа {other_user.profile.group or "—"}'

    else:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Доступ запрещен")

    # Помечаем все сообщения от другого пользователя как прочитанные
    TeacherStudentMessage.objects.filter(
        sender=other_user,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)

    # Получаем все сообщения между пользователями
    chat_messages = TeacherStudentMessage.objects.filter(
        sender__in=[current_user, other_user],
        recipient__in=[current_user, other_user]
    ).order_by('created_at')

    return render(request, 'chat/teacher_student_chat_detail.html', {
        'other_user': other_user,
        'other_name': other_name,
        'other_role': other_role,
        'chat_messages': chat_messages,
        'is_teacher': is_teacher
    })


@login_required
@require_POST
@csrf_exempt
def send_teacher_student_message(request):
    """API для отправки сообщения между учителем и учеником"""
    try:
        data = json.loads(request.body)
        recipient_id = data.get('recipient_id')
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)

        recipient = get_object_or_404(User, id=recipient_id)
        current_user = request.user

        # Проверяем права
        is_teacher = current_user.profile.role == 'teacher'
        is_student = current_user.profile.role == 'student'

        if is_student:
            # Студент может писать только своему учителю
            if recipient != current_user.profile.teacher:
                return JsonResponse({'error': 'Вы можете писать только своему преподавателю'}, status=403)
        elif is_teacher:
            # Учитель может писать только своим ученикам
            if recipient.profile.teacher != current_user:
                return JsonResponse({'error': 'Этот ученик не принадлежит вам'}, status=403)
        else:
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)

        # Создаем сообщение
        message = TeacherStudentMessage.objects.create(
            sender=current_user,
            recipient=recipient,
            content=content
        )

        # Отправляем уведомление
        notify_about_teacher_message(recipient, current_user, content)

        sender_name = current_user.profile.full_name or current_user.username
        if is_teacher:
            sender_name = f"👩‍🏫 {sender_name}"
        else:
            sender_name = f"👨‍🎓 {sender_name}"

        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.strftime("%H:%M %d.%m.%Y"),
                'sender_id': message.sender_id,
                'sender_name': sender_name
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_teacher_student_messages(request, user_id):
    """API для получения новых сообщений между учителем и учеником"""
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # Проверяем права
    is_teacher = current_user.profile.role == 'teacher'
    is_student = current_user.profile.role == 'student'

    if is_student and other_user != current_user.profile.teacher:
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    elif is_teacher and other_user.profile.teacher != current_user:
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)

    last_id = request.GET.get('last_id')

    messages = TeacherStudentMessage.objects.filter(
        sender__in=[current_user, other_user],
        recipient__in=[current_user, other_user]
    )

    if last_id and last_id != 'null' and last_id != '0':
        try:
            last_id_int = int(last_id)
            messages = messages.filter(id__gt=last_id_int)
        except ValueError:
            pass

    messages = messages.order_by('created_at')

    # Помечаем сообщения от другого пользователя как прочитанные
    TeacherStudentMessage.objects.filter(
        sender=other_user,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)

    messages_data = []
    for msg in messages:
        sender_name = msg.sender.profile.full_name or msg.sender.username
        if msg.sender.profile.role == 'teacher':
            sender_name = f"👩‍🏫 {sender_name}"
        else:
            sender_name = f"👨‍🎓 {sender_name}"

        message_data = {
            'id': msg.id,
            'content': msg.content,
            'message_type': msg.message_type,
            'created_at': msg.created_at.strftime("%H:%M %d.%m.%Y"),
            'sender_id': msg.sender_id,
            'sender_name': sender_name,
            'reactions': msg.reactions or {}
        }

        if msg.message_type == 'file' and msg.file_attachment:
            message_data['file_url'] = msg.file_attachment.url
            message_data['file_name'] = msg.file_name
        elif msg.message_type == 'voice' and msg.voice_message:
            message_data['voice_url'] = msg.voice_message.url
            message_data['voice_duration'] = msg.voice_duration

        messages_data.append(message_data)

    return JsonResponse({'messages': messages_data})


@login_required
def teacher_student_chat_detail(request, user_id):
    """Универсальная страница чата (определяет роль по URL)"""
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    # Определяем по пути запроса, кто открыл страницу
    request_path = request.path
    is_teacher_route = request_path.startswith('/teacher/')
    is_student_route = request_path.startswith('/student/')

    if is_teacher_route:
        # Проверка для учителя
        if current_user.profile.role != 'teacher':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Доступ запрещен")
        if other_user.profile.teacher != current_user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Этот ученик не принадлежит вам")

        other_name = other_user.profile.full_name or other_user.username
        other_role = f'Ученик, группа {other_user.profile.group or "—"}'
        is_teacher = True
        back_url_name = 'teacher_student_chat_list'
        template_name = 'chat/teacher_student_chat_detail_teacher.html'

    elif is_student_route:
        # Проверка для студента
        if current_user.profile.role != 'student':
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Доступ запрещен")
        if other_user != current_user.profile.teacher:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Вы можете общаться только со своим преподавателем")

        other_name = other_user.profile.full_name or other_user.username
        other_role = 'Преподаватель'
        is_teacher = False
        back_url_name = 'student_teacher_chat_list'
        template_name = 'chat/teacher_student_chat_detail_student.html'
    else:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Доступ запрещен")

    # Помечаем все сообщения от другого пользователя как прочитанные
    TeacherStudentMessage.objects.filter(
        sender=other_user,
        recipient=current_user,
        is_read=False
    ).update(is_read=True)

    # Получаем все сообщения между пользователями
    chat_messages = TeacherStudentMessage.objects.filter(
        sender__in=[current_user, other_user],
        recipient__in=[current_user, other_user]
    ).order_by('created_at')

    return render(request, template_name, {
        'other_user': other_user,
        'other_name': other_name,
        'other_role': other_role,
        'chat_messages': chat_messages,
        'is_teacher': is_teacher,
        'back_url_name': back_url_name,
    })