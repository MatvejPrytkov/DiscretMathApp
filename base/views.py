from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import RegistrationForm
from django.contrib.auth.forms import AuthenticationForm
import pandas as pd
import random
import openpyxl
def index(request):
    return render(request, 'index.html')
# Create your views here.
def start (request):
    # Список файлов и их названия для отчета
    files = {
        'graphs': 'graphs.xlsx',
        'logic': 'logic.xlsx',
        'plenty': 'Plenty.xlsx'
    }

    if request.method == 'POST':
        results = {}
        total_correct = 0

        for key, filename in files.items():
            df = pd.read_excel(filename)
            correct_count = 0

            # Получаем ID вопросов, которые были заданы пользователю (скрытые поля в форме)
            question_ids = request.POST.getlist(f'ids_{key}')

            for q_id in question_ids:
                user_answer = request.POST.get(f'q_{key}_{q_id}')
                # Ищем правильный ответ в Excel по ID
                # В ваших файлах колонки называются по-разному (id, question_id, question_number)
                id_col = df.columns[0]
                actual_correct = df[df[id_col] == int(q_id)]['correct_answer'].values[0]

                if user_answer == str(actual_correct).strip():
                    correct_count += 1

            results[key] = {
                'name': filename,
                'correct': correct_count,
                'total': len(question_ids)
            }
            total_correct += correct_count

        return render(request, 'results.html', {'results': results, 'total': total_correct})

    # GET запрос: Выбираем случайные вопросы
    questions_to_render = []

    for key, filename in files.items():
        df = pd.read_excel(filename)
        # Выбираем 5 случайных строк
        sample = df.sample(n=min(5, len(df))).to_dict('records')

        # Определяем имя колонки с ID (они разные в ваших файлах)
        id_col = df.columns[0]

        for item in sample:
            item['category'] = key
            item['id_val'] = item[id_col]
            questions_to_render.append(item)

    # Перемешиваем все 15 вопросов между собой
    random.shuffle(questions_to_render)

    return render(request, 'start.html', {'questions': questions_to_render})
def finish (request):
    return render(request, 'final.html')



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Автоматически логиним пользователя
            messages.success(request, f'Регистрация успешна! Добро пожаловать, {user.profile.full_name}!')
            return redirect('initial')  # Перенаправляем на главную
        else:
            form = RegistrationForm()
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.profile.full_name}!')
            return redirect('initial')
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('initial')