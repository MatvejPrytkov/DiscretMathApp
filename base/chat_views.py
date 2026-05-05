# chat_views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .decorators import student_required
from .models import User, Message, Notification
from .utils import create_notification
import json


@login_required
@student_required
def groupmates_list(request):
    """Страница со списком одногруппников"""
    user_profile = request.user.profile

    if not user_profile.group or not user_profile.course:
        # Если у студента не указана группа или курс, показываем сообщение
        return render(request, 'student/groupmates.html', {
            'groupmates': [],
            'error': 'У вас не указана группа или курс. Обратитесь к преподавателю.'
        })

    # Находим всех одногруппников (такая же группа, курс и учитель)
    groupmates = User.objects.filter(
        profile__role='student',
        profile__group=user_profile.group,
        profile__course=user_profile.course,
        profile__teacher=user_profile.teacher
    ).exclude(id=request.user.id).select_related('profile')

    # Получаем непрочитанные сообщения для каждого одногруппника
    for groupmate in groupmates:
        unread_count = Message.objects.filter(
            sender=groupmate,
            recipient=request.user,
            is_read=False
        ).count()
        groupmate.unread_count = unread_count

    return render(request, 'student/groupmates.html', {
        'groupmates': groupmates,
        'my_group': user_profile.group,
        'my_course': user_profile.course
    })


@login_required
@student_required
def chat_detail(request, user_id):
    """Страница чата с конкретным пользователем"""
    other_user = get_object_or_404(User, id=user_id)

    # Проверяем, что это одногруппник
    user_profile = request.user.profile
    other_profile = other_user.profile

    if (user_profile.group != other_profile.group or
            user_profile.course != other_profile.course or
            user_profile.teacher != other_profile.teacher):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Вы можете общаться только с одногруппниками")

    # Помечаем все сообщения от этого пользователя как прочитанные
    Message.objects.filter(
        sender=other_user,
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    # Получаем все сообщения между пользователями
    chat_messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        recipient__in=[request.user, other_user]
    ).order_by('created_at')

    return render(request, 'student/chat_detail.html', {
        'other_user': other_user,
        'chat_messages': chat_messages,  # ← ИСПРАВЛЕНО: используем другое имя
        'other_full_name': other_profile.full_name or other_user.username
    })


@login_required
@require_POST
@csrf_exempt
def send_message(request):
    """API для отправки сообщения"""
    try:
        data = json.loads(request.body)
        recipient_id = data.get('recipient_id')
        content = data.get('content', '').strip()

        if not content:
            return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)

        recipient = get_object_or_404(User, id=recipient_id)

        # Проверяем, что это одногруппник
        user_profile = request.user.profile
        recipient_profile = recipient.profile

        if (user_profile.group != recipient_profile.group or
                user_profile.course != recipient_profile.course or
                user_profile.teacher != recipient_profile.teacher):
            return JsonResponse({'error': 'Вы можете общаться только с одногруппниками'}, status=403)

        # Создаем сообщение
        message = Message.objects.create(
            sender=request.user,
            recipient=recipient,
            content=content
        )

        # Отправляем уведомление получателю
        from .utils import create_notification
        create_notification(
            recipient=recipient,
            sender=request.user,
            notification_type='new_message',
            title='💬 Новое сообщение',
            message=f'{request.user.profile.full_name or request.user.username}: {content[:100]}',
            link=f'/student/chat/{request.user.id}/'
        )

        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.strftime("%H:%M %d.%m.%Y"),
                'sender_id': message.sender_id,
                'sender_name': request.user.profile.full_name or request.user.username
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_unread_messages_count(request):
    """API для получения количества непрочитанных сообщений"""
    count = Message.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return JsonResponse({'count': count})


@login_required
def get_chat_users_list(request):
    """API для получения списка чатов с непрочитанными сообщениями"""
    # Находим всех пользователей, от которых есть непрочитанные сообщения
    users_with_unread = User.objects.filter(
        sent_messages__recipient=request.user,
        sent_messages__is_read=False
    ).distinct()

    result = []
    for user in users_with_unread:
        unread_count = Message.objects.filter(
            sender=user,
            recipient=request.user,
            is_read=False
        ).count()
        result.append({
            'id': user.id,
            'name': user.profile.full_name or user.username,
            'unread_count': unread_count
        })

    return JsonResponse({'users': result})