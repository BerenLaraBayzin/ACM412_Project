from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register(r'books', api_views.BookViewSet, basename='api-book')
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')

urlpatterns = [
    path('', include(router.urls)),
]
