from .models import Notification

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