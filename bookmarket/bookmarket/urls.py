from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('api/', include('books.api_urls')),
    path('', include('books.urls')),
]

# Yüklenen kitap görsellerini servis et.
# DEBUG=True iken Django'nun standart helper'ı; production'da (free Render)
# bulut storage olmadığı için ephemeral diskten direkt servis ediyoruz.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        path(
            'media/<path:path>',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
