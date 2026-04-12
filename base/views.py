import os

from django.template.loader import render_to_string

from .utils import notify_teacher_about_submission, notify_teacher_about_test_completion, notify_students_about_new_lab, notify_students_about_new_test, notify_student_about_lab_grade, notify_student_about_test_grade
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from .forms import RegistrationForm, GradeTestForm
from .models import LabWork, LabSubmission, TestResult, TestKindCategory, TestKindConfig, Notification
from django.contrib.auth.forms import AuthenticationForm
import pandas as pd
import random
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import TestAnswer
from .forms import UserUpdateForm, PasswordChangeForm, TeacherTestForm, TestQuestionForm
from .decorators import student_required, teacher_required
from django.db.models import Count, Sum, Avg, Max, CharField, Case, When, FloatField, Value
from django.db.models.functions import Round, Cast
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .forms import MyLoginForm, LabWorkForm, AddQuestionForm, CreateTeacherTestForm
from django.db.models import Q
from django.core.paginator import Paginator
from .models import TestCategory, TestQuestion, TeacherTest, TeacherTestQuestion
from django.forms import formset_factory
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from django.http import HttpResponse
from io import BytesIO


def get_file_response(file_field, filename):
    """Возвращает правильный HTTP ответ для файла в зависимости от его типа"""
    file_path = file_field.path
    file_extension = os.path.splitext(filename)[1].lower()

    # MIME-типы для разных форматов
    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
    }

    content_type = mime_types.get(file_extension, 'application/octet-stream')

    # Для файлов, которые можно просмотреть в браузере (PDF, изображения, текстовые)
    viewable_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.txt'}

    if file_extension in viewable_extensions:
        # Открываем в браузере
        response = HttpResponse(content_type=content_type)
        with open(file_path, 'rb') as f:
            response.write(f.read())
        response['Content-Disposition'] = f'inline; filename="{filename}"'
    else:
        # Скачиваем файл
        response = HttpResponse(content_type=content_type)
        with open(file_path, 'rb') as f:
            response.write(f.read())
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
def index(request):
    return render(request, 'index.html')
@login_required
@student_required
def test_view(request, test_kind: str):
    """
    test_kind: 'start' или 'final' (код из TestKindConfig)
    Полностью работает с данными из БД
    """
    # Получаем конфигурацию теста из БД
    try:
        test_config = TestKindConfig.objects.get(code=test_kind, is_active=True)
    except TestKindConfig.DoesNotExist:
        messages.error(request, f"Тест '{test_kind}' не найден или неактивен")
        return redirect('profile')

    # =============== POST (проверка и сохранение) ===============
    if request.method == 'POST':
        results = {}
        total_correct = 0
        total_questions_all = 0

        # Получаем все категории для этого типа теста
        test_categories = test_config.categories.all()

        for category in test_categories:
            try:
                # Получаем конфигурацию количества вопросов для этой категории
                kind_category = TestKindCategory.objects.get(
                    test_kind=test_config,
                    category=category
                )
                questions_needed = kind_category.questions_count

                # Получаем отправленные ID вопросов для этой категории
                question_ids = request.POST.getlist(f'ids_{category.code}')

                correct_count = 0
                question_details = []

                for q_id in question_ids:
                    user_answer = (request.POST.get(f'q_{category.code}_{q_id}') or '').strip().lower()
                    try:
                        question = TestQuestion.objects.get(
                            id=q_id,
                            category=category,
                            is_active=True
                        )
                        is_correct = (user_answer == question.correct_option)

                        if is_correct:
                            correct_count += 1

                        # Сохраняем детали ответа
                        question_details.append({
                            'question_id': q_id,
                            'user_answer': user_answer,
                            'correct_answer': question.correct_option,
                            'is_correct': is_correct,
                            'question_text': question.question_text
                        })

                    except TestQuestion.DoesNotExist:
                        continue

                results[category.code] = {
                    'name': category.name,
                    'correct': correct_count,
                    'total': len(question_ids),
                    'config_questions': questions_needed,
                    'questions': question_details
                }

                total_correct += correct_count
                total_questions_all += len(question_ids)

            except TestKindCategory.DoesNotExist:
                results[category.code] = {'name': category.name, 'correct': 0, 'total': 0}
            except Exception as e:
                results[category.code] = {'name': category.name, 'correct': 0, 'total': 0}

        # Сохраняем результат теста
        test_result = TestResult.objects.create(
            user=request.user,
            test_type=test_kind,
            score=total_correct,
            total_questions=total_questions_all,
            percent=round((total_correct / total_questions_all) * 100, 2) if total_questions_all else 0,
            correct_answers=total_correct,
            percentage=round((total_correct / total_questions_all) * 100, 2) if total_questions_all else 0,
            category_results=results
        )

        # Сохраняем детальные ответы
        for category_code, data in results.items():
            for question_detail in data.get('questions', []):
                question = TestQuestion.objects.get(id=question_detail['question_id'])

                TestAnswer.objects.create(
                    result=test_result,
                    question_id=question.id,
                    question_text=question.question_text,
                    user_answer=question_detail['user_answer'],
                    user_answer_text=_get_answer_text(question, question_detail['user_answer']),
                    correct_answer=question.correct_option,
                    correct_answer_text=_get_answer_text(question, question.correct_option),
                    is_correct=question_detail['is_correct']
                )

        # ========== УВЕДОМЛЕНИЕ УЧИТЕЛЮ ==========
        # Получаем учителя ученика
        teacher = None
        if hasattr(request.user, 'profile') and request.user.profile.teacher:
            teacher = request.user.profile.teacher

        # Отправляем уведомление учителю о прохождении теста
        if teacher:
            test_name = "Входное тестирование" if test_kind == 'start' else "Итоговое тестирование"
            from .utils import create_notification
            create_notification(
                recipient=teacher,
                sender=request.user,
                notification_type='test_completed',
                title=f'📊 Пройден тест: {test_name}',
                message=f'Студент {request.user.profile.full_name} прошел {test_name}. Результат: {total_correct}/{total_questions_all} ({round((total_correct / total_questions_all) * 100, 2)}%).',
                link=f'/result/{test_result.id}/'
            )

        # Рендерим результаты
        return render(request, test_config.result_template, {
            'result': test_result,
            'answers': test_result.answers.all().order_by('question_id'),
            'results_by_category': results,
            'total': total_correct,
            'total_questions': total_questions_all,
            'percent': test_result.percent,
            'test_title': test_config.title,
            'test_config': test_config,
            'back_url': 'profile',
            'back_text': 'Вернуться в профиль'
        })

    # =============== GET (показ вопросов) ===============
    questions_to_render = []

    # Получаем все категории для этого типа теста
    test_categories = test_config.categories.filter(is_active=True)

    for category in test_categories:
        try:
            # Получаем конфигурацию количества вопросов для этой категории
            kind_category = TestKindCategory.objects.get(
                test_kind=test_config,
                category=category
            )
            questions_needed = kind_category.questions_count

            # Получаем вопросы для категории
            queryset = TestQuestion.objects.filter(
                category=category,
                is_active=True
            )

            # Выбираем вопросы в зависимости от конфигурации
            if questions_needed > 0:
                questions = list(queryset.order_by('?')[:questions_needed])
            else:
                # 0 означает все вопросы
                questions = list(queryset.order_by('?'))

            # Форматируем для шаблона
            for question in questions:
                questions_to_render.append({
                    'category': category.code,
                    'id_val': question.id,
                    'question': question.question_text,
                    'answer1': question.option_a,
                    'answer2': question.option_b,
                    'answer3': question.option_c,
                    'answer4': question.option_d,
                    'correct_answer': question.correct_option,
                    'difficulty': question.get_difficulty_display()
                })

        except TestKindCategory.DoesNotExist:
            continue
        except TestQuestion.DoesNotExist:
            continue

    # Перемешиваем вопросы
    random.shuffle(questions_to_render)

    return render(request, test_config.template, {
        'questions': questions_to_render,
        'test_title': test_config.title,
        'test_kind': test_kind,
        'test_config': test_config,
        'categories': test_categories
    })

def _get_answer_text(question, option_letter):
    """Получает текст ответа по букве варианта"""
    mapping = {
        'a': question.option_a,
        'b': question.option_b,
        'c': question.option_c,
        'd': question.option_d,
    }
    return mapping.get(option_letter.lower(), '')

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


def login_view(request):
    if request.method == "POST":
        # Используем MyLoginForm вместо AuthenticationForm
        form = MyLoginForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()
            selected_role = request.POST.get("role")  # 'student' или 'teacher'
            profile = getattr(user, 'profile', None)
            actual_role = getattr(profile, 'role', None)

            # Если у пользователя нет профиля/роли — лучше запретить вход
            if not actual_role:
                messages.error(request, "У аккаунта не задана роль. Обратитесь к администратору.")
                return render(request, "login.html", {"form": form})

            # Проверка на несовпадение роли
            if selected_role != actual_role:
                messages.error(request, "Вы выбрали неверную роль для этого аккаунта.")
                return render(request, "login.html", {"form": form})
            login(request, user)
            if actual_role == 'teacher':
                return redirect('teacher_dashboard')
            return redirect('profile')


        # Если данные неверны, Django автоматически передаст форму с нашими русскими ошибками
        return render(request, "login.html", {"form": form})

    else:
        form = MyLoginForm()

    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('initial')


@login_required
@student_required
def profile(request):
    user = request.user

    # Получаем параметры фильтрации из GET-запроса
    type_filter = request.GET.get('type', '')
    grade_filter = request.GET.get('grade', '')
    status_filter = request.GET.get('status', '')
    anchor = request.GET.get('anchor', '')  # Добавляем получение якоря

    # Оценки за лабораторные
    lab_submissions = LabSubmission.objects.filter(
        student=user,
    ).select_related('lab_work')

    # Применяем фильтры к лабораторным
    if type_filter and type_filter != 'lab':
        lab_submissions = lab_submissions.none()

    if grade_filter:
        if grade_filter == 'pending':
            lab_submissions = lab_submissions.filter(Q(grade__isnull=True) | Q(grade=''))
        else:
            lab_submissions = lab_submissions.filter(grade=grade_filter)

    if status_filter:
        lab_submissions = lab_submissions.filter(status=status_filter)

    # Оценки за тесты
    test_grades = TestResult.objects.filter(
        user=user
    ).order_by('-date_completed')

    # Применяем фильтры к тестам
    if type_filter and type_filter != 'lab':
        if type_filter == 'start':
            test_grades = test_grades.filter(test_type='start')
        elif type_filter == 'final':
            test_grades = test_grades.filter(test_type='final')
        elif type_filter == 'teacher':
            test_grades = test_grades.filter(test_type='teacher')
    elif type_filter == 'lab':
        test_grades = test_grades.none()

    if grade_filter:
        if grade_filter == 'pending':
            test_grades = test_grades.filter(grade__isnull=True)
        else:
            test_grades = test_grades.filter(grade=grade_filter)

    if status_filter:
        if status_filter == 'graded':
            test_grades = test_grades.filter(grade__isnull=False)
        elif status_filter == 'pending':
            test_grades = test_grades.filter(grade__isnull=True)

    total_count = lab_submissions.count() + test_grades.count()

    teacher_tests = TeacherTest.objects.filter(assigned_to=user, is_active=True).distinct()

    # Получаем данные об учителе ученика
    teacher = None
    teacher_name = None
    if hasattr(user, 'profile') and user.profile.teacher:
        teacher = user.profile.teacher
        if hasattr(teacher, 'profile') and teacher.profile.full_name:
            teacher_name = teacher.profile.full_name
        else:
            teacher_name = teacher.get_full_name() or teacher.username

    context = {
        'user': user,
        'lab_grades': lab_submissions,
        'test_grades': test_grades,
        'results': test_grades,
        'teacher_tests': teacher_tests,
        'total_count': total_count,
        'teacher': teacher,
        'teacher_name': teacher_name,
        # Передаем текущие фильтры в шаблон
        'current_type_filter': type_filter,
        'current_grade_filter': grade_filter,
        'current_status_filter': status_filter,
        'anchor': anchor,  # Передаем якорь в шаблон
    }
    return render(request, 'student/Profile.html', context)

@login_required
def result_detail(request, pk):
    result = get_object_or_404(TestResult, pk=pk)

    # Проверка прав: либо владелец, либо учитель
    is_teacher = getattr(request.user.profile, 'role', '') == 'teacher'
    if result.user != request.user and not is_teacher:
        messages.error(request, "У вас нет прав для просмотра этого результата.")
        return redirect('profile')

    # Обработка формы оценки (только для учителей)
    if is_teacher and request.method == 'POST':
        form = GradeTestForm(request.POST, instance=result)
        if form.is_valid():
            saved_result = form.save(commit=False)
            saved_result.graded_by = request.user
            saved_result.graded_at = timezone.now()
            saved_result.save()
            notify_student_about_test_grade(request.user, result.user, saved_result)
            messages.success(request, 'Оценка успешно сохранена!')
            return redirect('result_detail', pk=pk)
    else:
        form = GradeTestForm(instance=result)

    answers = result.answers.all().order_by('question_id')

    # Получаем результаты по темам из JSON-поля
    results_by_category = result.category_results

    # Определяем URL для кнопки "Назад"
    if result.user == request.user:
        back_url = 'profile'
        back_text = 'Назад в профиль'
    else:
        back_url = 'teacher_dashboard'
        back_text = 'Назад в панель учителя'

    return render(request, 'student/result_detail.html', {
        'result': result,
        'answers': answers,
        'results_by_category': results_by_category,  # Добавьте эту строку
        'form': form,
        'is_teacher': is_teacher,
        'back_url': back_url,
        'back_text': back_text
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

    return render(request, 'student/profile_update.html', {'form': form})

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

    return render(request, 'student/change_password.html', {'form': form})


@login_required
def delete_account(request):
    """Удаление аккаунта"""
    if request.method == 'POST':
        user = request.user
        username = user.username
        user.delete()
        messages.success(request, f'Аккаунт {username} удалён.')
        return redirect('initial')

    return render(request, 'student/delete_account.html')


@login_required
@teacher_required
def student_results(request):
    """Просмотр результатов: либо всех 'своих' учеников, либо конкретного"""
    student_id = request.GET.get('student_id')
    type_filter = request.GET.get('type_filter', '')
    grade_filter = request.GET.get('grade_filter', '')

    # Базовый фильтр: только ученики, привязанные к данному учителю
    students = User.objects.filter(
        profile__role='student',
        profile__teacher=request.user
    ).select_related('profile')

    # Если выбран конкретный ученик
    selected_student = None
    if student_id:
        selected_student = get_object_or_404(students, id=student_id)

    # Результаты тестов учеников
    test_results = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).select_related('user', 'user__profile').order_by('-date_completed')

    # Результаты лабораторных работ
    lab_results = LabSubmission.objects.filter(
        student__profile__teacher=request.user
    ).select_related('student__profile', 'lab_work').order_by('-submitted_at')

    # Фильтрация по конкретному ученику
    if student_id:
        test_results = test_results.filter(user_id=student_id)
        lab_results = lab_results.filter(student_id=student_id)

    # Применяем фильтр по типу
    if type_filter == 'test':
        lab_results = lab_results.none()
    elif type_filter == 'lab':
        test_results = test_results.none()

    # Применяем фильтр по оценке
    if grade_filter:
        if grade_filter == 'pending':
            # Непроверенные работы
            test_results = test_results.filter(grade__isnull=True)
            lab_results = lab_results.filter(grade__isnull=True)
        else:
            # Конкретная оценка
            test_results = test_results.filter(grade=grade_filter)
            lab_results = lab_results.filter(grade=grade_filter)

    # Преобразуем лабораторные работы в формат, похожий на TestResult для единого отображения
    combined_results = []

    # Добавляем результаты тестов
    for result in test_results:
        combined_results.append({
            'type': 'test',
            'user': result.user,
            'user_name': result.user.profile.full_name or result.user.username,
            'title': result.get_test_type_display(),
            'score': f"{result.score}/{result.total_questions}",
            'percent': result.percent,
            'grade': result.get_grade_display() if result.grade else None,
            'grade_value': result.grade,
            'date': result.date_completed,
            'detail_url': f'/result/{result.id}/'
        })

    # Добавляем результаты лабораторных работ
    for submission in lab_results:
        grade_num = None
        if submission.grade == '5':
            grade_num = 5
        elif submission.grade == '4':
            grade_num = 4
        elif submission.grade == '3':
            grade_num = 3
        elif submission.grade == '2':
            grade_num = 2

        combined_results.append({
            'type': 'lab',
            'user': submission.student,
            'user_name': submission.student.profile.full_name or submission.student.username,
            'title': f"Лабораторная: {submission.lab_work.title}",
            'score': submission.grade or "—",
            'percent': None,
            'grade': submission.grade,
            'grade_value': grade_num,
            'date': submission.submitted_at,
            'status': submission.get_status_display(),
            'detail_url': f'/teacher/lab/submission/{submission.id}/'
        })

    # Сортируем по дате (сначала новые)
    combined_results.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'teacher/student_results.html', {
        'results': combined_results,
        'students': students,
        'selected_student': selected_student,
        'student_id': student_id,
    })

@teacher_required
def manage_tests(request):
    """Управление тестами (добавление/редактирование вопросов)"""
    # Здесь можно добавить логику для работы с Excel файлами
    return render(request, 'teacher/manage_tests.html')


@login_required
@teacher_required
def teacher_dashboard(request):
    if request.user.profile.role != 'teacher':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    my_students = User.objects.filter(
        profile__role='student',
        profile__teacher=request.user
    ).select_related('profile').annotate(
        test_count=Count('testresult', distinct=True),
        lab_submission_count=Count(
            'lab_submissions__lab_work',
            filter=Q(lab_submissions__status__in=['submitted', 'under_review', 'graded']),
            distinct=True
        )
    )

    # 📊 ДАННЫЕ ДЛЯ ГРАФИКОВ
    test_stats = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).values('test_type').annotate(
        count=Count('id'),
        avg_score=Round(Avg('percent'), 1),
        max_score=Max('percent')
    )

    # Распределение оценок за ТЕСТЫ (исправлено)
    test_grade_counts = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).values('grade').annotate(count=Count('id'))

    test_grade_5_count = 0
    test_grade_4_count = 0
    test_grade_3_count = 0
    test_grade_2_count = 0
    test_grade_pending_count = 0

    for item in test_grade_counts:
        if item['grade'] == 5:
            test_grade_5_count = item['count']
        elif item['grade'] == 4:
            test_grade_4_count = item['count']
        elif item['grade'] == 3:
            test_grade_3_count = item['count']
        elif item['grade'] == 2:
            test_grade_2_count = item['count']

    # Непроверенные тесты
    test_grade_pending_count = TestResult.objects.filter(
        user__profile__teacher=request.user,
        grade__isnull=True
    ).count()

    # Распределение оценок за ЛАБОРАТОРНЫЕ
    lab_submissions = LabSubmission.objects.filter(
        student__profile__teacher=request.user
    )

    lab_grade_5_count = lab_submissions.filter(grade='5').count()
    lab_grade_4_count = lab_submissions.filter(grade='4').count()
    lab_grade_3_count = lab_submissions.filter(grade='3').count()
    lab_grade_2_count = lab_submissions.filter(grade='2').count()
    lab_grade_pending_count = lab_submissions.filter(grade__isnull=True).count()

    # Статистика по лабораторным работам (для графика)
    lab_stats = []
    labs = LabWork.objects.filter(created_by=request.user, is_active=True)
    for lab in labs:
        submissions = LabSubmission.objects.filter(lab_work=lab, student__profile__teacher=request.user)
        total = submissions.count()
        graded_count = submissions.filter(grade__isnull=False).exclude(grade='').count()
        lab_stats.append({
            'name': lab.title[:20],
            'total': total,
            'graded_count': graded_count
        })

    # Статистика по темам (из category_results)
    theme_stats = {}
    TRANSLATIONS = {
        'graphs': 'Графы',
        'logic': 'Логика',
        'plenty': 'Множества',
        'final': 'Итоговый',
        'start': 'Входной',
        'teacher_test':'Тест от учителя'
    }
    all_results = TestResult.objects.filter(user__profile__teacher=request.user)
    for result in all_results:
        if result.category_results:
            for theme, data in result.category_results.items():
                if theme not in theme_stats:
                    display_name = TRANSLATIONS.get(theme, theme)
                    theme_stats[theme] = {'correct': 0, 'total': 0, 'name': display_name}
                theme_stats[theme]['correct'] += data.get('correct', 0)
                theme_stats[theme]['total'] += data.get('total', 0)

    total_tests_passed = my_students.aggregate(total=Sum('test_count'))['total'] or 0
    total_labs_submitted = my_students.aggregate(total=Sum('lab_submission_count'))['total'] or 0
    lab_count = LabWork.objects.filter(created_by=request.user).count()
    pending_submissions = LabSubmission.objects.filter(
        status='under_review',
        lab_work__created_by=request.user
    ).count()

    return render(request, 'teacher/teacher_dashboard.html', {
        'students': my_students,
        'student_count': my_students.count(),
        'total_tests_passed': total_tests_passed,
        'total_labs_submitted': total_labs_submitted,
        'test_stats': test_stats,
        'test_grade_5_count': test_grade_5_count,
        'test_grade_4_count': test_grade_4_count,
        'test_grade_3_count': test_grade_3_count,
        'test_grade_2_count': test_grade_2_count,
        'test_grade_pending_count': test_grade_pending_count,
        'lab_grade_5_count': lab_grade_5_count,
        'lab_grade_4_count': lab_grade_4_count,
        'lab_grade_3_count': lab_grade_3_count,
        'lab_grade_2_count': lab_grade_2_count,
        'lab_grade_pending_count': lab_grade_pending_count,
        'theme_stats': list(theme_stats.items()),
        'lab_stats': lab_stats,
        'lab_count': lab_count,
        'pending_submissions': pending_submissions,
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
@login_required
@teacher_required
def download_report(request):
    # Берём все результаты учеников, закреплённых за учителем
    results = (
        TestResult.objects
        .filter(user__profile__teacher=request.user)
        .select_related('user', 'user__profile')
        .prefetch_related('answers')
        .order_by('user__profile__full_name', '-date_completed')
    )

    now = timezone.localtime(timezone.now())
    lines = []
    lines.append("ОТЧЁТ ПО ТЕСТАМ")
    lines.append(f"Преподаватель: {request.user.profile.full_name}")
    lines.append(f"Дата формирования: {now.strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")

    if not results.exists():
        lines.append("Нет данных для отчёта.")
    else:
        current_student = None

        for r in results:
            student_name = getattr(r.user.profile, "full_name", r.user.username)

            # Заголовок ученика
            if student_name != current_student:
                current_student = student_name
                lines.append(f"Ученик: {student_name}")
                lines.append(f"Email: {r.user.email}")
                grp = r.user.profile.group or "-"
                course = r.user.profile.course or "-"
                lines.append(f"Группа: {grp} | Курс: {course}")
                lines.append("-" * 60)

            # Строка теста
            test_type_display = "Входной" if r.test_type == "start" else "Итоговый" if r.test_type == "final" else r.test_type
            dt = timezone.localtime(r.date_completed).strftime('%d.%m.%Y %H:%M')
            percent = r.percent if r.percent is not None else r.percentage

            lines.append(f"[{dt}] {test_type_display}: {r.score}/{r.total_questions} ({round(percent, 2)}%)")

            # Результаты по темам (из JSON category_results)
            if r.category_results:
                lines.append("  По темам:")
                for key, data in r.category_results.items():
                    name = data.get("name") or key
                    correct = data.get("correct", 0)
                    total = data.get("total", 0)
                    p = round((correct / total) * 100, 2) if total else 0
                    lines.append(f"   - {name}: {correct}/{total} ({p}%)")

            # (опционально) детализация по каждому вопросу
            # если не нужно — удалите этот блок целиком
            ans = list(r.answers.all().order_by('question_id'))
            if ans:
                lines.append("  Детализация ответов:")
                for a in ans:
                    status = "OK" if a.is_correct else "NO"
                    ua = a.user_answer or "-"
                    ca = a.correct_answer or "-"
                    lines.append(f"   Q{a.question_id}: {status} | ваш: {ua} | верный: {ca}")
            lines.append("")

    content = "\n".join(lines)
    filename = f"report_{now.strftime('%Y-%m-%d_%H-%M')}.txt"

    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@teacher_required
def grade_test_result(request, result_id):
    result = get_object_or_404(TestResult, id=result_id)
    if result.user.profile.teacher != request.user:
        raise PermissionDenied("Нет прав на оценку этого теста")

    if request.method == 'POST':
        grade = request.POST.get('grade')
        comment = request.POST.get('comment', '')

        # Валидация оценки
        valid_grades = ['2', '3', '4', '5', 'н']
        if grade not in valid_grades:
            messages.error(request, 'Неверная оценка')
            return render(request, 'teacher/grade_test.html', {'result': result})

        result.grade = grade
        result.grade_comment = comment
        result.grade_date = timezone.now()
        result.save()

        messages.success(request, f'Оценка "{grade}" выставлена за тест!')
        return redirect('student_results')

    return render(request, 'teacher/grade_test.html', {'result': result})


@login_required
@teacher_required
def teacher_labs(request):
    labs = LabWork.objects.filter(created_by=request.user).order_by('-created_at')

    submissions = LabSubmission.objects.filter(
        lab_work__created_by=request.user
    ).select_related('student__profile', 'lab_work')

    # Фильтрация по проверенности через grade, а не checked
    checked_filter = request.GET.get('checked')

    if checked_filter == 'true':
        submissions = submissions.filter(
            Q(grade__isnull=False) & ~Q(grade='')
        )
    elif checked_filter == 'false':
        submissions = submissions.filter(
            Q(grade__isnull=True) | Q(grade='')
        )

    # Фильтрация по ФИО студента
    search_name = request.GET.get('search_name', '').strip()
    if search_name:
        submissions = submissions.filter(
            student__profile__full_name__icontains=search_name
        )

    submissions = submissions.order_by('-submitted_at')
    total_submissions = submissions.count()

    return render(request, 'teacher/teacher_labs.html', {
        'labs': labs,
        'submissions': submissions,
        'total_submissions': total_submissions,
        'checked_filter': checked_filter,
        'search_name': search_name,
    })

@login_required
@teacher_required
def delete_lab_work(request, lab_id):
    """Удаление лабораторной работы (только для создавшего учителя)"""
    lab = get_object_or_404(LabWork, id=lab_id)

    # Проверяем, что текущий пользователь - создатель лабораторной
    if lab.created_by != request.user:
        messages.error(request, 'Вы не можете удалить чужую лабораторную работу')
        return redirect('teacher_labs')

    # Получаем название перед удалением для сообщения
    lab_title = lab.title

    # Удаляем лабораторную работу (все связанные submission удалятся каскадно)
    lab.delete()

    messages.success(request, f'Лабораторная работа "{lab_title}" успешно удалена')
    return redirect('teacher_labs')


@login_required
@student_required
def student_labs(request):
    teacher_labs = LabWork.objects.filter(
        created_by=request.user.profile.teacher
    ).filter(is_active=True)

    # Свои сдачи
    my_submissions = LabSubmission.objects.filter(
        student=request.user
    ).select_related('lab_work', 'graded_by__profile').order_by('-submitted_at')

    # Получаем ID всех лабораторных работ, которые уже сданы
    submitted_lab_ids = set(submission.lab_work_id for submission in my_submissions)

    return render(request, 'student/student_labs.html', {
        'labs': teacher_labs,
        'my_submissions': my_submissions,
        'submitted_lab_ids': submitted_lab_ids  # Новый контекст
    })
@login_required
@teacher_required
def create_lab_work(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        theme = request.POST.get('theme')
        docx_file = request.FILES.get('docx_file')
        pptx_file = request.FILES.get('pptx_file')  # новое поле для презентации

        if not all([title, description, theme, docx_file]):
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('teacher_labs')

        lab = LabWork.objects.create(
            title=title,
            description=description,
            theme=theme,
            docx_file=docx_file,
            pptx_file=pptx_file,  # сохраняем pptx файл
            created_by=request.user,
            difficulty=request.POST.get('difficulty', 'medium')
        )
        students = User.objects.filter(profile__teacher=request.user, profile__role='student')
        notify_students_about_new_lab(request.user, students, lab)
        messages.success(request, f'Лабораторная "{title}" создана!')
        return redirect('lab_detail', lab_id=lab.id)

    return render(request, 'teacher/create_lab.html')

@login_required
def lab_view(request, lab_id):

    lab = get_object_or_404(LabWork, id=lab_id)
    if lab.created_by != request.user.profile.teacher:
        raise PermissionDenied("У вас нет доступа к этой лабораторной")
    existing_submission = lab.submissions.filter(
        student=request.user,
        lab_work=lab
    ).first()

    context = {
        'lab': lab,
        'existing_submission': existing_submission,
    }
    return render(request, 'student/lab.html', context)


@login_required
@teacher_required
def lab_detail(request, lab_id):
    lab = get_object_or_404(LabWork, id=lab_id, created_by=request.user)
    submissions = lab.submissions.select_related('student__profile').order_by('-submitted_at')

    if request.method == 'POST':
        submission_id = request.POST.get('submission_id')
        grade = request.POST.get('grade')
        comment = request.POST.get('comment', '')

        if submission_id and grade:
            submission = get_object_or_404(LabSubmission, id=submission_id, lab_work=lab)
            submission.grade = grade
            submission.comment = comment
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.graded_by = request.user
            submission.save()
            messages.success(request, 'Оценка сохранена!')
            return redirect('lab_detail', lab_id=lab.id)

    return render(request, 'teacher/lab_detail.html', {
        'lab': lab,
        'submissions': submissions,
    })


@login_required
@student_required
def submit_lab(request, lab_id):
    """Сдача лабораторной работы"""
    lab = get_object_or_404(LabWork, id=lab_id, is_active=True)

    # Проверяем, что это лабораторная преподавателя ученика
    if lab.created_by != request.user.profile.teacher:
        messages.error(request, 'У вас нет доступа к этой лабораторной')
        return redirect('student_labs')

    if request.method == 'POST':
        submitted_file = request.FILES.get('submitted_file')
        comment = request.POST.get('comment', '').strip()

        if submitted_file:
            submission = LabSubmission.objects.create(
                lab_work=lab,
                student=request.user,
                submitted_file=submitted_file,
                comment=comment,
                status='under_review'
            )

            # Передаем submission.id в функцию
            notify_teacher_about_submission(lab.created_by, request.user, lab, submission.id)

            messages.success(request, 'Работа сдана на проверку!')
            return redirect('student_labs')
        else:
            messages.error(request, 'Прикрепите файл!')

    return render(request, 'student/lab.html', {'lab': lab})

@login_required
@teacher_required
def add_question(request):
    """Добавление нового вопроса в базу"""
    if request.method == 'POST':
        form = AddQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            messages.success(request, 'Вопрос успешно добавлен!')
            return redirect('manage_questions')
    else:
        form = AddQuestionForm()
    return render(request, 'teacher/add_question.html', {'form': form})


@login_required
@teacher_required
def manage_questions(request):
    """Просмотр всех вопросов, созданных учителем"""
    questions = TestQuestion.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'teacher/manage_questions.html', {'questions': questions})


@login_required
@teacher_required
def create_teacher_test(request):
    if request.method == 'POST':
        test_form = TeacherTestForm(request.POST)
        question_formset = formset_factory(TestQuestionForm, extra=0)

        # Обработка выбранных вопросов из БД
        selected_question_ids = request.POST.getlist('existing_questions')
        selected_questions = TestQuestion.objects.filter(id__in=selected_question_ids)

        if test_form.is_valid():
            test = test_form.save(commit=False)
            test.teacher = request.user
            test.save()

            # Добавляем выбранные вопросы из БД
            test.questions.add(*selected_questions)

            # Обрабатываем динамически добавленные вопросы
            i = 0
            while f'question_form-{i}-question_text' in request.POST:
                question_text = request.POST.get(f'question_form-{i}-question_text')
                if question_text:  # Проверяем, что вопрос не пустой
                    # Получаем категорию
                    category_id = request.POST.get(f'question_form-{i}-category')
                    try:
                        category = TestCategory.objects.get(id=category_id)
                    except (TestCategory.DoesNotExist, ValueError):
                        # Если категория не выбрана, берем первую доступную
                        category = TestCategory.objects.first()
                        if not category:
                            messages.error(request, 'Нет доступных категорий вопросов')
                            return redirect('create_teacher_test')

                    # Преобразуем правильный ответ из '1','2','3','4' в 'a','b','c','d'
                    correct_option_raw = request.POST.get(f'question_form-{i}-correct_answer')
                    correct_option_map = {'1': 'a', '2': 'b', '3': 'c', '4': 'd'}
                    correct_option = correct_option_map.get(correct_option_raw, 'a')

                    question = TestQuestion.objects.create(
                        category=category,
                        question_text=question_text,
                        option_a=request.POST.get(f'question_form-{i}-option1'),
                        option_b=request.POST.get(f'question_form-{i}-option2'),
                        option_c=request.POST.get(f'question_form-{i}-option3'),
                        option_d=request.POST.get(f'question_form-{i}-option4'),
                        correct_option=correct_option,
                        created_by=request.user
                    )
                    test.questions.add(question)
                i += 1

            # ОБРАБОТКА ВЫБРАННЫХ УЧЕНИКОВ
            selected_student_ids = request.POST.getlist('selected_students')
            if selected_student_ids:
                # Добавляем только выбранных учеников
                students = User.objects.filter(id__in=selected_student_ids, profile__teacher=request.user)
                test.assigned_to.set(students)
            else:
                # Если никого не выбрано - добавляем всех учеников учителя
                students = User.objects.filter(profile__teacher=request.user, profile__role='student')
                test.assigned_to.set(students)
                messages.info(request, 'Тест назначен всем вашим ученикам')
            notify_students_about_new_test(request.user, students, test)
            messages.success(request, f'Тест "{test.title}" успешно создан!')
            return redirect('teacher_manage_tests')

    else:
        test_form = TeacherTestForm()

    # Получаем все существующие вопросы для чекбоксов
    all_questions = TestQuestion.objects.all()
    # Получаем все категории для выпадающих списков
    categories = TestCategory.objects.all()

    context = {
        'test_form': test_form,
        'all_questions': all_questions,
        'categories': categories,
    }
    return render(request, 'teacher/create_teacher_test.html', context)
@login_required
@teacher_required
def teacher_manage_tests(request):
    """Управление тестами от учителя"""
    tests = TeacherTest.objects.filter(teacher=request.user).order_by('-created_at')
    return render(request, 'teacher/manage_tests.html', {'tests': tests})


@login_required
@teacher_required
def teacher_test_detail(request, test_id):
    """Детали теста от учителя"""
    test = get_object_or_404(TeacherTest, id=test_id, teacher=request.user)
    return render(request, 'teacher/test_detail.html', {'test': test})


@login_required
@teacher_required
def delete_teacher_test(request, test_id):
    """Удаление теста учителя"""
    test = get_object_or_404(TeacherTest, id=test_id, teacher=request.user)

    if request.method == 'POST':
        test_title = test.title
        test.delete()
        messages.success(request, f'Тест "{test_title}" успешно удален')
        return redirect('teacher_manage_tests')

    # Если GET запрос, показываем подтверждение (будет через JavaScript)
    return redirect('teacher_manage_tests')


@login_required
@student_required
def student_teacher_tests(request):
    teacher = request.user.profile.teacher

    tests = TeacherTest.objects.filter(
        teacher=teacher,
        is_active=True
    ).filter(
        Q(assigned_to=request.user) | Q(assigned_to__isnull=True)
    ).distinct()

    # Получаем ID тестов, которые уже пройдены (используя новое поле)
    completed_test_ids = set(
        TestResult.objects.filter(
            user=request.user,
            test_type='teacher',
            teacher_test__isnull=False
        ).values_list('teacher_test_id', flat=True)
    )

    # Создаем словарь результатов для быстрого доступа
    results_map = {
        result.teacher_test_id: result
        for result in TestResult.objects.filter(
            user=request.user,
            test_type='teacher',
            teacher_test__isnull=False
        ).select_related('teacher_test')
    }

    for test in tests:
        test.is_completed = test.id in completed_test_ids
        test.result = results_map.get(test.id)

    return render(request, 'student/teacher_tests.html', {'tests': tests})
@login_required
@student_required
def take_teacher_test(request, test_id):
    """Прохождение теста от учителя"""
    test = get_object_or_404(TeacherTest, id=test_id, is_active=True)
    if not test.assigned_to.filter(id=request.user.id).exists():
        raise PermissionDenied("Вам не назначен этот тест")

    if request.method == 'POST':
        correct = 0
        total = test.questions.count()
        answers = []
        for question in test.questions.all():
            user_answer = request.POST.get(f'q_{question.id}', '').strip().lower()
            is_correct = user_answer == question.correct_option
            if is_correct:
                correct += 1
            answers.append({
                'question': question,
                'user_answer': user_answer,
                'correct_answer': question.correct_option,
                'is_correct': is_correct,
            })
        percent = round((correct / total) * 100, 2) if total else 0

        # Сохраняем результат в TestResult с привязкой к TeacherTest
        result = TestResult.objects.create(
            user=request.user,
            test_type='teacher',
            score=correct,
            total_questions=total,
            percent=percent,
            correct_answers=correct,
            percentage=percent,
            teacher_test=test,  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
            category_results={'teacher_test': {'name': test.title, 'correct': correct, 'total': total}}
        )
        # Сохраняем детали ответов
        for answer in answers:
            TestAnswer.objects.create(
                result=result,
                question_id=answer['question'].id,
                question_text=answer['question'].question_text,
                user_answer=answer['user_answer'],
                user_answer_text=_get_answer_text(answer['question'], answer['user_answer']),
                correct_answer=answer['correct_answer'],
                correct_answer_text=_get_answer_text(answer['question'], answer['correct_answer']),
                is_correct=answer['is_correct']
            )
        notify_teacher_about_test_completion(test.teacher, request.user, result)
        messages.success(request, f'Тест завершен! Ваш результат: {correct}/{total} ({percent}%)')
        return redirect('result_detail', pk=result.id)

    questions = test.questions.all()
    return render(request, 'student/take_teacher_test.html', {'test': test, 'questions': questions})


@login_required
@teacher_required
def teacher_lab_detail(request, lab_id):
    # Получаем работу или возвращаем 404
    lab = get_object_or_404(LabWork, id=lab_id)

    # Проверяем, что пользователь - учитель
    if not request.user.profile.role == 'teacher':
        return redirect('home')

    # Проверяем, что работа принадлежит студенту этого учителя
    if lab.student.profile.teacher != request.user:
        return redirect('teacher_labs')

    context = {
        'lab': lab,
        'student': lab.student,
        'student_profile': lab.student.profile,
    }
    return render(request, 'teacher/teacher_lab_detail.html', context)


@login_required
@teacher_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(
        LabSubmission.objects.select_related(
            'student__profile',
            'lab_work',
            'graded_by__profile'
        ),
        id=submission_id,
        lab_work__created_by=request.user
    )

    if request.method == 'POST':
        grade = request.POST.get('grade')
        comment = request.POST.get('comment', '').strip()

        valid_grades = ['5', '4', '3', '2', 'н']
        if grade not in valid_grades:
            messages.error(request, 'Выберите корректную оценку.')
            return redirect('submission_detail', submission_id=submission.id)

        submission.grade = grade
        submission.comment = comment
        submission.checked = True
        submission.status = 'graded'
        submission.graded_at = timezone.now()
        submission.graded_by = request.user
        submission.save()
        notify_student_about_lab_grade(request.user, submission.student, submission)
        messages.success(request, 'Оценка за лабораторную работу сохранена.')
        return redirect('submission_detail', submission_id=submission.id)
    student_profile = getattr(submission.student, 'profile', None)
    student_submissions_count = LabSubmission.objects.filter(
        student=submission.student
    ).count()

    # Определяем тип файла для правильного отображения в шаблоне
    filename = os.path.basename(submission.submitted_file.name) if submission.submitted_file else ''
    file_extension = os.path.splitext(filename)[1].lower()

    # Расширения, которые можно просмотреть в iframe/embed
    viewable_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif'}
    can_preview = file_extension in viewable_extensions

    context = {
        'submission': submission,
        'lab': submission.lab_work,
        'student': submission.student,
        'student_profile': student_profile,
        'student_full_name': student_profile.full_name if student_profile else submission.student.username,
        'student_username': submission.student.username,
        'student_course': student_profile.course if student_profile else '-',
        'student_submissions_count': student_submissions_count,
        'submitted_file_name': filename,
        'submitted_file_extension': file_extension,
        'can_preview': can_preview,
        'file_download_url': f'/teacher/lab/submission/{submission.id}/download/',
    }

    return render(request, 'teacher/students_lab_detail.html', context)

# Добавьте функцию экспорта в Excel:
@login_required
@teacher_required
def export_student_results_excel(request):
    """Экспорт результатов учеников в Excel"""
    student_id = request.GET.get('student_id')
    type_filter = request.GET.get('type_filter', '')
    grade_filter = request.GET.get('grade_filter', '')

    # Получаем данные с теми же фильтрами, что и на странице
    students_qs = User.objects.filter(
        profile__role='student',
        profile__teacher=request.user
    ).select_related('profile')

    test_results = TestResult.objects.filter(
        user__profile__teacher=request.user
    ).select_related('user', 'user__profile').order_by('-date_completed')

    lab_results = LabSubmission.objects.filter(
        student__profile__teacher=request.user
    ).select_related('student__profile', 'lab_work').order_by('-submitted_at')

    if student_id:
        test_results = test_results.filter(user_id=student_id)
        lab_results = lab_results.filter(student_id=student_id)

    if type_filter == 'test':
        lab_results = lab_results.none()
    elif type_filter == 'lab':
        test_results = test_results.none()

    if grade_filter:
        if grade_filter == 'pending':
            test_results = test_results.filter(grade__isnull=True)
            lab_results = lab_results.filter(grade__isnull=True)
        else:
            test_results = test_results.filter(grade=grade_filter)
            lab_results = lab_results.filter(grade=grade_filter)

    # Создаем книгу Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Результаты учеников"

    # Стили
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2f66ff", end_color="2f66ff", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Заголовки
    headers = ['Тип', 'Ученик', 'Название', 'Результат', 'Процент', 'Оценка', 'Дата']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Заполняем данными
    row = 2

    # Тесты
    for result in test_results:
        user_name = result.user.profile.full_name or result.user.username
        title = result.get_test_type_display()
        score = f"{result.score}/{result.total_questions}"
        percent = f"{result.percent}%" if result.percent else "—"
        grade = result.get_grade_display() if result.grade else "—"
        date = result.date_completed.strftime("%d.%m.%Y %H:%M")

        ws.cell(row=row, column=1, value="Тест").border = border
        ws.cell(row=row, column=2, value=user_name).border = border
        ws.cell(row=row, column=3, value=title).border = border
        ws.cell(row=row, column=4, value=score).border = border
        ws.cell(row=row, column=5, value=percent).border = border
        ws.cell(row=row, column=6, value=grade).border = border
        ws.cell(row=row, column=7, value=date).border = border
        row += 1

    # Лабораторные работы
    for submission in lab_results:
        user_name = submission.student.profile.full_name or submission.student.username
        title = f"Лабораторная: {submission.lab_work.title}"
        score = submission.grade or "—"
        percent = "—"
        grade = submission.grade or "—"
        date = submission.submitted_at.strftime("%d.%m.%Y %H:%M")

        ws.cell(row=row, column=1, value="Лабораторная").border = border
        ws.cell(row=row, column=2, value=user_name).border = border
        ws.cell(row=row, column=3, value=title).border = border
        ws.cell(row=row, column=4, value=score).border = border
        ws.cell(row=row, column=5, value=percent).border = border
        ws.cell(row=row, column=6, value=grade).border = border
        ws.cell(row=row, column=7, value=date).border = border
        row += 1

    # Автоматическая ширина колонок
    for col in range(1, 8):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].auto_width = True

    # Формируем имя файла
    filename = f"student_results_{timezone.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"

    # Сохраняем в response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response

@login_required
def get_notifications(request):
    """Получение уведомлений пользователя (AJAX)"""
    notifications = Notification.objects.filter(recipient=request.user)[:20]
    html = render_to_string('includes/notifications.html', {'notifications': notifications}, request=request)
    return JsonResponse({'html': html})

@login_required
def mark_notification_read(request, notification_id):
    """Отметить уведомление как прочитанное"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'ok'})


@login_required
def mark_all_notifications_read(request):
    """Отметить все уведомления как прочитанные"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    # Если AJAX запрос, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        return JsonResponse({'status': 'ok', 'count': 0})

    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def get_unread_notifications_count(request):
    """Получение количества непрочитанных уведомлений"""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def delete_notification(request, notification_id):
    """Удалить уведомление"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    return JsonResponse({'status': 'ok'})

@login_required
def delete_all_notifications(request):
    """Удалить все уведомления пользователя"""
    Notification.objects.filter(recipient=request.user).delete()
    return JsonResponse({'status': 'ok'})





@login_required
def serve_submission_file(request, submission_id):
    """Отдельный view для отдачи файла с правильной обработкой"""
    submission = get_object_or_404(
        LabSubmission,
        id=submission_id,
        lab_work__created_by=request.user
    )

    if not submission.submitted_file:
        return HttpResponse("Файл не найден", status=404)

    filename = os.path.basename(submission.submitted_file.name)
    return get_file_response(submission.submitted_file, filename)