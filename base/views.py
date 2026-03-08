from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import RegistrationForm
from .models import TestResult
from django.contrib.auth.forms import AuthenticationForm
import pandas as pd
import random
from django.contrib.auth.decorators import login_required
import openpyxl
def index(request):
    return render(request, 'index.html')
# Create your views here.
@login_required
def start(request):
    files = {
        'graphs': 'graphs.xlsx',
        'logic': 'logic.xlsx',
        'plenty': 'Plenty.xlsx'
    }

    if request.method == 'POST':
        results = {}
        total_correct = 0

        for key, filename in files.items():
            try:
                df = pd.read_excel(filename)
                id_col = df.columns[0]  # первая колонка = ID

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

        TestResult.objects.create(
            user=request.user,
            test_type='start',
            score=total_correct,
            total_questions=15,
            percent=round((total_correct / 15) * 100, 2)
        )

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
    filename = 'final_test.xlsx'

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

        TestResult.objects.create(
            user=request.user,
            test_type='final',
            score=correct_count,
            total_questions=total_questions,
            percent=round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
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

    return render(request, 'profile', {'form': form})

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


