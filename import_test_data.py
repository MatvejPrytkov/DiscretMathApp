import os
import django
import pandas as pd

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from base.models import TestCategory, TestQuestion


def import_excel_to_db():
    # Соответствие файлов категориям
    file_category_map = {
        'graphs.xlsx': {'code': 'graphs', 'name': 'Графы'},
        'logic.xlsx': {'code': 'logic', 'name': 'Логика'},
        'Plenty.xlsx': {'code': 'plenty', 'name': 'Множества'},
        'final_test.xlsx': {'code': 'final', 'name': 'Итоговый тест'},
    }

    for filename, category_info in file_category_map.items():
        filepath = f'core/static/{filename}'

        if not os.path.exists(filepath):
            print(f"Файл {filepath} не найден")
            continue

        try:
            # Создаем или получаем категорию
            category, created = TestCategory.objects.get_or_create(
                code=category_info['code'],
                defaults={'name': category_info['name']}
            )

            # Читаем Excel файл
            df = pd.read_excel(filepath)

            # Импортируем вопросы
            imported_count = 0
            for _, row in df.iterrows():
                # Предполагаем структуру Excel: question, answer1, answer2, answer3, answer4, correct_answer
                question = TestQuestion.objects.create(
                    category=category,
                    question_text=str(row['question']).strip(),
                    option_a=str(row.get('answer1', '')).strip(),
                    option_b=str(row.get('answer2', '')).strip(),
                    option_c=str(row.get('answer3', '')).strip(),
                    option_d=str(row.get('answer4', '')).strip(),
                    correct_option=str(row['correct_answer']).strip().lower(),
                    difficulty='medium'
                )
                imported_count += 1

            print(f"Импортировано {imported_count} вопросов из {filename} в категорию {category.name}")

        except Exception as e:
            print(f"Ошибка при импорте {filename}: {e}")


if __name__ == '__main__':
    import_excel_to_db()