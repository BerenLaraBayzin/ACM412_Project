from .models import Category, Message


def nav(request):
    """Navigasyon için global bağlam: kategoriler ve okunmamış mesaj sayısı."""
    unread = 0
    if request.user.is_authenticated:
        unread = Message.objects.filter(
            receiver=request.user, is_read=False,
        ).count()
    return {
        'nav_categories': list(Category.objects.all().order_by('name')[:8]),
        'unread_messages': unread,
    }
