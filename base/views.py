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
LETTER_TO_COL = {
    'a': 'answer1',
    'b': 'answer2',
    'c': 'answer3',
    'd': 'answer4',
}

def normalize_letter(x):
    return (str(x).strip().lower() if x is not None else '')

def option_text_from_row(row, letter: str) -> str:
    letter = normalize_letter(letter)
    col = LETTER_TO_COL.get(letter)
    if not col or col not in row.columns:
        return ''
    val = row[col].values[0]
    if val is None:
        return ''
    text = str(val).strip()
    # опционально: убрать префикс "a. " / "b. " и т.п. в начале
    if len(text) >= 3 and text[1] == '.' and text[0].lower() in ['a','b','c','d']:
        text = text[2:].strip()
    return text
def index(request):
    return render(request, 'index.html')
# Create your views here.
@login_required
def start(request):
    files = {
        'graphs': 'static/graphs.xlsx',
        'logic': 'static/logic.xlsx',
        'plenty': 'static/Plenty.xlsx'
    }

    if request.method == 'POST':
        results = {}
        total_correct = 0

        for key, filename in files.items():
            try:
                df = pd.read_excel(filename)
                id_col = df.columns[0]  # первая колонка

                # 🎯 Получаем ID вопросов этой категории
                question_ids = request.POST.getlist(f'ids_{key}')
                correct_count = 0

                for q_id in question_ids:
                    user_answer = request.POST.get(f'q_{key}_{q_id}')
                    if user_answer:  # проверяем, что ответ выбран
                        actual_row = df[df[id_col] == int(q_id)]
                        if not actual_row.empty:
                            actual_correct = str(actual_row['correct_answer'].values[0]).strip()
                            if user_answer == actual_correct:
                                correct_count += 1

                results[key] = {
                    'name': filename,
                    'correct': correct_count,
                    'total': len(question_ids)
                }
                total_correct += correct_count
            except Exception as e:
                results[key] = {'name': filename, 'correct': 0, 'total': 0}

        test_result = TestResult.objects.create(
            user=request.user,
            test_type='start',
            score=total_correct,
            total_questions=15,
            percent=round((total_correct / 15) * 100, 2)
        )

        # сохраняем детализацию

        for key, filename in files.items():
            try:
                df = pd.read_excel(filename)
                # Определяем имя первой колонки (ID) динамически
                id_col = df.columns[0]

                question_ids = request.POST.getlist(f'ids_{key}')

                for q_id in question_ids:
                    user_answer = request.POST.get(f'q_{key}_{q_id}')
                    if user_answer:
                        user_answer = str(user_answer).strip()
                        # Приводим колонку ID к строке для надежного сравнения
                        df[id_col] = df[id_col].astype(str)
                        actual_row = df[df[id_col] == str(q_id)]

                        if not actual_row.empty:
                            correct_answer_text = str(actual_row['correct_answer'].values[0]).strip()
                            q_text = "Текст вопроса не найден"
                            if 'question' in df.columns and not actual_row.empty:
                                q_text = str(actual_row['question'].values[0])

                            TestAnswer.objects.create(
                            result=test_result,
                            question_id=int(q_id),
                            question_text=q_text,
                            user_answer=str(user_answer).strip(),
                            correct_answer=correct_answer_text,
                            is_correct=(user_answer == correct_answer_text)
                        )
            except Exception as e:
                print(f"Ошибка при сохранении ответа: {e}")
                continue

        return render(request, 'results.html', {
            'results': results,
            'total': total_correct,
            'saved': True
        })

    # GET запрос остается БЕЗ ИЗМЕНЕНИЙ
    questions_to_render = []
    for key, filename in files.items():
        try:
            df = pd.read_excel(filename)
            sample = df.sample(n=min(5, len(df))).to_dict('records')
            id_col = df.columns[0]

            for item in sample:
                item['category'] = key
                item['id_val'] = item[id_col]
                questions_to_render.append(item)
        except:
            continue

    random.shuffle(questions_to_render)
    return render(request, 'start.html', {'questions': questions_to_render})
@login_required
def finish (request):
    filename = 'static/final_test.xlsx'

    if request.method == 'POST':
        try:
            df = pd.read_excel(filename)
        except Exception as e:
            return render(request, 'results_final.html', {'error': 'Файл с тестом не найден.'})

        correct_count = 0
        total_questions = 0

        # Получаем список ID вопросов, которые были в форме
        question_ids = request.POST.getlist('question_ids')
        total_questions = len(question_ids)

        for q_id in question_ids:
            user_answer = request.POST.get(f'q_{q_id}')
            # Находим строку с нужным ID
            # В вашем файле колонка называется "id"
            actual_row = df[df['id'] == int(q_id)]

            if not actual_row.empty:
                actual_correct = str(actual_row['correct_answer'].values[0]).strip()
                if user_answer == actual_correct:
                    correct_count += 1

        test_result = TestResult.objects.create(
            user=request.user,
            test_type='final',
            score=correct_count,
            total_questions=total_questions,
            percent=round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
        )

        for q_id in question_ids:
            user_answer = request.POST.get(f'q_{q_id}', '') or ''
            actual_row = df[df['id'] == int(q_id)]
            if not actual_row.empty:
                correct_letter = str(actual_row['correct_answer'].values[0]).strip()

                q_text = ''
                if 'question' in df.columns:
                    q_text = str(actual_row['question'].values[0])

                def option_text(letter: str) -> str:
                    letter = (letter or '').strip().lower()
                    if letter in ['a', 'b', 'c', 'd'] and letter in df.columns:
                        return str(actual_row[letter].values[0]).strip()
                    return ''
                TestAnswer.objects.create(
                    result=test_result,
                    question_id=int(q_id),
                    question_text=q_text,
                    user_answer=str(user_answer).strip(),
                    user_answer_text= option_text(user_answer),
                    correct_answer=correct_letter,
                    correct_answer_text = option_text(correct_letter),
                    is_correct=(str(user_answer).strip() == correct_letter)
                )

        return render(request, 'results_final.html', {
            'correct': correct_count,
            'total': total_questions,
            'percent': round((correct_count / total_questions) * 100, 2),
            'saved': True
        })

    # GET запрос: Загружаем все вопросы из итогового теста
    try:
        df = pd.read_excel(filename)
        # Превращаем в список словарей и перемешиваем (опционально)
        questions = df.to_dict('records')
        random.shuffle(questions)
    except Exception as e:
        questions = []

    return render(request, 'final.html', {'questions': questions})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            full_name = getattr(getattr(user, 'profile', None), 'full_name', user.get_username())
            messages.success(request, f'Регистрация успешна! Добро пожаловать, {full_name}!')

            return redirect('profile')
        else:
            # ВАЖНО: не перезатираем form, иначе пропадут ошибки в форме
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
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            full_name = getattr(getattr(user, 'profile', None), 'full_name', user.get_username())
            messages.success(request, f'Добро пожаловать, {full_name}!')

            return redirect('profile')
        else:
            messages.error(request, 'Неверный логин или пароль.')

    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('initial')
@login_required
def profile(request):
    results = TestResult.objects.filter(user=request.user).order_by('-date_completed')
    return render(request, 'profile.html', {'results': results})
@login_required
def result_detail(request, pk):
    result = get_object_or_404(TestResult, pk=pk, user=request.user)
    answers = result.answers.all().order_by('question_id')
    return render(request, 'result_detail.html', {'result': result, 'answers': answers})


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