from django.core.management.base import BaseCommand
from base.models import TestKindConfig, TestCategory, TestKindCategory


class Command(BaseCommand):
    help = 'Заполняет начальные конфигурации тестов'

    def handle(self, *args, **options):
        # Создаем или получаем тестовые категории
        categories_data = [
            {'code': 'graphs', 'name': 'Графы'},
            {'code': 'logic', 'name': 'Логика'},
            {'code': 'plenty', 'name': 'Множества'},
            {'code': 'final', 'name': 'Итоговый тест'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = TestCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={'name': cat_data['name'], 'is_active': True}
            )
            categories[cat.code] = cat
            if created:
                self.stdout.write(f"Создана категория: {cat.name}")

        # Конфигурация входного тестирования
        start_test, created = TestKindConfig.objects.get_or_create(
            code='start',
            defaults={
                'title': 'Входное тестирование',
                'template': 'student/start.html',
                'result_template': 'student/result_detail.html',
                'is_active': True,
                'order': 1
            }
        )

        if created:
            # Добавляем категории с количеством вопросов
            TestKindCategory.objects.create(
                test_kind=start_test,
                category=categories['graphs'],
                questions_count=5,
                order=1
            )
            TestKindCategory.objects.create(
                test_kind=start_test,
                category=categories['logic'],
                questions_count=5,
                order=2
            )
            TestKindCategory.objects.create(
                test_kind=start_test,
                category=categories['plenty'],
                questions_count=5,
                order=3
            )
            self.stdout.write("Создана конфигурация входного тестирования")

        # Конфигурация итогового тестирования
        final_test, created = TestKindConfig.objects.get_or_create(
            code='final',
            defaults={
                'title': 'Итоговое тестирование',
                'template': 'student/final.html',
                'result_template': 'student/result_detail.html',
                'is_active': True,
                'order': 2
            }
        )

        if created:
            TestKindCategory.objects.create(
                test_kind=final_test,
                category=categories['final'],
                questions_count=0,  # 0 = все вопросы
                order=1
            )
            self.stdout.write("Создана конфигурация итогового тестирования")

        self.stdout.write(self.style.SUCCESS('Конфигурации тестов успешно созданы!'))