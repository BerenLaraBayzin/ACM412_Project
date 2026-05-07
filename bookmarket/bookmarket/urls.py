from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.register),
    path('users/', include('users.urls')),
    path('', include('books.urls')), # Kitaplar ana sayfa olacak
]

# Medya dosyalarını (kitap resimleri) tarayıcıda görebilmek için:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)