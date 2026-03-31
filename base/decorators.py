from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

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