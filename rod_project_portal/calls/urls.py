from django.urls import path
from .views import CallView, ContactsView

app_name = "calls"

urlpatterns = [
    path("contacts/", ContactsView.as_view(), name="contacts"),
    path(
        "call/<str:room_name>/", CallView.as_view(), name="call_room"
    ),  # Динамическая комната для звонка
    path("calls/", CallView.as_view(), name="call_test"),
]
