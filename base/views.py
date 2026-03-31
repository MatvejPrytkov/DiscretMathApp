from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from .forms import RegistrationForm
from .models import TestResult
from django.contrib.auth.forms import AuthenticationForm
import pandas as pd
import random
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import TestAnswer
from .forms import UserUpdateForm, PasswordChangeForm
from .decorators import student_required, teacher_required
from django.db.models import Count, Sum, Avg, Max, CharField, Case, When, FloatField, Value
from django.db.models.functions import Round, Cast
def index(request):
    return render(request, 'index.html')
@login_required
@student_required
def test_view(request, test_kind: str):
    """
    test_kind: 'start' или 'final'
    """

    TESTS = {
        'start': {
            'title': 'Входное тестирование',
            'template': 'start.html',
            'result_template': 'result_detail.html',
            'files': {
                'graphs': 'core/static/graphs.xlsx',
                'logic': 'core/static/logic.xlsx',
                'plenty': 'core/static/Plenty.xlsx',
            },
            'per_file_sample': 5,   # как у вас сейчас: по 5 из каждой таблицы
        },
        'final': {
            'title': 'Итоговое тестирование',
            'template': 'final.html',
            'result_template': 'result_detail.html',  # или results_final.html — как вам нужно
            'files': {
                'final': 'core/static/final_test.xlsx',
            },
            'per_file_sample': None,  # берём все вопросы, как сейчас в finish()
        }
    }

    if test_kind not in TESTS:
        return redirect('profile')

    cfg = TESTS[test_kind]

    def option_text(df, actual_row, letter: str) -> str:
        """Преобразует 'a'/'b'/'c'/'d' в текст ответа из answer1..answer4."""
        letter = (letter or '').strip().lower()
        mapping = {'a': 'answer1', 'b': 'answer2', 'c': 'answer3', 'd': 'answer4'}
        col = mapping.get(letter)
        if not col or col not in df.columns:
            return ''
        val = actual_row[col].values[0]
        return '' if pd.isna(val) else str(val).strip()

    # =============== POST (проверка и сохранение) ===============
    if request.method == 'POST':
        results = {}
        total_correct = 0
        total_questions_all = 0
        THEME_NAMES = {
            'graphs': 'Графы',
            'logic': 'Логика',
            'plenty': 'Множества',
        }

        # 1) сначала считаем результат
        for key, filename in cfg['files'].items():
            try:
                df = pd.read_excel(filename)
                id_col = df.columns[0]
                df[id_col] = df[id_col].astype(str)

                question_ids = request.POST.getlist(f'ids_{key}')
                correct_count = 0

                for q_id in question_ids:
                    user_answer = (request.POST.get(f'q_{key}_{q_id}') or '').strip().lower()
                    actual_row = df[df[id_col] == str(q_id)]
                    if actual_row.empty:
                        continue

                    correct_letter = str(actual_row['correct_answer'].values[0]).strip().lower()
                    if user_answer and user_answer == correct_letter:
                        correct_count += 1

                results[key] = {
                    'name': THEME_NAMES.get(key, key),  # ← ЧЕЛОВЕКОЧИТАЕМОЕ НАЗВАНИЕ
                    'correct': correct_count,
                    'total': len(question_ids)
                }
                total_correct += correct_count
                total_questions_all += len(question_ids)

            except Exception as e:
                results[key] = {'name': filename, 'correct': 0, 'total': 0}

        # 2) сохраняем TestResult
        test_result = TestResult.objects.create(
            user=request.user,
            test_type=test_kind,
            score=total_correct,
            total_questions=total_questions_all,
            percent=round((total_correct / total_questions_all) * 100, 2) if total_questions_all else 0,
            correct_answers=total_correct,  # ← ДОБАВЬТЕ
            percentage=round((total_correct / total_questions_all) * 100, 2) if total_questions_all else 0,
            # ← ДОБАВЬТЕ
            category_results=results
        )

        # 3) сохраняем детализацию TestAnswer
        for key, filename in cfg['files'].items():
            try:
                df = pd.read_excel(filename)
                id_col = df.columns[0]
                df[id_col] = df[id_col].astype(str)

                question_ids = request.POST.getlist(f'ids_{key}')

                for q_id in question_ids:
                    user_answer = (request.POST.get(f'q_{key}_{q_id}') or '').strip().lower()
                    actual_row = df[df[id_col] == str(q_id)]
                    if actual_row.empty:
                        continue

                    correct_letter = str(actual_row['correct_answer'].values[0]).strip().lower()
                    q_text = str(actual_row['question'].values[0]) if 'question' in df.columns else ''

                    TestAnswer.objects.create(
                        result=test_result,
                        question_id=int(q_id),
                        question_text=q_text,
                        user_answer=user_answer,
                        user_answer_text=option_text(df, actual_row, user_answer),
                        correct_answer=correct_letter,
                        correct_answer_text=option_text(df, actual_row, correct_letter),
                        is_correct=(user_answer == correct_letter)
                    )

            except Exception as e:
                continue

        # 4) рендер результатов (для start оставим вашу results.html, для final — result_detail.html)
        if test_kind == 'start':
            return render(request, cfg['result_template'], {
                'result': test_result,
                'answers': test_result.answers.all().order_by('question_id'),
                'results_by_category': results,  # Переименуем для ясности в шаблоне
                'total': total_correct,
                'total_questions': total_questions_all,
                'percent': test_result.percent,
                'test_title': cfg['title'],
                'back_url': 'profile',
                'back_text': 'Вернуться в профиль'
            })

        # final: можно вести на детальную страницу по pk, но вы сейчас рендерите шаблон напрямую
        return render(request, cfg['result_template'], {
            'result': test_result,
            'answers': test_result.answers.all().order_by('question_id'),
            'correct': total_correct,
            'total': total_questions_all,
            'percent': test_result.percent,
            'saved': True,
            'test_title': cfg['title'],
            'back_url': 'profile',
            'back_text': 'Назад в профиль',
        })

    # =============== GET (показ вопросов) ===============
    questions_to_render = []

    for key, filename in cfg['files'].items():
        try:
            df = pd.read_excel(filename)
            id_col = df.columns[0]

            if cfg['per_file_sample'] is None:
                sample_df = df
            else:
                sample_df = df.sample(n=min(cfg['per_file_sample'], len(df)))

            for item in sample_df.to_dict('records'):
                item['category'] = key
                item['id_val'] = item[id_col]
                questions_to_render.append(item)

        except Exception:
            continue

    random.shuffle(questions_to_render)

    return render(request, cfg['template'], {
        'questions': questions_to_render,
        'test_title': cfg['title'],
        'test_kind': test_kind,
    })

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            full_name = getattr(getattr(user, 'profile', None), 'full_name', user.get_username())
            messages.success(request, f'Регистрация успешна! Добро пожаловать, {full_name}!')

            # Получаем роль пользователя из формы
            role = form.cleaned_data.get('role')

            # Перенаправляем в зависимости от роли
            if role == 'teacher':
                return redirect('teacher_dashboard')  # Используем имя маршрута из urls.py
            else:
                return redirect('profile')  # Для учеников

        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


# def verify_email(request, uidb64, token):
#     User = get_user_model()
#     try:
#         uid = force_str(urlsafe_base64_decode(uidb64))
#         user = User.objects.get(pk=uid)
#     except (ValueError, TypeError, OverflowError, User.DoesNotExist):
#         user = None
#
#     if user is not None and default_token_generator.check_token(user, token):
#         user.is_active = True
#         user.save()
#         messages.success(request, "Email подтверждён. Теперь вы можете войти.")
#         return redirect('login')
#
#     messages.error(request, "Ссылка подтверждения неверная или устарела.")
#     return redirect('register')
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.as_p:  # Просто проверка валидности формы
            if form.is_valid():
                user = form.get_user()
                login(request, user)

                # Получаем роль напрямую из профиля
                profile = getattr(user, 'profile', None)
                if profile and profile.role == 'teacher':
                    return redirect('teacher_dashboard')
                return redirect('profile')
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('initial')
@login_required
@student_required
def profile(request):
    results = TestResult.objects.filter(user=request.user).order_by('-date_completed')
    return render(request, 'profile.html', {'results': results})


@login_required
def result_detail(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    # Проверка прав: либо владелец, либо учитель
    is_teacher = getattr(request.user.profile, 'role', '') == 'teacher'
    if result.user != request.user and not is_teacher:
        messages.error(request, "У вас нет прав для просмотра этого результата.")
        return redirect('profile')

    answers = result.answers.all().order_by('question_id')
    # 🆕 Вычисляем результаты по категориям из JSON или пересчитываем из ответов
    category_results = result.category_results
    if not category_results:  # Если поле пустое, пересчитываем из TestAnswer
        category_results = {}
        for answer in answers:
            category = 'final'  # по умолчанию
            # Можно добавить логику определения категории по question_id или question_text
            if answer.question_id <= 4:
                category = 'graphs'
            elif answer.question_id <= 9:
                category = 'logic'
            else:
                category = 'plenty'

            if category not in category_results:
                category_results[category] = {'correct': 0, 'total': 0, 'name': ''}

            category_results[category]['total'] += 1
            if answer.is_correct:
                category_results[category]['correct'] += 1

        # Названия тем
        THEME_NAMES = {'graphs': 'Графы', 'logic': 'Логика', 'plenty': 'Множества', 'final': 'Итоговый тест'}
        for cat in category_results:
            category_results[cat]['name'] = THEME_NAMES.get(cat, cat)
    # 🆕 Определяем, куда вести "Назад в профиль"
    if result.user == request.user:
        # Ученик смотрит свои результаты → ведет в его профиль
        back_url = 'profile'
        back_text = 'Назад в профиль'
    else:
        # Учитель смотрит результаты ученика → ведет в учительскую панель
        back_url = 'teacher_dashboard'
        back_text = 'Назад в панель учителя'

    return render(request, 'result_detail.html', {
        'result': result,
        'answers': answers,
        'results_by_category': category_results,
        'back_url': back_url,  # 🆕 Передаем URL для кнопки
        'back_text': back_text  # 🆕 Передаем текст для кнопки
    })
@login_required
def profile_update(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'profile_update.html', {'form': form})


@login_required
def change_password(request):
    """Смена пароля"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['old_password']):
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)  # не выкидывает из сессии
                messages.success(request, 'Пароль успешно изменён!')
                return redirect('profile')
            else:
                form.add_error('old_password', 'Неверный текущий пароль')
    else:
        form = PasswordChangeForm()

    return render(request, 'change_password.html', {'form': form})


@login_required
def delete_account(request):
    """Удаление аккаунта"""
    if request.method == 'POST':
        user = request.user
        username = user.username
        user.delete()
        messages.success(request, f'Аккаунт {username} удалён.')
        return redirect('initial')

    return render(request, 'delete_account.html')


@login_required
@teacher_required
def student_results(request):
    """Просмотр результатов: либо всех 'своих' учеников, либо конкретного"""
    student_id = request.GET.get('student_id')

    # Базовый фильтр: только тесты учеников, привязанных к данному учителю
    results = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).select_related('user', 'user__profile').order_by('-date_completed')

    # Если передан ID конкретного ученика, фильтруем по нему
    if student_id:
        results = results.filter(user_id=student_id)

    return render(request, 'teacher/student_results.html', {
        'results': results
    })

@teacher_required
def manage_tests(request):
    """Управление тестами (добавление/редактирование вопросов)"""
    # Здесь можно добавить логику для работы с Excel файлами
    return render(request, 'teacher/manage_tests.html')

@login_required
def teacher_dashboard(request):
    if request.user.profile.role != 'teacher':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    my_students = User.objects.filter(
        profile__role='student',
        profile__teacher=request.user
    ).select_related('profile').annotate(
        test_count=Count('testresult')
    )

    # 📊 ДАННЫЕ ДЛЯ ГРАФИКОВ
    test_stats = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).values('test_type').annotate(
        count=Count('id'),
        avg_score=Round(Avg('percent'), 1),
        max_score=Max('percent')
    )

    # Распределение успеваемости
    grade_distribution = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).extra(
        select={
            'grade': "CASE "
                     "WHEN percent >= 90 THEN 'Отлично' "
                     "WHEN percent >= 75 THEN 'Хорошо' "
                     "WHEN percent >= 60 THEN 'Удовл.' "
                     "ELSE 'Неудовл.' END"
        }
    ).values('grade').annotate(count=Count('id'))

    # Статистика по темам (из category_results)
    theme_stats = {}
    all_results = TestResult.objects.filter(user__profile__teacher=request.user)
    for result in all_results:
        if result.category_results:
            for theme, data in result.category_results.items():
                if theme not in theme_stats:
                    theme_stats[theme] = {'correct': 0, 'total': 0}
                theme_stats[theme]['correct'] += data.get('correct', 0)
                theme_stats[theme]['total'] += data.get('total', 0)

    total_tests_passed = my_students.aggregate(total=Sum('test_count'))['total'] or 0

    return render(request, 'teacher/teacher_dashboard.html', {
        'students': my_students,
        'student_count': my_students.count(),
        'total_tests_passed': total_tests_passed,
        'test_stats': test_stats,  # Типы тестов
        'grade_distribution': grade_distribution,  # Оценки
        'theme_stats': list(theme_stats.items()),  # Темы
    })

@login_required
def view_student_results(request):
    if request.user.profile.role != 'teacher':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    # Получаем результаты тестов только тех учеников, которые закреплены за текущим учителем
    results = TestResult.objects.filter(
        student__profile__teacher=request.user
    ).order_related('student', 'test').order_by('-date_taken')

    return render(request, 'teacher_results.html', {
        'results': results
    })


@login_required
def student_detail(request, student_id):
    student = get_object_or_404(
        User,
        id=student_id,
        profile__role='student',
        profile__teacher=request.user
    )
    student_results = TestResult.objects.filter(student=student).order_by('-date_taken')

    return render(request, 'student_detail.html', {
        'student': student,
        'results': student_results
    })


