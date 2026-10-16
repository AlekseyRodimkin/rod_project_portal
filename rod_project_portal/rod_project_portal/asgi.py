"""
ASGI config for rod_project_portal project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import calls.routing  # роутинг внутри приложения

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rod_project_portal.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(calls.routing.websocket_urlpatterns)
        )
    ),
})
