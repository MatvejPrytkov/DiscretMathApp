# decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

from base.models import TestResult


def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role != 'student':
            messages.error(request, 'Доступ только для учеников')
            return redirect('profile')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role != 'teacher':
            messages.error(request, 'Доступ только для учителей')
            return redirect('profile')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def any_user_required(view_func):
    """Декоратор для доступа любым авторизованным пользователям"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def check_test_result_access(func):
    """Декоратор для проверки доступа к результатам теста"""

    @wraps(func)
    def wrapper(request, pk, *args, **kwargs):
        try:
            result = TestResult.objects.get(pk=pk)
        except TestResult.DoesNotExist:
            messages.error(request, "Результат теста не найден")
            if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                return redirect('teacher_dashboard')
            return redirect('profile')

        is_teacher = getattr(request.user.profile, 'role', '') == 'teacher'
        is_student = getattr(request.user.profile, 'role', '') == 'student'

        if is_student and result.user != request.user:
            messages.error(request, "Вы не можете просматривать результаты других учеников")
            return redirect('profile')

        if is_teacher and result.user.profile.teacher != request.user:
            messages.error(request, "Этот результат принадлежит не вашему ученику")
            return redirect('teacher_dashboard')

        return func(request, pk, *args, **kwargs)

    return wrapper