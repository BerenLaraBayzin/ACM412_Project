from .models import Category


def nav(request):
    return {
        'nav_categories': list(Category.objects.all().order_by('name')[:8]),
    }
