from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from .forms import RegistrationForm, GradeTestForm
from .models import LabWork, LabSubmission, TestResult, TestKindCategory, TestKindConfig
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
from django.http import HttpResponse
from django.utils import timezone
from .forms import MyLoginForm, LabWorkForm
from django.db.models import Q
from django.core.paginator import Paginator
from .models import TestCategory, TestQuestion
def index(request):
    return render(request, 'index.html')
@login_required
@student_required
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

        # Оценки за лабораторные
        lab_submissions = LabSubmission.objects.filter(
            student=user,
        ).select_related('lab_work')

        # Оценки за тесты
        test_grades = TestResult.objects.filter(
            user=user
        ).order_by('-date_completed')  # сортировка по дате

        context = {
            'user': user,
            'lab_grades': lab_submissions,
            'test_grades': test_grades,
            'results': test_grades,  # для блока "История тестов"
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
        test_count=Count('testresult'),
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
    # Словарь для перевода
    TRANSLATIONS = {
        'graphs': 'Графы',
        'logic': 'Логика',
        'plenty': 'Множества',
        'final': 'Итоговый',
        'start': 'Входной'
    }
    all_results = TestResult.objects.filter(user__profile__teacher=request.user)
    for result in all_results:
        if result.category_results:
            for theme, data in result.category_results.items():
                if theme not in theme_stats:
                    # Используем перевод, если он есть, иначе оставляем ключ
                    display_name = TRANSLATIONS.get(theme, theme)
                    theme_stats[theme] = {'correct': 0, 'total': 0, 'name': display_name}

                theme_stats[theme]['correct'] += data.get('correct', 0)
                theme_stats[theme]['total'] += data.get('total', 0)

    total_tests_passed = my_students.aggregate(total=Sum('test_count'))['total'] or 0
    total_labs_submitted = my_students.aggregate(total=Sum('lab_submission_count'))['total'] or 0  # ← ДОБАВЛЕНО
    lab_count = LabWork.objects.filter(created_by=request.user).count()
    pending_submissions = LabSubmission.objects.filter(
        status='under_review',
        lab_work__created_by=request.user
    ).count()

    return render(request, 'teacher/teacher_dashboard.html', {
        'students': my_students,
        'student_count': my_students.count(),
        'total_tests_passed': total_tests_passed,
        'test_stats': test_stats,  # Типы тестов
        'grade_distribution': grade_distribution,  # Оценки
        'theme_stats': list(theme_stats.items()),  # Темы
        'lab_count': lab_count,
        'pending_submissions': pending_submissions,
        'total_labs_submitted': total_labs_submitted,
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
    ).select_related('student__profile', 'lab_work').order_by('-submitted_at')

    return render(request, 'teacher/teacher_labs.html', {
        'labs': labs,
        'submissions': submissions
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
        if submitted_file:
            LabSubmission.objects.create(
                lab_work=lab,
                student=request.user,
                submitted_file=submitted_file,
                status='under_review'
            )
            messages.success(request, 'Работа сдана на проверку!')
            return redirect('student_labs')
        else:
            messages.error(request, 'Прикрепите файл!')

    return render(request, 'student/submit_lab.html', {'lab': lab})