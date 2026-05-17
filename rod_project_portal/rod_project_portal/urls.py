from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def redirect_to_portal(request):
    return redirect('/portal/')


urlpatterns = [
    path('', redirect_to_portal),
    path('portal/admin/', admin.site.urls),
    path('portal/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
