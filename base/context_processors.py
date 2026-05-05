from .models import Notification, TestResult


def notifications_count(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}
def test_type_context(request):
    """Добавляет test_type в контекст для всех страниц"""
    test_type = None
    if request.resolver_match and request.resolver_match.url_name == 'test_view':
        if request.resolver_match.args:
            test_type = request.resolver_match.args[0]
    return {'test_type': test_type}
def has_final_test(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        has_final = TestResult.objects.filter(user=request.user, test_type='final').exists()
        final_result = TestResult.objects.filter(user=request.user, test_type='final').first() if has_final else None
        return {
            'has_final_test': has_final,
            'final_test_result': final_result
        }
    return {'has_final_test': False, 'final_test_result': None}
def has_test_results(request):
    """Проверяет, есть ли у студента результаты тестов"""
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'student':
        has_results = TestResult.objects.filter(user=request.user).exists()
        return {'test_results_exists': has_results}
    return {'test_results_exists': False}