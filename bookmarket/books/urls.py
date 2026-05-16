from django.urls import path
from . import views

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('book/<int:pk>/', views.book_detail, name='book_detail'),
    path('book/new/', views.book_create, name='book_create'),
    path('book/<int:pk>/edit/', views.book_update, name='book_update'),
    path('book/<int:pk>/delete/', views.book_delete, name='book_delete'),
    path('book/<int:pk>/satin-al/', views.order_create, name='order_create'),
    path('book/<int:pk>/favori/', views.favorite_toggle, name='favorite_toggle'),
    path('favorilerim/', views.favorites_list, name='favorites_list'),
    path('isbn-lookup/', views.isbn_lookup, name='isbn_lookup'),
    path('mesajlar/', views.message_list, name='message_list'),
    path(
        'book/<int:book_pk>/mesaj/',
        views.message_compose,
        name='message_compose',
    ),
    path(
        'book/<int:book_pk>/mesaj/kullanici/<int:user_pk>/',
        views.message_thread,
        name='message_thread',
    ),
    path(
        'book/<int:book_pk>/mesaj/kullanici/<int:user_pk>/ajax/',
        views.message_send_ajax,
        name='message_send_ajax',
    ),
]