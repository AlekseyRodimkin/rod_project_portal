from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from calls.views import push_subscribe
from accounts.utils import service_worker


def redirect_to_portal(request):
    return redirect("/portal/")


urlpatterns = [
    path("", redirect_to_portal),
    path("portal/admin/", admin.site.urls),
    path("portal/", include("accounts.urls")),
    path("portal/", include("youtube.urls")),
    path("portal/", include("calls.urls")),
    path('sw.js', service_worker),
    path('push/subscribe/', push_subscribe),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
