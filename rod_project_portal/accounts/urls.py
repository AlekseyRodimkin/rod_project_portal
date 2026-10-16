from django.urls import path
from .views import (
    AppLogoutView, ServicesView, Main, create_ticket, NotificationsView, AppLoginView
)

app_name = "accounts"
urlpatterns = [
    path(
        "login/",
        AppLoginView.as_view(),
        name="login",
    ),
    path("logout/", AppLogoutView.as_view(), name="logout"),
    # path("register/", RegisterView.as_view(), name="register"),
    path("", Main.as_view(), name="main"),
    path("services/", ServicesView.as_view(), name="services"),
    path('create-ticket/', create_ticket, name='create_ticket'),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
]
