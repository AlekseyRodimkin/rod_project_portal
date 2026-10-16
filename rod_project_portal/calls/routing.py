from django.urls import re_path, path
from .consumers import CallConsumer, IncomingCallConsumer

websocket_urlpatterns = [
    re_path(r"ws/call/$", CallConsumer.as_asgi()),
    path("ws/incoming/", IncomingCallConsumer.as_asgi()),
]
