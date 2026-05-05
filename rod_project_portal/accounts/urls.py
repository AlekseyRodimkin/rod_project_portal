from django.contrib.auth.views import LoginView
from django.urls import path

from .views import (
    AppLogoutView, Main, create_ticket, NotificationsView
)

app_name = "accounts"
urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
            next_page="accounts:main",
        ),
        name="login",
    ),
    path("logout/", AppLogoutView.as_view(), name="logout"),
    # path("register/", RegisterView.as_view(), name="register"),
    path("", Main.as_view(), name="main"),
    path('create-ticket/', create_ticket, name='create_ticket'),
    path("notifications/", NotificationsView.as_view(), name="notifications"),
]
