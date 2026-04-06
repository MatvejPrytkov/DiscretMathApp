import os
import django
import pandas as pd
from sqlalchemy import create_engine
from django.db import connection

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from base.models import TestCategory, TestQuestion, TestKindConfig, TestKindCategory


def get_db_config():
    """Получает параметры подключения к БД из настроек Django"""
    from django.conf import settings

    db_settings = settings.DATABASES['default']

    if db_settings['ENGINE'] == 'django.db.backends.sqlite3':
        return f"sqlite:///{db_settings['NAME']}"
    elif db_settings['ENGINE'] == 'django.db.backends.postgresql':
        return f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
    elif db_settings['ENGINE'] == 'django.db.backends.mysql':
        return f"mysql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
    else:
        raise ValueError(f"Unsupported database engine: {db_settings['ENGINE']}")


def import_from_table(table_name, category_code, category_name):
    """Импортирует вопросы из таблицы БД в модель TestQuestion"""

    print(f"\nИмпорт из таблицы: {table_name} → категория '{category_name}'")

    try:
        # 1. Создаем или получаем категорию
        category, created = TestCategory.objects.get_or_create(
            code=category_code,
            defaults={
                'name': category_name,
                'order': {
                    'graphs': 1,
                    'logic': 2,
                    'plenty': 3,
                    'final': 4
                }.get(category_code, 5)
            }
        )

        if created:
            print(f"  Создана новая категория: {category.name}")
        else:
            print(f"  Используем существующую категорию: {category.name}")

        # 2. Подключаемся к БД через SQLAlchemy для чтения таблицы
        db_url = get_db_config()
        engine = create_engine(db_url)

        # 3. Читаем данные из таблицы
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, engine)

        print(f"  Найдено {len(df)} вопросов в таблице")

        # 4. Импортируем каждый вопрос
        imported_count = 0
        skipped_count = 0

        for index, row in df.iterrows():
            # Проверяем, есть ли уже такой вопрос
            existing = TestQuestion.objects.filter(
                category=category,
                question_text=row['question']
            ).exists()

            if existing:
                skipped_count += 1
                continue

            # Создаем новый вопрос
            try:
                TestQuestion.objects.create(
                    category=category,
                    question_text=row['question'],
                    option_a=row['answer1'],
                    option_b=row['answer2'],
                    option_c=row['answer3'],
                    option_d=row['answer4'],
                    correct_option=row['correct_answer'].lower().strip() if pd.notna(row['correct_answer']) else 'a',
                    is_active=True
                )
                imported_count += 1

            except Exception as e:
                print(f"  Ошибка при импорте вопроса {index + 1}: {e}")

        print(f"  Импортировано: {imported_count}, пропущено (дубликаты): {skipped_count}")

        return imported_count

    except Exception as e:
        print(f"  Ошибка импорта таблицы {table_name}: {e}")
        return 0


def setup_test_configurations():
    """Настраивает конфигурации тестов"""

    print("\n" + "=" * 60)
    print("НАСТРОЙКА КОНФИГУРАЦИЙ ТЕСТОВ")
    print("=" * 60)

    # 1. Конфигурация для входного тестирования (start)
    start_config, created = TestKindConfig.objects.get_or_create(
        code='start',
        defaults={
            'title': 'Входное тестирование',
            'template': 'student/start.html',
            'result_template': 'student/result_detail.html',
            'description': 'Тестирование перед началом обучения',
            'is_active': True,
            'order': 1
        }
    )

    print(f"Конфигурация 'Входное тестирование': {'создана' if created else 'уже существует'}")

    # 2. Конфигурация для итогового тестирования (final)
    final_config, created = TestKindConfig.objects.get_or_create(
        code='final',
        defaults={
            'title': 'Итоговое тестирование',
            'template': 'student/final.html',
            'result_template': 'student/result_detail.html',
            'description': 'Итоговый контроль знаний',
            'is_active': True,
            'order': 2
        }
    )

    print(f"Конфигурация 'Итоговое тестирование': {'создана' if created else 'уже существует'}")

    # 3. Настраиваем связи с категориями

    # Для входного тестирования: по 5 вопросов из каждой категории
    start_categories = [
        ('graphs', 'Графы', 5),
        ('logic', 'Логика', 5),
        ('plenty', 'Множества', 5)
    ]

    for code, name, count in start_categories:
        try:
            category = TestCategory.objects.get(code=code)
            tkc, created = TestKindCategory.objects.get_or_create(
                test_kind=start_config,
                category=category,
                defaults={'questions_count': count}
            )
            if not created:
                tkc.questions_count = count
                tkc.save()
            print(f"  Настроено: {start_config.title} → {name}: {count} вопросов")
        except TestCategory.DoesNotExist:
            print(f"  Категория {name} не найдена!")

    # Для итогового тестирования: все вопросы из категории final
    try:
        final_category = TestCategory.objects.get(code='final')
        tkc, created = TestKindCategory.objects.get_or_create(
            test_kind=final_config,
            category=final_category,
            defaults={'questions_count': 0}  # 0 означает "все вопросы"
        )
        if not created:
            tkc.questions_count = 0
            tkc.save()
        print(f"  Настроено: {final_config.title} → Итоговый тест: все вопросы")
    except TestCategory.DoesNotExist:
        print("  Категория 'final' не найдена!")


def check_existing_data():
    """Проверяет существующие данные"""

    print("\n" + "=" * 60)
    print("ПРОВЕРКА СУЩЕСТВУЮЩИХ ДАННЫХ")
    print("=" * 60)

    # Проверяем категории
    categories = TestCategory.objects.all()
    print(f"\nСуществующие категории ({categories.count()}):")
    for cat in categories:
        q_count = TestQuestion.objects.filter(category=cat).count()
        print(f"  {cat.name} ({cat.code}): {q_count} вопросов")

    # Проверяем конфигурации тестов
    configs = TestKindConfig.objects.all()
    print(f"\nКонфигурации тестов ({configs.count()}):")
    for config in configs:
        tkc_count = TestKindCategory.objects.filter(test_kind=config).count()
        print(f"  {config.title} ({config.code}): {tkc_count} категорий")


def main():
    """Основная функция импорта"""

    print("=" * 60)
    print("ИМПОРТ ВОПРОСОВ ИЗ СУЩЕСТВУЮЩИХ ТАБЛИЦ БД")
    print("=" * 60)

    # 1. Проверяем существующие данные
    check_existing_data()

    # 2. Импортируем данные из таблиц
    import_mapping = [
        ('graphs', 'graphs', 'Графы'),
        ('logic', 'logic', 'Логика'),
        ('plenty', 'plenty', 'Множества'),
        ('final_test', 'final', 'Итоговый тест')
    ]

    total_imported = 0
    for table_name, category_code, category_name in import_mapping:
        imported = import_from_table(table_name, category_code, category_name)
        total_imported += imported

    print(f"\nВсего импортировано вопросов: {total_imported}")

    # 3. Настраиваем конфигурации тестов
    setup_test_configurations()

    # 4. Финальная проверка
    check_existing_data()

    print("\n" + "=" * 60)
    print("ИМПОРТ ЗАВЕРШЕН!")
    print("=" * 60)


if __name__ == "__main__":
    main()